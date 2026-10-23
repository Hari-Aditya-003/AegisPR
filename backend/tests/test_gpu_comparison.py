from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.verification.gpu import GPUComparisonError, compare_gpu_artifacts, load_gpu_artifact
from app.cli import main


def artifact(outputs: dict[str, list[float]], latency: dict[str, list[float]]) -> dict:
    return {
        "device": {"backend": "cuda", "name": "NVIDIA Test GPU"},
        "outputs": outputs,
        "latency_ms": latency,
    }


def test_comparison_finds_numeric_difference_without_model_call() -> None:
    base = artifact({"sum": [1.0, 2.0]}, {"sum": [10.0, 10.1, 9.9]})
    head = artifact({"sum": [1.0, 2.5]}, {"sum": [10.0, 10.1, 9.9]})
    result = compare_gpu_artifacts(base, head)
    assert result["numeric_status"] == "difference_observed"
    assert result["different_cases"] == ["sum"]
    assert result["model_calls"] == 0
    assert "not hardware attestation" in result["scope"]


def test_comparison_allows_bounded_floating_point_tolerance_and_flags_slowdown() -> None:
    base = artifact({"sum": [1.0, 2.0]}, {"sum": [10.0, 10.1, 9.9]})
    head = artifact({"sum": [1.000001, 2.0]}, {"sum": [15.0, 15.1, 14.9]})
    result = compare_gpu_artifacts(base, head)
    assert result["numeric_status"] == "no_difference_observed"
    assert result["performance"]["sum"]["status"] == "possible_regression"


def test_comparison_rejects_mismatched_device_and_nonfinite_output() -> None:
    base = artifact({"sum": [1.0]}, {"sum": [10.0, 10.0, 10.0]})
    head = artifact({"sum": [float("nan")]}, {"sum": [10.0, 10.0, 10.0]})
    with pytest.raises(GPUComparisonError, match="finite"):
        compare_gpu_artifacts(base, head)
    head = artifact({"sum": [1.0]}, {"sum": [10.0, 10.0, 10.0]})
    head["device"]["name"] = "Other GPU"
    with pytest.raises(GPUComparisonError, match="same device"):
        compare_gpu_artifacts(base, head)


def test_gpu_artifact_loader_rejects_oversize_file(tmp_path: Path) -> None:
    path = tmp_path / "large.json"
    path.write_bytes(b"x" * 1_000_001)
    with pytest.raises(GPUComparisonError, match="1 MB"):
        load_gpu_artifact(path)


def test_cli_compares_gpu_artifacts_without_running_code(tmp_path: Path, capsys) -> None:
    base_path, head_path = tmp_path / "base.json", tmp_path / "head.json"
    base_path.write_text(json.dumps(artifact({"sum": [1]}, {"sum": [10, 10, 10]})), encoding="utf-8")
    head_path.write_text(json.dumps(artifact({"sum": [2]}, {"sum": [10, 10, 10]})), encoding="utf-8")
    assert main(["compare-gpu", "--base", str(base_path), "--head", str(head_path), "--json"]) == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["numeric_status"] == "difference_observed"
