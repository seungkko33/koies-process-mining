from pathlib import Path

import httpx
import pytest
from app.config import load_settings
from app.main import create_app

from backend.tests.conftest import insert_golden_events


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.mark.anyio
async def test_health_and_overview_api(tmp_path: Path) -> None:
    settings = load_settings()
    settings = settings.model_copy(
        update={
            "data": settings.data.model_copy(
                update={"database_path": tmp_path / "api-test.duckdb"}
            ),
            "duckdb": settings.duckdb.model_copy(
                update={"temp_directory": tmp_path / "duckdb-temp"}
            ),
        }
    )
    application = create_app(settings)

    async with application.router.lifespan_context(application):
        with application.state.database.connection() as connection:
            insert_golden_events(connection)

        transport = httpx.ASGITransport(app=application)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            health = await client.get("/health")
            overview = await client.get("/api/overview")

    assert health.status_code == 200
    assert health.json() == {"status": "ok", "service": "koies-process-mining"}
    assert overview.status_code == 200
    payload = overview.json()
    assert payload["data"]["case_count"] == 3
    assert payload["data"]["event_count"] == 10
    assert payload["meta"]["filter_signature"] == "all-events"
    assert payload["warnings"] == []
