from __future__ import annotations

import os
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import duckdb
from duckdb import DuckDBPyConnection
from fastapi import UploadFile

from app.config import Settings
from app.datasets.domain import (
    ActivityMappingSetRecord,
    ArtifactRecord,
    ColumnProfileRecord,
    DatasetRecord,
    MappingRecord,
    QualityReportRecord,
    SemanticContractRecord,
)
from app.datasets.errors import DatasetError
from app.datasets.normalizer import DatasetNormalizer, NormalizationArtifacts
from app.datasets.repository import DatasetRepository
from app.datasets.scanner import DatasetScanner
from app.datasets.storage import DatasetStorage
from app.schemas.datasets import (
    ActivityCoverageRow,
    ActivityMappingCoverage,
    ActivityMappingEntryResponse,
    ActivityMappingSetCreateRequest,
    ActivityMappingSetResponse,
    ArtifactDeleteResponse,
    ArtifactDiskUsage,
    ArtifactListResponse,
    ArtifactPinRequest,
    ArtifactResponse,
    ArtifactType,
    DataQualityReport,
    DatasetColumnProfile,
    DatasetFileType,
    DatasetPreviewResponse,
    DatasetProfileResponse,
    DatasetStatus,
    DatasetSummary,
    ImportMode,
    LocalImportRequest,
    MappingCreateRequest,
    MappingDefinitionResponse,
    NormalizationStatus,
    SemanticContractListResponse,
    SemanticContractResponse,
    TimestampPreview,
    UnmappedActivityPolicy,
)


