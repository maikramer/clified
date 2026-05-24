# Hooks

Hooks customize installation **without changing Clified core**. Register them in `tools.yaml` as `module:function`.

## Types

| YAML field | When it runs | Replaces default? |
|------------|--------------|-------------------|
| `custom_install` | During Python install, **before** wrappers | **Yes** — replaces `pip install -e` |
| `post_install` | **After** main install and wrappers | No — complements |

Supported on:

- **Python** — `custom_install` and `post_install`
- **Rust** — `post_install` (since v0.4.1)
- **Bun** — use project-specific patterns for now

## Built-in hooks (`clified.hooks`)

Reference directly in YAML:

| Hook | Purpose |
|------|---------|
| `clified.hooks:pip_check` | Validate critical imports after install |
| `clified.hooks:register_mcp` | Register MCP server in Cursor |
| `clified.hooks:register_mcp_serve` | MCP with `mcp serve` args (denv pattern) |
| `clified.hooks:register_cursor_skill` | Copy skill to `.cursor/skills/` |
| `clified.hooks.pytorch:install_nvdiffrast` | PyTorch nvdiffrast extra (GameDev) |

### MCP in Cursor

```yaml
tools:
  denv:
    kind: python
    cli_name: denv
    post_install: clified.hooks:register_mcp_serve
```

Optional variables:

- `CLIFIED_MCP_NAME` — server name (default: `cli_name`)
- `CLIFIED_MCP_ARGS` — extra space-separated args

### Cursor skill (pc)

```yaml
post_install: clified.hooks:register_cursor_skill
```

Copies the project skill (see `clified.hooks.skills`).

## Local hooks (`clified_install.py`)

For **repository-specific** logic, add an importable module at the repo root:

```python
# clified_install.py
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from clified.installer.python_installer import PythonProjectInstaller


def post_install(installer: PythonProjectInstaller) -> bool:
    """Runs after the default install."""
    # installer.project_root, installer.venv_python, installer.bin_dir, ...
    return True
```

```yaml
post_install: clified_install:post_install
```

Clified inserts `project_root` on `sys.path` before import — so root-level `clified_install` works.

### Real examples

| Project | Hook | What it does |
|---------|------|--------------|
| **denv** | `clified_install:post_install` | `pip install mcp` + register `denv mcp serve` |
| **pc** | `custom_install` + `post_install` | Requirements, local `.pth`, `pc-cli` skill |
| **ai2print** | `clified_install:post_install` | Python venv + wrapper with `STL_REPAIR_ROOT` |
| **GameDev** | `gamedev_shared.installer.clified_hooks:*` | PyTorch, nvdiffrast, text3d, etc. |

## `custom_install` (Python)

Fully replaces the `pip install -e` / `requirements.txt` phase:

```yaml
custom_install: clified_install:custom_install
```

```python
def custom_install(installer: PythonProjectInstaller) -> bool:
    subprocess.run(
        [str(installer.venv_python), "-m", "pip", "install", "-r", "requirements.txt"],
        check=True,
        cwd=installer.project_root,
    )
    return True  # False aborts installation
```

## Hook function contract

```python
def my_hook(installer) -> bool | None:
    ...
```

| Return | Meaning |
|--------|---------|
| `True` or `None` | Success |
| `False` | Failure — installation aborted |

Useful installer attributes:

**Python:** `project_root`, `venv_python`, `venv_dir`, `bin_dir`, `cli_name`, `python_cmd`, `logger`

**Rust:** `project_root`, `bin_dir`, `cli_name`, `release_binary`, `cargo_bin_name`, `is_windows`, `logger`

## Execution order (Python)

```
check_python → system_deps → ensure_project_venv
  → custom_install OR install_in_venv
  → create_cli_wrappers
  → post_install
  → create_activate_wrapper → check_path
```

## Execution order (Rust)

```
install_binary → check_path → test_installation
  → post_install (if defined)
```

## Debugging

```bash
CLIFIED_RETRY=1 clified-install my-tool --verbose
```

Hook errors appear as `Hook failed (module:func): ...` in Rich output.
