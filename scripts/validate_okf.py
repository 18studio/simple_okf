#!/usr/bin/env python3
"""Validate an OKF bundle.

Checks:
- concept Markdown files have YAML frontmatter;
- every concept has `type`;
- recommended fields are reported when missing;
- internal Markdown links to `.md` files resolve;
- duplicate `requirement_id` values are reported.

`index.md` and `log.md` are treated as non-concept support files.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

SUPPORT_FILES = {"index.md", "log.md"}
RECOMMENDED_KEYS = ("title", "description", "timestamp")
LINK_RE = re.compile(r"(?<!!)\[[^\]]*\]\(([^)]+)\)")


def iter_markdown(bundle: Path) -> Iterable[Path]:
    for path in sorted(bundle.rglob("*.md")):
        if any(part.startswith(".") for part in path.relative_to(bundle).parts):
            continue
        yield path


def is_concept(path: Path) -> bool:
    return path.name not in SUPPORT_FILES


def parse_frontmatter(text: str) -> Tuple[Dict[str, str], str | None]:
    if not text.startswith("---\n") and not text.startswith("---\r\n"):
        return {}, "missing YAML frontmatter"

    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}, "missing YAML frontmatter"

    end = None
    for i, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            end = i
            break

    if end is None:
        return {}, "unterminated YAML frontmatter"

    data: Dict[str, str] = {}
    for raw in lines[1:end]:
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        if raw.startswith(" ") or raw.startswith("-"):
            # Continuation/list item for the previous key. This validator only
            # needs top-level key presence.
            continue
        if ":" not in raw:
            continue
        key, value = raw.split(":", 1)
        key = key.strip()
        if key:
            data[key] = value.strip()

    return data, None


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


def resolve_internal_link(bundle: Path, source: Path, target: str) -> Path:
    if target.startswith("/"):
        return (bundle / target.lstrip("/")).resolve()
    return (source.parent / target).resolve()


def validate(bundle: Path) -> int:
    bundle = bundle.resolve()
    errors: List[str] = []
    warnings: List[str] = []
    requirement_ids: Dict[str, Path] = {}
    concept_count = 0

    if not bundle.exists() or not bundle.is_dir():
        print(f"ERROR: bundle directory does not exist: {bundle}", file=sys.stderr)
        return 2

    for path in iter_markdown(bundle):
        rel = path.relative_to(bundle)
        text = path.read_text(encoding="utf-8")

        if is_concept(path):
            concept_count += 1
            fm, err = parse_frontmatter(text)
            if err:
                errors.append(f"{rel}: {err}")
                fm = {}
            if "type" not in fm:
                errors.append(f"{rel}: missing required frontmatter key `type`")
            for key in RECOMMENDED_KEYS:
                if key not in fm:
                    warnings.append(f"{rel}: missing recommended frontmatter key `{key}`")
            req_id = fm.get("requirement_id")
            if req_id:
                if req_id in requirement_ids:
                    errors.append(
                        f"{rel}: duplicate requirement_id `{req_id}` also used by "
                        f"{requirement_ids[req_id].relative_to(bundle)}`"
                    )
                else:
                    requirement_ids[req_id] = path

        for match in LINK_RE.finditer(text):
            target = normalize_link(match.group(1))
            if is_external(target):
                continue
            if not target.endswith(".md"):
                continue
            resolved = resolve_internal_link(bundle, path, target)
            try:
                resolved.relative_to(bundle)
            except ValueError:
                # Links to canonical source docs outside the bundle are allowed.
                continue
            if not resolved.exists():
                errors.append(f"{rel}: broken link `{match.group(1)}`")

    for warning in warnings:
        print(f"WARNING: {warning}")
    for error in errors:
        print(f"ERROR: {error}", file=sys.stderr)

    print(
        f"Validated {concept_count} concept file(s) in {bundle.relative_to(Path.cwd()) if bundle.is_relative_to(Path.cwd()) else bundle}."
    )

    if errors:
        print(f"FAILED: {len(errors)} error(s), {len(warnings)} warning(s).", file=sys.stderr)
        return 1
    print(f"OK: 0 error(s), {len(warnings)} warning(s).")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate an OKF bundle")
    parser.add_argument("bundle", nargs="?", default="okf/platform-system")
    args = parser.parse_args()
    return validate(Path(args.bundle))


if __name__ == "__main__":
    raise SystemExit(main())
