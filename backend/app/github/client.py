from __future__ import annotations

import httpx

from app.github.parser import PullRequestReference
from app.schemas.verification import PullRequestSummary


class GitHubClient:
    def __init__(self, token: str | None = None) -> None:
        headers = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        self._client = httpx.AsyncClient(
            base_url="https://api.github.com",
            headers=headers,
            timeout=httpx.Timeout(30.0),
            follow_redirects=False,
        )

    async def get_pull_request(self, reference: PullRequestReference) -> PullRequestSummary:
        response = await self._client.get(
            f"/repos/{reference.owner}/{reference.repository}/pulls/{reference.number}"
        )
        response.raise_for_status()
        payload = response.json()
        if payload.get("base", {}).get("repo", {}).get("private"):
            raise ValueError("Only public repositories are supported in the hackathon MVP")
        return PullRequestSummary(
            owner=reference.owner,
            repository=reference.repository,
            number=reference.number,
            title=payload.get("title", ""),
            html_url=payload["html_url"],
            clone_url=payload["base"]["repo"]["clone_url"],
            base_ref=payload["base"]["ref"],
            head_ref=payload["head"]["ref"],
            base_commit=payload["base"]["sha"],
            head_commit=payload["head"]["sha"],
            changed_files=payload.get("changed_files", 0),
            additions=payload.get("additions", 0),
            deletions=payload.get("deletions", 0),
        )

    async def close(self) -> None:
        await self._client.aclose()

