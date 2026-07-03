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
import re
import subprocess
import time
import urllib.request
from contextlib import suppress
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
)
# ``fatal: repository '<url>' not found`` (com a URL entre aspas) não contém o
# substring ``"repository not found"`` — casamos via regex para não recorrer ao
# ``"not found"`` genérico (que colidiria com "branch not found", "path not found").
_REPO_NOT_FOUND_RE = re.compile(r"repository\s+'[^']*'\s+not found")


@dataclass(frozen=True)
class RepoSpec:
    """Entrada do catálogo: nome → repositório + ferramenta."""

    name: str
    repo: str
    tool: str
    tools_yaml: str = "tools.yaml"
    description: str = ""
    access: str = "public"  # "public" | "private" (informational)
    ref: str = ""


_COMMIT_SHA = re.compile(r"^[0-9a-fA-F]{7,40}$")


def parse_tool_at_ref(spec: str) -> tuple[str, str]:
    """Divide ``nome@ref`` no último ``@``."""
    if "@" not in spec:
        return spec.strip(), ""
    name, ref = spec.rsplit("@", 1)
    return name.strip(), ref.strip()


def with_ref(spec: RepoSpec, ref: str) -> RepoSpec:
    """Devolve cópia de ``spec`` com ``ref`` (imutável)."""
    if not ref or ref == spec.ref:
        return spec
    return RepoSpec(
        name=spec.name,
        repo=spec.repo,
        tool=spec.tool,
        tools_yaml=spec.tools_yaml,
        description=spec.description,
        access=spec.access,
        ref=ref,
    )


def _is_commit_sha(ref: str) -> bool:
    return bool(_COMMIT_SHA.fullmatch(ref.strip()))


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


