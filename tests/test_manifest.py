"""Run-manifest validation: hashes, timestamps, and required provenance fields."""

from __future__ import annotations

import pytest

from conftest import assert_valid, codes
from edi_schema import validate_manifest


def test_valid_manifest_passes() -> None:
    from conftest import make_manifest

    assert validate_manifest(make_manifest()) == []


def test_sdc_hash_is_optional() -> None:
    from conftest import make_manifest

    manifest = make_manifest()
    del manifest["inputs"]["sdc_hash"]
    assert validate_manifest(manifest) == []


def test_nix_flake_lock_hash_is_optional() -> None:
    from conftest import make_manifest

    manifest = make_manifest()
    del manifest["environment"]["nix_flake_lock_hash"]
    assert validate_manifest(manifest) == []


@pytest.mark.parametrize(
    "bad_hash",
    ["", "not-a-hash", "ABCDEF" * 10 + "ABCD", "a" * 63, "a" * 65],
)
def test_hashes_must_be_lowercase_hex_sha256(bad_hash: str) -> None:
    from conftest import make_manifest

    manifest = make_manifest()
    manifest["inputs"]["config_hash"] = bad_hash
    assert "schema:pattern" in codes(validate_manifest(manifest))


def test_64_char_uppercase_hex_is_rejected() -> None:
    """sha256 digests are lowercase by convention; be strict so hashes compare equal."""
    from conftest import make_manifest

    manifest = make_manifest()
    manifest["inputs"]["config_hash"] = "A" * 64
    assert "schema:pattern" in codes(validate_manifest(manifest))


@pytest.mark.parametrize(
    "started_at",
    ["2026-08-28T11:42:18+00:00", "2026-08-28T11:42:18Z", "2026-08-28T11:42:18-04:00"],
)
def test_iso8601_timestamps_are_accepted(started_at: str) -> None:
    from conftest import make_manifest

    manifest = make_manifest(started_at=started_at)
    assert validate_manifest(manifest) == []


@pytest.mark.parametrize("started_at", ["28/08/2026", "yesterday", "", "2026-13-45T99:99:99Z"])
def test_non_iso8601_timestamps_are_rejected(started_at: str) -> None:
    from conftest import make_manifest

    manifest = make_manifest(started_at=started_at)
    assert "E_STARTED_AT_NOT_ISO8601" in codes(validate_manifest(manifest))


@pytest.mark.parametrize("started_at", ["2026-08-28T11:42:18", "2026-08-28 11:42:18"])
def test_timezone_naive_timestamp_is_rejected(started_at: str) -> None:
    """Two machines in different zones must not produce text that cannot be ordered."""
    from conftest import make_manifest

    manifest = make_manifest(started_at=started_at)
    assert "E_STARTED_AT_NO_TIMEZONE" in codes(validate_manifest(manifest))


def test_missing_top_level_fields_are_reported() -> None:
    from conftest import make_manifest

    for field in ("design", "environment", "pdk", "inputs", "run_id", "started_at", "host"):
        manifest = make_manifest()
        del manifest[field]
        assert codes(validate_manifest(manifest)), f"removing {field} should be an error"


def test_manifest_kind_detection() -> None:
    from conftest import make_manifest
    from edi_schema import detect_kind

    assert_valid("manifest", make_manifest())
    assert detect_kind(make_manifest()) == "manifest"
