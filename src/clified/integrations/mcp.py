"""Integração Cursor MCP — registo genérico de servidores."""

from __future__ import annotations

import json
import os
import platform
from pathlib import Path
from typing import Any

from clified.logging import Logger


def cursor_mcp_config_path() -> Path:
    home = Path.home()
    if platform.system().lower() == "windows":
        candidates = [
            home / ".cursor" / "mcp.json",
            Path(os.environ.get("APPDATA", "")) / "Cursor" / "User" / "globalStorage" / "cursor.mcp" / "mcp.json",
        ]
    else:
        candidates = [home / ".cursor" / "mcp.json"]
    for path in candidates:
        if path.is_file():
            return path
    return candidates[0]


def register_mcp_server(
    name: str,
    command: str,
    args: list[str] | None = None,
    *,
    env: dict[str, str] | None = None,
    logger: Logger | None = None,
) -> bool:
    """Adiciona ou actualiza um servidor em ``~/.cursor/mcp.json``."""
    log = logger or Logger()
    path = cursor_mcp_config_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.is_file():
            try:
                config = json.loads(path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                config = {}
        else:
            config = {}

        if not isinstance(config, dict):
            config = {}

        servers = config.setdefault("mcpServers", {})
        entry: dict[str, Any] = {"command": command, "args": args or []}
        if env:
            entry["env"] = env
        servers[name] = entry

        path.write_text(json.dumps(config, indent=2, ensure_ascii=False), encoding="utf-8")
        log.success(f"MCP '{name}' registado em {path}")
        return True
    except OSError as exc:
        log.warn(f"Não foi possível configurar MCP: {exc}")
        return False


def unregister_mcp_server(name: str, *, logger: Logger | None = None) -> bool:
    log = logger or Logger()
    path = cursor_mcp_config_path()
    if not path.is_file():
        return True
    try:
        config = json.loads(path.read_text(encoding="utf-8"))
        servers = config.get("mcpServers", {})
        if name in servers:
            del servers[name]
            path.write_text(json.dumps(config, indent=2, ensure_ascii=False), encoding="utf-8")
            log.success(f"MCP '{name}' removido de {path}")
        return True
    except (OSError, json.JSONDecodeError) as exc:
        log.warn(f"Erro ao remover MCP: {exc}")
        return False
