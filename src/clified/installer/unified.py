"""Instalador unificado Clified."""

from __future__ import annotations

import argparse
import importlib
import os
import platform
import sys
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from clified.cli.output import OutputFormatter
from clified.core.retry import RetryEngine, RetryPolicy
from clified.logging import Logger
from clified.patterns import get_pattern_loader
from clified.paths import tools_yaml_path

from .bun_installer import BunProjectInstaller
from .python_installer import PythonProjectInstaller
from .receipts import InstallReceipt, InstallResult, record_install, remove as remove_receipt
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


@dataclass
class ReceiptContext:
    """Metadados para gravar receipt após instalação."""

    receipt_key: str
    source: str = "local"  # catalog | repo | local
    catalog_name: str = ""
    repo: str = ""
    ref: str = ""
    commit: str = ""
    repo_clone_path: str = ""
    tools_yaml: str = ""


def _build_receipt(
    spec: ToolSpec,
    inst: PythonProjectInstaller | RustProjectInstaller | BunProjectInstaller,
    ctx: ReceiptContext,
) -> InstallReceipt:
    venv_path = ""
    if hasattr(inst, "venv_dir"):
        venv_path = str(inst.venv_dir)
    artifacts = inst.collect_artifacts()
    if venv_path and venv_path not in artifacts:
        artifacts.append(venv_path)
    workspace = get_workspace()
    project_root = str(spec.project_root(workspace.root))
    ty = ctx.tools_yaml or os.environ.get("CLIFIED_TOOLS", str(tools_yaml_path()))
    return InstallReceipt(
        kind=spec.kind.value,
        cli_name=spec.cli_name,
        source=ctx.source,
        repo=ctx.repo,
        ref=ctx.ref,
        commit=ctx.commit,
        tools_yaml=ty,
        project_root=project_root,
        venv_path=venv_path,
        catalog_name=ctx.catalog_name,
        install_prefix=str(inst.install_prefix),
        artifacts=artifacts,
    )


def _diagnose_failure(message: str, logger: Logger) -> None:
    try:
        diagnosis = get_pattern_loader().get_diagnosis(message)
        if diagnosis:
            logger.warn(f"Diagnóstico: {diagnosis['diagnosis']}")
            for i, solution in enumerate(diagnosis.get("solutions") or [], 1):
                logger.info(f"  {i}. {solution}")
    except Exception:
        pass


def _run_with_retry(
    action: str,
    func: Callable[[], bool],
    logger: Logger,
    *,
    max_attempts: int | None = None,
) -> bool:
    if max_attempts is None:
        env = os.environ.get("CLIFIED_RETRY", "").strip().lower() in (
            "1",
            "true",
            "yes",
        )
        max_attempts = 3 if env else 1
    if max_attempts <= 1:
        ok = func()
        if not ok:
            _diagnose_failure(f"install action {action} failed", logger)
        return ok

    engine = RetryEngine(
        policy=RetryPolicy(max_attempts=max_attempts, base_delay=2.0), logger=logger
    )
    result = engine.execute(func)
    if not result.success and result.final_exception:
        _diagnose_failure(str(result.final_exception), logger)
    return result.success


def _run_hook(hook: str, installer: PythonProjectInstaller) -> bool:
    if not hook:
        return True
    if ":" not in hook:
        Logger().error(f"Hook inválido (esperado modulo:funcao): {hook!r}")
        return False
    module_path, func_name = hook.rsplit(":", 1)
    project_root = getattr(installer, "project_root", None)
    inserted: list[str] = []
    paths: list[str] = []
    shared = getattr(installer, "shared_python", None)
    workspace_root = getattr(installer, "workspace_root", None)
    if shared is not None and workspace_root is not None:
        shared_src = Path(workspace_root) / shared.path / shared.src_subpath
        if shared_src.is_dir():
            paths.append(str(shared_src.resolve()))
    if project_root is not None:
        paths.append(str(Path(project_root).resolve()))
    for path_str in paths:
        if path_str not in sys.path:
            sys.path.insert(0, path_str)
            inserted.append(path_str)
    try:
        mod = importlib.import_module(module_path)
        func = getattr(mod, func_name)
        result = func(installer)
        return result is not False
    except Exception as exc:
        Logger().error(f"Hook falhou ({hook}): {exc}")
        return False
    finally:
        for _ in inserted:
            if sys.path and sys.path[0] in inserted:
                sys.path.pop(0)


