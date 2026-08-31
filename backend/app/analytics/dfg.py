from __future__ import annotations

from duckdb import DuckDBPyConnection

from app.analytics.filters import build_event_filter
from app.schemas.analytics import DFGEdge, DFGNode, DFGResult, EventFilters


def calculate_dfg(
    connection: DuckDBPyConnection,
    filters: EventFilters | None = None,
) -> DFGResult:
    active_filters = filters or EventFilters()
    where_clause, parameters = build_event_filter(active_filters)

    node_rows = connection.execute(
        f"""
        WITH filtered_events AS (
            SELECT case_id, activity
            FROM curated.event_log
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
        """,
        parameters,
    ).fetchall()

    edge_rows = connection.execute(
        f"""
        WITH filtered_events AS (
            SELECT
                event_id,
                case_id,
                activity,
                event_ts,
                source_sequence,
                ingest_sequence
            FROM curated.event_log
            WHERE {where_clause}
        ),
        totals AS (
            SELECT count(DISTINCT case_id) AS total_cases
            FROM filtered_events
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
                    ingest_sequence NULLS LAST,
                    event_id
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
        WHERE target IS NOT NULL
        GROUP BY source, target
        ORDER BY transition_count DESC, source ASC, target ASC
        """,
        parameters,
    ).fetchall()

    return DFGResult(
        nodes=[
            DFGNode(
                activity=row[0],
                event_count=row[1],
                case_count=row[2],
                case_share=row[3],
            )
            for row in node_rows
        ],
        edges=[
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
        ],
    )

