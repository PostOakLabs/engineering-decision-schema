"""zkprof report validation, including the primitive-share invariant."""

from __future__ import annotations

import pytest

from conftest import codes, first_message
from edi_schema import SHARE_TOLERANCE, validate_report


def test_report_example_is_valid(report: dict) -> None:
    assert validate_report(report) == []


def test_shares_summing_to_one_are_accepted(report: dict) -> None:
    report["primitives"] = [
        {"name": "msm", "ms": 60.0, "share": 0.6},
        {"name": "ntt_fft", "ms": 40.0, "share": 0.4},
    ]
    assert validate_report(report) == []


@pytest.mark.parametrize("total", [1.2, 0.8, 2.0])
def test_shares_outside_tolerance_are_rejected(report: dict, total: float) -> None:
    report["primitives"] = [
        {"name": "msm", "ms": 10.0, "share": total / 2},
        {"name": "ntt_fft", "ms": 10.0, "share": total / 2},
    ]
    errors = validate_report(report)
    assert "E_SHARE_SUM_PRIMITIVES" in codes(errors)
    message = next(err.message for err in errors if err.code == "E_SHARE_SUM_PRIMITIVES")
    assert f"{total:.4f}" in message


@pytest.mark.parametrize("total", [1.0 + SHARE_TOLERANCE, 1.0 - SHARE_TOLERANCE])
def test_tolerance_boundary_is_inclusive(report: dict, total: float) -> None:
    """A sum exactly on the tolerance edge still passes."""
    half = total / 2
    report["primitives"] = [
        {"name": "msm", "ms": 10.0, "share": half},
        {"name": "ntt_fft", "ms": 10.0, "share": half},
    ]
    assert validate_report(report) == []


def test_just_outside_tolerance_is_rejected(report: dict) -> None:
    half = (1.0 + SHARE_TOLERANCE + 0.001) / 2
    report["primitives"] = [
        {"name": "msm", "ms": 10.0, "share": half},
        {"name": "ntt_fft", "ms": 10.0, "share": half},
    ]
    assert "E_SHARE_SUM_PRIMITIVES" in codes(validate_report(report))


def test_phase_shares_are_deliberately_not_enforced(report: dict) -> None:
    """Phases may nest or overlap, so they need not partition total_ms."""
    report["phases"] = [
        {"name": "outer", "ms": 100.0, "share": 1.0},
        {"name": "inner", "ms": 30.0, "share": 0.3},
    ]
    assert validate_report(report) == []


def test_primitives_must_not_be_empty(report: dict) -> None:
    report["primitives"] = []
    assert "schema:minItems" in codes(validate_report(report))


@pytest.mark.parametrize(
    "name",
    ["msm", "ntt_fft", "hash", "field_arith", "marshalling", "witness_gen", "other"],
)
def test_every_primitive_name_is_accepted(report: dict, name: str) -> None:
    report["primitives"] = [{"name": name, "ms": 100.0, "share": 1.0}]
    assert validate_report(report) == []


def test_unknown_primitive_name_is_rejected(report: dict) -> None:
    report["primitives"] = [{"name": "vibes", "ms": 100.0, "share": 1.0}]
    assert "schema:enum" in codes(validate_report(report))


def test_empty_memory_object_is_allowed(report: dict) -> None:
    """Not measured is expressed by omission, never by a zero."""
    report["memory"] = {}
    assert validate_report(report) == []
    del report["memory"]
    assert "schema:required" in codes(validate_report(report))


def test_report_version_is_semver(report: dict) -> None:
    report["report_version"] = "0.1"
    assert "schema:pattern" in codes(validate_report(report))


def test_iterations_must_be_positive(report: dict) -> None:
    report["iterations"] = 0
    assert validate_report(report)


@pytest.mark.parametrize("source", ["timestamp-query", "wall-clock"])
def test_every_gpu_timing_source_is_accepted(report: dict, source: str) -> None:
    report["gpu_timing_source"] = source
    assert validate_report(report) == []


def test_unknown_gpu_timing_source_is_rejected(report: dict) -> None:
    report["gpu_timing_source"] = "stopwatch"
    assert "schema:enum" in codes(validate_report(report))


def test_gpu_timing_source_is_optional(report: dict) -> None:
    """Absent means the report attributes no time to a GPU at all."""
    report.pop("gpu_timing_source", None)
    assert validate_report(report) == []


def test_gpu_timing_source_must_be_a_string(report: dict) -> None:
    report["gpu_timing_source"] = 1
    assert "schema:type" in codes(validate_report(report))


def test_deployment_context_fields_are_required(report: dict) -> None:
    for field in ("crossOriginIsolated", "timer_resolution_us", "iterations", "threads"):
        mutated = dict(report)
        del mutated[field]
        assert codes(validate_report(mutated)), f"removing {field} should be an error"


def test_error_message_names_the_field(report: dict) -> None:
    report["primitives"] = [{"name": "msm", "ms": 1.0, "share": 1.2}]
    assert "primitives" in first_message(validate_report(report))
