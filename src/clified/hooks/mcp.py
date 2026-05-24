"""Registo MCP no Cursor."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

from clified.integrations.mcp import register_mcp_server

if TYPE_CHECKING:
    from clified.installer.python_installer import PythonProjectInstaller
    from clified.installer.rust_installer import RustProjectInstaller


def register_mcp(
    installer: PythonProjectInstaller | RustProjectInstaller,
    *,
    server_name: str | None = None,
    command: str | None = None,
    args: list[str] | None = None,
) -> bool:
    name = server_name or os.environ.get("CLIFIED_MCP_NAME") or installer.cli_name
    cmd = command or str(installer.bin_dir / installer.cli_name)
    if args is None:
        raw = os.environ.get("CLIFIED_MCP_ARGS", "").strip()
        mcp_args = raw.split() if raw else []
    else:
        mcp_args = args
    return register_mcp_server(name, cmd, mcp_args, logger=installer.logger)


def register_mcp_serve(
    installer: PythonProjectInstaller | RustProjectInstaller,
) -> bool:
    """Regista MCP com args ``mcp serve`` (padrão denv)."""
    return register_mcp(installer, args=["mcp", "serve"])
