-- DuckDB initial metadata/curated schema template
-- Operational raw data is preferably kept as Parquet and queried directly.

CREATE SCHEMA IF NOT EXISTS meta;
CREATE SCHEMA IF NOT EXISTS curated;
CREATE SCHEMA IF NOT EXISTS analytics;

CREATE TABLE IF NOT EXISTS meta.ingestion_batch (
    ingestion_batch_id VARCHAR,
    source_system VARCHAR NOT NULL,
    source_uri VARCHAR,
    source_checksum VARCHAR,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    status VARCHAR,
    raw_row_count BIGINT,
    curated_row_count BIGINT,
    rejected_row_count BIGINT,
    mapping_version VARCHAR,
    case_rule_version VARCHAR,
    notes VARCHAR
);

CREATE TABLE IF NOT EXISTS meta.activity_mapping (
    mapping_id VARCHAR,
    mapping_version VARCHAR NOT NULL,
    enabled BOOLEAN DEFAULT TRUE,
    priority INTEGER DEFAULT 100,
    source_system VARCHAR,
    class_pattern VARCHAR,
    method_pattern VARCHAR,
    module_pattern VARCHAR,
    condition_expression VARCHAR,
    activity_name VARCHAR NOT NULL,
    activity_group VARCHAR,
    valid_from TIMESTAMP,
    valid_to TIMESTAMP,
    description VARCHAR
);

CREATE TABLE IF NOT EXISTS meta.case_rule (
    rule_id VARCHAR,
    rule_version VARCHAR NOT NULL,
    process_domain VARCHAR NOT NULL,
    priority INTEGER DEFAULT 100,
    extraction_source VARCHAR NOT NULL,
    extraction_expression VARCHAR NOT NULL,
    hash_required BOOLEAN DEFAULT TRUE,
    fallback_rule_id VARCHAR,
    valid_from TIMESTAMP,
    valid_to TIMESTAMP,
    description VARCHAR
);

-- For smaller deployments this can be materialized inside DuckDB.
-- For very large deployments the same logical schema may live as Parquet.
CREATE TABLE IF NOT EXISTS curated.event_log (
    event_id VARCHAR,
    case_id VARCHAR NOT NULL,
    activity VARCHAR NOT NULL,
    event_ts TIMESTAMP NOT NULL,
    process_domain VARCHAR,
    source_system VARCHAR,
    source_class VARCHAR,
    source_method VARCHAR,
    module VARCHAR,
    lifecycle VARCHAR,
    org_code VARCHAR,
    actor_hash VARCHAR,
    result_code VARCHAR,
    duration_ms BIGINT,
    source_sequence BIGINT,
    ingest_sequence BIGINT,
    mapping_version VARCHAR,
    case_rule_version VARCHAR,
    ingestion_batch_id VARCHAR,
    event_date DATE
);

CREATE TABLE IF NOT EXISTS meta.data_quality_result (
    ingestion_batch_id VARCHAR,
    metric_name VARCHAR,
    metric_value DOUBLE,
    threshold_value DOUBLE,
    status VARCHAR,
    measured_at TIMESTAMP
);
