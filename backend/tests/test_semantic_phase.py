from __future__ import annotations

import hashlib
import hmac
import os
from pathlib import Path

import duckdb
import httpx
import pytest
from app.datasets.normalizer import DatasetNormalizer
from app.main import create_app
from app.schemas.datasets import MappingCreateRequest
from pydantic import ValidationError

from .test_ingestion import FIXTURE_DIR, ingestion_client, isolated_settings, upload_fixture

SEMANTIC_CSV = FIXTURE_DIR / "semantic_event_log.csv"


def contract_payload(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "case_id_column": "case_id",
        "activity_column": "activity",
        "timestamp_column": "event_ts",
        "event_id_column": "event_id",
        "optional_mappings": {"source_sequence": "source_sequence"},
        "timezone": "Asia/Seoul",
        "display_timezone": "Asia/Seoul",
    }
    payload.update(overrides)
    return payload


@pytest.mark.anyio
async def test_semantic_contract_versions_and_utc_normalization(tmp_path: Path) -> None:
    async with ingestion_client(tmp_path) as (client, settings):
        uploaded = await upload_fixture(client, SEMANTIC_CSV)
        dataset_id = str(uploaded["dataset_id"])

        first = await client.post(
            f"/api/datasets/{dataset_id}/semantic-contracts",
            json=contract_payload(),
        )
        second = await client.post(
            f"/api/datasets/{dataset_id}/semantic-contracts",
            json=contract_payload(display_timezone="UTC"),
        )
        listed = await client.get(f"/api/datasets/{dataset_id}/semantic-contracts")

        assert first.status_code == 200, first.text
        assert first.json()["version"] == 1
        assert first.json()["normalized_timezone"] == "UTC"
        assert first.json()["timestamp_preview"][0]["utc_value"].startswith(
            "2026-09-01 01:00:00"
        )
        assert second.status_code == 200, second.text
        assert second.json()["version"] == 2
        assert [item["status"] for item in listed.json()["contracts"]] == [
            "ACTIVE",
            "SUPERSEDED",
        ]

        normalized = await client.post(f"/api/datasets/{dataset_id}/normalize")
        assert normalized.status_code == 200, normalized.text
        path = settings.data.curated_dir / dataset_id / "events-v2.parquet"
        with duckdb.connect() as connection:
            event_ts = connection.execute(
                "SELECT CAST(event_ts AS VARCHAR) FROM read_parquet(?) WHERE event_id = 'E1'",
                [str(path)],
            ).fetchone()
        assert event_ts == ("2026-09-01 01:00:00",)


@pytest.mark.anyio
async def test_timezone_contract_rejects_missing_and_invalid_zone(tmp_path: Path) -> None:
    async with ingestion_client(tmp_path) as (client, _settings):
        uploaded = await upload_fixture(client, SEMANTIC_CSV)
        dataset_id = str(uploaded["dataset_id"])

        missing = await client.post(
            f"/api/datasets/{dataset_id}/semantic-contracts",
            json=contract_payload(timezone=None, display_timezone=None),
        )
        invalid = await client.post(
            f"/api/datasets/{dataset_id}/semantic-contracts",
            json=contract_payload(timezone="Mars/Olympus"),
        )

        assert missing.status_code == 422
        assert missing.json()["detail"]["code"] == "SOURCE_TIMEZONE_REQUIRED"
        assert invalid.status_code == 422
        assert invalid.json()["detail"]["code"] == "INVALID_TIMEZONE"


@pytest.mark.anyio
async def test_timezone_aware_source_respects_embedded_offset(tmp_path: Path) -> None:
    aware = tmp_path / "aware.csv"
    aware.write_text(
        "event_id,case_id,activity,event_ts\n"
        "E1,C1,A,2026-09-01T10:30:00+09:00\n",
        encoding="utf-8",
    )
    async with ingestion_client(tmp_path) as (client, settings):
        uploaded = await upload_fixture(client, aware)
        dataset_id = str(uploaded["dataset_id"])
        contract = await client.post(
            f"/api/datasets/{dataset_id}/semantic-contracts",
            json={
                "case_id_column": "case_id",
                "activity_column": "activity",
                "timestamp_column": "event_ts",
                "event_id_column": "event_id",
                "display_timezone": "Asia/Seoul",
            },
        )
        assert contract.status_code == 200, contract.text
        assert contract.json()["timestamp_preview"][0]["timezone_aware"] is True
        assert (await client.post(f"/api/datasets/{dataset_id}/normalize")).status_code == 200
        path = settings.data.curated_dir / dataset_id / "events-v1.parquet"
        with duckdb.connect() as connection:
            value = connection.execute(
                "SELECT CAST(event_ts AS VARCHAR) FROM read_parquet(?)", [str(path)]
            ).fetchone()
        assert value == ("2026-09-01 01:30:00",)


