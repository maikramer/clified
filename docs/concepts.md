# Core concepts

Clified separates **what to install** (project data) from **how to install**
(generic engine). Understanding these four layers avoids confusion between
`tools.yaml`, the remote catalog, and the local state file.

## The four layers

```
┌──────────────────────────────────────────────────────────────────────┐
│  1. MOTOR (PyPI package `clified`)                                   │
│     venvs, pip/uv, cargo, bun, wrappers, hooks, retry, doctor        │
│     Entry points: clified, clified-install, python -m clified       │
└───────────────────────────────┬──────────────────────────────────────┘
                                │ reads
                                ▼
┌──────────────────────────────────────────────────────────────────────┐
│  2. REGISTRY (`tools.yaml` in a git repo)                            │
│     Which tools exist, folder, kind (python/rust/bun), hooks, order  │
│     Activated by CLIFIED_TOOLS or set automatically after --get      │
└───────────────────────────────┬──────────────────────────────────────┘
                                │ optional lookup
                                ▼
┌──────────────────────────────────────────────────────────────────────┐
│  3. CATALOG (`registry.yaml` — live repo + bundled snapshot)         │
│     Short name (denv) → git URL + tool key in that repo's tools.yaml │
│     Used by: clified get, clified-install --get, install.sh --get     │
└───────────────────────────────┬──────────────────────────────────────┘
                                │ records result
                                ▼
┌──────────────────────────────────────────────────────────────────────┐
│  4. STATE (`~/.config/clified/state.json`)                          │
│     InstallReceipt per tool: paths, commit, source, artifacts        │
│     Used by: clified list, update, uninstall, doctor                 │
└──────────────────────────────────────────────────────────────────────┘
```

| Layer | Lives in | Changes when |
|-------|----------|--------------|
| Motor | PyPI / pip | You upgrade `clified` |
| Registry | Tool repository | Tool authors edit `tools.yaml` |
| Catalog | `maikramer/clified-catalog` (+ bundled fallback) | New PR to catalog repo — **no Clified release needed** |
| State | User machine | Every install/update/uninstall |

## Two common workflows

### A. Clone a project (classic)

The user clones a repository that ships its own `tools.yaml` and `install.sh`.

```
git clone org/my-project
cd my-project
./install.sh
```

1. `install.sh` sets `CLIFIED_TOOLS=./tools.yaml`
2. Bootstrap ensures `clified` is installed via pip
3. `clified-install my-tool` reads the local registry and installs

The state file records the installation, but the **source of truth for tool
definitions** remains the repo's `tools.yaml`.

### B. One-liner / catalog (`--get`)

The user never clones manually — Clified fetches from the catalog.

```
curl -fsSL .../install.sh | bash -s -- --get denv
# or
clified get denv
```

1. Load catalog → resolve `denv` → `RepoSpec(repo=…, tool=…)`
2. Clone to `~/.config/clified/sources/denv`
3. Set `CLIFIED_TOOLS` and `CLIFIED_ROOT` to the clone
4. Install the tool from the cloned repo's `tools.yaml`
5. Write receipt to `state.json` with `source: catalog`

See [Remote catalog](catalog.md) and [Package manager](package-manager.md).

## Path resolution

### Finding `tools.yaml`

Order (first match wins):

1. `CLIFIED_TOOLS` — explicit path (set by `install.sh` or after `--get`)
2. `~/.config/clified/tools.yaml` — user global registry
3. `tools.yaml` at Clified checkout root (development)

Implementation: `clified.paths.tools_yaml_path()`.

### Resolving project paths inside YAML

`workspace.root` is **relative to the `tools.yaml` file**, not the current
working directory:

```yaml
workspace:
  root: .          # directory containing tools.yaml
  name: "MyProject"

tools:
  text2d:
    folder: Text2D   # → workspace.root / Text2D
```

If `tools.yaml` lives in a subfolder (e.g. `cli/tools.yaml`), set
`workspace.root: ..` and `folder` relative to that root.

### User config home

`~/.config/clified` (or `CLIFIED_HOME`, or `$XDG_CONFIG_HOME/clified`):

| File / dir | Purpose |
|------------|---------|
| `state.json` | Installed tool receipts |
| `catalog.cache.yaml` | Cached remote `registry.yaml` |
| `tools.yaml` | Optional personal registry |
| `sources/` | Git clones from catalog installs |

## Install prefix and wrappers

By default, CLI wrappers land in `~/.local/bin` (`INSTALL_PREFIX`).

- **Python**: shell script (Unix) or `.cmd` (Windows) that invokes
  `project/.venv/bin/python -m <module> "$@"`
- **Rust**: copy of `target/release/<binary>`
- **Bun**: wrapper pointing at `bun run <script>`

Wrappers contain the marker `gerado por clified` — used by `doctor` to
distinguish Clified-generated scripts from user files. See
[Install pipeline](install-pipeline.md).

## CLI duality: `clified` vs `clified-install`

Since **0.8.0**, Clified exposes two entry points that share the same engine:

| | `clified` | `clified-install` |
|---|-----------|-------------------|
| Style | Subcommands (`clified list`) | Positional / flags (`clified-install denv`) |
| Focus | Day-to-day package management | Project `install.sh` scripts, legacy |
| State-aware | Yes (`list`, `update`, `uninstall`) | Partial (records receipts on `--get`) |

**Back-compat:** `clified denv`, `clified --get denv`, and `clified --list`
delegate to `clified-install` / `unified.main`.

Prefer **`clified`** for catalog installs and managing what is already on disk.
Prefer **`clified-install`** inside project `install.sh` when `CLIFIED_TOOLS`
points at a local `tools.yaml`.

## Actions: install, update, reinstall, uninstall

| Action | Effect |
|--------|--------|
| `install` | Create venv/build, wrappers, hooks; write/update receipt |
| `update` | Refresh deps/build without recreating venv (`UV_VENV_CLEAR=0`) |
| `reinstall` | Force full reinstall (venv clear if configured) |
| `uninstall` | Remove wrappers; optionally remove receipt and clone (`--purge`) |

`clified update` additionally runs `git pull` on catalog clones before
re-running the installer. See [Package manager](package-manager.md).

## Error handling and retry

Transient failures (network, pip timeouts) can be retried:

```bash
CLIFIED_RETRY=1 clified-install my-tool
clified install my-tool --retry 3
```

Permanent failures (missing directory, `FileNotFoundError`, invalid
`tools.yaml`) are **not** retried. A installer returning `False` is always
treated as failure — never recorded as a successful install.

Pattern-based hints (`ModuleNotFoundError`, git auth) come from
`clified.patterns`. See [CLI library](library.md).

## What belongs where

| Responsibility | Location |
|----------------|----------|
| Business logic (Docker, ML, GTK) | Tool repository |
| Tool list, order, hooks | Repo `tools.yaml` |
| Short name → repo mapping | Catalog `registry.yaml` |
| Installed-tool metadata | User `state.json` |
| Generic MCP, skills, PyTorch | `clified.hooks` |
| venv / wrapper / build engine | Clified (PyPI) |

## Next steps

- [Install pipeline](install-pipeline.md) — step-by-step install mechanics
- [Remote catalog](catalog.md) — `--get`, cache, pinning
- [Package manager](package-manager.md) — receipts and subcommands
- [`tools.yaml` reference](tools-yaml.md) — register your tool
