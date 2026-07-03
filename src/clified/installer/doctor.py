"""Health diagnostics for registered tools (``clified-install --doctor``).

Reports, per tool, whether its venv exists and runs a Python the tool
actually supports, whether the CLI wrapper is installed and *wins on PATH*
(a stale wrapper elsewhere silently shadowing it is a classic, hard-to-spot
failure), and which build backends (uv/cargo/bun) are available. The intent
is that a single ``--doctor`` run explains why a tool is broken instead of
leaving the user to reverse-engineer it from an install traceback.
"""

from __future__ import annotations

import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any

from .registry import ToolKind
from .requires_python import bounds_from_pyproject

if TYPE_CHECKING:
    from clified.cli.output import OutputFormatter
    from clified.logging import Logger

    from .registry import ToolSpec, WorkspaceConfig

Bound = tuple[int, int]

OK = "ok"
WARN = "warn"
FAIL = "fail"

_RANK = {OK: 0, WARN: 1, FAIL: 2}


def _venv_python(project_root: Path) -> Path:
    sub = "Scripts/python.exe" if sys.platform == "win32" else "bin/python"
    return project_root / ".venv" / sub


def _read_python_abi(python: Path) -> Bound | None:
    try:
        proc = subprocess.run(
            [
                str(python),
                "-c",
                "import sys;print(sys.version_info[0],sys.version_info[1])",
            ],
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
        )
    except (subprocess.SubprocessError, OSError):
        return None
    parts = proc.stdout.split()
    if len(parts) != 2:
        return None
    try:
        return int(parts[0]), int(parts[1])
    except ValueError:
        return None


def _effective_bounds(spec: ToolSpec, project_root: Path) -> tuple[Bound, Bound | None]:
    floor: Bound = spec.min_python
    ceiling: Bound | None = spec.max_python
    pj_floor, pj_ceiling = bounds_from_pyproject(project_root)
    if pj_floor is not None and pj_floor > floor:
        floor = pj_floor
    if pj_ceiling is not None:
        ceiling = pj_ceiling if ceiling is None else min(ceiling, pj_ceiling)
    return floor, ceiling


def _module_imports(python: Path, module: str) -> bool:
    try:
        subprocess.run(
            [str(python), "-c", f"import {module}"],
            check=True,
            capture_output=True,
            timeout=60,
        )
    except (subprocess.SubprocessError, OSError):
        return False
    return True


def _wrapper_candidates(bin_dir: Path, cli_name: str) -> list[Path]:
    """Paths where clified may install a CLI wrapper (platform-specific)."""
    if sys.platform == "win32":
        return [
            bin_dir / f"{cli_name}.cmd",
            bin_dir / f"{cli_name}.exe",
            bin_dir / cli_name,
        ]
    return [bin_dir / cli_name]


def _wrapper_path(bin_dir: Path, cli_name: str) -> Path:
    """Canonical wrapper path — prefers the file that exists, else the default created by clified."""
    for candidate in _wrapper_candidates(bin_dir, cli_name):
        if candidate.is_file():
            return candidate
    if sys.platform == "win32":
        return bin_dir / f"{cli_name}.cmd"
    return bin_dir / cli_name


def _wrapper_exists(bin_dir: Path, cli_name: str) -> bool:
    return any(p.is_file() for p in _wrapper_candidates(bin_dir, cli_name))


def diagnose_tool(
    spec: ToolSpec, workspace: WorkspaceConfig, bin_dir: Path
) -> dict[str, Any]:
    """Return a health report dict for a single tool."""
    project_root = spec.project_root(workspace.root)
    issues: list[str] = []
    status = OK

    report: dict[str, Any] = {
        "name": spec.cli_name,
        "kind": spec.kind.value,
        "project_root": str(project_root),
        "project_exists": spec.exists(workspace.root),
    }

    if not report["project_exists"]:
        return {**report, "status": FAIL, "issues": ["projecto ausente no disco"]}

    if spec.kind == ToolKind.PYTHON:
        venv_py = _venv_python(project_root)
        report["venv"] = str(venv_py.parent.parent)
        if not venv_py.is_file():
            issues.append("venv ausente — execute a instalação")
            status = FAIL
        else:
            abi = _read_python_abi(venv_py)
            report["python"] = f"{abi[0]}.{abi[1]}" if abi else "?"
            floor, ceiling = _effective_bounds(spec, project_root)
            report["requires"] = f">={floor[0]}.{floor[1]}" + (
                f",<={ceiling[0]}.{ceiling[1]}" if ceiling else ""
            )
            if abi is None:
                issues.append("venv não executa Python")
                status = FAIL
            elif abi < floor:
                issues.append(
                    f"Python {abi[0]}.{abi[1]} < mínimo {floor[0]}.{floor[1]}"
                )
                status = FAIL
            elif ceiling is not None and abi > ceiling:
                issues.append(
                    f"Python {abi[0]}.{abi[1]} > máximo {ceiling[0]}.{ceiling[1]} "
                    "(reinstale para recriar o venv)"
                )
                status = FAIL
            module = spec.python_module or spec.cli_name.replace("-", "_")
            if abi is not None and not _module_imports(venv_py, module):
                issues.append(f"módulo {module!r} não importa no venv")
                status = FAIL

    # CLI wrapper + PATH shadowing (all kinds).
    wrapper = _wrapper_path(bin_dir, spec.cli_name)
    report["wrapper"] = str(wrapper)
    report["wrapper_exists"] = _wrapper_exists(bin_dir, spec.cli_name)
    resolved = shutil.which(spec.cli_name)
    report["path_resolves_to"] = resolved
    if not wrapper.is_file():
        issues.append("wrapper do CLI ausente")
        status = _worse(status, WARN)
    elif resolved is None:
        issues.append(f"{bin_dir} não está no PATH")
        status = _worse(status, WARN)
    elif _norm(resolved) != _norm(str(wrapper)):
        issues.append(f"PATH resolve para {resolved} (wrapper ofuscado)")
        status = _worse(status, FAIL)

    report["status"] = status
    report["issues"] = issues
    return report


