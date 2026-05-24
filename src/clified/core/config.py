"""Configuração genérica do Clified (Pydantic + YAML)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field, field_validator

from clified.paths import default_clified_yml

from .exceptions import ConfigError


class RetryConfig(BaseModel):
    max_attempts: int = Field(default=3, ge=1, le=10)
    base_delay: float = Field(default=2.0, ge=0.1, le=60.0)
    max_delay: float = Field(default=60.0, ge=1.0, le=600.0)
    exponential_base: float = Field(default=2.0, ge=1.0, le=5.0)
    jitter: bool = True

    model_config = {"extra": "ignore"}


class LoggingConfig(BaseModel):
    level: str = Field(default="INFO")

    model_config = {"extra": "ignore"}

    @field_validator("level")
    @classmethod
    def validate_level(cls, v: str) -> str:
        valid = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        upper = v.upper()
        if upper not in valid:
            msg = f"Nível inválido: {v}. Use: {sorted(valid)}"
            raise ValueError(msg)
        return upper


class InstallConfig(BaseModel):
    """Defaults para o instalador."""

    prefix: Path = Field(default_factory=lambda: Path.home() / ".local")
    use_uv: bool = True
    default_python: str = "python3"

    model_config = {"extra": "ignore", "arbitrary_types_allowed": True}

    @field_validator("prefix", mode="before")
    @classmethod
    def path_from_str(cls, v: Any) -> Any:
        return Path(v) if isinstance(v, str) else v


class ClifiedConfig(BaseModel):
    base_dir: Path = Field(default_factory=lambda: Path.home() / ".clified")
    retry: RetryConfig = Field(default_factory=RetryConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    install: InstallConfig = Field(default_factory=InstallConfig)

    model_config = {"extra": "ignore", "arbitrary_types_allowed": True}

    @field_validator("base_dir", mode="before")
    @classmethod
    def path_from_str(cls, v: Any) -> Any:
        return Path(v) if isinstance(v, str) else v


class ConfigManager:
    """Carrega e persiste configuração YAML do Clified."""

    def __init__(self, config_file: Path | None = None) -> None:
        self.config_file = config_file or default_clified_yml()
        self._config: ClifiedConfig | None = None

    def get_config(self) -> ClifiedConfig:
        if self._config is None:
            self._load()
        if self._config is None:
            msg = "Configuração não carregada"
            raise ConfigError(msg)
        return self._config

    def _load(self) -> None:
        data: dict[str, Any] = {}
        if self.config_file.is_file():
            try:
                raw = self.config_file.read_text(encoding="utf-8").strip()
                if raw:
                    loaded = yaml.safe_load(raw)
                    if isinstance(loaded, dict):
                        data = loaded
            except Exception as exc:
                msg = f"Erro ao ler {self.config_file}: {exc}"
                raise ConfigError(msg) from exc
        self._config = ClifiedConfig.model_validate(data)

    def save(self) -> None:
        cfg = self.get_config()
        self.config_file.parent.mkdir(parents=True, exist_ok=True)
        payload = cfg.model_dump(mode="json")
        payload["base_dir"] = str(cfg.base_dir)
        payload["install"]["prefix"] = str(cfg.install.prefix)
        self.config_file.write_text(
            yaml.safe_dump(payload, default_flow_style=False, allow_unicode=True),
            encoding="utf-8",
        )

    def reload(self) -> ClifiedConfig:
        self._config = None
        return self.get_config()
