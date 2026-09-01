from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import sys
import time
import tracemalloc
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import duckdb

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.analytics.dfg import calculate_dfg
from app.analytics.source import EventSource
from app.config import PROJECT_ROOT, Settings, load_settings
from app.database import DuckDBManager
from app.datasets.service import DatasetService
from app.schemas.datasets import MappingCreateRequest

from scripts.generate_synthetic_events import write_csv_for_event_target

RECOMMENDED_EVENT_SCALES = (100_000, 1_000_000, 5_000_000, 20_000_000)
LARGE_RUN_THRESHOLD = 20_000_000
ESTIMATED_CSV_BYTES_PER_EVENT = 130


def _benchmark_settings(work_dir: Path) -> Settings:
    settings = load_settings()
    data_root = work_dir / "data"
    return settings.model_copy(
        update={
            "data": settings.data.model_copy(
                update={
                    "staging_dir": data_root / "staging",
                    "raw_dir": data_root / "raw",
                    "raw_parquet_dir": data_root / "parquet-raw",
                    "curated_dir": data_root / "curated",
                    "quarantine_dir": data_root / "quarantine",
                    "temp_dir": data_root / "temp",
                    "database_path": work_dir / "ingestion-benchmark.duckdb",
                }
            ),
            "duckdb": settings.duckdb.model_copy(
                update={"temp_directory": data_root / "duckdb-temp"}
            ),
        }
    )


def benchmark_preflight(event_target: int, work_dir: Path) -> dict[str, int]:
    settings = load_settings()
    estimated_source = event_target * ESTIMATED_CSV_BYTES_PER_EVENT
    required = int(
        estimated_source * settings.quality.minimum_free_space_multiplier
    )
    work_dir.mkdir(parents=True, exist_ok=True)
    current_free = shutil.disk_usage(work_dir).free
    return {
        "estimated_source_bytes": estimated_source,
        "required_free_bytes": required,
        "current_free_bytes": current_free,
    }


def _directory_bytes(path: Path) -> int:
    if not path.exists():
        return 0
    return sum(item.stat().st_size for item in path.rglob("*") if item.is_file())


def _prepare_source(
    event_target: int,
    source_root: Path,
    seed: int,
    *,
    source_path: Path | None,
    reuse_source: bool,
) -> tuple[Path, int, float, bool]:
    if source_path is not None:
        selected = source_path.resolve()
        if not selected.is_file():
            raise FileNotFoundError("The supplied benchmark source does not exist")
        return selected, event_target, 0.0, True

    source_root.mkdir(parents=True, exist_ok=True)
    selected = source_root / f"synthetic-{event_target}-{seed}.csv"
    if reuse_source and selected.is_file():
        return selected, event_target, 0.0, True

    generation_started_at = time.perf_counter()
    generated_events = write_csv_for_event_target(selected, event_target, seed)
    generation_seconds = time.perf_counter() - generation_started_at
    return selected, generated_events, generation_seconds, False


