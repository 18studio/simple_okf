from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
LOCAL_MCP_INIT = (PROJECT_ROOT / "mcp" / "__init__.py").resolve()


def _force_project_root_first() -> None:
    root_text = str(PROJECT_ROOT)
    filtered: list[str] = []
    for entry in sys.path:
        try:
            if Path(entry or ".").resolve() == PROJECT_ROOT:
                continue
        except OSError:
            pass
        filtered.append(entry)
    sys.path[:] = [root_text, *filtered]


def _evict_nonlocal_mcp() -> None:
    existing = sys.modules.get("mcp")
    if existing is None:
        return
    module_file = getattr(existing, "__file__", None)
    try:
        is_local = module_file is not None and Path(module_file).resolve() == LOCAL_MCP_INIT
    except OSError:
        is_local = False
    if is_local:
        return
    for name in list(sys.modules):
        if name == "mcp" or name.startswith("mcp."):
            del sys.modules[name]


_force_project_root_first()
_evict_nonlocal_mcp()

from simple_okf_mcp.cli import mcp_main as main


if __name__ == "__main__":
    raise SystemExit(main())
