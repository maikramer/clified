"""BaseInstaller — lógica partilhada entre instaladores."""

from __future__ import annotations

import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

from clified.logging import Logger
from clified.paths import install_all_constraints_file as _constraints_file


def path_env_contains_dir(path_env: str, bin_dir: Path, *, is_windows: bool) -> bool:
    sep = ";" if is_windows else ":"
    if is_windows:
        target = os.path.normcase(os.path.normpath(str(bin_dir)))
        for p in path_env.split(sep):
            if not p.strip():
                continue
            if os.path.normcase(os.path.normpath(p)) == target:
                return True
    else:
        target = os.path.normpath(str(bin_dir.resolve()))
        for p in path_env.split(sep):
            if not p.strip():
                continue
            if os.path.normpath(p) == target:
                return True
    return False


def prepend_path_env(bin_dir: Path, *, is_windows: bool) -> bool:
    """Prepend ``bin_dir`` a ``PATH`` (desta sessão) se ainda não estiver presente.

    Devolve ``True`` se já estava presente (sem alteração), ``False`` se prependido.
    Comparação via :func:`path_env_contains_dir` (normcase-aware).
    """
    path_env = os.environ.get("PATH", "")
    if path_env_contains_dir(path_env, bin_dir, is_windows=is_windows):
        return True
    sep = ";" if is_windows else ":"
    os.environ["PATH"] = f"{bin_dir.resolve()!s}{sep}{path_env}"
    return False


def default_python_command() -> str:
    env = os.environ.get("PYTHON_CMD", "").strip()
    if env:
        return env
    try:
        from clified.installer.bootstrap import find_python_with_pip

        return find_python_with_pip()
    except RuntimeError:
        pass
    if platform.system().lower() == "windows":
        return "python"
    return "python3"


def has_uv() -> bool:
    return shutil.which("uv") is not None


def uv_cmd() -> str:
    found = shutil.which("uv")
    return found or "uv"


def install_all_constraints_file() -> Path | None:
    return _constraints_file()


def install_all_constraint_argv() -> list[str]:
    if os.environ.get("CLIFIED_INSTALL_ALL") != "1":
        return []
    path = install_all_constraints_file()
    if path is None:
        return []
    return ["-c", str(path)]


def write_cli_wrapper(
    bin_dir: Path,
    bin_name: str,
    command: str,
    *,
    is_windows: bool,
    project_name: str,
    logger: Logger,
) -> Path:
    """Escreve um wrapper CLI que executa ``command`` com pass-through de args.

    ``command`` é a string de argv ANTES do pass-through (``%*`` em Windows,
    ``"$@"`` em Unix), ex.: ``'"python" -m mymod'`` ou ``'"node" "/p/cli.mjs"'``.
    Unifica a geração de wrappers ``.cmd`` (Windows) e bash (Unix) usada pelos
    instaladores Python, Bun e aliases de CLI.
    """
    bin_dir.mkdir(parents=True, exist_ok=True)
    if is_windows:
        wrapper = bin_dir / f"{bin_name}.cmd"
        with open(wrapper, "w", encoding="utf-8", newline="\r\n") as f:
            f.write("@echo off\n")
            f.write(f"REM {project_name} — gerado por clified\n")
            f.write(f"{command} %*\n")
        logger.success(str(wrapper))
        return wrapper

    wrapper = bin_dir / bin_name
    with open(wrapper, "w", encoding="utf-8") as f:
        f.write("#!/usr/bin/env bash\n")
        f.write(f"# {project_name} — gerado por clified\n")
        f.write(f'exec {command} "$@"\n')
    wrapper.chmod(0o755)
    logger.success(str(wrapper))
    return wrapper


