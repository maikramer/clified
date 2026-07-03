"""PythonProjectInstaller — instalador para projectos Python."""

from __future__ import annotations

import contextlib
import re
import shutil
import subprocess
from typing import TYPE_CHECKING

from .base import (
    BaseInstaller,
    has_uv,
    install_all_constraint_argv,
    uv_cmd,
    write_cli_wrapper,
)
from .requires_python import bounds_from_pyproject

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path

    from .registry import LocalPackage, SharedPythonConfig

_PIP_BOOTSTRAP = ("pip", "setuptools>=68,<82", "wheel")

# A relative ``file:`` dependency URL (e.g. ``gamedev-shared @ file:../Shared``)
# is invalid PEP 508 — pip tolerates it but uv rejects it while building the
# editable wheel. Match the relative path so it can be made absolute.
_REL_FILE_DEP = re.compile(r"""(@\s*file:)(?!/)([^\s"',\]]+)""")


def _rewrite_relative_file_deps(text: str, base_dir: Path) -> tuple[str, bool]:
    """Rewrite relative ``file:`` dependency URLs to absolute ones.

    Returns the (possibly) rewritten text and whether anything changed.
    Paths are resolved against *base_dir* (the project root).
    """
    changed = False

    def _sub(match: re.Match[str]) -> str:
        nonlocal changed
        rel = match.group(2)
        abs_path = (base_dir / rel).resolve()
        changed = True
        # Proper file URL: file:///C:/Users/.../Shared (3 slashes, forward
        # slashes). uv rejects the malformed ``file://C:\\...`` (2 slashes +
        # backslashes) and also the original relative ``file:../Shared``; pip
        # tolerates both, so this form works for either backend.
        return f"{match.group(1)}///{abs_path.as_posix()}"

    return _REL_FILE_DEP.sub(_sub, text), changed


@contextlib.contextmanager
def _patched_relative_deps(project_root: Path, logger) -> Iterator[None]:  # noqa: ANN001
    """Temporarily absolutise relative ``file:`` deps for the uv build.

    pyproject is restored afterwards (even on failure), so the working tree is
    never left modified. A no-op when there are no relative ``file:`` deps.
    """
    pyproject = project_root / "pyproject.toml"
    try:
        with open(pyproject, encoding="utf-8", newline="") as f:
            original = f.read()
    except (OSError, UnicodeDecodeError):
        yield
        return
    patched, changed = _rewrite_relative_file_deps(original, project_root)
    if not changed:
        yield
        return
    logger.info("Absolutizando deps file: relativas para o build (uv)")
    try:
        with open(pyproject, "w", encoding="utf-8", newline="") as f:
            f.write(patched)
        yield
    finally:
        with open(pyproject, "w", encoding="utf-8", newline="") as f:
            f.write(original)


def _find_site_packages(venv_dir: Path) -> Path | None:
    # POSIX: lib/pythonX.Y/site-packages ; Windows: Lib/site-packages
    for sp in venv_dir.glob("lib/*/site-packages"):
        return sp
    win_sp = venv_dir / "Lib" / "site-packages"
    if win_sp.is_dir():
        return win_sp
    return None


def link_local_src(*, venv_dir: Path, src_dir: Path, import_name: str) -> bool:
    sp = _find_site_packages(venv_dir)
    if sp is None:
        return False
    pth = sp / f"_clified_{import_name}.pth"
    pth.write_text(str(src_dir), encoding="utf-8")
    for old in sp.glob("__editable__.*.pth"):
        old.unlink(missing_ok=True)
    pkg_dir = sp / import_name
    if pkg_dir.is_dir():
        shutil.rmtree(pkg_dir, ignore_errors=True)
    for dist in sp.glob(f"{import_name}*.dist-info"):
        if dist.is_dir():
            shutil.rmtree(dist, ignore_errors=True)
    return True


