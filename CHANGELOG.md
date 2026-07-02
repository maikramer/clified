# Changelog

## 0.7.0 — 2026-07

Major overhaul: frictionless one-liner install, remote tool catalog, bootstrap
consolidation, and code-quality fixes across the installers.

### Install / one-liner
- `curl -fsSL .../install.sh | bash` and `irm .../install.ps1 | iex` now install
  the Clified engine and **delegate** the remaining args to `clified-install`
  (pipe-safe, dev-mode aware).
- `clified-install --get <tool>`: fetch + install a remote tool from the catalog
  (`bundled/registry.yaml`) in one step. `--repo <url>` overrides the source.
- `clified-install --catalog`: list remote tools known to the catalog.
- `install.bat` is now a thin wrapper around `install.ps1`.

### Bootstrap consolidation (Phase 2)
- Merged `python_select.py` into `installer/bootstrap.py` (single Python picker).
- Shared shell libraries `scripts/_bootstrap.sh` and `scripts/_bootstrap.ps1`;
  `install-bootstrap.{sh,ps1}` are now thin wrappers that source them.

### Code-quality (Phase 3)
- Single-source version: `__version__` in `clified/__init__.py` drives the
  hatchling build (`dynamic = ["version"]`); `paths.version()` reads it.
- Removed `src/clified/bundled/` ↔ root `config/`+`examples/` duplication; the
  wheel ships bundled resources from a single location.
- Consolidated CLI wrapper generation (`write_cli_wrapper`) across Python/Bun
  installers; fixed double-CR in Windows `.cmd` wrappers; standardized on
  `#!/usr/bin/env bash`.
- Shared `prepend_path_env` helper used by `check_path` and `bootstrap.run`.
- Logger no-Rich fallback now emits plain text instead of silently swallowing.
- Renamed `ConnectionError`/`TimeoutError` → `ClifiedConnectionError`/
  `ClifiedTimeoutError` (no longer shadow builtins).
- Moved `--text2d-venv-only` into `tools.yaml` as `install_before_mode: venv_only`.
- New `--retry N` CLI flag (default follows `CLIFIED_RETRY`; 1 = no retry).
- `main()` auto non-interactive when stdin isn't a TTY (pipe installs) and
  forces UTF-8 for child processes on Windows.
- Clarified docstrings of `clified.paths` vs `clified.core.paths`.

### Tests / CI (Phase 4)
- Unix-only tests skip on Windows (`skipif sys.platform == "win32"`).
- CI matrix now runs on `ubuntu-latest` **and** `windows-latest`; smoke step
  exercises `--catalog`.

## 0.6.1
- Internal installer refinements.
