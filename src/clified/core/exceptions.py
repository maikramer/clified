"""Exceções genéricas do Clified."""

from __future__ import annotations


class ClifiedError(Exception):
    """Exceção base."""

    def __init__(self, message: str = "", *, details: dict | None = None) -> None:
        self.message = message
        self.details = details or {}
        super().__init__(message)


class ConfigError(ClifiedError):
    """Erro de configuração."""


class ValidationError(ClifiedError):
    """Erro de validação de entrada."""


class ToolError(ClifiedError):
    """Erro genérico de ferramenta."""


class InstallError(ClifiedError):
    """Erro durante instalação."""


class InfrastructureError(ClifiedError):
    """Erro de infraestrutura (rede, serviços externos, etc.)."""


class NetworkError(InfrastructureError):
    """Erro de rede."""


class ClifiedConnectionError(InfrastructureError):
    """Erro de conexão."""


class DeploymentError(InfrastructureError):
    """Erro de deploy/build."""


class RetryableError(ClifiedError):
    """Operação pode ser retentada."""


class ClifiedTimeoutError(ClifiedError):
    """Operação excedeu tempo limite."""


class CircuitBreakerError(ClifiedError):
    """Circuit breaker bloqueou a operação."""
