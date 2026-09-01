from __future__ import annotations

from collections.abc import Iterator
from datetime import datetime
from time import perf_counter
from typing import Annotated

from duckdb import DuckDBPyConnection
from fastapi import APIRouter, Depends, HTTPException, Query, Request

from app.analytics.dfg import calculate_dfg
from app.analytics.overview import calculate_overview
from app.config import Settings
from app.database import DuckDBManager
from app.schemas.analytics import (
    DFGEnvelope,
    EventFilters,
    HealthResponse,
    OverviewEnvelope,
    QueryMeta,
)

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


@router.get("/api/dfg", response_model=DFGEnvelope)
def dfg(
    request: Request,
    connection: Annotated[DuckDBPyConnection, Depends(get_connection)],
    date_from: Annotated[datetime | None, Query()] = None,
    date_to: Annotated[datetime | None, Query()] = None,
    max_nodes: Annotated[int | None, Query(ge=1)] = None,
    max_edges: Annotated[int | None, Query(ge=1)] = None,
) -> DFGEnvelope:
    if date_from is not None and date_to is not None and date_from >= date_to:
        raise HTTPException(
            status_code=422,
            detail="date_from must be earlier than date_to",
        )

    settings: Settings = request.app.state.settings
    effective_max_nodes = min(
        max_nodes or settings.analytics.max_process_nodes,
        settings.analytics.max_process_nodes,
    )
    effective_max_edges = min(
        max_edges or settings.analytics.max_process_edges,
        settings.analytics.max_process_edges,
    )
    filters = EventFilters(date_from=date_from, date_to=date_to)

    started_at = perf_counter()
    result = calculate_dfg(
        connection,
        filters=filters,
        max_nodes=effective_max_nodes,
        max_edges=effective_max_edges,
    )
    query_ms = round((perf_counter() - started_at) * 1_000)
    filter_signature = (
        f"date_from={date_from.isoformat() if date_from else 'all'};"
        f"date_to={date_to.isoformat() if date_to else 'all'};"
        f"max_nodes={effective_max_nodes};max_edges={effective_max_edges}"
    )

    warnings: list[str] = []
    if result.node_count == effective_max_nodes:
        warnings.append("Node limit reached; increase the configured limit or narrow the filter.")
    if result.edge_count == effective_max_edges:
        warnings.append("Edge limit reached; increase the configured limit or narrow the filter.")

    return DFGEnvelope(
        data=result,
        meta=QueryMeta(
            query_ms=query_ms,
            rows=result.node_count + result.edge_count,
            filter_signature=filter_signature,
            mapping_version="all",
        ),
        warnings=warnings,
    )
