from pathlib import Path

from app.config import PROJECT_ROOT, load_settings


def test_load_example_config_and_resolve_paths() -> None:
    settings = load_settings(PROJECT_ROOT / "config" / "app.example.yaml")

    assert settings.app.host == "127.0.0.1"
    assert settings.duckdb.memory_limit == "20GB"
    assert settings.data.database_path == PROJECT_ROOT / "db" / "process_mining.duckdb"
    assert settings.duckdb.temp_directory == PROJECT_ROOT / "data" / "temp"
    assert isinstance(settings.data.raw_dir, Path)

