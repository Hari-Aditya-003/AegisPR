import httpx
import pytest

from app.github.client import GitHubClient
from app.github.parser import PullRequestReference


@pytest.mark.asyncio
async def test_fetches_public_pull_request_metadata() -> None:
    payload = {
        "title": "Coupon support", "html_url": "https://github.com/acme/store/pull/42",
        "changed_files": 2, "additions": 12, "deletions": 3,
        "base": {"ref": "main", "sha": "a" * 40, "repo": {"clone_url": "https://github.com/acme/store.git", "private": False}},
        "head": {"ref": "coupon", "sha": "b" * 40},
    }
    client = GitHubClient("token")
    await client._client.aclose()
    client._client = httpx.AsyncClient(
        transport=httpx.MockTransport(lambda request: httpx.Response(200, json=payload)),
        base_url="https://api.github.com",
    )
    summary = await client.get_pull_request(PullRequestReference("acme", "store", 42))
    assert summary.title == "Coupon support"
    assert summary.head_commit == "b" * 40
    await client.close()


@pytest.mark.asyncio
async def test_rejects_private_repository_metadata() -> None:
    client = GitHubClient()
    await client._client.aclose()
    client._client = httpx.AsyncClient(
        transport=httpx.MockTransport(lambda request: httpx.Response(200, json={"base": {"repo": {"private": True}}})),
        base_url="https://api.github.com",
    )
    with pytest.raises(ValueError, match="public repositories"):
        await client.get_pull_request(PullRequestReference("acme", "store", 42))
    await client.close()
