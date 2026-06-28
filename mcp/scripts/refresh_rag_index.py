#!/usr/bin/env python3
"""Refresh the local JSON OKF RAG index artifact configured by mcp/rag/.env."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from mcp.rag import LocalOKFRetriever, RagConfigError, load_settings  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Refresh local OKF RAG index")
    parser.add_argument("--env", default=None, help="Path to mcp/rag/.env file")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON")
    args = parser.parse_args()
    try:
        settings = load_settings(Path(args.env) if args.env else None)
        payload = LocalOKFRetriever(settings.bundle_dir).refresh_index(settings.artifacts_dir)
    except (RagConfigError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(payload, ensure_ascii=False, indent=2 if args.pretty else None))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
