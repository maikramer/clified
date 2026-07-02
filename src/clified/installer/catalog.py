"""Catálogo de ferramentas remotas — ``--get`` e one-liner de instalação.

O catálogo vive em ``bundled/registry.yaml`` (ou ``CLIFIED_CATALOG``) e mapeia
um nome curto (ex.: ``denv``) ao repositório git + ferramenta registada no
``tools.yaml`` desse repositório. Isto permite:

    clified-install --get denv
    curl -fsSL https://raw.githubusercontent.com/.../install.sh | bash -s -- --get denv
"""

from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

import yaml

from clified.paths import bundled_path, clified_home

if TYPE_CHECKING:
    from collections.abc import Iterable


@dataclass(frozen=True)
class RepoSpec:
    """Entrada do catálogo: nome → repositório + ferramenta."""

    name: str
    repo: str
    tool: str
    tools_yaml: str = "tools.yaml"
    description: str = ""


def catalog_path() -> Path:
    """Caminho do ``registry.yaml`` (env override ou embutido no pacote)."""
    env = os.environ.get("CLIFIED_CATALOG", "").strip()
    if env:
        return Path(env).expanduser().resolve()
    return bundled_path("registry.yaml")


def _parse_entry(key: str, data: dict[str, object]) -> RepoSpec:
    repo = str(data.get("repo", "")).strip()
    if not repo:
        msg = f"Entrada de catálogo inválida ({key!r}): falta 'repo'."
        raise ValueError(msg)
    return RepoSpec(
        name=key,
        repo=repo,
        tool=str(data.get("tool", key)).strip() or key,
        tools_yaml=str(data.get("tools_yaml", "tools.yaml")).strip() or "tools.yaml",
        description=str(data.get("description", "")).strip(),
    )


def load_catalog(path: Path | None = None) -> dict[str, RepoSpec]:
    """Carrega o catálogo conhecido (nome → ``RepoSpec``)."""
    yaml_path = path or catalog_path()
    if not yaml_path.is_file():
        return {}
    raw = yaml.safe_load(yaml_path.read_text(encoding="utf-8")) or {}
    tools = raw.get("tools") or {}
    catalog: dict[str, RepoSpec] = {}
    for key, data in tools.items():
        if isinstance(data, dict):
            catalog[str(key).lower()] = _parse_entry(str(key).lower(), data)
    return catalog


def resolve(name: str) -> RepoSpec:
    """Resolve um nome (case-insensitive) para ``RepoSpec``."""
    catalog = load_catalog()
    key = name.lower().strip()
    if key in catalog:
        return catalog[key]
    available = ", ".join(sorted(catalog)) or "(nenhuma)"
    msg = f"Ferramenta remota desconhecida: {name!r}. Conhecidas: {available}"
    raise KeyError(msg)


def list_known() -> list[RepoSpec]:
    """Lista as entradas conhecidas do catálogo (ordenadas por nome)."""
    return [load_catalog()[k] for k in sorted(load_catalog())]


def sources_dir() -> Path:
    """Onde os repositórios remotos são clonados (``~/.clified/sources``)."""
    env = os.environ.get("CLIFIED_SOURCES", "").strip()
    if env:
        return Path(env).expanduser().resolve()
    return clified_home() / "sources"


def clone_or_update(
    spec: RepoSpec,
    dest: Path | None = None,
    *,
    logger: object | None = None,
) -> Path:
    """Clona (ou actualiza com ``git pull``) o repositório e devolve o caminho.

    Levanta ``RuntimeError`` se o ``git`` não estiver disponível ou falhar.
    """
    dest = dest or (sources_dir() / spec.name)
    dest.parent.mkdir(parents=True, exist_ok=True)

    if (dest / ".git").is_dir():
        if logger is not None:
            _log(logger, f"Actualizando {spec.name} ({dest})...")
        result = subprocess.run(
            ["git", "-C", str(dest), "pull", "--ff-only"],
            check=False,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            msg = f"git pull falhou em {dest}:\n{result.stderr.strip()}"
            raise RuntimeError(msg)
        return dest.resolve()

    if logger is not None:
        _log(logger, f"A clonar {spec.repo} para {dest}...")
    if dest.exists():
        # Restos de um clone interrompido — limpar antes de clonar de novo.
        _rm_tree(dest)
    result = subprocess.run(
        ["git", "clone", "--depth", "1", spec.repo, str(dest)],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        msg = f"git clone falhou para {spec.repo}:\n{result.stderr.strip()}"
        raise RuntimeError(msg)
    return dest.resolve()


def resolve_tools_yaml(spec: RepoSpec, repo_dir: Path) -> Path:
    """Caminho absoluto do ``tools.yaml`` dentro do repositório clonado."""
    candidate = (repo_dir / spec.tools_yaml).resolve()
    if not candidate.is_file():
        msg = (
            f"tools.yaml não encontrado em {candidate}. "
            f"Verifica o campo 'tools_yaml' do catálogo para {spec.name!r}."
        )
        raise FileNotFoundError(msg)
    return candidate


def _log(logger: object, msg: str) -> None:
    step = getattr(logger, "step", None)
    if callable(step):
        step(msg)
        return
    info = getattr(logger, "info", None)
    if callable(info):
        info(msg)


def _rm_tree(path: Path) -> None:
    import shutil

    shutil.rmtree(path, ignore_errors=True)


def iter_known_names() -> Iterable[str]:
    """Itera os nomes conhecidos (compatibilidade com helpers externos)."""
    return iter(sorted(load_catalog()))
