"""Testes do CLI unificado."""

from __future__ import annotations

import pytest

from clified.installer.unified import main


@pytest.mark.usefixtures("demo_project")
def test_main_list(
    sample_tools_yaml,
    clified_root,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """``--list`` imprime ferramentas registadas."""
    monkeypatch.setenv("CLIFIED_ROOT", str(clified_root))
    monkeypatch.setenv("CLIFIED_TOOLS", str(sample_tools_yaml))

    code = main(["--list"])
    assert code == 0
    out = capsys.readouterr().out
    assert "demo" in out.lower() or "Demo" in out


@pytest.mark.usefixtures("demo_project")
def test_main_list_json(
    sample_tools_yaml,
    clified_root,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """``--list --json`` devolve JSON válido."""
    import json

    monkeypatch.setenv("CLIFIED_ROOT", str(clified_root))
    monkeypatch.setenv("CLIFIED_TOOLS", str(sample_tools_yaml))

    code = main(["--list", "--json"])
    assert code == 0
    data = json.loads(capsys.readouterr().out)
    assert data["count"] == 1
    assert data["tools"][0]["name"] == "demo"


def test_main_help(
    sample_tools_yaml,
    clified_root,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Invocação sem subcomando mostra ajuda."""
    monkeypatch.setenv("CLIFIED_ROOT", str(clified_root))
    monkeypatch.setenv("CLIFIED_TOOLS", str(sample_tools_yaml))
    code = main([])
    assert code == 0
