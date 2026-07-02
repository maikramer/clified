"""Testes do fluxo ``clified-install --get`` (busca + instalação remota)."""

from __future__ import annotations

import textwrap
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from clified.installer import catalog
from clified.installer.unified import main


@pytest.fixture
def empty_catalog(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    path = tmp_path / "registry.yaml"
    path.write_text("tools: {}\n", encoding="utf-8")
    monkeypatch.setenv("CLIFIED_CATALOG", str(path))
    return path


@pytest.fixture
def known_catalog(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    path = tmp_path / "registry.yaml"
    path.write_text(
        textwrap.dedent(
            """
            tools:
              denv:
                repo: https://example.com/denv.git
                tool: denv
                tools_yaml: tools.yaml
                description: "Denv mock"
            """,
        ).strip(),
        encoding="utf-8",
    )
    monkeypatch.setenv("CLIFIED_CATALOG", str(path))
    return path


def _fake_repo(dest: Path) -> Path:
    """Cria um repo fictício com tools.yaml válido em ``dest``."""
    dest.mkdir(parents=True, exist_ok=True)
    (dest / "tools.yaml").write_text(
        textwrap.dedent(
            """
            workspace:
              root: ".."
              name: Mock

            tools:
              mytool:
                kind: python
                folder: mytool
                cli_name: mytool
                description: mock
            """,
        ).strip(),
        encoding="utf-8",
    )
    return dest.resolve()


def test_get_unknown_tool_returns_1(
    empty_catalog: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.delenv("CLIFIED_TOOLS", raising=False)
    code = main(["--get", "nope"])
    assert code == 1
    assert "desconhecida" in capsys.readouterr().out.lower()


def test_get_with_repo_clones_and_installs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sources = tmp_path / "sources"
    repo_dir = sources / "mytool"

    def fake_clone(spec, dest=None, *, logger=None):
        assert spec.repo == "https://example.com/x.git"
        assert spec.tool == "mytool"
        return _fake_repo(repo_dir)

    monkeypatch.setattr(catalog, "clone_or_update", fake_clone)
    install_mock = MagicMock(return_value=True)
    monkeypatch.setattr("clified.installer.unified.install_tool", install_mock)

    code = main(
        [
            "--get",
            "mytool",
            "--repo",
            "https://example.com/x.git",
            "--sources-dir",
            str(sources),
        ]
    )
    assert code == 0
    install_mock.assert_called_once()
    assert install_mock.call_args.args[0] == "mytool"


def test_get_clone_failure_returns_1(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fake_clone(spec, dest=None, *, logger=None):
        msg = "git clone falhou"
        raise RuntimeError(msg)

    monkeypatch.setattr(catalog, "clone_or_update", fake_clone)
    code = main(
        [
            "--get",
            "mytool",
            "--repo",
            "https://example.com/x.git",
            "--sources-dir",
            str(tmp_path),
        ]
    )
    assert code == 1


def test_catalog_flag_lists_known(
    known_catalog: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    code = main(["--catalog"])
    assert code == 0
    out = capsys.readouterr().out
    assert "denv" in out.lower()


def test_catalog_flag_json(
    known_catalog: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    import json

    code = main(["--catalog", "--json"])
    assert code == 0
    data = json.loads(capsys.readouterr().out)
    assert data["count"] == 1
    assert data["tools"][0]["name"] == "denv"
