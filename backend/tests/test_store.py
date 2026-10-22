import sqlite3
from pathlib import Path

from app.schemas.verification import VerificationRun, VerificationStatus
from app.services.store import VerificationStore


def test_store_round_trips_and_lists_runs(tmp_path: Path) -> None:
    store = VerificationStore(tmp_path / "runs.sqlite3")
    run = VerificationRun(
        pull_request_url="https://github.com/acme/store/pull/42",
        status=VerificationStatus.ANALYSIS_ONLY,
    )
    store.save(run)

    assert store.get(run.id) == run
    assert store.get("missing") is None
    assert [item.id for item in store.list(limit=1)] == [run.id]


def test_run_store_uses_wal_for_streaming_readers(tmp_path: Path) -> None:
    store = VerificationStore(tmp_path / "runs.sqlite3")
    with sqlite3.connect(store.path) as connection:
        assert connection.execute("PRAGMA journal_mode").fetchone()[0] == "wal"
