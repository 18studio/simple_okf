"""RAG event model and evaluation helpers."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


@dataclass(frozen=True)
class RagMetric:
    name: str
    value: float
    threshold: float
    passed: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class RagEvent:
    event_id: str
    correlation_id: str
    timestamp: str
    event_type: str
    status: str
    query: str
    retrieval_mode: str
    filters: dict[str, Any] = field(default_factory=dict)
    corpus_digest: str = ""
    retrieved: list[dict[str, Any]] = field(default_factory=list)
    citations: list[dict[str, Any]] = field(default_factory=list)
    answer: str = ""
    metrics: list[dict[str, Any]] = field(default_factory=list)
    evaluator: dict[str, Any] = field(default_factory=dict)
    timings_ms: dict[str, float] = field(default_factory=dict)
    error: str = ""
    raw: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def create(
        cls,
        *,
        event_type: str,
        status: str,
        query: str,
        retrieval_mode: str,
        correlation_id: str | None = None,
        **kwargs: Any,
    ) -> "RagEvent":
        return cls(
            event_id=str(uuid4()),
            correlation_id=correlation_id or str(uuid4()),
            timestamp=utc_now_iso(),
            event_type=event_type,
            status=status,
            query=query,
            retrieval_mode=retrieval_mode,
            **kwargs,
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_clickhouse_row(self) -> dict[str, Any]:
        data = self.to_dict()
        # ClickHouse DateTime64 JSONEachRow accepts `YYYY-MM-DD HH:MM:SS` reliably.
        data["timestamp"] = self.timestamp.replace("T", " ").replace("+00:00", "")
        for key in ("filters", "retrieved", "citations", "metrics", "evaluator", "timings_ms", "raw"):
            data[key] = json.dumps(data[key], ensure_ascii=False, sort_keys=True)
        return data


class DeterministicRagEvaluator:
    """Dependency-free evaluator that provides stable RAGAS-like metrics."""

    def __init__(self, *, threshold: float = 0.5, model: str = "deterministic-ragas-v1") -> None:
        self.threshold = threshold
        self.model = model

    def evaluate(self, *, question: str, answer: str, hits: list[dict[str, Any]], citations: list[dict[str, Any]]) -> list[RagMetric]:
        question_terms = {part.casefold() for part in question.split() if len(part) > 2}
        context_text = " ".join(str(hit.get("content", "")) for hit in hits).casefold()
        answer_text = answer.casefold()
        matched_terms = {term for term in question_terms if term in context_text}
        context_precision = min(1.0, len(hits) / max(len(hits), 1)) if hits else 0.0
        context_recall = len(matched_terms) / max(len(question_terms), 1)
        faithfulness = 1.0 if citations and answer.strip() else (0.5 if hits else 0.0)
        answer_relevancy = len({term for term in question_terms if term in answer_text}) / max(len(question_terms), 1)
        citation_coverage = len(citations) / max(len(hits), 1) if hits else 0.0
        factual_correctness = faithfulness if citations else 0.0
        values = {
            "context_precision": context_precision,
            "context_recall": context_recall,
            "faithfulness": faithfulness,
            "answer_relevancy": answer_relevancy,
            "citation_coverage": citation_coverage,
            "factual_correctness": factual_correctness,
        }
        return [
            RagMetric(name=name, value=round(value, 4), threshold=self.threshold, passed=value >= self.threshold)
            for name, value in values.items()
        ]

    def metadata(self) -> dict[str, Any]:
        return {"provider": "deterministic", "model": self.model, "threshold": self.threshold}
