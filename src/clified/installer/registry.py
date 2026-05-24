"""Registry de ferramentas — carregado de ``tools.yaml``."""

from __future__ import annotations

import os
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any

import yaml

TOOLS: dict[str, ToolSpec] = {}
WORKSPACE: WorkspaceConfig | None = None
_CLIFIED_ROOT: Path | None = None


class ToolKind(Enum):
    PYTHON = "python"
    RUST = "rust"
    BUN = "bun"


@dataclass(frozen=True)
class SharedPythonConfig:
    path: str
    import_name: str
    src_subpath: str = "src"


@dataclass(frozen=True)
class WorkspaceConfig:
    root: Path
    name: str
    shared_python: SharedPythonConfig | None = None
    clified_root: Path | None = None

    def resolve(self, relative: str) -> Path:
        return (self.root / relative).resolve()


@dataclass(frozen=True)
class LocalPackage:
    path: str
    import_name: str


@dataclass(frozen=True)
class ToolSpec:
    key: str
    name: str
    kind: ToolKind
    folder: str
    cli_name: str
    description: str

    cargo_bin_name: str = ""
    python_module: str = ""
    min_python: tuple[int, int] = (3, 10)
    max_python: tuple[int, int] | None = None
    extra_aliases: tuple[str, ...] = ()
    needs_pytorch: bool = False
    install_before: tuple[str, ...] = ()
    cross_deps: tuple[str, ...] = ()
    local_packages: tuple[LocalPackage, ...] = ()
    post_install: str = ""
    custom_install: str = ""
    install_before_mode: str = ""  # "" | "venv_only"
    install_order: int | None = None

    bun_cli_script: str = ""
    bun_build_command: str = "build"
    bun_install_args: tuple[str, ...] = ("install", "--frozen-lockfile")

    def project_root(self, workspace: Path) -> Path:
        return workspace / self.folder

    def exists(self, workspace: Path) -> bool:
        root = self.project_root(workspace)
        if self.kind == ToolKind.PYTHON:
            return (root / "setup.py").is_file() or (root / "pyproject.toml").is_file()
        if self.kind == ToolKind.RUST:
            return (root / "Cargo.toml").is_file()
        if self.kind == ToolKind.BUN:
            return (root / "package.json").is_file()
        return root.is_dir()


def clified_root() -> Path:
    """Raiz do pacote Clified (contém ``tools.yaml`` e ``pyproject.toml``)."""
    global _CLIFIED_ROOT
    if _CLIFIED_ROOT is not None:
        return _CLIFIED_ROOT

    env = os.environ.get("CLIFIED_ROOT", "").strip()
    if env:
        _CLIFIED_ROOT = Path(env).resolve()
        return _CLIFIED_ROOT

    _CLIFIED_ROOT = Path(__file__).resolve().parents[3]
    return _CLIFIED_ROOT


def tools_yaml_path() -> Path:
    custom = os.environ.get("CLIFIED_TOOLS", "").strip()
    if custom:
        return Path(custom).resolve()
    return clified_root() / "tools.yaml"


def _parse_python_version(raw: Any, default: tuple[int, int]) -> tuple[int, int]:
    if isinstance(raw, (list, tuple)) and len(raw) >= 2:
        return int(raw[0]), int(raw[1])
    if isinstance(raw, str) and "." in raw:
        major, minor = raw.split(".", 1)
        return int(major), int(minor)
    return default


def _parse_local_packages(raw: Any) -> tuple[LocalPackage, ...]:
    if not raw:
        return ()
    result: list[LocalPackage] = []
    for item in raw:
        if isinstance(item, dict):
            path = str(item.get("path", "")).strip()
            import_name = str(item.get("import_name", "")).strip()
            if path and import_name:
                result.append(LocalPackage(path=path, import_name=import_name))
    return tuple(result)


