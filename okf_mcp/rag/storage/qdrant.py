"""Qdrant storage adapter for OKF RAG chunks."""

from __future__ import annotations

from typing import Any

from okf_mcp.rag.embeddings import EmbeddingProvider
from okf_mcp.rag.http import RagHttpError, request_json
from okf_mcp.rag.models import OKFChunkRecord, OKFRetrievalHit


class QdrantStore:
    def __init__(
        self,
        *,
        url: str,
        collection: str,
        api_key: str = "",
        vector_size: int = 64,
        timeout: float = 10.0,
    ) -> None:
        self.url = url
        self.collection = collection
        self.api_key = api_key
        self.vector_size = vector_size
        self.timeout = timeout

    def ensure_collection(self, *, recreate: bool = False) -> dict[str, Any]:
        if not self.collection:
            raise RagHttpError("RAG_QDRANT_COLLECTION is not configured")
        if recreate:
            request_json(
                "DELETE",
                self.url,
                f"collections/{self.collection}",
                bearer_token=self.api_key,
                timeout=self.timeout,
                expected=(200, 202, 404),
            )
        payload = {"vectors": {"size": self.vector_size, "distance": "Cosine"}}
        return request_json(
            "PUT",
            self.url,
            f"collections/{self.collection}",
            payload=payload,
            bearer_token=self.api_key,
            timeout=self.timeout,
            expected=(200,),
        ).json() or {}

    def index_chunks(self, chunks: tuple[OKFChunkRecord, ...], embedding_provider: EmbeddingProvider) -> dict[str, Any]:
        self.ensure_collection(recreate=True)
        points = []
        for index, chunk in enumerate(chunks):
            points.append(
                {
                    "id": index + 1,
                    "vector": embedding_provider.embed(chunk.contextualized_content),
                    "payload": {**chunk.to_dict(), "chunk_id": chunk.chunk_id},
                }
            )
        if points:
            request_json(
                "PUT",
                self.url,
                f"collections/{self.collection}/points",
                payload={"points": points},
                bearer_token=self.api_key,
                timeout=self.timeout,
            )
        return {"indexed_count": len(points), "collection": self.collection, "vector_size": self.vector_size}

    def search(
        self,
        query: str,
        *,
        chunks_by_id: dict[str, OKFChunkRecord],
        embedding_provider: EmbeddingProvider,
        limit: int = 10,
        type_filter: str | None = None,
        tag: str | None = None,
    ) -> list[OKFRetrievalHit]:
        must: list[dict[str, Any]] = []
        if type_filter:
            must.append({"key": "type", "match": {"value": type_filter}})
        if tag:
            must.append({"key": "tags", "match": {"value": tag}})
        body: dict[str, Any] = {
            "vector": embedding_provider.embed(query),
            "limit": max(1, limit),
            "with_payload": True,
        }
        if must:
            body["filter"] = {"must": must}
        payload = request_json(
            "POST",
            self.url,
            f"collections/{self.collection}/points/search",
            payload=body,
            bearer_token=self.api_key,
            timeout=self.timeout,
        ).json() or {}
        hits: list[OKFRetrievalHit] = []
        for item in payload.get("result", []):
            source = item.get("payload") or {}
            chunk_id = str(source.get("chunk_id") or "")
            chunk = chunks_by_id.get(chunk_id)
            if chunk is None:
                continue
            hits.append(OKFRetrievalHit(chunk=chunk, score=float(item.get("score") or 0.0), reasons=("qdrant",)))
        return hits
