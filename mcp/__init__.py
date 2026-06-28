"""FastMCP server and OKF filesystem helpers.

This repository intentionally keeps its local implementation under the
``mcp/`` directory.  The FastMCP dependency also imports the official Python
SDK package named ``mcp``.  To let both coexist, this package exposes the SDK
submodules through ``__path__`` while keeping the local OKF modules available
from the same directory.
"""

from __future__ import annotations

import sys
from pathlib import Path

__version__ = "0.1.0"

_LOCAL_PACKAGE_DIR = Path(__file__).resolve().parent


def _extend_with_sdk_package() -> None:
    """Add the official MCP SDK package directory to this package path.

    Without this bridge, ``fastmcp`` sees this local ``mcp`` package first and
    imports like ``mcp.types`` or ``mcp.server.lowlevel`` fail.  The SDK path is
    inserted before the local path so SDK subpackages (especially
    ``mcp.server``) win over local files with the same basename.
    """

    for entry in list(sys.path):
        if not entry:
            continue
        candidate = (Path(entry).resolve() / "mcp").resolve()
        if candidate == _LOCAL_PACKAGE_DIR:
            continue
        if (candidate / "types.py").is_file() and (candidate / "server").is_dir():
            candidate_text = str(candidate)
            if candidate_text not in __path__:
                __path__.insert(0, candidate_text)
            return


_extend_with_sdk_package()

# Re-export the official MCP SDK public API used by FastMCP.  These imports are
# resolved from the SDK path inserted above, not from local OKF modules.
try:  # pragma: no cover - exercised by the runtime MCP server import path.
    from .client.session import ClientSession
    from .client.session_group import ClientSessionGroup
    from .client.stdio import StdioServerParameters, stdio_client
    from .server.session import ServerSession
    from .server.stdio import stdio_server
    from .shared.exceptions import McpError, UrlElicitationRequiredError
    from .types import (
        CallToolRequest,
        ClientCapabilities,
        ClientNotification,
        ClientRequest,
        ClientResult,
        CompleteRequest,
        CreateMessageRequest,
        CreateMessageResult,
        CreateMessageResultWithTools,
        ErrorData,
        GetPromptRequest,
        GetPromptResult,
        Implementation,
        IncludeContext,
        InitializedNotification,
        InitializeRequest,
        InitializeResult,
        JSONRPCError,
        JSONRPCRequest,
        JSONRPCResponse,
        ListPromptsRequest,
        ListPromptsResult,
        ListResourcesRequest,
        ListResourcesResult,
        ListToolsResult,
        LoggingLevel,
        LoggingMessageNotification,
        Notification,
        PingRequest,
        ProgressNotification,
        PromptsCapability,
        ReadResourceRequest,
        ReadResourceResult,
        Resource,
        ResourcesCapability,
        ResourceUpdatedNotification,
        RootsCapability,
        SamplingCapability,
        SamplingContent,
        SamplingContextCapability,
        SamplingMessage,
        SamplingMessageContentBlock,
        SamplingToolsCapability,
        ServerCapabilities,
        ServerNotification,
        ServerRequest,
        ServerResult,
        SetLevelRequest,
        StopReason,
        SubscribeRequest,
        Tool,
        ToolChoice,
        ToolResultContent,
        ToolsCapability,
        ToolUseContent,
        UnsubscribeRequest,
    )
    from .types import Role as SamplingRole
except ImportError:
    # Keep local OKF CLI helpers importable even when FastMCP/MCP SDK server
    # dependencies are not installed.  Starting the MCP server will still fail
    # with the dependency error at the actual FastMCP import site.
    pass

__all__ = [
    "__version__",
    "CallToolRequest",
    "ClientCapabilities",
    "ClientNotification",
    "ClientRequest",
    "ClientResult",
    "ClientSession",
    "ClientSessionGroup",
    "CompleteRequest",
    "CreateMessageRequest",
    "CreateMessageResult",
    "CreateMessageResultWithTools",
    "ErrorData",
    "GetPromptRequest",
    "GetPromptResult",
    "Implementation",
    "IncludeContext",
    "InitializeRequest",
    "InitializeResult",
    "InitializedNotification",
    "JSONRPCError",
    "JSONRPCRequest",
    "JSONRPCResponse",
    "ListPromptsRequest",
    "ListPromptsResult",
    "ListResourcesRequest",
    "ListResourcesResult",
    "ListToolsResult",
    "LoggingLevel",
    "LoggingMessageNotification",
    "McpError",
    "Notification",
    "PingRequest",
    "ProgressNotification",
    "PromptsCapability",
    "ReadResourceRequest",
    "ReadResourceResult",
    "Resource",
    "ResourcesCapability",
    "ResourceUpdatedNotification",
    "RootsCapability",
    "SamplingCapability",
    "SamplingContent",
    "SamplingContextCapability",
    "SamplingMessage",
    "SamplingMessageContentBlock",
    "SamplingRole",
    "SamplingToolsCapability",
    "ServerCapabilities",
    "ServerNotification",
    "ServerRequest",
    "ServerResult",
    "ServerSession",
    "SetLevelRequest",
    "StdioServerParameters",
    "StopReason",
    "SubscribeRequest",
    "Tool",
    "ToolChoice",
    "ToolResultContent",
    "ToolsCapability",
    "ToolUseContent",
    "UnsubscribeRequest",
    "UrlElicitationRequiredError",
    "stdio_client",
    "stdio_server",
]
