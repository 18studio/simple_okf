from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import yaml

SUPPORT_FILES = {"index.md", "log.md"}
RECOMMENDED_KEYS = ("title", "description", "timestamp")
_FRONTMATTER_DELIM = "---"
_CONCEPT_SEGMENT_RE = re.compile(r"[A-Za-z0-9_][A-Za-z0-9_.-]*")
_LINK_RE = re.compile(r"(?<!!)\[([^\]]*)\]\(([^)]+)\)")


class OKFError(ValueError):
    """Raised when an OKF operation cannot be completed."""


@dataclass
class OKFDocument:
    frontmatter: dict[str, Any] = field(default_factory=dict)
    body: str = ""

    @classmethod
    def parse(cls, text: str) -> "OKFDocument":
        lines = text.splitlines()
        if not lines or lines[0].strip() != _FRONTMATTER_DELIM:
            return cls(frontmatter={}, body=text)

        end_idx: int | None = None
        for i, line in enumerate(lines[1:], start=1):
            if line.strip() == _FRONTMATTER_DELIM:
                end_idx = i
                break
        if end_idx is None:
            raise OKFError("Unterminated YAML frontmatter block")

        fm_text = "\n".join(lines[1:end_idx])
        try:
            fm = yaml.safe_load(fm_text) or {}
        except yaml.YAMLError as exc:
            raise OKFError(f"Invalid YAML in frontmatter: {exc}") from exc
        if not isinstance(fm, dict):
            raise OKFError("Frontmatter must be a YAML mapping")

        body = "\n".join(lines[end_idx + 1 :])
        if body.startswith("\n"):
            body = body[1:]
        return cls(frontmatter=dict(fm), body=body)

    def serialize(self) -> str:
        fm_text = yaml.safe_dump(
            self.frontmatter,
            sort_keys=False,
            allow_unicode=True,
            default_flow_style=False,
        ).rstrip()
        body = self.body if self.body.endswith("\n") else self.body + "\n"
        return f"{_FRONTMATTER_DELIM}\n{fm_text}\n{_FRONTMATTER_DELIM}\n\n{body}"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _normalize_link(raw: str) -> str:
    target = raw.strip().split()[0]
    target = target.split("#", 1)[0]
    target = target.split("?", 1)[0]
    return target


def _is_external_link(target: str) -> bool:
    lowered = target.lower()
    return (
        not target
        or lowered.startswith(("http://", "https://", "mailto:", "tel:", "urn:"))
        or target.startswith("#")
    )


def _jsonable(value: Any) -> Any:
    try:
        json.dumps(value, ensure_ascii=False)
        return value
    except TypeError:
        if isinstance(value, (datetime,)):
            return value.isoformat()
        if isinstance(value, Path):
            return value.as_posix()
        return str(value)


def _safe_frontmatter(frontmatter: dict[str, Any]) -> dict[str, Any]:
    return {str(k): _jsonable(v) for k, v in frontmatter.items()}


def _snippet(text: str, limit: int = 280) -> str:
    compact = " ".join(part.strip() for part in text.split())
    if len(compact) <= limit:
        return compact
    return compact[:limit].rstrip() + "…"


def _title_from_filename(path: Path) -> str:
    return path.stem.replace("-", " ").replace("_", " ").title()


def _dir_title(path: Path, bundle: Path) -> str:
    if path == bundle:
        return "OKF Bundle"
    return path.name.replace("-", " ").replace("_", " ").title()


def _slugify(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9а-яё]+", "-", value, flags=re.IGNORECASE)
    value = value.strip("-")
    return value or "document"


def _first_heading(text: str, fallback: str) -> str:
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            return stripped.lstrip("#").strip() or fallback
    return fallback


def _iter_source_docs(source: Path) -> Iterable[Path]:
    for path in sorted(source.rglob("*.md")):
        if any(part.startswith(".") for part in path.relative_to(source).parts):
            continue
        yield path


