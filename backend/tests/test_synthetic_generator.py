from pathlib import Path

from scripts.generate_synthetic_events import generate_events, write_csv_for_event_target


def test_synthetic_generator_is_deterministic_and_streaming() -> None:
    first_run = list(generate_events(case_count=3, seed=7))
    second_run = list(generate_events(case_count=3, seed=7))

    assert first_run == second_run
    assert {event["case_id"] for event in first_run} == {
        "SYN-CASE-00000001",
        "SYN-CASE-00000002",
        "SYN-CASE-00000003",
    }
    assert all(str(event["case_id"]).startswith("SYN-") for event in first_run)


def test_write_csv_for_event_target_writes_exact_streamed_count(tmp_path: Path) -> None:
    output_path = tmp_path / "events.csv"

    event_count = write_csv_for_event_target(output_path, event_target=7, seed=11)

    assert event_count == 7
    assert len(output_path.read_text(encoding="utf-8").splitlines()) == 8