def _run_post_install(spec: ToolSpec, installer: PythonProjectInstaller) -> bool:
    return _run_hook(spec.post_install, installer)


def _resolve_cross_deps(
    spec: ToolSpec, workspace: WorkspaceConfig
) -> list[tuple[Path, str]]:
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
        retry_attempts: int | None = None,
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
        self.retry_attempts = retry_attempts

    def install_in_venv(self) -> None:
        if self.spec.custom_install:
            if not _run_hook(self.spec.custom_install, self):
                msg = f"custom_install falhou: {self.spec.custom_install}"
                raise RuntimeError(msg)
            return
        super().install_in_venv()

    def check_python(self, _min_version: tuple[int, int] = (3, 10)) -> bool:
        if self._use_uv:
            self.logger.info(
                f"uv disponível — Python {self.spec.min_python[0]}.{self.spec.min_python[1]}+ "
                "será provisionado ao criar o venv."
            )
            return True
        return super().check_python(min_version=self.spec.min_python)

    def run(self) -> bool:
        skip_before = self.spec.install_before_mode == "venv_only"
        for dep_key in self.spec.install_before:
            if skip_before:
                self.logger.info(
                    f"install_before_mode=venv_only: {dep_key!r} via cross_deps/.pth apenas"
                )
                continue
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
                retry_attempts=self.retry_attempts,
            ):
                self.logger.error(f"Falha ao instalar dependência {dep_key!r}")
                return False

        if not super().run():
            return False

        aliases = list(self.spec.extra_aliases) if self.spec.extra_aliases else None
        self.create_cli_wrappers(extra_aliases=aliases)

        if not _run_post_install(self.spec, self):
            return False

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

    def run(self) -> bool:
        if not super().run():
            return False
        if self.spec.post_install:
            return _run_post_install(self.spec, self)
        return True


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
    retry_attempts: int | None = None,
    receipt_ctx: ReceiptContext | None = None,
) -> InstallResult:
    if workspace is None:
        load_registry()
        workspace = get_workspace()

    t0 = time.perf_counter()
    spec = get_tool(name)

    if not spec.exists(workspace.root):
        Logger().error(f"Diretório não encontrado: {spec.project_root(workspace.root)}")
        return InstallResult(
            tool=name,
            action=action,
            ok=False,
            duration_ms=(time.perf_counter() - t0) * 1000,
            error="project directory missing",
        )

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
            retry_attempts=retry_attempts,
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
        return InstallResult(
            tool=name,
            action=action,
            ok=False,
            duration_ms=(time.perf_counter() - t0) * 1000,
            error=f"unsupported kind: {spec.kind}",
        )

    logger = Logger()
    ctx = receipt_ctx or ReceiptContext(receipt_key=spec.key, source="local")
    ok = False

    if action in ("install", "update"):
        if action == "update":
            os.environ["UV_VENV_CLEAR"] = "0"
        ok = _run_with_retry(action, inst.run, logger, max_attempts=retry_attempts)
    elif action == "uninstall":
        ok = inst.run_uninstall()
        if ok:
            remove_receipt(ctx.receipt_key)
    elif action == "reinstall":
        ok = _run_with_retry(
            "reinstall", inst.run_reinstall, logger, max_attempts=retry_attempts
        )
    else:
        Logger().error(f"Acção desconhecida: {action}")
        return InstallResult(
            tool=name,
            action=action,
            ok=False,
            duration_ms=(time.perf_counter() - t0) * 1000,
            error=f"unknown action: {action}",
        )

    duration_ms = (time.perf_counter() - t0) * 1000
    artifacts = inst.collect_artifacts() if ok else []

    if ok and action in ("install", "update", "reinstall"):
        record_install(ctx.receipt_key, _build_receipt(spec, inst, ctx))

    return InstallResult(
        tool=name,
        action=action,
        ok=ok,
        duration_ms=duration_ms,
        artifacts=artifacts,
    )


