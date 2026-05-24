# Troubleshooting

## Installing Clified

### `No module named pip` when running `./install.sh`

**Cause:** `python3` on PATH points at a venv (Sherpa, conda, etc.) without pip.

**Fix:**

```bash
PYTHON_CMD=/usr/bin/python3.12 ./install.sh
```

Or install `python3-full` (Debian/Ubuntu). Bootstrap automatically tries `python3.14`, `python3.12`, …

### `externally-managed-environment` (PEP 668)

**Cause:** Ubuntu/Debian blocks `pip install --user` on system Python.

**Fixes (preferred order):**

```bash
pipx install clified
# or let bootstrap retry automatically (--break-system-packages)
# or manually:
pip install --user --break-system-packages clified
```

### `clified-install: command not found` after pip

**Cause:** `~/.local/bin` is not on PATH.

**Fix:** Add to `~/.bashrc`:

```bash
export PATH="$HOME/.local/bin:$PATH"
```

Bootstrap adds it temporarily for the same session; restart the shell or `source ~/.bashrc`.

### Wrong Clified version

```bash
pip install --user --upgrade "clified>=0.4.1"
clified-install --help
```

Features by version:

| Version | Highlights |
|---------|------------|
| 0.4.0 | PyPI, bundled data, basic bootstrap |
| 0.4.1 | PEP 668, Python detection, Rust `post_install` |

## Installing tools

### `Directory not found` / tool missing

- Confirm `CLIFIED_TOOLS` points at the correct `tools.yaml`
- Check `workspace.root` and `folder:` relative to the YAML file
- For Python: project needs `pyproject.toml`, `setup.py`, or `requirements.txt`

### venv not created / permissions

```bash
sudo apt install python3-venv python3-full
```

Or force recreate:

```bash
rm -rf .venv
clified-install my-tool --force
```

### Rust: `cargo not found`

Install [rustup](https://rustup.rs). For GTK GUIs (ai2print):

```bash
sudo apt install libgtk-4-dev libadwaita-1-dev
```

### Hook `post_install` failed

```bash
clified-install my-tool --verbose
```

Ensure the hook module is at repo root (`clified_install.py`) or on `sys.path` (shared_python).

### ai2print: GUI opens but Python fails

Check wrapper:

```bash
cat "$(which ai2print)"
# should export STL_REPAIR_ROOT and STL_REPAIR_PYTHON → .venv/bin/python3
./install.sh --action reinstall
```

## MCP / Cursor

### MCP server not showing up

- Did `post_install` run? Reinstall: `./install.sh --action reinstall`
- Check `~/.cursor/mcp.json` (or equivalent Cursor config)
- Variables: `CLIFIED_MCP_NAME`, `CLIFIED_MCP_ARGS`

## Clified development

### Local tests

```bash
pip install -e ".[dev]"
pytest -q
ruff check src tests
```

### Use local checkout instead of PyPI

```bash
export CLIFIED_ROOT=/path/to/clified
pip install -e "$CLIFIED_ROOT[dev]"
```

Migrated projects **do not need** `CLIFIED_ROOT` — only Clified itself for dev.

### CI fails on Ruff

```bash
ruff check src tests --fix
ruff format src tests
```

## Getting help

1. `clified-install --verbose`
2. `CLIFIED_RETRY=1` for automatic retries
3. [GitHub Issues](https://github.com/maikramer/clified/issues)

Include: OS, Python version (`python3 -V`), output of `clified-install --list`, and full log with `--verbose`.
