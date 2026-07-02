"""Dispatcher de subcomandos ``clified`` (0.8+)."""

from __future__ import annotations

import argparse
import os
import platform
import shutil
import sys
from pathlib import Path

from clified.cli.output import OutputFormatter
from clified.logging import Logger

SUBCOMMANDS = frozenset(
    {"install", "get", "list", "update", "uninstall", "search", "doctor", "catalog"}
)


def _global_flags(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--json", action="store_true", help="Saída JSON")
    parser.add_argument("-q", "--quiet", action="store_true", help="Silencioso")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verboso")
    parser.add_argument("-y", "--yes", action="store_true", help="Sem confirmação")


def _install_flags(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--action",
        choices=["install", "update", "uninstall", "reinstall"],
        default="install",
    )
    parser.add_argument("--prefix", default=None)
    parser.add_argument("--use-venv", action="store_true")
    parser.add_argument("--skip-deps", action="store_true")
    parser.add_argument("--skip-models", action="store_true")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--retry", type=int, default=None)
    parser.add_argument(
        "--python",
        default="python" if platform.system() == "Windows" else "python3",
    )


def _build_subparsers() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(prog="clified")
    sub = root.add_subparsers(dest="command", required=True)

    p_install = sub.add_parser("install", help="Instalar ferramenta do tools.yaml activo")
    p_install.add_argument("tool", nargs="?", default=None)
    p_install.add_argument("--all", action="store_true")
    _global_flags(p_install)
    _install_flags(p_install)

    p_get = sub.add_parser("get", help="Buscar e instalar do catálogo remoto")
    p_get.add_argument("tool", help="Nome ou nome@ref")
    p_get.add_argument("--repo", default=None)
    p_get.add_argument("--sources-dir", default=None)
    p_get.add_argument("--refresh-catalog", action="store_true")
    _global_flags(p_get)
    _install_flags(p_get)

    p_list = sub.add_parser("list", help="Ferramentas instaladas (state file)")
    _global_flags(p_list)

    p_update = sub.add_parser("update", help="Actualizar ferramentas instaladas")
    p_update.add_argument("tool", nargs="?", default=None)
    p_update.add_argument("--all", action="store_true")
    p_update.add_argument("--ref", default=None, help="Nova ref git (branch/tag/commit)")
    p_update.add_argument("--force", action="store_true")
    p_update.add_argument("--prefix", default=None)
    p_update.add_argument(
        "--python",
        default="python" if platform.system() == "Windows" else "python3",
    )
    _global_flags(p_update)

    p_un = sub.add_parser("uninstall", help="Desinstalar via receipt")
    p_un.add_argument("tool")
    p_un.add_argument("--purge", action="store_true", help="Apagar clone em sources/")
    p_un.add_argument("--prefix", default=None)
    p_un.add_argument(
        "--python",
        default="python" if platform.system() == "Windows" else "python3",
    )
    _global_flags(p_un)

    p_search = sub.add_parser("search", help="Procurar no catálogo remoto")
    p_search.add_argument("query")
    p_search.add_argument("--refresh", action="store_true")
    _global_flags(p_search)

    p_doc = sub.add_parser("doctor", help="Diagnóstico de saúde")
    p_doc.add_argument("tool", nargs="?", default=None)
    p_doc.add_argument("--fix", action="store_true")
    p_doc.add_argument("--prefix", default=None)
    _global_flags(p_doc)

    p_cat = sub.add_parser("catalog", help="Listar catálogo remoto")
    p_cat.add_argument("--refresh-catalog", action="store_true")
    _global_flags(p_cat)

    return root


def _apply_pipe_defaults(args: argparse.Namespace) -> None:
    if platform.system() == "Windows":
        os.environ.setdefault("PYTHONUTF8", "1")
    if sys.stdin is None or not sys.stdin.isatty():
        args.yes = True
        os.environ.setdefault("PIP_NO_INPUT", "1")


def _restore_env_from_receipt(receipt) -> None:
    if receipt.tools_yaml:
        os.environ["CLIFIED_TOOLS"] = receipt.tools_yaml
    if receipt.project_root:
        root = Path(receipt.project_root).parent
        while root != root.parent:
            if (root / "tools.yaml").is_file() or (root / ".git").is_dir():
                os.environ["CLIFIED_ROOT"] = str(root)
                break
            root = root.parent
    if receipt.repo_clone_path:
        os.environ.setdefault("CLIFIED_ROOT", str(Path(receipt.repo_clone_path)))


def _cmd_list(args: argparse.Namespace) -> int:
    from clified.installer.receipts import list_with_status

    output = OutputFormatter(json_mode=args.json, quiet=args.quiet)
    rows = list_with_status()
    if output.is_json:
        output.data({"installed": rows, "count": len(rows)}, title="list")
        return 0
    logger = Logger()
    if not rows:
        logger.info("Nenhuma ferramenta instalada registada.")
        return 0
    table = [
        (
            r["name"],
            r["kind"],
            r["commit_short"] or r["ref"] or "-",
            r["source"],
            r["status"],
        )
        for r in rows
    ]
    logger.table(table, title="Ferramentas instaladas (clified list)")
    return 0


def _cmd_search(args: argparse.Namespace) -> int:
    from clified.installer import catalog
    from clified.installer.receipts import load_all

    if args.refresh:
        os.environ["CLIFIED_CATALOG_TTL"] = "0"

    installed = set(load_all())
    query = args.query.lower()
    matches = []
    for spec in catalog.list_known():
        hay = f"{spec.name} {spec.tool} {spec.description}".lower()
        if query not in hay:
            continue
        label = spec.name
        if spec.access == "private":
            label += " (privado)"
        if spec.name in installed:
            label += " [instalado]"
        matches.append(
            {
                "name": spec.name,
                "tool": spec.tool,
                "repo": spec.repo,
                "description": spec.description,
                "access": spec.access,
                "installed": spec.name in installed,
                "ref": spec.ref,
            }
        )

    output = OutputFormatter(json_mode=args.json, quiet=args.quiet)
    if output.is_json:
        output.data({"query": args.query, "results": matches, "count": len(matches)})
        return 0
    logger = Logger()
    if not matches:
        logger.warn(f"Nenhum resultado para {args.query!r}")
        return 0
    rows = [(m["name"], m["description"] or m["repo"]) for m in matches]
    logger.table(rows, title=f"Catálogo — {args.query!r}")
    return 0


def _cmd_catalog(args: argparse.Namespace) -> int:
    from clified.installer.unified import _print_catalog

    if args.refresh_catalog:
        os.environ["CLIFIED_CATALOG_TTL"] = "0"
    output = OutputFormatter(json_mode=args.json, quiet=args.quiet)
    return _print_catalog(Logger(), output)


def _cmd_doctor(args: argparse.Namespace) -> int:
    from clified.installer.doctor import run_doctor_with_state
    from clified.installer.registry import load_registry, list_available_tools, get_workspace

    try:
        load_registry()
    except FileNotFoundError:
        pass

    output = OutputFormatter(json_mode=args.json, quiet=args.quiet)
    logger = Logger()
    prefix = Path(args.prefix) if args.prefix else None
    base = prefix or Path(os.environ.get("INSTALL_PREFIX", Path.home() / ".local"))
    bin_dir = base / "bin"

    workspace = None
    available = []
    try:
        workspace = get_workspace()
        available = list_available_tools(workspace.root)
    except Exception:
        workspace = None

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


def _git_pull_changed(clone_path: Path) -> bool:
    from clified.installer import catalog

    before = catalog.git_head_commit(clone_path)
    result = catalog.pull_ff_only(clone_path)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "git pull falhou")
    after = catalog.git_head_commit(clone_path)
    return before != after


