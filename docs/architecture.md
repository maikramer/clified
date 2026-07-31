# Architecture

> **Deep dives:** [Concepts](concepts.md) · [Install pipeline](install-pipeline.md) ·
> [Remote catalog](catalog.md) · [Package manager](package-manager.md) ·
> [Doctor](doctor.md) · [Full doc index](README.md)

## Overview

```
┌─────────────────────────────────────────────────────────────────┐
│  PROJECT REPOSITORY (git clone)                                 │
│  ├── tools.yaml          ← catalog: what, where, hooks          │
│  ├── install.sh          ← pip bootstrap + clified-install      │
│  ├── clified_install.py  ← local hooks (optional)               │
│  └── src/ / Cargo.toml / package.json  ← tool source code       │
└───────────────────────────────┬─────────────────────────────────┘
                                │
                    pip install clified (PyPI)
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│  CLIFIED (generic engine)                                       │
│  clified-install / python -m clified                            │
│  ├── registry.py     reads tools.yaml                           │
│  ├── python_installer  venv + pip + wrappers                    │
│  ├── rust_installer    cargo build + binary                     │
│  ├── bun_installer     bun install + build                      │
│  └── unified.py        CLI, hooks, install all                  │
└───────────────────────────────┬─────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│  RESULT ON THE USER MACHINE                                     │
│  ~/.local/bin/my-cli     ← wrapper or binary                    │
│  ~/project/.venv/        ← isolated Python deps (kind: python)  │
│  ~/.config/clified/state.json  ← install receipts (0.8+)        │
└─────────────────────────────────────────────────────────────────┘
```

## Not chicken-and-egg

| Question | Answer |
|----------|--------|
| Do I need to clone Clified? | **No** — it comes from PyPI |
| What do I clone? | The **tool** repository (denv, pc, AiGameKit, ai2print) |
| What installs Clified? | `pip` (automatic in `install.sh`) |
| What installs the tool? | `clified-install` reading the repo `tools.yaml` |

## Path resolution

Order for finding `tools.yaml`:

1. `CLIFIED_TOOLS` (set by the project `install.sh`)
2. `~/.config/clified/tools.yaml` (user global config)
3. `tools.yaml` at the root of a Clified checkout (dev)

`workspace.root` in the YAML is **relative to the `tools.yaml` file**, not the cwd:

```yaml
workspace:
  root: .          # root = directory containing tools.yaml
  name: "MyProject"
```

Tool folders (`folder:`) are relative to `workspace.root`.

## Installer types

### Python (`kind: python`)

1. Check Python version (`min_python` / `max_python`)
2. Install system deps (if configured)
3. Create `project_root/.venv` via `uv` or `python -m venv`
4. `pip install -e .` or `requirements.txt` (or `custom_install`)
5. Link local packages / `cross_deps` via `.pth` files
6. Generate shell/cmd wrappers in `INSTALL_PREFIX/bin`
7. Run `post_install` hooks

### Rust (`kind: rust`)

1. `cargo build --release` (if binary missing)
2. Copy `target/release/<cargo_bin_name>` → `~/.local/bin/<cli_name>`
3. `post_install` hooks (since v0.4.1)

### Bun (`kind: bun`)

1. `bun install` in the project
2. Optional build (`bun_build_command`)
3. Wrapper pointing at CLI script (`bun_cli_script`)

## Bootstrap (`scripts/install-bootstrap.sh`)

Shared across migrated projects. Handles common issues:

- **`python3` on PATH points at a venv without pip** → tries `python3.14`, `python3.12`, …
- **PEP 668** → retry with `--break-system-packages`
- **`clified-install` missing after pip** → prepends `~/.local/bin` to PATH

Python equivalent: `clified.installer.bootstrap` (selecção de Python + pip install).

## Bundled data (PyPI wheel)

On PyPI installs, bundled resources live under `clified/bundled/`:

- `examples/` — reference YAML (denv, pc, AiGameKit)
- `config/` — constraints, config samples

Local dev: `CLIFIED_ROOT` points at a checkout; paths resolved by `clified.paths`.

## What stays in the project vs Clified

| Responsibility | Location |
|----------------|----------|
| Business logic (Docker, ML, GTK) | Tool repository |
| Registry and install order | Repo `tools.yaml` |
| Generic MCP, skills, PyTorch extras | `clified.hooks` |
| Project-specific post-install | Repo `clified_install.py` |
| venv / wrapper / build engine | Clified (PyPI) |
| Installed-tool metadata (0.8+) | `~/.config/clified/state.json` |

## Package manager layer (0.8+)

Catalog installs (`--get`) write an **InstallReceipt** per tool. The `clified`
entry point exposes `list`, `update`, `uninstall`, `search`, and `doctor` on
top of this state — see [Package manager](package-manager.md).

Legacy `clified-install` and positional `clified <tool>` remain supported.
