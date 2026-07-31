# `tools.yaml` reference

The `tools.yaml` file is the contract between your repository and Clified. Copy `tools.yaml.example` and adapt it.

## Minimal structure

```yaml
workspace:
  root: .
  name: "MyProject"

tools:
  my-tool:
    name: "My Tool"
    kind: python          # python | rust | bun
    folder: .
    cli_name: my-tool
    description: "Short description for clified-install --list"
```

## `workspace` section

| Field | Type | Description |
|-------|------|-------------|
| `root` | string | Path relative to the **`tools.yaml` file**. Use `.` when YAML is at repo root |
| `name` | string | Display name in `clified-install --list` |
| `shared_python` | object | Shared Python package across tools (monorepos) |

### `shared_python` (optional)

```yaml
workspace:
  root: .
  name: "AiGameKit"
  shared_python:
    path: Shared
    import_name: aigamekit_shared
    src_subpath: src
```

Installs `Shared` in editable mode in Python venvs and exposes shared imports.

## Common fields (`tools.*`)

| Field | Types | Description |
|-------|-------|-------------|
| `name` | string | Human-readable name |
| `kind` | `python` \| `rust` \| `bun` | Installer used |
| `folder` | string | Path relative to `workspace.root` |
| `cli_name` | string | Command name in `~/.local/bin` |
| `description` | string | Listing text |
| `extra_aliases` | list[string] | Extra wrappers (e.g. `stl-repair-gui`) |
| `install_order` | int | Order in `clified-install all` (lower = first) |
| `install_before` | list[string] | Install other tools before this one |
| `install_before_mode` | `""` \| `venv_only` | Only prepare cross_deps/.pth without installing the tool |
| `post_install` | string | Hook `module:function(installer)` |
| `custom_install` | string | Hook that **replaces** default pip install (Python) |

## Python (`kind: python`)

| Field | Default | Description |
|-------|---------|-------------|
| `python_module` | ≈ `cli_name` | Module for `python -m` in wrapper |
| `min_python` | `[3, 10]` | Minimum version `[major, minor]` |
| `max_python` | — | Optional maximum version |
| `needs_pytorch` | `false` | Install PyTorch/CUDA via Clified logic |
| `cross_deps` | — | Other tools whose `src/` is linked via `.pth` |
| `local_packages` | — | Extra local packages (path + import_name) |

### Python project detection

Clified considers a project valid if it has:

- `pyproject.toml` or `setup.py`, or
- `requirements.txt`, or
- a directory named like `python_module`

### Example — simple Python CLI

```yaml
tools:
  denv:
    name: "DENV"
    kind: python
    folder: .
    cli_name: denv
    python_module: denv
    min_python: [3, 12]
    post_install: clified_install:post_install
```

### Example — monorepo with cross-deps

```yaml
tools:
  text3d:
    kind: python
    folder: Text3D
    cli_name: text3d
    python_module: text3d
    min_python: [3, 13]
    needs_pytorch: true
    install_before: [text2d]
    cross_deps: [text2d]
    post_install: aigamekit_shared.installer.clified_hooks:text3d_post_install
```

## Rust (`kind: rust`)

| Field | Description |
|-------|-------------|
| `cargo_bin_name` | Binary name in `target/release/` (default: `cli_name`) |

```yaml
tools:
  materialize:
    name: "Materialize"
    kind: rust
    folder: Materialize
    cli_name: materialize
    cargo_bin_name: materialize
    description: "Rust CLI — PBR maps"
```

### Rust + Python (ai2print)

Hybrid tools use a local `post_install` hook for Python venv and env-var wrappers:

```yaml
tools:
  ai2print:
    kind: rust
    folder: .
    cli_name: ai2print
    cargo_bin_name: stl-repair-gui
    post_install: clified_install:post_install
```

## Bun (`kind: bun`)

| Field | Default | Description |
|-------|---------|-------------|
| `bun_cli_script` | — | Script invoked by the wrapper |
| `bun_build_command` | `build` | `bun run` command before wrapper |
| `bun_install_args` | `["install", "--frozen-lockfile"]` | Args for `bun install` |

## Hooks — syntax

```yaml
post_install: clified.hooks:register_mcp_serve
post_install: clified_install:post_install
post_install: mypackage.hooks:setup
```

Format: `python_module:function`

- The module is imported with `project_root` (and `shared_python.src`) on `sys.path`
- The function receives the installer (`PythonProjectInstaller` or `RustProjectInstaller`)
- Return `True`/`None` for success or `False` for failure

See [Hooks](hooks.md).

## Full examples in the repository

| File | Origin |
|------|--------|
| `bundled/examples/tools.denv.yaml.example` | denv |
| `bundled/examples/tools.pc.yaml.example` | pc |
| `bundled/examples/tools.aigamekit.yaml.example` | AiGameKit monorepo |

## CLI — using the registry

```bash
export CLIFIED_TOOLS=/path/to/tools.yaml
clified-install --list
clified-install my-tool
clified-install my-tool --action uninstall
clified-install all --force
```

Useful flags: `--prefix`, `--python`, `--skip-deps`, `--force`, `--json`, `--quiet`.

See also: [Install pipeline](install-pipeline.md) · [Package manager](package-manager.md)