def _install_all_sort_key(spec: ToolSpec) -> tuple[int, str]:
    if spec.install_order is not None:
        return (spec.install_order, spec.cli_name.lower())
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
    retry_attempts: int | None = None,
    receipt_ctx_factory: Callable[[ToolSpec], ReceiptContext] | None = None,
) -> tuple[bool, list[InstallResult]]:
    if workspace is None:
        load_registry()
        workspace = get_workspace()

    logger = Logger()
    tools = sorted(list_available_tools(workspace.root), key=_install_all_sort_key)
    if not tools:
        logger.error("Nenhuma ferramenta encontrada. Registe projectos em tools.yaml.")
        return False, []

    prev = os.environ.get("CLIFIED_INSTALL_ALL")
    prev_uv = os.environ.get("UV_CONCURRENT_BUILDS")
    os.environ["CLIFIED_INSTALL_ALL"] = "1"
    os.environ.setdefault("UV_CONCURRENT_BUILDS", "4")

    install_results: list[InstallResult] = []
    try:
        logger.header(f"Instalando {len(tools)} ferramentas")
        results: dict[str, bool] = {}

        for spec in tools:
            logger.header(f"→ {spec.name}")
            ctx = (
                receipt_ctx_factory(spec)
                if receipt_ctx_factory
                else ReceiptContext(receipt_key=spec.key, source="local")
            )
            try:
                result = install_tool(
                    spec.key,
                    workspace=workspace,
                    install_prefix=install_prefix,
                    python_cmd=python_cmd,
                    use_venv=use_venv,
                    skip_deps=skip_deps,
                    skip_models=skip_models,
                    force=force,
                    retry_attempts=retry_attempts,
                    receipt_ctx=ctx,
                )
                ok = bool(result)
                install_results.append(result)
            except Exception as exc:
                logger.error(f"{spec.name}: {exc}")
                ok = False
                install_results.append(
                    InstallResult(tool=spec.key, action="install", ok=False, error=str(exc))
                )
            results[spec.name] = ok

        logger.header("Resumo")
        for name, ok in results.items():
            if ok:
                logger.success(f"{name}: OK")
            else:
                logger.error(f"{name}: FALHOU")

        return all(results.values()), install_results
    finally:
        if prev is None:
            os.environ.pop("CLIFIED_INSTALL_ALL", None)
        else:
            os.environ["CLIFIED_INSTALL_ALL"] = prev
        if prev_uv is None:
            os.environ.pop("UV_CONCURRENT_BUILDS", None)
        else:
            os.environ["UV_CONCURRENT_BUILDS"] = prev_uv


