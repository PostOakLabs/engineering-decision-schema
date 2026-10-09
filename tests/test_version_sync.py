"""Release hygiene: the package version must not disagree three ways (EDI-15/19).

`edi-schema` is consumed by git tag. Downstream provenance renders
`edi_schema.__version__` into published artifacts, so the three version
sources -- `__version__` in `src/edi_schema/__init__.py`, the `version` in
`pyproject.toml`, and the installed distribution metadata -- must agree. The
tag (`vX.Y.Z`) is cut by the operator at release time; this test pins the two
in-repo sources and the installed metadata together so a future renumber that
leaves one behind is caught in CI rather than shipped as a provenance stamp
that names the wrong version.
"""

from __future__ import annotations

import importlib.metadata
import tomllib
from pathlib import Path

import edi_schema

REPO_ROOT = Path(__file__).resolve().parent.parent


def test_package_version_matches_pyproject() -> None:
    pyproject = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    pyproject_version = pyproject["project"]["version"]
    assert edi_schema.__version__ == pyproject_version, (
        f"src/edi_schema/__init__.py __version__ ({edi_schema.__version__}) != "
        f"pyproject.toml version ({pyproject_version}); bump both together"
    )


def test_installed_metadata_matches_package_version() -> None:
    metadata_version = importlib.metadata.version("edi-schema")
    assert edi_schema.__version__ == metadata_version, (
        f"__version__ ({edi_schema.__version__}) != installed metadata "
        f"({metadata_version}); the installed dist is stale relative to src"
    )
