"""Testes do módulo installer/rust_installer.py."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from clified.installer.rust_installer import RustProjectInstaller


class TestRustInstallerInit:
    def test_unix_paths(self, tmp_path: Path) -> None:
        with patch("clified.installer.base.platform") as mock_plat:
            mock_plat.system.return_value = "Linux"
            mock_plat.lower.return_value = "linux"
            inst = RustProjectInstaller(
                project_name="mat",
                cli_name="mat",
                project_root=tmp_path,
                cargo_bin_name="materialize-cli",
            )
        assert inst.cargo_bin_name == "materialize-cli"
        assert (
            inst.release_binary
            == tmp_path.resolve() / "target" / "release" / "materialize-cli"
        )
        assert (
            inst.debug_binary
            == tmp_path.resolve() / "target" / "debug" / "materialize-cli"
        )
        assert inst.installed_binary == inst.bin_dir / "mat"
        assert inst.installed_binary.suffix == ""

    def test_windows_paths(self, tmp_path: Path) -> None:
        with patch("clified.installer.base.platform") as mock_plat:
            mock_plat.system.return_value = "Windows"
            mock_plat.lower.return_value = "windows"
            inst = RustProjectInstaller(
                project_name="mat",
                cli_name="mat",
                project_root=tmp_path,
                cargo_bin_name="materialize-cli",
            )
        assert inst.release_binary.suffix == ".exe"
        assert inst.debug_binary.suffix == ".exe"
        assert inst.installed_binary.suffix == ".exe"

    def test_inherits_base_attributes(self, tmp_path: Path) -> None:
        prefix = tmp_path / "prefix"
        inst = RustProjectInstaller(
            project_name="mat",
            cli_name="mat",
            project_root=tmp_path,
            cargo_bin_name="materialize-cli",
            install_prefix=prefix,
        )
        assert inst.project_name == "mat"
        assert inst.cli_name == "mat"
        assert inst.install_prefix == prefix


class TestRustInstallerCheckCargo:
    def test_cargo_found(self, tmp_path: Path) -> None:
        inst = RustProjectInstaller(
            project_name="mat",
            cli_name="mat",
            project_root=tmp_path,
            cargo_bin_name="mat",
        )
        mock_result = MagicMock(stdout="cargo 1.80.0\n")
        with patch(
            "clified.installer.rust_installer.subprocess.run", return_value=mock_result
        ):
            assert inst.check_cargo() is True

    def test_cargo_not_found(self, tmp_path: Path) -> None:
        inst = RustProjectInstaller(
            project_name="mat",
            cli_name="mat",
            project_root=tmp_path,
            cargo_bin_name="mat",
        )
        from subprocess import CalledProcessError

        with patch(
            "clified.installer.rust_installer.subprocess.run",
            side_effect=CalledProcessError(1, "cargo"),
        ):
            assert inst.check_cargo() is False


class TestRustInstallerGetExistingBinary:
    def test_prefers_release(self, tmp_path: Path) -> None:
        inst = RustProjectInstaller(
            project_name="mat",
            cli_name="mat",
            project_root=tmp_path,
            cargo_bin_name="mat",
        )
        inst.release_binary.parent.mkdir(parents=True, exist_ok=True)
        inst.release_binary.write_text("binary", encoding="utf-8")
        inst.debug_binary.parent.mkdir(parents=True, exist_ok=True)
        inst.debug_binary.write_text("debug", encoding="utf-8")
        assert inst.get_existing_binary() == inst.release_binary

    def test_falls_back_to_debug(self, tmp_path: Path) -> None:
        inst = RustProjectInstaller(
            project_name="mat",
            cli_name="mat",
            project_root=tmp_path,
            cargo_bin_name="mat",
        )
        inst.debug_binary.parent.mkdir(parents=True, exist_ok=True)
        inst.debug_binary.write_text("debug", encoding="utf-8")
        assert inst.get_existing_binary() == inst.debug_binary

    def test_returns_none_when_missing(self, tmp_path: Path) -> None:
        inst = RustProjectInstaller(
            project_name="mat",
            cli_name="mat",
            project_root=tmp_path,
            cargo_bin_name="mat",
        )
        assert inst.get_existing_binary() is None


class TestRustInstallerUninstall:
    def test_removes_binary(self, tmp_path: Path) -> None:
        inst = RustProjectInstaller(
            project_name="mat",
            cli_name="mat",
            project_root=tmp_path,
            cargo_bin_name="mat",
        )
        inst.bin_dir.mkdir(parents=True, exist_ok=True)
        inst.installed_binary.write_text("binary", encoding="utf-8")
        assert inst.uninstall() is True
        assert not inst.installed_binary.exists()

    def test_succeeds_when_no_binary(self, tmp_path: Path) -> None:
        inst = RustProjectInstaller(
            project_name="mat",
            cli_name="mat",
            project_root=tmp_path,
            cargo_bin_name="mat",
        )
        assert inst.uninstall() is True


class TestRustInstallerTestInstallation:
    def test_version_check_success(self, tmp_path: Path) -> None:
        inst = RustProjectInstaller(
            project_name="mat",
            cli_name="mat",
            project_root=tmp_path,
            cargo_bin_name="mat",
        )
        mock_result = MagicMock(returncode=0, stdout="mat 1.0.0\n")
        with patch(
            "clified.installer.rust_installer.subprocess.run", return_value=mock_result
        ):
            assert inst.test_installation() is True

    def test_version_check_nonzero_still_ok(self, tmp_path: Path) -> None:
        inst = RustProjectInstaller(
            project_name="mat",
            cli_name="mat",
            project_root=tmp_path,
            cargo_bin_name="mat",
        )
        mock_result = MagicMock(returncode=1, stdout="")
        with patch(
            "clified.installer.rust_installer.subprocess.run", return_value=mock_result
        ):
            assert inst.test_installation() is True

    def test_exception_still_ok(self, tmp_path: Path) -> None:
        inst = RustProjectInstaller(
            project_name="mat",
            cli_name="mat",
            project_root=tmp_path,
            cargo_bin_name="mat",
        )
        with patch(
            "clified.installer.rust_installer.subprocess.run",
            side_effect=OSError("not found"),
        ):
            assert inst.test_installation() is True


class TestRustInstallerBuildRelease:
    def test_build_success(self, tmp_path: Path) -> None:
        inst = RustProjectInstaller(
            project_name="mat",
            cli_name="mat",
            project_root=tmp_path,
            cargo_bin_name="mat",
        )
        with patch("clified.installer.rust_installer.subprocess.run"):
            assert inst.build_release() is True

    def test_build_failure(self, tmp_path: Path) -> None:
        inst = RustProjectInstaller(
            project_name="mat",
            cli_name="mat",
            project_root=tmp_path,
            cargo_bin_name="mat",
        )
        from subprocess import CalledProcessError

        inst.logger.exception = MagicMock()
        with patch(
            "clified.installer.rust_installer.subprocess.run",
            side_effect=CalledProcessError(101, "cargo"),
        ):
            assert inst.build_release() is False

    def test_build_cargo_not_found(self, tmp_path: Path) -> None:
        inst = RustProjectInstaller(
            project_name="mat",
            cli_name="mat",
            project_root=tmp_path,
            cargo_bin_name="mat",
        )
        inst.logger.exception = MagicMock()
        with patch(
            "clified.installer.rust_installer.subprocess.run",
            side_effect=FileNotFoundError,
        ):
            assert inst.build_release() is False


class TestRustInstallerInstallBinary:
    def test_installs_existing_release(self, tmp_path: Path) -> None:
        inst = RustProjectInstaller(
            project_name="mat",
            cli_name="mat",
            project_root=tmp_path,
            cargo_bin_name="mat",
        )
        inst.release_binary.parent.mkdir(parents=True, exist_ok=True)
        inst.release_binary.write_text("binary", encoding="utf-8")
        assert inst.install_binary() is True
        assert inst.installed_binary.is_file()

    def test_builds_when_no_binary(self, tmp_path: Path) -> None:
        inst = RustProjectInstaller(
            project_name="mat",
            cli_name="mat",
            project_root=tmp_path,
            cargo_bin_name="mat",
        )
        mock_cargo = MagicMock(stdout="cargo 1.80\n")
        with (
            patch(
                "clified.installer.rust_installer.subprocess.run",
                return_value=mock_cargo,
            ),
            patch.object(inst, "build_release", return_value=True),
        ):
            inst.release_binary.parent.mkdir(parents=True, exist_ok=True)
            inst.release_binary.write_text("binary", encoding="utf-8")
            assert inst.install_binary() is True
