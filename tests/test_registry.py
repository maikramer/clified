"""Testes do registry tools.yaml."""

from __future__ import annotations

import os

import pytest

from clified.installer import registry as reg


@pytest.fixture(autouse=True)
def _reset_registry(monkeypatch: pytest.MonkeyPatch) -> None:
    reg.TOOLS.clear()
    reg.WORKSPACE = None
    reg._CLIFIED_ROOT = None
    monkeypatch.delenv("CLIFIED_ROOT", raising=False)
    monkeypatch.delenv("CLIFIED_TOOLS", raising=False)


def test_load_registry(sample_tools_yaml, clified_root, demo_project, monkeypatch):
    monkeypatch.setenv("CLIFIED_ROOT", str(clified_root))
    monkeypatch.setenv("CLIFIED_TOOLS", str(sample_tools_yaml))

    workspace, tools = reg.load_registry()

    assert workspace.name == "Test Workspace"
    assert workspace.root.resolve() == clified_root.parent.resolve()
    assert "demo" in tools
    assert tools["demo"].cli_name == "demo"
    assert tools["demo"].kind == reg.ToolKind.PYTHON


def test_get_tool_aliases(sample_tools_yaml, clified_root, monkeypatch):
    monkeypatch.setenv("CLIFIED_ROOT", str(clified_root))
    monkeypatch.setenv("CLIFIED_TOOLS", str(sample_tools_yaml))
    reg.load_registry()

    assert reg.get_tool("demo").key == "demo"
    assert reg.get_tool("Demo Tool").key == "demo"


def test_get_tool_unknown(sample_tools_yaml, clified_root, monkeypatch):
    monkeypatch.setenv("CLIFIED_ROOT", str(clified_root))
    monkeypatch.setenv("CLIFIED_TOOLS", str(sample_tools_yaml))
    reg.load_registry()

    with pytest.raises(KeyError, match="desconhecida"):
        reg.get_tool("nao-existe")


def test_list_available_tools(sample_tools_yaml, clified_root, demo_project, monkeypatch):
    monkeypatch.setenv("CLIFIED_ROOT", str(clified_root))
    monkeypatch.setenv("CLIFIED_TOOLS", str(sample_tools_yaml))
    reg.load_registry()

    available = reg.list_available_tools()
    assert len(available) == 1
    assert available[0].cli_name == "demo"


def test_missing_tools_yaml(clified_root, monkeypatch):
    monkeypatch.setenv("CLIFIED_ROOT", str(clified_root))
    with pytest.raises(FileNotFoundError, match="Registry não encontrado"):
        reg.load_registry()