def _fetch_text(url: str, timeout: float = 5.0, *, bust_cache: bool = False) -> str:
    """Busca o texto de uma URL; levanta ``OSError`` em falha de rede/HTTP.

    Com ``bust_cache=True`` (usado em ``--refresh-catalog``) anexa um query
    ``?v=<ts>`` para o CDN do raw.githubusercontent.com não servir snapshot
    antigo — o header ``Cache-Control: no-cache`` só por si não é fiável lá.
    A cache local (TTL) continua a ser a camada de caching do clified.
    """
    fetch_url = url
    if bust_cache and "?" not in url:
        fetch_url = f"{url}?v={int(time.time())}"
    elif bust_cache:
        fetch_url = f"{url}&v={int(time.time())}"
    req = urllib.request.Request(  # noqa: S310 - URL do catálogo é trusted/default
        fetch_url,
        headers={
            "User-Agent": f"clified/{version()}",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
        },
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
        text = _fetch_text(url, bust_cache=(ttl == 0))
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
    ref = str(data.get("ref", "")).strip()
    return RepoSpec(
        name=key,
        repo=repo,
        tool=str(data.get("tool", key)).strip() or key,
        tools_yaml=str(data.get("tools_yaml", "tools.yaml")).strip() or "tools.yaml",
        description=str(data.get("description", "")).strip(),
        access=access,
        ref=ref,
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
    """Onde os repositórios remotos são clonados (``~/.config/clified/sources``)."""
    env = os.environ.get("CLIFIED_SOURCES", "").strip()
    if env:
        return Path(env).expanduser().resolve()
    return clified_home() / "sources"


def _classify_clone_error(repo: str, stderr: str) -> str:
    """Mensagem amigável para falhas de auth/acesso; stderr cru nos restantes."""
    s = (stderr or "").lower()
    if any(
        marker in s for marker in _AUTH_FAILURE_MARKERS
    ) or _REPO_NOT_FOUND_RE.search(s):
        return (
            f"Acesso negado ou repositório inacessível: {repo}\n"
            "Se for privada, requer permissão de leitura no git da organização "
            "(configura chave SSH ou token HTTPS via git credential manager, "
            "ou pede acesso ao responsável)."
        )
    return f"git clone falhou para {repo}:\n{stderr.strip()}"


def git_head_commit(repo_dir: Path) -> str:
    """SHA do HEAD no clone local."""
    result = subprocess.run(
        ["git", "-C", str(repo_dir), "rev-parse", "HEAD"],
        check=False,
        capture_output=True,
        text=True,
    )
    return (result.stdout or "").strip() if result.returncode == 0 else ""


def current_branch(repo_dir: Path) -> str | None:
    """Branch actual (None se em detached HEAD)."""
    r = _git_run(["git", "symbolic-ref", "-q", "--short", "HEAD"], cwd=repo_dir)
    if r.returncode == 0 and r.stdout.strip():
        return r.stdout.strip()
    return None


def _default_branch(repo_dir: Path) -> str:
    """Detecta o branch por omissão do remote."""
    r = _git_run(
        ["git", "symbolic-ref", "--short", "refs/remotes/origin/HEAD"], cwd=repo_dir
    )
    if r.returncode == 0 and r.stdout.strip():
        return r.stdout.strip().split("/", 1)[-1]
    for cand in ("main", "master", "trunk"):
        c = _git_run(
            ["git", "rev-parse", "--verify", "--quiet", f"refs/remotes/origin/{cand}"],
            cwd=repo_dir,
        )
        if c.returncode == 0:
            return cand
    b = _git_run(
        ["git", "for-each-ref", "--format=%(refname:short)", "refs/remotes/origin"],
        cwd=repo_dir,
    )
    for line in (b.stdout or "").splitlines():
        name = line.strip()
        if name and name.lower() != "head":
            return name.split("/", 1)[-1]
    return "main"


def _git_run(
    args: list[str], *, cwd: Path | None = None
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        cwd=str(cwd) if cwd else None,
        check=False,
        capture_output=True,
        text=True,
    )


def _clone_shallow(repo: str, dest: Path, ref: str) -> None:
    if _is_commit_sha(ref):
        dest.mkdir(parents=True, exist_ok=True)
        init = _git_run(["git", "init"], cwd=dest)
        if init.returncode != 0:
            raise RuntimeError(init.stderr.strip() or "git init falhou")
        remote = _git_run(["git", "remote", "add", "origin", repo], cwd=dest)
        if remote.returncode != 0:
            raise RuntimeError(remote.stderr.strip() or "git remote add falhou")
        # Shallow-by-SHA needs server-side allowReachableSHA1InWant (GitHub has
        # it; local/bare repos usually don't). Fall back to a full fetch.
        fetch = _git_run(["git", "fetch", "--depth", "1", "origin", ref], cwd=dest)
        if fetch.returncode != 0:
            fetch = _git_run(["git", "fetch", "origin"], cwd=dest)
            if fetch.returncode != 0:
                raise RuntimeError(fetch.stderr.strip() or "git fetch falhou")
        checkout = _git_run(["git", "checkout", ref], cwd=dest)
        if checkout.returncode != 0:
            raise RuntimeError(checkout.stderr.strip() or "git checkout falhou")
        return

    cmd = ["git", "clone", "--depth", "1"]
    if ref:
        cmd.extend(["--branch", ref])
    cmd.extend([repo, str(dest)])
    result = _git_run(cmd)
    if result.returncode != 0:
        msg = _classify_clone_error(repo, result.stderr)
        raise RuntimeError(msg)


def _checkout_ref(dest: Path, repo: str, ref: str) -> None:
    if not ref:
        return
    if _is_commit_sha(ref):
        fetch = _git_run(["git", "fetch", "--depth", "1", "origin", ref], cwd=dest)
        if fetch.returncode != 0:
            # Short SHAs are rejected as ref names by the server, and on a
            # shallow clone ``git fetch origin`` only brings ref tips (not old
            # SHAs). Unshallow to fetch full history so the SHA is present
            # locally; fall back to a plain fetch if the clone isn't shallow.
            fetch = _git_run(["git", "fetch", "--unshallow", "origin"], cwd=dest)
            if fetch.returncode != 0:
                fetch = _git_run(["git", "fetch", "origin"], cwd=dest)
                if fetch.returncode != 0:
                    msg = fetch.stderr.strip() or f"git fetch falhou para {repo}"
                    raise RuntimeError(msg)
        checkout = _git_run(["git", "checkout", ref], cwd=dest)
    else:
        fetch = _git_run(["git", "fetch", "--depth", "1", "origin", ref], cwd=dest)
        if fetch.returncode != 0:
            msg = fetch.stderr.strip() or f"git fetch falhou para {repo}"
            raise RuntimeError(msg)
        checkout = _git_run(["git", "checkout", ref], cwd=dest)
    if checkout.returncode != 0:
        msg = checkout.stderr.strip() or f"git checkout falhou para {repo}@{ref}"
        raise RuntimeError(msg)


def clone_or_update(
    spec: RepoSpec,
    dest: Path | None = None,
    *,
    logger: object | None = None,
    force_ref: bool = False,
) -> Path:
    """Clona (ou actualiza) o repositório e devolve o caminho.

    Com ``spec.ref`` usa branch/tag ou SHA (7-40 hex). ``force_ref`` força
    checkout mesmo quando o clone já existe.
    """
    dest = dest or (sources_dir() / spec.name)
    dest.parent.mkdir(parents=True, exist_ok=True)
    ref = (spec.ref or "").strip()

    if (dest / ".git").is_dir():
        if ref and force_ref:
            if logger is not None:
                _log(logger, f"Checkout {spec.name}@{ref} ({dest})...")
            _checkout_ref(dest, spec.repo, ref)
            return dest.resolve()
        if ref:
            current = git_head_commit(dest)
            if logger is not None:
                _log(logger, f"Actualizando {spec.name}@{ref or 'HEAD'} ({dest})...")
            if _is_commit_sha(ref):
                if current.startswith(ref) or ref.startswith(current):
                    return dest.resolve()
                _checkout_ref(dest, spec.repo, ref)
                return dest.resolve()
            fetch = _git_run(["git", "fetch", "--depth", "1", "origin", ref], cwd=dest)
            if fetch.returncode != 0:
                msg = _classify_clone_error(spec.repo, fetch.stderr)
                raise RuntimeError(msg)
            pull = _git_run(["git", "pull", "--ff-only", "origin", ref], cwd=dest)
            if pull.returncode != 0:
                checkout = _git_run(["git", "checkout", ref], cwd=dest)
                if checkout.returncode != 0:
                    msg = _classify_clone_error(
                        spec.repo, pull.stderr or checkout.stderr
                    )
                    raise RuntimeError(msg)
            return dest.resolve()

        if logger is not None:
            _log(logger, f"Actualizando {spec.name} ({dest})...")
        branch = current_branch(dest)
        if branch is None:
            # detached HEAD (ex.: pin de SHA anterior) — voltar ao branch por omissão
            branch = _default_branch(dest)
            _git_run(["git", "checkout", "-B", branch, f"origin/{branch}"], cwd=dest)
            result = _git_run(
                ["git", "-C", str(dest), "pull", "--ff-only", "origin", branch]
            )
        else:
            result = _git_run(["git", "-C", str(dest), "pull", "--ff-only"])
        if result.returncode != 0:
            msg = _classify_clone_error(spec.repo, result.stderr)
            raise RuntimeError(msg)
        return dest.resolve()

    if logger is not None:
        label = f"{spec.repo}@{ref}" if ref else spec.repo
        _log(logger, f"A clonar {label} para {dest}...")
    if dest.exists():
        rm_tree(dest)
    _clone_shallow(spec.repo, dest, ref)
    return dest.resolve()


def pull_ff_only(repo_dir: Path) -> subprocess.CompletedProcess[str]:
    """``git pull --ff-only`` no clone local."""
    return _git_run(["git", "-C", str(repo_dir), "pull", "--ff-only"])


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


def rm_tree(path: Path) -> None:
    """Remove árvore robustamente (ficheiros read-only do git no Windows)."""
    import shutil
    import stat

    def _onexc(func: object, p: str | Path, _exc: object) -> None:
        with suppress(OSError):
            Path(p).chmod(stat.S_IWRITE)
        with suppress(OSError):
            func(p)

    try:
        shutil.rmtree(path, onexc=_onexc)
    except TypeError:  # Python < 3.12 (sem onexc)

        def _onerror(func: object, p: str | Path, _exc_info: object) -> None:
            _onexc(func, p, None)

        shutil.rmtree(path, onerror=_onerror)


def iter_known_names() -> Iterable[str]:
    """Itera os nomes conhecidos (compatibilidade com helpers externos)."""
    return iter(sorted(load_catalog()))
