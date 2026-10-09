"""The committed examples are the contract. They must always validate.

They are also the place where the no-fabrication rule is enforced mechanically:
an example can be a template (TODO markers) or a synthetic fixture, but it can
never claim ``provenance: reproduced``, because no run produced it.
"""

from __future__ import annotations

import pytest

from conftest import (
    MANIFEST_EXAMPLE,
    REPORT_EXAMPLE,
    REPRODUCED_EXAMPLE,
    RETROSPECTIVE_EXAMPLE,
    load_example,
)
from edi_schema import detect_kind, validate

ALL_EXAMPLES = [RETROSPECTIVE_EXAMPLE, REPRODUCED_EXAMPLE, MANIFEST_EXAMPLE, REPORT_EXAMPLE]


@pytest.mark.parametrize("name", ALL_EXAMPLES)
def test_example_is_valid_json_and_kind_detectable(name: str) -> None:
    document = load_example(name)
    kind = detect_kind(document)
    assert kind is not None, f"{name}: kind not detectable from $schema or shape"


@pytest.mark.parametrize(
    ("name", "expected_kind"),
    [
        (RETROSPECTIVE_EXAMPLE, "episode"),
        (REPRODUCED_EXAMPLE, "episode"),
        (MANIFEST_EXAMPLE, "manifest"),
        (REPORT_EXAMPLE, "report"),
    ],
)
def test_example_validates_against_its_schema(name: str, expected_kind: str) -> None:
    document = load_example(name)
    assert detect_kind(document) == expected_kind
    errors = validate(document, expected_kind)  # type: ignore[arg-type]
    assert errors == [], f"{name} failed validation:\n" + "\n".join(str(e) for e in errors)


def test_examples_never_claim_reproduced_provenance() -> None:
    """A reproduced episode comes from a real run; examples are never that."""
    for name in (RETROSPECTIVE_EXAMPLE, REPRODUCED_EXAMPLE):
        document = load_example(name)
        assert document["provenance"] != "reproduced", (
            f"{name} claims provenance 'reproduced' without a backing run"
        )


def test_report_example_announces_itself_as_a_fixture() -> None:
    document = load_example(REPORT_EXAMPLE)
    assert "fixture" in document["workload_id"] or "not-a-measurement" in document["workload_id"]


def test_report_example_primitive_shares_sum_to_one() -> None:
    document = load_example(REPORT_EXAMPLE)
    total = sum(item["share"] for item in document["primitives"])
    assert total == pytest.approx(1.0, abs=0.02)
