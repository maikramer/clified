"""Instalador unificado Clified."""

from __future__ import annotations

import argparse
import importlib
import os
import platform
import sys
from collections.abc import Callable
from pathlib import Path

from clified.core.retry import RetryEngine, RetryPolicy
from clified.logging import Logger
from clified.patterns import get_pattern_loader

from .bun_installer import BunProjectInstaller
from .python_installer import PythonProjectInstaller
from .registry import (
    TOOLS,
    ToolKind,
    ToolSpec,
    WorkspaceConfig,
    get_tool,
    get_workspace,
    list_available_tools,
    load_registry,
)
from .rust_installer import RustProjectInstaller


def _diagnose_failure(message: str, logger: Logger) -> None:
    try:
        diagnosis = get_pattern_loader().get_diagnosis(message)
        if diagnosis:
            logger.warn(f"Diagnóstico: {diagnosis['diagnosis']}")
            for i, solution in enumerate(diagnosis.get("solutions") or [], 1):
                logger.info(f"  {i}. {solution}")
    except Exception:
        pass


def _run_with_retry(action: str, func: Callable[[], bool], logger: Logger) -> bool:
    if os.environ.get("CLIFIED_RETRY", "").strip().lower() not in ("1", "true", "yes"):
        ok = func()
        if not ok:
            _diagnose_failure(f"install action {action} failed", logger)
        return ok

    engine = RetryEngine(policy=RetryPolicy(max_attempts=3, base_delay=2.0), logger=logger)
    result = engine.execute(func)
    if not result.success and result.final_exception:
        _diagnose_failure(str(result.final_exception), logger)
    return result.success


def _run_post_install(spec: ToolSpec, installer: PythonProjectInstaller) -> bool:
    if not spec.post_install:
        return True
    if ":" not in spec.post_install:
        Logger().error(f"post_install inválido (esperado modulo:funcao): {spec.post_install!r}")
        return False
    module_path, func_name = spec.post_install.rsplit(":", 1)
    try:
        mod = importlib.import_module(module_path)
        func = getattr(mod, func_name)
        result = func(installer)
        return result is not False
    except Exception as exc:
        Logger().error(f"post_install falhou ({spec.post_install}): {exc}")
        return False


def _resolve_cross_deps(spec: ToolSpec, workspace: WorkspaceConfig) -> list[tuple[Path, str]]:
    result: list[tuple[Path, str]] = []
    for dep_key in spec.cross_deps:
        try:
            sibling = get_tool(dep_key)
        except KeyError:
            continue
        src_dir = (workspace.root / sibling.folder / "src").resolve()
        if sibling.python_module and src_dir.is_dir():
            result.append((src_dir, sibling.python_module))
    return result


class _ToolPythonInstaller(PythonProjectInstaller):
    """Adaptador: PythonProjectInstaller a partir de um ToolSpec."""

    def __init__(
        self,
        spec: ToolSpec,
        workspace: WorkspaceConfig,
        *,
        install_prefix: Path | None = None,
        python_cmd: str = "python3",
        use_venv: bool = False,
        skip_deps: bool = False,
        skip_models: bool = False,
        force: bool = False,
    ) -> None:
        cross_deps = _resolve_cross_deps(spec, workspace)
        super().__init__(
            project_name=spec.name,
            cli_name=spec.cli_name,
            project_root=spec.project_root(workspace.root),
            install_prefix=install_prefix,
            python_cmd=python_cmd,
            use_venv=use_venv,
            skip_deps=skip_deps,
            skip_models=skip_models,
            force=force,
            skip_pytorch=not spec.needs_pytorch,
            min_python=spec.min_python,
            max_python=spec.max_python,
            cross_dep_folders=cross_deps,
            python_module=spec.python_module or None,
            shared_python=workspace.shared_python,
            workspace_root=workspace.root,
            local_packages=spec.local_packages,
        )
        self.spec = spec

    def check_python(self, min_version: tuple[int, int] = (3, 10)) -> bool:
        if self._use_uv:
            self.logger.info(
                f"uv disponível — Python {self.spec.min_python[0]}.{self.spec.min_python[1]}+ "
                "será provisionado ao criar o venv."
            )
            return True
        return super().check_python(min_version=self.spec.min_python)

    def run(self) -> bool:
        for dep_key in self.spec.install_before:
            self.logger.step(f"Instalando dependência: {dep_key}")
            if not install_tool(
                dep_key,
                workspace=self._workspace(),
                install_prefix=self.install_prefix,
                python_cmd=self.python_cmd,
                use_venv=self.use_venv,
                skip_deps=self.skip_deps,
                skip_models=self.skip_models,
                force=self.force,
            ):
                self.logger.error(f"Falha ao instalar dependência {dep_key!r}")
                return False

        if not super().run():
            return False

        if not _run_post_install(self.spec, self):
            return False

        aliases = list(self.spec.extra_aliases) if self.spec.extra_aliases else None
        self.create_cli_wrappers(extra_aliases=aliases)
        self.create_activate_wrapper()
        self.check_path()

        cmds = [f"{self.cli_name} --help"]
        self.show_summary(commands=cmds)
        return True

    def _workspace(self) -> WorkspaceConfig:
        return get_workspace()


