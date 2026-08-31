-- Reference SQL snippets. Production code should parameterize filters and keep them in a query module.

-- Overview
SELECT
    count(*) AS event_count,
    count(DISTINCT case_id) AS case_count,
    count(DISTINCT activity) AS activity_count
FROM curated.event_log;

-- DFG
SELECT
    activity AS source_activity,
    next_activity AS target_activity,
    count(*) AS transition_count,
    count(DISTINCT case_id) AS case_count,
    median(date_diff('millisecond', event_ts, next_event_ts)) AS median_transition_ms,
    quantile_cont(date_diff('millisecond', event_ts, next_event_ts), 0.9) AS p90_transition_ms
FROM analytics.v_ordered_events
WHERE next_activity IS NOT NULL
GROUP BY activity, next_activity
ORDER BY transition_count DESC;

-- Throughput
SELECT
    median(throughput_ms) AS median_throughput_ms,
    avg(throughput_ms) AS avg_throughput_ms,
    quantile_cont(throughput_ms, 0.75) AS p75_throughput_ms,
    quantile_cont(throughput_ms, 0.90) AS p90_throughput_ms,
    quantile_cont(throughput_ms, 0.95) AS p95_throughput_ms
FROM analytics.v_case_summary;

-- Rework by activity
WITH activity_per_case AS (
    SELECT case_id, activity, count(*) AS cnt
    FROM curated.event_log
    GROUP BY case_id, activity
)
SELECT
    activity,
    rework_case_count,
    cases_with_activity,
    rework_case_count::DOUBLE / NULLIF(cases_with_activity, 0) AS rework_case_rate
FROM (
    SELECT
        activity,
        count(*) FILTER (WHERE cnt >= 2) AS rework_case_count,
        count(*) AS cases_with_activity
    FROM activity_per_case
    GROUP BY activity
) s
ORDER BY rework_case_rate DESC, rework_case_count DESC;

-- Variant template. list aggregation may be memory intensive on very high-cardinality data;
-- benchmark before using for the full dataset and consider staged materialization.
WITH seq AS (
    SELECT
        case_id,
        string_agg(activity, ' > ' ORDER BY event_ts, source_sequence, ingest_sequence, event_id) AS variant_sequence
    FROM curated.event_log
    GROUP BY case_id
)
SELECT
    variant_sequence,
    count(*) AS case_count
FROM seq
GROUP BY variant_sequence
ORDER BY case_count DESC
LIMIT 100;
