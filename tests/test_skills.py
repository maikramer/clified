"""Testes hooks de Cursor skills."""

from __future__ import annotations

from pathlib import Path

import pytest

from clified.hooks.skills import resolve_skill_source


def test_resolve_skill_source_project_cursor_skill(tmp_path: Path) -> None:
    project = tmp_path / "mytool"
    skill_dir = project / "cursor_skill"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text("# Skill\n", encoding="utf-8")

    resolved = resolve_skill_source("mytool", project)
    assert resolved == skill_dir


def test_resolve_skill_source_workspace_create_skill(tmp_path: Path) -> None:
    ws = tmp_path / "workspace"
    project = ws / "mytool"
    skill_dir = ws / ".cursor" / "create-skill" / "mytool"
    skill_dir.mkdir(parents=True)
    project.mkdir()
    (skill_dir / "SKILL.md").write_text("# Skill\n", encoding="utf-8")

    resolved = resolve_skill_source("mytool", project, workspace_root=ws)
    assert resolved == skill_dir


def test_resolve_skill_source_missing(tmp_path: Path) -> None:
    project = tmp_path / "empty"
    project.mkdir()
    with pytest.raises(FileNotFoundError, match="Skill não encontrada"):
        resolve_skill_source("missing", project)
