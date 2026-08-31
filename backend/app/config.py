from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG_PATH = PROJECT_ROOT / "config" / "app.example.yaml"
LOCAL_HOSTS = {"127.0.0.1", "localhost", "::1"}


class AppConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    host: str = "127.0.0.1"
    port: int = Field(default=8000, ge=1, le=65_535)
    environment: str = "local"


class DataConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    raw_dir: Path
    raw_parquet_dir: Path
    curated_dir: Path
    quarantine_dir: Path
    temp_dir: Path
    database_path: Path


class DuckDBConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    threads: int = Field(default=6, ge=1)
    memory_limit: str = Field(default="20GB", pattern=r"^\d+(\.\d+)?(KB|MB|GB|TB)$")
    preserve_insertion_order: bool = False
    temp_directory: Path


class AnalyticsConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    max_process_nodes: int = Field(default=100, ge=1, le=10_000)
    max_process_edges: int = Field(default=300, ge=1, le=10_000)
    max_variants: int = Field(default=100, ge=1, le=10_000)
    default_case_page_size: int = Field(default=100, ge=1, le=1_000)
    query_timeout_seconds: int = Field(default=60, ge=1)


class SecurityConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    allow_external_ai: bool = False
    allow_raw_export: bool = False
    expose_raw_params: bool = False
    bind_localhost_only: bool = True


class QualityConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    max_timestamp_parse_failure_rate: float = Field(default=0.01, ge=0, le=1)
    max_ambiguous_mapping_count: int = Field(default=0, ge=0)
    warn_unmapped_activity_rate: float = Field(default=0.05, ge=0, le=1)


class Settings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    app: AppConfig
    data: DataConfig
    duckdb: DuckDBConfig
    analytics: AnalyticsConfig
    security: SecurityConfig
    quality: QualityConfig

    @model_validator(mode="after")
    def require_local_bind_when_enabled(self) -> Settings:
        if self.security.bind_localhost_only and self.app.host not in LOCAL_HOSTS:
            raise ValueError("app.host must be local when bind_localhost_only is enabled")
        return self


def _resolve_path(path: Path, base_dir: Path) -> Path:
    return path if path.is_absolute() else (base_dir / path).resolve()


def _resolve_data_paths(settings: Settings, base_dir: Path) -> Settings:
    data = settings.data.model_copy(
        update={
            field_name: _resolve_path(getattr(settings.data, field_name), base_dir)
            for field_name in DataConfig.model_fields
        }
    )
    duckdb = settings.duckdb.model_copy(
        update={
            "temp_directory": _resolve_path(settings.duckdb.temp_directory, base_dir),
        }
    )
    return settings.model_copy(update={"data": data, "duckdb": duckdb})


def load_settings(config_path: Path | str | None = None) -> Settings:
    selected_value: Path | str = (
        config_path
        if config_path is not None
        else os.environ.get("PROCESS_MINING_CONFIG", str(DEFAULT_CONFIG_PATH))
    )
    selected_path = Path(selected_value).resolve()
    with selected_path.open(encoding="utf-8") as config_file:
        raw: Any = yaml.safe_load(config_file)
    if not isinstance(raw, dict):
        raise ValueError(f"Configuration must be a YAML mapping: {selected_path}")

    settings = Settings.model_validate(raw)
    base_dir = (
        selected_path.parent.parent
        if selected_path.parent.name == "config"
        else PROJECT_ROOT
    )
    return _resolve_data_paths(settings, base_dir)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return load_settings()
