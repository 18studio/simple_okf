#!/usr/bin/env python3
"""Run local OKF RAG retrieval configured by mcp/rag/.env."""

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
    parser = argparse.ArgumentParser(description="Retrieve OKF RAG chunks")
    parser.add_argument("query")
    parser.add_argument("--env", default=None, help="Path to mcp/rag/.env file")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--type-filter", default=None)
    parser.add_argument("--tag", default=None)
    parser.add_argument("--answer", action="store_true", help="Return extractive answer instead of raw hits")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON")
    args = parser.parse_args()
    try:
        settings = load_settings(Path(args.env) if args.env else None)
        retriever = LocalOKFRetriever(settings.bundle_dir)
        if args.answer:
            payload = retriever.answer(args.query, limit=args.limit or settings.answer_evidence_limit)
        else:
            payload = retriever.retrieve(
                args.query,
                limit=args.limit or settings.retrieval_result_limit,
                type_filter=args.type_filter,
                tag=args.tag,
            )
    except (RagConfigError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(payload, ensure_ascii=False, indent=2 if args.pretty else None))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
