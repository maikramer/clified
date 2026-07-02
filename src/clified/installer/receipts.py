"""Registo persistente de ferramentas instaladas via Clified."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from clified.core.state_store import StateStore, get_state_store
from clified.paths import clified_home, version

_NAMESPACE = "installed"


@dataclass
class InstallReceipt:
    """Receipt de uma instalação Clified."""

    kind: str
    cli_name: str
    source: str  # catalog | repo | local
    repo: str = ""
    ref: str = ""
    commit: str = ""
    tools_yaml: str = ""
    project_root: str = ""
    venv_path: str = ""
    catalog_name: str = ""
    install_prefix: str = ""
    repo_clone_path: str = ""
    artifacts: list[str] = field(default_factory=list)
    installed_at: str = ""
    updated_at: str = ""
    clified_version: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> InstallReceipt:
        return cls(
            kind=str(data.get("kind", "")),
            cli_name=str(data.get("cli_name", "")),
            source=str(data.get("source", "local")),
            repo=str(data.get("repo", "")),
            ref=str(data.get("ref", "")),
            commit=str(data.get("commit", "")),
            tools_yaml=str(data.get("tools_yaml", "")),
            project_root=str(data.get("project_root", "")),
            venv_path=str(data.get("venv_path", "")),
            catalog_name=str(data.get("catalog_name", "")),
            install_prefix=str(data.get("install_prefix", "")),
            repo_clone_path=str(data.get("repo_clone_path", "")),
            artifacts=list(data.get("artifacts") or []),
            installed_at=str(data.get("installed_at", "")),
            updated_at=str(data.get("updated_at", "")),
            clified_version=str(data.get("clified_version", "")),
        )


@dataclass
class InstallResult:
    """Resultado de uma acção install/update/uninstall."""

    tool: str
    action: str
    ok: bool
    duration_ms: float = 0.0
    artifacts: list[str] = field(default_factory=list)
    error: str = ""

    def __bool__(self) -> bool:
        return self.ok

    def to_dict(self) -> dict[str, Any]:
        return {
            "tool": self.tool,
            "action": self.action,
            "ok": self.ok,
            "duration_ms": round(self.duration_ms, 1),
            "artifacts": self.artifacts,
            "error": self.error,
        }


def state_path() -> Path:
    return clified_home() / "state.json"


def _store() -> StateStore:
    return get_state_store(state_path())


def reset_store() -> None:
    """Limpa singleton (tests)."""
    import clified.core.state_store as mod

    mod._store = None


def load_all() -> dict[str, InstallReceipt]:
    raw = _store().get_namespace(_NAMESPACE)
    return {k: InstallReceipt.from_dict(v) for k, v in raw.items() if isinstance(v, dict)}


def get(name: str) -> InstallReceipt | None:
    data = _store().get(_NAMESPACE, name.lower())
    if not isinstance(data, dict):
        return None
    return InstallReceipt.from_dict(data)


def record_install(name: str, receipt: InstallReceipt) -> None:
    key = name.lower().strip()
    now = datetime.now(tz=timezone.utc).isoformat()
    existing = _store().get(_NAMESPACE, key)
    if isinstance(existing, dict) and existing.get("installed_at"):
        receipt.installed_at = str(existing["installed_at"])
    else:
        receipt.installed_at = receipt.installed_at or now
    receipt.updated_at = now
    receipt.clified_version = version()
    _store().set(_NAMESPACE, key, receipt.to_dict())


def update_receipt(name: str, **fields: Any) -> None:
    key = name.lower().strip()
    data = _store().get(_NAMESPACE, key)
    if not isinstance(data, dict):
        return
    receipt = InstallReceipt.from_dict(data)
    for k, v in fields.items():
        if hasattr(receipt, k):
            setattr(receipt, k, v)
    record_install(key, receipt)


def remove(name: str) -> bool:
    return _store().delete(_NAMESPACE, name.lower().strip())


def verify(receipt: InstallReceipt) -> str:
    """Devolve ``ok`` ou ``broken`` conforme artifacts / venv / wrapper."""
    checked: list[Path] = []
    for raw in receipt.artifacts:
        p = Path(raw).expanduser()
        if p not in checked:
            checked.append(p)

    if not checked:
        if receipt.venv_path:
            checked.append(Path(receipt.venv_path).expanduser())
        prefix = Path(receipt.install_prefix or Path.home() / ".local")
        bin_dir = prefix / "bin"
        if receipt.cli_name:
            if (bin_dir / receipt.cli_name).exists():
                checked.append(bin_dir / receipt.cli_name)
            if (bin_dir / f"{receipt.cli_name}.cmd").exists():
                checked.append(bin_dir / f"{receipt.cli_name}.cmd")

    if not checked:
        return "broken"

    for path in checked:
        if not path.exists():
            return "broken"
    return "ok"


def list_with_status() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for name, receipt in sorted(load_all().items()):
        status = verify(receipt)
        commit_short = receipt.commit[:8] if receipt.commit else ""
        rows.append(
            {
                "name": name,
                "cli_name": receipt.cli_name,
                "kind": receipt.kind,
                "source": receipt.source,
                "ref": receipt.ref,
                "commit": receipt.commit,
                "commit_short": commit_short,
                "status": status,
                "installed_at": receipt.installed_at,
                "updated_at": receipt.updated_at,
                "repo": receipt.repo,
                "project_root": receipt.project_root,
            }
        )
    return rows
