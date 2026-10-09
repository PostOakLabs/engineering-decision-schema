"""Validate documents against the edi-schema JSON Schemas.

Three document kinds share this module:

``episode``   -- one expert decision (schemas/episode.schema.json)
``manifest``  -- one reproducible flow run (schemas/run-manifest.schema.json)
``report``    -- one profiling run of a proving workload
                 (schemas/zkprof-report.schema.json)

Every function takes a decoded Python object (not JSON text) and returns a list
of :class:`Error`. An empty list means the document is valid. Nothing raises on
invalid input -- that is the whole point of returning errors instead.

JSON Schema cannot express every rule the episode format needs, so the checks
that span fields live here as explicit, individually-named codes. Where a rule
exists in both places (notably ``provenance == "reproduced"`` requiring an
``environment`` block) the schema copy exists for non-Python consumers, and the
copy here exists so the message a human reads names the actual problem.
"""

from __future__ import annotations

import json
import math
import os
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Literal

from jsonschema import Draft202012Validator

__all__ = [
    "SHARE_TOLERANCE",
    "AmbiguousDocumentError",
    "DocumentKind",
    "Error",
    "SCHEMA_DIR",
    "detect_kind",
    "format_errors",
    "load_schema",
    "schema_path",
    "validate",
    "validate_episode",
    "validate_manifest",
    "validate_report",
]

DocumentKind = Literal["episode", "manifest", "report"]

KINDS: tuple[DocumentKind, ...] = ("episode", "manifest", "report")

_SCHEMA_FILES: dict[DocumentKind, str] = {
    "episode": "episode.schema.json",
    "manifest": "run-manifest.schema.json",
    "report": "zkprof-report.schema.json",
}

#: Primitive shares must sum to this, plus or minus this tolerance.
SHARE_SUM_TARGET = 1.0
SHARE_TOLERANCE = 0.02


class AmbiguousDocumentError(ValueError):
    """Raised when a document's kind cannot be determined without ``--type``."""


@dataclass(frozen=True)
class Error:
    """One validation problem, located by JSON-pointer-ish path."""

    code: str
    path: str
    message: str

    def __str__(self) -> str:
        return f"{self.code} at {self.path}: {self.message}"


# --------------------------------------------------------------------------
# Schema location
# --------------------------------------------------------------------------


def _resolve_schema_dir() -> Path:
    """Find the directory holding the three schema files.

    Resolution order: ``EDI_SCHEMA_DIR``, the copy bundled into an installed
    wheel (``edi_schema/schemas``), then the ``schemas/`` directory of a source
    checkout. The last case is what makes an editable install work without
    duplicating the canonical files.
    """
    override = os.environ.get("EDI_SCHEMA_DIR")
    if override:
        return Path(override)

    bundled = Path(__file__).resolve().parent / "schemas"
    if (bundled / "episode.schema.json").is_file():
        return bundled

    for parent in Path(__file__).resolve().parents:
        candidate = parent / "schemas"
        if (candidate / "episode.schema.json").is_file():
            return candidate

    msg = (
        "could not locate edi-schema schema files; set EDI_SCHEMA_DIR to the "
        "directory containing episode.schema.json"
    )
    raise FileNotFoundError(msg)


SCHEMA_DIR: Path = _resolve_schema_dir()

_SCHEMA_CACHE: dict[DocumentKind, Mapping[str, Any]] = {}


def schema_path(kind: DocumentKind) -> Path:
    """Absolute path to the schema file for ``kind``."""
    _check_kind(kind)
    return SCHEMA_DIR / _SCHEMA_FILES[kind]


def load_schema(kind: DocumentKind) -> Mapping[str, Any]:
    """Load (and memoize) the decoded schema for ``kind``."""
    _check_kind(kind)
    if kind not in _SCHEMA_CACHE:
        _SCHEMA_CACHE[kind] = json.loads(schema_path(kind).read_text(encoding="utf-8"))
    return _SCHEMA_CACHE[kind]


