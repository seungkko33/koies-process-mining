from __future__ import annotations

from collections.abc import Iterator
from time import perf_counter
from typing import Annotated

from duckdb import DuckDBPyConnection
from fastapi import APIRouter, Depends, Request

from app.analytics.overview import calculate_overview
from app.database import DuckDBManager
from app.schemas.analytics import HealthResponse, OverviewEnvelope, QueryMeta

router = APIRouter()


def get_connection(request: Request) -> Iterator[DuckDBPyConnection]:
    manager: DuckDBManager = request.app.state.database
    with manager.connection() as connection:
        yield connection


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok", service="koies-process-mining")


@router.get("/api/overview", response_model=OverviewEnvelope)
def overview(
    connection: Annotated[DuckDBPyConnection, Depends(get_connection)],
) -> OverviewEnvelope:
    started_at = perf_counter()
    result = calculate_overview(connection)
    query_ms = round((perf_counter() - started_at) * 1_000)
    return OverviewEnvelope(
        data=result,
        meta=QueryMeta(
            query_ms=query_ms,
            rows=1,
            filter_signature="all-events",
            mapping_version="all",
        ),
        warnings=[],
    )