class DatasetService:
    def __init__(self, connection: DuckDBPyConnection, settings: Settings) -> None:
        self._connection = connection
        self._settings = settings
        self._repository = DatasetRepository(connection)
        self._storage = DatasetStorage(settings)
        self._scanner = DatasetScanner(connection)

    async def upload(self, upload: UploadFile) -> DatasetSummary:
        original_filename, file_type, staged_filename = self._storage.validate_filename(
            upload.filename
        )
        dataset_id = str(uuid4())
        record = DatasetRecord(
            dataset_id=dataset_id,
            original_filename=original_filename,
            staged_filename=staged_filename,
            file_type=file_type,
            file_size_bytes=0,
            checksum=None,
            created_at=datetime.now(UTC),
            status=DatasetStatus.UPLOADING,
            row_count=None,
            column_count=None,
            schema_version=1,
            mapping_version=None,
            normalization_version=None,
            normalization_status=NormalizationStatus.NOT_STARTED,
            normalized_filename=None,
            normalized_file_size_bytes=None,
            quarantine_filename=None,
            quarantine_file_size_bytes=None,
            source_type="UPLOADED_FILE",
            error_code=None,
        )
        self._repository.create_dataset(record)
        try:
            size, checksum, source_path = await self._storage.write_upload(
                upload,
                dataset_id,
                staged_filename,
                file_type,
            )
            self._repository.update_staged_file(dataset_id, size, checksum)
            self._register_source_artifact(
                dataset_id,
                storage_area="STAGING",
                relative_path=self._storage.staging_relative_path(
                    dataset_id, staged_filename
                ),
                size=size,
            )
            self._profile_dataset(dataset_id, source_path, file_type)
            return dataset_summary(self._repository.require_dataset(dataset_id))
        except DatasetError:
            self._repository.mark_failed(dataset_id, "UPLOAD_FAILED")
            raise
        except (duckdb.Error, OSError, ValueError) as error:
            self._repository.mark_failed(dataset_id, "INVALID_SOURCE_FILE")
            raise DatasetError(
                "INVALID_SOURCE_FILE",
                "The file could not be scanned as the declared format",
            ) from error

    def import_local(self, request: LocalImportRequest) -> DatasetSummary:
        source, file_type, staged_filename = self._storage.resolve_local_import(
            request.path
        )
        mode = request.mode or ImportMode(self._settings.dataset_import.default_mode)
        dataset_id = str(uuid4())
        record = DatasetRecord(
            dataset_id=dataset_id,
            original_filename=source.name,
            staged_filename=staged_filename,
            file_type=file_type,
            file_size_bytes=0,
            checksum=None,
            created_at=datetime.now(UTC),
            status=DatasetStatus.UPLOADING,
            row_count=None,
            column_count=None,
            schema_version=1,
            mapping_version=None,
            normalization_version=None,
            normalization_status=NormalizationStatus.NOT_STARTED,
            normalized_filename=None,
            normalized_file_size_bytes=None,
            quarantine_filename=None,
            quarantine_file_size_bytes=None,
            source_type=f"LOCAL_{mode.value}",
            error_code=None,
            import_mode=mode,
        )
        self._repository.create_dataset(record)
        try:
            if mode == ImportMode.COPY:
                size, checksum, source_path = self._storage.stage_local_file(
                    source, dataset_id, staged_filename, file_type
                )
                self._repository.update_staged_file(dataset_id, size, checksum)
                artifact_area = "STAGING"
                artifact_path = self._storage.staging_relative_path(
                    dataset_id, staged_filename
                )
            else:
                size, mtime_ns, checksum = self._storage.inspect_local_source(source)
                source_path = source
                self._repository.update_reference_source(
                    dataset_id,
                    size=size,
                    checksum=checksum,
                    source_path=str(source),
                    source_mtime_ns=mtime_ns,
                )
                artifact_area = "EXTERNAL"
                artifact_path = source.name
            self._register_source_artifact(
                dataset_id,
                storage_area=artifact_area,
                relative_path=artifact_path,
                size=size,
            )
            self._profile_dataset(dataset_id, source_path, file_type)
            return dataset_summary(self._repository.require_dataset(dataset_id))
        except DatasetError:
            self._repository.mark_failed(dataset_id, "LOCAL_IMPORT_FAILED")
            raise
        except (duckdb.Error, OSError, ValueError) as error:
            self._repository.mark_failed(dataset_id, "INVALID_SOURCE_FILE")
            raise DatasetError(
                "INVALID_SOURCE_FILE",
                "The local file could not be scanned as the declared format",
            ) from error

    def register_staged_benchmark_file(
        self,
        source: Path,
        original_filename: str,
    ) -> DatasetRecord:
        record = self.stage_benchmark_file(source, original_filename)
        self.profile_staged_dataset(record.dataset_id)
        return self._repository.require_dataset(record.dataset_id)

    def stage_benchmark_file(
        self,
        source: Path,
        original_filename: str,
    ) -> DatasetRecord:
        safe_name, file_type, staged_filename = self._storage.validate_filename(
            original_filename
        )
        dataset_id = str(uuid4())
        record = DatasetRecord(
            dataset_id=dataset_id,
            original_filename=safe_name,
            staged_filename=staged_filename,
            file_type=file_type,
            file_size_bytes=0,
            checksum=None,
            created_at=datetime.now(UTC),
            status=DatasetStatus.UPLOADING,
            row_count=None,
            column_count=None,
            schema_version=1,
            mapping_version=None,
            normalization_version=None,
            normalization_status=NormalizationStatus.NOT_STARTED,
            normalized_filename=None,
            normalized_file_size_bytes=None,
            quarantine_filename=None,
            quarantine_file_size_bytes=None,
            source_type="UPLOADED_FILE",
            error_code=None,
        )
        self._repository.create_dataset(record)
        size, checksum, _staged_path = self._storage.stage_local_file(
            source,
            dataset_id,
            staged_filename,
            file_type,
        )
        self._repository.update_staged_file(dataset_id, size, checksum)
        self._register_source_artifact(
            dataset_id,
            storage_area="STAGING",
            relative_path=self._storage.staging_relative_path(
                dataset_id, staged_filename
            ),
            size=size,
        )
        return self._repository.require_dataset(dataset_id)

    def detect_staged_schema(self, dataset_id: str) -> list[tuple[str, str]]:
        dataset = self._require_dataset(dataset_id)
        return self._scanner.detect_schema(self._source_path(dataset), dataset.file_type)

    def profile_staged_dataset(
        self,
        dataset_id: str,
        schema: list[tuple[str, str]] | None = None,
    ) -> DatasetRecord:
        dataset = self._require_dataset(dataset_id)
        self._repository.transition_status(dataset_id, DatasetStatus.PROFILING)
        profile = self._scanner.profile(
            dataset_id,
            self._source_path(dataset),
            dataset.file_type,
            schema,
        )
        self._repository.save_profile(dataset_id, profile.row_count, profile.columns)
        return self._repository.require_dataset(dataset_id)

    def list_datasets(self) -> list[DatasetSummary]:
        return [dataset_summary(record) for record in self._repository.list_datasets()]

    def get_dataset(self, dataset_id: str) -> DatasetSummary:
        return dataset_summary(self._require_dataset(dataset_id))

    def get_profile(self, dataset_id: str) -> DatasetProfileResponse:
        dataset = self._require_dataset(dataset_id)
        columns = self._repository.get_profile(dataset_id)
        return DatasetProfileResponse(
            dataset=dataset_summary(dataset),
            columns=[column_profile(column) for column in columns],
        )

    def preview(self, dataset_id: str, requested_limit: int) -> DatasetPreviewResponse:
        dataset = self._require_dataset(dataset_id)
        if dataset.status in {
            DatasetStatus.UPLOADING,
            DatasetStatus.STAGED,
            DatasetStatus.PROFILING,
        }:
            raise DatasetError("DATASET_NOT_PROFILED", "Dataset profiling is not complete", 409)
        effective_limit = min(requested_limit, self._settings.quality.max_preview_rows)
        source_path = self._source_path(dataset)
        columns, rows = self._scanner.preview(
            source_path,
            dataset.file_type,
            effective_limit,
        )
        return DatasetPreviewResponse(
            columns=columns,
            rows=rows,
            returned_rows=len(rows),
            limit=effective_limit,
        )

    def create_mapping(
        self,
        dataset_id: str,
        request: MappingCreateRequest,
    ) -> MappingDefinitionResponse:
        dataset = self._require_dataset(dataset_id)
        if dataset.status not in {
            DatasetStatus.PROFILED,
            DatasetStatus.MAPPING_REQUIRED,
            DatasetStatus.READY,
            DatasetStatus.FAILED,
        }:
            raise DatasetError(
                "DATASET_NOT_PROFILED",
                "Dataset profiling must complete before mapping",
                409,
            )
        available_columns = {
            column.column_name for column in self._repository.get_profile(dataset_id)
        }
        selected_columns = {
            request.case_id_column,
            request.activity_column,
            request.timestamp_column,
            *request.optional_mappings.values(),
        }
        if request.event_id_column is not None:
            selected_columns.add(request.event_id_column)
        missing = selected_columns - available_columns
        if missing:
            raise DatasetError(
                "UNKNOWN_MAPPING_COLUMN",
                f"Unknown mapping columns: {', '.join(sorted(missing))}",
            )
        source_path = self._source_path(dataset)
        if request.timestamp_format is not None:
            try:
                self._scanner.validate_timestamp_format(
                    source_path,
                    dataset.file_type,
                    request.timestamp_column,
                    request.timestamp_format,
                )
            except duckdb.Error as error:
                raise DatasetError(
                    "INVALID_TIMESTAMP_FORMAT",
                    "The timestamp format could not be applied",
                    422,
                ) from error
        requires_timezone = self._scanner.timestamp_requires_source_timezone(
            source_path,
            dataset.file_type,
            request.timestamp_column,
        )
        if requires_timezone and request.timezone is None:
            raise DatasetError(
                "SOURCE_TIMEZONE_REQUIRED",
                "Naive timestamps require an explicit source timezone",
                422,
            )
        source_timezone = request.timezone or "UTC"
        display_timezone = request.display_timezone or source_timezone
        self._validate_timezone(source_timezone)
        self._validate_timezone(display_timezone)
        effective_request = request.model_copy(
            update={
                "timezone": source_timezone,
                "display_timezone": display_timezone,
            }
        )
        if effective_request.case_id_pseudonymized:
            self._pseudonymization_key(required=True)
        preview_candidate = MappingRecord(
            mapping_id="preview",
            dataset_id=dataset_id,
            version=0,
            case_id_column=effective_request.case_id_column,
            activity_column=effective_request.activity_column,
            timestamp_column=effective_request.timestamp_column,
            event_id_column=effective_request.event_id_column,
            optional_mappings=dict(effective_request.optional_mappings),
            timestamp_format=effective_request.timestamp_format,
            timezone=source_timezone,
            display_timezone=display_timezone,
            created_at=datetime.now(UTC),
        )
        try:
            preview = self._scanner.timestamp_preview(
                source_path,
                dataset.file_type,
                preview_candidate,
            )
        except duckdb.Error as error:
            raise DatasetError(
                "INVALID_TIMESTAMP_FORMAT",
                "The timestamp format could not be applied",
                422,
            ) from error
        self._connection.execute("BEGIN TRANSACTION")
        try:
            mapping = self._repository.create_mapping(dataset_id, effective_request)
            contract = self._repository.create_semantic_contract(
                dataset_id, mapping, effective_request
            )
            self._connection.execute("COMMIT")
        except Exception:
            self._connection.execute("ROLLBACK")
            raise
        return mapping_response(mapping, preview, contract)

    def create_semantic_contract(
        self,
        dataset_id: str,
        request: MappingCreateRequest,
    ) -> SemanticContractResponse:
        response = self.create_mapping(dataset_id, request)
        contracts = self._repository.list_semantic_contracts(dataset_id)
        contract = next(
            item
            for item in contracts
            if item.version == response.semantic_contract_version
        )
        return semantic_contract_response(contract, response.timestamp_preview, response)

    def list_semantic_contracts(self, dataset_id: str) -> SemanticContractListResponse:
        self._require_dataset(dataset_id)
        mappings = {
            mapping.version: mapping
            for mapping in self._list_mapping_records(dataset_id)
        }
        return SemanticContractListResponse(
            contracts=[
                semantic_contract_response(
                    contract,
                    [],
                    mapping_response(mappings[contract.mapping_version], [], contract),
                )
                for contract in self._repository.list_semantic_contracts(dataset_id)
            ]
        )

    def normalize(self, dataset_id: str) -> tuple[DatasetSummary, DataQualityReport]:
        dataset, quality, _artifacts = self.normalize_with_artifacts(dataset_id)
        return dataset, quality

    def normalize_with_artifacts(
        self,
        dataset_id: str,
    ) -> tuple[DatasetSummary, DataQualityReport, NormalizationArtifacts]:
        dataset = self._require_dataset(dataset_id)
        mapping = self._repository.get_latest_mapping(dataset_id)
        contract = self._repository.get_latest_semantic_contract(dataset_id)
        if mapping is None:
            raise DatasetError("MAPPING_REQUIRED", "Create an Event Log mapping first", 409)
        if contract is None or contract.mapping_version != mapping.version:
            raise DatasetError(
                "SEMANTIC_CONTRACT_REQUIRED",
                "Create a Semantic Contract for the active mapping first",
                409,
            )
        if dataset.status not in {
            DatasetStatus.MAPPING_REQUIRED,
            DatasetStatus.READY,
            DatasetStatus.FAILED,
        }:
            raise DatasetError(
                "DATASET_NOT_READY_FOR_VALIDATION",
                "Dataset cannot be normalized in its current state",
                409,
            )
        self._repository.transition_status(
            dataset_id,
            DatasetStatus.VALIDATING,
            normalization_status=NormalizationStatus.RUNNING,
        )
        self._repository.set_operation(dataset_id, "NORMALIZING")
        try:
            artifacts = DatasetNormalizer(self._connection, self._storage).normalize(
                dataset,
                mapping,
                contract,
                self._source_path(dataset),
                self._pseudonymization_key(
                    required=(
                        contract.case_id_pseudonymized
                        or any(
                            policy.value == "PSEUDONYMIZE"
                            for policy in contract.attribute_policies.values()
                        )
                    )
                ),
                self._settings.quality.large_case_event_threshold,
            )
            self._repository.save_quality_report(artifacts.quality)
            ready = artifacts.quality.valid_events > 0
            updated = self._repository.finish_normalization(
                dataset_id,
                normalized_filename=self._storage.relative_curated_path(
                    artifacts.normalized_path
                ),
                normalized_size=artifacts.normalized_path.stat().st_size,
                quarantine_filename=self._storage.relative_quarantine_path(
                    artifacts.quarantine_path
                ),
                quarantine_size=artifacts.quarantine_path.stat().st_size,
                ready=ready,
            )
            self._register_normalization_artifacts(updated, contract, artifacts)
            return (
                dataset_summary(updated),
                quality_response(artifacts.quality),
                artifacts,
            )
        except (duckdb.Error, OSError, ValueError) as error:
            self._repository.mark_failed(dataset_id, "NORMALIZATION_FAILED")
            raise DatasetError(
                "NORMALIZATION_FAILED",
                "Dataset normalization failed; the source file remains unchanged",
            ) from error
        finally:
            self._repository.set_operation(dataset_id, None)

    def get_quality(self, dataset_id: str) -> DataQualityReport:
        self._require_dataset(dataset_id)
        report = self._repository.get_quality_report(dataset_id)
        if report is None:
            raise DatasetError(
                "QUALITY_NOT_AVAILABLE",
                "Normalize the Dataset to create a quality report",
                404,
            )
        return quality_response(report)

    def create_activity_mapping_set(
        self,
        dataset_id: str,
        request: ActivityMappingSetCreateRequest,
    ) -> ActivityMappingSetResponse:
        dataset = self._require_dataset(dataset_id)
        if dataset.status != DatasetStatus.READY:
            raise DatasetError(
                "DATASET_NOT_READY",
                "Normalize the Dataset before creating activity mappings",
                409,
            )
        return activity_mapping_set_response(
            self._repository.create_activity_mapping_set(dataset_id, request)
        )

    def list_activity_mapping_sets(
        self, dataset_id: str
    ) -> list[ActivityMappingSetResponse]:
        self._require_dataset(dataset_id)
        return [
            activity_mapping_set_response(record)
            for record in self._repository.list_activity_mapping_sets(dataset_id)
        ]

    def activity_mapping_coverage(
        self,
        dataset_id: str,
        version: int,
    ) -> ActivityMappingCoverage:
        path, _mapping_version = self.normalized_path_for_analysis(dataset_id)
        mapping_set = self._repository.get_activity_mapping_set(dataset_id, version)
        if mapping_set is None:
            raise DatasetError(
                "ACTIVITY_MAPPING_NOT_FOUND",
                "Activity mapping version was not found",
                404,
            )
        rows = self._connection.execute(
            """
            WITH activity_counts AS (
                SELECT activity AS source_activity, count(*) AS event_count,
                       count(DISTINCT case_id) AS case_count
                FROM read_parquet(?)
                GROUP BY activity
            )
            SELECT a.source_activity, m.business_activity, a.event_count,
                   a.case_count, m.source_activity IS NOT NULL AS mapped
            FROM activity_counts a
            LEFT JOIN meta.activity_mapping_entry m
              ON m.mapping_set_id = ?
             AND m.enabled
             AND m.source_activity = a.source_activity
            ORDER BY a.event_count DESC, a.source_activity
            """,
            [str(path), mapping_set.mapping_set_id],
        ).fetchall()
        coverage_rows = [
            ActivityCoverageRow(
                source_activity=str(row[0]),
                business_activity=None if row[1] is None else str(row[1]),
                event_count=int(row[2]),
                case_count=int(row[3]),
                mapped=bool(row[4]),
            )
            for row in rows
        ]
        unique_count = len(coverage_rows)
        mapped_count = sum(row.mapped for row in coverage_rows)
        mapped_events = sum(row.event_count for row in coverage_rows if row.mapped)
        total_events = sum(row.event_count for row in coverage_rows)
        business_activities: set[str] = set()
        for row in coverage_rows:
            if row.mapped and row.business_activity is not None:
                business_activities.add(row.business_activity)
            elif mapping_set.unmapped_policy == UnmappedActivityPolicy.KEEP_SOURCE:
                business_activities.add(row.source_activity)
            elif mapping_set.unmapped_policy == UnmappedActivityPolicy.GROUP_AS_UNMAPPED:
                business_activities.add("__UNMAPPED__")
        return ActivityMappingCoverage(
            dataset_id=dataset_id,
            activity_mapping_version=version,
            unique_source_activities=unique_count,
            mapped_activities=mapped_count,
            unmapped_activities=unique_count - mapped_count,
            business_activities=len(business_activities),
            mapped_event_count=mapped_events,
            unmapped_event_count=total_events - mapped_events,
            activity_mapping_coverage=(mapped_count / unique_count if unique_count else 0),
            event_mapping_coverage=(mapped_events / total_events if total_events else 0),
            rows=coverage_rows,
        )

    def require_activity_mapping_set(
        self,
        dataset_id: str,
        requested_version: int | None,
    ) -> ActivityMappingSetRecord:
        dataset = self._require_dataset(dataset_id)
        version = requested_version or dataset.active_activity_mapping_version
        if version is None:
            raise DatasetError(
                "ACTIVITY_MAPPING_REQUIRED",
                "Create or select an Activity Mapping version",
                409,
            )
        mapping_set = self._repository.get_activity_mapping_set(dataset_id, version)
        if mapping_set is None:
            raise DatasetError(
                "ACTIVITY_MAPPING_NOT_FOUND",
                "Activity mapping version was not found",
                404,
            )
        return mapping_set

    def list_artifacts(self, dataset_id: str) -> ArtifactListResponse:
        self._require_dataset(dataset_id)
        artifacts = self._repository.list_artifacts(dataset_id)
        responses = [artifact_response(artifact) for artifact in artifacts]
        active_normalized = sum(
            item.size_bytes
            for item in artifacts
            if item.artifact_type == ArtifactType.NORMALIZED and item.active
        )
        active_quarantine = sum(
            item.size_bytes
            for item in artifacts
            if item.artifact_type == ArtifactType.QUARANTINE and item.active
        )
        previous = sum(
            item.size_bytes
            for item in artifacts
            if item.artifact_type in {ArtifactType.NORMALIZED, ArtifactType.QUARANTINE}
            and not item.active
        )
        raw = sum(
            item.size_bytes for item in artifacts if item.artifact_type == ArtifactType.SOURCE
        )
        temporary = sum(
            item.size_bytes
            for item in artifacts
            if item.artifact_type == ArtifactType.TEMPORARY
        )
        return ArtifactListResponse(
            artifacts=responses,
            disk_usage=ArtifactDiskUsage(
                raw_source=raw,
                normalized=active_normalized,
                quarantine=active_quarantine,
                previous_versions=previous,
                temporary=temporary,
                total=sum(item.size_bytes for item in artifacts),
            ),
        )

    def pin_artifact(
        self, dataset_id: str, artifact_id: str, request: ArtifactPinRequest
    ) -> ArtifactResponse:
        artifact = self._require_artifact(dataset_id, artifact_id)
        self._repository.set_artifact_pinned(dataset_id, artifact_id, request.pinned)
        return artifact_response(
            replace(artifact, pinned=request.pinned)
        )

    def delete_artifact(
        self, dataset_id: str, artifact_id: str
    ) -> ArtifactDeleteResponse:
        artifact = self._require_artifact(dataset_id, artifact_id)
        if artifact.artifact_type == ArtifactType.SOURCE:
            raise DatasetError(
                "SOURCE_ARTIFACT_PROTECTED",
                "Source artifacts can only be removed by deleting the Dataset",
                409,
            )
        if artifact.active:
            raise DatasetError(
                "ACTIVE_ARTIFACT_PROTECTED",
                "The active artifact cannot be deleted",
                409,
            )
        if artifact.pinned:
            raise DatasetError(
                "PINNED_ARTIFACT_PROTECTED",
                "Unpin the artifact before deletion",
                409,
            )
        path = self._storage.artifact_path(
            artifact.storage_area, artifact.relative_path
        )
        self._storage.remove_file(path)
        self._repository.delete_artifact(dataset_id, artifact_id)
        return ArtifactDeleteResponse(artifact_id=artifact_id, deleted=True)

    def delete(self, dataset_id: str) -> None:
        self._require_dataset(dataset_id)
        self._storage.cleanup_dataset(dataset_id)
        self._repository.delete_dataset(dataset_id)

    def normalized_path_for_analysis(self, dataset_id: str) -> tuple[Path, int]:
        dataset = self._require_dataset(dataset_id)
        if (
            dataset.status != DatasetStatus.READY
            or dataset.normalized_filename is None
            or dataset.mapping_version is None
        ):
            raise DatasetError(
                "DATASET_NOT_READY",
                "Dataset must be READY before analysis",
                409,
            )
        if dataset.import_mode == ImportMode.REFERENCE:
            self._source_path(dataset)
        path = self._storage.normalized_path(dataset.normalized_filename)
        if not path.is_file():
            raise DatasetError(
                "DATASET_FILE_MISSING",
                "The normalized Dataset file is unavailable",
                409,
            )
        return path, dataset.mapping_version

    def _validate_timezone(self, timezone: str) -> None:
        row = self._connection.execute(
            "SELECT count(*) = 1 FROM pg_timezone_names() WHERE name = ?",
            [timezone],
        ).fetchone()
        if row is None or not bool(row[0]):
            raise DatasetError(
                "INVALID_TIMEZONE",
                "Use a valid IANA timezone name",
                422,
            )

    def _pseudonymization_key(self, *, required: bool) -> bytes | None:
        value = os.environ.get(self._settings.security.pseudonymization_key_env)
        if value:
            return value.encode("utf-8")
        if required:
            raise DatasetError(
                "PSEUDONYMIZATION_KEY_UNAVAILABLE",
                "Pseudonymization is enabled but the configured local secret is unavailable",
                409,
            )
        return None

    def _register_source_artifact(
        self,
        dataset_id: str,
        *,
        storage_area: str,
        relative_path: str,
        size: int,
    ) -> None:
        self._repository.create_artifact(
            ArtifactRecord(
                artifact_id=str(uuid4()),
                dataset_id=dataset_id,
                semantic_contract_version=None,
                mapping_version=None,
                artifact_type=ArtifactType.SOURCE,
                storage_area=storage_area,
                relative_path=relative_path,
                size_bytes=size,
                created_at=datetime.now(UTC),
                active=True,
                pinned=True,
            )
        )

    def _register_normalization_artifacts(
        self,
        dataset: DatasetRecord,
        contract: SemanticContractRecord,
        artifacts: NormalizationArtifacts,
    ) -> None:
        for artifact_type, storage_area, path, relative_path in (
            (
                ArtifactType.NORMALIZED,
                "CURATED",
                artifacts.normalized_path,
                self._storage.relative_curated_path(artifacts.normalized_path),
            ),
            (
                ArtifactType.QUARANTINE,
                "QUARANTINE",
                artifacts.quarantine_path,
                self._storage.relative_quarantine_path(artifacts.quarantine_path),
            ),
        ):
            self._repository.create_artifact(
                ArtifactRecord(
                    artifact_id=str(uuid4()),
                    dataset_id=dataset.dataset_id,
                    semantic_contract_version=contract.version,
                    mapping_version=contract.mapping_version,
                    artifact_type=artifact_type,
                    storage_area=storage_area,
                    relative_path=relative_path,
                    size_bytes=path.stat().st_size,
                    created_at=datetime.now(UTC),
                    active=True,
                    pinned=False,
                )
            )

    def _require_artifact(self, dataset_id: str, artifact_id: str) -> ArtifactRecord:
        self._require_dataset(dataset_id)
        artifact = self._repository.get_artifact(dataset_id, artifact_id)
        if artifact is None:
            raise DatasetError("ARTIFACT_NOT_FOUND", "Artifact was not found", 404)
        return artifact

    def _list_mapping_records(self, dataset_id: str) -> list[MappingRecord]:
        return self._repository.list_mappings(dataset_id)

    def _profile_dataset(
        self,
        dataset_id: str,
        source_path: Path,
        file_type: DatasetFileType,
    ) -> None:
        self._repository.transition_status(dataset_id, DatasetStatus.PROFILING)
        profile = self._scanner.profile(dataset_id, source_path, file_type)
        self._repository.save_profile(dataset_id, profile.row_count, profile.columns)

    def _source_path(self, dataset: DatasetRecord) -> Path:
        if dataset.import_mode == ImportMode.REFERENCE:
            if dataset.source_path is None:
                raise DatasetError(
                    "SOURCE_FILE_MISSING",
                    "The referenced source file is unavailable",
                    409,
                )
            try:
                path, file_type, _staged_name = self._storage.resolve_local_import(
                    dataset.source_path
                )
                stat = path.stat()
                changed = (
                    file_type != dataset.file_type
                    or stat.st_size != dataset.file_size_bytes
                    or stat.st_mtime_ns != dataset.source_mtime_ns
                    or self._storage.hash_file(path) != dataset.checksum
                )
            except DatasetError:
                self._repository.mark_source_changed(dataset.dataset_id)
                raise DatasetError(
                    "SOURCE_CHANGED",
                    "The referenced source file is missing, changed, or no longer allowed",
                    409,
                ) from None
            if changed:
                self._repository.mark_source_changed(dataset.dataset_id)
                raise DatasetError(
                    "SOURCE_CHANGED",
                    "The referenced source file changed after import",
                    409,
                )
            return path
        path = self._storage.staged_path(
            dataset.dataset_id,
            dataset.staged_filename,
        )
        if not path.is_file() or path.stat().st_size != dataset.file_size_bytes:
            raise DatasetError(
                "SOURCE_FILE_MISSING",
                "The staged source file is unavailable or changed",
                409,
            )
        return path

    def _require_dataset(self, dataset_id: str) -> DatasetRecord:
        try:
            return self._repository.require_dataset(dataset_id)
        except KeyError as error:
            raise DatasetError("NOT_FOUND", "Dataset was not found", 404) from error


