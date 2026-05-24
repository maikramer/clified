"""Fixtures partilhadas."""

from __future__ import annotations

import textwrap
from typing import TYPE_CHECKING

import pytest

from clified.installer import registry as reg

if TYPE_CHECKING:
    from pathlib import Path


@pytest.fixture(autouse=True)
def _reset_registry_state(monkeypatch: pytest.MonkeyPatch) -> None:
    """Estado limpo antes de cada teste."""
    reg.reset_registry()
    monkeypatch.delenv("CLIFIED_ROOT", raising=False)
    monkeypatch.delenv("CLIFIED_TOOLS", raising=False)


@pytest.fixture
def clified_root(tmp_path: Path) -> Path:
    """Raiz mínima do Clified com tools.yaml de teste."""
    root = tmp_path / "clified"
    root.mkdir()
    (root / "config").mkdir()
    (root / "src" / "clified").mkdir(parents=True)
    (root / "pyproject.toml").write_text(
        "[project]\nname = 'clified'\n", encoding="utf-8"
    )
    return root


@pytest.fixture
def sample_tools_yaml(clified_root: Path) -> Path:
    content = textwrap.dedent(
        """
        workspace:
          root: ".."
          name: "Test Workspace"

        tools:
          demo:
            name: "Demo Tool"
            kind: python
            folder: demo-tool
            cli_name: demo
            python_module: demo
            description: "Ferramenta de teste"
        """,
    ).strip()
    path = clified_root / "tools.yaml"
    path.write_text(content, encoding="utf-8")
    return path


@pytest.fixture
def demo_project(clified_root: Path) -> Path:
    """Projecto Python fictício ao lado de clified/."""
    ws = clified_root.parent
    proj = ws / "demo-tool"
    (proj / "src").mkdir(parents=True)
    (proj / "pyproject.toml").write_text("[project]\nname='demo'\n", encoding="utf-8")
    return proj
