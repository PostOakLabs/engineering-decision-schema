"""Acceptance: each mutation must fail, and each must fail *differently*.

A validator that reports "invalid" for every problem is useless to someone
filling in an episode by hand. This test pins the three mutations named in the
build spec -- a missing field, two chosen candidates, and primitive shares that
sum to 1.2 -- and asserts they are distinguishable from one another.
"""

from __future__ import annotations

import copy
from itertools import combinations
from typing import Any

import pytest

from conftest import REPORT_EXAMPLE, REPRODUCED_EXAMPLE, RETROSPECTIVE_EXAMPLE, load_example
from edi_schema import validate_episode, validate_report


def _missing_field_mutation() -> tuple[str, list[Any]]:
    document = load_example(RETROSPECTIVE_EXAMPLE)
    del document["rationale"]
    return "missing field (rationale)", validate_episode(document)


def _two_null_rejections_mutation() -> tuple[str, list[Any]]:
    document = load_example(REPRODUCED_EXAMPLE)
    for candidate in document["candidates_considered"]:
        candidate["rejected_because"] = None
    return "two null rejections", validate_episode(document)


def _shares_sum_1_2_mutation() -> tuple[str, list[Any]]:
    document = load_example(REPORT_EXAMPLE)
    document["primitives"] = [
        {"name": "msm", "ms": 60.0, "share": 0.6},
        {"name": "ntt_fft", "ms": 60.0, "share": 0.6},
    ]
    return "primitive shares sum to 1.2", validate_report(document)


@pytest.fixture
def mutations() -> list[tuple[str, list[Any]]]:
    return [
        _missing_field_mutation(),
        _two_null_rejections_mutation(),
        _shares_sum_1_2_mutation(),
    ]


def test_every_mutation_fails_validation(mutations: list[tuple[str, list[Any]]]) -> None:
    for label, errors in mutations:
        assert errors, f"mutation {label!r} should have failed validation but passed"


def test_each_mutation_produces_a_distinct_message(mutations: list[tuple[str, list[Any]]]) -> None:
    messages = [errors[0].message for _, errors in mutations]
    for (label_a, message_a), (label_b, message_b) in combinations(
        list(zip([m[0] for m in mutations], messages, strict=True)), 2
    ):
        assert message_a != message_b, (
            f"mutations {label_a!r} and {label_b!r} produce the same message: {message_a!r}"
        )


def test_each_mutation_produces_a_distinct_code(mutations: list[tuple[str, list[Any]]]) -> None:
    first_codes = [errors[0].code for _, errors in mutations]
    assert len(set(first_codes)) == len(first_codes), f"mutations share error codes: {first_codes}"


def test_messages_name_the_offending_field(mutations: list[tuple[str, list[Any]]]) -> None:
    expected_substrings = ["rationale", "candidates", "primitives"]
    for (label, errors), expected in zip(mutations, expected_substrings, strict=True):
        assert expected in errors[0].message, (
            f"mutation {label!r} message does not name {expected!r}: {errors[0].message!r}"
        )


def test_unmutated_examples_are_the_baseline() -> None:
    """Guard the guard: if the examples break, the mutations above prove nothing."""
    for name, validator in (
        (RETROSPECTIVE_EXAMPLE, validate_episode),
        (REPRODUCED_EXAMPLE, validate_episode),
        (REPORT_EXAMPLE, validate_report),
    ):
        document = copy.deepcopy(load_example(name))
        assert validator(document) == [], f"baseline example {name} no longer validates"
