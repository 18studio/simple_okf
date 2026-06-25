#!/usr/bin/env python3
"""Generate a JSON graph from an OKF bundle.

Nodes are concept Markdown files. Edges are internal Markdown links from one
concept to another existing concept.

Reserved support files (`index.md`, `log.md`) are not graph nodes.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

SUPPORT_FILES = {"index.md", "log.md"}
LINK_RE = re.compile(r"(?<!!)\[([^\]]+)\]\(([^)]+)\)")


def iter_concepts(bundle: Path) -> Iterable[Path]:
    for path in sorted(bundle.rglob("*.md")):
        rel_parts = path.relative_to(bundle).parts
        if any(part.startswith(".") for part in rel_parts):
            continue
        if path.name in SUPPORT_FILES:
            continue
        yield path


def concept_id(bundle: Path, path: Path) -> str:
    return path.relative_to(bundle).with_suffix("").as_posix()


def parse_frontmatter(text: str) -> Tuple[Dict[str, object], str]:
    if not text.startswith("---"):
        return {}, text

    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}, text

    end = None
    for i, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            end = i
            break

    if end is None:
        return {}, text

    data: Dict[str, object] = {}
    current_key: str | None = None

    for raw in lines[1:end]:
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue

        stripped = raw.strip()
        if stripped.startswith("-") and current_key:
            value = stripped[1:].strip().strip('"\'')
            existing = data.get(current_key)
            if not isinstance(existing, list):
                existing = []
                data[current_key] = existing
            existing.append(value)
            continue

        if ":" not in raw or raw.startswith(" "):
            continue

        key, value = raw.split(":", 1)
        key = key.strip()
        value = value.strip()
        current_key = key

        if value.startswith("[") and value.endswith("]"):
            inner = value[1:-1].strip()
            data[key] = [item.strip().strip('"\'') for item in inner.split(",") if item.strip()]
        elif value == "":
            data[key] = []
        else:
            data[key] = value.strip('"\'')

    body = "\n".join(lines[end + 1 :])
    return data, body


def normalize_link(raw: str) -> str:
    target = raw.strip().split()[0]
    target = target.split("#", 1)[0]
    target = target.split("?", 1)[0]
    return target


def is_external(target: str) -> bool:
    lowered = target.lower()
    return (
        not target
        or lowered.startswith(("http://", "https://", "mailto:", "tel:", "urn:"))
        or target.startswith("#")
    )


def resolve_link(bundle: Path, source: Path, target: str) -> Path:
    if target.startswith("/"):
        return (bundle / target.lstrip("/")).resolve()
    return (source.parent / target).resolve()


def line_number(text: str, offset: int) -> int:
    return text.count("\n", 0, offset) + 1


def build_graph(bundle: Path) -> Dict[str, object]:
    bundle = bundle.resolve()
    concept_paths = list(iter_concepts(bundle))
    id_by_path = {path.resolve(): concept_id(bundle, path) for path in concept_paths}

    nodes: List[Dict[str, object]] = []
    edges: List[Dict[str, object]] = []

    for path in concept_paths:
        text = path.read_text(encoding="utf-8")
        frontmatter, _body = parse_frontmatter(text)
        node = {
            "id": concept_id(bundle, path),
            "path": path.relative_to(bundle).as_posix(),
            "type": frontmatter.get("type", ""),
            "title": frontmatter.get("title", path.stem),
            "description": frontmatter.get("description", ""),
            "tags": frontmatter.get("tags", []),
            "resource": frontmatter.get("resource", ""),
        }
        nodes.append(node)

        for match in LINK_RE.finditer(text):
            label = match.group(1)
            raw_target = match.group(2)
            target = normalize_link(raw_target)
            if is_external(target) or not target.endswith(".md"):
                continue

            resolved = resolve_link(bundle, path, target)
            target_id = id_by_path.get(resolved)
            if not target_id:
                continue

            edges.append(
                {
                    "source": node["id"],
                    "target": target_id,
                    "label": label,
                    "href": raw_target,
                    "line": line_number(text, match.start()),
                }
            )

    return {
        "bundle": str(bundle),
        "node_count": len(nodes),
        "edge_count": len(edges),
        "nodes": nodes,
        "edges": edges,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate OKF graph JSON from Markdown links")
    parser.add_argument("bundle", nargs="?", default="okf/platform-system")
    parser.add_argument("--out", help="Output JSON file. Defaults to stdout.")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON output")
    args = parser.parse_args()

    bundle = Path(args.bundle)
    if not bundle.exists() or not bundle.is_dir():
        print(f"ERROR: bundle directory does not exist: {bundle}", file=sys.stderr)
        return 2

    graph = build_graph(bundle)
    json_text = json.dumps(graph, ensure_ascii=False, indent=2 if args.pretty else None)

    if args.out:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json_text + "\n", encoding="utf-8")
        print(f"Wrote OKF graph: {out} ({graph['node_count']} nodes, {graph['edge_count']} edges)")
    else:
        print(json_text)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