def run_benchmark(
    event_target: int,
    work_dir: Path,
    seed: int,
    *,
    source_path: Path | None = None,
    reuse_source: bool = False,
) -> dict[str, object]:
    if event_target < 1:
        raise ValueError("event_target must be at least 1")

    work_dir.mkdir(parents=True, exist_ok=True)
    preflight = benchmark_preflight(event_target, work_dir)
    if preflight["current_free_bytes"] < preflight["required_free_bytes"]:
        raise OSError("Insufficient free space for the benchmark preflight estimate")

    run_id = f"ingestion-{event_target}-{uuid4().hex[:8]}"
    run_directory = work_dir / "runs" / run_id
    run_directory.mkdir(parents=True, exist_ok=False)
    free_disk_before = shutil.disk_usage(work_dir).free
    overall_started_at = time.perf_counter()
    selected_source, generated_events, generation_seconds, source_reused = (
        _prepare_source(
            event_target,
            work_dir / "sources",
            seed,
            source_path=source_path,
            reuse_source=reuse_source,
        )
    )
    source_file_size = selected_source.stat().st_size

    settings = _benchmark_settings(run_directory)
    manager = DuckDBManager(settings)
    manager.initialize()
    temp_bytes_before = _directory_bytes(settings.duckdb.temp_directory)
    tracemalloc.start()
    application_started_at = time.perf_counter()

    with manager.connection() as connection:
        service = DatasetService(connection, settings)

        staging_started_at = time.perf_counter()
        staged = service.stage_benchmark_file(selected_source, selected_source.name)
        staging_seconds = time.perf_counter() - staging_started_at

        schema_started_at = time.perf_counter()
        schema = service.detect_staged_schema(staged.dataset_id)
        schema_inference_seconds = time.perf_counter() - schema_started_at

        profile_started_at = time.perf_counter()
        service.profile_staged_dataset(staged.dataset_id, schema)
        profiling_seconds = time.perf_counter() - profile_started_at

        mapping_started_at = time.perf_counter()
        service.create_mapping(
            staged.dataset_id,
            MappingCreateRequest(
                case_id_column="case_id",
                activity_column="activity",
                timestamp_column="event_ts",
                event_id_column="event_id",
                optional_mappings={"source_sequence": "source_sequence"},
                timezone="UTC",
                display_timezone="UTC",
            ),
        )
        mapping_seconds = time.perf_counter() - mapping_started_at
        dataset, quality, artifacts = service.normalize_with_artifacts(staged.dataset_id)
        normalized_path, mapping_version = service.normalized_path_for_analysis(
            staged.dataset_id
        )

        dfg_started_at = time.perf_counter()
        dfg = calculate_dfg(
            connection,
            max_nodes=settings.analytics.max_process_nodes,
            max_edges=settings.analytics.max_process_edges,
            source=EventSource.normalized_parquet(
                normalized_path,
                staged.dataset_id,
                mapping_version,
                dataset.semantic_contract_version,
                dataset.normalization_version or "event-log-v1",
            ),
        )
        dfg_seconds = time.perf_counter() - dfg_started_at

    application_processing_seconds = time.perf_counter() - application_started_at
    _, python_peak_bytes = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    overall_seconds = time.perf_counter() - overall_started_at
    temp_bytes_after = _directory_bytes(settings.duckdb.temp_directory)
    free_disk_after = shutil.disk_usage(work_dir).free

    return {
        "run_id": run_id,
        "recorded_at": datetime.now(UTC).isoformat(),
        "requested_events": event_target,
        "generated_events": generated_events,
        "cases": dfg.total_cases,
        "unique_activities": quality.unique_activities,
        "valid_events": quality.valid_events,
        "invalid_events": quality.invalid_events,
        "dataset_status": dataset.status.value,
        "source_generation_seconds": round(generation_seconds, 6),
        "source_reused": source_reused,
        "staging_seconds": round(staging_seconds, 6),
        "schema_inference_seconds": round(schema_inference_seconds, 6),
        "profiling_seconds": round(profiling_seconds, 6),
        "semantic_contract_seconds": round(mapping_seconds, 6),
        "validation_seconds": round(artifacts.validation_seconds, 6),
        "normalization_seconds": round(artifacts.normalization_seconds, 6),
        "quarantine_seconds": round(artifacts.quarantine_seconds, 6),
        "parquet_materialization_seconds": round(
            artifacts.normalization_seconds + artifacts.quarantine_seconds,
            6,
        ),
        "dfg_query_seconds": round(dfg_seconds, 6),
        "application_processing_seconds": round(application_processing_seconds, 6),
        "overall_seconds": round(overall_seconds, 6),
        "source_file_bytes": source_file_size,
        "normalized_file_bytes": artifacts.normalized_path.stat().st_size,
        "quarantine_file_bytes": artifacts.quarantine_path.stat().st_size,
        "duckdb_file_bytes": settings.data.database_path.stat().st_size,
        "python_tracemalloc_peak_bytes": python_peak_bytes,
        "process_rss_peak_bytes": None,
        "process_rss_measurement": "not measured; no new process-inspection dependency added",
        "duckdb_temp_spill_bytes": max(0, temp_bytes_after - temp_bytes_before),
        "free_disk_before_bytes": free_disk_before,
        "free_disk_after_bytes": free_disk_after,
        "dfg_total_cases": dfg.total_cases,
        "dfg_nodes": dfg.node_count,
        "dfg_edges": dfg.edge_count,
        "preflight": preflight,
        "environment": {
            "os": platform.system(),
            "python": platform.python_version(),
            "duckdb": duckdb.__version__,
            "cpu_logical_count": os.cpu_count(),
            "configured_threads": settings.duckdb.threads,
            "configured_memory_limit": settings.duckdb.memory_limit,
            "file_format": "CSV to Parquet",
        },
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Benchmark source generation separately from KOIES application processing. "
            f"Recommended scales: {', '.join(map(str, RECOMMENDED_EVENT_SCALES))}."
        )
    )
    parser.add_argument("--events", type=int, default=100_000)
    parser.add_argument("--seed", type=int, default=20260831)
    parser.add_argument(
        "--work-dir",
        type=Path,
        default=PROJECT_ROOT / "data" / "benchmarks",
        help="Ignored local directory for reusable sources, runs, and results.",
    )
    parser.add_argument("--source", type=Path, help="Use an existing synthetic source.")
    parser.add_argument(
        "--reuse-source",
        action="store_true",
        help="Reuse the scale/seed source under work-dir when it already exists.",
    )
    parser.add_argument(
        "--results-dir",
        type=Path,
        help="Machine-readable result directory; defaults under work-dir.",
    )
    parser.add_argument(
        "--confirm-large-run",
        action="store_true",
        help="Required for 20M or larger runs after reviewing the preflight estimate.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    work_dir = args.work_dir.resolve()
    preflight = benchmark_preflight(args.events, work_dir)
    print(json.dumps({"preflight": preflight}, ensure_ascii=False), file=sys.stderr)
    if args.events >= LARGE_RUN_THRESHOLD and not args.confirm_large_run:
        raise SystemExit(
            "20M+ benchmark blocked: review preflight and pass --confirm-large-run"
        )
    metrics = run_benchmark(
        args.events,
        work_dir,
        args.seed,
        source_path=args.source,
        reuse_source=args.reuse_source,
    )
    results_dir = (args.results_dir or work_dir / "benchmark-results").resolve()
    results_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    result_path = results_dir / f"ingestion-{args.events}-{timestamp}.json"
    result_path.write_text(
        json.dumps(metrics, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    metrics["result_file"] = result_path.name
    print(json.dumps(metrics, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