def _path_dirs() -> list[Path]:
    import os
    from pathlib import Path as _Path

    return [_Path(p) for p in os.environ.get("PATH", "").split(os.pathsep) if p.strip()]


def fix_shadows(report: dict[str, Any], logger: Logger) -> list[str]:
    """Remove CLI wrappers that shadow the canonical clified wrapper on PATH.

    Only runs when a clified wrapper exists for the tool, so a tool is never
    left without a CLI. Every other executable named ``cli_name`` found earlier
    on PATH is deleted. Returns the paths removed.
    """
    if not report.get("wrapper_exists"):
        return []
    wrapper = report["wrapper"]
    name = report["name"]
    removed: list[str] = []
    for d in _path_dirs():
        candidates = (
            [d / f"{name}.cmd", d / f"{name}.exe", d / name]
            if sys.platform == "win32"
            else [d / name]
        )
        for candidate in candidates:
            if not candidate.is_file():
                continue
            if _norm(str(candidate)) == _norm(wrapper):
                continue
            try:
                candidate.unlink()
            except OSError as exc:
                logger.warning(f"Não consegui remover {candidate}: {exc}")
                continue
            removed.append(str(candidate))
            logger.success(f"Removido wrapper ofuscador: {candidate}")
    return removed


def run_doctor(
    specs: list[ToolSpec],
    workspace: WorkspaceConfig,
    *,
    bin_dir: Path,
    logger: Logger,
    output: OutputFormatter,
    fix: bool = False,
) -> bool:
    """Diagnose *specs*; print a report; return ``True`` when all are healthy.

    When *fix* is set, shadowing wrappers are removed and the affected tools
    are re-diagnosed so the final report reflects the repair.
    """
    backends = {
        "uv": shutil.which("uv"),
        "cargo": shutil.which("cargo"),
        "bun": shutil.which("bun"),
        "git": shutil.which("git"),
    }
    reports = [diagnose_tool(spec, workspace, bin_dir) for spec in specs]

    if fix:
        by_name = {spec.cli_name: spec for spec in specs}
        repaired = False
        for r in reports:
            if any("ofuscado" in i for i in r["issues"]) and fix_shadows(r, logger):
                repaired = True
        if repaired:
            reports = [
                diagnose_tool(spec, workspace, bin_dir) for spec in by_name.values()
            ]

    all_ok = all(r["status"] == OK for r in reports)

    if output.is_json:
        output.data(
            {
                "workspace": str(workspace.root),
                "bin_dir": str(bin_dir),
                "backends": backends,
                "tools": reports,
                "healthy": all_ok,
            },
            title="doctor",
        )
        return all_ok

    rows: list[tuple[str, str]] = [
        ("Workspace", str(workspace.root)),
        ("bin", str(bin_dir)),
        (
            "Backends",
            ", ".join(f"{k}={'sim' if v else 'não'}" for k, v in backends.items()),
        ),
    ]
    logger.table(rows, title="Clified doctor")

    for r in reports:
        head = f"{r['name']} [{r['kind']}]"
        detail = []
        if r.get("python"):
            detail.append(f"py {r['python']}")
        if r.get("requires"):
            detail.append(f"req {r['requires']}")
        suffix = f"  ({', '.join(detail)})" if detail else ""
        if r["status"] == OK:
            logger.success(f"{head}{suffix}")
        elif r["status"] == WARN:
            logger.warning(f"{head}{suffix}")
        else:
            logger.error(f"{head}{suffix}")
        for issue in r["issues"]:
            logger.info(f"    - {issue}")

    if all_ok:
        logger.success("Tudo saudável.")
    else:
        logger.warning("Problemas encontrados — veja acima.")
    return all_ok


def _broken_receipts() -> list[dict[str, Any]]:
    from clified.installer.receipts import load_all, verify

    broken = []
    for name, receipt in load_all().items():
        status = verify(receipt)
        if status != "ok":
            broken.append(
                {
                    "name": name,
                    "cli_name": receipt.cli_name,
                    "status": status,
                    "issues": ["receipt broken — artifacts missing"],
                }
            )
    return broken


