"""Parse OKF concepts into deterministic local RAG chunks."""

from __future__ import annotations

import hashlib
import re
from collections import Counter
from pathlib import Path
from urllib.parse import unquote

from okf_mcp.okf import OKFBundle, OKFDocument
from okf_mcp.rag.corpus import OKFRagCorpus
from okf_mcp.rag.models import OKFChunkingReport, OKFChunkingResult, OKFChunkRecord

_LINK_RE = re.compile(r"(?<!!)\[([^\]]*)\]\(([^)]+)\)")
_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
_TOKEN_RE = re.compile(r"[\wА-Яа-яЁё-]+", re.UNICODE)


def _sha256_text(text: str) -> str:
    return f"sha256:{hashlib.sha256(text.encode('utf-8')).hexdigest()}"


def _normalize_link(raw: str) -> str:
    target = raw.strip().split()[0]
    target = target.split("#", 1)[0]
    target = target.split("?", 1)[0]
    return unquote(target)


def _is_external(target: str) -> bool:
    lowered = target.lower()
    return (
        not target
        or lowered.startswith(("http://", "https://", "mailto:", "tel:", "urn:"))
        or target.startswith("#")
    )


def _token_count(text: str) -> int:
    return max(1, len(_TOKEN_RE.findall(text)))


def _body_start_line(lines: list[str]) -> int:
    if not lines or lines[0].strip() != "---":
        return 1
    for index, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            first_body = index + 2
            if len(lines) >= first_body and lines[first_body - 1].strip() == "":
                first_body += 1
            return first_body
    return 1


def _slug(value: str) -> str:
    slug = re.sub(r"[^\wА-Яа-яЁё.-]+", "-", value.lower(), flags=re.UNICODE).strip("-")
    return slug or "section"


class OKFConceptParser:
    """Create searchable chunks from OKF concept files.

    The parser keeps OKF concepts as the primary unit and splits by Markdown
    headings. Frontmatter is injected into contextualized content so retrieval
    can match type/title/tags even when the body section is small.
    """

    def __init__(self, bundle_dir: str | Path) -> None:
        self.bundle = OKFBundle(bundle_dir)

    def parse(self, correlation_id: str = "okf-rag") -> OKFChunkingResult:
        inventory = OKFRagCorpus(self.bundle.root).inspect(correlation_id)
        id_by_path = {path.resolve(): self.bundle.path_to_concept_id(path) for path in self.bundle.iter_concepts()}
        chunks: list[OKFChunkRecord] = []
        unresolved_links: list[str] = []

        for path in self.bundle.iter_concepts():
            raw_text = path.read_text(encoding="utf-8")
            lines = raw_text.splitlines()
            body_start_line = _body_start_line(lines)
            doc = OKFDocument.parse(raw_text)
            concept_id = self.bundle.path_to_concept_id(path)
            document = next(item for item in inventory.documents if item.concept_id == concept_id)
            sections = self._sections(doc.body, body_start_line)
            for ordinal, section in enumerate(sections):
                content, heading_path, line_start, line_end = section
                internal_links, linked_concepts, unresolved = self._links(path, content, id_by_path)
                unresolved_links.extend(f"{concept_id}:{item}" for item in unresolved)
                context_parts = [
                    f"Concept ID: {concept_id}",
                    f"Type: {document.type}",
                    f"Status: {document.status}",
                    f"Title: {document.title}",
                ]
                if document.description:
                    context_parts.append(f"Description: {document.description}")
                if document.tags:
                    context_parts.append("Tags: " + ", ".join(document.tags))
                if document.requirement_id:
                    context_parts.append(f"Requirement ID: {document.requirement_id}")
                if heading_path:
                    context_parts.append("Heading: " + " > ".join(heading_path))
                contextualized = "\n".join(context_parts) + "\n\n" + content.strip()
                digest = _sha256_text(content)
                chunk_identity = f"{concept_id}\0{ordinal}\0{line_start}\0{line_end}\0{digest}"
                chunks.append(
                    OKFChunkRecord(
                        chunk_id=_sha256_text(chunk_identity),
                        concept_id=concept_id,
                        path=f"{concept_id}.md",
                        type=document.type,
                        status=document.status,
                        title=document.title,
                        description=document.description,
                        tags=document.tags,
                        requirement_id=document.requirement_id,
                        resource=document.resource,
                        source_path=document.source_path,
                        heading_path=heading_path,
                        anchor=_slug(heading_path[-1]) if heading_path else "",
                        line_start=line_start,
                        line_end=line_end,
                        content=content.strip(),
                        contextualized_content=contextualized,
                        internal_links=tuple(internal_links),
                        linked_concept_ids=tuple(linked_concepts),
                        token_count=_token_count(contextualized),
                        content_digest=digest,
                    )
                )

        chunk_ids = [chunk.chunk_id for chunk in chunks]
        duplicates = tuple(sorted(chunk_id for chunk_id, count in Counter(chunk_ids).items() if count > 1))
        report = OKFChunkingReport(
            corpus_digest=inventory.corpus_digest,
            concept_count=inventory.concept_count,
            chunk_count=len(chunks),
            unresolved_links=tuple(sorted(unresolved_links)),
            duplicate_chunk_ids=duplicates,
        )
        return OKFChunkingResult(inventory=inventory, chunks=tuple(chunks), report=report)

    def _sections(self, body: str, body_start_line: int) -> list[tuple[str, tuple[str, ...], int, int]]:
        lines = body.splitlines()
        if not lines:
            return [("", (), body_start_line, body_start_line)]

        headings: list[tuple[int, int, str]] = []
        for offset, line in enumerate(lines):
            match = _HEADING_RE.match(line)
            if match:
                headings.append((offset, len(match.group(1)), match.group(2).strip()))

        if not headings:
            return [(body.strip(), (), body_start_line, body_start_line + max(0, len(lines) - 1))]

        sections: list[tuple[str, tuple[str, ...], int, int]] = []
        heading_stack: list[tuple[int, str]] = []
        for index, (offset, level, title) in enumerate(headings):
            while heading_stack and heading_stack[-1][0] >= level:
                heading_stack.pop()
            heading_stack.append((level, title))
            next_offset = headings[index + 1][0] if index + 1 < len(headings) else len(lines)
            section_lines = lines[offset:next_offset]
            content = "\n".join(section_lines).strip()
            if content:
                sections.append(
                    (
                        content,
                        tuple(item[1] for item in heading_stack),
                        body_start_line + offset,
                        body_start_line + next_offset - 1,
                    )
                )
        return sections or [(body.strip(), (), body_start_line, body_start_line + max(0, len(lines) - 1))]

    def _links(
        self,
        source: Path,
        content: str,
        id_by_path: dict[Path, str],
    ) -> tuple[list[str], list[str], list[str]]:
        internal: list[str] = []
        linked: list[str] = []
        unresolved: list[str] = []
        for match in _LINK_RE.finditer(content):
            raw = match.group(2)
            target = _normalize_link(raw)
            if _is_external(target) or not target.endswith(".md"):
                continue
            resolved = self.bundle._resolve_link(source, target)  # OKFBundle owns path safety.
            try:
                resolved.relative_to(self.bundle.root)
            except ValueError:
                continue
            internal.append(raw)
            concept_id = id_by_path.get(resolved)
            if concept_id:
                linked.append(concept_id)
            else:
                unresolved.append(raw)
        return internal, sorted(set(linked)), unresolved
