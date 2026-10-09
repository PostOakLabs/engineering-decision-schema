"""Episode validation: JSON Schema rules and the cross-field rules it cannot express."""

from __future__ import annotations

import pytest

from conftest import assert_valid, codes, first_message
from edi_schema import validate_episode


def test_retrospective_example_is_valid(episode: dict) -> None:
    assert validate_episode(episode) == []


def test_retrospective_needs_no_environment(episode: dict) -> None:
    episode.pop("environment", None)
    assert validate_episode(episode) == []


def test_missing_required_field_is_reported(episode: dict) -> None:
    del episode["rationale"]
    errors = validate_episode(episode)
    assert errors
    assert "rationale" in first_message(errors)


def test_unknown_top_level_field_is_rejected(episode: dict) -> None:
    """The schema is closed: a typo'd field is an error, not a silent addition."""
    episode["confidance"] = 0.9
    assert "schema:additionalProperties" in codes(validate_episode(episode))


def test_zero_chosen_candidates_is_rejected(episode: dict) -> None:
    for candidate in episode["candidates_considered"]:
        candidate["rejected_because"] = "FIXTURE: rejected for a test reason"
    errors = validate_episode(episode)
    assert "E_CANDIDATES_NO_CHOSEN" in codes(errors)


def test_two_chosen_candidates_is_rejected(episode: dict) -> None:
    for candidate in episode["candidates_considered"]:
        candidate["rejected_because"] = None
    errors = validate_episode(episode)
    assert "E_CANDIDATES_MULTIPLE_CHOSEN" in codes(errors)
    message = next(err.message for err in errors if err.code == "E_CANDIDATES_MULTIPLE_CHOSEN")
    assert "[0]" in message and "[1]" in message


def test_candidates_must_not_be_empty(episode: dict) -> None:
    episode["candidates_considered"] = []
    assert "schema:minItems" in codes(validate_episode(episode))


def test_reproduced_requires_environment(reproduced: dict) -> None:
    reproduced["provenance"] = "reproduced"
    del reproduced["environment"]
    assert "E_PROVENANCE_REPRODUCED_REQUIRES_ENVIRONMENT" in codes(validate_episode(reproduced))


def test_reproduced_requires_pinned_commits(reproduced: dict) -> None:
    reproduced["provenance"] = "reproduced"
    reproduced["design"].pop("rtl_commit")
    reproduced["design"].pop("pdk_commit")
    found = codes(validate_episode(reproduced))
    assert "E_PROVENANCE_REPRODUCED_REQUIRES_RTL_COMMIT" in found
    assert "E_PROVENANCE_REPRODUCED_REQUIRES_PDK_COMMIT" in found


def test_reproduced_with_environment_and_commits_is_valid(reproduced: dict) -> None:
    reproduced["provenance"] = "reproduced"
    assert_valid("episode", reproduced)


@pytest.mark.parametrize("bad", [1.5, -0.1])
def test_confidence_is_bounded(episode: dict, bad: float) -> None:
    episode["confidence"] = bad
    assert validate_episode(episode)


@pytest.mark.parametrize("value", [0.0, 0.5, 1.0])
def test_confidence_boundary_values_are_accepted(episode: dict, value: float) -> None:
    episode["confidence"] = value
    assert validate_episode(episode) == []


def test_failure_class_is_an_enum(episode: dict) -> None:
    episode["failure_class"] = "FAIL_MADE_UP"
    assert "schema:enum" in codes(validate_episode(episode))


@pytest.mark.parametrize(
    "failure_class",
    [
        "FAIL_CONGESTION",
        "FAIL_TIMING",
        "FAIL_IR_DROP",
        "FAIL_ANTENNA",
        "FAIL_DRC",
        "FAIL_LVS",
        "FAIL_ROUTER",
        "FAIL_CTS",
        "FAIL_MEMORY",
        "FAIL_FLOW",
        "SDC_BUDGET",
    ],
)
def test_every_failure_class_is_accepted(episode: dict, failure_class: str) -> None:
    episode["failure_class"] = failure_class
    assert validate_episode(episode) == []


def test_metrics_values_are_scalars_only(episode: dict) -> None:
    episode["prior_state"]["metrics"]["wns_ns"] = {"nested": True}
    assert "schema:type" in codes(validate_episode(episode))


def test_metrics_accept_numbers_and_strings(episode: dict) -> None:
    episode["prior_state"]["metrics"]["wirelength_um"] = 1234.5
    episode["post_state"]["metrics"]["wirelength_um"] = "TODO(expert): value after"
    assert validate_episode(episode) == []


def test_state_requires_stage_and_metrics(episode: dict) -> None:
    del episode["prior_state"]["stage"]
    assert "schema:required" in codes(validate_episode(episode))


# --- R9: schema_version + the ONE sanctioned x_ extension slot ---


def test_schema_version_is_optional_and_semver(episode: dict) -> None:
    # Absent -> still valid (additive; a record from before the field validates).
    assert validate_episode(episode) == []
    episode["schema_version"] = "0.2.0"
    assert validate_episode(episode) == []


def test_schema_version_rejects_non_semver(episode: dict) -> None:
    episode["schema_version"] = "0.2"
    assert "schema:pattern" in codes(validate_episode(episode))


def test_x_extension_slot_accepts_arbitrary_keys(episode: dict) -> None:
    # The ONE sanctioned extension point: capture-only metadata lives here.
    episode["x_extension"] = {
        "x_capture": {
            "instrument": "episode-questionnaire",
            "self_reported": True,
            "captured_at": "2026-09-01T00:00:00Z",
        },
        "x_scale_bucket": "medium",
    }
    assert validate_episode(episode) == []


def test_x_prefixed_field_at_root_is_still_rejected(episode: dict) -> None:
    # The slot is scoped: a bare x_ field at the top level is NOT a sanctioned
    # extension and is rejected by the closed schema (this is the QST-1 fix).
    episode["x_capture"] = {"instrument": "episode-questionnaire"}
    assert "schema:additionalProperties" in codes(validate_episode(episode))


def test_x_extension_must_be_an_object(episode: dict) -> None:
    episode["x_extension"] = "not-an-object"
    assert "schema:type" in codes(validate_episode(episode))
