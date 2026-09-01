from __future__ import annotations

from typing import Annotated
from uuid import UUID

from duckdb import DuckDBPyConnection
from fastapi import APIRouter, Depends, File, Query, Request, UploadFile, status

from app.api.dependencies import get_connection
from app.config import Settings
from app.datasets.service import DatasetService
from app.schemas.datasets import (
    ActivityMappingCoverage,
    ActivityMappingSetCreateRequest,
    ActivityMappingSetListResponse,
    ActivityMappingSetResponse,
    ArtifactDeleteResponse,
    ArtifactListResponse,
    ArtifactPinRequest,
    ArtifactResponse,
    DataQualityReport,
    DatasetListResponse,
    DatasetPreviewResponse,
    DatasetProfileResponse,
    DatasetSummary,
    DeleteDatasetResponse,
    LocalImportRequest,
    MappingCreateRequest,
    MappingDefinitionResponse,
    NormalizationResponse,
    SemanticContractListResponse,
    SemanticContractResponse,
)

router = APIRouter(prefix="/api/datasets", tags=["datasets"])


def _service(request: Request, connection: DuckDBPyConnection) -> DatasetService:
    settings: Settings = request.app.state.settings
    return DatasetService(connection, settings)


@router.post(
    "/upload",
    response_model=DatasetSummary,
    status_code=status.HTTP_201_CREATED,
)
async def upload_dataset(
    request: Request,
    connection: Annotated[DuckDBPyConnection, Depends(get_connection)],
    file: Annotated[UploadFile, File()],
) -> DatasetSummary:
    return await _service(request, connection).upload(file)


@router.post(
    "/import-local",
    response_model=DatasetSummary,
    status_code=status.HTTP_201_CREATED,
)
def import_local_dataset(
    payload: LocalImportRequest,
    request: Request,
    connection: Annotated[DuckDBPyConnection, Depends(get_connection)],
) -> DatasetSummary:
    return _service(request, connection).import_local(payload)


@router.get("", response_model=DatasetListResponse)
def list_datasets(
    request: Request,
    connection: Annotated[DuckDBPyConnection, Depends(get_connection)],
) -> DatasetListResponse:
    return DatasetListResponse(datasets=_service(request, connection).list_datasets())


@router.get("/{dataset_id}", response_model=DatasetSummary)
def get_dataset(
    dataset_id: UUID,
    request: Request,
    connection: Annotated[DuckDBPyConnection, Depends(get_connection)],
) -> DatasetSummary:
    return _service(request, connection).get_dataset(str(dataset_id))


@router.get("/{dataset_id}/profile", response_model=DatasetProfileResponse)
def get_dataset_profile(
    dataset_id: UUID,
    request: Request,
    connection: Annotated[DuckDBPyConnection, Depends(get_connection)],
) -> DatasetProfileResponse:
    return _service(request, connection).get_profile(str(dataset_id))


@router.get("/{dataset_id}/preview", response_model=DatasetPreviewResponse)
def preview_dataset(
    dataset_id: UUID,
    request: Request,
    connection: Annotated[DuckDBPyConnection, Depends(get_connection)],
    limit: Annotated[int, Query(ge=1)] = 100,
) -> DatasetPreviewResponse:
    return _service(request, connection).preview(str(dataset_id), limit)


@router.post("/{dataset_id}/mappings", response_model=MappingDefinitionResponse)
def create_dataset_mapping(
    dataset_id: UUID,
    mapping: MappingCreateRequest,
    request: Request,
    connection: Annotated[DuckDBPyConnection, Depends(get_connection)],
) -> MappingDefinitionResponse:
    return _service(request, connection).create_mapping(str(dataset_id), mapping)


@router.post(
    "/{dataset_id}/semantic-contracts",
    response_model=SemanticContractResponse,
)
def create_semantic_contract(
    dataset_id: UUID,
    contract: MappingCreateRequest,
    request: Request,
    connection: Annotated[DuckDBPyConnection, Depends(get_connection)],
) -> SemanticContractResponse:
    return _service(request, connection).create_semantic_contract(
        str(dataset_id), contract
    )


