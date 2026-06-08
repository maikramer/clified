"""Tests for requires-python bound parsing and venv target selection."""

from __future__ import annotations

from pathlib import Path

import pytest

from clified.installer.requires_python import (
    bounds_from_pyproject,
    parse_specifier,
    read_requires_python,
)


@pytest.mark.parametrize(
    ("spec", "expected"),
    [
        (">=3.13,<3.14", ((3, 13), (3, 13))),
        (">=3.10", ((3, 10), None)),
        ("<=3.12", (None, (3, 12))),
        ("<3.14", (None, (3, 13))),
        (">3.9", ((3, 10), None)),
        ("==3.12.*", ((3, 12), (3, 12))),
        ("==3.11", ((3, 11), (3, 11))),
        (">=3.10,<4", ((3, 10), None)),  # major-only ceiling => no minor cap
        ("garbage", (None, None)),
    ],
)
def test_parse_specifier(spec: str, expected: tuple) -> None:
    assert parse_specifier(spec) == expected


def test_read_and_bounds_from_pyproject(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "x"\nrequires-python = ">=3.13,<3.14"\n',
        encoding="utf-8",
    )
    assert read_requires_python(tmp_path) == ">=3.13,<3.14"
    assert bounds_from_pyproject(tmp_path) == ((3, 13), (3, 13))


def test_bounds_missing_file(tmp_path: Path) -> None:
    assert bounds_from_pyproject(tmp_path) == (None, None)


def test_bounds_no_field(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "x"\n', encoding="utf-8"
    )
    assert bounds_from_pyproject(tmp_path) == (None, None)


def _installer(project_root: Path, **kw):
    from clified.installer.python_installer import PythonProjectInstaller

    return PythonProjectInstaller(
        project_name="x",
        cli_name="x",
        project_root=project_root,
        **kw,
    )


def test_installer_honours_pyproject_ceiling(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nrequires-python = ">=3.13,<3.14"\n', encoding="utf-8"
    )
    inst = _installer(tmp_path, min_python=(3, 10))
    # Floor tightened up from the registry default; ceiling discovered.
    assert inst.min_python == (3, 13)
    assert inst.max_python == (3, 13)
    assert inst._target_py_version() == "3.13"
    # A newer interpreter must be rejected so the venv is recreated.
    assert inst._venv_abi_ok((3, 14)) is False
    assert inst._venv_abi_ok((3, 13)) is True


def test_installer_unconstrained_keeps_floor(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nrequires-python = ">=3.10"\n', encoding="utf-8"
    )
    inst = _installer(tmp_path, min_python=(3, 11))
    assert inst.min_python == (3, 11)  # registry floor wins (tighter)
    assert inst.max_python is None
    assert inst._target_py_version() == "3.11"