class BaseInstaller:
    """Classe base para instaladores Clified."""

    def __init__(
        self,
        *,
        project_name: str,
        cli_name: str,
        project_root: Path,
        install_prefix: Path | None = None,
        python_cmd: str = "python3",
    ) -> None:
        self.project_name = project_name
        self.cli_name = cli_name
        self.project_root = project_root.resolve()
        self.install_prefix = install_prefix or Path(
            os.environ.get("INSTALL_PREFIX", str(Path.home() / ".local"))
        )
        self.python_cmd = os.environ.get("PYTHON_CMD", python_cmd)

        self.plat = platform.system().lower()
        self.is_windows = self.plat == "windows"
        self.is_macos = self.plat == "darwin"
        self.is_linux = self.plat == "linux"

        self.bin_dir = self._default_bin_dir()
        self.logger = Logger()

    def _default_bin_dir(self) -> Path:
        return self.install_prefix / "bin"

    def check_python(self, min_version: tuple[int, int] = (3, 10)) -> bool:
        self.logger.step("Verificando Python...")
        try:
            result = subprocess.run(
                [self.python_cmd, "--version"],
                capture_output=True,
                text=True,
                check=True,
            )
            version_str = (result.stdout or result.stderr or "").strip()
            self.logger.info(f"Python detectado: {version_str}")

            major, minor = min_version
            ok = subprocess.run(
                [
                    self.python_cmd,
                    "-c",
                    f"import sys; print('OK' if sys.version_info >= ({major}, {minor}) else 'FAIL')",
                ],
                capture_output=True,
                text=True,
                check=True,
            )
            if "OK" not in ok.stdout:
                self.logger.error(f"Python {major}.{minor}+ necessário")
                return False
            return True
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            self.logger.exception(f"Python não encontrado: {e}")
            return False

    def install_system_deps(self) -> None:
        self.logger.step("Dependências do sistema...")
        if shutil.which("apt-get"):
            self.logger.info("Detectado: Debian/Ubuntu")
            self.logger.warning(
                "Opcional: sudo apt-get install python3-dev python3-venv git"
            )
        elif shutil.which("dnf"):
            self.logger.info("Detectado: Fedora")
            self.logger.warning(
                "Opcional: sudo dnf install python3-devel python3-pip git"
            )
        elif shutil.which("pacman"):
            self.logger.info("Detectado: Arch Linux")
            self.logger.warning(
                "Opcional: sudo pacman -S python python-pip git base-devel"
            )
        elif self.is_windows:
            self.logger.info("Detectado: Windows")
            self.logger.warning(
                "Python: python.org ou ``winget install Python.Python.3.12``. "
                "CUDA: drivers NVIDIA + CUDA Toolkit (nvcc) para compilar extensões GPU.",
            )
        else:
            self.logger.warning(
                "SO não reconhecido — instala Python 3.10+, pip e git manualmente."
            )

    def _python_minor(self) -> int:
        try:
            out = subprocess.run(
                [self.python_cmd, "-c", "import sys; print(sys.version_info[1])"],
                capture_output=True,
                text=True,
                check=True,
            )
            return int((out.stdout or "").strip())
        except (ValueError, subprocess.CalledProcessError):
            return 10

    def install_pytorch(
        self,
        pip_cmd: list[str] | None = None,
        *,
        cwd: str | Path | None = None,
    ) -> None:
        if pip_cmd is None:
            pip_cmd = [self.python_cmd, "-m", "pip", "install"]

        _kw: dict = {}
        if cwd is not None:
            _kw["cwd"] = str(cwd)

        constr = install_all_constraint_argv()
        has_cuda = shutil.which("nvidia-smi") is not None
        py_minor = self._python_minor()

        if has_cuda:
            try:
                result = subprocess.run(["nvidia-smi"], capture_output=True, text=True)
                if "CUDA Version" in result.stdout:
                    for line in result.stdout.split("\n"):
                        if "CUDA Version" in line:
                            cuda_version = line.split("CUDA Version:")[1].split()[0]
                            self.logger.info(f"CUDA detectado: {cuda_version}")
                            cuda_major = int(cuda_version.split(".")[0])
                            cuda_minor = (
                                int(cuda_version.split(".")[1])
                                if "." in cuda_version
                                else 0
                            )
                            if py_minor >= 13 or cuda_major >= 13:
                                self.logger.info(
                                    f"PyTorch via PyPI (CUDA {cuda_version})..."
                                )
                                subprocess.run(
                                    [*pip_cmd, *constr, "torch", "torchvision"],
                                    check=True,
                                    **_kw,
                                )
                                return
                            if cuda_major == 12 and cuda_minor >= 6:
                                idx = "https://download.pytorch.org/whl/cu126"
                            elif cuda_version.startswith("12"):
                                idx = "https://download.pytorch.org/whl/cu121"
                            else:
                                idx = "https://download.pytorch.org/whl/cu118"
                            self.logger.info(f"PyTorch ({idx.split('/')[-1]})...")
                            subprocess.run(
                                [
                                    *pip_cmd,
                                    *constr,
                                    "torch",
                                    "torchvision",
                                    "--index-url",
                                    idx,
                                ],
                                check=True,
                                **_kw,
                            )
                            return
                else:
                    self.logger.info(
                        "nvidia-smi sem 'CUDA Version' — PyTorch CUDA via PyPI...",
                    )
                    subprocess.run(
                        [*pip_cmd, *constr, "torch", "torchvision"], check=True, **_kw
                    )
                    return
            except Exception:
                pass

        self.logger.info("Sem CUDA utilizável; PyTorch CPU...")
        subprocess.run(
            [
                *pip_cmd,
                *constr,
                "torch",
                "torchvision",
                "--index-url",
                "https://download.pytorch.org/whl/cpu",
            ],
            check=True,
            **_kw,
        )

    def create_wrapper(
        self,
        bin_name: str,
        *,
        python_path: str | None = None,
        module_name: str | None = None,
        target_binary: Path | None = None,
    ) -> Path:
        if target_binary:
            command = f'"{target_binary}"'
        else:
            py = python_path or self.python_cmd
            mod = module_name or self.cli_name
            command = f'"{py}" -m {mod}'
        return write_cli_wrapper(
            self.bin_dir,
            bin_name,
            command,
            is_windows=self.is_windows,
            project_name=self.project_name,
            logger=self.logger,
        )

    def _ensure_windows_user_path(self) -> bool:
        if sys.platform != "win32":
            return False

        import ctypes
        import winreg

        bin_str = str(self.bin_dir.resolve())
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Environment",
            0,
            winreg.KEY_READ | winreg.KEY_WRITE,
        )
        try:
            try:
                path, typ = winreg.QueryValueEx(key, "Path")
            except FileNotFoundError:
                path = ""
                typ = winreg.REG_EXPAND_SZ

            parts = [p.strip() for p in path.split(";") if p.strip()]

            def _norm(s: str) -> str:
                return os.path.normcase(os.path.normpath(s))

            target = _norm(bin_str)
            for p in parts:
                if _norm(p) == target:
                    return True

            stripped = path.rstrip().rstrip(";")
            new_path = (stripped + ";" + bin_str) if stripped else bin_str
            winreg.SetValueEx(key, "Path", 0, typ, new_path)
        except OSError as e:
            self.logger.warning(
                f"Não foi possível actualizar o PATH do utilizador: {e}"
            )
            return False
        finally:
            winreg.CloseKey(key)

        try:
            HWND_BROADCAST = 0xFFFF
            WM_SETTINGCHANGE = 0x001A
            SMTO_ABORTIFHUNG = 0x0002
            result = ctypes.c_ulong()
            ctypes.windll.user32.SendMessageTimeoutW(
                HWND_BROADCAST,
                WM_SETTINGCHANGE,
                0,
                ctypes.c_wchar_p("Environment"),
                SMTO_ABORTIFHUNG,
                5000,
                ctypes.byref(result),
            )
        except Exception:
            pass

        return True

    def _ensure_unix_user_path(self) -> bool:
        profile = Path.home() / ".profile"
        bin_str = str(self.bin_dir.resolve())
        marker = "# clified-install PATH"
        line = f'export PATH="{bin_str}:$PATH"'
        try:
            if profile.is_file():
                text = profile.read_text(encoding="utf-8")
                if marker in text and bin_str in text:
                    return True
            block = f"\n{marker}\n{line}\n"
            with open(profile, "a", encoding="utf-8") as f:
                f.write(block)
        except OSError as e:
            self.logger.warning(f"Não foi possível actualizar {profile}: {e}")
            return False

        return True

    def check_path(self) -> bool:
        bin_str = str(self.bin_dir.resolve())
        path_env = os.environ.get("PATH", "")

        if path_env_contains_dir(path_env, self.bin_dir, is_windows=self.is_windows):
            self.logger.success(f"{bin_str} está no PATH")
            return True

        persisted = (
            self._ensure_windows_user_path()
            if self.is_windows
            else self._ensure_unix_user_path()
        )
        prepend_path_env(self.bin_dir, is_windows=self.is_windows)

        if persisted:
            self.logger.success(
                f"{bin_str} adicionado ao PATH permanente; activo nesta sessão."
            )
            if not self.is_windows:
                self.logger.info("Novo terminal: source ~/.profile")
        else:
            self.logger.warning(f"{bin_str} adicionado só ao PATH desta sessão")
            if not self.is_windows:
                self.logger.info(f'Adicione manualmente: export PATH="{bin_str}:$PATH"')
            else:
                self.logger.info(f"Adicione manualmente ao PATH: {bin_str}")

        return persisted

    def show_summary(
        self, commands: list[str], *, extras: list[str] | None = None
    ) -> None:
        lines = ["[bold]Comandos[/bold]" if self.logger.rich_available else "Comandos:"]
        for cmd in commands:
            if self.logger.rich_available:
                lines.append(f"  [cyan]{cmd}[/cyan]")
            else:
                lines.append(f"  {cmd}")

        if extras:
            lines.append("")
            lines.extend(extras)

        lines.append("")
        found = shutil.which(self.cli_name)
        if found:
            if self.logger.rich_available:
                lines.append(
                    f"{self.cli_name} no PATH: [bold green]{found}[/bold green]"
                )
            else:
                lines.append(f"✓ {self.cli_name} no PATH: {found}")
        elif self.is_windows:
            hint = f'[yellow]Adiciona ao PATH:[/yellow] $env:Path += ";{self.bin_dir}"'
            if self.logger.rich_available:
                lines.append(hint)
            else:
                lines.append(f"Adicione ao PATH: {self.bin_dir}")
        elif self.logger.rich_available:
            lines.append(
                f'[yellow]Adiciona ao PATH:[/yellow] export PATH="{self.bin_dir}:$PATH"'
            )
        else:
            lines.append(f'⚠ Adicione ao PATH: export PATH="{self.bin_dir}:$PATH"')

        self.logger.panel(
            "\n".join(lines),
            title=f"{self.project_name} — instalação concluída",
            border="green",
        )
