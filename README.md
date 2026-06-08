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

Each project ships its own `install.sh`, sets `CLIFIED_TOOLS` to the local `tools.yaml`, and installs Clified via pip on first run. **You do not need to clone the Clified repository.**

## Quick start

```bash
pip install --user clified
# or: pipx install clified

git clone https://github.com/your-org/my-cli.git
cd my-cli
./install.sh
my-cli --help
```

## Documentation

| Guide | Contents |
|-------|----------|
| [Getting started](docs/getting-started.md) | Installation, clean-machine flow, `install.sh` |
| [Architecture](docs/architecture.md) | Engine, YAML, venvs, and wrappers |
| [`tools.yaml` reference](docs/tools-yaml.md) | Fields, Python/Rust/Bun types, examples |
| [Hooks](docs/hooks.md) | `post_install`, built-in hooks, local hooks |
| [Migrating a project](docs/migrating-a-project.md) | denv / pc / GameDev / ai2print walkthrough |
| [CLI library](docs/library.md) | OutputFormatter, retry, patterns, Click |
| [Troubleshooting](docs/troubleshooting.md) | PEP 668, wrong Python on PATH, MCP |
| [Development](docs/development.md) | Tests, PyPI release, contributing |

## Main commands

```bash
clified-install --list              # tools in the active tools.yaml
clified-install denv                # install one tool
clified-install denv --action update # refresh deps reusing the existing venv
clified-install denv --action reinstall --force
clified-install all                 # all tools (respects install_order)
clified-install --doctor            # health report for every tool
clified-install --doctor --fix      # + remove CLI wrappers shadowed on PATH
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
| **pc** | ProjetoCursor | Python |
| **text2d**, **materialize**, … | GameDev | Python / Rust / Bun |
| **ai2print** | ai2print | Rust + Python (hook) |

## License

MIT — see [LICENSE](LICENSE).
