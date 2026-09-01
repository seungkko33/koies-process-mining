-- DuckDB initial metadata/curated schema template
-- Operational raw data is preferably kept as Parquet and queried directly.

CREATE SCHEMA IF NOT EXISTS meta;
CREATE SCHEMA IF NOT EXISTS curated;
CREATE SCHEMA IF NOT EXISTS analytics;

CREATE TABLE IF NOT EXISTS meta.dataset (
    dataset_id VARCHAR PRIMARY KEY,
    original_filename VARCHAR NOT NULL,
    staged_filename VARCHAR NOT NULL,
    file_type VARCHAR NOT NULL,
    file_size_bytes BIGINT NOT NULL,
    checksum VARCHAR,
    created_at TIMESTAMP NOT NULL,
    status VARCHAR NOT NULL,
    row_count BIGINT,
    column_count INTEGER,
    schema_version INTEGER NOT NULL DEFAULT 1,
    mapping_version INTEGER,
    normalization_version VARCHAR,
    normalization_status VARCHAR NOT NULL DEFAULT 'NOT_STARTED',
    normalized_filename VARCHAR,
    normalized_file_size_bytes BIGINT,
    quarantine_filename VARCHAR,
    quarantine_file_size_bytes BIGINT,
    source_type VARCHAR NOT NULL DEFAULT 'UPLOADED_FILE',
    error_code VARCHAR,
    source_path VARCHAR,
    source_mtime_ns BIGINT,
    import_mode VARCHAR,
    semantic_contract_version INTEGER,
    active_activity_mapping_version INTEGER,
    current_step VARCHAR,
    operation_started_at TIMESTAMP
);

-- Idempotent additions keep existing local databases forward-compatible.
ALTER TABLE meta.dataset ADD COLUMN IF NOT EXISTS source_path VARCHAR;
ALTER TABLE meta.dataset ADD COLUMN IF NOT EXISTS source_mtime_ns BIGINT;
ALTER TABLE meta.dataset ADD COLUMN IF NOT EXISTS import_mode VARCHAR;
ALTER TABLE meta.dataset ADD COLUMN IF NOT EXISTS semantic_contract_version INTEGER;
ALTER TABLE meta.dataset ADD COLUMN IF NOT EXISTS active_activity_mapping_version INTEGER;
ALTER TABLE meta.dataset ADD COLUMN IF NOT EXISTS current_step VARCHAR;
ALTER TABLE meta.dataset ADD COLUMN IF NOT EXISTS operation_started_at TIMESTAMP;

CREATE TABLE IF NOT EXISTS meta.dataset_column_profile (
    dataset_id VARCHAR NOT NULL,
    ordinal_position INTEGER NOT NULL,
    column_name VARCHAR NOT NULL,
    inferred_type VARCHAR NOT NULL,
    null_count BIGINT NOT NULL,
    approx_distinct BIGINT NOT NULL,
    min_value VARCHAR,
    max_value VARCHAR,
    sample_values_json VARCHAR NOT NULL,
    PRIMARY KEY (dataset_id, ordinal_position)
);

CREATE TABLE IF NOT EXISTS meta.mapping_definition (
    mapping_id VARCHAR PRIMARY KEY,
    dataset_id VARCHAR NOT NULL,
    version INTEGER NOT NULL,
    case_id_column VARCHAR NOT NULL,
    activity_column VARCHAR NOT NULL,
    timestamp_column VARCHAR NOT NULL,
    event_id_column VARCHAR,
    optional_mappings_json VARCHAR NOT NULL,
    timestamp_format VARCHAR,
    timezone VARCHAR,
    created_at TIMESTAMP NOT NULL,
    UNIQUE (dataset_id, version)
);

ALTER TABLE meta.mapping_definition ADD COLUMN IF NOT EXISTS display_timezone VARCHAR;

CREATE TABLE IF NOT EXISTS meta.semantic_contract (
    contract_id VARCHAR PRIMARY KEY,
    dataset_id VARCHAR NOT NULL,
    version INTEGER NOT NULL,
    mapping_version INTEGER NOT NULL,
    case_null_policy VARCHAR NOT NULL,
    case_empty_policy VARCHAR NOT NULL,
    case_id_pseudonymized BOOLEAN NOT NULL,
    case_id_classification VARCHAR NOT NULL,
    source_timezone VARCHAR NOT NULL,
    display_timezone VARCHAR NOT NULL,
    normalized_timezone VARCHAR NOT NULL,
    ordering_fields_json VARCHAR NOT NULL,
    attribute_policy_json VARCHAR NOT NULL,
    pii_policy_json VARCHAR NOT NULL,
    business_activity_mapping_version INTEGER,
    created_at TIMESTAMP NOT NULL,
    status VARCHAR NOT NULL,
    UNIQUE (dataset_id, version)
);

