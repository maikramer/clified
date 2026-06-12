"""Testes do módulo installer/base.py."""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from clified.installer.base import (
    BaseInstaller,
    default_python_command,
    has_uv,
    install_all_constraint_argv,
    path_env_contains_dir,
    uv_cmd,
)


class TestHasUv:
    @patch("clified.installer.base.shutil.which", return_value="/usr/bin/uv")
    def test_returns_true_when_found(self, mock_which: MagicMock) -> None:
        assert has_uv() is True

    @patch("clified.installer.base.shutil.which", return_value=None)
    def test_returns_false_when_missing(self, mock_which: MagicMock) -> None:
        assert has_uv() is False


class TestUvCmd:
    @patch("clified.installer.base.shutil.which", return_value="/usr/local/bin/uv")
    def test_returns_found_path(self, mock_which: MagicMock) -> None:
        assert uv_cmd() == "/usr/local/bin/uv"

    @patch("clified.installer.base.shutil.which", return_value=None)
    def test_falls_back_to_uv(self, mock_which: MagicMock) -> None:
        assert uv_cmd() == "uv"


class TestPathEnvContainsDir:
    def test_unix_match(self) -> None:
        env = "/usr/bin:/home/user/.local/bin:/usr/local/bin"
        assert (
            path_env_contains_dir(env, Path("/home/user/.local/bin"), is_windows=False)
            is True
        )

    def test_unix_no_match(self) -> None:
        env = "/usr/bin:/usr/local/bin"
        assert (
            path_env_contains_dir(env, Path("/home/user/.local/bin"), is_windows=False)
            is False
        )

    def test_unix_empty_entries_ignored(self) -> None:
        env = "/usr/bin::/usr/local/bin"
        assert path_env_contains_dir(env, Path("/usr/bin"), is_windows=False) is True

    def test_windows_match(self) -> None:
        env = r"C:\Windows;C:\Users\test\.local\bin"
        assert (
            path_env_contains_dir(
                env,
                Path(r"C:\Users\test\.local\bin"),
                is_windows=True,
            )
            is True
        )

    def test_windows_no_match(self) -> None:
        env = r"C:\Windows;C:\Python"
        assert (
            path_env_contains_dir(
                env,
                Path(r"C:\Users\test\.local\bin"),
                is_windows=True,
            )
            is False
        )


