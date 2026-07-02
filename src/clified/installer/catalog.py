"""Catálogo de ferramentas remotas — ``--get`` e one-liner de instalação.

O catálogo mapeia um nome curto (ex.: ``denv``) ao repositório git + ferramenta
registada no ``tools.yaml`` desse repositório. Isto permite:

    clified-install --get denv
    curl -fsSL https://raw.githubusercontent.com/.../install.sh | bash -s -- --get denv

Por defeito o catálogo é lido de um repo remoto público
(``maikramer/clified-catalog``) com cache local (TTL via ``CLIFIED_CATALOG_TTL``)
e fallback ao ``bundled/registry.yaml`` quando offline. ``CLIFIED_CATALOG``
sobrepõe-se (URL ``http(s)://`` ou path local). Entradas ``access: private``
(ex.: repos da Locatelli) são meramente informativas: o clone depende das creds
git do utilizador; sem acesso, falhamos de forma suave (mensagem clara).
"""

from __future__ import annotations

import os
import subprocess
import time
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

import yaml

from clified.paths import bundled_path, clified_home, version

if TYPE_CHECKING:
    from collections.abc import Iterable

DEFAULT_CATALOG_URL = (
    "https://raw.githubusercontent.com/maikramer/clified-catalog/main/registry.yaml"
)
_DEFAULT_CATALOG_TTL = 3600
_AUTH_FAILURE_MARKERS = (
    "authentication failed",
    "permission denied",
    "could not read username",
    "could not read from remote repository",
    "remote: invalid username",
    "repository not found",
    "not found",
)


@dataclass(frozen=True)
class RepoSpec:
    """Entrada do catálogo: nome → repositório + ferramenta."""

    name: str
    repo: str
    tool: str
    tools_yaml: str = "tools.yaml"
    description: str = ""
    access: str = "public"  # "public" | "private" (informational)


def catalog_path() -> Path:
    """Caminho local do ``registry.yaml`` (env path local ou embutido).

    Back-compat: ignora URLs em ``CLIFIED_CATALOG`` (use ``load_catalog()``
    para suporte a URL remoto). Sem callers internos; mantida p/ uso externo.
    """
    env = os.environ.get("CLIFIED_CATALOG", "").strip()
    if env and not _is_url(env):
        return Path(env).expanduser().resolve()
    return bundled_path("registry.yaml")


def _bundled_catalog_path() -> Path:
    return bundled_path("registry.yaml")


def _is_url(s: str) -> bool:
    return s.startswith(("http://", "https://"))


def _catalog_ttl() -> int:
    """TTL da cache em segundos (env ``CLIFIED_CATALOG_TTL``).

    ``0`` = sempre fetch; ``-1`` = só bundled (offline); default 3600.
    """
    raw = os.environ.get("CLIFIED_CATALOG_TTL", "").strip()
    if not raw:
        return _DEFAULT_CATALOG_TTL
    try:
        return int(raw)
    except ValueError:
        return _DEFAULT_CATALOG_TTL