def dataset_summary(record: DatasetRecord) -> DatasetSummary:
    return DatasetSummary(
        dataset_id=record.dataset_id,
        original_filename=record.original_filename,
        file_type=record.file_type,
        file_size_bytes=record.file_size_bytes,
        checksum=record.checksum,
        created_at=record.created_at,
        status=record.status,
        row_count=record.row_count,
        column_count=record.column_count,
        schema_version=record.schema_version,
        mapping_version=record.mapping_version,
        normalization_version=record.normalization_version,
        normalization_status=record.normalization_status,
        normalized_file_size_bytes=record.normalized_file_size_bytes,
        quarantine_file_size_bytes=record.quarantine_file_size_bytes,
        source_type=record.source_type,
        error_code=record.error_code,
        semantic_contract_version=record.semantic_contract_version,
        active_activity_mapping_version=record.active_activity_mapping_version,
        import_mode=record.import_mode,
        current_step=record.current_step,
        operation_started_at=record.operation_started_at,
        data_ready=record.status == DatasetStatus.READY,
        semantic_ready=record.semantic_contract_version is not None,
        analysis_ready=(
            record.status == DatasetStatus.READY
            and record.semantic_contract_version is not None
        ),
    )


def column_profile(record: ColumnProfileRecord) -> DatasetColumnProfile:
    return DatasetColumnProfile(
        ordinal_position=record.ordinal_position,
        column_name=record.column_name,
        inferred_type=record.inferred_type,
        nullable_observed=record.null_count > 0,
        null_count=record.null_count,
        approx_distinct=record.approx_distinct,
        min_value=record.min_value,
        max_value=record.max_value,
        sample_values=list(record.sample_values),
    )


