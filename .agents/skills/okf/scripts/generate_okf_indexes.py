#!/usr/bin/env python3
"""Generate OKF `index.md` files for every directory in a bundle."""

from __future__ import annotations

import argparse
from collections import defaultdict
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

SUPPORT_FILES = {"index.md", "log.md"}


def parse_frontmatter(text: str) -> Dict[str, str]:
    if not text.startswith("---"):
        return {}
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}
    end = None
    for i, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            end = i
            break
    if end is None:
        return {}
    data: Dict[str, str] = {}
    for raw in lines[1:end]:
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        if raw.startswith(" ") or raw.startswith("-"):
            continue
        if ":" not in raw:
            continue
        key, value = raw.split(":", 1)
        data[key.strip()] = value.strip().strip('"\'')
    return data


def markdown_files(directory: Path) -> Iterable[Path]:
    for path in sorted(directory.iterdir()):
        if path.is_file() and path.suffix == ".md" and path.name not in SUPPORT_FILES:
            yield path


def child_dirs(directory: Path) -> Iterable[Path]:
    for path in sorted(directory.iterdir()):
        if path.is_dir() and not path.name.startswith("."):
            yield path


def title_from_filename(path: Path) -> str:
    return path.stem.replace("-", " ").replace("_", " ").title()


def dir_title(path: Path, bundle: Path) -> str:
    if path == bundle:
        return "OKF Bundle"
    return path.name.replace("-", " ").replace("_", " ").title()


def render_index(directory: Path, bundle: Path) -> str:
    lines: List[str] = [f"# {dir_title(directory, bundle)}", ""]

    dirs = list(child_dirs(directory))
    if dirs:
        lines.append("## Directories")
        lines.append("")
        for child in dirs:
            lines.append(f"* [{dir_title(child, bundle)}]({child.name}/index.md)")
        lines.append("")

    grouped: Dict[str, List[Tuple[Path, Dict[str, str]]]] = defaultdict(list)
    for file in markdown_files(directory):
        fm = parse_frontmatter(file.read_text(encoding="utf-8"))
        grouped[fm.get("type", "Concept")].append((file, fm))

    for type_name in sorted(grouped):
        lines.append(f"## {type_name}")
        lines.append("")
        for file, fm in sorted(grouped[type_name], key=lambda item: item[0].name):
            title = fm.get("title") or title_from_filename(file)
            description = fm.get("description", "")
            suffix = f" - {description}" if description else ""
            lines.append(f"* [{title}]({file.name}){suffix}")
        lines.append("")

    if len(lines) == 2:
        lines.append("No concepts yet.")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def generate(bundle: Path) -> int:
    bundle = bundle.resolve()
    if not bundle.exists() or not bundle.is_dir():
        raise SystemExit(f"Bundle directory does not exist: {bundle}")

    count = 0
    for directory in sorted([p for p in bundle.rglob("*") if p.is_dir()] + [bundle]):
        if any(part.startswith(".") for part in directory.relative_to(bundle).parts):
            continue
        (directory / "index.md").write_text(render_index(directory, bundle), encoding="utf-8")
        count += 1

    print(f"Generated {count} index file(s) under {bundle}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate OKF index.md files")
    parser.add_argument("bundle", nargs="?", default="okf/platform-system")
    args = parser.parse_args()
    return generate(Path(args.bundle))


if __name__ == "__main__":
    raise SystemExit(main())
