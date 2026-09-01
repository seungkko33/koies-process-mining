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
            dfg = await client.get("/api/dfg")

    assert health.status_code == 200
    assert health.json() == {"status": "ok", "service": "koies-process-mining"}
    assert overview.status_code == 200
    payload = overview.json()
    assert payload["data"]["case_count"] == 3
    assert payload["data"]["event_count"] == 10
    assert payload["meta"]["filter_signature"] == "all-events"
    assert payload["warnings"] == []
    assert dfg.status_code == 200
    dfg_payload = dfg.json()
    assert dfg_payload["data"]["total_cases"] == 3
    assert dfg_payload["data"]["total_events"] == 10
    assert dfg_payload["data"]["node_count"] == 4
    assert dfg_payload["data"]["edge_count"] == 5
    assert dfg_payload["data"]["edges"][0]["source"] == "A"
    assert dfg_payload["data"]["edges"][0]["target"] == "B"


@pytest.mark.anyio
async def test_dfg_api_handles_empty_event_log_and_limits(tmp_path: Path) -> None:
    settings = load_settings()
    settings = settings.model_copy(
        update={
            "data": settings.data.model_copy(
                update={"database_path": tmp_path / "empty-api-test.duckdb"}
            ),
            "duckdb": settings.duckdb.model_copy(
                update={"temp_directory": tmp_path / "empty-duckdb-temp"}
            ),
        }
    )
    application = create_app(settings)

    async with application.router.lifespan_context(application):
        transport = httpx.ASGITransport(app=application)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            empty_response = await client.get("/api/dfg?max_nodes=2&max_edges=1")

    assert empty_response.status_code == 200
    payload = empty_response.json()
    assert payload["data"] == {
        "total_cases": 0,
        "total_events": 0,
        "node_count": 0,
        "edge_count": 0,
        "nodes": [],
        "edges": [],
    }
    assert payload["meta"]["rows"] == 0


@pytest.mark.anyio
async def test_dfg_api_rejects_invalid_date_range(tmp_path: Path) -> None:
    settings = load_settings()
    settings = settings.model_copy(
        update={
            "data": settings.data.model_copy(
                update={"database_path": tmp_path / "invalid-filter-api-test.duckdb"}
            ),
            "duckdb": settings.duckdb.model_copy(
                update={"temp_directory": tmp_path / "invalid-filter-duckdb-temp"}
            ),
        }
    )
    application = create_app(settings)

    async with application.router.lifespan_context(application):
        transport = httpx.ASGITransport(app=application)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get(
                "/api/dfg?date_from=2026-01-02T00:00:00&date_to=2026-01-01T00:00:00"
            )

    assert response.status_code == 422
    assert response.json() == {"detail": "date_from must be earlier than date_to"}
