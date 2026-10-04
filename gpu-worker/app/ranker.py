from __future__ import annotations

import hashlib
import re
from typing import Any

import numpy as np
from pydantic import BaseModel, Field


TOKEN_PATTERN = re.compile(r"[A-Za-z_][A-Za-z0-9_]{1,63}")


class Document(BaseModel):
    path: str
    content: str
    changed: bool = False
    score: float = 0.0


class RankingResult(BaseModel):
    documents: list[Document] = Field(default_factory=list)
    accelerator: str
    device: str | None = None


class HashingRanker:
    def __init__(
        self,
        array_module: Any,
        accelerator: str,
        device: str | None = None,
        dimensions: int = 4096,
    ) -> None:
        self.xp = array_module
        self.accelerator = accelerator
        self.device = device
        self.dimensions = dimensions

    def rank(self, query: str, documents: list[Document], limit: int) -> RankingResult:
        if not documents:
            return RankingResult(documents=[], accelerator=self.accelerator, device=self.device)
        query_vector = self._vectorize(query)
        document_matrix = self.xp.stack([self._vectorize(doc.content + " " + doc.path) for doc in documents])
        query_norm = self.xp.linalg.norm(query_vector)
        document_norms = self.xp.linalg.norm(document_matrix, axis=1)
        scores = (document_matrix @ query_vector) / self.xp.maximum(document_norms * query_norm, 1e-9)
        changed_bonus = self.xp.asarray([1.0 if document.changed else 0.0 for document in documents])
        scores = scores + changed_bonus
        host_scores = self._to_host(scores)
        ranked = [
            document.model_copy(update={"score": float(host_scores[index])})
            for index, document in enumerate(documents)
        ]
        ranked.sort(key=lambda item: (-item.score, item.path))
        return RankingResult(
            documents=ranked[: max(1, min(limit, len(ranked)))],
            accelerator=self.accelerator,
            device=self.device,
        )

    def _vectorize(self, value: str):
        vector = np.zeros(self.dimensions, dtype=np.float32)
        for token in TOKEN_PATTERN.findall(value.lower()):
            digest = hashlib.blake2b(token.encode("utf-8"), digest_size=8).digest()
            index = int.from_bytes(digest, "little") % self.dimensions
            vector[index] += 1.0
        return self.xp.asarray(vector)

    def _to_host(self, value):
        if self.accelerator == "cuda":
            return self.xp.asnumpy(value)
        return np.asarray(value)


def create_ranker() -> HashingRanker:
    try:
        import cupy as cp

        if cp.cuda.runtime.getDeviceCount():
            properties = cp.cuda.runtime.getDeviceProperties(0)
            name = properties.get("name", "NVIDIA CUDA GPU")
            if isinstance(name, bytes):
                name = name.decode("utf-8", errors="replace")
            return HashingRanker(cp, accelerator="cuda", device=str(name))
    except Exception:
        pass
    return HashingRanker(np, accelerator="cpu")
