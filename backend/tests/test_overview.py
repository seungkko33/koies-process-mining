import pytest
from app.analytics.overview import calculate_overview
from duckdb import DuckDBPyConnection


def test_calculate_overview_matches_golden_fixture(
    golden_connection: DuckDBPyConnection,
) -> None:
    overview = calculate_overview(golden_connection)

    assert overview.case_count == 3
    assert overview.event_count == 10
    assert overview.activity_count == 4
    assert overview.median_throughput_ms == 420_000
    assert overview.p90_throughput_ms == pytest.approx(516_000)
    assert overview.rework_rate == pytest.approx(1 / 3)