def _update_one(
    name: str,
    *,
    ref: str | None,
    force: bool,
    prefix: Path | None,
    python_cmd: str,
    output: OutputFormatter,
) -> tuple[bool, dict]:
    from clified.installer import catalog
    from clified.installer import registry as reg
    from clified.installer.receipts import get, update_receipt
    from clified.installer.unified import ReceiptContext, install_tool, load_registry

    receipt = get(name)
    if receipt is None:
        raise KeyError(f"Não instalado: {name!r}")

    _restore_env_from_receipt(receipt)
    reg.reset_registry()
    load_registry()

    new_ref = (ref or receipt.ref or "").strip()
    pulled = False
    if receipt.source != "local" and receipt.repo_clone_path:
        clone = Path(receipt.repo_clone_path)
        if clone.is_dir() and (clone / ".git").is_dir():
            if new_ref and new_ref != receipt.ref:
                spec = catalog.RepoSpec(
                    name=name,
                    repo=receipt.repo,
                    tool=name,
                    ref=new_ref,
                )
                catalog.clone_or_update(spec, clone, force_ref=True)
                pulled = True
            elif not force:
                pulled = _git_pull_changed(clone)
                if not pulled:
                    return True, {"tool": name, "ok": True, "skipped": True}
            else:
                _git_pull_changed(clone)
                pulled = True
            commit = catalog.git_head_commit(clone)
            update_receipt(name, commit=commit, ref=new_ref or receipt.ref)

    ctx = ReceiptContext(
        receipt_key=name,
        source=receipt.source,
        catalog_name=receipt.catalog_name,
        repo=receipt.repo,
        ref=new_ref or receipt.ref,
        commit=receipt.commit,
        repo_clone_path=receipt.repo_clone_path,
        tools_yaml=receipt.tools_yaml,
    )

    tool_name = name
    try:
        from clified.installer.registry import get_tool

        get_tool(name)
    except KeyError:
        if receipt.catalog_name:
            from clified.installer import catalog as cat

            try:
                spec = cat.resolve(receipt.catalog_name)
                tool_name = spec.tool
            except KeyError:
                tool_name = receipt.cli_name

    result = install_tool(
        tool_name,
        action="update",
        install_prefix=prefix,
        python_cmd=python_cmd,
        force=force,
        receipt_ctx=ctx,
    )
    payload = result.to_dict()
    payload["skipped"] = False
    return bool(result), payload


