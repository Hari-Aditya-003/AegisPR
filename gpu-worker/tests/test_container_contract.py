from pathlib import Path


def test_cupy_cache_uses_writable_tmp_directory() -> None:
    dockerfile = (Path(__file__).parents[1] / "Dockerfile").read_text(encoding="utf-8")

    assert "CUPY_CACHE_DIR=/tmp/cupy-cache" in dockerfile
