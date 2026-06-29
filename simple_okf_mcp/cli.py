from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType
from typing import Sequence

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
_LOCAL_MCP_INIT = (_PROJECT_ROOT / "mcp" / "__init__.py").resolve()
_LOCAL_MCP_CLI = (_PROJECT_ROOT / "mcp" / "cli.py").resolve()


def _module_file(module: ModuleType) -> Path | None:
    module_file = getattr(module, "__file__", None)
    if not module_file:
        return None
    try:
        return Path(module_file).resolve()
    except OSError:
        return None


def _is_local_mcp(module: ModuleType) -> bool:
    return _module_file(module) == _LOCAL_MCP_INIT


def _ensure_project_root_first() -> None:
    root_text = str(_PROJECT_ROOT)
    filtered: list[str] = []
    for entry in sys.path:
        try:
            if Path(entry or ".").resolve() == _PROJECT_ROOT:
                continue
        except OSError:
            pass
        filtered.append(entry)
    sys.path[:] = [root_text, *filtered]


def _evict_nonlocal_mcp() -> None:
    existing = sys.modules.get("mcp")
    if existing is None or _is_local_mcp(existing):
        return
    for name in list(sys.modules):
        if name == "mcp" or name.startswith("mcp."):
            del sys.modules[name]


def _load_local_cli() -> ModuleType:
    """Load this repository's canonical ``mcp/cli.py`` despite SDK name collisions."""

    _ensure_project_root_first()
    _evict_nonlocal_mcp()

    import mcp  # noqa: WPS433 - deliberately imports the local bridged package.

    if not _is_local_mcp(mcp):
        raise RuntimeError(f"Could not load local Simple OKF MCP package from {_LOCAL_MCP_INIT}")

    existing = sys.modules.get("mcp.cli")
    if existing is not None:
        if _module_file(existing) == _LOCAL_MCP_CLI:
            return existing
        del sys.modules["mcp.cli"]
        if getattr(mcp, "cli", None) is existing:
            delattr(mcp, "cli")

    spec = importlib.util.spec_from_file_location("mcp.cli", _LOCAL_MCP_CLI)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load local Simple OKF CLI from {_LOCAL_MCP_CLI}")
    module = importlib.util.module_from_spec(spec)
    sys.modules["mcp.cli"] = module
    setattr(mcp, "cli", module)
    spec.loader.exec_module(module)
    return module


def main(argv: Sequence[str] | None = None) -> int:
    return int(_load_local_cli().main(argv, multi_app_help_for_options=True) or 0)


def mcp_main(argv: Sequence[str] | None = None) -> int:
    return int(_load_local_cli().main(argv) or 0)


def server_main(argv: Sequence[str] | None = None) -> int:
    return int(_load_local_cli().server_main(argv) or 0)


def validate_main(argv: Sequence[str] | None = None) -> int:
    return int(_load_local_cli().validate_main(argv) or 0)


def indexes_main(argv: Sequence[str] | None = None) -> int:
    return int(_load_local_cli().indexes_main(argv) or 0)


def export_main(argv: Sequence[str] | None = None) -> int:
    return int(_load_local_cli().export_main(argv) or 0)


def graph_main(argv: Sequence[str] | None = None) -> int:
    return int(_load_local_cli().graph_main(argv) or 0)


def rag_inspect_main(argv: Sequence[str] | None = None) -> int:
    return int(_load_local_cli().rag_inspect_main(argv) or 0)


def rag_refresh_main(argv: Sequence[str] | None = None) -> int:
    return int(_load_local_cli().rag_refresh_main(argv) or 0)


def rag_retrieve_main(argv: Sequence[str] | None = None) -> int:
    return int(_load_local_cli().rag_retrieve_main(argv) or 0)


def seven_d_main(argv: Sequence[str] | None = None) -> int:
    return int(_load_local_cli().seven_d_main(argv) or 0)
