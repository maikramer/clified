"""Testes adicionais de paths."""

from __future__ import annotations

from pathlib import Path

import pytest

from clified.core.paths import find_project_root, resolve_project_file


def test_find_project_root_env_override(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    env_root = tmp_path / "forced"
    env_root.mkdir()
    sub = env_root / "deep"
    sub.mkdir()
    monkeypatch.setenv("CLIFIED_PROJECT_ROOT", str(env_root))
    assert find_project_root(sub) == env_root.resolve()


def test_find_project_root_cargo_marker(tmp_path: Path) -> None:
    proj = tmp_path / "rust-app"
    proj.mkdir()
    (proj / "Cargo.toml").write_text("[package]\nname='x'\n", encoding="utf-8")
    assert find_project_root(proj) == proj.resolve()


def test_resolve_project_file_absolute(tmp_path: Path) -> None:
    f = tmp_path / "abs.txt"
    f.write_text("ok", encoding="utf-8")
    assert resolve_project_file(f) == f.resolve()
