"""Instalação de Cursor skills (inspirado no GameDev skill_install)."""

from __future__ import annotations

import shutil
from typing import TYPE_CHECKING

from clified.core.paths import find_project_root

if TYPE_CHECKING:
    from pathlib import Path

    from clified.installer.python_installer import PythonProjectInstaller


def resolve_skill_source(
    tool_name: str,
    project_root: Path,
    *,
    workspace_root: Path | None = None,
) -> Path:
    candidates: list[Path] = []

    ws = workspace_root or find_project_root(project_root) or project_root.parent
    candidates.append(ws / ".cursor" / "create-skill" / tool_name)
    candidates.append(project_root / "cursor_skill")
    candidates.append(project_root / ".cursor" / "skills" / tool_name)

    for cand in candidates:
        if (cand / "SKILL.md").is_file():
            return cand

    msg = (
        f"Skill não encontrada para {tool_name!r}. "
        f"Esperado SKILL.md em .cursor/create-skill/{tool_name}/ ou {project_root}/cursor_skill/"
    )
    raise FileNotFoundError(
        msg,
    )


def register_cursor_skill(
    installer: PythonProjectInstaller,
    *,
    tool_name: str | None = None,
    target_root: Path | None = None,
    force: bool = False,
) -> bool:
    name = tool_name or installer.cli_name
    target = target_root or installer.project_root
    try:
        src = resolve_skill_source(
            name, installer.project_root, workspace_root=installer.workspace_root
        )
    except FileNotFoundError as exc:
        installer.logger.warning(str(exc))
        return True

    dest_dir = target / ".cursor" / "skills" / name
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest_file = dest_dir / "SKILL.md"
    if dest_file.exists() and not force:
        installer.logger.info(f"Skill já existe: {dest_file}")
        return True

    shutil.copy2(src / "SKILL.md", dest_file)
    installer.logger.success(f"Skill instalada: {dest_file}")
    return True
