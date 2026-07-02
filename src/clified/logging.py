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
        """True se Rich está instalado e o console está activo."""
        return _RICH and self._console is not None

    @property
    def console(self) -> Console | None:
        """Console Rich interno, ou ``None`` no fallback ANSI."""
        return self._console

    def _plain(self, label: str, msg: str) -> None:
        """Fallback sem Rich: escreve linha prefixada em stdout (texto simples)."""
        line = f"{label} {msg}\n" if label else f"{msg}\n"
        sys.stdout.write(line)
        sys.stdout.flush()

    def info(self, msg: str) -> None:
        """Mensagem informativa (verde)."""
        if self.rich_available:
            self._console.print(  # type: ignore[union-attr]
                f"[bold green]INFO[/bold green] {msg}"
            )
        else:
            self._plain("INFO", msg)

    def warning(self, message: str) -> None:
        """Alias de ``warn``."""
        self.warn(message)

    def warn(self, message: str) -> None:
        """Aviso (amarelo)."""
        if self.rich_available:
            self._console.print(  # type: ignore[union-attr]
                f"[bold yellow]WARN[/bold yellow] {message}"
            )
        else:
            self._plain("WARN", message)

    def error(self, msg: str) -> None:
        """Erro (vermelho)."""
        if self.rich_available:
            self._console.print(  # type: ignore[union-attr]
                f"[bold red]ERROR[/bold red] {msg}"
            )
        else:
            self._plain("ERROR", msg)

    def step(self, msg: str) -> None:
        """Passo de instalação (azul)."""
        if self.rich_available:
            self._console.print(  # type: ignore[union-attr]
                f"[bold blue]STEP[/bold blue] {msg}"
            )
        else:
            self._plain("STEP", msg)

    def success(self, msg: str) -> None:
        """Conclusão bem-sucedida (verde com ✓)."""
        if self.rich_available:
            self._console.print(  # type: ignore[union-attr]
                f"[bold green]✓[/bold green] {msg}"
            )
        else:
            self._plain("OK", msg)

    def header(self, text: str) -> None:
        """Secção destacada com Panel Rich."""
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
            sys.stdout.write(f"\n## {text}\n")
            sys.stdout.flush()

    def panel(self, content: str, *, title: str = "", border: str = "green") -> None:
        """Panel Rich com título e cor de borda configuráveis."""
        if self.rich_available:
            self._console.print(  # type: ignore[union-attr]
                Panel(content, title=title or None, border_style=border),
            )
        else:
            if title:
                self._plain("", title)
            self._plain("", content)

    def table(self, rows: list[tuple[str, str]], *, title: str = "") -> None:
        """Tabela chave/valor com Rich ou fallback em texto simples."""
        if self.rich_available:
            t = Table(show_header=False, box=box.SIMPLE, title=title or None)
            for k, v in rows:
                t.add_row(k, v)
            self._console.print(Panel(t, border_style="cyan"))  # type: ignore[union-attr]
        else:
            if title:
                self._plain("", title)
            for k, v in rows:
                self._plain("", f"{k}: {v}")
