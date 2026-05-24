"""Testes integração MCP Cursor."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from clified.hooks.mcp import register_mcp, register_mcp_serve
from clified.integrations.mcp import register_mcp_server, unregister_mcp_server


@pytest.fixture
def mcp_config(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    cfg = tmp_path / "mcp.json"
    monkeypatch.setattr(
        "clified.integrations.mcp.cursor_mcp_config_path",
        lambda: cfg,
    )
    return cfg


def test_register_mcp_server_creates_file(mcp_config: Path) -> None:
    ok = register_mcp_server("demo", "/usr/bin/demo", ["serve"])
    assert ok is True
    data = json.loads(mcp_config.read_text(encoding="utf-8"))
    assert data["mcpServers"]["demo"]["command"] == "/usr/bin/demo"
    assert data["mcpServers"]["demo"]["args"] == ["serve"]


def test_register_mcp_server_updates_existing(mcp_config: Path) -> None:
    mcp_config.write_text(
        json.dumps({"mcpServers": {"demo": {"command": "old", "args": []}}}),
        encoding="utf-8",
    )
    register_mcp_server("demo", "/new/cmd", ["a"])
    data = json.loads(mcp_config.read_text(encoding="utf-8"))
    assert data["mcpServers"]["demo"]["command"] == "/new/cmd"


def test_unregister_mcp_server(mcp_config: Path) -> None:
    register_mcp_server("demo", "/cmd", [])
    assert unregister_mcp_server("demo") is True
    data = json.loads(mcp_config.read_text(encoding="utf-8"))
    assert "demo" not in data.get("mcpServers", {})


def test_hook_register_mcp_serve(
    monkeypatch: pytest.MonkeyPatch,
    mcp_config: Path,
    tmp_path: Path,
) -> None:
    installer = type(
        "Installer",
        (),
        {
            "cli_name": "denv",
            "bin_dir": tmp_path / "bin",
            "logger": type("L", (), {"success": lambda *_a, **_k: None})(),
        },
    )()
    monkeypatch.setenv("CLIFIED_MCP_NAME", "denv-mcp")
    assert register_mcp_serve(installer) is True
    data = json.loads(mcp_config.read_text(encoding="utf-8"))
    assert data["mcpServers"]["denv-mcp"]["args"] == ["mcp", "serve"]


def test_hook_register_mcp_custom_args(
    mcp_config: Path,
    tmp_path: Path,
) -> None:
    installer = type(
        "Installer",
        (),
        {
            "cli_name": "tool",
            "bin_dir": tmp_path / "opt",
            "logger": type("L", (), {"success": lambda *_a, **_k: None})(),
        },
    )()
    assert register_mcp(installer, args=["custom"]) is True
    data = json.loads(mcp_config.read_text(encoding="utf-8"))
    assert data["mcpServers"]["tool"]["args"] == ["custom"]
