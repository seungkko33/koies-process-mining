from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from app.datasets.domain import ActivityMappingSetRecord
from app.schemas.datasets import UnmappedActivityPolicy


@dataclass(frozen=True)
class EventSource:
    relation_sql: str
    parameters: tuple[object, ...]
    signature: str
    mapping_version: str
    dataset_id: str | None = None
    semantic_contract_version: str | None = None
    activity_mapping_version: str | None = None
    normalization_version: str | None = None
    activity_level: str = "source"

    @classmethod
    def default_table(cls) -> EventSource:
        return cls(
            relation_sql="(SELECT *, event_id AS source_event_id FROM curated.event_log)",
            parameters=(),
            signature="all-events",
            mapping_version="all",
        )

    @classmethod
    def normalized_parquet(
        cls,
        path: Path,
        dataset_id: str,
        mapping_version: int,
        semantic_contract_version: int | None = None,
        normalization_version: str = "event-log-v1",
    ) -> EventSource:
        return cls(
            relation_sql="read_parquet(?)",
            parameters=(str(path),),
            signature=f"dataset={dataset_id}",
            mapping_version=f"mapping-v{mapping_version}",
            dataset_id=dataset_id,
            semantic_contract_version=(
                None
                if semantic_contract_version is None
                else f"contract-v{semantic_contract_version}"
            ),
            normalization_version=normalization_version,
        )

    @classmethod
    def business_activity_parquet(
        cls,
        path: Path,
        dataset_id: str,
        mapping_version: int,
        semantic_contract_version: int,
        normalization_version: str,
        mapping_set: ActivityMappingSetRecord,
    ) -> EventSource:
        if mapping_set.unmapped_policy == UnmappedActivityPolicy.GROUP_AS_UNMAPPED:
            activity_expression = "coalesce(m.business_activity, '__UNMAPPED__')"
            where_clause = "TRUE"
        elif mapping_set.unmapped_policy == UnmappedActivityPolicy.EXCLUDE:
            activity_expression = "m.business_activity"
            where_clause = "m.source_activity IS NOT NULL"
        else:
            activity_expression = "coalesce(m.business_activity, e.activity)"
            where_clause = "TRUE"
        return cls(
            relation_sql=f"""(
                SELECT e.* EXCLUDE (activity), {activity_expression} AS activity
                FROM read_parquet(?) e
                LEFT JOIN meta.activity_mapping_entry m
                  ON m.mapping_set_id = ?
                 AND m.enabled
                 AND m.source_activity = e.activity
                WHERE {where_clause}
            )""",
            parameters=(str(path), mapping_set.mapping_set_id),
            signature=(
                f"dataset={dataset_id};activity-level=business;"
                f"activity-mapping-v{mapping_set.version};"
                f"unmapped={mapping_set.unmapped_policy.value}"
            ),
            mapping_version=f"mapping-v{mapping_version}",
            dataset_id=dataset_id,
            semantic_contract_version=f"contract-v{semantic_contract_version}",
            activity_mapping_version=f"activity-mapping-v{mapping_set.version}",
            normalization_version=normalization_version,
            activity_level="business",
        )
