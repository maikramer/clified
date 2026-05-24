"""Logger Rich/ANSI para o Clified."""

from __future__ import annotations

import contextlib
import sys


def _configure_stdio_utf8() -> None:
    """Evita UnicodeEncodeError no Windows (cp1252) com Rich e símbolos como ✓."""
    if sys.platform != "win32":
        return
    for stream in (sys.stdout, sys.stderr):
        if stream is not None and hasattr(stream, "reconfigure"):
            with contextlib.suppress(OSError, ValueError):
                stream.reconfigure(encoding="utf-8")


_configure_stdio_utf8()

try:
    from rich import box
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table

    _RICH = True
except ImportError:
    _RICH = False


class Logger:
    """Saída com Rich quando disponível; fallback ANSI."""

    def __init__(self, console: Console | None = None) -> None:
        if _RICH:
            self._console: Console | None = console or Console()
        else:
            self._console = None

    @property
    def rich_available(self) -> bool:
        return _RICH and self._console is not None

    @property
    def console(self) -> Console | None:
        return self._console

    def info(self, msg: str) -> None:
        if self.rich_available:
            self._console.print(f"[bold green]INFO[/bold green] {msg}")  # type: ignore[union-attr]
        else:
            pass

    def warning(self, message: str) -> None:
        """Alias de ``warn``."""
        self.warn(message)

    def warn(self, message: str) -> None:
        if self.rich_available:
            self._console.print(f"[bold yellow]WARN[/bold yellow] {message}")  # type: ignore[union-attr]
        else:
            pass

    def error(self, msg: str) -> None:
        if self.rich_available:
            self._console.print(f"[bold red]ERROR[/bold red] {msg}")  # type: ignore[union-attr]
        else:
            pass

    def step(self, msg: str) -> None:
        if self.rich_available:
            self._console.print(f"[bold blue]STEP[/bold blue] {msg}")  # type: ignore[union-attr]
        else:
            pass

    def success(self, msg: str) -> None:
        if self.rich_available:
            self._console.print(f"[bold green]✓[/bold green] {msg}")  # type: ignore[union-attr]
        else:
            pass

    def header(self, text: str) -> None:
        if self.rich_available:
            self._console.print()  # type: ignore[union-attr]
            self._console.print(  # type: ignore[union-attr]
                Panel(
                    f"[bold cyan]{text}[/bold cyan]",
                    border_style="cyan",
                    expand=False,
                ),
            )
        else:
            pass

    def panel(self, content: str, *, title: str = "", border: str = "green") -> None:
        if self.rich_available:
            self._console.print(  # type: ignore[union-attr]
                Panel(content, title=title or None, border_style=border),
            )
        elif title:
            pass

    def table(self, rows: list[tuple[str, str]], *, title: str = "") -> None:
        if self.rich_available:
            t = Table(show_header=False, box=box.SIMPLE, title=title or None)
            for k, v in rows:
                t.add_row(k, v)
            self._console.print(Panel(t, border_style="cyan"))  # type: ignore[union-attr]
        else:
            if title:
                pass
            for _k, _v in rows:
                pass
