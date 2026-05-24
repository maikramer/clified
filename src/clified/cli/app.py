"""Scaffold Click reutilizável (--json, --quiet, --verbose)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

try:
    import click
except ImportError:  # pragma: no cover - optional dep
    click = None  # type: ignore[assignment]

from .output import OutputFormatter, get_output_formatter

if TYPE_CHECKING:
    from collections.abc import Callable


def require_click() -> None:
    if click is None:
        msg = "Click não instalado. Use: pip install clified[cli]"
        raise ImportError(
            msg,
        )


def create_cli_group(name: str = "cli", help_text: str = "CLI tool") -> Any:
    """Cria grupo Click com opções globais de output."""
    require_click()

    @click.group(name=name, help=help_text)
    @click.option(
        "--json", "json_output", is_flag=True, help="Saída JSON (machine-readable)"
    )
    @click.option("-q", "--quiet", is_flag=True, help="Suprime output decorativo")
    @click.option("-v", "--verbose", is_flag=True, help="Modo verboso")
    @click.pass_context
    def group(
        ctx: click.Context, json_output: bool, quiet: bool, verbose: bool
    ) -> None:
        ctx.ensure_object(dict)
        ctx.obj["output"] = OutputFormatter(json_mode=json_output, quiet=quiet)
        ctx.obj["verbose"] = verbose

    return group


def pass_output(func: Callable) -> Callable:
    """Decorator que injecta ``OutputFormatter`` como kwarg ``output``."""
    require_click()

    @click.pass_context
    def wrapper(ctx: click.Context, *args: Any, **kwargs: Any) -> Any:
        kwargs["output"] = get_output_formatter(ctx)
        return func(*args, **kwargs)

    return wrapper
