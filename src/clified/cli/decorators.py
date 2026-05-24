"""Decorators para comandos CLI."""

from __future__ import annotations

import functools
import sys
from typing import TYPE_CHECKING

from clified.core.exceptions import (
    ClifiedError,
    ConfigError,
    DeploymentError,
    InfrastructureError,
    InstallError,
    NetworkError,
    ValidationError,
)
from clified.logging import Logger

if TYPE_CHECKING:
    from collections.abc import Callable

logger = Logger()

EXIT_SUCCESS = 0
EXIT_GENERAL_ERROR = 1
EXIT_CONFIG_ERROR = 2
EXIT_INFRA_ERROR = 3

_CONFIG_EXCEPTIONS: tuple[type[Exception], ...] = (ConfigError, ValidationError)
_INFRA_EXCEPTIONS: tuple[type[Exception], ...] = (
    InfrastructureError,
    NetworkError,
    DeploymentError,
    InstallError,
)


def handle_cli_errors(func: Callable) -> Callable:
    """Padroniza exit codes: 0 ok, 1 geral, 2 config, 3 infra."""

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except (SystemExit, KeyboardInterrupt):
            raise
        except _CONFIG_EXCEPTIONS as exc:
            logger.error(str(exc))
            sys.exit(EXIT_CONFIG_ERROR)
        except _INFRA_EXCEPTIONS as exc:
            logger.error(str(exc))
            sys.exit(EXIT_INFRA_ERROR)
        except ClifiedError as exc:
            logger.error(str(exc))
            sys.exit(EXIT_GENERAL_ERROR)
        except Exception as exc:
            logger.error(f"Erro inesperado: {exc}")
            sys.exit(EXIT_GENERAL_ERROR)

    return wrapper
