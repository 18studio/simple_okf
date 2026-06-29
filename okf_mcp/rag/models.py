"""Internal models for OKF-aware local RAG."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class OKFConceptDocument:
    concept_id: str
    path: str
    type: str
    title: str
    description: str
    tags: tuple[str, ...]
    requirement_id: str | None
    resource: str | None
    source_path: str | None
    size_bytes: int
    modified_at: datetime
    content_digest: str
    frontmatter: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["modified_at"] = self.modified_at.isoformat()
        return data


@dataclass(frozen=True)
class OKFCorpusInventory:
    correlation_id: str
    bundle_root: str
    concept_count: int
    total_bytes: int
    corpus_digest: str
    documents: tuple[OKFConceptDocument, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "correlation_id": self.correlation_id,
            "bundle_root": self.bundle_root,
            "concept_count": self.concept_count,
            "total_bytes": self.total_bytes,
            "corpus_digest": self.corpus_digest,
            "documents": [document.to_dict() for document in self.documents],
        }


@dataclass(frozen=True)
class OKFChunkRecord:
    chunk_id: str
    concept_id: str
    path: str
    type: str
    title: str
    description: str
    tags: tuple[str, ...]
    requirement_id: str | None
    resource: str | None
    source_path: str | None
    heading_path: tuple[str, ...]
    anchor: str
    line_start: int
    line_end: int
    content: str
    contextualized_content: str
    internal_links: tuple[str, ...]
    linked_concept_ids: tuple[str, ...]
    token_count: int
    content_digest: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class OKFChunkingReport:
    corpus_digest: str
    concept_count: int
    chunk_count: int
    unresolved_links: tuple[str, ...]
    duplicate_chunk_ids: tuple[str, ...]

    @property
    def is_valid(self) -> bool:
        return not self.unresolved_links and not self.duplicate_chunk_ids

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["is_valid"] = self.is_valid
        return data


@dataclass(frozen=True)
class OKFChunkingResult:
    inventory: OKFCorpusInventory
    chunks: tuple[OKFChunkRecord, ...]
    report: OKFChunkingReport

    def to_dict(self) -> dict[str, Any]:
        return {
            "inventory": self.inventory.to_dict(),
            "chunks": [chunk.to_dict() for chunk in self.chunks],
            "report": self.report.to_dict(),
        }


@dataclass(frozen=True)
class OKFRetrievalHit:
    chunk: OKFChunkRecord
    score: float
    reasons: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {"score": self.score, "reasons": list(self.reasons), **self.chunk.to_dict()}
