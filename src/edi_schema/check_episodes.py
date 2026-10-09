"""Episode admission control for the Croissant exporter.

The Croissant export turns episode files into a discoverable dataset. A discovery
surface must never index a TODO skeleton as if it were recorded data, so before
an episode enters the export it has to clear ``check_episode``.

Two gates:

* **Schema validity** -- the document must pass :func:`validate_episode`. A file
  that is not a well-formed episode is never data.
* **Not a draft** (strict mode only) -- the document must not carry a
  ``TODO(...)`` marker anywhere, and must not be ``provenance:
  "synthetic-fixture"``. The schema itself says synthetic-fixture is "validator
  food, NOT data", and the example episodes fill every judgment field with
  ``TODO(expert): ...`` strings to signal "unfinished". Those are skeletons, and
  indexing them would advertise an empty corpus.

The default for the exporter is strict mode: drafts are excluded silently
(counted, reported on stderr, never emitted). ``--include-drafts`` opts out of
the second gate so a human can preview what the export *would* contain.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from .validate import Error, validate_episode

__all__ = [
    "DRAFT_MARKER",
    "CheckResult",
    "check_episode",
    "check_episodes",
    "iter_episode_files",
]

# Matches "TODO(expert):", "TODO(maintainer)", "TODO(any-name)" -- the convention the
# schema examples use to mark an unfinished field. A negative lookbehind keeps it
# from matching inside a longer token like "NOTTODO(thing)", so a word that
# merely contains "TODO" is not mistaken for a draft marker.
DRAFT_MARKER = re.compile(r"(?<![A-Za-z])TODO\([^)]*\)")

# provenance values that are explicitly not data, by the schema's own contract.
_NON_DATA_PROVENANCE = frozenset({"synthetic-fixture"})


@dataclass(frozen=True)
class CheckResult:
    """The verdict on one episode document."""

    path: str
    included: bool
    errors: tuple[Error, ...] = ()
    draft_reasons: tuple[str, ...] = ()

    @property
    def valid(self) -> bool:
        return not self.errors

    @property
    def excluded(self) -> bool:
        """Schema-valid but held out by strict mode (a draft skeleton)."""
        return self.valid and not self.included


def _find_draft_markers(document: Any) -> list[str]:
    """Recursively collect every ``TODO(...)`` marker string in ``document``."""
    found: list[str] = []

    def walk(node: Any) -> None:
        if isinstance(node, str):
            for match in DRAFT_MARKER.findall(node):
                found.append(match)
        elif isinstance(node, Mapping):
            for value in node.values():
                walk(value)
        elif isinstance(node, Sequence) and not isinstance(node, (str, bytes)):
            for item in node:
                walk(item)

    walk(document)
    return found


def check_episode(
    path: str,
    document: Any,
    strict: bool = True,
) -> CheckResult:
    """Decide whether one episode document belongs in the export.

    ``strict=True`` (the exporter default) excludes drafts: documents carrying a
    ``TODO(...)`` marker or ``provenance: "synthetic-fixture"`` are returned with
    ``included=False`` even when they are schema-valid. ``strict=False`` admits
    any schema-valid document regardless of draft markers.
    """
    errors = tuple(validate_episode(document))
    if errors:
        return CheckResult(path=path, included=False, errors=errors)

    if not strict:
        return CheckResult(path=path, included=True)

    reasons: list[str] = []
    if isinstance(document, Mapping):
        provenance = document.get("provenance")
        if provenance in _NON_DATA_PROVENANCE:
            reasons.append(f"provenance is {provenance!r}, which the schema marks as not data")
        markers = _find_draft_markers(document)
        if markers:
            # De-duplicate while preserving order so the message is short.
            seen: dict[str, None] = {}
            for marker in markers:
                seen.setdefault(marker)
            reasons.append("contains draft marker(s): " + ", ".join(f"{m!r}" for m in seen))

    if reasons:
        return CheckResult(path=path, included=False, draft_reasons=tuple(reasons))
    return CheckResult(path=path, included=True)


def iter_episode_files(directory: str) -> list[tuple[str, Any]]:
    """Load every ``*.json`` under ``directory`` as a decoded document.

    Files that are not valid JSON are skipped (and reported by the caller via
    :func:`check_episodes`, which gets the raw load errors). This returns only
    the documents that parsed, paired with their path, so callers can validate
    the unparseable ones separately.
    """
    import json
    from pathlib import Path

    loaded: list[tuple[str, Any]] = []
    for path in sorted(Path(directory).rglob("*.json")):
        if not path.is_file():
            continue
        try:
            loaded.append((str(path), json.loads(path.read_text(encoding="utf-8"))))
        except (OSError, json.JSONDecodeError):
            # Surfaced by the caller, not silently dropped.
            continue
    return loaded


def check_episodes(
    directory: str,
    strict: bool = True,
) -> tuple[list[CheckResult], list[tuple[str, str]]]:
    """Check every episode JSON under ``directory``.

    Returns ``(results, unreadable)`` where ``results`` is one
    :class:`CheckResult` per parsed file and ``unreadable`` is a list of
    ``(path, reason)`` for files that could not be read or parsed.
    """
    import json
    from pathlib import Path

    results: list[CheckResult] = []
    unreadable: list[tuple[str, str]] = []

    for path in sorted(Path(directory).rglob("*.json")):
        if not path.is_file():
            continue
        try:
            document = json.loads(path.read_text(encoding="utf-8"))
        except OSError as exc:
            unreadable.append((str(path), f"cannot read: {exc.strerror}"))
            continue
        except json.JSONDecodeError as exc:
            unreadable.append((str(path), f"invalid JSON: {exc}"))
            continue
        results.append(check_episode(str(path), document, strict=strict))

    return results, unreadable
