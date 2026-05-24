"""Persistência JSON thread-safe para estado entre execuções."""

from __future__ import annotations

import json
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, ClassVar

from clified.logging import Logger


class StateStore:
    """Armazena estado em ``~/.clified/state.json`` (ou path customizado)."""

    DEFAULT_STATE: ClassVar[dict[str, Any]] = {
        "metadata": {"version": "1.0", "created_at": None, "updated_at": None},
        "namespaces": {},
    }

    def __init__(self, path: Path | None = None, logger: Logger | None = None) -> None:
        self.path = path or Path.home() / ".clified" / "state.json"
        self.logger = logger or Logger()
        self._lock = threading.Lock()
        self._state: dict[str, Any] = {}
        self._load()

    def _load(self) -> None:
        with self._lock:
            try:
                if self.path.is_file():
                    self._state = json.loads(self.path.read_text(encoding="utf-8"))
                else:
                    self._state = json.loads(json.dumps(self.DEFAULT_STATE))
                    self._state["metadata"]["created_at"] = datetime.now(
                        tz=timezone.utc
                    ).isoformat()
            except json.JSONDecodeError:
                self.logger.warn("State corrompido; recriando.")
                self._state = json.loads(json.dumps(self.DEFAULT_STATE))
            for key, default in self.DEFAULT_STATE.items():
                if key not in self._state:
                    self._state[key] = (
                        default if not isinstance(default, dict) else dict(default)
                    )

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._state["metadata"]["updated_at"] = datetime.now(
            tz=timezone.utc
        ).isoformat()
        temp = self.path.with_suffix(".tmp")
        temp.write_text(
            json.dumps(self._state, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        temp.replace(self.path)

    def get(self, namespace: str, key: str, default: Any = None) -> Any:
        with self._lock:
            return (
                self._state.get("namespaces", {}).get(namespace, {}).get(key, default)
            )

    def set(self, namespace: str, key: str, value: Any) -> None:
        with self._lock:
            ns = self._state.setdefault("namespaces", {})
            bucket = ns.setdefault(namespace, {})
            bucket[key] = value
            self._save()

    def get_namespace(self, namespace: str) -> dict[str, Any]:
        with self._lock:
            return dict(self._state.get("namespaces", {}).get(namespace, {}))

    def delete(self, namespace: str, key: str) -> bool:
        with self._lock:
            ns = self._state.get("namespaces", {})
            if namespace in ns and key in ns[namespace]:
                del ns[namespace][key]
                self._save()
                return True
            return False

    def clear_namespace(self, namespace: str) -> None:
        with self._lock:
            self._state.setdefault("namespaces", {})[namespace] = {}
            self._save()

    def clear_all(self) -> None:
        with self._lock:
            self._state = json.loads(json.dumps(self.DEFAULT_STATE))
            self._state["metadata"]["created_at"] = datetime.now(
                tz=timezone.utc
            ).isoformat()
            self._save()

    def export_state(self) -> dict[str, Any]:
        with self._lock:
            return json.loads(json.dumps(self._state))

    def import_state(self, state: dict[str, Any]) -> None:
        with self._lock:
            self._state = state
            self._save()


_store: StateStore | None = None


def get_state_store(
    path: Path | None = None, logger: Logger | None = None
) -> StateStore:
    global _store
    if _store is None:
        _store = StateStore(path, logger)
    return _store