class PythonProjectInstaller(BaseInstaller):
    """Instalador para projectos Python (``pip install -e`` no venv do projecto)."""

    def __init__(
        self,
        *,
        project_name: str,
        cli_name: str,
        project_root: Path,
        install_prefix: Path | None = None,
        python_cmd: str = "python3",
        use_venv: bool = False,
        skip_deps: bool = False,
        skip_models: bool = False,
        force: bool = False,
        skip_pytorch: bool = False,
        min_python: tuple[int, int] = (3, 10),
        max_python: tuple[int, int] | None = None,
        cross_dep_folders: list[tuple[Path, str]] | None = None,
        python_module: str | None = None,
        shared_python: SharedPythonConfig | None = None,
        workspace_root: Path | None = None,
        local_packages: tuple[LocalPackage, ...] = (),
    ) -> None:
        super().__init__(
            project_name=project_name,
            cli_name=cli_name,
            project_root=project_root,
            install_prefix=install_prefix,
            python_cmd=python_cmd,
        )
        self.use_venv = use_venv
        self.skip_deps = skip_deps
        self.skip_models = skip_models
        self.force = force
        self.skip_pytorch = skip_pytorch
        self.python_module = python_module or cli_name.replace("-", "_")
        self.min_python = min_python
        self.max_python = max_python
        self._refine_python_bounds()
        self._use_uv = has_uv()
        self.cross_dep_folders: list[tuple[Path, str]] = cross_dep_folders or []
        self.shared_python = shared_python
        self.workspace_root = workspace_root or project_root.parent
        self.local_packages = local_packages

        self.venv_dir = self.project_root / ".venv"
        if self.is_windows:
            self.venv_python = self.venv_dir / "Scripts" / "python.exe"
        else:
            self.venv_python = self.venv_dir / "bin" / "python"
        self.venv_exists = self.venv_python.is_file()

    def _refine_python_bounds(self) -> None:
        """Tighten min/max Python using the project's ``requires-python``.

        ``tools.yaml`` carries a coarse floor; the tool's ``pyproject.toml`` is
        authoritative. We keep the tighter of the two floors and the lower of
        the two ceilings so a tool capped at e.g. ``<3.14`` never lands on a
        newer interpreter than it declares support for.
        """
        floor, ceiling = bounds_from_pyproject(self.project_root)
        if floor is not None and floor > self.min_python:
            self.min_python = floor
        if ceiling is not None:
            self.max_python = (
                ceiling if self.max_python is None else min(self.max_python, ceiling)
            )
        # A ceiling below the floor means the registry/pyproject disagree;
        # trust the project's ceiling and pin the floor to it.
        if self.max_python is not None and self.max_python < self.min_python:
            self.min_python = self.max_python

    def _target_py_version(self) -> str:
        """``major.minor`` to request from uv when creating the venv.

        Picks the newest interpreter allowed by the bounds (the ceiling when
        one exists, otherwise the floor) so tools get the most recent
        compatible Python with the best wheel availability.
        """
        target = self.max_python if self.max_python is not None else self.min_python
        return f"{target[0]}.{target[1]}"

    def run(self) -> bool:
        self.logger.table(
            [
                ("Prefixo", str(self.install_prefix)),
                ("Python", self.python_cmd),
                ("Projeto", str(self.project_root)),
            ],
            title=f"{self.project_name} — instalador",
        )

        if not self.check_python(self.min_python):
            return False

        if not self.skip_deps:
            self.install_system_deps()

        if not self.ensure_project_venv():
            return False

        try:
            self.install_in_venv()
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            self.logger.exception(f"Falha na instalação no venv: {e}")
            return False
        return True

    def run_uninstall(self) -> bool:
        self.logger.header(f"Desinstalando {self.project_name}")

        wrapper_names = [self.cli_name]
        if self.is_windows:
            wrapper_names.append(f"{self.cli_name}.cmd")
        for name in wrapper_names:
            w = self.bin_dir / name
            if w.exists() or w.is_symlink():
                w.unlink()
                self.logger.success(f"Removido wrapper: {w}")

        activate = self.bin_dir / f"{self.cli_name}-activate"
        if not self.is_windows and (activate.exists() or activate.is_symlink()):
            activate.unlink()
            self.logger.success(f"Removido: {activate}")

        if self.venv_dir.exists():
            try:
                shutil.rmtree(self.venv_dir)
                self.logger.success(f"Venv removido: {self.venv_dir}")
                self.venv_exists = False
            except OSError as e:
                self.logger.exception(f"Erro ao remover venv: {e}")
                return False

        self.logger.success(f"{self.project_name} desinstalado.")
        return True

    def run_reinstall(self) -> bool:
        self.run_uninstall()
        return self.run()

    def _read_venv_python_abi(self) -> tuple[int, int] | None:
        if not self.venv_python.is_file():
            return None
        try:
            proc = subprocess.run(
                [
                    str(self.venv_python),
                    "-c",
                    "import sys; print(sys.version_info.major, sys.version_info.minor)",
                ],
                check=True,
                capture_output=True,
                text=True,
                timeout=60,
            )
            parts = proc.stdout.strip().split()
            if len(parts) != 2:
                return None
            return int(parts[0]), int(parts[1])
        except (subprocess.CalledProcessError, ValueError, OSError):
            return None

    def _venv_abi_ok(self, abi: tuple[int, int]) -> bool:
        if abi < self.min_python:
            return False
        return not (self.max_python is not None and abi > self.max_python)

    def ensure_project_venv(self) -> bool:
        if self.venv_python.is_file():
            abi = self._read_venv_python_abi()
            if abi is not None and self._venv_abi_ok(abi):
                self.venv_exists = True
                self.logger.info(f"Venv do projecto: {self.venv_dir}")
                return True
            if abi is None:
                self.logger.warning(".venv incompleto; recriando.")
            elif abi < self.min_python:
                self.logger.warning(
                    f"Venv usa Python {abi[0]}.{abi[1]} (mínimo {self.min_python[0]}.{self.min_python[1]}); recriando.",
                )
            elif self.max_python is not None:
                self.logger.warning(
                    f"Venv usa Python {abi[0]}.{abi[1]} (máximo {self.max_python[0]}.{self.max_python[1]}); recriando.",
                )
            self.logger.step(f"Removendo {self.venv_dir}…")
            shutil.rmtree(self.venv_dir, ignore_errors=True)
            self.venv_exists = False

        py_version = self._target_py_version()

        if self._use_uv:
            self.logger.step(f"Criando venv com uv (Python {py_version})...")
            try:
                subprocess.run(
                    [
                        uv_cmd(),
                        "venv",
                        str(self.venv_dir),
                        "--python",
                        py_version,
                        "--seed",
                        "--clear",
                    ],
                    check=True,
                    stdout=self._subprocess_stdout,
                )
            except subprocess.CalledProcessError as e:
                self.logger.exception(f"Falha ao criar venv com uv: {e}")
                return False
        else:
            self.logger.step(f"Criando venv em {self.venv_dir}...")
            try:
                subprocess.run(
                    [self.python_cmd, "-m", "venv", str(self.venv_dir)],
                    check=True,
                    stdout=self._subprocess_stdout,
                )
            except subprocess.CalledProcessError as e:
                self.logger.exception(f"Falha ao criar venv: {e}")
                if not self.is_windows:
                    self.logger.info("Em Debian/Ubuntu: sudo apt install python3-venv")
                return False

        if not self.venv_python.is_file():
            self.logger.error(
                f"Python não encontrado após criar venv: {self.venv_python}"
            )
            return False

        # Valida o ABI do venv criado (ambas as vias): a via não-uv usa o
        # ``self.python_cmd`` do sistema, que pode violar o teto ``max_python``.
        abi = self._read_venv_python_abi()
        if abi is None or not self._venv_abi_ok(abi):
            bound = f">= {self.min_python[0]}.{self.min_python[1]}"
            if self.max_python is not None:
                bound += f", < {self.max_python[0]}.{self.max_python[1]}"
            self.logger.error(
                f"Venv criado com Python {abi} fora dos limites "
                f"({bound}); instala ``uv`` ou um Python compatível."
            )
            shutil.rmtree(self.venv_dir, ignore_errors=True)
            return False

        self.venv_exists = True
        self.logger.success(f"Venv criado: {self.venv_dir}")
        return True

    def _pip_install_cmd(self) -> list[str]:
        if self._use_uv:
            return [uv_cmd(), "pip", "install", "--python", str(self.venv_python)]
        return [str(self.venv_python), "-m", "pip", "install"]

    def install_in_venv(self) -> None:
        self.logger.step("Instalando no venv do projecto...")
        python = str(self.venv_python)
        pip_cmd = self._pip_install_cmd()
        constr = install_all_constraint_argv()
        _root = str(self.project_root)

        if self._use_uv:
            self.logger.info("Usando uv para instalar dependências")
            subprocess.run(
                [
                    uv_cmd(),
                    "pip",
                    "install",
                    "--python",
                    python,
                    "pip",
                    "setuptools>=68,<82",
                    "wheel",
                ],
                check=True,
                cwd=_root,
                stdout=self._subprocess_stdout,
            )
        else:
            subprocess.run(
                [python, "-m", "pip", "install", "--upgrade", *_PIP_BOOTSTRAP],
                check=True,
                cwd=_root,
                stdout=self._subprocess_stdout,
            )

        if self.shared_python is not None:
            shared_root = (self.workspace_root / self.shared_python.path).resolve()
            if (shared_root / "pyproject.toml").is_file() or (
                shared_root / "setup.py"
            ).is_file():
                self.logger.info(f"Sincronizando pacote partilhado: {shared_root}")
                # O shared_python também pode ter deps ``file:`` relativas que
                # o ``uv`` rejeita — absolutiza dentro do seu próprio root.
                with _patched_relative_deps(shared_root, self.logger):
                    subprocess.run(
                        [*pip_cmd, *constr, "-e", str(shared_root)],
                        check=True,
                        cwd=_root,
                        stdout=self._subprocess_stdout,
                    )

        if not self.skip_pytorch:
            self.install_pytorch(pip_cmd, cwd=self.project_root)

        self.logger.info("Instalando pacote em modo editável...")
        with _patched_relative_deps(self.project_root, self.logger):
            if self._use_uv:
                subprocess.run(
                    [*pip_cmd, *constr, "-e", str(self.project_root)],
                    check=True,
                    cwd=_root,
                    stdout=self._subprocess_stdout,
                )
            else:
                subprocess.run(
                    [
                        python,
                        "-m",
                        "pip",
                        "install",
                        *constr,
                        "-e",
                        str(self.project_root),
                    ],
                    check=True,
                    cwd=_root,
                    stdout=self._subprocess_stdout,
                )

        self._write_pth_files()
        self.logger.success("Instalado no venv")

    def _write_pth_files(self) -> None:
        if self.shared_python is not None:
            shared_src = (
                self.workspace_root
                / self.shared_python.path
                / self.shared_python.src_subpath
            ).resolve()
            if shared_src.is_dir():
                ok = link_local_src(
                    venv_dir=self.venv_dir,
                    src_dir=shared_src,
                    import_name=self.shared_python.import_name,
                )
                if ok:
                    self.logger.info(
                        f"PTH: {self.shared_python.import_name} → {shared_src}"
                    )

        project_src = (self.project_root / "src").resolve()
        if project_src.is_dir() and self.cli_name:
            sp = _find_site_packages(self.venv_dir)
            if sp is not None:
                pth = sp / f"_clified_{self.cli_name}.pth"
                pth.write_text(str(project_src), encoding="utf-8")
                self.logger.info(f"PTH: {self.cli_name} → {project_src}")

        for src_dir, import_name in self.cross_dep_folders:
            if src_dir.is_dir():
                ok = link_local_src(
                    venv_dir=self.venv_dir, src_dir=src_dir, import_name=import_name
                )
                if ok:
                    self.logger.info(f"PTH: {import_name} → {src_dir}")

        for pkg in self.local_packages:
            src = (self.project_root / pkg.path).resolve()
            if not src.is_dir():
                src = (self.workspace_root / pkg.path).resolve()
            if src.is_dir():
                ok = link_local_src(
                    venv_dir=self.venv_dir, src_dir=src, import_name=pkg.import_name
                )
                if ok:
                    self.logger.info(f"PTH: {pkg.import_name} → {src}")

    def create_cli_wrappers(self, extra_aliases: list[str] | None = None) -> None:
        python_path = str(self.venv_python) if self.venv_exists else self.python_cmd
        self.create_wrapper(
            self.cli_name,
            python_path=python_path,
            module_name=self.python_module,
        )
        mod = self.python_module
        for alias in extra_aliases or []:
            if self.is_windows:
                command = f'"{python_path}" -m {mod} generate'
            else:
                command = f'"{self.bin_dir}/{self.cli_name}" generate'
            write_cli_wrapper(
                self.bin_dir,
                alias,
                command,
                is_windows=self.is_windows,
                project_name=self.project_name,
                logger=self.logger,
            )
            self.track_artifact(
                self.bin_dir / (f"{alias}.cmd" if self.is_windows else alias)
            )

    def create_activate_wrapper(self) -> Path | None:
        if self.is_windows or not self.venv_exists:
            return None
        wrapper = self.bin_dir / f"{self.cli_name}-activate"
        with open(wrapper, "w", encoding="utf-8") as f:
            f.write("#!/bin/bash\n")
            f.write(f'source "{self.venv_dir}/bin/activate"\n')
            f.write('exec "$@"\n')
        wrapper.chmod(0o755)
        self.logger.success(str(wrapper))
        self.track_artifact(wrapper)
        return wrapper