class _ToolRustInstaller(RustProjectInstaller):
    def __init__(
        self,
        spec: ToolSpec,
        workspace: WorkspaceConfig,
        *,
        install_prefix: Path | None = None,
    ) -> None:
        super().__init__(
            project_name=spec.name,
            cli_name=spec.cli_name,
            project_root=spec.project_root(workspace.root),
            cargo_bin_name=spec.cargo_bin_name or spec.cli_name,
            install_prefix=install_prefix,
        )
        self.spec = spec


def install_tool(
    name: str,
    *,
    workspace: WorkspaceConfig | None = None,
    action: str = "install",
    install_prefix: Path | None = None,
    python_cmd: str = "python3",
    use_venv: bool = False,
    skip_deps: bool = False,
    skip_models: bool = False,
    force: bool = False,
) -> bool:
    if workspace is None:
        load_registry()
        workspace = get_workspace()

    spec = get_tool(name)

    if not spec.exists(workspace.root):
        Logger().error(f"Diretório não encontrado: {spec.project_root(workspace.root)}")
        return False

    inst: PythonProjectInstaller | RustProjectInstaller | BunProjectInstaller
    if spec.kind == ToolKind.PYTHON:
        inst = _ToolPythonInstaller(
            spec,
            workspace,
            install_prefix=install_prefix,
            python_cmd=python_cmd,
            use_venv=use_venv,
            skip_deps=skip_deps,
            skip_models=skip_models,
            force=force,
        )
    elif spec.kind == ToolKind.RUST:
        inst = _ToolRustInstaller(spec, workspace, install_prefix=install_prefix)
    elif spec.kind == ToolKind.BUN:
        cli_script = None
        if spec.bun_cli_script:
            cli_script = spec.project_root(workspace.root) / spec.bun_cli_script
        inst = BunProjectInstaller(
            project_name=spec.name,
            cli_name=spec.cli_name,
            project_root=spec.project_root(workspace.root),
            install_prefix=install_prefix,
            cli_script=cli_script,
            build_command=spec.bun_build_command,
            install_args=spec.bun_install_args,
        )
    else:
        Logger().error(f"Tipo não suportado: {spec.kind}")
        return False

    logger = Logger()

    if action == "install":
        return _run_with_retry("install", inst.run, logger)
    if action == "uninstall":
        return inst.run_uninstall()
    if action == "reinstall":
        return _run_with_retry("reinstall", inst.run_reinstall, logger)

    Logger().error(f"Acção desconhecida: {action}")
    return False


def _install_all_sort_key(spec: ToolSpec) -> tuple[int, str]:
    rank = 0
    if spec.needs_pytorch:
        rank = 0
    elif spec.kind == ToolKind.PYTHON:
        rank = 1
    elif spec.kind == ToolKind.RUST:
        rank = 2
    else:
        rank = 3
    return (rank, spec.cli_name.lower())


def install_all(
    *,
    workspace: WorkspaceConfig | None = None,
    install_prefix: Path | None = None,
    python_cmd: str = "python3",
    use_venv: bool = False,
    skip_deps: bool = False,
    skip_models: bool = False,
    force: bool = False,
) -> bool:
    if workspace is None:
        load_registry()
        workspace = get_workspace()

    logger = Logger()
    tools = sorted(list_available_tools(workspace.root), key=_install_all_sort_key)
    if not tools:
        logger.error("Nenhuma ferramenta encontrada. Registe projectos em tools.yaml.")
        return False

    prev = os.environ.get("CLIFIED_INSTALL_ALL")
    prev_uv = os.environ.get("UV_CONCURRENT_BUILDS")
    os.environ["CLIFIED_INSTALL_ALL"] = "1"
    os.environ.setdefault("UV_CONCURRENT_BUILDS", "4")

    try:
        logger.header(f"Instalando {len(tools)} ferramentas")
        results: dict[str, bool] = {}

        for spec in tools:
            logger.header(f"→ {spec.name}")
            try:
                ok = install_tool(
                    spec.key,
                    workspace=workspace,
                    install_prefix=install_prefix,
                    python_cmd=python_cmd,
                    use_venv=use_venv,
                    skip_deps=skip_deps,
                    skip_models=skip_models,
                    force=force,
                )
            except Exception as exc:
                logger.error(f"{spec.name}: {exc}")
                ok = False
            results[spec.name] = ok

        logger.header("Resumo")
        for name, ok in results.items():
            if ok:
                logger.success(f"{name}: OK")
            else:
                logger.error(f"{name}: FALHOU")

        return all(results.values())
    finally:
        if prev is None:
            os.environ.pop("CLIFIED_INSTALL_ALL", None)
        else:
            os.environ["CLIFIED_INSTALL_ALL"] = prev
        if prev_uv is None:
            os.environ.pop("UV_CONCURRENT_BUILDS", None)
        else:
            os.environ["UV_CONCURRENT_BUILDS"] = prev_uv


