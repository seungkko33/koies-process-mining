from scripts.generate_synthetic_events import generate_events


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

