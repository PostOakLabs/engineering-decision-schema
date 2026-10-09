"""Enum-derivation gate (EDI-10): the enum copies must not drift from the schema.

The episode schema closes over four enums (`provenance`, `severity`,
`expert_assessment`, `failure_class`). Those values are hand-repeated in the
questionnaire page's `<option>` pickers and in `test_croissant.py`'s PROV
mapping. A fourth PROVENANCE value or a renamed enum member added to the schema
would leave those copies behind. This test asserts each copy still matches the
schema, so the drift is a red rather than a silent divergence.
"""

from __future__ import annotations

import re
from pathlib import Path

from edi_schema import load_schema

REPO_ROOT = Path(__file__).resolve().parent.parent
PAGE = REPO_ROOT / "web" / "questionnaire" / "index.html"


def _schema_enums() -> dict[str, list[str]]:
    props = load_schema("episode")["properties"]
    enums: dict[str, list[str]] = {}
    for name in ("provenance", "expert_assessment", "failure_class"):
        enums[name] = list(props[name]["enum"])
    enums["severity"] = list(props["observation"]["properties"]["severity"]["enum"])
    return enums


def _html_options() -> dict[str, list[str]]:
    """Read the picker options the questionnaire renders, keyed by field.

    The page lays each `<select>` out as: a `value=""` placeholder option then
    the enum members. We find the label/select pairs by the known select ids.
    """
    text = PAGE.read_text(encoding="utf-8")
    # capture the <select id="X"> ... </select> block and list its <option>s
    result: dict[str, list[str]] = {}
    id_to_enum = {
        "obs-severity": "severity",
        "failure-class": "failure_class",
        "expert-assessment": "expert_assessment",
    }
    if "provenance" in text:
        id_to_enum["provenance"] = "provenance"
    for select_id, enum_name in id_to_enum.items():
        m = re.search(r'<select id="' + re.escape(select_id) + r'">(.*?)</select>', text, re.S)
        if not m:
            continue
        options = re.findall(r"<option[^>]*>([^<]*)</option>", m.group(1))
        values = []
        for opt in options:
            stripped = opt.strip()
            # Skip the placeholder options ("select" / "(none selected)") the
            # page uses as the empty first choice.
            if stripped == "" or stripped in ("select", "(none selected)"):
                continue
            values.append(stripped)
        result[enum_name] = values
    return result


def test_questionnaire_options_match_the_schema_enums() -> None:
    schema = _schema_enums()
    html = _html_options()
    # At least the three enum pickers the page renders must be present.
    for enum_name in ("severity", "expert_assessment", "failure_class"):
        assert enum_name in html, f"questionnaire has no {enum_name} picker to check"
    mismatches = []
    for enum_name, schema_values in schema.items():
        if enum_name not in html:
            continue
        if sorted(html[enum_name]) != sorted(schema_values):
            mismatches.append(
                f"{enum_name}: schema={sorted(schema_values)} page={sorted(html[enum_name])}"
            )
    assert not mismatches, "questionnaire enum pickers drifted from the schema:\n" + "\n".join(
        mismatches
    )


def test_croissant_prov_mapping_keys_match_the_provenance_enum() -> None:
    """The PROV provenance→term mapping in croissant.py must cover exactly the
    provenance enum, so a new provenance value cannot be silently unmapped."""
    from edi_schema.croissant import PROV_MAPPING

    provenance_enum = set(load_schema("episode")["properties"]["provenance"]["enum"])
    mapping_keys = set(PROV_MAPPING)
    missing = sorted(provenance_enum - mapping_keys)
    extra = sorted(mapping_keys - provenance_enum)
    assert not missing and not extra, (
        f"PROV_MAPPING drifted from the schema: missing={missing} extra={extra}"
    )
