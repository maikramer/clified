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
clified-install denv --action reinstall --force
clified-install all                 # all tools (respects install_order)
```

## Projects using Clified

| CLI | Repository | Type |
|-----|------------|------|
| **denv** | LocatelliDockerManager | Python |
| **pc** | ProjetoCursor | Python |
| **text2d**, **materialize**, … | GameDev | Python / Rust / Bun |
| **ai2print** | ai2print | Rust + Python (hook) |

## License

MIT — see [LICENSE](LICENSE).