def _orphan_wrappers(bin_dir: Path) -> list[str]:
    """Wrappers clified cujo venv referenciado não existe.

    Só considera ficheiros gerados pelo clified (marcador ``gerado por clified``)
    para não tocar em scripts alheios do utilizador presentes em ``bin_dir``.
    """
    orphans: list[str] = []
    if not bin_dir.is_dir():
        return orphans
    for path in bin_dir.iterdir():
        if path.is_dir():
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if "gerado por clified" not in text or ".venv" not in text:
            continue
        for line in text.splitlines():
            if ".venv" in line:
                match = re.search(r'["\']([^"\']*\.venv[^"\']*)["\']', line)
                if match:
                    venv_part = Path(match.group(1))
                    if (
                        not venv_part.exists()
                        and not (venv_part.parent / ".venv").exists()
                    ):
                        orphans.append(str(path))
                break
    return orphans


def _norm_tool(name: str) -> str:
    """Normaliza nome de ferramenta para matching (lowercase, sem ``-``/``_``)."""
    return name.strip().lower().replace("-", "").replace("_", "")


def run_doctor_with_state(  # noqa: PLR0915
    specs: list[ToolSpec],
    workspace: WorkspaceConfig | None,
    *,
    bin_dir: Path,
    logger: Logger,
    output: OutputFormatter,
    fix: bool = False,
    tool_filter: str | None = None,
    yes: bool = False,
) -> bool:
    """Doctor integrado com state file (receipts broken + wrappers órfãos)."""
    from clified.installer.receipts import load_all, remove

    broken = _broken_receipts()
    orphans = _orphan_wrappers(bin_dir)
    actions: list[dict[str, Any]] = []

    # ``--fix`` é destrutivo (remove receipts e wrappers); em modo interactivo
    # sem ``--yes`` pede confirmação. Em pipe (não-tty) o ``--yes`` é implícito.
    if fix and (broken or orphans) and not yes and sys.stdin.isatty():
        print("doctor --fix vai remover:")  # noqa: T201
        for item in broken:
            print(f"  receipt: {item['name']}")  # noqa: T201
        for p in orphans:
            print(f"  wrapper: {p}")  # noqa: T201
        ans = input("Continuar? [y/N] ").strip().lower()
        if ans not in ("y", "yes", "s", "sim"):
            logger.warn("--fix cancelado pelo utilizador.")
            fix = False

    if fix:
        for item in broken:
            remove(item["name"])
            logger.success(f"Receipt órfão removido: {item['name']}")
            actions.append({"type": "remove_receipt", "name": item["name"]})
        for path in orphans:
            try:
                Path(path).unlink()
                logger.success(f"Wrapper órfão removido: {path}")
                actions.append({"type": "remove_wrapper", "path": path})
            except OSError as exc:  # noqa: PERF203
                logger.warn(f"Não foi possível remover {path}: {exc}")
        broken = _broken_receipts()
        orphans = _orphan_wrappers(bin_dir)

    tools_ok = True
    tool_reports: list[dict[str, Any]] = []
    if workspace is not None and specs:
        filtered = specs
        if tool_filter and tool_filter.lower() != "all":
            tf = _norm_tool(tool_filter)
            filtered = [
                s
                for s in specs
                if _norm_tool(s.key) == tf or _norm_tool(s.cli_name) == tf
            ]
        if filtered:
            if output.is_json:
                tool_reports = [
                    diagnose_tool(spec, workspace, bin_dir) for spec in filtered
                ]
                tools_ok = all(r["status"] == OK for r in tool_reports)
            else:
                tools_ok = run_doctor(
                    filtered,
                    workspace,
                    bin_dir=bin_dir,
                    logger=logger,
                    output=output,
                    fix=fix,
                )
    elif not specs and not broken and not orphans:
        if output.is_json:
            payload: dict[str, Any] = {
                "healthy": True,
                "broken_receipts": [],
                "orphan_wrappers": [],
                "installed_count": len(load_all()),
            }
            if actions:
                payload["actions"] = actions
            output.data(payload, title="doctor")
        else:
            logger.info("Sem tools.yaml activo — apenas verificação de state.")
        return not broken and not orphans

    state_ok = not broken and not orphans
    if output.is_json:
        payload = {
            "healthy": tools_ok and state_ok,
            "broken_receipts": broken,
            "orphan_wrappers": orphans,
            "installed_count": len(load_all()),
        }
        if actions:
            payload["actions"] = actions
        if tool_reports:
            payload["tools"] = tool_reports
            payload["bin_dir"] = str(bin_dir)
        output.data(payload, title="doctor")
        return tools_ok and state_ok

    if broken:
        logger.warning("Receipts broken:")
        for item in broken:
            logger.error(f"  {item['name']} ({item['cli_name']})")
    if orphans:
        logger.warning("Wrappers órfãos (venv em falta):")
        for path in orphans:
            logger.info(f"  {path}")

    return tools_ok and state_ok


def _worse(current: str, candidate: str) -> str:
    return current if _RANK[current] >= _RANK[candidate] else candidate


def _norm(path: str) -> str:
    import os

    return os.path.normcase(os.path.realpath(path))
