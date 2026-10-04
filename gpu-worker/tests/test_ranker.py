import numpy as np

from app.ranker import Document, HashingRanker


def test_ranks_changed_relevant_document_first_on_cpu_fallback() -> None:
    ranker = HashingRanker(array_module=np, accelerator="cpu")
    result = ranker.rank(
        "coupon negative cart total",
        [
            Document(path="src/auth.py", content="validate access token", changed=False),
            Document(path="src/coupon.py", content="coupon discount cart total", changed=True),
        ],
        limit=2,
    )

    assert result.accelerator == "cpu"
    assert result.documents[0].path == "src/coupon.py"
    assert result.documents[0].score > result.documents[1].score


def test_ranking_is_bounded_by_limit() -> None:
    ranker = HashingRanker(array_module=np, accelerator="cpu")
    documents = [Document(path=f"{index}.py", content="query") for index in range(5)]
    assert len(ranker.rank("query", documents, limit=3).documents) == 3