def main(argv: list[str] | None = None) -> int:
    os.environ.setdefault("UV_VENV_CLEAR", "1")
    os.environ.setdefault("UV_LINK_MODE", "copy")

    try:
        load_registry()
    except FileNotFoundError as e:
        Logger().error(str(e))
        return 1

    workspace = get_workspace()
    available = list_available_tools(workspace.root)
    tool_names = sorted(TOOLS.keys())

    parser = argparse.ArgumentParser(
        prog="clified-install",
        description=(
            "Instalador universal Clified. "
            "Registe ferramentas em tools.yaml (Python, Rust ou Bun)."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=_build_epilog(available, workspace),
    )

    parser.add_argument(
        "tool",
        nargs="?",
        default=None,
        help="Ferramenta a instalar (ou 'all'). Opções: " + ", ".join([*tool_names, "all"]),
    )
    parser.add_argument(
        "--action",
        choices=["install", "uninstall", "reinstall"],
        default="install",
        help="Acção (default: install)",
    )
    parser.add_argument("--list", action="store_true", help="Listar ferramentas disponíveis")
    parser.add_argument("--all", action="store_true", help="Instalar todas as ferramentas")
    parser.add_argument("--prefix", default=None, help="Prefixo de instalação (default: ~/.local)")
    parser.add_argument(
        "--use-venv",
        action="store_true",
        help="(Legado) O instalador cria projecto/.venv automaticamente.",
    )
    parser.add_argument("--skip-deps", action="store_true", help="Não instalar deps de sistema")
    parser.add_argument("--skip-models", action="store_true", help="Reservado para hooks futuros")
    parser.add_argument("--force", action="store_true", help="Forçar reinstalação")
    parser.add_argument(
        "--python",
        default="python" if platform.system() == "Windows" else "python3",
        help="Comando Python",
    )

    args = parser.parse_args(argv)
    logger = Logger()

    if args.list:
        _print_tool_list(available, workspace, logger)
        return 0

    if args.all and args.tool is not None:
        parser.error("Não uses --all juntamente com o nome da ferramenta.")

    effective_tool = "all" if args.all else args.tool
    if effective_tool is None:
        parser.print_help()
        return 0

    prefix = Path(args.prefix) if args.prefix else None

    if effective_tool.lower() == "all":
        ok = install_all(
            workspace=workspace,
            install_prefix=prefix,
            python_cmd=args.python,
            use_venv=args.use_venv,
            skip_deps=args.skip_deps,
            skip_models=args.skip_models,
            force=args.force,
        )
    else:
        ok = install_tool(
            effective_tool,
            workspace=workspace,
            action=args.action,
            install_prefix=prefix,
            python_cmd=args.python,
            use_venv=args.use_venv,
            skip_deps=args.skip_deps,
            skip_models=args.skip_models,
            force=args.force,
        )

    return 0 if ok else 1


def _build_epilog(available: list[ToolSpec], workspace: WorkspaceConfig) -> str:
    lines = [
        f"Workspace: {workspace.name} ({workspace.root})",
        "",
        "Ferramentas disponíveis:",
        "",
    ]
    for spec in available:
        kind = spec.kind.value.capitalize()
        lines.append(f"  {spec.cli_name:<16s}  [{kind}]  {spec.description}")
    lines.extend(
        [
            "",
            "Exemplos:",
            "  clified-install mytool              # Instalar ferramenta Python",
            "  clified-install myrust              # Instalar CLI Rust",
            "  clified-install all                 # Todas as ferramentas registadas",
            "  clified-install --list              # Listar ferramentas",
            "  clified-install mytool --action uninstall",
        ]
    )
    return "\n".join(lines)


def _print_tool_list(available: list[ToolSpec], workspace: WorkspaceConfig, logger: Logger) -> None:
    rows = [(f"Workspace", str(workspace.root))]
    for spec in available:
        kind = spec.kind.value.capitalize()
        rows.append((f"{spec.cli_name} [{kind}]", spec.description))
    logger.table(rows, title=f"Ferramentas — {workspace.name}")


if __name__ == "__main__":
    sys.exit(main())
