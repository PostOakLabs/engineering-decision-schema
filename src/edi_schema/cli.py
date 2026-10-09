"""``edi-validate`` -- validate one or more JSON documents against edi-schema.

Exit codes:

0  every document is valid
1  at least one document failed validation
2  usage/IO problem: unreadable file, malformed JSON, or an undetectable
   document kind (fix by passing --type)

The document kind is taken from ``--type`` when given, otherwise inferred from
the document's ``$schema`` discriminator, otherwise from its shape.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from edi_schema.validate import (
    KINDS,
    AmbiguousDocumentError,
    DocumentKind,
    detect_kind,
    format_errors,
    validate,
)

_USAGE_EXIT = 2


class _UsageError(Exception):
    """Unreadable file, malformed JSON, or an undetectable document kind."""


def _load(path: Path) -> Any:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        msg = f"edi-validate: cannot read {path}: {exc.strerror}"
        raise _UsageError(msg) from exc
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        msg = f"edi-validate: {path} is not valid JSON: {exc}"
        raise _UsageError(msg) from exc


def _resolve_kind(path: Path, document: Any, forced: str | None) -> DocumentKind:
    if forced:
        return forced  # type: ignore[return-value]
    kind = detect_kind(document)
    if kind is None:
        msg = (
            f"edi-validate: cannot tell what kind of document {path} is; "
            f"pass --type {{{','.join(KINDS)}}}"
        )
        raise _UsageError(msg)
    return kind


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="edi-validate",
        description="Validate JSON documents against the edi-schema schemas.",
    )
    parser.add_argument(
        "files",
        nargs="+",
        type=Path,
        help="JSON files to validate",
    )
    parser.add_argument(
        "--type",
        choices=list(KINDS),
        default=None,
        help="force a document kind instead of inferring it from $schema or shape",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        dest="as_json",
        help="emit errors as JSON instead of text (one object per file)",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    failures: list[dict[str, Any]] = []
    failed_files = 0

    for path in args.files:
        try:
            document = _load(path)
            kind = _resolve_kind(path, document, args.type)
            errors = validate(document, kind)
        except (_UsageError, AmbiguousDocumentError) as exc:
            print(exc, file=sys.stderr)
            print("(usage error: exit 2)", file=sys.stderr)
            return _USAGE_EXIT

        if errors:
            failed_files += 1
            if args.as_json:
                failures.append(
                    {
                        "file": str(path),
                        "kind": kind,
                        "errors": [vars(err) for err in errors],
                    }
                )
            else:
                print(f"{path} [{kind}]")
                print(format_errors(errors))
        elif not args.as_json:
            print(f"{path} [{kind}]: ok")

    if args.as_json:
        print(json.dumps(failures if failures else [], indent=2))

    return 1 if failed_files else 0


if __name__ == "__main__":  # pragma: no cover - exercised via console_script
    raise SystemExit(main())
