"""Testes de resolução de paths (wheel / checkout / home)."""

from __future__ import annotations

from pathlib import Path

from clified import paths


def test_package_dir_exists() -> None:
    assert paths.package_dir().is_dir()
    assert (paths.package_dir() / "__init__.py").is_file()


def test_bundled_tools_example_shipped() -> None:
    example = paths.bundled_path("tools.yaml.example")
    assert example.is_file()


def test_bundled_constraints_shipped() -> None:
    assert paths.install_all_constraints_file() is not None


def test_clified_home_override(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("CLIFIED_HOME", str(tmp_path / "cfg"))
    assert paths.clified_home() == (tmp_path / "cfg").resolve()


def test_tools_yaml_clified_tools(tmp_path: Path, monkeypatch) -> None:
    custom = tmp_path / "custom.yaml"
    custom.write_text("workspace:\n  root: .\n  name: T\n\ntools: {}\n")
    monkeypatch.setenv("CLIFIED_TOOLS", str(custom))
    assert paths.tools_yaml_path() == custom.resolve()
