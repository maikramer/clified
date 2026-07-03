# Clified

Universal installer and CLI library for **Python**, **Rust**, and **Bun** tools.

Published on [PyPI](https://pypi.org/project/clified/) · [GitHub](https://github.com/maikramer/clified)

**Português:** [README_PT.md](README_PT.md)

## What it is

Clified splits two responsibilities:

| Piece | Where it lives | Role |
|-------|----------------|------|
| **Engine** | `clified` package (PyPI) | venvs, wrappers, Rust/Bun builds, hooks |
| **Registry** | `tools.yaml` in each repo | What to install, code location, post-steps |
| **Catalog** | `maikramer/clified-catalog` (live) + bundled fallback | Maps a short name (`denv`) → repo + tool, for `--get` |

Each project ships its own `install.sh`, sets `CLIFIED_TOOLS` to the local `tools.yaml`, and installs Clified via pip on first run. **You do not need to clone the Clified repository.** For known tools you can skip even the project clone — `clified-install --get <tool>` clones the repo from the catalog and installs the tool in one step.

## Quick start

### One-liner (no clone needed)

Install the engine and a known tool from the catalog in one shot:

```bash
# Linux / macOS — engine + tool from the catalog
curl -fsSL https://raw.githubusercontent.com/maikramer/clified/main/install.sh | bash -s -- --get denv
# Linux / macOS — engine only, then list remote tools
curl -fsSL https://raw.githubusercontent.com/maikramer/clified/main/install.sh | bash
# Windows (PowerShell)
irm https://raw.githubusercontent.com/maikramer/clified/main/install.ps1 | iex
# Windows + arguments
& ([scriptblock]::Create((irm https://raw.githubusercontent.com/maikramer/clified/main/install.ps1))) --get denv
```

With no arguments the one-liner installs the engine and prints next steps.
List known tools with `clified-install --catalog`, or point `--get` at any repo
with `--repo`:

```bash
clified-install --get mytool --repo https://github.com/your-org/your-cli.git
```

## Remote catalog (`--get` / `--catalog`)

The catalog maps a short name (`denv`, `cissapi`, `pc`, …) to a git repo + tool.
By default it's read live from [`maikramer/clified-catalog`](https://github.com/maikramer/clified-catalog)
(raw `registry.yaml`) with a local cache (`~/.config/clified/catalog.cache.yaml`,
TTL 1h) and falls back to the bundled snapshot when offline. **Adding a tool no
longer requires a Clified release** — just edit the catalog repo.

```bash
clified-install --catalog                 # list remote tools (private marked)
clified-install --refresh-catalog --catalog  # ignore cache, force fresh fetch
clified-install --get denv                # fetch + install from the catalog
```

| Env | Default | Effect |
|-----|---------|--------|
| `CLIFIED_CATALOG` | unset | Override the catalog source: URL (`http(s)://`) or local path. |
| `CLIFIED_CATALOG_TTL` | `3600` | Cache TTL in seconds. `0` = always fetch; `-1` = bundled only (offline). |

### Public vs private tools

Each entry has an optional `access: public|private` (default `public`).
`--catalog` marks private tools as `(privado)` and `--get <private>` warns
before cloning. Private repos (e.g. `LocatelliSupermercados/*`) clone with your
own git credentials (SSH key / HTTPS token via git credential manager). On
access denial Clified **fails gracefully** with a clear message — no raw git
crash.

### Publishing a tool

- **No catalog** — any public repo: `clified-install --get mytool --repo https://github.com/you/x.git`.
- **Public catalog** — open a PR to `maikramer/clified-catalog` with
  `access: public`.
- **Self-host** — keep your own `registry.yaml` (private repo or local file)
  and point Clified at it with `CLIFIED_CATALOG=<url-or-path>`.

### From a cloned project

```bash
git clone https://github.com/your-org/my-cli.git
cd my-cli
./install.sh
my-cli --help
```

## Documentation

Full index: **[docs/README.md](docs/README.md)**

| Guide | Contents |
|-------|----------|
| [Getting started](docs/getting-started.md) | Installation, clean-machine flow, `install.sh` |
| [Concepts](docs/concepts.md) | **Motor, registry, catalog, state** — how it fits together |
| [Architecture](docs/architecture.md) | High-level diagram, path resolution, installer types |
| [Install pipeline](docs/install-pipeline.md) | CLI → installer → wrappers → receipt (deep dive) |
| [Remote catalog](docs/catalog.md) | `registry.yaml`, cache, `--get`, version pinning |
| [Package manager](docs/package-manager.md) | `state.json`, receipts, list/update/uninstall |
| [Doctor](docs/doctor.md) | Diagnostics, `--fix`, orphan wrappers |
| [`tools.yaml` reference](docs/tools-yaml.md) | Fields, Python/Rust/Bun types, examples |
| [Hooks](docs/hooks.md) | `post_install`, built-in hooks, local hooks |
| [Migrating a project](docs/migrating-a-project.md) | denv / pc / GameDev / ai2print walkthrough |
| [CLI library](docs/library.md) | OutputFormatter, retry, patterns, Click |
| [Troubleshooting](docs/troubleshooting.md) | PEP 668, wrong Python on PATH, MCP |
| [Development](docs/development.md) | Tests, PyPI release, contributing |

## Managing installed tools (`clified` 0.8+)

After installing with `--get` or from a clone, Clified records each tool in
`~/.config/clified/state.json`. Use the **`clified`** entry point (not
`clified-install`) for day-to-day package management:

```bash
clified list                         # installed tools (ok / broken)
clified list --json
clified search game                  # search remote catalog
clified get text2d                   # fetch + install from catalog
clified get text2d@v1.2.0            # pin branch/tag/commit
clified update text2d                # git pull + refresh deps
clified update --all                 # update everything installed
clified uninstall text2d --purge     # remove tool + clone in sources/
clified doctor --fix                 # broken receipts + orphan wrappers
```

`clified-install` and legacy invocations (`clified text2d`, `clified --get denv`)
remain fully supported.

## Main commands

```bash
clified-install --list              # tools in the active tools.yaml
clified-install denv                # install one tool
clified-install denv --action update # refresh deps reusing the existing venv
clified-install denv --action reinstall --force
clified-install all                 # all tools (respects install_order)
clified-install --doctor            # health report for every tool
clified-install --doctor --fix      # + remove CLI wrappers shadowed on PATH
clified-install --catalog           # list remote tools known to the catalog
clified-install --refresh-catalog --catalog  # force fresh catalog fetch
clified-install --get denv          # fetch + install a remote tool (catalog)
clified-install --get mytool --repo https://github.com/your-org/your-cli.git
clified-install denv --retry 3      # retry transient failures up to 3 attempts
```

## Diagnostics (`--doctor`)

`clified-install --doctor` reports, per tool, whether the venv exists and runs
a **supported** Python, whether the CLI wrapper is installed and actually wins
on `PATH`, and which build backends (uv/cargo/bun/git) are present. Add `--fix`
to delete stale wrappers that shadow the canonical one, or `--json` for
machine-readable output. Pass a tool name to scope it to one tool.

### Python version selection

Clified honours each tool's `requires-python` (read from its `pyproject.toml`)
in addition to `min_python` in `tools.yaml`: it keeps the tighter floor and the
lower ceiling, so a tool capped at `<3.14` never lands on a newer interpreter
than it supports — uv provisions the right version automatically.

### Monorepo `file:` dependencies

A relative `file:` dependency (e.g. `gamedev-shared @ file:../Shared`) is
invalid PEP 508 and breaks uv's editable build. Clified absolutises such URLs
for the duration of the build and restores `pyproject.toml` afterwards, so
shared-package monorepos install cleanly without per-tool workarounds.

## Projects using Clified

| CLI | Repository | Type |
|-----|------------|------|
| **denv** | LocatelliDockerManager | Python |
| **cissapi** | LocatelliCissApi | Python |
| **pc** | ProjetoCursor | Python |
| **text2d**, **materialize**, … | GameDev | Python / Rust / Bun |
| **ai2print** | ai2print | Rust + Python (hook) |

## License

MIT — see [LICENSE](LICENSE).