def _cmd_update(args: argparse.Namespace) -> int:
    from clified.installer.receipts import load_all

    output = OutputFormatter(json_mode=args.json, quiet=args.quiet)
    logger = Logger()
    prefix = Path(args.prefix) if args.prefix else None

    if args.all:
        names = sorted(load_all())
    elif args.tool:
        names = [args.tool.lower()]
    else:
        logger.error("Indica uma ferramenta ou --all.")
        return 1

    if not names:
        logger.info("Nada para actualizar.")
        return 0

    results: list[dict] = []
    all_ok = True
    for name in names:
        try:
            ok, payload = _update_one(
                name,
                ref=args.ref,
                force=args.force,
                prefix=prefix,
                python_cmd=args.python,
                output=output,
            )
            results.append(payload)
            if payload.get("skipped"):
                logger.info(f"{name}: já actualizado (skip)")
            elif ok:
                logger.success(f"{name}: actualizado")
            else:
                logger.error(f"{name}: falhou")
            all_ok = all_ok and ok
        except (KeyError, RuntimeError) as exc:
            logger.error(f"{name}: {exc}")
            results.append({"tool": name, "ok": False, "error": str(exc)})
            all_ok = False

    if output.is_json:
        output.data({"ok": all_ok, "results": results}, title="update")
    return 0 if all_ok else 1


