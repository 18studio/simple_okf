"""OKF bundle inventory for local RAG."""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from mcp.okf import OKFBundle, OKFDocument
from mcp.rag.models import OKFConceptDocument, OKFCorpusInventory


def _sha256_bytes(content: bytes) -> str:
    return f"sha256:{hashlib.sha256(content).hexdigest()}"


def _tags(value: Any) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        return (value,)
    if isinstance(value, (list, tuple, set)):
        return tuple(str(item) for item in value)
    return (str(value),)


class OKFRagCorpus:
    """Inspect an OKF bundle as a RAG corpus."""

    def __init__(self, bundle_dir: str | Path) -> None:
        self.bundle = OKFBundle(bundle_dir)

    def inspect(self, correlation_id: str) -> OKFCorpusInventory:
        self.bundle.ensure_exists()
        documents: list[OKFConceptDocument] = []
        corpus_hasher = hashlib.sha256()

        for path in self.bundle.iter_concepts():
            raw = path.read_bytes()
            text = raw.decode("utf-8")
            doc = OKFDocument.parse(text)
            fm = doc.frontmatter
            concept_id = self.bundle.path_to_concept_id(path)
            rel_path = path.relative_to(self.bundle.root).as_posix()
            digest = _sha256_bytes(raw)
            stat = path.stat()
            document = OKFConceptDocument(
                concept_id=concept_id,
                path=rel_path,
                type=str(fm.get("type") or ""),
                title=str(fm.get("title") or path.stem),
                description=str(fm.get("description") or ""),
                tags=_tags(fm.get("tags")),
                requirement_id=str(fm["requirement_id"]) if fm.get("requirement_id") else None,
                resource=str(fm["resource"]) if fm.get("resource") else None,
                source_path=str(fm["source_path"]) if fm.get("source_path") else None,
                size_bytes=len(raw),
                modified_at=datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc),
                content_digest=digest,
                frontmatter=dict(fm),
            )
            documents.append(document)
            corpus_hasher.update(concept_id.encode("utf-8"))
            corpus_hasher.update(b"\0")
            corpus_hasher.update(digest.encode("utf-8"))
            corpus_hasher.update(b"\0")

        return OKFCorpusInventory(
            correlation_id=correlation_id,
            bundle_root=str(self.bundle.root),
            concept_count=len(documents),
            total_bytes=sum(document.size_bytes for document in documents),
            corpus_digest=f"sha256:{corpus_hasher.hexdigest()}",
            documents=tuple(documents),
        )
