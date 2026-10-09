"""The schema files themselves are an artifact other repositories consume.

They are validated against the draft 2020-12 meta-schema here so a malformed
schema fails in CI rather than in whichever downstream repo happens to load it.
"""

from __future__ import annotations

import json

import pytest
from jsonschema import Draft202012Validator

from conftest import SCHEMA_DIR
from edi_schema import KINDS, load_schema, schema_path

DRAFT_2020_12 = "https://json-schema.org/draft/2020-12/schema"


def _raw(name: str) -> dict:
    return json.loads((SCHEMA_DIR / name).read_text(encoding="utf-8"))


@pytest.mark.parametrize("kind", KINDS)
def test_schema_file_is_reachable(kind: str) -> None:
    assert schema_path(kind).is_file()


@pytest.mark.parametrize("kind", KINDS)
def test_schema_declares_draft_2020_12(kind: str) -> None:
    assert load_schema(kind)["$schema"] == DRAFT_2020_12


@pytest.mark.parametrize("kind", KINDS)
def test_schema_is_valid_against_the_meta_schema(kind: str) -> None:
    errors = sorted(
        Draft202012Validator(Draft202012Validator.META_SCHEMA).iter_errors(load_schema(kind))
    )
    assert errors == [], "\n".join(str(e) for e in errors)


@pytest.mark.parametrize("kind", KINDS)
def test_schema_has_a_title_and_description(kind: str) -> None:
    schema = load_schema(kind)
    assert schema["title"]
    assert len(schema["description"]) > 40


def test_schema_ids_are_distinct() -> None:
    ids = [load_schema(kind)["$id"] for kind in KINDS]
    assert len(set(ids)) == len(ids)


def test_schema_filenames_are_detectable_from_their_ids() -> None:
    """The CLI infers document kind by substring-matching $schema; keep that working."""
    from edi_schema import detect_kind

    for kind in KINDS:
        document = {"$schema": load_schema(kind)["$id"]}
        assert detect_kind(document) == kind, f"kind {kind} not detectable from its own $id"


def test_episode_schema_couples_reproduced_to_environment() -> None:
    schema = load_schema("episode")
    conditionals = schema["allOf"]
    assert len(conditionals) == 1
    assert conditionals[0]["if"]["properties"]["provenance"]["const"] == "reproduced"
    assert "environment" in conditionals[0]["then"]["required"]


def test_no_schema_file_is_left_untracked() -> None:
    files = sorted(path.name for path in SCHEMA_DIR.glob("*.schema.json"))
    assert files == [
        "episode.schema.json",
        "run-manifest.schema.json",
        "zkprof-report.schema.json",
    ]


def test_raw_file_reads_match_load_schema() -> None:
    assert _raw("episode.schema.json") == load_schema("episode")


def test_episode_schema_has_version_and_one_extension_slot() -> None:
    """R9: a per-record schema_version field and exactly ONE sanctioned
    x_ extension slot. The slot is container-only (additionalProperties: true);
    the rest of the schema stays closed."""
    props = load_schema("episode")["properties"]
    assert "schema_version" in props
    assert props["schema_version"]["pattern"] == r"^[0-9]+\.[0-9]+\.[0-9]+$"
    slot = props["x_extension"]
    assert slot["type"] == "object"
    assert slot["additionalProperties"] is True


def test_extension_slot_is_container_only_at_root() -> None:
    """The sanctioned slot is the sole extension point; a bare x_-prefixed field
    at the top level remains a schema violation (the QST-1 fix mechanism)."""
    schema = load_schema("episode")
    assert schema["additionalProperties"] is False