def _cmd_uninstall(args: argparse.Namespace) -> int:
    from clified.installer import catalog
    from clified.installer import registry as reg
    from clified.installer.receipts import get, remove
    from clified.installer.unified import ReceiptContext, install_tool, load_registry

    output = OutputFormatter(json_mode=args.json, quiet=args.quiet)
    logger = Logger()
    name = args.tool.lower()
    receipt = get(name)
    if receipt is None:
        logger.error(f"Não instalado: {name!r} (use clified list)")
        return 1

    _restore_env_from_receipt(receipt)
    reg.reset_registry()
    try:
        load_registry()
    except FileNotFoundError:
        pass

    prefix = Path(args.prefix) if args.prefix else None
    ctx = ReceiptContext(receipt_key=name, source=receipt.source)

    tool_name = name
    try:
        from clified.installer.registry import get_tool

        get_tool(name)
    except KeyError:
        tool_name = receipt.cli_name

    result = install_tool(
        tool_name,
        action="uninstall",
        install_prefix=prefix,
        python_cmd=args.python,
        receipt_ctx=ctx,
    )
    remove(name)

    if args.purge and receipt.repo_clone_path:
        clone = Path(receipt.repo_clone_path)
        if clone.is_dir():
            shutil.rmtree(clone, ignore_errors=True)
            logger.success(f"Clone removido: {clone}")
        elif receipt.repo:
            fallback = catalog.sources_dir() / name
            if fallback.is_dir():
                shutil.rmtree(fallback, ignore_errors=True)
                logger.success(f"Clone removido: {fallback}")

    if output.is_json:
        output.data(result.to_dict(), title="uninstall")
    return 0 if result.ok else 1


def _cmd_install(args: argparse.Namespace) -> int:
    from clified.installer.unified import install_all, install_tool, load_registry

    os.environ.setdefault("UV_VENV_CLEAR", "1")
    try:
        load_registry()
    except FileNotFoundError as e:
        Logger().error(str(e))
        return 1

    prefix = Path(args.prefix) if args.prefix else None
    output = OutputFormatter(json_mode=args.json, quiet=args.quiet)
    results = []

    if args.all or args.tool is None:
        ok, results = install_all(
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
            args.tool,
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
        results = [result]

    if output.is_json:
        output.data(
            {"ok": ok, "action": args.action, "results": [r.to_dict() for r in results]},
            title="install",
        )
    return 0 if ok else 1


def _cmd_get(args: argparse.Namespace) -> int:
    from clified.installer.unified import _run_get

    os.environ.setdefault("UV_VENV_CLEAR", "1")
    if args.refresh_catalog:
        os.environ["CLIFIED_CATALOG_TTL"] = "0"
    if args.sources_dir:
        os.environ["CLIFIED_SOURCES"] = str(Path(args.sources_dir).expanduser())

    ns = argparse.Namespace(
        get=args.tool,
        repo=args.repo,
        sources_dir=args.sources_dir,
        action=args.action,
        prefix=args.prefix,
        python=args.python,
        use_venv=args.use_venv,
        skip_deps=args.skip_deps,
        skip_models=args.skip_models,
        force=args.force,
        retry=args.retry,
        json=args.json,
        quiet=args.quiet,
    )
    output = OutputFormatter(json_mode=args.json, quiet=args.quiet)
    return _run_get(ns, Logger(), output)


def _dispatch(command: str, args: argparse.Namespace) -> int:
    handlers = {
        "install": _cmd_install,
        "get": _cmd_get,
        "list": _cmd_list,
        "update": _cmd_update,
        "uninstall": _cmd_uninstall,
        "search": _cmd_search,
        "doctor": _cmd_doctor,
        "catalog": _cmd_catalog,
    }
    return handlers[command](args)


def main(argv: list[str] | None = None) -> int:
    argv = list(argv) if argv is not None else sys.argv[1:]
    if not argv or argv[0] not in SUBCOMMANDS:
        from clified.installer.unified import main as legacy_main

        return legacy_main(argv)

    parser = _build_subparsers()
    args = parser.parse_args(argv)
    _apply_pipe_defaults(args)
    return _dispatch(args.command, args)
