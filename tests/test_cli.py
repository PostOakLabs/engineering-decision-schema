"""End-to-end CLI behaviour, including exit codes.

0 = all valid, 1 = validation failure, 2 = usage/IO problem. Callers in CI and
in the other two repositories depend on 0-vs-nonzero, so these are pinned.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from conftest import EXAMPLES_DIR, REPORT_EXAMPLE, RETROSPECTIVE_EXAMPLE

MODULE = "edi_schema.cli"


def run(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", MODULE, *args],
        capture_output=True,
        text=True,
        check=False,
        encoding="utf-8",
    )


@pytest.mark.parametrize(
    "name", ["episode.retrospective.example.json", "zkprof-report.example.json"]
)
def test_valid_example_exits_zero(name: str) -> None:
    result = run([str(EXAMPLES_DIR / name)])
    assert result.returncode == 0, result.stdout + result.stderr
    assert "ok" in result.stdout


def test_all_examples_together_exit_zero() -> None:
    files = sorted(str(path) for path in EXAMPLES_DIR.glob("*.json"))
    assert files, "no examples found"
    assert run(files).returncode == 0


def test_invalid_document_exits_one(tmp_path: Path) -> None:
    document = json.loads((EXAMPLES_DIR / RETROSPECTIVE_EXAMPLE).read_text(encoding="utf-8"))
    del document["rationale"]
    path = tmp_path / "bad.json"
    path.write_text(json.dumps(document), encoding="utf-8")

    result = run([str(path)])
    assert result.returncode == 1
    assert "rationale" in result.stdout


def test_malformed_json_exits_two(tmp_path: Path) -> None:
    path = tmp_path / "broken.json"
    path.write_text("{not json", encoding="utf-8")

    result = run([str(path)])
    assert result.returncode == 2
    assert "not valid JSON" in result.stderr


def test_undetectable_kind_exits_two(tmp_path: Path) -> None:
    path = tmp_path / "mystery.json"
    path.write_text('{"hello": "world"}', encoding="utf-8")

    result = run([str(path)])
    assert result.returncode == 2
    assert "--type" in result.stderr


def test_missing_file_exits_two(tmp_path: Path) -> None:
    result = run([str(tmp_path / "does-not-exist.json")])
    assert result.returncode == 2
    assert "cannot read" in result.stderr


def test_forced_type_overrides_inference() -> None:
    """An episode forced through the report validator must fail."""
    result = run(["--type", "report", str(EXAMPLES_DIR / RETROSPECTIVE_EXAMPLE)])
    assert result.returncode == 1


def test_shape_fallback_and_forced_type_agree(tmp_path: Path) -> None:
    """Without a $schema discriminator the shape fallback must reach the same verdict."""
    document = json.loads((EXAMPLES_DIR / REPORT_EXAMPLE).read_text(encoding="utf-8"))
    document.pop("$schema")
    path = tmp_path / "schemaless.json"
    path.write_text(json.dumps(document), encoding="utf-8")

    inferred = run([str(path)])
    forced = run(["--type", "report", str(path)])
    assert inferred.returncode == 0, inferred.stdout + inferred.stderr
    assert forced.returncode == 0, forced.stdout + forced.stderr
    assert "[report]" in inferred.stdout


def test_json_error_output(tmp_path: Path) -> None:
    document = json.loads((EXAMPLES_DIR / RETROSPECTIVE_EXAMPLE).read_text(encoding="utf-8"))
    del document["rationale"]
    path = tmp_path / "bad.json"
    path.write_text(json.dumps(document), encoding="utf-8")

    result = run(["--json", str(path)])
    assert result.returncode == 1
    payload = json.loads(result.stdout)
    assert payload[0]["kind"] == "episode"
    assert payload[0]["errors"]
    assert {"code", "path", "message"} <= set(payload[0]["errors"][0])


def test_help_works() -> None:
    result = run(["--help"])
    assert result.returncode == 0
    assert "edi-validate" in result.stdout
