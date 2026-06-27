#!/usr/bin/env python3
"""Generate JSON and optional HTML graph reports from an OKF bundle.

Nodes are concept Markdown files. Edges are internal Markdown links from one
concept to another existing concept.

Reserved support files (`index.md`, `log.md`) are not graph nodes.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Allow running this file directly from the repository checkout.
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from mcp.okf import OKFBundle, OKFError  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate OKF graph JSON/HTML from Markdown links")
    parser.add_argument("bundle", nargs="?", default="okf")
    parser.add_argument("--out", help="Output JSON file. Defaults to stdout.")
    parser.add_argument("--html-out", help="Output self-contained HTML report file.")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON output")
    args = parser.parse_args()

    bundle_path = Path(args.bundle)
    if not bundle_path.exists() or not bundle_path.is_dir():
        print(f"ERROR: bundle directory does not exist: {bundle_path}", file=sys.stderr)
        return 2

    bundle = OKFBundle(bundle_path)
    try:
        graph = bundle.build_graph()
    except OKFError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    json_text = json.dumps(graph, ensure_ascii=False, indent=2 if args.pretty else None)

    if args.out:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json_text + "\n", encoding="utf-8")
        print(f"Wrote OKF graph JSON: {out} ({graph['node_count']} nodes, {graph['edge_count']} edges)")
    elif not args.html_out:
        print(json_text)

    if args.html_out:
        html_out = Path(args.html_out)
        html_out.parent.mkdir(parents=True, exist_ok=True)
        html_out.write_text(bundle.render_graph_html(graph), encoding="utf-8")
        print(
            "Wrote OKF graph HTML: "
            f"{html_out} ({graph['node_count']} nodes, {graph['edge_count']} edges)"
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
