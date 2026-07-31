"""Hooks PyTorch/CUDA reutilizáveis (inspirado no AiGameKit)."""

from __future__ import annotations

import os
import subprocess
from typing import TYPE_CHECKING

from clified.installer.base import has_uv, uv_cmd

if TYPE_CHECKING:
    from clified.installer.python_installer import PythonProjectInstaller


def pip_check(installer: PythonProjectInstaller) -> bool:
    """Executa ``pip check`` no venv do projecto."""
    installer.logger.step("Verificando conflitos (pip check)...")
    cmd = [str(installer.venv_python), "-m", "pip", "check"]
    if has_uv():
        cmd = [uv_cmd(), "pip", "check", "--python", str(installer.venv_python)]
    try:
        subprocess.run(cmd, check=True, cwd=str(installer.project_root))
        installer.logger.success("pip check OK")
        return True
    except subprocess.CalledProcessError:
        installer.logger.warning("pip check reportou conflitos — revise dependências")
        return True


def install_nvdiffrast(installer: PythonProjectInstaller) -> bool:
    """Instala nvdiffrast (--no-build-isolation). ``SKIP_NVDIFFRAST=1`` para saltar."""
    skip = (
        os.environ.get("SKIP_NVDIFFRAST", os.environ.get("PAINT3D_SKIP_NVDIFFRAST", ""))
        .strip()
        .lower()
    )
    if skip in ("1", "true", "yes", "on"):
        installer.logger.warning("SKIP_NVDIFFRAST — a saltar nvdiffrast")
        return True

    installer.logger.step("Instalando nvdiffrast...")
    env = os.environ.copy()
    if not (env.get("TORCH_CUDA_ARCH_LIST") or "").strip():
        env["TORCH_CUDA_ARCH_LIST"] = "7.5;8.0;8.6;8.9;9.0"

    url = "git+https://github.com/NVlabs/nvdiffrast.git"
    try:
        if has_uv():
            cmd = [
                uv_cmd(),
                "pip",
                "install",
                "--python",
                str(installer.venv_python),
                url,
                "--no-build-isolation",
            ]
        else:
            cmd = [
                str(installer.venv_python),
                "-m",
                "pip",
                "install",
                url,
                "--no-build-isolation",
            ]
        subprocess.run(cmd, check=True, cwd=str(installer.project_root), env=env)
        installer.logger.success("nvdiffrast instalado")
        return True
    except subprocess.CalledProcessError as exc:
        installer.logger.exception(f"Falha nvdiffrast: {exc}")
        return False
