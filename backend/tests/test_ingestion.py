from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

import duckdb
import httpx
import pytest
from app.config import Settings, load_settings
from app.datasets.domain import require_status_transition
from app.main import create_app
from app.schemas.datasets import DatasetStatus

FIXTURE_DIR = Path(__file__).parent / "fixtures"
VALID_CSV = FIXTURE_DIR / "valid_event_log.csv"
INVALID_CSV = FIXTURE_DIR / "invalid_event_log.csv"
VALID_PARQUET = FIXTURE_DIR / "valid_event_log.parquet"


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


def isolated_settings(tmp_path: Path) -> Settings:
    settings = load_settings()
    return settings.model_copy(
        update={
            "data": settings.data.model_copy(
                update={
                    "staging_dir": tmp_path / "staging",
                    "raw_dir": tmp_path / "raw",
                    "raw_parquet_dir": tmp_path / "parquet-raw",
                    "curated_dir": tmp_path / "curated",
                    "quarantine_dir": tmp_path / "quarantine",
                    "temp_dir": tmp_path / "temp",
                    "database_path": tmp_path / "ingestion-test.duckdb",
                }
            ),
            "duckdb": settings.duckdb.model_copy(
                update={"temp_directory": tmp_path / "duckdb-temp"}
            ),
        }
    )


@asynccontextmanager
async def ingestion_client(
    tmp_path: Path,
) -> AsyncIterator[tuple[httpx.AsyncClient, Settings]]:
    settings = isolated_settings(tmp_path)
    application = create_app(settings)
    async with application.router.lifespan_context(application):
        transport = httpx.ASGITransport(app=application)
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://test",
        ) as client:
            yield client, settings


async def upload_fixture(
    client: httpx.AsyncClient,
    path: Path,
    *,
    filename: str | None = None,
) -> dict[str, object]:
    response = await client.post(
        "/api/datasets/upload",
        files={
            "file": (
                filename or path.name,
                path.read_bytes(),
                "application/octet-stream",
            )
        },
    )
    assert response.status_code == 201, response.text
    payload: dict[str, object] = response.json()
    return payload


async def create_golden_mapping(
    client: httpx.AsyncClient,
    dataset_id: str,
) -> httpx.Response:
    return await client.post(
        f"/api/datasets/{dataset_id}/mappings",
        json={
            "case_id_column": "case_id",
            "activity_column": "activity",
            "timestamp_column": "event_ts",
            "event_id_column": "event_id",
            "optional_mappings": {"source_sequence": "source_sequence"},
            "timezone": "Asia/Seoul",
        },
    )


@pytest.mark.anyio
async def test_csv_upload_profile_mapping_normalize_and_existing_analytics(
    tmp_path: Path,
) -> None:
    async with ingestion_client(tmp_path) as (client, settings):
        uploaded = await upload_fixture(client, VALID_CSV)
        dataset_id = str(uploaded["dataset_id"])

        assert uploaded["status"] == "MAPPING_REQUIRED"
        assert uploaded["row_count"] == 10
        assert uploaded["column_count"] == 5
        assert uploaded["checksum"]

        profile = await client.get(f"/api/datasets/{dataset_id}/profile")
        preview = await client.get(
            f"/api/datasets/{dataset_id}/preview?limit=999"
        )
        assert profile.status_code == 200
        profile_payload = profile.json()
        columns = {column["column_name"]: column for column in profile_payload["columns"]}
        assert columns["event_ts"]["inferred_type"] == "TIMESTAMP"
        assert columns["case_id"]["approx_distinct"] == 3
        assert preview.status_code == 200
        assert preview.json()["limit"] == 200
        assert preview.json()["returned_rows"] == 10

        mapping = await create_golden_mapping(client, dataset_id)
        assert mapping.status_code == 200, mapping.text
        assert mapping.json()["version"] == 1
        assert mapping.json()["timezone"] == "Asia/Seoul"
        assert mapping.json()["timestamp_preview"][0]["parsed_value"] is not None

        normalized = await client.post(f"/api/datasets/{dataset_id}/normalize")
        assert normalized.status_code == 200, normalized.text
        normalized_payload = normalized.json()
        assert normalized_payload["dataset"]["status"] == "READY"
        assert normalized_payload["quality"]["total_rows"] == 10
        assert normalized_payload["quality"]["valid_events"] == 10
        assert normalized_payload["quality"]["invalid_events"] == 0
        assert normalized_payload["quality"]["single_event_cases"] == 0

        overview = await client.get(f"/api/overview?dataset_id={dataset_id}")
        dfg = await client.get(f"/api/dfg?dataset_id={dataset_id}")
        assert overview.status_code == 200, overview.text
        assert overview.json()["data"]["case_count"] == 3
        assert overview.json()["data"]["event_count"] == 10
        assert dfg.status_code == 200, dfg.text
        assert dfg.json()["data"]["node_count"] == 4
        assert dfg.json()["data"]["edge_count"] == 5
        assert dfg.json()["data"]["edges"][0]["transition_count"] == 2
        assert dfg.json()["meta"]["mapping_version"] == "mapping-v1"

        normalized_path = settings.data.curated_dir / dataset_id / "events-v1.parquet"
        assert normalized_path.is_file()
        with duckdb.connect() as connection:
            assert connection.execute(
                "SELECT count(*) FROM read_parquet(?)",
                [str(normalized_path)],
            ).fetchone() == (10,)


