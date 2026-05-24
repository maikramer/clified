# Migrating a project to Clified

Guide for adopting Clified in a repository that today uses `setup.sh`, Makefiles, or ad-hoc installers.

## Checklist

- [ ] Create `tools.yaml` + `tools.yaml.example`
- [ ] Add `install.sh`, `install.ps1`, `scripts/install-bootstrap.sh`
- [ ] (Optional) `installer/installer.py` → `bootstrap.run` bridge
- [ ] (Optional) `clified_install.py` for post-install logic
- [ ] Update project README
- [ ] Remove duplicate legacy installers

## 1. Define the registry

At the **repo root** (or agreed folder):

```yaml
# tools.yaml
workspace:
  root: .
  name: "MyProject"

tools:
  my-cli:
    name: "My CLI"
    kind: python
    folder: .
    cli_name: my-cli
    python_module: my_cli
    min_python: [3, 10]
    description: "Short description"
```

Version `tools.yaml.example` identically or with placeholders. Add `tools.yaml` to `.gitignore` **only** if it contains sensitive local paths — in most cases commit it directly.

## 2. `install.sh`

Copy from a migrated project or Clified:

```bash
#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export CLIFIED_TOOLS="${CLIFIED_TOOLS:-$SCRIPT_DIR/tools.yaml}"

if [[ ! -f "$CLIFIED_TOOLS" && -f "$SCRIPT_DIR/tools.yaml.example" ]]; then
  cp "$SCRIPT_DIR/tools.yaml.example" "$CLIFIED_TOOLS"
fi

source "$SCRIPT_DIR/scripts/install-bootstrap.sh"
clified_bootstrap my-cli "$@"
```

Also copy `clified/scripts/install-bootstrap.sh` → `scripts/install-bootstrap.sh`.

## 3. Python bridge (optional)

For `python installer/installer.py`:

```python
#!/usr/bin/env python3
import os, sys
from pathlib import Path

def main() -> int:
    repo = Path(__file__).resolve().parents[1]
    os.environ.setdefault("CLIFIED_TOOLS", str(repo / "tools.yaml"))
    from clified.installer.bootstrap import run
    return run(["my-cli", *sys.argv[1:]], cwd=str(repo))

if __name__ == "__main__":
    sys.exit(main())
```

## 4. Move legacy logic into hooks

| Before (legacy install.sh) | After |
|----------------------------|-------|
| `pip install mcp` + Cursor config | `post_install: clified.hooks:register_mcp_serve` |
| Custom requirements install | `custom_install` or Clified default |
| Copy skill | `clified.hooks:register_cursor_skill` |
| Rust build + Python venv | `kind: rust` + local `post_install` |

### ai2print example (Rust + Python)

Clified's Rust installer **does not** create a Python venv. The local hook:

1. Creates `.venv` + `pip install -r python/requirements.txt`
2. Generates a shell wrapper with `STL_REPAIR_ROOT` and `STL_REPAIR_PYTHON`

## 5. Remove legacy code

After validating `./install.sh` and the global command:

- Redirect `setup.sh` → `./install.sh`
- Keep `run.sh` only as a **development** shortcut in the repo
- Delete monolithic duplicate Python installers

## 6. Validate

```bash
./install.sh --list
./install.sh
which my-cli
my-cli --help
./install.sh --action reinstall --force
./install.sh --action uninstall
```

## Reference by project

| Project | `kind` | Local hook | Notes |
|---------|--------|------------|-------|
| denv | python | MCP | `folder: .` |
| pc | python | custom + skill | `folder: tools` |
| GameDev | mixed | `gamedev_shared.installer.clified_hooks` | monorepo, `shared_python` |
| ai2print | rust | venv + env wrapper | GTK/Python hybrid |

YAML examples live in Clified `examples/`.

## Monorepo with multiple tools

Single root `tools.yaml`; each tool with a different `folder:`:

```yaml
tools:
  text2d:
    folder: Text2D
    kind: python
    ...
  materialize:
    folder: Materialize
    kind: rust
    ...
```

Subproject scripts can delegate:

```python
# Materialize/installer/installer.py
subprocess.call([str(monorepo / "install.sh"), "materialize", "--action", action])
```

## Programmatic bridge (GameDev)

```python
from gamedev_shared.installer.unified import install_tool, main
install_tool("text2d", force=True)
# or CLI: gamedev-install text2d
```

Installs `clified` via pip automatically if import fails.
