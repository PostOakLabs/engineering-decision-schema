"""edi_schema -- load and validate Engineering Decision Intelligence documents.

Three document kinds, one validation discipline:

>>> from edi_schema import validate_episode
>>> validate_episode({}) != []          # missing everything
True

Nothing in this package fabricates data. Fixtures that exist only to exercise
the validator are labelled ``"provenance": "synthetic-fixture"`` and are not
measurements.
"""

from __future__ import annotations

from edi_schema.check_episodes import CheckResult, check_episode, check_episodes
from edi_schema.croissant import (
    CROISSANT_SPEC_URL,
    CROISSANT_VERSION,
    ExportOptions,
    build_croissant,
)
from edi_schema.validate import (
    KINDS,
    SCHEMA_DIR,
    SHARE_TOLERANCE,
    AmbiguousDocumentError,
    DocumentKind,
    Error,
    detect_kind,
    format_errors,
    load_schema,
    schema_path,
    validate,
    validate_episode,
    validate_manifest,
    validate_report,
)

# Aligned with the release tag (v0.5.0: schema $id values moved to the
# engineering-decision-schema address); hardcoded stamp, not derived — bump by hand.
__version__ = "0.5.0"

__all__ = [
    "CROISSANT_SPEC_URL",
    "CROISSANT_VERSION",
    "CheckResult",
    "ExportOptions",
    "KINDS",
    "SCHEMA_DIR",
    "SHARE_TOLERANCE",
    "AmbiguousDocumentError",
    "DocumentKind",
    "Error",
    "__version__",
    "build_croissant",
    "check_episode",
    "check_episodes",
    "detect_kind",
    "format_errors",
    "load_schema",
    "schema_path",
    "validate",
    "validate_episode",
    "validate_manifest",
    "validate_report",
]
