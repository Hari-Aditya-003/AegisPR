from __future__ import annotations

import httpx

from app.github.parser import PullRequestReference, parse_pull_request_url
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
        parse_pull_request_url(
            f"https://github.com/{reference.owner}/{reference.repository}/pull/{reference.number}"
        )
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
            description=payload.get("body") or "",
            html_url=payload["html_url"],
            clone_url=f"https://github.com/{reference.owner}/{reference.repository}.git",
            base_ref=payload["base"]["ref"],
            head_ref=payload["head"]["ref"],
            base_commit=payload["base"]["sha"],
            head_commit=payload["head"]["sha"],
            changed_files=payload.get("changed_files", 0),
            additions=payload.get("additions", 0),
            deletions=payload.get("deletions", 0),
        )

    async def get_commit_messages(self, reference: PullRequestReference) -> list[str]:
        response = await self._client.get(
            f"/repos/{reference.owner}/{reference.repository}/pulls/{reference.number}/commits",
            params={"per_page": 10},
        )
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, list):
            return []
        return [item["commit"]["message"][:300] for item in payload
                if isinstance(item, dict) and isinstance(item.get("commit"), dict)
                and isinstance(item["commit"].get("message"), str)][:10]

    async def close(self) -> None:
        await self._client.aclose()

