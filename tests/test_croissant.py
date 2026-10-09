"""Tests for edi_schema.croissant Croissant export."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from edi_schema.croissant import (
    CROISSANT_CONFORMS_URI,
    CROISSANT_SPEC_URL,
    CROISSANT_VERSION,
    PROV_MAPPING,
    ExportOptions,
    ProvenanceMappingError,
    build_croissant,
    croissant_field,
    provenance_to_prov,
)

pytestmark = pytest.mark.usefixtures("episode", "reproduced")


def _write_episodes(tmp_path: Path, episode: dict, reproduced: dict) -> Path:
    """Write one clean episode, one draft (TODO markers), one synthetic fixture."""
    clean = json.loads(json.dumps(episode).replace("TODO(expert): ", ""))
    # Give the clean one a concrete, non-draft provenance so it is real data.
    clean["provenance"] = "retrospective"
    clean["failure_class"] = "FAIL_TIMING"
    (tmp_path / "clean.json").write_text(json.dumps(clean))
    (tmp_path / "draft.json").write_text(json.dumps(episode))  # full of TODO(expert)
    (tmp_path / "fixture.json").write_text(json.dumps(reproduced))  # synthetic-fixture
    return tmp_path


def test_export_excludes_drafts_by_default(tmp_path: Path, episode: dict, reproduced: dict) -> None:
    _write_episodes(tmp_path, episode, reproduced)
    document, summary = build_croissant(str(tmp_path), ExportOptions())
    assert summary.included == 1
    assert summary.excluded_drafts == 2
    assert summary.schema_invalid == 0
    rows = document["recordSet"][0]["data"]["includes"]
    assert len(rows) == 1
    assert rows[0]["episode_id"] == "EXAMPLE-EP-RETROSPECTIVE-001"


def test_export_include_drafts_admits_everything(
    tmp_path: Path, episode: dict, reproduced: dict
) -> None:
    _write_episodes(tmp_path, episode, reproduced)
    document, summary = build_croissant(str(tmp_path), ExportOptions(include_drafts=True))
    assert summary.included == 3
    assert summary.excluded_drafts == 0
    rows = document["recordSet"][0]["data"]["includes"]
    assert len(rows) == 3


def test_dataset_has_croissant_structure() -> None:
    document, _ = build_croissant("/nonexistent-empty", ExportOptions())
    assert document["@type"] == "Dataset"
    assert document["version"] == CROISSANT_VERSION
    assert document["@context"]["cr"] == "http://mlcommons.org/croissant/"
    # Croissant 1.1 declares the versioned spec URI via dct:conformsTo, and adds
    # the W3C PROV + EDI external-vocabulary namespaces for the provenance
    # mapping.
    assert document["conformsTo"] == CROISSANT_CONFORMS_URI
    assert document["@context"]["prov"] == "http://www.w3.org/ns/prov#"
    assert (
        document["@context"]["edi"] == "https://postoaklabs.github.io/engineering-decision-schema/"
    )
    # An empty corpus still produces a well-formed (if empty) dataset.
    assert document["recordSet"][0]["data"]["includes"] == []


def test_record_set_has_prov_annotation() -> None:
    document, _ = build_croissant("/nonexistent-empty", ExportOptions())
    annotation = document["recordSet"][0]["annotation"]
    assert annotation and annotation[0]["equivalentProperty"] == "prov:derivation"
    subfields = {s["name"]: s["value"]["term"] for s in annotation[0]["subField"]}
    assert subfields == {
        "retrospective": "prov:wasDerivedFrom",
        "reproduced": "prov:wasGeneratedBy",
        "synthetic-fixture": "edi:non_evidential",
    }


def test_record_set_has_all_mapped_fields(tmp_path: Path, episode: dict, reproduced: dict) -> None:
    _write_episodes(tmp_path, episode, reproduced)
    document, _ = build_croissant(str(tmp_path), ExportOptions())
    fields = document["recordSet"][0]["field"]
    names = {f["name"] for f in fields}
    # A representative subset of the mapped episode fields.
    for expected in {
        "episode_id",
        "provenance",
        "failure_class",
        "observation_metric",
        "hypothesis",
        "confidence",
        "chosen_parameter",
    }:
        assert expected in names, f"field {expected} missing from RecordSet"
    # Every field is a cr:Field with a source JSONPath.
    for f in fields:
        assert f["@type"] == "cr:Field"
        assert f["source"]["@type"] == "cr:JsonPath"
        assert f["source"]["jsonPath"].startswith("$.")


def test_enumerations_derived_from_admitted_rows(
    tmp_path: Path, episode: dict, reproduced: dict
) -> None:
    _write_episodes(tmp_path, episode, reproduced)
    document, _ = build_croissant(str(tmp_path), ExportOptions())
    enums = {
        e["name"]: {t["name"] for t in e["terms"]} for e in document["recordSet"][0]["enumeration"]
    }
    # Only the clean (admitted) episode contributes; provenance=retrospective.
    assert enums["provenance"] == {"retrospective"}
    assert enums["failure_class"] == {"FAIL_TIMING"}


def test_croissant_field_helper_renders_source(tmp_path: Path) -> None:
    # Indirectly exercised via build_croissant; assert the shape directly too.
    from edi_schema.croissant import _RECORD_FIELDS

    field_def = croissant_field(_RECORD_FIELDS[0])
    assert field_def["@type"] == "cr:Field"
    assert field_def["dataType"] == _RECORD_FIELDS[0].data_type


def test_empty_corpus_enumerations_are_empty_lists(
    tmp_path: Path, episode: dict, reproduced: dict
) -> None:
    # Write only drafts; none admitted -> empty enumerations.
    (tmp_path / "draft.json").write_text(json.dumps(episode))
    (tmp_path / "fixture.json").write_text(json.dumps(reproduced))
    document, summary = build_croissant(str(tmp_path), ExportOptions())
    assert summary.included == 0
    assert document["recordSet"][0]["enumeration"] == []


def test_numeric_fields_keep_numeric_type(tmp_path: Path, episode: dict, reproduced: dict) -> None:
    clean = json.loads(json.dumps(episode).replace("TODO(expert): ", ""))
    clean["provenance"] = "retrospective"
    clean["confidence"] = 0.8
    (tmp_path / "clean.json").write_text(json.dumps(clean))
    document, _ = build_croissant(str(tmp_path), ExportOptions())
    rows = document["recordSet"][0]["data"]["includes"]
    assert rows[0]["confidence"] == 0.8  # not the string "0.8"


def test_spec_url_and_version_are_pinned() -> None:
    assert CROISSANT_VERSION == "1.1"
    assert "mlcommons" in CROISSANT_SPEC_URL
    assert CROISSANT_CONFORMS_URI == "http://mlcommons.org/croissant/1.1"


def test_distribution_is_flat_fileobject_with_rows_checksum(
    tmp_path: Path, episode: dict, reproduced: dict
) -> None:
    # The official mlcroissant validator requires distribution nodes to be
    # FileObject/FileSet with contentUrl + encodingFormat directly on the
    # node (no `data` wrapper), plus a content hash. FIX-2.
    _write_episodes(tmp_path, episode, reproduced)
    document, _ = build_croissant(str(tmp_path), ExportOptions())
    (dist,) = document["distribution"]
    assert dist["@type"] == "https://schema.org/FileObject"
    assert "data" not in dist
    assert dist["encodingFormat"] == "application/json"
    assert dist["contentUrl"].endswith("/tree/main/episodes")
    rows = document["recordSet"][0]["data"]["includes"]
    expected = hashlib.sha256(
        json.dumps(rows, separators=(",", ":"), sort_keys=True, ensure_ascii=False).encode("utf-8")
    ).hexdigest()
    assert dist["sha256"] == expected
    # Deterministic: rebuilding over the same corpus yields the same digest.
    rebuilt, _ = build_croissant(str(tmp_path), ExportOptions())
    assert rebuilt["distribution"][0]["sha256"] == expected


# --- W1.3 PROV-O mapping tests: one mapping check per provenance value, plus
# one mutation test per mapping, where a wrong provenance term must fail with a
# distinct error code (house style). ---


def test_prov_mapping_retrospective() -> None:
    assert provenance_to_prov("retrospective") == "prov:wasDerivedFrom"


def test_prov_mapping_reproduced() -> None:
    assert provenance_to_prov("reproduced") == "prov:wasGeneratedBy"


def test_prov_mapping_synthetic_fixture_is_non_evidential() -> None:
    assert provenance_to_prov("synthetic-fixture") == "edi:non_evidential"


def test_prov_mapping_covers_exactly_the_enum() -> None:
    # The mapping must cover exactly the three provenance enum values, no more,
    # so a mutation cannot silently add or drop a mapping.
    assert set(PROV_MAPPING) == {"retrospective", "reproduced", "synthetic-fixture"}


@pytest.mark.parametrize(
    "mutated,expected_code",
    [
        ("derived", ProvenanceMappingError.code),
        ("generated-by", ProvenanceMappingError.code),
        ("non-evidential", ProvenanceMappingError.code),
        ("", ProvenanceMappingError.code),
    ],
)
def test_prov_mapping_mutation_fails_with_distinct_code(mutated: str, expected_code: str) -> None:
    # A wrong/mutated provenance term must fail with the distinct
    # E_PROV_UNMAPPED_PROVENANCE code, never silently map to a plausible PROV term.
    with pytest.raises(ProvenanceMappingError) as exc:
        provenance_to_prov(mutated)
    assert exc.value.code == expected_code


def test_prov_mapping_error_code_is_distinct() -> None:
    # Distinct from the schema-validation error codes, so a graded run can tell
    # this failure apart from a schema error.
    assert ProvenanceMappingError.code == "E_PROV_UNMAPPED_PROVENANCE"
    assert ProvenanceMappingError.code != "E_SCHEMA_INVALID"