class OKFBundle:
    """Filesystem-backed OKF bundle reader/writer."""

    def __init__(self, root: str | Path):
        self.root = Path(root).expanduser().resolve()

    def ensure_exists(self) -> None:
        if not self.root.exists() or not self.root.is_dir():
            raise OKFError(f"Bundle directory does not exist: {self.root}")

    def concept_id_to_path(self, concept_id: str) -> Path:
        parts = [part for part in concept_id.strip("/").split("/") if part]
        if not parts:
            raise OKFError("concept_id must not be empty")
        for part in parts:
            if not _CONCEPT_SEGMENT_RE.fullmatch(part):
                raise OKFError(f"Invalid concept_id segment: {part!r}")
        if parts[-1].endswith(".md"):
            parts[-1] = parts[-1][:-3]
        if f"{parts[-1]}.md" in SUPPORT_FILES:
            raise OKFError("index.md and log.md are support files, not concepts")
        *dirs, name = parts
        path = self.root.joinpath(*dirs, f"{name}.md").resolve()
        self._assert_inside(path)
        return path

    def support_path(self, relative_path: str) -> Path:
        rel = relative_path.strip().lstrip("/") or "index.md"
        path = (self.root / rel).resolve()
        self._assert_inside(path)
        if path.suffix != ".md" and path.name != "graph.json":
            raise OKFError("Only Markdown support files and graph.json can be read")
        return path

    def path_to_concept_id(self, path: Path) -> str:
        return path.resolve().relative_to(self.root).with_suffix("").as_posix()

    def _assert_inside(self, path: Path) -> None:
        try:
            path.relative_to(self.root)
        except ValueError as exc:
            raise OKFError(f"Path escapes bundle root: {path}") from exc

    def iter_markdown(self, *, include_support: bool = True) -> Iterable[Path]:
        self.ensure_exists()
        for path in sorted(self.root.rglob("*.md")):
            rel_parts = path.relative_to(self.root).parts
            if any(part.startswith(".") for part in rel_parts):
                continue
            if not include_support and path.name in SUPPORT_FILES:
                continue
            yield path

    def iter_concepts(self) -> Iterable[Path]:
        yield from self.iter_markdown(include_support=False)

    def read_document(self, concept_id: str) -> OKFDocument:
        path = self.concept_id_to_path(concept_id)
        if not path.exists():
            raise OKFError(f"Concept does not exist: {concept_id}")
        return OKFDocument.parse(path.read_text(encoding="utf-8"))

    def read_concept(self, concept_id: str, *, include_body: bool = True) -> dict[str, Any]:
        path = self.concept_id_to_path(concept_id)
        if not path.exists():
            raise OKFError(f"Concept does not exist: {concept_id}")
        doc = OKFDocument.parse(path.read_text(encoding="utf-8"))
        result: dict[str, Any] = {
            "id": self.path_to_concept_id(path),
            "path": path.relative_to(self.root).as_posix(),
            "frontmatter": _safe_frontmatter(doc.frontmatter),
            "title": str(doc.frontmatter.get("title") or path.stem),
            "type": str(doc.frontmatter.get("type") or ""),
            "description": str(doc.frontmatter.get("description") or ""),
        }
        if include_body:
            result["body"] = doc.body
        return result

    def read_raw(self, concept_id: str) -> str:
        path = self.concept_id_to_path(concept_id)
        if not path.exists():
            raise OKFError(f"Concept does not exist: {concept_id}")
        return path.read_text(encoding="utf-8")

    def read_support_file(self, relative_path: str = "index.md") -> dict[str, Any]:
        path = self.support_path(relative_path)
        if not path.exists():
            raise OKFError(f"Support file does not exist: {relative_path}")
        return {
            "path": path.relative_to(self.root).as_posix(),
            "text": path.read_text(encoding="utf-8"),
        }

    def list_concepts(
        self,
        *,
        type_filter: str | None = None,
        tag: str | None = None,
        query: str | None = None,
        include_snippet: bool = False,
    ) -> list[dict[str, Any]]:
        q = query.lower() if query else None
        type_q = type_filter.lower() if type_filter else None
        tag_q = tag.lower() if tag else None
        out: list[dict[str, Any]] = []

        for path in self.iter_concepts():
            try:
                doc = OKFDocument.parse(path.read_text(encoding="utf-8"))
            except OKFError:
                continue
            fm = doc.frontmatter
            tags = fm.get("tags") or []
            if isinstance(tags, str):
                tags = [tags]
            tags = [str(t) for t in tags]
            typ = str(fm.get("type") or "")
            title = str(fm.get("title") or path.stem)
            desc = str(fm.get("description") or "")
            cid = self.path_to_concept_id(path)

            if type_q and typ.lower() != type_q:
                continue
            if tag_q and tag_q not in {t.lower() for t in tags}:
                continue
            haystack = "\n".join([cid, typ, title, desc, " ".join(tags), doc.body]).lower()
            if q and q not in haystack:
                continue

            item: dict[str, Any] = {
                "id": cid,
                "path": path.relative_to(self.root).as_posix(),
                "type": typ,
                "title": title,
                "description": desc,
                "tags": tags,
                "resource": fm.get("resource", ""),
            }
            if include_snippet:
                item["snippet"] = _snippet(doc.body)
            out.append(item)
        return out

    def search_concepts(self, query: str, *, limit: int = 20) -> list[dict[str, Any]]:
        if not query.strip():
            raise OKFError("query must not be empty")
        q = query.lower()
        scored: list[tuple[int, dict[str, Any]]] = []
        for item in self.list_concepts(include_snippet=True):
            doc = self.read_document(item["id"])
            score = 0
            for field, weight in (
                (item["id"], 6),
                (item.get("title", ""), 8),
                (item.get("description", ""), 5),
                (item.get("type", ""), 3),
                (" ".join(item.get("tags") or []), 4),
                (doc.body, 1),
            ):
                score += str(field).lower().count(q) * weight
            if score:
                item["score"] = score
                scored.append((score, item))
        scored.sort(key=lambda pair: (-pair[0], pair[1]["id"]))
        return [item for _, item in scored[: max(1, int(limit))]]

    def list_directory(self, directory: str = "") -> dict[str, Any]:
        self.ensure_exists()
        rel = directory.strip().strip("/")
        path = (self.root / rel).resolve() if rel else self.root
        self._assert_inside(path)
        if not path.exists() or not path.is_dir():
            raise OKFError(f"Directory does not exist: {directory}")

        dirs: list[dict[str, str]] = []
        concepts: list[dict[str, Any]] = []
        support_files: list[dict[str, str]] = []

        for child in sorted(path.iterdir()):
            if child.name.startswith("."):
                continue
            child_rel = child.relative_to(self.root).as_posix()
            if child.is_dir():
                dirs.append({"name": child.name, "path": child_rel})
            elif child.suffix == ".md" and child.name in SUPPORT_FILES:
                support_files.append({"name": child.name, "path": child_rel})
            elif child.suffix == ".md":
                try:
                    concepts.append(self.read_concept(self.path_to_concept_id(child), include_body=False))
                except OKFError:
                    concepts.append({"id": self.path_to_concept_id(child), "path": child_rel})

        return {
            "path": path.relative_to(self.root).as_posix() if path != self.root else "",
            "directories": dirs,
            "concepts": concepts,
            "support_files": support_files,
        }

    def write_concept(
        self,
        concept_id: str,
        frontmatter: dict[str, Any],
        body: str,
        *,
        overwrite: bool = True,
        merge_frontmatter: bool = True,
    ) -> dict[str, Any]:
        if not isinstance(frontmatter, dict):
            raise OKFError("frontmatter must be an object")
        if not frontmatter.get("type"):
            raise OKFError("frontmatter.type is required")
        if not isinstance(body, str):
            raise OKFError("body must be a string")

        path = self.concept_id_to_path(concept_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists() and not overwrite:
            raise OKFError(f"Concept already exists: {concept_id}")

        fm = dict(frontmatter)
        if path.exists() and merge_frontmatter:
            existing = OKFDocument.parse(path.read_text(encoding="utf-8")).frontmatter
            existing.update(fm)
            fm = existing
        fm.setdefault("timestamp", utc_now_iso())

        doc = OKFDocument(frontmatter=fm, body=body)
        text = doc.serialize()
        path.write_text(text, encoding="utf-8")
        return {
            "id": self.path_to_concept_id(path),
            "path": path.relative_to(self.root).as_posix(),
            "bytes": len(text.encode("utf-8")),
            "frontmatter": _safe_frontmatter(fm),
        }

    def _resolve_link(self, source: Path, target: str) -> Path:
        if target.startswith("/"):
            return (self.root / target.lstrip("/")).resolve()
        return (source.parent / target).resolve()

    def build_graph(self) -> dict[str, Any]:
        self.ensure_exists()
        concept_paths = list(self.iter_concepts())
        id_by_path = {path.resolve(): self.path_to_concept_id(path) for path in concept_paths}
        nodes: list[dict[str, Any]] = []
        edges: list[dict[str, Any]] = []

        for path in concept_paths:
            text = path.read_text(encoding="utf-8")
            try:
                doc = OKFDocument.parse(text)
            except OKFError:
                doc = OKFDocument()
            fm = doc.frontmatter
            node = {
                "id": self.path_to_concept_id(path),
                "path": path.relative_to(self.root).as_posix(),
                "type": fm.get("type", ""),
                "title": fm.get("title", path.stem),
                "description": fm.get("description", ""),
                "tags": fm.get("tags", []),
                "resource": fm.get("resource", ""),
            }
            nodes.append(_safe_frontmatter(node))

            for match in _LINK_RE.finditer(text):
                label = match.group(1)
                raw_target = match.group(2)
                target = _normalize_link(raw_target)
                if _is_external_link(target) or not target.endswith(".md"):
                    continue
                resolved = self._resolve_link(path, target)
                target_id = id_by_path.get(resolved)
                if not target_id:
                    continue
                edges.append(
                    {
                        "source": node["id"],
                        "target": target_id,
                        "label": label,
                        "href": raw_target,
                        "line": text.count("\n", 0, match.start()) + 1,
                    }
                )

        return {
            "bundle": str(self.root),
            "node_count": len(nodes),
            "edge_count": len(edges),
            "nodes": nodes,
            "edges": edges,
        }

    def write_graph(self, out_path: str | Path = "graph.json") -> dict[str, Any]:
        graph = self.build_graph()
        out = Path(out_path)
        if not out.is_absolute():
            out = self.root / out
        out = out.resolve()
        self._assert_inside(out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(graph, ensure_ascii=False) + "\n", encoding="utf-8")
        return {"path": out.relative_to(self.root).as_posix(), **graph}

    def _render_index(self, directory: Path) -> str:
        lines: list[str] = [f"# {_dir_title(directory, self.root)}", ""]

        dirs = [p for p in sorted(directory.iterdir()) if p.is_dir() and not p.name.startswith(".")]
        if dirs:
            lines.append("## Directories")
            lines.append("")
            for child in dirs:
                lines.append(f"* [{_dir_title(child, self.root)}]({child.name}/index.md)")
            lines.append("")

        grouped: dict[str, list[tuple[Path, dict[str, Any]]]] = {}
        for file in sorted(directory.iterdir()):
            if not (file.is_file() and file.suffix == ".md" and file.name not in SUPPORT_FILES):
                continue
            try:
                fm = OKFDocument.parse(file.read_text(encoding="utf-8")).frontmatter
            except OKFError:
                fm = {}
            grouped.setdefault(str(fm.get("type") or "Concept"), []).append((file, fm))

        for type_name in sorted(grouped):
            lines.append(f"## {type_name}")
            lines.append("")
            for file, fm in sorted(grouped[type_name], key=lambda item: item[0].name):
                title = str(fm.get("title") or _title_from_filename(file))
                description = str(fm.get("description") or "")
                suffix = f" - {description}" if description else ""
                lines.append(f"* [{title}]({file.name}){suffix}")
            lines.append("")

        if len(lines) == 2:
            lines.append("No concepts yet.")
            lines.append("")

        return "\n".join(lines).rstrip() + "\n"

    def generate_indexes(self) -> dict[str, Any]:
        """Regenerate index.md files for every directory in the bundle."""
        self.ensure_exists()
        directories = [self.root] + sorted(p for p in self.root.rglob("*") if p.is_dir())
        written: list[str] = []
        for directory in directories:
            if any(part.startswith(".") for part in directory.relative_to(self.root).parts):
                continue
            index_path = directory / "index.md"
            index_path.write_text(self._render_index(directory), encoding="utf-8")
            written.append(index_path.relative_to(self.root).as_posix())
        return {"bundle": str(self.root), "count": len(written), "written": written}

    def export_source_documents(
        self,
        source: str | Path = "system",
        *,
        force: bool = False,
        project_root: str | Path | None = None,
    ) -> dict[str, Any]:
        """Export Markdown source files as Source Document concepts."""
        root = Path(project_root).resolve() if project_root else Path.cwd().resolve()
        source_path = Path(source)
        if not source_path.is_absolute():
            source_path = root / source_path
        source_path = source_path.resolve()
        if not source_path.exists() or not source_path.is_dir():
            raise OKFError(f"Source directory does not exist: {source_path}")

        documents = self.root / "documents"
        documents.mkdir(parents=True, exist_ok=True)
        written: list[str] = []
        skipped: list[str] = []

        for source_file in _iter_source_docs(source_path):
            rel = source_file.relative_to(source_path)
            concept_id = f"documents/{_slugify(rel.with_suffix('').as_posix())}"
            target = self.concept_id_to_path(concept_id)
            if target.exists() and not force:
                skipped.append(target.relative_to(self.root).as_posix())
                continue

            text = source_file.read_text(encoding="utf-8")
            try:
                rel_source = source_file.relative_to(root).as_posix()
            except ValueError:
                rel_source = source_file.as_posix()
            title = _first_heading(text, _title_from_filename(source_file))
            body = (
                f"# Overview\n\n"
                f"This concept represents the canonical source document `{rel_source}`.\n\n"
                f"# Source\n\n"
                f"Canonical source: [{rel_source}](../../../{rel_source})\n\n"
                f"# Extracted body\n\n"
                f"{text.rstrip()}\n"
            )
            self.write_concept(
                concept_id,
                {
                    "type": "Source Document",
                    "title": title,
                    "description": "Canonical source document exported to OKF.",
                    "resource": rel_source,
                    "tags": ["source-document"],
                    "timestamp": utc_now_iso(),
                    "source_path": rel_source,
                    "owner_document": source_file.name,
                },
                body,
                overwrite=True,
                merge_frontmatter=False,
            )
            written.append(target.relative_to(self.root).as_posix())

        return {
            "bundle": str(self.root),
            "source": str(source_path),
            "written_count": len(written),
            "skipped_count": len(skipped),
            "written": written,
            "skipped": skipped,
        }

    def validate(self) -> dict[str, Any]:
        self.ensure_exists()
        errors: list[str] = []
        warnings: list[str] = []
        requirement_ids: dict[str, Path] = {}
        concept_count = 0

        for path in self.iter_markdown(include_support=True):
            rel = path.relative_to(self.root).as_posix()
            text = path.read_text(encoding="utf-8")
            doc: OKFDocument | None = None

            if path.name not in SUPPORT_FILES:
                concept_count += 1
                try:
                    doc = OKFDocument.parse(text)
                except OKFError as exc:
                    errors.append(f"{rel}: {exc}")
                    doc = OKFDocument()
                if "type" not in doc.frontmatter:
                    errors.append(f"{rel}: missing required frontmatter key `type`")
                for key in RECOMMENDED_KEYS:
                    if key not in doc.frontmatter:
                        warnings.append(f"{rel}: missing recommended frontmatter key `{key}`")
                req_id = doc.frontmatter.get("requirement_id")
                if req_id:
                    req_id = str(req_id)
                    if req_id in requirement_ids:
                        errors.append(
                            f"{rel}: duplicate requirement_id `{req_id}` also used by "
                            f"{requirement_ids[req_id].relative_to(self.root).as_posix()}`"
                        )
                    else:
                        requirement_ids[req_id] = path

            for match in _LINK_RE.finditer(text):
                target = _normalize_link(match.group(2))
                if _is_external_link(target) or not target.endswith(".md"):
                    continue
                resolved = self._resolve_link(path, target)
                try:
                    resolved.relative_to(self.root)
                except ValueError:
                    continue
                if not resolved.exists():
                    errors.append(f"{rel}: broken link `{match.group(2)}`")

        return {
            "bundle": str(self.root),
            "concept_count": concept_count,
            "errors": errors,
            "warnings": warnings,
            "ok": not errors,
        }
