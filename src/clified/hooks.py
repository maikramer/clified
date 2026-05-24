"""Hooks reutilizáveis para ``post_install`` em tools.yaml."""

from __future__ import annotations

from typing import Any

from clified.integrations.mcp import register_mcp_server
from clified.installer.python_installer import PythonProjectInstaller
from clified.installer.rust_installer import RustProjectInstaller


def register_mcp(
    installer: PythonProjectInstaller | RustProjectInstaller,
    *,
    server_name: str | None = None,
    command: str | None = None,
    args: list[str] | None = None,
) -> bool:
    """Regista o CLI da tool no Cursor MCP (``post_install`` hook).

    Exemplo em tools.yaml::

        post_install: clified.hooks:register_mcp

    Variáveis de ambiente opcionais:
    - ``CLIFIED_MCP_NAME``: nome do servidor (default: cli_name)
    - ``CLIFIED_MCP_ARGS``: args separados por espaço (default: sem args)
    """
    import os

    name = server_name or os.environ.get("CLIFIED_MCP_NAME") or installer.cli_name
    cmd = command or str(installer.bin_dir / installer.cli_name)
    if args is None:
        raw = os.environ.get("CLIFIED_MCP_ARGS", "").strip()
        mcp_args = raw.split() if raw else []
    else:
        mcp_args = args

    return register_mcp_server(name, cmd, mcp_args, logger=installer.logger)


def noop(_installer: Any) -> bool:
    """Hook vazio (útil para testes)."""
    return True