@pytest.mark.anyio
async def test_parquet_upload_uses_the_same_pipeline(tmp_path: Path) -> None:
    async with ingestion_client(tmp_path) as (client, _settings):
        uploaded = await upload_fixture(client, VALID_PARQUET)
        dataset_id = str(uploaded["dataset_id"])
        assert uploaded["file_type"] == "PARQUET"
        assert uploaded["row_count"] == 10

        mapping = await create_golden_mapping(client, dataset_id)
        normalized = await client.post(f"/api/datasets/{dataset_id}/normalize")

        assert mapping.status_code == 200
        assert normalized.status_code == 200, normalized.text
        assert normalized.json()["dataset"]["status"] == "READY"
        assert normalized.json()["quality"]["valid_events"] == 10


@pytest.mark.anyio
async def test_invalid_rows_are_reported_and_quarantined(tmp_path: Path) -> None:
    async with ingestion_client(tmp_path) as (client, settings):
        uploaded = await upload_fixture(client, INVALID_CSV)
        dataset_id = str(uploaded["dataset_id"])
        mapping = await create_golden_mapping(client, dataset_id)
        assert mapping.status_code == 200

        normalized = await client.post(f"/api/datasets/{dataset_id}/normalize")
        assert normalized.status_code == 200, normalized.text
        quality = normalized.json()["quality"]
        assert quality["total_rows"] == 9
        assert quality["valid_events"] == 2
        assert quality["invalid_events"] == 7
        assert quality["null_case_id"] == 1
        assert quality["empty_case_id"] == 1
        assert quality["null_activity"] == 1
        assert quality["empty_activity"] == 1
        assert quality["invalid_timestamp"] == 1
        assert quality["duplicate_events"] == 2
        assert quality["outcome"] == "PASSED_WITH_QUARANTINE"
        assert normalized.json()["dataset"]["status"] == "READY"

        quarantine_path = (
            settings.data.quarantine_dir / dataset_id / "quarantine-v1.parquet"
        )
        with duckdb.connect() as connection:
            rows = connection.execute(
                "SELECT failure_code FROM read_parquet(?) ORDER BY source_row_number",
                [str(quarantine_path)],
            ).fetchall()
        assert len(rows) == 7
        assert any("INVALID_TIMESTAMP" in str(row[0]) for row in rows)
        assert any("DUPLICATE_EVENT" in str(row[0]) for row in rows)


