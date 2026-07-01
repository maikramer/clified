# Development and publishing

## Setup

```bash
git clone https://github.com/maikramer/clified.git
cd clified
python3 -m venv .installer-venv
source .installer-venv/bin/activate
pip install -e ".[dev]"
cp tools.yaml.example tools.yaml   # optional local registry
```

## Tests and quality

```bash
pytest -q
pytest -q --cov=clified --cov-report=term-missing
ruff check src tests
ruff format --check src tests
```

CI (GitHub Actions) runs on Python 3.10, 3.12, and 3.13.

## Code layout

```
src/clified/
├── __init__.py          # __version__
├── __main__.py          # python -m clified
├── logging.py
├── paths.py             # bundled data, CLIFIED_HOME, tools.yaml
├── cli/                 # CLI library
├── core/                # retry, paths, state, circuit breaker
├── patterns/            # regex diagnosis
├── hooks/               # MCP, skills, pytorch
├── integrations/        # mcp.json
└── installer/
    ├── bootstrap.py     # pip install clified
    ├── python_select.py # detect Python with pip
    ├── registry.py      # tools.yaml → ToolSpec
    ├── unified.py       # clified-install CLI
    ├── python_installer.py
    ├── rust_installer.py
    └── bun_installer.py
```

## Entry points

Defined in `pyproject.toml`:

| Command | Module |
|---------|--------|
| `clified-install` | `clified.installer.unified:main` |
| `clified` | `clified.__main__:main` |

## Versioning

Keep in sync:

- `src/clified/__init__.py` → `__version__`
- `pyproject.toml` → `version`

## Publishing to PyPI

### Automatic (recommended)

1. Commit and push to `main`
2. Create GitHub release `vX.Y.Z`
3. Workflow `.github/workflows/publish.yml` runs lint, tests, build, and publish

Requires: GitHub environment `pypi` with Trusted Publishing on PyPI.

### Manual

```bash
pip install hatch
hatch build
hatch publish
```

## Useful scripts

| Script | Purpose |
|--------|---------|
| `install.sh` | Dev: create `.installer-venv` + editable install |
| `scripts/run-clified.sh` | PyPI or local |
| `scripts/install-bootstrap.sh` | Copy into migrated projects (Linux/macOS) |
| `scripts/install-bootstrap.ps1` | Copy into migrated projects (Windows) |

## Adding a built-in hook

1. Implement in `src/clified/hooks/`
2. Export in `hooks/__init__.py` if public
3. Document in `docs/hooks.md` and `tools.yaml.example`
4. Add tests in `tests/`

## Adding a registry field

1. `ToolSpec` in `registry.py`
2. Parsing in `_parse_tool`
3. Consumption in the relevant installer
4. Example in `tools.yaml.example`
5. Tests in `tests/test_registry.py`

## Conventions

- Python >= 3.10
- Ruff strict (see `pyproject.toml`)
- Docstrings on public hooks
- CLI messages in English (project docs: English primary, README_PT for Portuguese)
- No hardcoded project names in core — use YAML + hooks
