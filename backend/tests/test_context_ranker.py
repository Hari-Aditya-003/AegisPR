import pytest

from app.services.context_ranker import ContextDocument, ContextRanker


@pytest.mark.asyncio
async def test_cpu_fallback_prioritizes_changed_and_query_relevant_files() -> None:
    ranker = ContextRanker(gpu_worker_url=None)
    documents = [
        ContextDocument(path="src/coupon.py", content="apply coupon discount to cart total", changed=True),
        ContextDocument(path="src/auth.py", content="validate access token", changed=False),
        ContextDocument(path="README.md", content="project documentation", changed=False),
    ]

    result = await ranker.rank("coupon can produce negative cart total", documents, limit=2)

    assert result.accelerator == "cpu"
    assert result.documents[0].path == "src/coupon.py"
    assert len(result.documents) == 2