def mapping_response(
    record: MappingRecord,
    timestamp_preview: list[TimestampPreview],
    contract: SemanticContractRecord | None = None,
) -> MappingDefinitionResponse:
    return MappingDefinitionResponse(
        mapping_id=record.mapping_id,
        dataset_id=record.dataset_id,
        version=record.version,
        case_id_column=record.case_id_column,
        activity_column=record.activity_column,
        timestamp_column=record.timestamp_column,
        event_id_column=record.event_id_column,
        optional_mappings=dict(record.optional_mappings),
        timestamp_format=record.timestamp_format,
        timezone=record.timezone,
        display_timezone=record.display_timezone,
        created_at=record.created_at,
        timestamp_preview=timestamp_preview,
        semantic_contract_id=contract.contract_id if contract else None,
        semantic_contract_version=contract.version if contract else None,
    )


def quality_response(record: QualityReportRecord) -> DataQualityReport:
    return DataQualityReport(
        dataset_id=record.dataset_id,
        mapping_version=record.mapping_version,
        total_rows=record.total_rows,
        valid_events=record.valid_events,
        invalid_events=record.invalid_events,
        unique_cases=record.unique_cases,
        unique_activities=record.unique_activities,
        null_case_id=record.null_case_id,
        empty_case_id=record.empty_case_id,
        null_activity=record.null_activity,
        empty_activity=record.empty_activity,
        null_timestamp=record.null_timestamp,
        invalid_timestamp=record.invalid_timestamp,
        duplicate_events=record.duplicate_events,
        duplicate_timestamp_rows=record.duplicate_timestamp_rows,
        single_event_cases=record.single_event_cases,
        ambiguous_ordering_cases=record.ambiguous_ordering_cases,
        events_per_case_min=record.events_per_case_min,
        events_per_case_median=record.events_per_case_median,
        events_per_case_p90=record.events_per_case_p90,
        events_per_case_max=record.events_per_case_max,
        extremely_large_cases=record.extremely_large_cases,
        source_timezone_missing=record.source_timezone_missing,
        timestamps_outside_dataset_range=record.timestamps_outside_dataset_range,
        technical_quality=record.outcome,
        semantic_quality=(
            "WARNING_AMBIGUOUS_ORDERING"
            if record.ambiguous_ordering_cases > 0
            else "PASSED"
        ),
        outcome=record.outcome,
        measured_at=record.measured_at,
    )