@pytest.mark.anyio
async def test_unsupported_and_traversal_filenames_leave_no_staging_orphan(
    tmp_path: Path,
) -> None:
    async with ingestion_client(tmp_path) as (client, settings):
        unsupported = await client.post(
            "/api/datasets/upload",
            files={"file": ("events.xlsx", b"not-excel", "application/octet-stream")},
        )
        traversal = await client.post(
            "/api/datasets/upload",
            files={"file": ("../events.csv", b"a,b\n1,2\n", "text/csv")},
        )
        datasets = await client.get("/api/datasets")

        assert unsupported.status_code == 415
        assert unsupported.json()["detail"]["code"] == "UNSUPPORTED_FILE_TYPE"
        assert traversal.status_code == 400
        assert traversal.json()["detail"]["code"] == "INVALID_FILENAME"
        assert datasets.json()["datasets"] == []
        assert not settings.data.staging_dir.exists()


@pytest.mark.anyio
async def test_invalid_parquet_signature_records_failed_state_without_file(
    tmp_path: Path,
) -> None:
    async with ingestion_client(tmp_path) as (client, settings):
        response = await client.post(
            "/api/datasets/upload",
            files={"file": ("broken.parquet", b"not parquet", "application/octet-stream")},
        )
        datasets = await client.get("/api/datasets")

        assert response.status_code == 422
        assert response.json()["detail"]["code"] == "INVALID_PARQUET"
        records = datasets.json()["datasets"]
        assert len(records) == 1
        assert records[0]["status"] == "FAILED"
        assert list(settings.data.staging_dir.glob("*")) == []


@pytest.mark.anyio
async def test_preview_is_server_bounded_to_configured_maximum(tmp_path: Path) -> None:
    header = b"event_id,case_id,activity,event_ts,source_sequence\n"
    rows = b"".join(
        f"event-{index},case-{index},A,2026-01-01T00:00:00,{index}\n".encode()
        for index in range(250)
    )
    async with ingestion_client(tmp_path) as (client, _settings):
        response = await client.post(
            "/api/datasets/upload",
            files={"file": ("preview.csv", header + rows, "text/csv")},
        )
        assert response.status_code == 201, response.text
        dataset_id = response.json()["dataset_id"]

        preview = await client.get(f"/api/datasets/{dataset_id}/preview?limit=10000")

        assert preview.status_code == 200
        assert preview.json()["limit"] == 200
        assert preview.json()["returned_rows"] == 200


@pytest.mark.anyio
async def test_invalid_timestamp_format_is_rejected_before_mapping_is_saved(
    tmp_path: Path,
) -> None:
    async with ingestion_client(tmp_path) as (client, _settings):
        uploaded = await upload_fixture(client, VALID_CSV)
        dataset_id = str(uploaded["dataset_id"])

        response = await client.post(
            f"/api/datasets/{dataset_id}/mappings",
            json={
                "case_id_column": "case_id",
                "activity_column": "activity",
                "timestamp_column": "event_ts",
                "timestamp_format": "%Q",
            },
        )
        dataset = await client.get(f"/api/datasets/{dataset_id}")

        assert response.status_code == 422
        assert response.json()["detail"]["code"] == "INVALID_TIMESTAMP_FORMAT"
        assert dataset.json()["mapping_version"] is None


@pytest.mark.anyio
async def test_delete_removes_metadata_and_all_dataset_artifacts(tmp_path: Path) -> None:
    async with ingestion_client(tmp_path) as (client, settings):
        uploaded = await upload_fixture(client, VALID_CSV)
        dataset_id = str(uploaded["dataset_id"])
        assert (await create_golden_mapping(client, dataset_id)).status_code == 200
        assert (
            await client.post(f"/api/datasets/{dataset_id}/normalize")
        ).status_code == 200

        response = await client.delete(f"/api/datasets/{dataset_id}")

        assert response.status_code == 200
        assert response.json() == {"dataset_id": dataset_id, "deleted": True}
        assert (await client.get(f"/api/datasets/{dataset_id}")).status_code == 404
        for root in (
            settings.data.staging_dir,
            settings.data.curated_dir,
            settings.data.quarantine_dir,
            settings.data.temp_dir,
        ):
            assert not (root / dataset_id).exists()


def test_dataset_state_machine_rejects_invalid_transition() -> None:
    require_status_transition(DatasetStatus.UPLOADING, DatasetStatus.STAGED)
    with pytest.raises(ValueError, match="invalid dataset status transition"):
        require_status_transition(DatasetStatus.UPLOADING, DatasetStatus.READY)
