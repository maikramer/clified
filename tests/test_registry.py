"""Testes do registry tools.yaml."""

from __future__ import annotations

from pathlib import Path

import pytest

from clified.installer import registry as reg


@pytest.mark.usefixtures("demo_project")
def test_load_registry(
    sample_tools_yaml,
    clified_root,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``load_registry`` lê workspace e tools do YAML."""
    monkeypatch.setenv("CLIFIED_ROOT", str(clified_root))
    monkeypatch.setenv("CLIFIED_TOOLS", str(sample_tools_yaml))

    workspace, tools = reg.load_registry()

    assert workspace.name == "Test Workspace"
    assert workspace.root.resolve() == clified_root.parent.resolve()
    assert "demo" in tools
    assert tools["demo"].cli_name == "demo"
    assert tools["demo"].kind == reg.ToolKind.PYTHON


def test_get_tool_aliases(
    sample_tools_yaml,
    clified_root,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``get_tool`` resolve nome, CLI e alias."""
    monkeypatch.setenv("CLIFIED_ROOT", str(clified_root))
    monkeypatch.setenv("CLIFIED_TOOLS", str(sample_tools_yaml))
    reg.load_registry()

    assert reg.get_tool("demo").key == "demo"
    assert reg.get_tool("Demo Tool").key == "demo"


def test_get_tool_unknown(
    sample_tools_yaml,
    clified_root,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Ferramenta inexistente levanta ``KeyError``."""
    monkeypatch.setenv("CLIFIED_ROOT", str(clified_root))
    monkeypatch.setenv("CLIFIED_TOOLS", str(sample_tools_yaml))
    reg.load_registry()

    with pytest.raises(KeyError, match="desconhecida"):
        reg.get_tool("nao-existe")


@pytest.mark.usefixtures("demo_project")
def test_list_available_tools(
    sample_tools_yaml,
    clified_root,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``list_available_tools`` filtra projectos existentes."""
    monkeypatch.setenv("CLIFIED_ROOT", str(clified_root))
    monkeypatch.setenv("CLIFIED_TOOLS", str(sample_tools_yaml))
    reg.load_registry()

    available = reg.list_available_tools()
    assert len(available) == 1
    assert available[0].cli_name == "demo"


def test_missing_tools_yaml(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """YAML inexistente levanta ``FileNotFoundError``."""
    missing = tmp_path / "nao-existe.yaml"
    monkeypatch.setenv("CLIFIED_TOOLS", str(missing))
    with pytest.raises(FileNotFoundError, match="Registry não encontrado"):
        reg.load_registry()


def test_registry_extended_fields(
    clified_root,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Campos opcionais do YAML são parseados correctamente."""
    import textwrap

    content = textwrap.dedent(
        """
        workspace:
          root: ".."
          name: "Test"

        tools:
          ext:
            kind: python
            folder: ext-tool
            cli_name: ext
            python_module: ext
            description: "Extended"
            custom_install: clified.hooks:noop
            install_before_mode: venv_only
            install_order: -5
            post_install: clified.hooks:noop
        """,
    ).strip()
    path = clified_root / "tools.yaml"
    path.write_text(content, encoding="utf-8")
    monkeypatch.setenv("CLIFIED_ROOT", str(clified_root))
    monkeypatch.setenv("CLIFIED_TOOLS", str(path))

    reg.load_registry()
    spec = reg.get_tool("ext")

    assert spec.custom_install == "clified.hooks:noop"
    assert spec.install_before_mode == "venv_only"
    assert spec.install_order == -5
