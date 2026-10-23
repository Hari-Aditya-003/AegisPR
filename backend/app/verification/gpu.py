"""Compare bounded, caller-supplied GPU results without executing repository code.

The JSON is not a trusted hardware receipt. A caller must collect base and head
results with the same harness on a real GPU before this comparison is meaningful.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

from app.verification.local import compare_measurements


class GPUComparisonError(ValueError):
    pass


def _finite_number(value: object) -> bool:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    try:
        return math.isfinite(float(value))
    except OverflowError:
        return False


def load_gpu_artifact(path: Path) -> dict:
    source = Path(path)
    try:
        if source.stat().st_size > 1_000_000:
            raise GPUComparisonError("GPU artifact exceeds the 1 MB limit")
        payload = json.loads(source.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise GPUComparisonError("GPU artifact could not be read as JSON") from exc
    if not isinstance(payload, dict):
        raise GPUComparisonError("GPU artifact must be a JSON object")
    return payload


def _validated(payload: dict) -> tuple[dict, dict[str, list[float]], dict[str, list[float]]]:
    device, outputs, latency = (payload.get(key) for key in ("device", "outputs", "latency_ms"))
    if not isinstance(device, dict) or device.get("backend") != "cuda" or not isinstance(device.get("name"), str) or not device["name"].strip():
        raise GPUComparisonError("GPU artifact needs a named CUDA device")
    if not isinstance(outputs, dict) or not outputs or len(outputs) > 100 or not isinstance(latency, dict):
        raise GPUComparisonError("GPU artifact needs one to 100 output cases and matching latency cases")
    if outputs.keys() != latency.keys():
        raise GPUComparisonError("GPU output and latency case names must match")
    for name, values in outputs.items():
        if not isinstance(name, str) or not name or len(name) > 100:
            raise GPUComparisonError("GPU case names must be short nonempty strings")
        if not isinstance(values, list) or not values or len(values) > 10_000:
            raise GPUComparisonError("GPU outputs must be bounded nonempty numeric arrays")
        if any(not _finite_number(value) for value in values):
            raise GPUComparisonError("GPU outputs must contain only finite numbers")
        samples = latency[name]
        if not isinstance(samples, list) or not 3 <= len(samples) <= 5:
            raise GPUComparisonError("GPU latency requires three to five samples per case")
        if any(not _finite_number(value) or value <= 0 for value in samples):
            raise GPUComparisonError("GPU latency samples must be finite positive numbers")
    return device, outputs, latency


def compare_gpu_artifacts(
    base: dict, head: dict, *, absolute_tolerance: float = 1e-5, relative_tolerance: float = 1e-4,
) -> dict:
    """Compare output arrays and repeated latency from two claimed CUDA runs."""
    if any(not math.isfinite(value) or value < 0 or value > 1 for value in (absolute_tolerance, relative_tolerance)):
        raise GPUComparisonError("Numeric tolerances must be finite values between zero and one")
    base_device, base_outputs, base_latency = _validated(base)
    head_device, head_outputs, head_latency = _validated(head)
    if base_device != head_device:
        raise GPUComparisonError("Base and head results must declare the same device")
    if base_outputs.keys() != head_outputs.keys():
        raise GPUComparisonError("Base and head output case names must match")
    differences: list[str] = []
    performance: dict[str, dict] = {}
    for name, expected in base_outputs.items():
        actual = head_outputs[name]
        if len(expected) != len(actual) or any(
            not math.isclose(left, right, abs_tol=absolute_tolerance, rel_tol=relative_tolerance)
            for left, right in zip(expected, actual)
        ):
            differences.append(name)
        timing = compare_measurements(base_latency[name], head_latency[name], [], [])
        performance[name] = {
            "status": timing["time_status"],
            "base_median_ms": timing["base_median_ms"],
            "head_median_ms": timing["head_median_ms"],
        }
    return {
        "numeric_status": "difference_observed" if differences else "no_difference_observed",
        "different_cases": differences,
        "performance": performance,
        "device_claim": base_device,
        "absolute_tolerance": absolute_tolerance,
        "relative_tolerance": relative_tolerance,
        "model_calls": 0,
        "scope": "Comparison of caller-supplied CUDA JSON; not hardware attestation or proof of Nebius GPU execution",
    }
