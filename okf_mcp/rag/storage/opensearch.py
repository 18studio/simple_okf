"""OpenSearch storage adapter for OKF RAG chunks."""

from __future__ import annotations

from typing import Any

from okf_mcp.rag.http import RagHttpError, request_json
from okf_mcp.rag.models import OKFChunkRecord, OKFRetrievalHit


class OpenSearchStore:
    def __init__(self, *, url: str, index: str, user: str = "", password: str = "", timeout: float = 10.0) -> None:
        self.url = url
        self.index = index
        self.user = user
        self.password = password
        self.timeout = timeout

    def ensure_index(self, *, recreate: bool = False) -> dict[str, Any]:
        if not self.index:
            raise RagHttpError("RAG_OPENSEARCH_INDEX is not configured")
        if recreate:
            request_json(
                "DELETE",
                self.url,
                self.index,
                user=self.user,
                password=self.password,
                timeout=self.timeout,
                expected=(200, 202, 404),
            )
        mapping = {
            "settings": {"index": {"number_of_shards": 1, "number_of_replicas": 0}},
            "mappings": {
                "properties": {
                    "content": {"type": "text"},
                    "contextualized_content": {"type": "text"},
                    "concept_id": {"type": "keyword"},
                    "chunk_id": {"type": "keyword"},
                    "type": {"type": "keyword"},
                    "status": {"type": "keyword"},
                    "tags": {"type": "keyword"},
                    "title": {"type": "text", "fields": {"keyword": {"type": "keyword"}}},
                    "path": {"type": "keyword"},
                    "line_start": {"type": "integer"},
                    "line_end": {"type": "integer"},
                }
            },
        }
        return request_json(
            "PUT",
            self.url,
            self.index,
            payload=mapping,
            user=self.user,
            password=self.password,
            timeout=self.timeout,
            expected=(200, 201, 400),
        ).json() or {}

    def index_chunks(self, chunks: tuple[OKFChunkRecord, ...]) -> dict[str, Any]:
        self.ensure_index(recreate=True)
        for chunk in chunks:
            request_json(
                "PUT",
                self.url,
                f"{self.index}/_doc/{chunk.chunk_id}",
                payload=chunk.to_dict(),
                user=self.user,
                password=self.password,
                timeout=self.timeout,
                expected=(200, 201),
            )
        request_json("POST", self.url, f"{self.index}/_refresh", user=self.user, password=self.password, timeout=self.timeout)
        return {"indexed_count": len(chunks), "index": self.index}

    def search(
        self,
        query: str,
        *,
        chunks_by_id: dict[str, OKFChunkRecord],
        limit: int = 10,
        type_filter: str | None = None,
        tag: str | None = None,
    ) -> list[OKFRetrievalHit]:
        filters: list[dict[str, Any]] = []
        if type_filter:
            filters.append({"term": {"type": type_filter}})
        if tag:
            filters.append({"term": {"tags": tag}})
        body = {
            "size": max(1, limit),
            "query": {
                "bool": {
                    "must": [
                        {
                            "multi_match": {
                                "query": query,
                                "fields": ["title^3", "description^2", "content", "contextualized_content", "concept_id"],
                            }
                        }
                    ],
                    "filter": filters,
                }
            },
        }
        payload = request_json(
            "POST",
            self.url,
            f"{self.index}/_search",
            payload=body,
            user=self.user,
            password=self.password,
            timeout=self.timeout,
        ).json() or {}
        hits: list[OKFRetrievalHit] = []
        for hit in payload.get("hits", {}).get("hits", []):
            source = hit.get("_source") or {}
            chunk_id = str(source.get("chunk_id") or hit.get("_id") or "")
            chunk = chunks_by_id.get(chunk_id)
            if chunk is None:
                continue
            hits.append(OKFRetrievalHit(chunk=chunk, score=float(hit.get("_score") or 0.0), reasons=("opensearch",)))
        return hits
