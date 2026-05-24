"""Testes de resolução de paths."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from clified.core.paths import find_project_root, resolve_project_file

if TYPE_CHECKING:
    from pathlib import Path


def test_find_project_root_by_pyproject(tmp_path: Path) -> None:
    proj = tmp_path / "myapp"
    proj.mkdir()
    (proj / "pyproject.toml").write_text("[project]\nname='x'\n", encoding="utf-8")
    sub = proj / "src" / "pkg"
    sub.mkdir(parents=True)

    root = find_project_root(sub)
    assert root == proj.resolve()


def test_resolve_project_file_relative(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    proj = tmp_path / "repo"
    proj.mkdir()
    (proj / "pyproject.toml").write_text("[project]\nname='x'\n", encoding="utf-8")
    cfg = proj / "config.yml"
    cfg.write_text("x: 1\n", encoding="utf-8")
    sub = proj / "src"
    sub.mkdir()
    monkeypatch.chdir(sub)

    resolved = resolve_project_file("config.yml")
    assert resolved == cfg.resolve()


def test_resolve_project_file_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    proj = tmp_path / "empty"
    proj.mkdir()
    (proj / "Cargo.toml").write_text("[package]\nname='x'\n", encoding="utf-8")
    monkeypatch.chdir(proj)

    with pytest.raises(FileNotFoundError, match="não encontrado"):
        resolve_project_file("missing.txt")
