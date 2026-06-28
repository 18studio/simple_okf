#!/usr/bin/env python3
"""Inspect the OKF RAG corpus configured by mcp/rag/.env."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from uuid import uuid4

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from mcp.rag import OKFRagCorpus, RagConfigError, load_settings  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Inspect OKF RAG corpus")
    parser.add_argument("--env", default=None, help="Path to mcp/rag/.env file")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON")
    args = parser.parse_args()
    try:
        settings = load_settings(Path(args.env) if args.env else None)
        inventory = OKFRagCorpus(settings.bundle_dir).inspect(str(uuid4()))
    except RagConfigError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    payload = {
        "env_file": str(settings.env_file),
        "artifacts_dir": str(settings.artifacts_dir),
        **inventory.to_dict(),
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2 if args.pretty else None))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
