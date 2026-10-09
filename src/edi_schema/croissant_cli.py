"""``edi-croissant`` -- emit a Croissant JSON-LD dataset from episode files.

Reads a directory of episode JSON documents, admits the schema-valid, non-draft
ones (see :mod:`edi_schema.check_episodes`), and writes a Croissant JSON-LD
document to stdout or a file.

Exit codes:

0  wrote a Croissant document
1  the directory had no admissible episodes (still wrote an empty dataset to the
   output so callers can detect "empty corpus" from "tool failed")
2  usage/IO problem: unreadable directory, or a write error
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path

from .croissant import CROISSANT_VERSION, ExportOptions, build_croissant

_USAGE_EXIT = 2


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="edi-croissant",
        description="Build a Croissant JSON-LD dataset from edi-schema episode files.",
    )
    parser.add_argument(
        "directory",
        type=Path,
        help="directory of episode *.json files to export",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="write the Croissant document here instead of stdout",
    )
    parser.add_argument(
        "--name",
        default="edi-episodes",
        help="Dataset name (default: edi-episodes)",
    )
    parser.add_argument(
        "--url",
        default="https://github.com/PostOakLabs/engineering-decision-schema",
        help="Dataset @id / canonical URL",
    )
    parser.add_argument(
        "--license",
        default="CC-BY-4.0",
        help=(
            "Dataset license for the episode corpus / fixture data. Default is "
            "CC-BY-4.0 per the licensing decision of 2026-09-02: the data corpus is "
            "CC-BY-4.0 while the code stays Apache-2.0. Set it explicitly to "
            "override."
        ),
    )
    parser.add_argument(
        "--include-drafts",
        action="store_true",
        help="include TODO-marked skeletons and synthetic fixtures (default: exclude them)",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="suppress the per-file admission summary on stderr",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if not args.directory.is_dir():
        print(f"edi-croissant: {args.directory} is not a directory", file=sys.stderr)
        return _USAGE_EXIT

    options = ExportOptions(
        name=args.name,
        url=args.url,
        license=args.license,
        include_drafts=args.include_drafts,
        extra_keywords=(f"croissant-{CROISSANT_VERSION}",),
    )

    try:
        document, summary = build_croissant(str(args.directory), options)
    except OSError as exc:
        print(f"edi-croissant: cannot read {args.directory}: {exc}", file=sys.stderr)
        return _USAGE_EXIT

    text = json.dumps(document, indent=2) + "\n"

    if args.out is None:
        sys.stdout.write(text)
    else:
        try:
            args.out.write_text(text, encoding="utf-8")
        except OSError as exc:
            print(f"edi-croissant: cannot write {args.out}: {exc.strerror}", file=sys.stderr)
            return _USAGE_EXIT

    if not args.quiet:
        print(
            f"edi-croissant: included {summary.included}, "
            f"excluded drafts {summary.excluded_drafts}, "
            f"schema-invalid {summary.schema_invalid}, "
            f"unreadable {summary.unreadable}",
            file=sys.stderr,
        )

    # A corpus with no admissible episodes is a valid (empty) dataset, not a
    # failure. The non-zero exit would make CI treat an empty repo as broken.
    return 0


if __name__ == "__main__":  # pragma: no cover - exercised via console_script
    raise SystemExit(main())
