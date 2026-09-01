from __future__ import annotations

from duckdb import DuckDBPyConnection

from app.analytics.filters import build_event_filter
from app.analytics.source import EventSource
from app.schemas.analytics import DFGEdge, DFGNode, DFGResult, EventFilters


def calculate_dfg(
    connection: DuckDBPyConnection,
    filters: EventFilters | None = None,
    max_nodes: int | None = None,
    max_edges: int | None = None,
    source: EventSource | None = None,
) -> DFGResult:
    active_filters = filters or EventFilters()
    active_source = source or EventSource.default_table()
    where_clause, parameters = build_event_filter(active_filters)
    source_parameters = list(active_source.parameters)

    totals_row = connection.execute(
        f"""
        SELECT
            count(DISTINCT case_id) AS total_cases,
            count(*) AS total_events
        FROM {active_source.relation_sql}
        WHERE {where_clause}
        """,
        [*source_parameters, *parameters],
    ).fetchone()
    if totals_row is None:
        raise RuntimeError("DFG totals query returned no row")

    node_limit_clause = "LIMIT ?" if max_nodes is not None else ""
    node_parameters = [*source_parameters, *parameters]
    if max_nodes is not None:
        node_parameters.append(max_nodes)

    node_rows = connection.execute(
        f"""
        WITH filtered_events AS (
            SELECT case_id, activity
            FROM {active_source.relation_sql}
            WHERE {where_clause}
        ),
        totals AS (
            SELECT count(DISTINCT case_id) AS total_cases
            FROM filtered_events
        )
        SELECT
            activity,
            count(*) AS event_count,
            count(DISTINCT case_id) AS case_count,
            coalesce(
                count(DISTINCT case_id)::DOUBLE / nullif(max(total_cases), 0),
                0.0
            ) AS case_share
        FROM filtered_events
        CROSS JOIN totals
        GROUP BY activity
        ORDER BY event_count DESC, activity ASC
        {node_limit_clause}
        """,
        node_parameters,
    ).fetchall()

    edge_node_limit_clause = "LIMIT ?" if max_nodes is not None else ""
    edge_limit_clause = "LIMIT ?" if max_edges is not None else ""
    edge_parameters = [*source_parameters, *parameters]
    if max_nodes is not None:
        edge_parameters.append(max_nodes)
    if max_edges is not None:
        edge_parameters.append(max_edges)

    edge_rows = connection.execute(
        f"""
        WITH filtered_events AS (
            SELECT
                event_id,
                source_event_id,
                case_id,
                activity,
                event_ts,
                source_sequence,
                ingest_sequence
            FROM {active_source.relation_sql}
            WHERE {where_clause}
        ),
        totals AS (
            SELECT count(DISTINCT case_id) AS total_cases
            FROM filtered_events
        ),
        visible_nodes AS (
            SELECT activity
            FROM filtered_events
            GROUP BY activity
            ORDER BY count(*) DESC, activity ASC
            {edge_node_limit_clause}
        ),
        sequenced AS (
            SELECT
                case_id,
                activity AS source,
                event_ts,
                lead(activity) OVER event_order AS target,
                lead(event_ts) OVER event_order AS next_event_ts
            FROM filtered_events
            WINDOW event_order AS (
                PARTITION BY case_id
                ORDER BY
                    event_ts,
                    source_sequence NULLS LAST,
                    source_event_id NULLS LAST,
                    ingest_sequence NULLS LAST
            )
        )
        SELECT
            source,
            target,
            count(*) AS transition_count,
            count(DISTINCT case_id) AS case_count,
            coalesce(
                count(DISTINCT case_id)::DOUBLE / nullif(max(total_cases), 0),
                0.0
            ) AS case_share,
            median(date_diff('millisecond', event_ts, next_event_ts)) AS median_transition_ms,
            quantile_cont(
                date_diff('millisecond', event_ts, next_event_ts),
                0.90
            ) AS p90_transition_ms
        FROM sequenced
        CROSS JOIN totals
        WHERE
            target IS NOT NULL
            AND source IN (SELECT activity FROM visible_nodes)
            AND target IN (SELECT activity FROM visible_nodes)
        GROUP BY source, target
        ORDER BY transition_count DESC, source ASC, target ASC
        {edge_limit_clause}
        """,
        edge_parameters,
    ).fetchall()

    nodes = [
        DFGNode(
            activity=row[0],
            event_count=row[1],
            case_count=row[2],
            case_share=row[3],
        )
        for row in node_rows
    ]
    edges = [
        DFGEdge(
            source=row[0],
            target=row[1],
            transition_count=row[2],
            case_count=row[3],
            case_share=row[4],
            median_transition_ms=row[5],
            p90_transition_ms=row[6],
        )
        for row in edge_rows
    ]
    return DFGResult(
        total_cases=totals_row[0],
        total_events=totals_row[1],
        node_count=len(nodes),
        edge_count=len(edges),
        nodes=nodes,
        edges=edges,
    )