@router.get(
    "/{dataset_id}/semantic-contracts",
    response_model=SemanticContractListResponse,
)
def list_semantic_contracts(
    dataset_id: UUID,
    request: Request,
    connection: Annotated[DuckDBPyConnection, Depends(get_connection)],
) -> SemanticContractListResponse:
    return _service(request, connection).list_semantic_contracts(str(dataset_id))


@router.post(
    "/{dataset_id}/activity-mappings",
    response_model=ActivityMappingSetResponse,
)
def create_activity_mapping_set(
    dataset_id: UUID,
    payload: ActivityMappingSetCreateRequest,
    request: Request,
    connection: Annotated[DuckDBPyConnection, Depends(get_connection)],
) -> ActivityMappingSetResponse:
    return _service(request, connection).create_activity_mapping_set(
        str(dataset_id), payload
    )


@router.get(
    "/{dataset_id}/activity-mappings",
    response_model=ActivityMappingSetListResponse,
)
def list_activity_mapping_sets(
    dataset_id: UUID,
    request: Request,
    connection: Annotated[DuckDBPyConnection, Depends(get_connection)],
) -> ActivityMappingSetListResponse:
    return ActivityMappingSetListResponse(
        mapping_sets=_service(request, connection).list_activity_mapping_sets(
            str(dataset_id)
        )
    )


@router.get(
    "/{dataset_id}/activity-mappings/{version}/coverage",
    response_model=ActivityMappingCoverage,
)
def activity_mapping_coverage(
    dataset_id: UUID,
    version: int,
    request: Request,
    connection: Annotated[DuckDBPyConnection, Depends(get_connection)],
) -> ActivityMappingCoverage:
    return _service(request, connection).activity_mapping_coverage(
        str(dataset_id), version
    )


@router.get("/{dataset_id}/artifacts", response_model=ArtifactListResponse)
def list_artifacts(
    dataset_id: UUID,
    request: Request,
    connection: Annotated[DuckDBPyConnection, Depends(get_connection)],
) -> ArtifactListResponse:
    return _service(request, connection).list_artifacts(str(dataset_id))


@router.patch(
    "/{dataset_id}/artifacts/{artifact_id}/pin",
    response_model=ArtifactResponse,
)
def pin_artifact(
    dataset_id: UUID,
    artifact_id: UUID,
    payload: ArtifactPinRequest,
    request: Request,
    connection: Annotated[DuckDBPyConnection, Depends(get_connection)],
) -> ArtifactResponse:
    return _service(request, connection).pin_artifact(
        str(dataset_id), str(artifact_id), payload
    )


@router.delete(
    "/{dataset_id}/artifacts/{artifact_id}",
    response_model=ArtifactDeleteResponse,
)
def delete_artifact(
    dataset_id: UUID,
    artifact_id: UUID,
    request: Request,
    connection: Annotated[DuckDBPyConnection, Depends(get_connection)],
) -> ArtifactDeleteResponse:
    return _service(request, connection).delete_artifact(
        str(dataset_id), str(artifact_id)
    )


@router.post("/{dataset_id}/normalize", response_model=NormalizationResponse)
def normalize_dataset(
    dataset_id: UUID,
    request: Request,
    connection: Annotated[DuckDBPyConnection, Depends(get_connection)],
) -> NormalizationResponse:
    dataset, quality = _service(request, connection).normalize(str(dataset_id))
    return NormalizationResponse(dataset=dataset, quality=quality)


@router.get("/{dataset_id}/quality", response_model=DataQualityReport)
def get_dataset_quality(
    dataset_id: UUID,
    request: Request,
    connection: Annotated[DuckDBPyConnection, Depends(get_connection)],
) -> DataQualityReport:
    return _service(request, connection).get_quality(str(dataset_id))


@router.delete("/{dataset_id}", response_model=DeleteDatasetResponse)
def delete_dataset(
    dataset_id: UUID,
    request: Request,
    connection: Annotated[DuckDBPyConnection, Depends(get_connection)],
) -> DeleteDatasetResponse:
    normalized_id = str(dataset_id)
    _service(request, connection).delete(normalized_id)
    return DeleteDatasetResponse(dataset_id=normalized_id, deleted=True)
