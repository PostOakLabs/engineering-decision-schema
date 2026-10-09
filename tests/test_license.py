"""License conformance (R14, LIC-1).

The data corpus is CC BY 4.0; the code is Apache-2.0 (licensing decision of 2026-09-02).
The `edi-croissant` exporter writes a machine-readable dataset `license` and the
repo carries a NOTICE recording the code/data split. This test pins both, so a
future re-license or a lost NOTICE is a red.

Apache-2.0 §4(d) requires reproducing upstream NOTICE contents if one exists;
this repo has no vendored third-party component, so the NOTICE records the
code/data split and the (MIT-style) jsonschema runtime dependency.
"""

from __future__ import annotations

from pathlib import Path

from edi_schema.croissant import ExportOptions

REPO_ROOT = Path(__file__).resolve().parent.parent


def test_exported_dataset_license_is_cc_by_40_by_default() -> None:
    """The exporter's machine-readable dataset license defaults to CC BY 4.0
    (the licensing decision for the data corpus), distinct from the Apache-2.0 code."""

    options = ExportOptions()
    assert options.license == "CC-BY-4.0", (
        "the dataset license must default to CC-BY-4.0 per the licensing decision"
    )


def test_build_croissant_carries_the_cc_by_40_license(tmp_path: Path) -> None:
    import json

    from edi_schema import validate_episode
    from edi_schema.croissant import build_croissant

    episode = {
        "$schema": "https://postoaklabs.github.io/engineering-decision-schema/episode.schema.json",
        "episode_id": "EP-LIC-001",
        "provenance": "retrospective",
        "design": {"name": "example", "pdk": "28nm"},
        "prior_state": {"stage": "post-cts", "metrics": {"wns_ns": "-0.4"}},
        "observation": {
            "metric": "wns_ns",
            "value": "-0.4",
            "target": "0",
            "severity": "degrading",
        },
        "hypothesis": "h",
        "candidates_considered": [
            {"intervention": "a", "rejected_because": "cost"},
            {"intervention": "b", "rejected_because": None},
        ],
        "chosen_intervention": {"parameter": "p", "before": "1", "after": "2"},
        "post_state": {"stage": "post-route", "metrics": {"wns_ns": "-0.1"}},
        "expert_assessment": "acceptable",
        "rationale": "r",
        "confidence": 0.8,
        "failure_class": "FAIL_TIMING",
    }
    assert validate_episode(episode) == []
    (tmp_path / "ep.json").write_text(json.dumps(episode), encoding="utf-8")
    document, _ = build_croissant(str(tmp_path), ExportOptions())
    assert document["license"] == "CC-BY-4.0", document["license"]


def test_notice_exists_and_states_the_split() -> None:
    notice = REPO_ROOT / "NOTICE"
    assert notice.is_file(), "NOTICE is missing (Apache-2.0 §4 / R14)"
    text = notice.read_text(encoding="utf-8")
    assert "Apache-2.0" in text
    assert "CC BY 4.0" in text or "CC-BY-4.0" in text