def semantic_contract_response(
    contract: SemanticContractRecord,
    timestamp_preview: list[TimestampPreview],
    mapping: MappingDefinitionResponse,
) -> SemanticContractResponse:
    return SemanticContractResponse(
        contract_id=contract.contract_id,
        dataset_id=contract.dataset_id,
        version=contract.version,
        mapping_version=contract.mapping_version,
        case_id_column=mapping.case_id_column,
        activity_column=mapping.activity_column,
        timestamp_column=mapping.timestamp_column,
        case_null_policy=contract.case_null_policy,
        case_empty_policy=contract.case_empty_policy,
        case_id_pseudonymized=contract.case_id_pseudonymized,
        case_id_classification=contract.case_id_classification,
        source_timezone=contract.source_timezone,
        display_timezone=contract.display_timezone,
        normalized_timezone=contract.normalized_timezone,
        ordering_fields=list(contract.ordering_fields),
        attribute_policies=dict(contract.attribute_policies),
        pii_classifications=dict(contract.pii_classifications),
        business_activity_mapping_version=contract.business_activity_mapping_version,
        created_at=contract.created_at,
        status=contract.status,
        timestamp_preview=timestamp_preview,
    )


def activity_mapping_set_response(
    record: ActivityMappingSetRecord,
) -> ActivityMappingSetResponse:
    return ActivityMappingSetResponse(
        mapping_set_id=record.mapping_set_id,
        dataset_id=record.dataset_id,
        version=record.version,
        name=record.name,
        unmapped_policy=record.unmapped_policy,
        created_at=record.created_at,
        status=record.status,
        entries=[
            ActivityMappingEntryResponse(
                source_activity=entry.source_activity,
                business_activity=entry.business_activity,
                description=entry.description,
                enabled=entry.enabled,
            )
            for entry in record.entries
        ],
    )


def artifact_response(record: ArtifactRecord) -> ArtifactResponse:
    return ArtifactResponse(
        artifact_id=record.artifact_id,
        dataset_id=record.dataset_id,
        semantic_contract_version=record.semantic_contract_version,
        mapping_version=record.mapping_version,
        artifact_type=record.artifact_type,
        path=record.relative_path,
        size_bytes=record.size_bytes,
        created_at=record.created_at,
        active=record.active,
        pinned=record.pinned,
    )
