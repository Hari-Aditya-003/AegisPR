from pathlib import Path


def test_cupy_cache_uses_writable_tmp_directory() -> None:
    dockerfile = (Path(__file__).parents[1] / "Dockerfile").read_text(encoding="utf-8")

    assert "CUPY_CACHE_DIR=/tmp/cupy-cache" in dockerfile


def test_cupy_runtime_includes_cuda_headers_for_jit_compilation() -> None:
    dockerfile = (Path(__file__).parents[1] / "Dockerfile").read_text(encoding="utf-8")

    assert "nvidia/cuda:12.8.1-devel-ubuntu24.04" in dockerfile
