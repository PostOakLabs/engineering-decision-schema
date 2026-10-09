"""Shared test helpers: example loading, document builders, error inspection."""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

import pytest

from edi_schema import Error, validate

REPO_ROOT = Path(__file__).resolve().parents[1]
EXAMPLES_DIR = REPO_ROOT / "examples"
SCHEMA_DIR = REPO_ROOT / "schemas"

RETROSPECTIVE_EXAMPLE = "episode.retrospective.example.json"
REPRODUCED_EXAMPLE = "episode.reproduced.example.json"
MANIFEST_EXAMPLE = "run-manifest.example.json"
REPORT_EXAMPLE = "zkprof-report.example.json"


def load_example(name: str) -> dict[str, Any]:
    """Read one of the committed example documents."""
    return json.loads((EXAMPLES_DIR / name).read_text(encoding="utf-8"))


def codes(errors: list[Error]) -> set[str]:
    return {err.code for err in errors}


def first_message(errors: list[Error]) -> str:
    assert errors, "expected validation to fail, but it passed"
    return errors[0].message


@pytest.fixture
def episode() -> dict[str, Any]:
    """A fresh, valid retrospective episode. Mutate freely."""
    return copy.deepcopy(load_example(RETROSPECTIVE_EXAMPLE))


@pytest.fixture
def reproduced() -> dict[str, Any]:
    """A fresh, valid reproduced-shaped (synthetic-fixture) episode."""
    return copy.deepcopy(load_example(REPRODUCED_EXAMPLE))


@pytest.fixture
def report() -> dict[str, Any]:
    """A fresh, valid zkprof report fixture."""
    return copy.deepcopy(load_example(REPORT_EXAMPLE))


def make_manifest(**overrides: Any) -> dict[str, Any]:
    """A valid run manifest. Keyword arguments replace whole top-level fields."""
    document: dict[str, Any] = {
        "$schema": "https://postoaklabs.github.io/engineering-decision-schema/run-manifest.schema.json",
        "design": {"name": "ibex", "rtl_commit": "FIXTURE-not-a-real-commit"},
        "environment": {
            "librelane_version": "FIXTURE-not-a-real-version",
            "openroad_version": "FIXTURE-not-a-real-version",
            "yosys_version": "FIXTURE-not-a-real-version",
            "nix_flake_lock_hash": "a" * 64,
        },
        "pdk": {"name": "sky130A", "commit": "FIXTURE-not-a-real-commit"},
        "inputs": {"config_hash": "b" * 64, "sdc_hash": "c" * 64},
        "run_id": "RUN_FIXTURE",
        "started_at": "2026-08-28T11:42:18+00:00",
        "host": {"os": "FIXTURE-not-a-real-platform", "cpu": "FIXTURE-not-a-real-platform"},
    }
    document.update(overrides)
    return document


def assert_valid(kind: str, document: dict[str, Any]) -> None:
    errors = validate(document, kind)  # type: ignore[arg-type]
    assert errors == [], f"expected a valid {kind}, got:\n" + "\n".join(str(e) for e in errors)
