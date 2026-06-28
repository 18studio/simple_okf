#!/usr/bin/env python3
"""Validate an OKF bundle."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Allow running this file directly from the repository checkout.
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from mcp.okf import OKFBundle, OKFError  # noqa: E402


def validate(bundle: Path) -> int:
    try:
        result = OKFBundle(bundle).validate()
    except OKFError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    for warning in result["warnings"]:
        print(f"WARNING: {warning}")
    for error in result["errors"]:
        print(f"ERROR: {error}", file=sys.stderr)

    bundle_display = result["bundle"]
    try:
        bundle_display = str(Path(bundle_display).relative_to(Path.cwd()))
    except ValueError:
        pass

    print(f"Validated {result['concept_count']} concept file(s) in {bundle_display}.")
    if result["errors"]:
        print(
            f"FAILED: {len(result['errors'])} error(s), {len(result['warnings'])} warning(s).",
            file=sys.stderr,
        )
        return 1

    print(f"OK: 0 error(s), {len(result['warnings'])} warning(s).")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate an OKF bundle")
    parser.add_argument("bundle", nargs="?", default="okf")
    args = parser.parse_args()
    return validate(Path(args.bundle))


if __name__ == "__main__":
    raise SystemExit(main())
