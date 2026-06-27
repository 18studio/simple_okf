from __future__ import annotations

import argparse

try:
    from .server import create_mcp
except ImportError:  # Allows running as `python mcp/__main__.py`.
    from server import create_mcp


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

    mcp = create_mcp(args.bundle)
    if args.transport == "stdio":
        mcp.run()
    else:
        mcp.run(transport=args.transport, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