def _check_kind(kind: str) -> None:
    if kind not in _SCHEMA_FILES:
        msg = f"unknown document kind {kind!r}; expected one of {sorted(_SCHEMA_FILES)}"
        raise ValueError(msg)


# --------------------------------------------------------------------------
# Schema-level validation
# --------------------------------------------------------------------------


def _pointer(segments: Sequence[Any]) -> str:
    if not segments:
        return "$"
    out = "$"
    for segment in segments:
        if isinstance(segment, int):
            out += f"[{segment}]"
        else:
            out += f".{segment}"
    return out


def _schema_errors(kind: DocumentKind, document: Any) -> list[Error]:
    """Run the JSON Schema and convert failures into :class:`Error` objects.

    Sorted by path then validator so the ordering is stable across runs; a
    validator that reordered its output would make diffs and tests noisy.
    """
    validator = Draft202012Validator(load_schema(kind))
    errors = [
        Error(
            code=f"schema:{item.validator}",
            path=_pointer(list(item.absolute_path)),
            message=item.message,
        )
        for item in validator.iter_errors(document)
    ]
    errors.sort(key=lambda err: (err.path, err.code, err.message))
    return errors


# --------------------------------------------------------------------------
# Cross-field checks (beyond JSON Schema)
# --------------------------------------------------------------------------


def _episode_cross_field(document: Mapping[str, Any]) -> list[Error]:
    errors: list[Error] = []

    # Exactly one candidate must be the chosen one (rejected_because: null).
    candidates = document.get("candidates_considered")
    if isinstance(candidates, list):
        chosen = [
            index
            for index, candidate in enumerate(candidates)
            if isinstance(candidate, Mapping) and candidate.get("rejected_because") is None
        ]
        if len(chosen) == 0:
            errors.append(
                Error(
                    code="E_CANDIDATES_NO_CHOSEN",
                    path="$.candidates_considered",
                    message=(
                        f"no candidate has rejected_because: null; exactly one of "
                        f"{len(candidates)} candidates must be the chosen intervention"
                    ),
                )
            )
        elif len(chosen) > 1:
            joined = ", ".join(f"[{i}]" for i in chosen)
            errors.append(
                Error(
                    code="E_CANDIDATES_MULTIPLE_CHOSEN",
                    path="$.candidates_considered",
                    message=(
                        f"{len(chosen)} candidates have rejected_because: null "
                        f"(at {joined}); exactly one must be the chosen intervention"
                    ),
                )
            )

    # provenance == "reproduced" requires an environment and pinned commits.
    # Mirrors the if/then in the schema; repeated here for a readable message.
    if document.get("provenance") == "reproduced":
        if "environment" not in document:
            errors.append(
                Error(
                    code="E_PROVENANCE_REPRODUCED_REQUIRES_ENVIRONMENT",
                    path="$.environment",
                    message=(
                        'provenance is "reproduced" but no environment block is present; '
                        "a reproduced episode must record the tool versions it was "
                        "reproduced with"
                    ),
                )
            )
        design = document.get("design")
        design_map = design if isinstance(design, Mapping) else {}
        for field_name in ("rtl_commit", "pdk_commit"):
            if not design_map.get(field_name):
                errors.append(
                    Error(
                        code=f"E_PROVENANCE_REPRODUCED_REQUIRES_{field_name.upper()}",
                        path=f"$.design.{field_name}",
                        message=(
                            f'provenance is "reproduced" but design.{field_name} is '
                            "missing; a reproduced episode must pin the commit it was "
                            "reproduced from"
                        ),
                    )
                )

    return errors


def _share_sum_errors(
    document: Mapping[str, Any],
    key: str,
    code: str,
) -> list[Error]:
    entries = document.get(key)
    if not isinstance(entries, list) or not entries:
        return []
    shares = [
        entry.get("share")
        for entry in entries
        if isinstance(entry, Mapping) and isinstance(entry.get("share"), (int, float))
    ]
    if len(shares) != len(entries):
        return []
    total = float(sum(shares))
    # The epsilon absorbs binary-float representation error: shares summing to
    # exactly 1.0 + 0.02 must count as inside the tolerance, not outside it.
    if not math.isclose(total, SHARE_SUM_TARGET, abs_tol=SHARE_TOLERANCE + 1e-9):
        return [
            Error(
                code=code,
                path=f"$.{key}",
                message=(
                    f"{key} shares sum to {total:.4f}, expected "
                    f"{SHARE_SUM_TARGET:.1f} +/- {SHARE_TOLERANCE}"
                ),
            )
        ]
    return []


