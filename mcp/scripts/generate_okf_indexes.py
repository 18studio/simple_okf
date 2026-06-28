#!/usr/bin/env python3
"""Generate OKF `index.md` files for every directory in a bundle."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Allow running this file directly from the repository checkout.
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from mcp.okf import OKFBundle, OKFError  # noqa: E402


def generate(bundle: Path) -> int:
    try:
        result = OKFBundle(bundle).generate_indexes()
    except OKFError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    print(f"Generated {result['count']} index file(s) under {result['bundle']}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate OKF index.md files")
    parser.add_argument("bundle", nargs="?", default="okf")
    args = parser.parse_args()
    return generate(Path(args.bundle))


if __name__ == "__main__":
    raise SystemExit(main())
