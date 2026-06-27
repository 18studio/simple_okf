#!/usr/bin/env python3
"""Export canonical Markdown documents into OKF Source Document concepts.

This script is intentionally conservative: it writes derived concepts under
`<bundle>/documents/` and does not delete existing files.
"""

from __future__ import annotations

import argparse
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable


def slugify(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9а-яё]+", "-", value, flags=re.IGNORECASE)
    value = value.strip("-")
    return value or "document"


def first_heading(text: str, fallback: str) -> str:
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            return stripped.lstrip("#").strip() or fallback
    return fallback


def iter_source_docs(source: Path) -> Iterable[Path]:
    for path in sorted(source.rglob("*.md")):
        if any(part.startswith(".") for part in path.relative_to(source).parts):
            continue
        yield path


def yaml_scalar(value: str) -> str:
    escaped = value.replace('"', '\\"')
    return f'"{escaped}"'


def render_concept(source_root: Path, source_file: Path, project_root: Path) -> str:
    text = source_file.read_text(encoding="utf-8")
    rel_source = source_file.relative_to(project_root).as_posix()
    title = first_heading(text, source_file.stem.replace("_", " ").replace("-", " ").title())
    timestamp = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

    return f"""---
type: Source Document
title: {yaml_scalar(title)}
description: {yaml_scalar('Canonical source document exported to OKF.')}
resource: {rel_source}
tags: [source-document]
timestamp: {timestamp}
source_path: {rel_source}
owner_document: {source_file.name}
---

# Overview

This concept represents the canonical source document `{rel_source}`.

# Source

Canonical source: [{rel_source}](../../../{rel_source})

# Extracted body

{text.rstrip()}
"""


def export(source: Path, out: Path, force: bool) -> int:
    project_root = Path.cwd().resolve()
    source = source.resolve()
    out = out.resolve()
    documents = out / "documents"
    documents.mkdir(parents=True, exist_ok=True)

    if not source.exists() or not source.is_dir():
        print(f"ERROR: source directory does not exist: {source}", file=sys.stderr)
        return 2

    written = 0
    skipped = 0
    for source_file in iter_source_docs(source):
        rel = source_file.relative_to(source)
        stem = slugify(rel.with_suffix("").as_posix())
        target = documents / f"{stem}.md"
        if target.exists() and not force:
            skipped += 1
            continue
        target.write_text(render_concept(source, source_file, project_root), encoding="utf-8")
        written += 1

    print(f"Exported {written} document concept(s) to {documents}")
    if skipped:
        print(f"Skipped {skipped} existing file(s). Use --force to overwrite.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Export Markdown docs into OKF Source Document concepts")
    parser.add_argument("--source", default="system", help="Canonical Markdown source directory")
    parser.add_argument("--out", default="okf", help="OKF bundle output directory")
    parser.add_argument("--force", action="store_true", help="Overwrite existing generated concepts")
    args = parser.parse_args()
    return export(Path(args.source), Path(args.out), args.force)


if __name__ == "__main__":
    raise SystemExit(main())
