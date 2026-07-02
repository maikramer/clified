"""Testes do catálogo remoto (``registry.yaml`` → ``--get``)."""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from clified.installer import catalog


@pytest.fixture
def temp_catalog(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Catálogo temporário isolado do bundled real."""
    content = textwrap.dedent(
        """
        tools:
          denv:
            repo: https://example.com/denv.git
            tool: denv
            tools_yaml: tools.yaml
            description: "Denv mock"
          cissapi:
            repo: https://example.com/ciss.git
            tool: cissapi
            tools_yaml: cli/tools.yaml
            description: "Ciss mock"
        """,
    ).strip()
    path = tmp_path / "registry.yaml"
    path.write_text(content, encoding="utf-8")
    monkeypatch.setenv("CLIFIED_CATALOG", str(path))
    return path


def test_load_catalog_known_tools(temp_catalog: Path) -> None:
    catalog_data = catalog.load_catalog()
    assert set(catalog_data) == {"denv", "cissapi"}
    spec = catalog_data["cissapi"]
    assert spec.tools_yaml == "cli/tools.yaml"
    assert spec.tool == "cissapi"


def test_resolve_case_insensitive(temp_catalog: Path) -> None:
    assert catalog.resolve("DENV").name == "denv"
    assert catalog.resolve("CissApi").name == "cissapi"


def test_resolve_unknown_raises_key_error(temp_catalog: Path) -> None:
    with pytest.raises(KeyError):
        catalog.resolve("nope")


def test_repo_spec_defaults() -> None:
    spec = catalog.RepoSpec(name="x", repo="https://x.git", tool="x")
    assert spec.tools_yaml == "tools.yaml"
    assert spec.description == ""


def test_resolve_tools_yaml_missing_raises(tmp_path: Path) -> None:
    spec = catalog.RepoSpec(
        name="x", repo="https://x.git", tool="x", tools_yaml="nope.yaml"
    )
    with pytest.raises(FileNotFoundError):
        catalog.resolve_tools_yaml(spec, tmp_path)


def test_resolve_tools_yaml_found(tmp_path: Path) -> None:
    spec = catalog.RepoSpec(
        name="x", repo="https://x.git", tool="x", tools_yaml="cli/tools.yaml"
    )
    (tmp_path / "cli").mkdir()
    (tmp_path / "cli" / "tools.yaml").write_text("tools: {}\n", encoding="utf-8")
    assert catalog.resolve_tools_yaml(spec, tmp_path).is_file()


def test_sources_dir_env_override(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("CLIFIED_SOURCES", str(tmp_path / "other"))
    assert catalog.sources_dir() == (tmp_path / "other").resolve()


def test_bundled_catalog_ships_locatelli_tools() -> None:
    """O bundled/registry.yaml real inclui as ferramentas Locatelli."""
    import os

    os.environ.pop("CLIFIED_CATALOG", None)
    data = catalog.load_catalog()
    assert "denv" in data
    assert "LocatelliDockerManager" in data["denv"].repo
