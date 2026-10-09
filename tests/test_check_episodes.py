"""Tests for edi_schema.check_episodes admission control."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from edi_schema.check_episodes import (
    DRAFT_MARKER,
    check_episode,
    check_episodes,
    iter_episode_files,
)

pytestmark = pytest.mark.usefixtures("episode", "reproduced")


def test_valid_episode_without_markers_is_included(episode: dict) -> None:
    # The retrospective example is full of TODO(expert) markers, so strip them to
    # get a clean, admissible document.
    cleaned = json.loads(json.dumps(episode).replace("TODO(expert): ", ""))
    result = check_episode("ep.json", cleaned, strict=True)
    assert result.included
    assert result.valid
    assert not result.excluded


def test_schema_invalid_episode_is_excluded_with_errors(episode: dict) -> None:
    broken = dict(episode)
    del broken["failure_class"]  # required field
    result = check_episode("bad.json", broken, strict=True)
    assert not result.included
    assert not result.valid
    assert result.errors  # carries the validation errors


def test_draft_marker_excluded_in_strict_mode(episode: dict) -> None:
    # The retrospective example literally contains "TODO(expert):" in many fields.
    result = check_episode("draft.json", episode, strict=True)
    assert result.valid  # schema-valid ...
    assert not result.included  # ... but excluded as a draft
    assert result.excluded
    assert any("TODO" in reason for reason in result.draft_reasons)


def test_synthetic_fixture_excluded_in_strict_mode(reproduced: dict) -> None:
    result = check_episode("fixture.json", reproduced, strict=True)
    assert result.valid
    assert not result.included
    assert result.excluded
    assert any("synthetic-fixture" in reason for reason in result.draft_reasons)


def test_include_drafts_override_admits_marked_episode(episode: dict) -> None:
    result = check_episode("draft.json", episode, strict=False)
    assert result.included
    assert result.valid
    assert not result.draft_reasons


def test_include_drafts_override_admits_synthetic_fixture(reproduced: dict) -> None:
    result = check_episode("fixture.json", reproduced, strict=False)
    assert result.included
    assert result.valid


def test_draft_marker_regex_matches_variants() -> None:
    assert DRAFT_MARKER.findall("TODO(expert): x TODO(maintainer) TODO(carol): y")
    assert not DRAFT_MARKER.findall("totodo(nope) and NOTTODO(thing)")


def test_check_episodes_over_directory(tmp_path: Path, episode: dict, reproduced: dict) -> None:
    # One clean episode (stripped), one draft (TODO markers), one synthetic fixture.
    clean = json.loads(json.dumps(episode).replace("TODO(expert): ", ""))
    (tmp_path / "clean.json").write_text(json.dumps(clean))
    (tmp_path / "draft.json").write_text(json.dumps(episode))
    (tmp_path / "fixture.json").write_text(json.dumps(reproduced))
    (tmp_path / "notjson.txt").write_text("hi")

    results, unreadable = check_episodes(str(tmp_path), strict=True)
    assert unreadable == []  # .txt is ignored by rglob("*.json")
    included = [r for r in results if r.included]
    excluded = [r for r in results if r.excluded]
    invalid = [r for r in results if not r.valid]
    assert len(included) == 1
    assert len(excluded) == 2
    assert invalid == []


def test_unreadable_files_reported_separately(tmp_path: Path) -> None:
    bad = tmp_path / "broken.json"
    bad.write_text("{ not valid json")
    results, unreadable = check_episodes(str(tmp_path), strict=True)
    assert results == []
    assert len(unreadable) == 1
    assert "broken.json" in unreadable[0][0]


def test_iter_episode_files_skips_unparseable(tmp_path: Path, episode: dict) -> None:
    (tmp_path / "ok.json").write_text(json.dumps(episode))
    (tmp_path / "bad.json").write_text("{ broken")
    loaded = iter_episode_files(str(tmp_path))
    assert len(loaded) == 1
    assert loaded[0][0].endswith("ok.json")
