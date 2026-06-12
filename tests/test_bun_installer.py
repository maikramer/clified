"""Testes do módulo installer/bun_installer.py."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from clified.installer.bun_installer import BunProjectInstaller


class TestBunInstallerInit:
    def test_default_cli_script(self, tmp_path: Path) -> None:
        inst = BunProjectInstaller(
            project_name="vibe",
            cli_name="vibe",
            project_root=tmp_path,
        )
        assert inst.cli_script == tmp_path.resolve() / "scripts" / "vibe-cli.mjs"

    def test_custom_cli_script(self, tmp_path: Path) -> None:
        script = tmp_path / "custom.mjs"
        inst = BunProjectInstaller(
            project_name="vibe",
            cli_name="vibe",
            project_root=tmp_path,
            cli_script=script,
        )
        assert inst.cli_script == script

    def test_custom_build_command(self, tmp_path: Path) -> None:
        inst = BunProjectInstaller(
            project_name="vibe",
            cli_name="vibe",
            project_root=tmp_path,
            build_command="bundle",
        )
        assert inst.build_command == "bundle"

    def test_custom_install_args(self, tmp_path: Path) -> None:
        inst = BunProjectInstaller(
            project_name="vibe",
            cli_name="vibe",
            project_root=tmp_path,
            install_args=("install",),
        )
        assert inst.install_args == ("install",)

    def test_default_install_args(self, tmp_path: Path) -> None:
        inst = BunProjectInstaller(
            project_name="vibe",
            cli_name="vibe",
            project_root=tmp_path,
        )
        assert inst.install_args == ("install", "--frozen-lockfile")

    def test_inherits_base_attributes(self, tmp_path: Path) -> None:
        prefix = tmp_path / "prefix"
        inst = BunProjectInstaller(
            project_name="vibe",
            cli_name="vibe",
            project_root=tmp_path,
            install_prefix=prefix,
        )
        assert inst.project_name == "vibe"
        assert inst.cli_name == "vibe"
        assert inst.install_prefix == prefix
        assert inst.bin_dir == prefix / "bin"


class TestBunInstallerCheckBun:
    def test_bun_found(self, tmp_path: Path) -> None:
        inst = BunProjectInstaller(
            project_name="vibe",
            cli_name="vibe",
            project_root=tmp_path,
        )
        mock_out = MagicMock(stdout="1.1.0\n", stderr="")
        with (
            patch(
                "clified.installer.bun_installer.shutil.which",
                return_value="/usr/bin/bun",
            ),
            patch(
                "clified.installer.bun_installer.subprocess.run", return_value=mock_out
            ),
        ):
            assert inst.check_bun() is True

    def test_bun_not_found(self, tmp_path: Path) -> None:
        inst = BunProjectInstaller(
            project_name="vibe",
            cli_name="vibe",
            project_root=tmp_path,
        )
        with patch("clified.installer.bun_installer.shutil.which", return_value=None):
            assert inst.check_bun() is False

    def test_bun_execution_fails(self, tmp_path: Path) -> None:
        inst = BunProjectInstaller(
            project_name="vibe",
            cli_name="vibe",
            project_root=tmp_path,
        )
        from subprocess import CalledProcessError

        inst.logger.exception = MagicMock()
        with (
            patch(
                "clified.installer.bun_installer.shutil.which",
                return_value="/usr/bin/bun",
            ),
            patch(
                "clified.installer.bun_installer.subprocess.run",
                side_effect=CalledProcessError(1, "bun"),
            ),
        ):
            assert inst.check_bun() is False


class TestBunInstallerCheckNode:
    def test_node_found(self, tmp_path: Path) -> None:
        inst = BunProjectInstaller(
            project_name="vibe",
            cli_name="vibe",
            project_root=tmp_path,
        )
        mock_out = MagicMock(stdout="v20.0.0\n", stderr="")
        with (
            patch(
                "clified.installer.bun_installer.shutil.which",
                return_value="/usr/bin/node",
            ),
            patch(
                "clified.installer.bun_installer.subprocess.run", return_value=mock_out
            ),
        ):
            assert inst.check_node() is True

    def test_node_not_found(self, tmp_path: Path) -> None:
        inst = BunProjectInstaller(
            project_name="vibe",
            cli_name="vibe",
            project_root=tmp_path,
        )
        with patch("clified.installer.bun_installer.shutil.which", return_value=None):
            assert inst.check_node() is False


class TestBunInstallerInstallWrapper:
    def test_fails_when_cli_script_missing(self, tmp_path: Path) -> None:
        inst = BunProjectInstaller(
            project_name="vibe",
            cli_name="vibe",
            project_root=tmp_path,
        )
        with patch(
            "clified.installer.bun_installer.shutil.which", return_value="/usr/bin/node"
        ):
            assert inst.install_wrapper() is False

    def test_unix_wrapper(self, tmp_path: Path) -> None:
        script = tmp_path / "scripts" / "vibe-cli.mjs"
        script.parent.mkdir(parents=True)
        script.write_text("console.log('hi')", encoding="utf-8")
        inst = BunProjectInstaller(
            project_name="vibe",
            cli_name="vibe",
            project_root=tmp_path,
        )
        with patch(
            "clified.installer.bun_installer.shutil.which", return_value="/usr/bin/node"
        ):
            result = inst.install_wrapper()
        assert result is True
        wrapper = inst.bin_dir / "vibe"
        assert wrapper.is_file()
        content = wrapper.read_text(encoding="utf-8")
        assert "/usr/bin/node" in content

    def test_windows_wrapper(self, tmp_path: Path) -> None:
        script = tmp_path / "scripts" / "vibe-cli.mjs"
        script.parent.mkdir(parents=True)
        script.write_text("console.log('hi')", encoding="utf-8")
        with patch("clified.installer.base.platform") as mock_plat:
            mock_plat.system.return_value = "Windows"
            mock_plat.lower.return_value = "windows"
            inst = BunProjectInstaller(
                project_name="vibe",
                cli_name="vibe",
                project_root=tmp_path,
            )
        with patch(
            "clified.installer.bun_installer.shutil.which", return_value="C:\\node.exe"
        ):
            result = inst.install_wrapper()
        assert result is True
        wrapper = inst.bin_dir / "vibe.cmd"
        assert wrapper.is_file()
        content = wrapper.read_text(encoding="utf-8")
        assert "@echo off" in content


class TestBunInstallerUninstall:
    def test_removes_wrapper(self, tmp_path: Path) -> None:
        inst = BunProjectInstaller(
            project_name="vibe",
            cli_name="vibe",
            project_root=tmp_path,
        )
        inst.bin_dir.mkdir(parents=True, exist_ok=True)
        wrapper = inst.bin_dir / "vibe"
        wrapper.write_text("#!/bin/bash", encoding="utf-8")
        assert inst.uninstall() is True
        assert not wrapper.exists()

    def test_succeeds_when_no_wrapper(self, tmp_path: Path) -> None:
        inst = BunProjectInstaller(
            project_name="vibe",
            cli_name="vibe",
            project_root=tmp_path,
        )
        assert inst.uninstall() is True


class TestBunInstallerTestInstallation:
    def test_wrapper_missing_returns_false(self, tmp_path: Path) -> None:
        inst = BunProjectInstaller(
            project_name="vibe",
            cli_name="vibe",
            project_root=tmp_path,
        )
        assert inst.test_installation() is False

    def test_version_check_success(self, tmp_path: Path) -> None:
        inst = BunProjectInstaller(
            project_name="vibe",
            cli_name="vibe",
            project_root=tmp_path,
        )
        inst.bin_dir.mkdir(parents=True, exist_ok=True)
        wrapper = inst.bin_dir / "vibe"
        wrapper.write_text("#!/bin/bash", encoding="utf-8")
        mock_result = MagicMock(returncode=0, stdout="1.0.0\n")
        with patch(
            "clified.installer.bun_installer.subprocess.run", return_value=mock_result
        ):
            assert inst.test_installation() is True