@pytest.mark.anyio
async def test_hmac_case_pseudonymization_is_deterministic(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("KOIES_PSEUDONYMIZATION_KEY", "synthetic-test-secret")
    async with ingestion_client(tmp_path) as (client, settings):
        uploaded = await upload_fixture(client, SEMANTIC_CSV)
        dataset_id = str(uploaded["dataset_id"])
        response = await client.post(
            f"/api/datasets/{dataset_id}/semantic-contracts",
            json=contract_payload(case_id_pseudonymized=True),
        )
        assert response.status_code == 200, response.text
        assert (await client.post(f"/api/datasets/{dataset_id}/normalize")).status_code == 200
        path = settings.data.curated_dir / dataset_id / "events-v1.parquet"
        with duckdb.connect() as connection:
            case_id = connection.execute(
                "SELECT case_id FROM read_parquet(?) WHERE event_id = 'E1'", [str(path)]
            ).fetchone()
        expected = hmac.new(
            b"synthetic-test-secret", b"C1", hashlib.sha256
        ).hexdigest()
        assert case_id == (expected,)


async def _ready_semantic_dataset(
    client: httpx.AsyncClient,
) -> str:
    uploaded = await upload_fixture(client, SEMANTIC_CSV)
    dataset_id = str(uploaded["dataset_id"])
    assert (
        await client.post(
            f"/api/datasets/{dataset_id}/semantic-contracts",
            json=contract_payload(),
        )
    ).status_code == 200
    assert (await client.post(f"/api/datasets/{dataset_id}/normalize")).status_code == 200
    return dataset_id


@pytest.mark.anyio
async def test_activity_mapping_coverage_business_dfg_and_unmapped_policies(
    tmp_path: Path,
) -> None:
    async with ingestion_client(tmp_path) as (client, _settings):
        dataset_id = await _ready_semantic_dataset(client)
        mapping = await client.post(
            f"/api/datasets/{dataset_id}/activity-mappings",
            json={
                "name": "업무 활동 v1",
                "unmapped_policy": "KEEP_SOURCE",
                "entries": [
                    {"source_activity": "method_a", "business_activity": "신청"},
                    {"source_activity": "method_b", "business_activity": "심사"},
                    {"source_activity": "method_c", "business_activity": "지급"},
                ],
            },
        )
        assert mapping.status_code == 200, mapping.text
        coverage = await client.get(
            f"/api/datasets/{dataset_id}/activity-mappings/1/coverage"
        )
        assert coverage.status_code == 200, coverage.text
        assert coverage.json()["unique_source_activities"] == 4
        assert coverage.json()["mapped_activities"] == 3
        assert coverage.json()["business_activities"] == 4
        assert coverage.json()["unmapped_event_count"] == 1
        assert coverage.json()["event_mapping_coverage"] == pytest.approx(6 / 7)

        source = await client.get(f"/api/dfg?dataset_id={dataset_id}")
        business = await client.get(
            f"/api/dfg?dataset_id={dataset_id}&activity_level=business"
        )
        assert source.status_code == 200, source.text
        assert business.status_code == 200, business.text
        assert {node["activity"] for node in source.json()["data"]["nodes"]} == {
            "method_a",
            "method_b",
            "method_c",
            "method_unknown",
        }
        assert {node["activity"] for node in business.json()["data"]["nodes"]} == {
            "신청",
            "심사",
            "지급",
            "method_unknown",
        }
        meta = business.json()["meta"]
        assert meta["semantic_contract_version"] == "contract-v1"
        assert meta["activity_mapping_version"] == "activity-mapping-v1"
        assert meta["normalization_version"] == "event-log-v1"
        assert meta["business_activities"] == 4

        grouped = await client.post(
            f"/api/datasets/{dataset_id}/activity-mappings",
            json={
                "name": "업무 활동 v2",
                "unmapped_policy": "GROUP_AS_UNMAPPED",
                "entries": [
                    {"source_activity": "method_a", "business_activity": "신청"}
                ],
            },
        )
        assert grouped.status_code == 200
        grouped_dfg = await client.get(
            f"/api/dfg?dataset_id={dataset_id}&activity_level=business&activity_mapping_version=2"
        )
        assert "__UNMAPPED__" in {
            node["activity"] for node in grouped_dfg.json()["data"]["nodes"]
        }
        assert grouped_dfg.json()["meta"]["business_activities"] == 2


@pytest.mark.anyio
async def test_event_id_retention_supports_drop_and_hmac(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("KOIES_PSEUDONYMIZATION_KEY", "synthetic-test-secret")
    async with ingestion_client(tmp_path) as (client, settings):
        dropped_upload = await upload_fixture(client, SEMANTIC_CSV)
        dropped_id = str(dropped_upload["dataset_id"])
        dropped_contract = await client.post(
            f"/api/datasets/{dropped_id}/semantic-contracts",
            json=contract_payload(
                attribute_policies={"event_id": "DROP"},
                pii_classifications={"event_id": "PII"},
            ),
        )
        assert dropped_contract.status_code == 200, dropped_contract.text
        assert dropped_contract.json()["attribute_policies"]["event_id"] == "DROP"
        dropped_normalized = await client.post(
            f"/api/datasets/{dropped_id}/normalize"
        )
        assert dropped_normalized.status_code == 200, dropped_normalized.text

        pseudonym_upload = await upload_fixture(client, SEMANTIC_CSV)
        pseudonym_id = str(pseudonym_upload["dataset_id"])
        pseudonym_contract = await client.post(
            f"/api/datasets/{pseudonym_id}/semantic-contracts",
            json=contract_payload(
                attribute_policies={"event_id": "PSEUDONYMIZE"},
                pii_classifications={"event_id": "PII"},
            ),
        )
        assert pseudonym_contract.status_code == 200, pseudonym_contract.text
        assert (
            await client.post(f"/api/datasets/{pseudonym_id}/normalize")
        ).status_code == 200

        with duckdb.connect() as connection:
            dropped = connection.execute(
                "SELECT event_id, source_event_id FROM read_parquet(?) "
                "ORDER BY ingest_sequence LIMIT 1",
                [str(settings.data.curated_dir / dropped_id / "events-v1.parquet")],
            ).fetchone()
            pseudonymized = connection.execute(
                "SELECT event_id, source_event_id FROM read_parquet(?) "
                "ORDER BY ingest_sequence LIMIT 1",
                [
                    str(
                        settings.data.curated_dir
                        / pseudonym_id
                        / "events-v1.parquet"
                    )
                ],
            ).fetchone()
        assert dropped is not None and dropped[0] != "E1" and dropped[1] is None
        expected = hmac.new(
            b"synthetic-test-secret", b"E1", hashlib.sha256
        ).hexdigest()
        assert pseudonymized == (expected, expected)


def test_numeric_attributes_reject_pseudonymization() -> None:
    with pytest.raises(ValidationError, match="numeric attributes cannot use PSEUDONYMIZE"):
        MappingCreateRequest.model_validate(
            contract_payload(attribute_policies={"source_sequence": "PSEUDONYMIZE"})
        )


@pytest.mark.anyio
async def test_local_reference_security_and_source_drift(tmp_path: Path) -> None:
    allowed_root = tmp_path / "allowed"
    allowed_root.mkdir()
    source = allowed_root / "events.csv"
    source.write_bytes(SEMANTIC_CSV.read_bytes())
    settings = isolated_settings(tmp_path).model_copy(
        update={
            "dataset_import": isolated_settings(tmp_path).dataset_import.model_copy(
                update={"allowed_roots": [allowed_root]}
            )
        }
    )
    application = create_app(settings)
    async with application.router.lifespan_context(application), httpx.AsyncClient(
        transport=httpx.ASGITransport(app=application), base_url="http://test"
    ) as client:
        imported = await client.post(
            "/api/datasets/import-local",
            json={"path": str(source), "mode": "REFERENCE"},
        )
        assert imported.status_code == 201, imported.text
        dataset_id = imported.json()["dataset_id"]

        outside = tmp_path / "outside.csv"
        outside.write_bytes(SEMANTIC_CSV.read_bytes())
        rejected = await client.post(
            "/api/datasets/import-local", json={"path": str(outside)}
        )
        traversal = await client.post(
            "/api/datasets/import-local",
            json={"path": str(allowed_root / ".." / "outside.csv")},
        )
        assert rejected.status_code == 403
        assert rejected.json()["detail"]["code"] == "PATH_OUTSIDE_ALLOWED_ROOT"
        assert traversal.status_code == 403
        assert traversal.json()["detail"]["code"] == "PATH_TRAVERSAL"

        source.write_bytes(source.read_bytes() + b"\n")
        drift = await client.post(
            f"/api/datasets/{dataset_id}/semantic-contracts",
            json=contract_payload(),
        )
        assert drift.status_code == 409
        assert drift.json()["detail"]["code"] == "SOURCE_CHANGED"
        state = await client.get(f"/api/datasets/{dataset_id}")
        assert state.json()["status"] == "SOURCE_CHANGED"


@pytest.mark.anyio
async def test_artifact_lifecycle_protects_source_active_and_pinned(tmp_path: Path) -> None:
    async with ingestion_client(tmp_path) as (client, _settings):
        dataset_id = await _ready_semantic_dataset(client)
        assert (
            await client.post(
                f"/api/datasets/{dataset_id}/semantic-contracts",
                json=contract_payload(display_timezone="UTC"),
            )
        ).status_code == 200
        assert (await client.post(f"/api/datasets/{dataset_id}/normalize")).status_code == 200
        listed = await client.get(f"/api/datasets/{dataset_id}/artifacts")
        artifacts = listed.json()["artifacts"]
        source = next(item for item in artifacts if item["artifact_type"] == "SOURCE")
        active = next(
            item
            for item in artifacts
            if item["artifact_type"] == "NORMALIZED" and item["active"]
        )
        old = next(
            item
            for item in artifacts
            if item["artifact_type"] == "NORMALIZED" and not item["active"]
        )

        source_delete = await client.delete(
            f"/api/datasets/{dataset_id}/artifacts/{source['artifact_id']}"
        )
        active_delete = await client.delete(
            f"/api/datasets/{dataset_id}/artifacts/{active['artifact_id']}"
        )
        assert source_delete.json()["detail"]["code"] == "SOURCE_ARTIFACT_PROTECTED"
        assert active_delete.json()["detail"]["code"] == "ACTIVE_ARTIFACT_PROTECTED"

        pinned = await client.patch(
            f"/api/datasets/{dataset_id}/artifacts/{old['artifact_id']}/pin",
            json={"pinned": True},
        )
        assert pinned.status_code == 200
        pinned_delete = await client.delete(
            f"/api/datasets/{dataset_id}/artifacts/{old['artifact_id']}"
        )
        assert pinned_delete.json()["detail"]["code"] == "PINNED_ARTIFACT_PROTECTED"
        assert (
            await client.patch(
                f"/api/datasets/{dataset_id}/artifacts/{old['artifact_id']}/pin",
                json={"pinned": False},
            )
        ).status_code == 200
        deleted = await client.delete(
            f"/api/datasets/{dataset_id}/artifacts/{old['artifact_id']}"
        )
        assert deleted.json()["deleted"] is True


def test_no_secret_is_committed_for_pseudonymization() -> None:
    assert "KOIES_PSEUDONYMIZATION_KEY" not in os.environ or os.environ[
        "KOIES_PSEUDONYMIZATION_KEY"
    ] != "production-secret"


@pytest.mark.anyio
async def test_ambiguous_ordering_is_semantic_quality_not_fake_chronology(
    tmp_path: Path,
) -> None:
    source = tmp_path / "ambiguous.csv"
    source.write_text(
        "case_id,activity,event_ts\n"
        "C1,A,2026-09-01 10:00:00\n"
        "C1,B,2026-09-01 10:00:00\n",
        encoding="utf-8",
    )
    async with ingestion_client(tmp_path) as (client, _settings):
        uploaded = await upload_fixture(client, source)
        dataset_id = str(uploaded["dataset_id"])
        contract = await client.post(
            f"/api/datasets/{dataset_id}/semantic-contracts",
            json={
                "case_id_column": "case_id",
                "activity_column": "activity",
                "timestamp_column": "event_ts",
                "timezone": "Asia/Seoul",
            },
        )
        assert contract.status_code == 200, contract.text
        normalized = await client.post(f"/api/datasets/{dataset_id}/normalize")
        assert normalized.status_code == 200, normalized.text
        quality = normalized.json()["quality"]
        assert quality["duplicate_timestamp_rows"] == 2
        assert quality["ambiguous_ordering_cases"] == 1
        assert quality["technical_quality"] == "PASSED"
        assert quality["semantic_quality"] == "WARNING_AMBIGUOUS_ORDERING"


@pytest.mark.anyio
async def test_atomic_normalization_failure_preserves_existing_active_artifact(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async with ingestion_client(tmp_path) as (client, settings):
        dataset_id = await _ready_semantic_dataset(client)
        active_path = settings.data.curated_dir / dataset_id / "events-v1.parquet"
        before = active_path.read_bytes()

        def fail_quarantine(*_args: object, **_kwargs: object) -> None:
            raise OSError("synthetic finalization failure")

        monkeypatch.setattr(DatasetNormalizer, "_write_quarantine", fail_quarantine)
        failed = await client.post(f"/api/datasets/{dataset_id}/normalize")

        assert failed.status_code == 422
        assert failed.json()["detail"]["code"] == "NORMALIZATION_FAILED"
        assert active_path.read_bytes() == before
        assert list(active_path.parent.glob("*.tmp.parquet")) == []
