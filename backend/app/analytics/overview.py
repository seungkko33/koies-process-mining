from __future__ import annotations

from duckdb import DuckDBPyConnection

from app.analytics.filters import build_event_filter
from app.schemas.analytics import EventFilters, OverviewResult


def calculate_overview(
    connection: DuckDBPyConnection,
    filters: EventFilters | None = None,
) -> OverviewResult:
    active_filters = filters or EventFilters()
    where_clause, parameters = build_event_filter(active_filters)
    row = connection.execute(
        f"""
        WITH filtered_events AS (
            SELECT case_id, activity, event_ts
            FROM curated.event_log
            WHERE {where_clause}
        ),
        case_summary AS (
            SELECT
                case_id,
                date_diff('millisecond', min(event_ts), max(event_ts)) AS throughput_ms
            FROM filtered_events
            GROUP BY case_id
        ),
        activity_per_case AS (
            SELECT case_id, activity, count(*) AS activity_count
            FROM filtered_events
            GROUP BY case_id, activity
        ),
        rework_cases AS (
            SELECT DISTINCT case_id
            FROM activity_per_case
            WHERE activity_count >= 2
        )
        SELECT
            count(DISTINCT case_id) AS case_count,
            count(*) AS event_count,
            count(DISTINCT activity) AS activity_count,
            (SELECT median(throughput_ms) FROM case_summary) AS median_throughput_ms,
            (SELECT quantile_cont(throughput_ms, 0.90) FROM case_summary) AS p90_throughput_ms,
            coalesce(
                (SELECT count(*) FROM rework_cases)::DOUBLE
                    / nullif(count(DISTINCT case_id), 0),
                0.0
            ) AS rework_rate
        FROM filtered_events
        """,
        parameters,
    ).fetchone()
    if row is None:
        raise RuntimeError("Overview query returned no row")

    return OverviewResult(
        case_count=row[0],
        event_count=row[1],
        activity_count=row[2],
        median_throughput_ms=row[3],
        p90_throughput_ms=row[4],
        rework_rate=row[5],
    )

