from __future__ import annotations

import argparse
import importlib.util
import sys
from pathlib import Path
from types import ModuleType
from typing import Callable


PROJECT_ROOT = Path(__file__).resolve().parents[1]
_LOCAL_SERVER_PATH = Path(__file__).resolve().with_name("server.py")
_LOCAL_SERVER_MODULE = "mcp._okf_server"


def _load_local_server_module() -> ModuleType:
    """Load this project's MCP tool surface without shadowing the MCP SDK.

    The repository's source directory is named ``mcp`` for historical/project
    reasons, while FastMCP depends on the official SDK package also named
    ``mcp``.  Loading ``mcp/server.py`` as ``mcp.server`` would block FastMCP
    from importing SDK modules such as ``mcp.server.lowlevel``.  Load the local
    file under a private module name instead.
    """

    project_root_text = str(PROJECT_ROOT)
    sys.path = [entry for entry in sys.path if entry != project_root_text]
    sys.path.insert(0, project_root_text)

    existing_mcp = sys.modules.get("mcp")
    local_init = PROJECT_ROOT / "mcp" / "__init__.py"
    if existing_mcp is not None and Path(getattr(existing_mcp, "__file__", "")).resolve() != local_init:
        del sys.modules["mcp"]

    # Import the local package first so mcp/__init__.py can bridge to the SDK.
    import mcp  # noqa: F401

    existing = sys.modules.get(_LOCAL_SERVER_MODULE)
    if existing is not None:
        return existing

    spec = importlib.util.spec_from_file_location(_LOCAL_SERVER_MODULE, _LOCAL_SERVER_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load local MCP server module from {_LOCAL_SERVER_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[_LOCAL_SERVER_MODULE] = module
    spec.loader.exec_module(module)
    return module


def _load_create_mcp() -> Callable[..., object]:
    module = _load_local_server_module()
    return module.create_mcp


def main() -> None:
    parser = argparse.ArgumentParser(description="Run an OKF FastMCP server")
    parser.add_argument("--bundle", default="okf", help="Path to the OKF bundle directory")
    parser.add_argument(
        "--transport",
        default="stdio",
        choices=("stdio", "http", "sse"),
        help="MCP transport to use",
    )
    parser.add_argument("--host", default="127.0.0.1", help="Host for HTTP/SSE transports")
    parser.add_argument("--port", type=int, default=8000, help="Port for HTTP/SSE transports")
    args = parser.parse_args()

    create_mcp = _load_create_mcp()
    mcp = create_mcp(args.bundle)
    if args.transport == "stdio":
        mcp.run()
    else:
        mcp.run(transport=args.transport, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