def _build_parser() -> argparse.ArgumentParser:
    """Constrói o parser do CLI (epilog estático; ferramentas via ``--list``)."""
    parser = argparse.ArgumentParser(
        prog="clified-install",
        description=(
            "Instalador universal Clified. "
            "Registe ferramentas em tools.yaml (Python, Rust ou Bun) "
            "ou busque uma remota com --get."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=_build_static_epilog(),
    )
    parser.add_argument(
        "tool",
        nargs="?",
        default=None,
        help="Ferramenta a instalar (ou 'all'). Use --list para ver as disponíveis.",
    )
    parser.add_argument(
        "--action",
        choices=["install", "update", "uninstall", "reinstall"],
        default="install",
        help="Acção (default: install). update = refrescar reaproveitando o venv",
    )
    parser.add_argument(
        "--list", action="store_true", help="Listar ferramentas disponíveis"
    )
    parser.add_argument(
        "--doctor",
        action="store_true",
        help="Diagnosticar saúde das ferramentas (venv, Python, wrappers, PATH)",
    )
    parser.add_argument(
        "--fix",
        action="store_true",
        help="Com --doctor: remover wrappers que ofuscam o CLI no PATH",
    )
    parser.add_argument(
        "--all", action="store_true", help="Instalar todas as ferramentas"
    )
    parser.add_argument(
        "--prefix", default=None, help="Prefixo de instalação (default: ~/.local)"
    )
    parser.add_argument(
        "--use-venv",
        action="store_true",
        help="(Legado) O instalador cria projecto/.venv automaticamente.",
    )
    parser.add_argument(
        "--skip-deps", action="store_true", help="Não instalar deps de sistema"
    )
    parser.add_argument(
        "--skip-models", action="store_true", help="Reservado para hooks futuros"
    )
    parser.add_argument("--force", action="store_true", help="Forçar reinstalação")
    parser.add_argument(
        "--json", action="store_true", help="Saída JSON (machine-readable)"
    )
    parser.add_argument(
        "-q", "--quiet", action="store_true", help="Suprime output decorativo"
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Modo verboso")
    parser.add_argument(
        "-y",
        "--yes",
        action="store_true",
        help="Não pedir confirmação (uninstall/reinstall)",
    )
    parser.add_argument(
        "--python",
        default="python" if platform.system() == "Windows" else "python3",
        help="Comando Python",
    )
    parser.add_argument(
        "--retry",
        metavar="N",
        type=int,
        default=None,
        help="Tentativas em falhas transitórias (1 = sem retry; default segue CLIFIED_RETRY=1 → 3)",
    )
    parser.add_argument(
        "--get",
        metavar="TOOL",
        default=None,
        help="Buscar e instalar uma ferramenta remota do catálogo (registry.yaml)",
    )
    parser.add_argument(
        "--repo",
        metavar="URL",
        default=None,
        help="URL git override para --get (repositório arbitrário)",
    )
    parser.add_argument(
        "--catalog",
        action="store_true",
        help="Listar ferramentas remotas conhecidas (--get)",
    )
    parser.add_argument(
        "--refresh-catalog",
        action="store_true",
        help="Forçar refresh do catálogo remoto (ignora cache; equiv. CLIFIED_CATALOG_TTL=0)",
    )
    parser.add_argument(
        "--sources-dir",
        default=None,
        help="Onde clonar repositórios remotos (default: ~/.config/clified/sources)",
    )
    return parser


def _apply_runtime_defaults(args: argparse.Namespace) -> None:
    """UTF-8 em Windows + modo não-interativo quando stdin não é TTY (pipe).

    Num pipe ``curl | bash`` / ``irm | iex`` o stdin não é terminal: filhos como
    o pip poderiam tentar ler do pipe e hang. Detecta isso e impõe não-interativo
    (``--yes`` implícito + ``PIP_NO_INPUT``) e UTF-8 para filhos Python (Windows).
    """
    if platform.system() == "Windows":
        os.environ.setdefault("PYTHONUTF8", "1")
    if sys.stdin is None or not sys.stdin.isatty():
        args.yes = True
        os.environ.setdefault("PIP_NO_INPUT", "1")
        os.environ.setdefault("PIP_DISABLE_PIP_VERSION_CHECK", "1")
        os.environ.setdefault("UV_NO_PROGRESS", "1")


def main(argv: list[str] | None = None) -> int:
    os.environ.setdefault("UV_VENV_CLEAR", "1")
    os.environ.setdefault("UV_LINK_MODE", "copy")

    parser = _build_parser()
    args = parser.parse_args(argv)
    _apply_runtime_defaults(args)

    if getattr(args, "refresh_catalog", False):
        os.environ["CLIFIED_CATALOG_TTL"] = "0"

    from clified.cli.output import OutputFormatter

    output = OutputFormatter(json_mode=args.json, quiet=args.quiet)
    logger = Logger()

    if args.catalog:
        return _print_catalog(logger, output)

    if args.get:
        return _run_get(args, logger, output)

    try:
        load_registry()
    except FileNotFoundError as e:
        logger.error(str(e))
        return 1

    workspace = get_workspace()
    available = list_available_tools(workspace.root)

    if args.list:
        _print_tool_list(available, workspace, logger, output=output)
        return 0

    if args.doctor:
        return _run_doctor_cli(args, workspace, available, logger, output)

    if args.all and args.tool is not None:
        parser.error("Não uses --all juntamente com o nome da ferramenta.")

    effective_tool = "all" if args.all else args.tool
    if effective_tool is None:
        parser.print_help()
        return 0

    prefix = Path(args.prefix) if args.prefix else None
    install_results: list[InstallResult] = []

    if effective_tool.lower() == "all":
        ok, install_results = install_all(
            workspace=workspace,
            install_prefix=prefix,
            python_cmd=args.python,
            use_venv=args.use_venv,
            skip_deps=args.skip_deps,
            skip_models=args.skip_models,
            force=args.force,
            retry_attempts=args.retry,
        )
    else:
        result = install_tool(
            effective_tool,
            workspace=workspace,
            action=args.action,
            install_prefix=prefix,
            python_cmd=args.python,
            use_venv=args.use_venv,
            skip_deps=args.skip_deps,
            skip_models=args.skip_models,
            force=args.force,
            retry_attempts=args.retry,
        )
        ok = bool(result)
        install_results = [result]

    if args.json:
        output.data(
            {
                "action": args.action,
                "ok": ok,
                "results": [r.to_dict() for r in install_results],
            },
            title="install",
        )

    return 0 if ok else 1


def _run_doctor_cli(
    args: argparse.Namespace,
    workspace: WorkspaceConfig,
    available: list[ToolSpec],
    logger: Logger,
    output: OutputFormatter,
) -> int:
    from .doctor import run_doctor_with_state

    prefix = Path(args.prefix) if args.prefix else None
    base = prefix or Path(os.environ.get("INSTALL_PREFIX", Path.home() / ".local"))
    bin_dir = base / "bin"
    ok = run_doctor_with_state(
        available,
        workspace,
        bin_dir=bin_dir,
        logger=logger,
        output=output,
        fix=args.fix,
        tool_filter=args.tool,
    )
    return 0 if ok else 1


def _build_static_epilog() -> str:
    return "\n".join(
        [
            "Exemplos:",
            "  clified-install --list                  # ferramentas do tools.yaml activo",
            "  clified-install mytool                  # instalar ferramenta local",
            "  clified-install all                     # todas (respeita install_order)",
            "  clified-install mytool --action update  # refrescar reaproveitando o venv",
            "  clified-install --doctor --fix          # diagnóstico + limpar wrappers sombreados",
            "  clified-install --catalog               # listar ferramentas remotas conhecidas",
            "  clified-install --get denv              # buscar e instalar ferramenta remota do catálogo",
            "  clified-install --get mytool --repo https://github.com/x/y.git",
            "",
            "One-liner (sem clonar o clified):",
            "  curl -fsSL https://raw.githubusercontent.com/maikramer/clified/main/install.sh | bash",
            "  curl -fsSL .../install.sh | bash -s -- --get denv",
            "  irm https://raw.githubusercontent.com/maikramer/clified/main/install.ps1 | iex",
        ]
    )


def _print_catalog(logger: Logger, output: OutputFormatter) -> int:
    from . import catalog

    known = catalog.list_known()
    if output.is_json:
        output.data(
            {
                "tools": [
                    {
                        "name": s.name,
                        "repo": s.repo,
                        "tool": s.tool,
                        "tools_yaml": s.tools_yaml,
                        "description": s.description,
                        "access": s.access,
                        "ref": s.ref,
                    }
                    for s in known
                ],
                "count": len(known),
            },
            title="catalog",
        )
        return 0
    if not known:
        logger.warn("Catálogo vazio (sem registry.yaml).")
        return 0
    rows = []
    for s in known:
        label = f"{s.name} (privado)" if s.access == "private" else s.name
        rows.append((label, f"{s.repo}  ->  clified-install {s.tool}"))
    logger.table(rows, title="Ferramentas remotas conhecidas (--get)")
    return 0


def _resolve_get_spec(tool_arg: str, repo_override: str | None):
    from . import catalog

    catalog_name, ref = catalog.parse_tool_at_ref(tool_arg)
    if repo_override:
        spec = catalog.RepoSpec(
            name=catalog_name,
            repo=repo_override,
            tool=catalog_name,
            tools_yaml="tools.yaml",
            ref=ref,
        )
        return spec, catalog_name, ref
    try:
        spec = catalog.resolve(catalog_name)
    except KeyError as e:
        raise KeyError(str(e)) from e
    if ref:
        spec = catalog.with_ref(spec, ref)
    elif spec.ref:
        ref = spec.ref
    return spec, catalog_name, ref


def _run_get(
    args: argparse.Namespace, logger: Logger, output: OutputFormatter | None = None
) -> int:
    from . import catalog

    out = output or OutputFormatter()
    try:
        spec, catalog_name, ref = _resolve_get_spec(args.get, args.repo)
    except KeyError as e:
        logger.error(str(e))
        logger.info("Use --catalog para listar conhecidas ou --repo <url>.")
        return 1
    if args.repo:
        logger.info(f"Repo override: {spec.repo}")

    if args.sources_dir:
        os.environ["CLIFIED_SOURCES"] = str(Path(args.sources_dir).expanduser())

    if spec.access == "private":
        logger.warn(
            f"{spec.tool!r} é privada — requer permissão de leitura no git "
            "da organização (ex.: Locatelli)."
        )

    try:
        dest = catalog.clone_or_update(spec, logger=logger)
        tools_yaml = catalog.resolve_tools_yaml(spec, dest)
        commit = catalog.git_head_commit(dest)
    except (RuntimeError, FileNotFoundError) as e:
        logger.error(str(e))
        return 1

    logger.success(f"Repo pronto: {dest}")
    os.environ["CLIFIED_TOOLS"] = str(tools_yaml)
    os.environ["CLIFIED_ROOT"] = str(dest)

    from . import registry as reg

    reg.reset_registry()
    try:
        load_registry()
    except FileNotFoundError as e:
        logger.error(str(e))
        return 1

    prefix = Path(args.prefix) if args.prefix else None
    source = "repo" if args.repo else "catalog"

    def _ctx_for(spec_tool: ToolSpec) -> ReceiptContext:
        return ReceiptContext(
            receipt_key=spec_tool.key,
            source=source,
            catalog_name=catalog_name,
            repo=spec.repo,
            ref=ref,
            commit=commit,
            repo_clone_path=str(dest),
            tools_yaml=str(tools_yaml),
        )

    install_results: list[InstallResult] = []
    if spec.tool.lower() == "all":
        ok, install_results = install_all(
            install_prefix=prefix,
            python_cmd=args.python,
            use_venv=args.use_venv,
            skip_deps=args.skip_deps,
            skip_models=args.skip_models,
            force=args.force,
            retry_attempts=args.retry,
            receipt_ctx_factory=lambda s: _ctx_for(s),
        )
    else:
        ctx = ReceiptContext(
            receipt_key=catalog_name,
            source=source,
            catalog_name=catalog_name,
            repo=spec.repo,
            ref=ref,
            commit=commit,
            repo_clone_path=str(dest),
            tools_yaml=str(tools_yaml),
        )
        result = install_tool(
            spec.tool,
            action=args.action,
            install_prefix=prefix,
            python_cmd=args.python,
            use_venv=args.use_venv,
            skip_deps=args.skip_deps,
            skip_models=args.skip_models,
            force=args.force,
            retry_attempts=args.retry,
            receipt_ctx=ctx,
        )
        ok = bool(result)
        install_results = [result]

    if out.is_json:
        out.data(
            {
                "catalog": catalog_name,
                "ref": ref,
                "commit": commit,
                "action": args.action,
                "ok": ok,
                "results": [r.to_dict() for r in install_results],
            },
            title="get",
        )

    return 0 if ok else 1


def _print_tool_list(
    available: list[ToolSpec],
    workspace: WorkspaceConfig,
    logger: Logger,
    *,
    output: OutputFormatter | None = None,
) -> None:
    out = output or OutputFormatter()
    rows = [
        {
            "name": spec.cli_name,
            "kind": spec.kind.value,
            "description": spec.description,
        }
        for spec in available
    ]
    if out.is_json:
        out.data(
            {
                "workspace": str(workspace.root),
                "workspace_name": workspace.name,
                "tools": rows,
                "count": len(rows),
            },
            title="tools",
        )
        return
    table_rows = [("Workspace", str(workspace.root))]
    for spec in available:
        kind = spec.kind.value.capitalize()
        table_rows.append((f"{spec.cli_name} [{kind}]", spec.description))
    logger.table(table_rows, title=f"Ferramentas — {workspace.name}")


if __name__ == "__main__":
    sys.exit(main())