def _fetch_text(url: str, timeout: float = 5.0) -> str:
    """Busca o texto de uma URL; levanta ``OSError`` em falha de rede/HTTP."""
    req = urllib.request.Request(  # noqa: S310 - URL do catálogo é trusted/default
        url,
        headers={"User-Agent": f"clified/{version()}"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310
        data = resp.read()
    encoding = resp.headers.get_content_charset() or "utf-8"
    return data.decode(encoding, errors="replace")


def _bundled_text() -> str:
    p = _bundled_catalog_path()
    try:
        return p.read_text(encoding="utf-8")
    except OSError:
        return ""


def _read_cache(cache: Path) -> str | None:
    try:
        return cache.read_text(encoding="utf-8")
    except OSError:
        return None


def _read_cache_if_fresh(cache: Path, ttl: int) -> str | None:
    if ttl <= 0 or not cache.is_file():
        return None
    age = time.time() - cache.stat().st_mtime
    if age >= ttl:
        return None
    return _read_cache(cache)


def _load_remote(url: str, ttl: int) -> str | None:
    """Busca o catálogo remoto com cache local + fallback stale.

    Devolve o texto YAML ou ``None`` (caller cai no bundled). ``ttl < 0`` →
    bundled only; ``ttl == 0`` → ignora cache; senão usa cache se fresca.
    """
    if ttl < 0:
        return None

    cache = clified_home() / "catalog.cache.yaml"
    fresh = _read_cache_if_fresh(cache, ttl)
    if fresh is not None:
        return fresh

    try:
        text = _fetch_text(url)
    except OSError:
        return _read_cache(cache)

    if not text.strip():
        return None

    try:
        cache.parent.mkdir(parents=True, exist_ok=True)
        cache.write_text(text, encoding="utf-8")
    except OSError:
        pass
    return text


def _resolve_catalog_text() -> str:
    """Resolve o texto do catálogo: env override (URL/path) → remoto → bundled."""
    env = os.environ.get("CLIFIED_CATALOG", "").strip()
    ttl = _catalog_ttl()
    if env:
        if _is_url(env):
            return _load_remote(env, ttl) or _bundled_text()
        p = Path(env).expanduser()
        return p.read_text(encoding="utf-8") if p.is_file() else _bundled_text()
    return _load_remote(DEFAULT_CATALOG_URL, ttl) or _bundled_text()


def _parse_entry(key: str, data: dict[str, object]) -> RepoSpec:
    repo = str(data.get("repo", "")).strip()
    if not repo:
        msg = f"Entrada de catálogo inválida ({key!r}): falta 'repo'."
        raise ValueError(msg)
    access = str(data.get("access", "public")).strip().lower() or "public"
    return RepoSpec(
        name=key,
        repo=repo,
        tool=str(data.get("tool", key)).strip() or key,
        tools_yaml=str(data.get("tools_yaml", "tools.yaml")).strip() or "tools.yaml",
        description=str(data.get("description", "")).strip(),
        access=access,
    )


def _parse_yaml_text(text: str) -> dict[str, RepoSpec]:
    raw = yaml.safe_load(text) or {}
    tools = raw.get("tools") or {}
    out: dict[str, RepoSpec] = {}
    for key, data in tools.items():
        if isinstance(data, dict):
            out[str(key).lower()] = _parse_entry(str(key).lower(), data)
    return out


def load_catalog(path: Path | None = None) -> dict[str, RepoSpec]:
    """Carrega o catálogo conhecido (nome → ``RepoSpec``).

    Com ``path`` dado lê o ficheiro local directamente (hermético p/ tests).
    Sem ``path`` segue ``_resolve_catalog_text()`` (remoto + cache + fallback).
    """
    if path is not None:
        if not path.is_file():
            return {}
        return _parse_yaml_text(path.read_text(encoding="utf-8"))
    return _parse_yaml_text(_resolve_catalog_text())


def resolve(name: str) -> RepoSpec:
    """Resolve um nome (case-insensitive) para ``RepoSpec``."""
    data = load_catalog()
    key = name.lower().strip()
    if key in data:
        return data[key]
    available = ", ".join(sorted(data)) or "(nenhuma)"
    msg = f"Ferramenta remota desconhecida: {name!r}. Conhecidas: {available}"
    raise KeyError(msg)


def list_known() -> list[RepoSpec]:
    """Lista as entradas conhecidas do catálogo (ordenadas por nome)."""
    data = load_catalog()
    return [data[k] for k in sorted(data)]


def sources_dir() -> Path:
    """Onde os repositórios remotos são clonados (``~/.clified/sources``)."""
    env = os.environ.get("CLIFIED_SOURCES", "").strip()
    if env:
        return Path(env).expanduser().resolve()
    return clified_home() / "sources"


def _classify_clone_error(repo: str, stderr: str) -> str:
    """Mensagem amigável para falhas de auth/acesso; stderr cru nos restantes."""
    s = (stderr or "").lower()
    if any(marker in s for marker in _AUTH_FAILURE_MARKERS):
        return (
            f"Acesso negado ou repositório inacessível: {repo}\n"
            "Se for privada, requer permissão de leitura no git da organização "
            "(configura chave SSH ou token HTTPS via git credential manager, "
            "ou pede acesso ao responsável)."
        )
    return f"git clone falhou para {repo}:\n{stderr.strip()}"


def clone_or_update(
    spec: RepoSpec,
    dest: Path | None = None,
    *,
    logger: object | None = None,
) -> Path:
    """Clona (ou actualiza com ``git pull``) o repositório e devolve o caminho.

    Levanta ``RuntimeError`` se o ``git`` não estiver disponível ou falhar.
    Erros de auth/acesso produzem mensagem amigável (``_classify_clone_error``).
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
            msg = _classify_clone_error(spec.repo, result.stderr)
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
        msg = _classify_clone_error(spec.repo, result.stderr)
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
