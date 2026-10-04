from __future__ import annotations

import math
import re
from collections import Counter

import httpx
from pydantic import BaseModel, Field


TOKEN_PATTERN = re.compile(r"[A-Za-z_][A-Za-z0-9_]{1,63}")


class ContextDocument(BaseModel):
    path: str
    content: str
    changed: bool = False
    score: float = 0.0


class ContextRanking(BaseModel):
    documents: list[ContextDocument] = Field(default_factory=list)
    accelerator: str = "cpu"
    device: str | None = None


class ContextRanker:
    def __init__(self, gpu_worker_url: str | None, token: str | None = None) -> None:
        self.gpu_worker_url = gpu_worker_url.rstrip("/") if gpu_worker_url else None
        self.token = token

    async def rank(
        self, query: str, documents: list[ContextDocument], limit: int = 20
    ) -> ContextRanking:
        if self.gpu_worker_url and documents:
            headers = {"Authorization": f"Bearer {self.token}"} if self.token else {}
            try:
                async with httpx.AsyncClient(timeout=20.0) as client:
                    response = await client.post(
                        f"{self.gpu_worker_url}/rank",
                        headers=headers,
                        json={
                            "query": query,
                            "documents": [doc.model_dump(exclude={"score"}) for doc in documents],
                            "limit": limit,
                        },
                    )
                    response.raise_for_status()
                    return ContextRanking.model_validate(response.json())
            except (httpx.HTTPError, ValueError):
                pass
        return self._cpu_rank(query, documents, limit)

    def _cpu_rank(
        self, query: str, documents: list[ContextDocument], limit: int
    ) -> ContextRanking:
        query_terms = Counter(token.lower() for token in TOKEN_PATTERN.findall(query))
        scored: list[ContextDocument] = []
        for document in documents:
            terms = Counter(token.lower() for token in TOKEN_PATTERN.findall(document.content))
            dot = sum(query_terms[token] * terms[token] for token in query_terms)
            query_norm = math.sqrt(sum(value * value for value in query_terms.values())) or 1.0
            document_norm = math.sqrt(sum(value * value for value in terms.values())) or 1.0
            lexical = dot / (query_norm * document_norm)
            path_bonus = sum(0.1 for token in query_terms if token in document.path.lower())
            changed_bonus = 1.0 if document.changed else 0.0
            scored.append(document.model_copy(update={"score": lexical + path_bonus + changed_bonus}))
        scored.sort(key=lambda item: (-item.score, item.path))
        return ContextRanking(documents=scored[: max(1, limit)], accelerator="cpu")

