"""Local OKF-aware retrieval without external indexes."""

from __future__ import annotations

import json
import re
from collections import deque
from datetime import datetime, timezone
from pathlib import Path

from okf_mcp.okf import OKFBundle
from okf_mcp.rag.ingestion import OKFConceptParser
from okf_mcp.rag.models import OKFChunkRecord, OKFRetrievalHit

_TOKEN_RE = re.compile(r"[\wА-Яа-яЁё-]+", re.UNICODE)


def _norm(value: str) -> str:
    return " ".join(_TOKEN_RE.findall(value.casefold()))


def _tokens(value: str) -> set[str]:
    return set(_TOKEN_RE.findall(value.casefold()))


def _snippet(text: str, limit: int = 500) -> str:
    compact = " ".join(part.strip() for part in text.split())
    if len(compact) <= limit:
        return compact
    return compact[:limit].rstrip() + "…"


class LocalOKFRetriever:
    """Deterministic lexical/metadata retriever for an OKF bundle."""

    def __init__(self, bundle_dir: str | Path) -> None:
        self.bundle = OKFBundle(bundle_dir)

    def parse(self):
        return OKFConceptParser(self.bundle.root).parse("local-retrieval")

    def refresh_index(self, artifacts_dir: str | Path) -> dict[str, object]:
        """Materialize the current local RAG chunks as a JSON artifact."""
        parsed = self.parse()
        out_dir = Path(artifacts_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / "okf-local-index.json"
        payload = {
            "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
            "kind": "local-okf-rag-index",
            **parsed.to_dict(),
        }
        out_path.write_text(json.dumps(payload, ensure_ascii=False) + "\n", encoding="utf-8")
        return {
            "path": str(out_path),
            "concept_count": parsed.inventory.concept_count,
            "chunk_count": len(parsed.chunks),
            "corpus_digest": parsed.inventory.corpus_digest,
            "report": parsed.report.to_dict(),
        }

    def retrieve(
        self,
        query: str,
        *,
        limit: int = 10,
        type_filter: str | None = None,
        tag: str | None = None,
    ) -> dict[str, object]:
        if not query.strip():
            raise ValueError("query must not be empty")
        parsed = self.parse()
        q_norm = _norm(query)
        q_tokens = _tokens(query)
        hits: list[OKFRetrievalHit] = []

        for chunk in parsed.chunks:
            if type_filter and chunk.type.casefold() != type_filter.casefold():
                continue
            if tag and tag.casefold() not in {item.casefold() for item in chunk.tags}:
                continue
            score, reasons = self._score(chunk, q_norm, q_tokens)
            if score > 0:
                hits.append(OKFRetrievalHit(chunk=chunk, score=score, reasons=tuple(reasons)))

        hits.sort(key=lambda hit: (-hit.score, hit.chunk.concept_id, hit.chunk.line_start))
        selected = hits[: max(1, limit)]
        return {
            "query": query,
            "limit": limit,
            "corpus_digest": parsed.inventory.corpus_digest,
            "chunk_count": len(parsed.chunks),
            "report": parsed.report.to_dict(),
            "hits": [hit.to_dict() for hit in selected],
        }

    def answer(self, question: str, *, limit: int = 5) -> dict[str, object]:
        result = self.retrieve(question, limit=limit)
        hits = result["hits"]
        if not hits:
            return {
                "status": "insufficient_evidence",
                "answer": "No OKF evidence found for the question.",
                "citations": [],
                "retrieval": result,
            }
        citations = []
        answer_lines = ["Found relevant OKF evidence:"]
        for index, hit in enumerate(hits, start=1):
            citation = {
                "concept_id": hit["concept_id"],
                "path": hit["path"],
                "title": hit["title"],
                "type": hit["type"],
                "line_start": hit["line_start"],
                "line_end": hit["line_end"],
            }
            citations.append(citation)
            answer_lines.append(
                f"{index}. {hit['title']} ({hit['concept_id']}:{hit['line_start']}-{hit['line_end']}): "
                f"{_snippet(str(hit['content']), 260)}"
            )
        return {
            "status": "extractive",
            "answer": "\n".join(answer_lines),
            "citations": citations,
            "retrieval": result,
        }

    def get_source(
        self,
        concept_id: str,
        *,
        line_start: int | None = None,
        line_end: int | None = None,
    ) -> dict[str, object]:
        path = self.bundle.concept_id_to_path(concept_id)
        if not path.exists():
            raise ValueError(f"concept does not exist: {concept_id}")
        lines = path.read_text(encoding="utf-8").splitlines()
        start = max(1, line_start or 1)
        end = min(len(lines), line_end or len(lines))
        if end < start:
            raise ValueError("line_end must be greater than or equal to line_start")
        return {
            "concept_id": self.bundle.path_to_concept_id(path),
            "path": path.relative_to(self.bundle.root).as_posix(),
            "line_start": start,
            "line_end": end,
            "text": "\n".join(lines[start - 1 : end]),
        }

    def concept_relationships(self, concept_id: str, *, depth: int = 1) -> dict[str, object]:
        depth = max(1, min(depth, 5))
        graph = self.bundle.build_graph()
        node_ids = {node["id"] for node in graph["nodes"]}
        if concept_id not in node_ids:
            raise ValueError(f"concept does not exist or is not a graph node: {concept_id}")

        outgoing_by_source: dict[str, list[dict[str, object]]] = {}
        incoming_by_target: dict[str, list[dict[str, object]]] = {}
        for edge in graph["edges"]:
            outgoing_by_source.setdefault(str(edge["source"]), []).append(edge)
            incoming_by_target.setdefault(str(edge["target"]), []).append(edge)

        visited = {concept_id}
        frontier = deque([(concept_id, 0)])
        related_edges: list[dict[str, object]] = []
        while frontier:
            current, current_depth = frontier.popleft()
            if current_depth >= depth:
                continue
            for edge in outgoing_by_source.get(current, []):
                related_edges.append({"direction": "outgoing", **edge})
                target = str(edge["target"])
                if target not in visited:
                    visited.add(target)
                    frontier.append((target, current_depth + 1))
            for edge in incoming_by_target.get(current, []):
                related_edges.append({"direction": "incoming", **edge})
                source = str(edge["source"])
                if source not in visited:
                    visited.add(source)
                    frontier.append((source, current_depth + 1))

        nodes_by_id = {node["id"]: node for node in graph["nodes"]}
        return {
            "concept_id": concept_id,
            "depth": depth,
            "nodes": [nodes_by_id[node_id] for node_id in sorted(visited)],
            "edges": related_edges,
        }

    def _score(self, chunk: OKFChunkRecord, q_norm: str, q_tokens: set[str]) -> tuple[float, list[str]]:
        score = 0.0
        reasons: list[str] = []
        searchable = _norm(chunk.contextualized_content)
        metadata_values = {
            "concept_id": chunk.concept_id,
            "path": chunk.path,
            "title": chunk.title,
            "type": chunk.type,
            "description": chunk.description,
            "requirement_id": chunk.requirement_id or "",
            "resource": chunk.resource or "",
            "source_path": chunk.source_path or "",
            "tags": " ".join(chunk.tags),
            "linked_concept_ids": " ".join(chunk.linked_concept_ids),
        }
        for field, value in metadata_values.items():
            normalized = _norm(value)
            if normalized and q_norm == normalized:
                score += 50
                reasons.append(f"exact {field}")
            elif normalized and q_norm in normalized:
                score += 18
                reasons.append(f"metadata {field}")

        for token in sorted(q_tokens):
            if len(token) < 2:
                continue
            occurrences = searchable.count(token)
            if occurrences:
                score += min(occurrences, 8)
        if q_norm and q_norm in searchable:
            score += 12
            reasons.append("phrase")
        if not reasons and score > 0:
            reasons.append("token match")
        return score, reasons