def _report_cross_field(document: Mapping[str, Any]) -> list[Error]:
    # Phase shares are deliberately NOT checked: phases may nest or overlap and
    # need not partition total_ms. Primitive attribution must partition it.
    return _share_sum_errors(document, "primitives", "E_SHARE_SUM_PRIMITIVES")


def _manifest_cross_field(document: Mapping[str, Any]) -> list[Error]:
    errors: list[Error] = []
    started_at = document.get("started_at")
    if not isinstance(started_at, str):
        return errors
    try:
        parsed = datetime.fromisoformat(started_at.replace("Z", "+00:00"))
    except ValueError:
        errors.append(
            Error(
                code="E_STARTED_AT_NOT_ISO8601",
                path="$.started_at",
                message=(
                    f"started_at {started_at!r} is not an ISO 8601 date-time; "
                    "run manifests are compared across machines and need a "
                    "timezone offset"
                ),
            )
        )
        return errors
    if parsed.tzinfo is None:
        errors.append(
            Error(
                code="E_STARTED_AT_NO_TIMEZONE",
                path="$.started_at",
                message=(
                    f"started_at {started_at!r} has no timezone offset; two machines "
                    "in different zones would produce text that cannot be ordered"
                ),
            )
        )
    return errors


_CROSS_FIELD: dict[DocumentKind, Any] = {
    "episode": _episode_cross_field,
    "manifest": _manifest_cross_field,
    "report": _report_cross_field,
}


# --------------------------------------------------------------------------
# Public API
# --------------------------------------------------------------------------


def validate(document: Any, kind: DocumentKind | None = None) -> list[Error]:
    """Validate ``document``; ``kind`` is inferred when omitted."""
    if kind is None:
        detected = detect_kind(document)
        if detected is None:
            raise AmbiguousDocumentError(
                "cannot determine document kind from its contents; pass an explicit type"
            )
        kind = detected
    _check_kind(kind)

    errors = _schema_errors(kind, document)
    if isinstance(document, Mapping):
        errors.extend(_CROSS_FIELD[kind](document))
    # One stable ordering across both sources of error, so a human reading the
    # output walks the document top to bottom rather than by error provenance.
    errors.sort(key=lambda err: (err.path, err.code, err.message))
    return errors


def validate_episode(document: Any) -> list[Error]:
    """Validate an episode document. Returns a list of errors (empty == valid)."""
    return validate(document, "episode")


def validate_manifest(document: Any) -> list[Error]:
    """Validate a run-manifest document. Returns a list of errors (empty == valid)."""
    return validate(document, "manifest")


def validate_report(document: Any) -> list[Error]:
    """Validate a zkprof report document. Returns a list of errors (empty == valid)."""
    return validate(document, "report")


def detect_kind(document: Any) -> DocumentKind | None:
    """Infer the document kind from a ``$schema`` discriminator, else from shape."""
    if not isinstance(document, Mapping):
        return None

    ref = document.get("$schema")
    if isinstance(ref, str):
        for kind, filename in _SCHEMA_FILES.items():
            stem = filename.removesuffix(".schema.json")
            if stem in ref or kind in ref:
                return kind

    keys = set(document)
    if {"episode_id", "failure_class"} <= keys:
        return "episode"
    if {"run_id", "pdk", "inputs"} <= keys:
        return "manifest"
    if {"workload_id", "primitives", "target"} <= keys:
        return "report"
    return None


def format_errors(errors: Sequence[Error]) -> str:
    """Render errors one per line, prefixed with a count."""
    if not errors:
        return "ok: no errors"
    lines = [f"{len(errors)} error(s):"]
    lines.extend(f"  - {err}" for err in errors)
    return "\n".join(lines)
