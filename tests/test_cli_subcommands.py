"""Testes do dispatcher de subcomandos clified."""

from __future__ import annotations

from unittest.mock import patch

from clified.installer.cli import SUBCOMMANDS, main


def test_subcommands_defined() -> None:
    assert "list" in SUBCOMMANDS
    assert "search" in SUBCOMMANDS
    assert "update" in SUBCOMMANDS


def test_back_compat_delegates_to_unified() -> None:
    with patch("clified.installer.unified.main", return_value=0) as mock:
        assert main(["--list"]) == 0
        mock.assert_called_once_with(["--list"])


def test_back_compat_tool_name() -> None:
    with patch("clified.installer.unified.main", return_value=0) as mock:
        assert main(["demo"]) == 0
        mock.assert_called_once_with(["demo"])


def test_list_subcommand_json(capsys) -> None:
    with patch(
        "clified.installer.receipts.list_with_status",
        return_value=[{"name": "text2d", "status": "ok"}],
    ):
        rc = main(["list", "--json"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "text2d" in out
    assert '"status": "success"' in out


def test_search_subcommand() -> None:
    from clified.installer.catalog import RepoSpec

    specs = [
        RepoSpec(
            name="text2d",
            repo="https://github.com/x/GameDev.git",
            tool="text2d",
            description="Image generation",
        )
    ]
    with patch("clified.installer.catalog.list_known", return_value=specs):
        with patch("clified.installer.receipts.load_all", return_value={}):
            assert main(["search", "text"]) == 0


def test_unknown_tool_delegates_without_traceback(
    tmp_path, monkeypatch, capsys
) -> None:
    """`clified <ferramenta-inexistente>` delega e devolve 1 (sem traceback)."""
    monkeypatch.setenv("CLIFIED_HOME", str(tmp_path / "home"))
    (tmp_path / "home").mkdir()
    # sem tools.yaml no cwd → ferramenta desconhecida
    monkeypatch.chdir(tmp_path)
    rc = main(["ferramenta-inexistente"])
    assert rc == 1
    captured = capsys.readouterr()
    assert "Traceback" not in captured.out
    assert "Traceback" not in captured.err
