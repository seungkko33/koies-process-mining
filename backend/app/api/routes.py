from __future__ import annotations

from datetime import datetime
from time import perf_counter
from typing import Annotated

from duckdb import DuckDBPyConnection
from fastapi import APIRouter, Depends, HTTPException, Query, Request

from app.analytics.dfg import calculate_dfg
from app.analytics.overview import calculate_overview
from app.analytics.source import EventSource
from app.api.dependencies import get_connection
from app.config import Settings
from app.datasets.service import DatasetService
from app.schemas.analytics import (
    DFGEnvelope,
    EventFilters,
    HealthResponse,
    OverviewEnvelope,
    QueryMeta,
)
from app.schemas.datasets import ActivityLevel

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok", service="koies-process-mining")


@router.get("/api/overview", response_model=OverviewEnvelope)
def overview(
    request: Request,
    connection: Annotated[DuckDBPyConnection, Depends(get_connection)],
    dataset_id: Annotated[str | None, Query()] = None,
) -> OverviewEnvelope:
    source = _event_source(request, connection, dataset_id)
    started_at = perf_counter()
    result = calculate_overview(connection, source=source)
    query_ms = round((perf_counter() - started_at) * 1_000)
    return OverviewEnvelope(
        data=result,
        meta=QueryMeta(
            query_ms=query_ms,
            rows=1,
            filter_signature=source.signature,
            mapping_version=source.mapping_version,
            dataset_id=source.dataset_id,
            semantic_contract_version=source.semantic_contract_version,
            normalization_version=source.normalization_version,
            activity_level=source.activity_level,
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
    dataset_id: Annotated[str | None, Query()] = None,
    activity_level: Annotated[ActivityLevel, Query()] = ActivityLevel.SOURCE,
    activity_mapping_version: Annotated[int | None, Query(ge=1)] = None,
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
    source = _event_source(
        request,
        connection,
        dataset_id,
        activity_level=activity_level,
        activity_mapping_version=activity_mapping_version,
    )
    coverage = None
    if dataset_id is not None and activity_level == ActivityLevel.BUSINESS:
        selected_version = int(str(source.activity_mapping_version).rsplit("v", 1)[1])
        coverage = DatasetService(connection, settings).activity_mapping_coverage(
            dataset_id, selected_version
        )

    started_at = perf_counter()
    result = calculate_dfg(
        connection,
        filters=filters,
        max_nodes=effective_max_nodes,
        max_edges=effective_max_edges,
        source=source,
    )
    query_ms = round((perf_counter() - started_at) * 1_000)
    filter_signature = (
        f"date_from={date_from.isoformat() if date_from else 'all'};"
        f"date_to={date_to.isoformat() if date_to else 'all'};"
        f"max_nodes={effective_max_nodes};max_edges={effective_max_edges};"
        f"{source.signature}"
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
            mapping_version=source.mapping_version,
            dataset_id=source.dataset_id,
            semantic_contract_version=source.semantic_contract_version,
            activity_mapping_version=source.activity_mapping_version,
            normalization_version=source.normalization_version,
            activity_level=source.activity_level,
            unique_source_activities=(
                coverage.unique_source_activities if coverage else None
            ),
            business_activities=(coverage.business_activities if coverage else None),
            event_mapping_coverage=(coverage.event_mapping_coverage if coverage else None),
        ),
        warnings=warnings,
    )


def _event_source(
    request: Request,
    connection: DuckDBPyConnection,
    dataset_id: str | None,
    *,
    activity_level: ActivityLevel = ActivityLevel.SOURCE,
    activity_mapping_version: int | None = None,
) -> EventSource:
    if dataset_id is None:
        return EventSource.default_table()
    settings: Settings = request.app.state.settings
    service = DatasetService(connection, settings)
    path, mapping_version = service.normalized_path_for_analysis(dataset_id)
    dataset = service.get_dataset(dataset_id)
    contract_version = dataset.semantic_contract_version
    if contract_version is None:
        raise HTTPException(status_code=409, detail="Semantic Contract is unavailable")
    normalization_version = dataset.normalization_version or "event-log-v1"
    if activity_level == ActivityLevel.BUSINESS:
        mapping_set = service.require_activity_mapping_set(
            dataset_id, activity_mapping_version
        )
        return EventSource.business_activity_parquet(
            path,
            dataset_id,
            mapping_version,
            contract_version,
            normalization_version,
            mapping_set,
        )
    return EventSource.normalized_parquet(
        path,
        dataset_id,
        mapping_version,
        contract_version,
        normalization_version,
    )
