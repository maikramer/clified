# Doctor

`clified doctor` checks the health of installed tools and the local Clified
state. It combines **per-tool diagnostics** (from the active `tools.yaml`) with
**state-file checks** (broken receipts, orphan wrappers).

```bash
clified doctor
clified doctor --tool text2d
clified doctor --fix
clified doctor --fix --yes          # skip confirmation
clified doctor --json
```

## What doctor checks

### 1. Broken receipts

A receipt in `state.json` is **broken** when critical paths no longer exist:

- `project_root` directory missing
- `venv_path` missing (Python tools)
- All paths in `artifacts` missing

Common causes: manual deletion of `.venv`, moved clone, incomplete uninstall.

### 2. Orphan wrappers

Wrappers in `INSTALL_PREFIX/bin` that reference a non-existent venv.

**Safety:** Only files containing the marker `gerado por clified` are
considered — user scripts in the same directory are never touched.

Detection scans wrapper content for `.venv` paths and checks whether those
paths still exist.

### 3. Per-tool diagnostics

When a `tools.yaml` is active (via `CLIFIED_TOOLS` or restored from a
receipt), `diagnose_tool()` runs for each matching tool:

| Check | Severity | Example |
|-------|----------|---------|
| Project directory exists | FAIL | Folder deleted |
| Venv exists | FAIL | `.venv` removed |
| Wrapper in `bin_dir` | FAIL | Not on PATH |
| Python version in bounds | WARN | 3.13 venv but max_python 3.12 |
| Shadow on PATH | WARN | Another `denv` earlier in PATH |
| Import smoke test | FAIL/WARN | `python -c "import module"` |

Status levels: `OK`, `WARN`, `FAIL`. Overall health is the worst status.

### Tool filter

`--tool NAME` filters diagnostics. Matching is **case-insensitive** and
ignores `-` and `_`:

- `--tool DENV` matches key `denv`
- `--tool my-tool` matches `mytool`

Use `--tool all` or omit for all tools in the active registry.

## Output modes

### Human (default)

Rich-formatted tables and coloured messages via `Logger`.

### JSON (`--json`)

Structured payload:

```json
{
  "status": "success",
  "title": "doctor",
  "data": {
    "healthy": false,
    "broken_receipts": [{"name": "text2d", "reason": "…"}],
    "orphan_wrappers": ["/home/user/.local/bin/old-tool"],
    "tools": [{"key": "text2d", "status": "fail", "checks": […]}],
    "installed_count": 5
  }
}
```

With `--fix`, successful removals appear in `actions`:

```json
"actions": [
  {"type": "remove_receipt", "name": "text2d"},
  {"type": "remove_wrapper", "path": "/home/user/.local/bin/old-tool.cmd"}
]
```

## `--fix` behaviour

`--fix` is **destructive** — it removes broken receipts and orphan wrappers.

### Confirmation

| Context | Behaviour |
|---------|-----------|
| Interactive TTY, no `--yes` | Lists items and prompts `Continuar? [y/N]` |
| Non-TTY (pipe/CI) | Proceeds without prompt |
| `--yes` / `-y` | Skip prompt |

Cancelled fix leaves state unchanged.

### What `--fix` removes

- **Broken receipts** — `remove(name)` from state file
- **Orphan wrappers** — `unlink()` on Clified-marked scripts only

It does **not**:

- Reinstall tools
- Delete git clones (`--purge` is separate: `clified uninstall --purge`)
- Remove venv directories
- Touch non-Clified scripts

After fix, checks run again to report remaining issues.

## PATH shadow detection

`fix_shadows()` (optional, per-tool report) detects when another executable
with the same name appears **earlier** on `PATH` than the Clified wrapper.

Example: system `python` shadowing a venv wrapper, or an old manual install
of `denv` before `~/.local/bin`.

Reported as WARN with the shadowing path.

## Doctor without active `tools.yaml`

If no registry is loaded and there are no broken receipts or orphans:

```
Sem tools.yaml activo — apenas verificação de state.
```

If broken receipts or orphans exist, those are still reported and fixable.

For full per-tool checks on a catalog install, doctor can restore context from
receipts when invoked as part of managed workflows; standalone `clified doctor`
uses the current `CLIFIED_TOOLS` if set.

## Integration with `clified list`

`clified list` shows `ok` / `broken` using the same path checks as
`_broken_receipts()`. Doctor adds wrappers, PATH shadows, and import tests.

## When to use doctor

| Situation | Command |
|-----------|---------|
| After manual cleanup of `.venv` or clones | `clified doctor --fix` |
| Tool command not found but `list` shows installed | `clified doctor --tool NAME` |
| CI health check | `clified doctor --json` |
| Suspect old wrappers after reinstall | `clified doctor --fix --yes` |

## Related

- [Package manager](package-manager.md) — state file and receipts
- [Install pipeline](install-pipeline.md) — wrapper generation
- [Troubleshooting](troubleshooting.md) — common user-facing errors
