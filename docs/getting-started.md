# Getting started

## Prerequisites

| Component | Required for |
|-----------|--------------|
| **Python 3.10+** with **pip** | Installing Clified and Python projects |
| **`~/.local/bin` on PATH** | `clified-install`, `denv`, `pc`, etc. |
| **Rust / cargo** | `kind: rust` tools |
| **Bun** | `kind: bun` tools |
| **`uv`** (optional) | Faster venv creation — bootstrapped when missing |

On Debian/Ubuntu, if system Python lacks pip:

```bash
sudo apt install python3-full python3-venv
# or use pipx:
pipx install clified
```

## Install Clified

```bash
pip install --user clified
# alternatives:
pipx install clified
pip install --user --break-system-packages clified   # PEP 668
```

Verify:

```bash
clified-install --help
# or
python3 -m clified --list   # requires CLIFIED_TOOLS pointing at a tools.yaml
```

## Install a tool (typical flow)

Each migrated repository includes:

```
my-project/
├── tools.yaml              # Clified registry
├── tools.yaml.example      # versioned template
├── install.sh              # entry point (Linux/macOS)
├── install.ps1             # entry point (Windows)
└── scripts/
    └── install-bootstrap.sh   # Python detection + pip install clified
```

### Step by step

```bash
git clone git@github.com:org/my-project.git
cd my-project
./install.sh
```

The `install.sh`:

1. Sets `CLIFIED_TOOLS` → `./tools.yaml`
2. If `clified-install` is missing → `pip install clified>=0.4.1`
3. Runs `clified-install <tool>`

### What happens under the hood

**Python projects** (denv, pc, text2d):

- Creates `Project/.venv`
- Installs dependencies (`pip install -e .` or `requirements.txt`)
- Generates a wrapper in `~/.local/bin/<cli-name>` pointing at the venv
- Runs `post_install` hooks (MCP, skills, etc.)

**Rust projects** (materialize, ai2print):

- `cargo build --release`
- Copies the binary to `~/.local/bin`
- `post_install` hooks (since 0.4.1) — e.g. ai2print sets up a Python venv

**Clified itself does not use a venv** — it runs like any pip CLI (`ruff`, `black`). Only installed tools are isolated in the project `.venv`.

## Useful environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `CLIFIED_TOOLS` | `~/.config/clified/tools.yaml` | **Path to the project registry** |
| `PYTHON_CMD` | auto-detected | Force interpreter (e.g. `/usr/bin/python3.12`) |
| `CLIFIED_MIN_VERSION` | `0.4.1` | Minimum version for bootstrap |
| `INSTALL_PREFIX` | `~/.local` | Where wrappers are installed |
| `UV_VENV_CLEAR` | — | GameDev: recreate venv |
| `UV_LINK_MODE` | — | GameDev: `copy` vs hardlink |

## Windows

```powershell
.\install.ps1
# or
.\install.ps1 --action reinstall
```

The PowerShell bootstrap follows the same logic: install `clified` via pip if needed, then `clified-install`.

## Next steps

- [Architecture](architecture.md) — engine vs registry
- [`tools.yaml` reference](tools-yaml.md) — register your tool
- [Migrating a project](migrating-a-project.md) — adopt Clified in an existing repo
