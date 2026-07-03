# Clified documentation

Guides for **using** and **understanding** Clified — the universal installer and
package manager for Python, Rust, and Bun tools.

## Start here

| Guide | Audience | Content |
|-------|----------|---------|
| [Getting started](getting-started.md) | End users | Install Clified, run `install.sh`, first tool |
| [Concepts](concepts.md) | Everyone | **Motor, registry, catalog, state** — how the pieces fit |
| [Architecture](architecture.md) | Contributors | High-level diagram, path resolution, installer types |

## Mechanisms (deep dives)

These explain **what happens under the hood** — useful when debugging, extending
a monorepo, or integrating Clified into your workflow.

| Guide | Content |
|-------|---------|
| [Install pipeline](install-pipeline.md) | From CLI to receipt: registry → installer → wrappers → hooks |
| [Remote catalog](catalog.md) | `registry.yaml`, cache, `--get`, cloning, version pinning |
| [Package manager](package-manager.md) | `state.json`, receipts, `list` / `update` / `uninstall` / `search` |
| [Doctor](doctor.md) | Diagnostics, broken receipts, orphan wrappers, `--fix` |
| [`tools.yaml` reference](tools-yaml.md) | Full field reference for the project registry |
| [Hooks](hooks.md) | `post_install`, `custom_install`, built-in hooks |

## Project adoption

| Guide | Content |
|-------|---------|
| [Migrating a project](migrating-a-project.md) | denv, pc, GameDev, ai2print patterns |
| [Troubleshooting](troubleshooting.md) | PEP 668, PATH, MCP, common errors |

## For developers

| Guide | Content |
|-------|---------|
| [CLI library](library.md) | OutputFormatter, retry, patterns, Click scaffold |
| [Development](development.md) | Tests, layout, PyPI release |

## CLI entry points

| Command | Role |
|---------|------|
| `clified` | **Package manager** (0.8+): `list`, `get`, `update`, `uninstall`, `search`, `doctor` |
| `clified-install` | **Legacy installer** + back-compat: `tool`, `--get`, `--catalog`, `all` |
| `python -m clified` | Same as `clified` |

Both entry points share the same engine (`clified.installer.*`). See
[Concepts](concepts.md) for when to use which.

## On-disk layout (user machine)

```
~/.config/clified/          # CLIFIED_HOME (or XDG_CONFIG_HOME/clified)
├── state.json              # installed tools (receipts)
├── catalog.cache.yaml      # cached remote registry.yaml
├── tools.yaml              # optional global registry
└── sources/                # git clones from --get / clified get
    └── denv/               # one directory per catalog entry name

~/.local/bin/               # INSTALL_PREFIX/bin (default)
├── denv                    # wrapper (bash) or denv.cmd (Windows)
└── text2d.cmd

~/project/.venv/            # per-tool Python venv (inside project tree)
```

Override paths with `CLIFIED_HOME`, `CLIFIED_SOURCES`, `INSTALL_PREFIX`.
