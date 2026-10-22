import httpx
import pytest

from app.github.client import GitHubClient
from app.github.parser import PullRequestReference


@pytest.mark.asyncio
async def test_fetches_public_pull_request_metadata() -> None:
    payload = {
        "title": "Coupon support", "body": "Preserve discount floor", "html_url": "https://github.com/acme/store/pull/42",
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
    assert summary.description == "Preserve discount floor"
    assert summary.head_commit == "b" * 40
    await client.close()


@pytest.mark.asyncio
async def test_commit_messages_are_bounded_for_intent_review() -> None:
    def response(request):
        assert request.url.path == "/repos/acme/store/pulls/42/commits"
        return httpx.Response(200, json=[{"commit": {"message": "x" * 400}}, {"commit": {"message": "Fix boundary"}}])

    client = GitHubClient()
    await client._client.aclose()
    client._client = httpx.AsyncClient(transport=httpx.MockTransport(response), base_url="https://api.github.com")
    try:
        messages = await client.get_commit_messages(PullRequestReference("acme", "store", 42))
        assert messages == ["x" * 300, "Fix boundary"]
    finally:
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


@pytest.mark.asyncio
async def test_clone_url_is_derived_from_validated_reference_not_api_payload() -> None:
    payload = {
        "html_url": "https://github.com/acme/store/pull/42",
        "base": {"ref": "main", "sha": "a" * 40, "repo": {"clone_url": "http://127.0.0.1/private.git", "private": False}},
        "head": {"ref": "head", "sha": "b" * 40},
    }
    client = GitHubClient()
    await client._client.aclose()
    client._client = httpx.AsyncClient(transport=httpx.MockTransport(lambda request: httpx.Response(200, json=payload)), base_url="https://api.github.com")
    try:
        summary = await client.get_pull_request(PullRequestReference("acme", "store", 42))
        assert summary.clone_url == "https://github.com/acme/store.git"
    finally:
        await client.close()