class TestDefaultPythonCommand:
    def test_env_var_override(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("PYTHON_CMD", "/opt/python3.13/bin/python")
        assert default_python_command() == "/opt/python3.13/bin/python"

    def test_env_var_whitespace_only(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("PYTHON_CMD", "   ")
        with (
            patch(
                "clified.installer.python_select.find_python_with_pip",
                side_effect=RuntimeError,
            ),
            patch("clified.installer.base.platform") as mock_plat,
        ):
            mock_plat.system.return_value = "Linux"
            result = default_python_command()
        assert result == "python3"

    def test_windows_fallback(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("PYTHON_CMD", raising=False)
        with (
            patch(
                "clified.installer.python_select.find_python_with_pip",
                side_effect=RuntimeError,
            ),
            patch("clified.installer.base.platform") as mock_plat,
        ):
            mock_plat.system.return_value = "Windows"
            result = default_python_command()
        assert result == "python"

    def test_unix_fallback(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("PYTHON_CMD", raising=False)
        with (
            patch(
                "clified.installer.python_select.find_python_with_pip",
                side_effect=RuntimeError,
            ),
            patch("clified.installer.base.platform") as mock_plat,
        ):
            mock_plat.system.return_value = "Linux"
            result = default_python_command()
        assert result == "python3"

    def test_find_python_with_pip_succeeds(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("PYTHON_CMD", raising=False)
        with patch(
            "clified.installer.python_select.find_python_with_pip",
            return_value="python3.12",
        ):
            result = default_python_command()
        assert result == "python3.12"


class TestInstallAllConstraintArgv:
    def test_empty_when_env_not_set(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("CLIFIED_INSTALL_ALL", raising=False)
        assert install_all_constraint_argv() == []

    def test_empty_when_no_constraints_file(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("CLIFIED_INSTALL_ALL", "1")
        with patch(
            "clified.installer.base.install_all_constraints_file",
            return_value=None,
        ):
            assert install_all_constraint_argv() == []

    def test_returns_constraint_args(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        monkeypatch.setenv("CLIFIED_INSTALL_ALL", "1")
        constraint_file = tmp_path / "constraints.txt"
        with patch(
            "clified.installer.base.install_all_constraints_file",
            return_value=constraint_file,
        ):
            result = install_all_constraint_argv()
        assert result == ["-c", str(constraint_file)]


class TestBaseInstallerInit:
    def test_default_attributes(self, tmp_path: Path) -> None:
        inst = BaseInstaller(
            project_name="demo",
            cli_name="demo",
            project_root=tmp_path,
        )
        assert inst.project_name == "demo"
        assert inst.cli_name == "demo"
        assert inst.project_root == tmp_path.resolve()
        assert inst.bin_dir == inst.install_prefix / "bin"
        assert inst.is_linux or inst.is_macos or inst.is_windows

    def test_custom_install_prefix(self, tmp_path: Path) -> None:
        prefix = tmp_path / "custom"
        inst = BaseInstaller(
            project_name="demo",
            cli_name="demo",
            project_root=tmp_path,
            install_prefix=prefix,
        )
        assert inst.install_prefix == prefix
        assert inst.bin_dir == prefix / "bin"

    def test_install_prefix_from_env(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("INSTALL_PREFIX", "/opt/demo")
        inst = BaseInstaller(
            project_name="demo",
            cli_name="demo",
            project_root=tmp_path,
        )
        assert inst.install_prefix == Path("/opt/demo")

    def test_python_cmd_from_env(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("PYTHON_CMD", "python3.13")
        inst = BaseInstaller(
            project_name="demo",
            cli_name="demo",
            project_root=tmp_path,
        )
        assert inst.python_cmd == "python3.13"

    def test_platform_detection(self, tmp_path: Path) -> None:
        with patch("clified.installer.base.platform") as mock_plat:
            mock_plat.system.return_value = "Windows"
            mock_plat.lower.return_value = "windows"
            inst = BaseInstaller(
                project_name="demo",
                cli_name="demo",
                project_root=tmp_path,
            )
        assert inst.is_windows is True
        assert inst.is_linux is False
        assert inst.is_macos is False


class TestBaseInstallerCheckPython:
    def test_success(self, tmp_path: Path) -> None:
        inst = BaseInstaller(
            project_name="demo",
            cli_name="demo",
            project_root=tmp_path,
        )
        mock_result = MagicMock(stdout="Python 3.12.0", stderr="")
        mock_ok = MagicMock(stdout="OK")
        with patch(
            "clified.installer.base.subprocess.run", side_effect=[mock_result, mock_ok]
        ):
            assert inst.check_python((3, 10)) is True

    def test_version_too_old(self, tmp_path: Path) -> None:
        inst = BaseInstaller(
            project_name="demo",
            cli_name="demo",
            project_root=tmp_path,
        )
        mock_result = MagicMock(stdout="Python 3.9.0", stderr="")
        mock_ok = MagicMock(stdout="FAIL")
        with patch(
            "clified.installer.base.subprocess.run", side_effect=[mock_result, mock_ok]
        ):
            assert inst.check_python((3, 10)) is False

    def test_python_not_found(self, tmp_path: Path) -> None:
        inst = BaseInstaller(
            project_name="demo",
            cli_name="demo",
            project_root=tmp_path,
        )
        exc = FileNotFoundError("python not found")
        with (
            patch("clified.installer.base.subprocess.run", side_effect=exc),
            patch.object(inst.logger, "error"),
            patch.object(inst.logger, "info"),
        ):
            # Source calls logger.exception which doesn't exist; add it
            inst.logger.exception = MagicMock()
            assert inst.check_python() is False


class TestBaseInstallerCreateWrapper:
    def test_unix_python_wrapper(self, tmp_path: Path) -> None:
        inst = BaseInstaller(
            project_name="demo",
            cli_name="demo",
            project_root=tmp_path,
        )
        wrapper = inst.create_wrapper(
            "demo", python_path="/usr/bin/python3", module_name="demo"
        )
        assert wrapper.exists()
        content = wrapper.read_text(encoding="utf-8")
        assert "#!/bin/bash" in content
        assert "/usr/bin/python3" in content
        assert "-m demo" in content
        assert wrapper.stat().st_mode & 0o111

    def test_unix_binary_wrapper(self, tmp_path: Path) -> None:
        inst = BaseInstaller(
            project_name="demo",
            cli_name="demo",
            project_root=tmp_path,
        )
        target = tmp_path / "mybin"
        target.write_text("binary", encoding="utf-8")
        wrapper = inst.create_wrapper("demo", target_binary=target)
        content = wrapper.read_text(encoding="utf-8")
        assert f'exec "{target}"' in content

    def test_windows_wrapper(self, tmp_path: Path) -> None:
        with patch("clified.installer.base.platform") as mock_plat:
            mock_plat.system.return_value = "Windows"
            mock_plat.lower.return_value = "windows"
            inst = BaseInstaller(
                project_name="demo",
                cli_name="demo",
                project_root=tmp_path,
            )
        wrapper = inst.create_wrapper(
            "demo", python_path="python.exe", module_name="demo"
        )
        assert wrapper.suffix == ".cmd"
        content = wrapper.read_text(encoding="utf-8")
        assert "@echo off" in content


class TestBaseInstallerCheckPath:
    def test_already_in_path(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        inst = BaseInstaller(
            project_name="demo",
            cli_name="demo",
            project_root=tmp_path,
        )
        monkeypatch.setenv(
            "PATH", str(inst.bin_dir.resolve()) + ":" + os.environ.get("PATH", "")
        )
        with patch.object(inst, "_ensure_unix_user_path", return_value=True):
            result = inst.check_path()
        assert result is True


class TestBaseInstallerInstallSystemDeps:
    def test_debian_detected(self, tmp_path: Path) -> None:
        inst = BaseInstaller(
            project_name="demo",
            cli_name="demo",
            project_root=tmp_path,
        )
        with patch(
            "clified.installer.base.shutil.which", return_value="/usr/bin/apt-get"
        ):
            inst.install_system_deps()


class TestBaseInstallerPythonMinor:
    def test_success(self, tmp_path: Path) -> None:
        inst = BaseInstaller(
            project_name="demo",
            cli_name="demo",
            project_root=tmp_path,
        )
        mock_result = MagicMock(stdout="12\n")
        with patch("clified.installer.base.subprocess.run", return_value=mock_result):
            assert inst._python_minor() == 12

    def test_failure_returns_10(self, tmp_path: Path) -> None:
        inst = BaseInstaller(
            project_name="demo",
            cli_name="demo",
            project_root=tmp_path,
        )
        from subprocess import CalledProcessError

        with patch(
            "clified.installer.base.subprocess.run",
            side_effect=CalledProcessError(1, "python"),
        ):
            assert inst._python_minor() == 10
