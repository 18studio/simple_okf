"""Mode-aware OKF RAG retriever with optional infrastructure backends."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from okf_mcp.rag.config import RagSettings
from okf_mcp.rag.embeddings import build_embedding_provider
from okf_mcp.rag.events import DeterministicRagEvaluator, RagEvent
from okf_mcp.rag.http import RagHttpError
from okf_mcp.rag.models import OKFChunkRecord, OKFRetrievalHit
from okf_mcp.rag.retrieval.local import LocalOKFRetriever
from okf_mcp.rag.storage import ClickHouseEventWriter, OpenSearchStore, QdrantStore


class OKFRagRetriever:
    """RAG retriever that supports local, keyword, semantic, and hybrid modes."""

    def __init__(self, settings: RagSettings) -> None:
        self.settings = settings
        self.local = LocalOKFRetriever(settings.bundle_dir)
        self.embedding_provider = build_embedding_provider(
            model=settings.embedding_model,
            dimensions=settings.embedding_dimensions,
        )

    def parse(self):
        return self.local.parse()

    def refresh_index(self, artifacts_dir: str | Path | None = None, *, mode: str | None = None) -> dict[str, object]:
        selected_mode = self._mode(mode)
        parsed = self.parse()
        local_payload = self.local.refresh_index(artifacts_dir or self.settings.artifacts_dir)
        payload: dict[str, object] = {
            **local_payload,
            "mode": selected_mode,
            "local": local_payload,
            "opensearch": None,
            "qdrant": None,
        }
        if selected_mode in {"keyword", "hybrid"}:
            payload["opensearch"] = self._opensearch().index_chunks(parsed.chunks)
        if selected_mode in {"semantic", "hybrid"}:
            payload["qdrant"] = self._qdrant().index_chunks(parsed.chunks, self.embedding_provider)
        return payload

    def retrieve(
        self,
        query: str,
        *,
        limit: int = 10,
        type_filter: str | None = None,
        tag: str | None = None,
        mode: str | None = None,
        correlation_id: str | None = None,
    ) -> dict[str, object]:
        started = time.monotonic()
        selected_mode = self._mode(mode)
        filters = {"type_filter": type_filter, "tag": tag}
        try:
            if selected_mode == "local":
                result = self.local.retrieve(query, limit=limit, type_filter=type_filter, tag=tag)
                result["mode"] = "local"
            else:
                result = self._retrieve_infrastructure(query, limit=limit, type_filter=type_filter, tag=tag, mode=selected_mode)
            timings = {"total": round((time.monotonic() - started) * 1000, 3)}
            result["timings_ms"] = timings
            event = RagEvent.create(
                event_type="retrieve",
                status="passed",
                query=query,
                retrieval_mode=selected_mode,
                correlation_id=correlation_id,
                filters={k: v for k, v in filters.items() if v},
                corpus_digest=str(result.get("corpus_digest") or ""),
                retrieved=self._event_hits(result.get("hits", [])),
                timings_ms=timings,
                raw={"limit": limit},
            )
            result["event"] = event.to_dict()
            result["event_storage"] = self._write_event(event)
            return result
        except Exception as exc:
            timings = {"total": round((time.monotonic() - started) * 1000, 3)}
            event = RagEvent.create(
                event_type="retrieve",
                status="failed",
                query=query,
                retrieval_mode=selected_mode,
                correlation_id=correlation_id,
                filters={k: v for k, v in filters.items() if v},
                timings_ms=timings,
                error=str(exc),
                raw={"limit": limit},
            )
            storage = self._write_event(event)
            if self.settings.event_storage_mode == "required" and storage.get("status") == "failed":
                raise ValueError(f"retrieval failed and event storage failed: {exc}; {storage.get('error')}") from exc
            raise

    def answer(self, question: str, *, limit: int = 5, mode: str | None = None, correlation_id: str | None = None) -> dict[str, object]:
        retrieval = self.retrieve(question, limit=limit, mode=mode, correlation_id=correlation_id)
        hits = list(retrieval.get("hits", []))
        if not hits:
            payload: dict[str, object] = {
                "status": "insufficient_evidence",
                "answer": "No OKF evidence found for the question.",
                "citations": [],
                "retrieval": retrieval,
            }
        elif retrieval.get("mode") == "local":
            payload = self.local.answer(question, limit=limit)
            payload["retrieval"] = retrieval
        else:
            citations = []
            answer_lines = ["Found relevant OKF evidence:"]
            for index, hit in enumerate(hits, start=1):
                citation = {
                    "concept_id": hit.get("concept_id"),
                    "path": hit.get("path"),
                    "title": hit.get("title"),
                    "type": hit.get("type"),
                    "line_start": hit.get("line_start"),
                    "line_end": hit.get("line_end"),
                }
                citations.append(citation)
                content = " ".join(str(hit.get("content") or "").split())
                if len(content) > 260:
                    content = content[:260].rstrip() + "…"
                answer_lines.append(
                    f"{index}. {hit.get('title')} ({hit.get('concept_id')}:{hit.get('line_start')}-{hit.get('line_end')}): {content}"
                )
            payload = {
                "status": "extractive",
                "answer": "\n".join(answer_lines),
                "citations": citations,
                "retrieval": retrieval,
            }
        self._evaluate_and_record_answer(question, payload, mode=str(retrieval.get("mode") or self._mode(mode)), correlation_id=correlation_id)
        return payload

    def get_source(self, concept_id: str, *, line_start: int | None = None, line_end: int | None = None) -> dict[str, object]:
        return self.local.get_source(concept_id, line_start=line_start, line_end=line_end)

    def concept_relationships(self, concept_id: str, *, depth: int = 1) -> dict[str, object]:
        return self.local.concept_relationships(concept_id, depth=depth)

    def _retrieve_infrastructure(
        self,
        query: str,
        *,
        limit: int,
        type_filter: str | None,
        tag: str | None,
        mode: str,
    ) -> dict[str, object]:
        parsed = self.parse()
        chunks_by_id = {chunk.chunk_id: chunk for chunk in parsed.chunks}
        hits: list[OKFRetrievalHit] = []
        if mode in {"keyword", "hybrid"}:
            hits.extend(self._opensearch().search(query, chunks_by_id=chunks_by_id, limit=limit, type_filter=type_filter, tag=tag))
        if mode in {"semantic", "hybrid"}:
            hits.extend(
                self._qdrant().search(
                    query,
                    chunks_by_id=chunks_by_id,
                    embedding_provider=self.embedding_provider,
                    limit=limit,
                    type_filter=type_filter,
                    tag=tag,
                )
            )
        selected = self._merge_hits(hits, limit=limit, mode=mode)
        return {
            "query": query,
            "limit": limit,
            "mode": mode,
            "corpus_digest": parsed.inventory.corpus_digest,
            "chunk_count": len(parsed.chunks),
            "report": parsed.report.to_dict(),
            "hits": [hit.to_dict() for hit in selected],
        }

    def _merge_hits(self, hits: list[OKFRetrievalHit], *, limit: int, mode: str) -> list[OKFRetrievalHit]:
        if mode != "hybrid":
            deduped: dict[str, OKFRetrievalHit] = {}
            for hit in sorted(hits, key=lambda item: (-item.score, item.chunk.concept_id, item.chunk.line_start)):
                deduped.setdefault(hit.chunk.chunk_id, hit)
            return list(deduped.values())[: max(1, limit)]

        # OpenSearch BM25 and Qdrant cosine scores are not comparable. Use
        # weighted reciprocal-rank fusion per backend, then sum contributions for
        # chunks found by both systems.
        by_backend: dict[str, list[OKFRetrievalHit]] = {"opensearch": [], "qdrant": []}
        for hit in hits:
            if "opensearch" in hit.reasons:
                by_backend["opensearch"].append(hit)
            elif "qdrant" in hit.reasons:
                by_backend["qdrant"].append(hit)
        fused: dict[str, OKFRetrievalHit] = {}
        weights = {"opensearch": self.settings.hybrid_keyword_weight, "qdrant": self.settings.hybrid_semantic_weight}
        for backend, backend_hits in by_backend.items():
            ranked = sorted(backend_hits, key=lambda item: (-item.score, item.chunk.concept_id, item.chunk.line_start))
            for rank, hit in enumerate(ranked, start=1):
                contribution = weights[backend] * (1.0 / (60.0 + rank))
                current = fused.get(hit.chunk.chunk_id)
                if current is None:
                    fused[hit.chunk.chunk_id] = OKFRetrievalHit(hit.chunk, contribution, hit.reasons)
                else:
                    reasons = tuple(sorted(set(current.reasons + hit.reasons)))
                    fused[hit.chunk.chunk_id] = OKFRetrievalHit(hit.chunk, current.score + contribution, reasons)
        merged = list(fused.values())
        merged.sort(key=lambda hit: (-hit.score, hit.chunk.concept_id, hit.chunk.line_start))
        return merged[: max(1, limit)]

    def _evaluate_and_record_answer(self, question: str, payload: dict[str, object], *, mode: str, correlation_id: str | None) -> None:
        if self.settings.evaluation_mode == "disabled":
            return
        hits = list((payload.get("retrieval") or {}).get("hits", [])) if isinstance(payload.get("retrieval"), dict) else []
        citations = list(payload.get("citations") or [])
        evaluator = DeterministicRagEvaluator(threshold=self.settings.evaluation_threshold)
        metrics = [metric.to_dict() for metric in evaluator.evaluate(question=question, answer=str(payload.get("answer") or ""), hits=hits, citations=citations)]
        passed = all(item.get("passed") for item in metrics)
        status = "passed" if passed else "degraded"
        if self.settings.evaluation_mode == "fail-on-threshold" and not passed:
            status = "failed"
        event = RagEvent.create(
            event_type="answer",
            status=status,
            query=question,
            retrieval_mode=mode,
            correlation_id=correlation_id,
            corpus_digest=str((payload.get("retrieval") or {}).get("corpus_digest") or "") if isinstance(payload.get("retrieval"), dict) else "",
            retrieved=self._event_hits(hits),
            citations=citations,
            answer=str(payload.get("answer") or ""),
            metrics=metrics,
            evaluator=evaluator.metadata(),
        )
        payload["evaluation"] = {"status": status, "metrics": metrics, "evaluator": evaluator.metadata()}
        payload["event"] = event.to_dict()
        payload["event_storage"] = self._write_event(event)
        if self.settings.evaluation_mode == "fail-on-threshold" and not passed:
            raise ValueError("RAG evaluation metrics did not meet configured threshold")

    def _write_event(self, event: RagEvent) -> dict[str, object]:
        if self.settings.event_storage_mode == "disabled":
            return {"status": "disabled"}
        try:
            return {"status": "written", **self._clickhouse().write_event(event)}
        except Exception as exc:
            if self.settings.event_storage_mode == "required":
                raise
            return {"status": "failed", "error": str(exc)}

    def _event_hits(self, hits: object) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        if not isinstance(hits, list):
            return out
        for hit in hits:
            if not isinstance(hit, dict):
                continue
            out.append(
                {
                    "chunk_id": hit.get("chunk_id"),
                    "concept_id": hit.get("concept_id"),
                    "score": hit.get("score"),
                    "reasons": hit.get("reasons"),
                    "line_start": hit.get("line_start"),
                    "line_end": hit.get("line_end"),
                    "title": hit.get("title"),
                    "type": hit.get("type"),
                    "status": hit.get("status"),
                }
            )
        return out

    def _mode(self, override: str | None) -> str:
        mode = (override or self.settings.retrieval_mode or "local").casefold()
        if mode not in {"local", "keyword", "semantic", "hybrid"}:
            raise ValueError("retrieval mode must be one of: local, keyword, semantic, hybrid")
        return mode

    def _opensearch(self) -> OpenSearchStore:
        return OpenSearchStore(
            url=self.settings.opensearch_url,
            index=self.settings.opensearch_index,
            user=self.settings.opensearch_user,
            password=self.settings.opensearch_password,
            timeout=self.settings.infrastructure_timeout_seconds,
        )

    def _qdrant(self) -> QdrantStore:
        return QdrantStore(
            url=self.settings.qdrant_url,
            collection=self.settings.qdrant_collection,
            api_key=self.settings.qdrant_api_key,
            vector_size=self.settings.embedding_dimensions,
            timeout=self.settings.infrastructure_timeout_seconds,
        )

    def _clickhouse(self) -> ClickHouseEventWriter:
        return ClickHouseEventWriter(
            url=self.settings.clickhouse_url,
            user=self.settings.clickhouse_user,
            password=self.settings.clickhouse_password,
            database=self.settings.clickhouse_database,
            table=self.settings.clickhouse_events_table,
            timeout=self.settings.infrastructure_timeout_seconds,
        )
