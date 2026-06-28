#!/usr/bin/env python3
"""Export canonical Markdown documents into OKF Source Document concepts."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Allow running this file directly from the repository checkout.
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from mcp.okf import OKFBundle, OKFError  # noqa: E402


def export(source: Path, out: Path, force: bool) -> int:
    try:
        result = OKFBundle(out).export_source_documents(source, force=force, project_root=Path.cwd())
    except OKFError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    print(f"Exported {result['written_count']} document concept(s) to {Path(result['bundle']) / 'documents'}")
    if result["skipped_count"]:
        print(f"Skipped {result['skipped_count']} existing file(s). Use --force to overwrite.")
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
