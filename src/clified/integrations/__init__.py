"""Integrações externas (Cursor MCP, etc.)."""

from .mcp import cursor_mcp_config_path, register_mcp_server, unregister_mcp_server

__all__ = [
    "cursor_mcp_config_path",
    "register_mcp_server",
    "unregister_mcp_server",
]
