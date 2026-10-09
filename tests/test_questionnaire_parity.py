"""Validator parity for the episode questionnaire's JS mirror (questionnaire-1).

The questionnaire page (web/questionnaire/index.html) reimplements the
edi-schema episode cross-field rules in JavaScript. Its Node test
(web/questionnaire/validate.test.mjs) drives the SAME seeded defects through the
JS validator and asserts the same codes this module produces. This test exists so
the two sides cannot drift: the defect vectors here mirror the JS test exactly,
and each must yield the same edi-schema code.

Each defect is the mutation-test discipline: a validator that reports every
problem as "invalid" would be useless, and one that cannot fail is worse. Here
each named mutation must fail with its own, distinct code.
"""

from __future__ import annotations

from typing import Any

from edi_schema import validate_episode


def _valid_doc() -> dict[str, Any]:
    """A schema-shaped retrospective episode that is valid on its own."""
    return {
        "$schema": "https://postoaklabs.github.io/engineering-decision-schema/episode.schema.json",
        "episode_id": "EP-Q-001",
        "provenance": "retrospective",
        "design": {"name": "example block", "pdk": "28nm"},
        "prior_state": {"stage": "post-cts", "metrics": {"wns_ns": "-0.4"}},
        "observation": {
            "metric": "wns_ns",
            "value": "-0.4",
            "target": "0",
            "severity": "degrading",
        },
        "hypothesis": "a constraint is missing",
        "candidates_considered": [
            {"intervention": "upsize a path", "rejected_because": "schedule"},
            {"intervention": "fix the constraint", "rejected_because": None},
        ],
        "chosen_intervention": {"parameter": "set_input_delay", "before": "0.5", "after": "0.8"},
        "post_state": {"stage": "post-route", "metrics": {"wns_ns": "-0.1"}},
        "expert_assessment": "acceptable",
        "rationale": "the missing constraint was the cheap, correct fix",
        "confidence": 0.8,
        "failure_class": "FAIL_TIMING",
    }


def _codes(document: dict[str, Any]) -> list[str]:
    return [error.code for error in validate_episode(document)]


def test_valid_base_is_clean() -> None:
    assert validate_episode(_valid_doc()) == []


def test_missing_field_is_schema_required() -> None:
    doc = _valid_doc()
    del doc["rationale"]
    assert "schema:required" in _codes(doc)


def test_two_chosen_candidates_is_distinct_code() -> None:
    doc = _valid_doc()
    for candidate in doc["candidates_considered"]:
        candidate["rejected_because"] = None
    assert "E_CANDIDATES_MULTIPLE_CHOSEN" in _codes(doc)


def test_no_chosen_candidate_is_distinct_code() -> None:
    doc = _valid_doc()
    for candidate in doc["candidates_considered"]:
        candidate["rejected_because"] = "cost"
    assert "E_CANDIDATES_NO_CHOSEN" in _codes(doc)


def test_invalid_severity_is_schema_enum() -> None:
    doc = _valid_doc()
    doc["observation"]["severity"] = "fatal"
    assert "schema:enum" in _codes(doc)


def test_reproduced_without_environment_is_distinct_code() -> None:
    doc = _valid_doc()
    doc["provenance"] = "reproduced"
    assert "E_PROVENANCE_REPRODUCED_REQUIRES_ENVIRONMENT" in _codes(doc)


def test_the_five_defects_are_distinguishable_from_one_another() -> None:
    # A validator that reports every problem with the same code is useless to
    # someone filling in a record by hand; each named defect maps to its own code.
    docs = {
        "missing field": _missing_field(),
        "two chosen": _two_chosen(),
        "no chosen": _no_chosen(),
        "bad severity": _bad_severity(),
        "reproduced no env": _reproduced_no_env(),
    }
    signatures = {name: sorted(set(_codes(doc)))[0] for name, doc in docs.items()}
    assert len(set(signatures.values())) == len(signatures), (
        f"distinct mutated cases must produce distinct codes, got {signatures}"
    )


# Helpers reused by the distinguishability test.
def _missing_field() -> dict[str, Any]:
    doc = _valid_doc()
    del doc["rationale"]
    return doc


def _two_chosen() -> dict[str, Any]:
    doc = _valid_doc()
    for candidate in doc["candidates_considered"]:
        candidate["rejected_because"] = None
    return doc


def _no_chosen() -> dict[str, Any]:
    doc = _valid_doc()
    for candidate in doc["candidates_considered"]:
        candidate["rejected_because"] = "cost"
    return doc


def _bad_severity() -> dict[str, Any]:
    doc = _valid_doc()
    doc["observation"]["severity"] = "fatal"
    return doc


def _reproduced_no_env() -> dict[str, Any]:
    doc = _valid_doc()
    doc["provenance"] = "reproduced"
    return doc
