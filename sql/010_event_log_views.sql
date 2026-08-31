-- Event sequencing views.
-- Replace curated.event_log with read_parquet(...) if Parquet is the source of truth.

CREATE OR REPLACE VIEW analytics.v_ordered_events AS
SELECT
    event_id,
    case_id,
    activity,
    event_ts,
    process_domain,
    result_code,
    duration_ms,
    org_code,
    source_sequence,
    ingest_sequence,
    row_number() OVER (
        PARTITION BY case_id
        ORDER BY event_ts, source_sequence NULLS LAST, ingest_sequence NULLS LAST, event_id
    ) AS event_position,
    lead(activity) OVER (
        PARTITION BY case_id
        ORDER BY event_ts, source_sequence NULLS LAST, ingest_sequence NULLS LAST, event_id
    ) AS next_activity,
    lead(event_ts) OVER (
        PARTITION BY case_id
        ORDER BY event_ts, source_sequence NULLS LAST, ingest_sequence NULLS LAST, event_id
    ) AS next_event_ts
FROM curated.event_log;

CREATE OR REPLACE VIEW analytics.v_case_summary AS
SELECT
    case_id,
    min(event_ts) AS case_start_ts,
    max(event_ts) AS case_end_ts,
    date_diff('millisecond', min(event_ts), max(event_ts)) AS throughput_ms,
    count(*) AS event_count,
    count(DISTINCT activity) AS distinct_activity_count
FROM curated.event_log
GROUP BY case_id;
