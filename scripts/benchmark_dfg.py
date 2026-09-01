from __future__ import annotations

import argparse
import json
import sys
import tempfile
import time
import tracemalloc
from pathlib import Path

from app.analytics.dfg import calculate_dfg
from app.config import Settings, load_settings
from app.database import DuckDBManager

RECOMMENDED_EVENT_SCALES = (100_000, 1_000_000, 5_000_000, 20_000_000)

INGEST_SQL = """
    INSERT INTO curated.event_log (
        event_id,
        case_id,
        activity,
        event_ts,
        source_sequence,
        ingest_sequence,
        mapping_version,
        case_rule_version,
        ingestion_batch_id,
        event_date
    )
    SELECT
        event_id,
        case_id,
        activity,
        CAST(event_ts AS TIMESTAMP),
        source_sequence,
        ingest_sequence,
        mapping_version,
        case_rule_version,
        ingestion_batch_id,
        CAST(event_ts AS DATE)
    FROM read_csv(
        ?,
        header = true,
        columns = {
            'event_id': 'VARCHAR',
            'case_id': 'VARCHAR',
            'activity': 'VARCHAR',
            'event_ts': 'VARCHAR',
            'source_sequence': 'BIGINT',
            'ingest_sequence': 'BIGINT',
            'mapping_version': 'VARCHAR',
            'case_rule_version': 'VARCHAR',
            'ingestion_batch_id': 'VARCHAR'
        }
    )
"""


def _benchmark_settings(work_dir: Path) -> Settings:
    settings = load_settings()
    return settings.model_copy(
        update={
            "data": settings.data.model_copy(
                update={"database_path": work_dir / "benchmark.duckdb"}
            ),
            "duckdb": settings.duckdb.model_copy(
                update={"temp_directory": work_dir / "duckdb-temp"}
            ),
        }
    )


def _write_synthetic_csv(csv_path: Path, event_target: int, seed: int) -> int:
    from scripts.generate_synthetic_events import write_csv_for_event_target

    return write_csv_for_event_target(csv_path, event_target, seed)


def run_benchmark(event_target: int, work_dir: Path, seed: int) -> dict[str, int | float | str]:
    if event_target < 1:
        raise ValueError("event_target must be at least 1")

    work_dir.mkdir(parents=True, exist_ok=True)
    csv_path = work_dir / "synthetic_events.csv"
    settings = _benchmark_settings(work_dir)
    manager = DuckDBManager(settings)

    tracemalloc.start()
    total_started_at = time.perf_counter()

    generation_started_at = time.perf_counter()
    generated_events = _write_synthetic_csv(csv_path, event_target, seed)
    generation_seconds = time.perf_counter() - generation_started_at

    manager.initialize()
    ingestion_started_at = time.perf_counter()
    with manager.connection() as connection:
        connection.execute(INGEST_SQL, [str(csv_path)])
        connection.execute("CHECKPOINT")
    ingestion_seconds = time.perf_counter() - ingestion_started_at

    dfg_started_at = time.perf_counter()
    with manager.connection() as connection:
        result = calculate_dfg(
            connection,
            max_nodes=settings.analytics.max_process_nodes,
            max_edges=settings.analytics.max_process_edges,
        )
    dfg_query_seconds = time.perf_counter() - dfg_started_at

    total_seconds = time.perf_counter() - total_started_at
    _, python_peak_bytes = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    return {
        "requested_events": event_target,
        "generated_events": generated_events,
        "total_cases": result.total_cases,
        "node_count": result.node_count,
        "edge_count": result.edge_count,
        "event_generation_seconds": round(generation_seconds, 6),
        "ingestion_seconds": round(ingestion_seconds, 6),
        "dfg_query_seconds": round(dfg_query_seconds, 6),
        "total_execution_seconds": round(total_seconds, 6),
        "duckdb_file_bytes": settings.data.database_path.stat().st_size,
        "python_peak_memory_bytes": python_peak_bytes,
        "work_directory": str(work_dir),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Benchmark streaming synthetic generation, DuckDB ingestion, and DFG SQL. "
            f"Recommended event scales: {', '.join(map(str, RECOMMENDED_EVENT_SCALES))}."
        )
    )
    parser.add_argument("--events", type=int, default=100_000)
    parser.add_argument("--seed", type=int, default=20260831)
    parser.add_argument(
        "--work-dir",
        type=Path,
        help="Keep benchmark CSV and DuckDB files in this ignored/local directory.",
    )
    return parser.parse_args()


def main() -> None:
    if __package__ in {None, ""}:
        sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    args = parse_args()
    if args.work_dir is not None:
        metrics = run_benchmark(args.events, args.work_dir.resolve(), args.seed)
        print(json.dumps(metrics, indent=2, ensure_ascii=False))
        return

    with tempfile.TemporaryDirectory(prefix="koies-dfg-benchmark-") as temp_dir:
        metrics = run_benchmark(args.events, Path(temp_dir), args.seed)
        metrics["work_directory"] = "temporary (removed after benchmark)"
        print(json.dumps(metrics, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
