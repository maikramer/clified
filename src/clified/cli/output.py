"""Saída CLI: Rich, JSON e quiet."""

from __future__ import annotations

import json
import sys
from typing import Any

from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table


class OutputFormatter:
    """Formata saída para humanos ou máquinas (JSON/quiet)."""

    def __init__(self, json_mode: bool = False, quiet: bool = False) -> None:
        self.json_mode = json_mode
        self.quiet = quiet
        self._console = Console(stderr=True) if json_mode else Console()

    @property
    def is_json(self) -> bool:
        return self.json_mode

    @property
    def is_quiet(self) -> bool:
        return self.quiet

    @property
    def console(self) -> Console:
        return self._console

    def success(self, data: dict[str, Any], message: str = "") -> None:
        if self.json_mode:
            self._print_json({"status": "success", **data})
        elif not self.quiet and message:
            self._console.print(f"[green]{message}[/green]")

    def error(self, message: str, details: dict[str, Any] | None = None) -> None:
        if self.json_mode:
            payload: dict[str, Any] = {"status": "error", "error": message}
            if details:
                payload["details"] = details
            self._print_json(payload)
        else:
            self._console.print(f"[red]{message}[/red]", highlight=False)

    def info(self, message: str) -> None:
        if self.json_mode or self.quiet:
            return
        self._console.print(message)

    def warning(self, message: str) -> None:
        if self.json_mode or self.quiet:
            return
        self._console.print(f"[yellow]{message}[/yellow]")

    def data(self, payload: dict[str, Any], title: str = "") -> None:
        if self.json_mode:
            self._print_json({"status": "success", **payload})
        elif not self.quiet:
            if title:
                text = json.dumps(payload, indent=2, default=str, ensure_ascii=False)
                self._console.print(Panel(text, title=title, border_style="blue"))
            else:
                self._console.print_json(data=payload)

    def table(
        self,
        rows: list[dict[str, Any]],
        columns: list[str],
        title: str = "",
        json_key: str = "items",
    ) -> None:
        if self.json_mode:
            self._print_json({"status": "success", json_key: rows, "count": len(rows)})
            return
        if self.quiet:
            return
        t = Table(title=title, box=box.ROUNDED, show_header=True, header_style="bold")
        for col in columns:
            t.add_column(col)
        for row in rows:
            t.add_row(*[str(row.get(col, "")) for col in columns])
        self._console.print(t)

    def _print_json(self, obj: Any) -> None:
        sys.stdout.write(json.dumps(obj, indent=2, default=str, ensure_ascii=False))
        sys.stdout.write("\n")
        sys.stdout.flush()
