"""Testes do catálogo remoto (``registry.yaml`` → ``--get``)."""

from __future__ import annotations

import textwrap
import types
from pathlib import Path

import pytest

from clified.installer import catalog


@pytest.fixture
def temp_catalog(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Catálogo temporário isolado do bundled real (path local → sem rede)."""
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
            access: private
        """,
    ).strip()
    path = tmp_path / "registry.yaml"
    path.write_text(content, encoding="utf-8")
    monkeypatch.setenv("CLIFIED_CATALOG", str(path))
    return path


@pytest.fixture
def isolated_catalog(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Ambiente isolado para testes de fetch remoto (CLIFIED_HOME=tmp; sem env catalog)."""
    monkeypatch.setenv("CLIFIED_HOME", str(tmp_path))
    monkeypatch.delenv("CLIFIED_CATALOG", raising=False)
    monkeypatch.delenv("CLIFIED_CATALOG_TTL", raising=False)
    monkeypatch.setattr(catalog, "DEFAULT_CATALOG_URL", "https://example.test/cat.yaml")
    return tmp_path


def _cache_path(home: Path) -> Path:
    return home / "catalog.cache.yaml"


def test_load_catalog_known_tools(temp_catalog: Path) -> None:
    catalog_data = catalog.load_catalog()
    assert set(catalog_data) == {"denv", "cissapi"}
    spec = catalog_data["cissapi"]
    assert spec.tools_yaml == "cli/tools.yaml"
    assert spec.tool == "cissapi"
    assert spec.access == "private"


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
    assert spec.access == "public"


def test_parse_entry_access_defaults_public() -> None:
    spec = catalog._parse_entry("x", {"repo": "https://x.git"})
    assert spec.access == "public"


def test_parse_entry_access_private() -> None:
    spec = catalog._parse_entry("x", {"repo": "https://x.git", "access": "Private"})
    assert spec.access == "private"


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
    """O bundled/registry.yaml real inclui as ferramentas Locatelli (sem rede)."""
    data = catalog.load_catalog(catalog._bundled_catalog_path())
    assert "denv" in data
    assert "LocatelliDockerManager" in data["denv"].repo


# --- fetch remoto / cache / fallback (hermético, mock _fetch_text) ---


def test_remote_fetch_success_writes_cache(
    isolated_catalog: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[str] = []

    def fake(url: str, *, bust_cache: bool = False, **_kw: object) -> str:
        calls.append(url)
        return "tools:\n  foo:\n    repo: https://x/foo.git\n    tool: foo\n"

    monkeypatch.setattr(catalog, "_fetch_text", fake)
    data = catalog.load_catalog()
    assert "foo" in data
    cache = _cache_path(isolated_catalog)
    assert cache.is_file()
    assert "foo" in cache.read_text(encoding="utf-8")
    assert calls == ["https://example.test/cat.yaml"]


def test_cache_fresh_skips_fetch(
    isolated_catalog: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cache = _cache_path(isolated_catalog)
    cache.write_text(
        "tools:\n  cached:\n    repo: https://x/c.git\n    tool: cached\n",
        encoding="utf-8",
    )

    def boom(*a: object, **k: object) -> str:
        raise AssertionError("should not fetch")

    monkeypatch.setattr(catalog, "_fetch_text", boom)
    data = catalog.load_catalog()
    assert "cached" in data


def test_fetch_fail_falls_back_to_bundled(
    isolated_catalog: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fake(url: str, *, bust_cache: bool = False, **_kw: object) -> str:
        raise OSError("boom")

    monkeypatch.setattr(catalog, "_fetch_text", fake)
    data = catalog.load_catalog()
    assert "denv" in data  # bundled fallback


def test_ttl_zero_forces_fetch(
    isolated_catalog: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cache = _cache_path(isolated_catalog)
    cache.write_text(
        "tools:\n  cached:\n    repo: https://x/c.git\n    tool: cached\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("CLIFIED_CATALOG_TTL", "0")
    calls: list[str] = []

    def fake(url: str, *, bust_cache: bool = False, **_kw: object) -> str:
        calls.append(url)
        return "tools:\n  fresh:\n    repo: https://x/f.git\n    tool: fresh\n"

    monkeypatch.setattr(catalog, "_fetch_text", fake)
    data = catalog.load_catalog()
    assert "fresh" in data
    assert "cached" not in data
    assert len(calls) == 1


def test_env_catalog_url_override(
    isolated_catalog: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("CLIFIED_CATALOG", "https://example.test/other.yaml")
    calls: list[str] = []

    def fake(url: str, *, bust_cache: bool = False, **_kw: object) -> str:
        calls.append(url)
        return "tools:\n  other:\n    repo: https://x/o.git\n    tool: other\n"

    monkeypatch.setattr(catalog, "_fetch_text", fake)
    data = catalog.load_catalog()
    assert "other" in data
    assert calls == ["https://example.test/other.yaml"]


def test_ttl_minus_one_bundled_only(
    isolated_catalog: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("CLIFIED_CATALOG_TTL", "-1")

    def boom(*a: object, **k: object) -> str:
        raise AssertionError("should not fetch")

    monkeypatch.setattr(catalog, "_fetch_text", boom)
    data = catalog.load_catalog()
    assert "denv" in data  # bundled, sem rede


def test_fetch_fail_uses_stale_cache(
    isolated_catalog: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cache = _cache_path(isolated_catalog)
    cache.write_text(
        "tools:\n  stale:\n    repo: https://x/s.git\n    tool: stale\n",
        encoding="utf-8",
    )

    def fake(url: str, *, bust_cache: bool = False, **_kw: object) -> str:
        raise OSError("network down")

    monkeypatch.setattr(catalog, "_fetch_text", fake)
    data = catalog.load_catalog()
    assert "stale" in data  # cache stale serve; não cai no bundled


# --- falha suave de clone (auth/acesso) ---


def _fake_run(stderr: str):
    def runner(cmd: list[str], **kw: object) -> types.SimpleNamespace:
        return types.SimpleNamespace(returncode=1, stdout="", stderr=stderr)

    return runner


def test_clone_auth_failure_friendly_message(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    spec = catalog.RepoSpec(
        name="x", repo="https://github.com/LocatelliSupermercados/x.git", tool="x"
    )
    monkeypatch.setattr(
        catalog.subprocess,
        "run",
        _fake_run("fatal: Authentication failed for 'https://github.com/x.git'"),
    )
    with pytest.raises(RuntimeError) as ei:
        catalog.clone_or_update(spec, dest=tmp_path / "x")
    msg = str(ei.value)
    assert "Acesso negado" in msg
    assert "Authentication failed" not in msg  # stderr cru não vaza


def test_clone_not_found_friendly_message(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    spec = catalog.RepoSpec(
        name="y", repo="https://github.com/LocatelliSupermercados/nope.git", tool="y"
    )
    monkeypatch.setattr(
        catalog.subprocess,
        "run",
        _fake_run("fatal: repository 'https://github.com/x/nope.git/' not found"),
    )
    with pytest.raises(RuntimeError) as ei:
        catalog.clone_or_update(spec, dest=tmp_path / "y")
    assert "Acesso negado" in str(ei.value)


def test_clone_generic_failure_keeps_stderr(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    spec = catalog.RepoSpec(name="z", repo="https://x.git", tool="z")
    monkeypatch.setattr(
        catalog.subprocess, "run", _fake_run("fatal: something else went wrong")
    )
    with pytest.raises(RuntimeError) as ei:
        catalog.clone_or_update(spec, dest=tmp_path / "z")
    msg = str(ei.value)
    assert "git clone falhou" in msg
    assert "something else went wrong" in msg