def _parse_tool(key: str, data: dict[str, Any]) -> ToolSpec:
    kind_str = str(data.get("kind", "python")).lower()
    kind = ToolKind(kind_str)

    return ToolSpec(
        key=key,
        name=str(data.get("name", key)),
        kind=kind,
        folder=str(data.get("folder", key)),
        cli_name=str(data.get("cli_name", key)),
        description=str(data.get("description", "")),
        cargo_bin_name=str(data.get("cargo_bin_name", "")),
        python_module=str(data.get("python_module", "")),
        min_python=_parse_python_version(data.get("min_python"), (3, 10)),
        max_python=_parse_python_version(data["max_python"], (99, 99))
        if data.get("max_python") is not None
        else None,
        extra_aliases=tuple(str(a) for a in data.get("extra_aliases") or ()),
        needs_pytorch=bool(data.get("needs_pytorch", False)),
        install_before=tuple(str(k) for k in data.get("install_before") or ()),
        cross_deps=tuple(str(k) for k in data.get("cross_deps") or ()),
        local_packages=_parse_local_packages(data.get("local_packages")),
        post_install=str(data.get("post_install", "")).strip(),
        custom_install=str(data.get("custom_install", "")).strip(),
        install_before_mode=str(data.get("install_before_mode", "")).strip().lower(),
        install_order=int(data["install_order"])
        if data.get("install_order") is not None
        else None,
        bun_cli_script=str(data.get("bun_cli_script", "")).strip(),
        bun_build_command=str(data.get("bun_build_command", "build")).strip()
        or "build",
        bun_install_args=tuple(
            str(a)
            for a in data.get("bun_install_args") or ("install", "--frozen-lockfile")
        ),
    )


def load_registry(
    path: Path | None = None,
) -> tuple[WorkspaceConfig, dict[str, ToolSpec]]:
    """Carrega ``tools.yaml`` e actualiza o registry global."""
    global TOOLS, WORKSPACE

    yaml_path = path or tools_yaml_path()
    if not yaml_path.is_file():
        msg = (
            f"Registry não encontrado: {yaml_path}\n"
            "Copie tools.yaml.example para tools.yaml e registe as suas ferramentas."
        )
        raise FileNotFoundError(msg)

    raw = yaml.safe_load(yaml_path.read_text(encoding="utf-8")) or {}

    ws_raw = raw.get("workspace") or {}
    root_rel = str(ws_raw.get("root", "..")).strip() or ".."
    ws_root = (clified_root() / root_rel).resolve()

    shared: SharedPythonConfig | None = None
    sp_raw = ws_raw.get("shared_python")
    if isinstance(sp_raw, dict) and sp_raw.get("path") and sp_raw.get("import_name"):
        shared = SharedPythonConfig(
            path=str(sp_raw["path"]),
            import_name=str(sp_raw["import_name"]),
            src_subpath=str(sp_raw.get("src_subpath", "src")),
        )

    workspace = WorkspaceConfig(
        root=ws_root,
        name=str(ws_raw.get("name", "Workspace")),
        shared_python=shared,
        clified_root=clified_root(),
    )

    tools: dict[str, ToolSpec] = {}
    for key, data in (raw.get("tools") or {}).items():
        if not isinstance(data, dict):
            continue
        tools[key.lower()] = _parse_tool(key.lower(), data)

    TOOLS = tools
    WORKSPACE = workspace
    return workspace, tools


def get_workspace() -> WorkspaceConfig:
    if WORKSPACE is None:
        load_registry()
    assert WORKSPACE is not None
    return WORKSPACE


def try_find_workspace_root(_start: Path | None = None) -> Path | None:
    """Devolve a raiz do workspace se ``tools.yaml`` existir."""
    try:
        return get_workspace().root
    except FileNotFoundError:
        return None


def find_workspace_root(start: Path | None = None) -> Path:
    """Devolve a raiz do workspace (onde estão os projectos)."""
    ws = try_find_workspace_root(start)
    if ws is not None:
        return ws
    msg = (
        "Workspace não configurado. Defina CLIFIED_ROOT/CLIFIED_TOOLS "
        "ou crie tools.yaml em clified/."
    )
    raise FileNotFoundError(msg)


def list_available_tools(workspace: Path | None = None) -> list[ToolSpec]:
    if workspace is None:
        workspace = find_workspace_root()
    if not TOOLS:
        load_registry()
    return [spec for spec in TOOLS.values() if spec.exists(workspace)]


def get_tool(name: str) -> ToolSpec:
    if not TOOLS:
        load_registry()

    key = name.lower().replace("-", "").replace("_", "").replace(" ", "")
    for k, spec in TOOLS.items():
        if k == key or spec.cli_name.lower().replace("-", "") == key:
            return spec
        if spec.name.lower().replace(" ", "").replace("-", "") == key:
            return spec
        for alias in spec.extra_aliases:
            if alias.lower().replace("-", "").replace("_", "") == key:
                return spec

    available = ", ".join(sorted(TOOLS.keys())) or "(nenhuma)"
    msg = f"Ferramenta desconhecida: {name!r}. Registadas em tools.yaml: {available}"
    raise KeyError(msg)