CREATE TABLE IF NOT EXISTS meta.activity_mapping_set (
    mapping_set_id VARCHAR PRIMARY KEY,
    dataset_id VARCHAR NOT NULL,
    version INTEGER NOT NULL,
    name VARCHAR NOT NULL,
    unmapped_policy VARCHAR NOT NULL,
    created_at TIMESTAMP NOT NULL,
    status VARCHAR NOT NULL,
    UNIQUE (dataset_id, version)
);

CREATE TABLE IF NOT EXISTS meta.activity_mapping_entry (
    mapping_set_id VARCHAR NOT NULL,
    source_activity VARCHAR NOT NULL,
    business_activity VARCHAR NOT NULL,
    description VARCHAR,
    enabled BOOLEAN NOT NULL DEFAULT TRUE,
    PRIMARY KEY (mapping_set_id, source_activity)
);

CREATE TABLE IF NOT EXISTS meta.dataset_artifact (
    artifact_id VARCHAR PRIMARY KEY,
    dataset_id VARCHAR NOT NULL,
    semantic_contract_version INTEGER,
    mapping_version INTEGER,
    artifact_type VARCHAR NOT NULL,
    storage_area VARCHAR NOT NULL,
    relative_path VARCHAR NOT NULL,
    size_bytes BIGINT NOT NULL,
    created_at TIMESTAMP NOT NULL,
    active BOOLEAN NOT NULL,
    pinned BOOLEAN NOT NULL
);

CREATE TABLE IF NOT EXISTS meta.dataset_quality_report (
    dataset_id VARCHAR NOT NULL,
    mapping_version INTEGER NOT NULL,
    total_rows BIGINT NOT NULL,
    valid_events BIGINT NOT NULL,
    invalid_events BIGINT NOT NULL,
    unique_cases BIGINT NOT NULL,
    unique_activities BIGINT NOT NULL,
    null_case_id BIGINT NOT NULL,
    empty_case_id BIGINT NOT NULL,
    null_activity BIGINT NOT NULL,
    empty_activity BIGINT NOT NULL,
    null_timestamp BIGINT NOT NULL,
    invalid_timestamp BIGINT NOT NULL,
    duplicate_events BIGINT NOT NULL,
    duplicate_timestamp_rows BIGINT NOT NULL,
    single_event_cases BIGINT NOT NULL,
    ambiguous_ordering_cases BIGINT NOT NULL DEFAULT 0,
    events_per_case_min BIGINT NOT NULL DEFAULT 0,
    events_per_case_median DOUBLE NOT NULL DEFAULT 0,
    events_per_case_p90 DOUBLE NOT NULL DEFAULT 0,
    events_per_case_max BIGINT NOT NULL DEFAULT 0,
    extremely_large_cases BIGINT NOT NULL DEFAULT 0,
    source_timezone_missing BOOLEAN NOT NULL DEFAULT FALSE,
    timestamps_outside_dataset_range BIGINT NOT NULL DEFAULT 0,
    outcome VARCHAR NOT NULL,
    measured_at TIMESTAMP NOT NULL,
    PRIMARY KEY (dataset_id, mapping_version)
);

ALTER TABLE meta.dataset_quality_report
    ADD COLUMN IF NOT EXISTS ambiguous_ordering_cases BIGINT DEFAULT 0;
ALTER TABLE meta.dataset_quality_report
    ADD COLUMN IF NOT EXISTS events_per_case_min BIGINT DEFAULT 0;
ALTER TABLE meta.dataset_quality_report
    ADD COLUMN IF NOT EXISTS events_per_case_median DOUBLE DEFAULT 0;
ALTER TABLE meta.dataset_quality_report
    ADD COLUMN IF NOT EXISTS events_per_case_p90 DOUBLE DEFAULT 0;
ALTER TABLE meta.dataset_quality_report
    ADD COLUMN IF NOT EXISTS events_per_case_max BIGINT DEFAULT 0;
ALTER TABLE meta.dataset_quality_report
    ADD COLUMN IF NOT EXISTS extremely_large_cases BIGINT DEFAULT 0;
ALTER TABLE meta.dataset_quality_report
    ADD COLUMN IF NOT EXISTS source_timezone_missing BOOLEAN DEFAULT FALSE;
ALTER TABLE meta.dataset_quality_report
    ADD COLUMN IF NOT EXISTS timestamps_outside_dataset_range BIGINT DEFAULT 0;

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
