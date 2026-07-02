"""Testes do módulo installer/python_installer.py."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

from clified.installer.python_installer import (
    PythonProjectInstaller,
    _find_site_packages,
    _rewrite_relative_file_deps,
    link_local_src,
)


class TestRewriteRelativeFileDeps:
    def test_no_file_deps(self, tmp_path: Path) -> None:
        text = 'dependencies = ["requests>=2.0"]'
        result, changed = _rewrite_relative_file_deps(text, tmp_path)
        assert changed is False
        assert result == text

    def test_relative_file_dep_absolutised(self, tmp_path: Path) -> None:
        text = 'dependencies = ["mylib @ file:../mylib"]'
        result, changed = _rewrite_relative_file_deps(text, tmp_path)
        assert changed is True
        assert "file://" in result
        assert "../mylib" not in result

    def test_absolute_file_dep_unchanged(self, tmp_path: Path) -> None:
        text = 'dependencies = ["mylib @ file:///opt/mylib"]'
        _result, changed = _rewrite_relative_file_deps(text, tmp_path)
        assert changed is False


class TestFindSitePackages:
    def test_finds_site_packages(self, tmp_path: Path) -> None:
        sp = tmp_path / "lib" / "python3.12" / "site-packages"
        sp.mkdir(parents=True)
        assert _find_site_packages(tmp_path) == sp

    def test_returns_none_when_missing(self, tmp_path: Path) -> None:
        assert _find_site_packages(tmp_path) is None


class TestLinkLocalSrc:
    def test_creates_pth_file(self, tmp_path: Path) -> None:
        venv = tmp_path / ".venv"
        sp = venv / "lib" / "python3.12" / "site-packages"
        sp.mkdir(parents=True)
        src_dir = tmp_path / "src" / "mylib"
        src_dir.mkdir(parents=True)
        assert (
            link_local_src(venv_dir=venv, src_dir=src_dir, import_name="mylib") is True
        )
        pth = sp / "_clified_mylib.pth"
        assert pth.is_file()
        assert str(src_dir) in pth.read_text(encoding="utf-8")

    def test_returns_false_when_no_site_packages(self, tmp_path: Path) -> None:
        venv = tmp_path / ".venv"
        venv.mkdir()
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        assert link_local_src(venv_dir=venv, src_dir=src_dir, import_name="x") is False

    def test_removes_editable_pth(self, tmp_path: Path) -> None:
        venv = tmp_path / ".venv"
        sp = venv / "lib" / "python3.12" / "site-packages"
        sp.mkdir(parents=True)
        (sp / "__editable__.mylib-1.0.pth").write_text("old", encoding="utf-8")
        src_dir = tmp_path / "src" / "mylib"
        src_dir.mkdir(parents=True)
        link_local_src(venv_dir=venv, src_dir=src_dir, import_name="mylib")
        assert not (sp / "__editable__.mylib-1.0.pth").exists()


class TestPythonProjectInstallerInit:
    def test_basic_init(self, tmp_path: Path) -> None:
        with patch("clified.installer.python_installer.has_uv", return_value=False):
            inst = PythonProjectInstaller(
                project_name="demo",
                cli_name="demo",
                project_root=tmp_path,
            )
        assert inst.project_name == "demo"
        assert inst.skip_deps is False
        assert inst.skip_models is False
        assert inst.force is False
        assert inst.skip_pytorch is False
        assert inst.use_venv is False

    def test_venv_paths_unix(self, tmp_path: Path) -> None:
        with (
            patch("clified.installer.python_installer.has_uv", return_value=False),
            patch("clified.installer.base.platform") as mock_plat,
        ):
            mock_plat.system.return_value = "Linux"
            mock_plat.lower.return_value = "linux"
            inst = PythonProjectInstaller(
                project_name="demo",
                cli_name="demo",
                project_root=tmp_path,
            )
        assert inst.venv_dir == tmp_path.resolve() / ".venv"
        assert inst.venv_python == tmp_path.resolve() / ".venv" / "bin" / "python"

    def test_venv_paths_windows(self, tmp_path: Path) -> None:
        with (
            patch("clified.installer.python_installer.has_uv", return_value=False),
            patch("clified.installer.base.platform") as mock_plat,
        ):
            mock_plat.system.return_value = "Windows"
            mock_plat.lower.return_value = "windows"
            inst = PythonProjectInstaller(
                project_name="demo",
                cli_name="demo",
                project_root=tmp_path,
            )
        expected = tmp_path.resolve() / ".venv" / "Scripts" / "python.exe"
        assert inst.venv_python == expected

    def test_python_module_default(self, tmp_path: Path) -> None:
        with patch("clified.installer.python_installer.has_uv", return_value=False):
            inst = PythonProjectInstaller(
                project_name="demo",
                cli_name="my-cli",
                project_root=tmp_path,
            )
        assert inst.python_module == "my_cli"

    def test_python_module_explicit(self, tmp_path: Path) -> None:
        with patch("clified.installer.python_installer.has_uv", return_value=False):
            inst = PythonProjectInstaller(
                project_name="demo",
                cli_name="demo",
                project_root=tmp_path,
                python_module="custom_mod",
            )
        assert inst.python_module == "custom_mod"

    def test_skip_flags(self, tmp_path: Path) -> None:
        with patch("clified.installer.python_installer.has_uv", return_value=False):
            inst = PythonProjectInstaller(
                project_name="demo",
                cli_name="demo",
                project_root=tmp_path,
                skip_deps=True,
                skip_models=True,
                skip_pytorch=True,
                force=True,
            )
        assert inst.skip_deps is True
        assert inst.skip_models is True
        assert inst.skip_pytorch is True
        assert inst.force is True

    @pytest.mark.skipif(
        sys.platform == "win32", reason="layout de venv Unix (.venv/bin/python)"
    )
    def test_venv_exists_when_python_present(self, tmp_path: Path) -> None:
        venv_python = tmp_path / ".venv" / "bin" / "python"
        venv_python.parent.mkdir(parents=True)
        venv_python.write_text("#!/bin/bash", encoding="utf-8")
        with patch("clified.installer.python_installer.has_uv", return_value=False):
            inst = PythonProjectInstaller(
                project_name="demo",
                cli_name="demo",
                project_root=tmp_path,
            )
        assert inst.venv_exists is True

    def test_venv_not_exists_when_python_absent(self, tmp_path: Path) -> None:
        with patch("clified.installer.python_installer.has_uv", return_value=False):
            inst = PythonProjectInstaller(
                project_name="demo",
                cli_name="demo",
                project_root=tmp_path,
            )
        assert inst.venv_exists is False


class TestPythonProjectInstallerPipCmd:
    def test_with_uv(self, tmp_path: Path) -> None:
        with (
            patch("clified.installer.python_installer.has_uv", return_value=True),
            patch(
                "clified.installer.python_installer.uv_cmd", return_value="/usr/bin/uv"
            ),
        ):
            inst = PythonProjectInstaller(
                project_name="demo",
                cli_name="demo",
                project_root=tmp_path,
            )
            cmd = inst._pip_install_cmd()
        assert "pip" in cmd
        assert "install" in cmd

    def test_without_uv(self, tmp_path: Path) -> None:
        with patch("clified.installer.python_installer.has_uv", return_value=False):
            inst = PythonProjectInstaller(
                project_name="demo",
                cli_name="demo",
                project_root=tmp_path,
            )
        cmd = inst._pip_install_cmd()
        assert "-m" in cmd
        assert "pip" in cmd


class TestPythonProjectInstallerTargetPyVersion:
    def test_with_max_python(self, tmp_path: Path) -> None:
        with patch("clified.installer.python_installer.has_uv", return_value=False):
            inst = PythonProjectInstaller(
                project_name="demo",
                cli_name="demo",
                project_root=tmp_path,
                max_python=(3, 13),
            )
        assert inst._target_py_version() == "3.13"

    def test_without_max_python(self, tmp_path: Path) -> None:
        with patch("clified.installer.python_installer.has_uv", return_value=False):
            inst = PythonProjectInstaller(
                project_name="demo",
                cli_name="demo",
                project_root=tmp_path,
                min_python=(3, 10),
            )
        assert inst._target_py_version() == "3.10"


class TestPythonProjectInstallerVenvAbiOk:
    def test_within_bounds(self, tmp_path: Path) -> None:
        with patch("clified.installer.python_installer.has_uv", return_value=False):
            inst = PythonProjectInstaller(
                project_name="demo",
                cli_name="demo",
                project_root=tmp_path,
                min_python=(3, 10),
                max_python=(3, 13),
            )
        assert inst._venv_abi_ok((3, 12)) is True

    def test_below_min(self, tmp_path: Path) -> None:
        with patch("clified.installer.python_installer.has_uv", return_value=False):
            inst = PythonProjectInstaller(
                project_name="demo",
                cli_name="demo",
                project_root=tmp_path,
                min_python=(3, 10),
            )
        assert inst._venv_abi_ok((3, 9)) is False

    def test_above_max(self, tmp_path: Path) -> None:
        with patch("clified.installer.python_installer.has_uv", return_value=False):
            inst = PythonProjectInstaller(
                project_name="demo",
                cli_name="demo",
                project_root=tmp_path,
                max_python=(3, 12),
            )
        assert inst._venv_abi_ok((3, 13)) is False

    def test_no_max(self, tmp_path: Path) -> None:
        with patch("clified.installer.python_installer.has_uv", return_value=False):
            inst = PythonProjectInstaller(
                project_name="demo",
                cli_name="demo",
                project_root=tmp_path,
                min_python=(3, 10),
            )
        assert inst._venv_abi_ok((3, 99)) is True


class TestPythonProjectInstallerRefinePythonBounds:
    def test_pyproject_floor_tighter(self, tmp_path: Path) -> None:
        (tmp_path / "pyproject.toml").write_text(
            '[project]\nrequires-python = ">=3.12"\n',
            encoding="utf-8",
        )
        with patch("clified.installer.python_installer.has_uv", return_value=False):
            inst = PythonProjectInstaller(
                project_name="demo",
                cli_name="demo",
                project_root=tmp_path,
                min_python=(3, 10),
            )
        assert inst.min_python == (3, 12)

    def test_pyproject_ceiling(self, tmp_path: Path) -> None:
        (tmp_path / "pyproject.toml").write_text(
            '[project]\nrequires-python = ">=3.10,<3.14"\n',
            encoding="utf-8",
        )
        with patch("clified.installer.python_installer.has_uv", return_value=False):
            inst = PythonProjectInstaller(
                project_name="demo",
                cli_name="demo",
                project_root=tmp_path,
                min_python=(3, 10),
            )
        assert inst.max_python == (3, 13)

    def test_no_pyproject(self, tmp_path: Path) -> None:
        with patch("clified.installer.python_installer.has_uv", return_value=False):
            inst = PythonProjectInstaller(
                project_name="demo",
                cli_name="demo",
                project_root=tmp_path,
                min_python=(3, 10),
            )
        assert inst.min_python == (3, 10)
        assert inst.max_python is None


class TestPythonProjectInstallerCreateCliWrappers:
    @pytest.mark.skipif(sys.platform == "win32", reason="gera wrapper bash em Unix")
    def test_creates_main_wrapper(self, tmp_path: Path) -> None:
        with patch("clified.installer.python_installer.has_uv", return_value=False):
            inst = PythonProjectInstaller(
                project_name="demo",
                cli_name="demo",
                project_root=tmp_path,
            )
        inst.create_cli_wrappers()
        wrapper = inst.bin_dir / "demo"
        assert wrapper.is_file()
        content = wrapper.read_text(encoding="utf-8")
        assert "-m demo" in content

    @pytest.mark.skipif(sys.platform == "win32", reason="gera alias bash em Unix")
    def test_creates_extra_aliases(self, tmp_path: Path) -> None:
        with patch("clified.installer.python_installer.has_uv", return_value=False):
            inst = PythonProjectInstaller(
                project_name="demo",
                cli_name="demo",
                project_root=tmp_path,
                python_module="demo",
            )
        inst.create_cli_wrappers(extra_aliases=["demo-gen"])
        alias = inst.bin_dir / "demo-gen"
        assert alias.is_file()
        content = alias.read_text(encoding="utf-8")
        assert "generate" in content


class TestPythonProjectInstallerActivateWrapper:
    def test_unix_creates_wrapper(self, tmp_path: Path) -> None:
        venv_python = tmp_path / ".venv" / "bin" / "python"
        venv_python.parent.mkdir(parents=True)
        venv_python.write_text("#!/bin/bash", encoding="utf-8")
        with (
            patch("clified.installer.python_installer.has_uv", return_value=False),
            patch("clified.installer.base.platform") as mock_plat,
        ):
            mock_plat.system.return_value = "Linux"
            mock_plat.lower.return_value = "linux"
            inst = PythonProjectInstaller(
                project_name="demo",
                cli_name="demo",
                project_root=tmp_path,
            )
        wrapper = inst.create_activate_wrapper()
        assert wrapper is not None
        assert wrapper.is_file()
        content = wrapper.read_text(encoding="utf-8")
        assert "activate" in content

    def test_windows_returns_none(self, tmp_path: Path) -> None:
        with (
            patch("clified.installer.python_installer.has_uv", return_value=False),
            patch("clified.installer.base.platform") as mock_plat,
        ):
            mock_plat.system.return_value = "Windows"
            mock_plat.lower.return_value = "windows"
            inst = PythonProjectInstaller(
                project_name="demo",
                cli_name="demo",
                project_root=tmp_path,
            )
        assert inst.create_activate_wrapper() is None

    def test_no_venv_returns_none(self, tmp_path: Path) -> None:
        with patch("clified.installer.python_installer.has_uv", return_value=False):
            inst = PythonProjectInstaller(
                project_name="demo",
                cli_name="demo",
                project_root=tmp_path,
            )
        assert inst.venv_exists is False
        assert inst.create_activate_wrapper() is None
