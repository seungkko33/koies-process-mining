from __future__ import annotations

import argparse
import csv
import random
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path

FIELD_NAMES = [
    "event_id",
    "case_id",
    "activity",
    "event_ts",
    "source_sequence",
    "ingest_sequence",
    "mapping_version",
    "case_rule_version",
    "ingestion_batch_id",
]

VARIANTS = (
    ("접수", "검증", "승인"),
    ("접수", "검증", "보완요청", "검증", "승인"),
    ("접수", "수동검토", "승인"),
)


def generate_events(case_count: int, seed: int = 20260831) -> Iterator[dict[str, object]]:
    """Yield synthetic events one row at a time without materializing the dataset."""
    if case_count < 1:
        raise ValueError("case_count must be at least 1")

    randomizer = random.Random(seed)
    base_time = datetime(2026, 1, 1, 9, 0, tzinfo=UTC)
    ingest_sequence = 0
    for case_index in range(1, case_count + 1):
        case_id = f"SYN-CASE-{case_index:08d}"
        variant = VARIANTS[randomizer.randrange(len(VARIANTS))]
        event_time = base_time + timedelta(minutes=case_index)
        for source_sequence, activity in enumerate(variant, start=1):
            ingest_sequence += 1
            if source_sequence > 1:
                event_time += timedelta(seconds=randomizer.randint(15, 300))
            yield {
                "event_id": f"SYN-EVENT-{ingest_sequence:012d}",
                "case_id": case_id,
                "activity": activity,
                "event_ts": event_time.isoformat(),
                "source_sequence": source_sequence,
                "ingest_sequence": ingest_sequence,
                "mapping_version": "synthetic-v1",
                "case_rule_version": "synthetic-v1",
                "ingestion_batch_id": "synthetic-local",
            }


def write_csv(output_path: Path, case_count: int, seed: int) -> int:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    event_count = 0
    with output_path.open("w", encoding="utf-8", newline="") as output_file:
        writer = csv.DictWriter(output_file, fieldnames=FIELD_NAMES)
        writer.writeheader()
        for event in generate_events(case_count, seed):
            writer.writerow(event)
            event_count += 1
    return event_count


def write_csv_for_event_target(output_path: Path, event_target: int, seed: int) -> int:
    """Stream exactly ``event_target`` synthetic events to CSV for benchmarks."""
    if event_target < 1:
        raise ValueError("event_target must be at least 1")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    event_count = 0
    with output_path.open("w", encoding="utf-8", newline="") as output_file:
        writer = csv.DictWriter(output_file, fieldnames=FIELD_NAMES)
        writer.writeheader()
        for event in generate_events(case_count=event_target, seed=seed):
            writer.writerow(event)
            event_count += 1
            if event_count == event_target:
                break
    return event_count


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate a fully synthetic event log.")
    parser.add_argument("--cases", type=int, default=1_000)
    parser.add_argument("--seed", type=int, default=20260831)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/synthetic/event_log.csv"),
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    event_count = write_csv(args.output, args.cases, args.seed)
    print(f"Wrote {event_count} synthetic events to {args.output}")


if __name__ == "__main__":
    main()
