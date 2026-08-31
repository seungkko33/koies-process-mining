import pytest
from app.analytics.dfg import calculate_dfg
from duckdb import DuckDBPyConnection


def test_calculate_dfg_matches_golden_fixture(
    golden_connection: DuckDBPyConnection,
) -> None:
    result = calculate_dfg(golden_connection)
    nodes = {node.activity: node for node in result.nodes}
    edges = {(edge.source, edge.target): edge for edge in result.edges}

    assert nodes["A"].event_count == 3
    assert nodes["B"].event_count == 3
    assert nodes["B"].case_count == 2
    assert nodes["B"].case_share == pytest.approx(2 / 3)

    assert edges[("A", "B")].transition_count == 2
    assert edges[("A", "B")].case_count == 2
    assert edges[("A", "B")].case_share == pytest.approx(2 / 3)
    assert edges[("A", "B")].median_transition_ms == 90_000
    assert edges[("A", "B")].p90_transition_ms == pytest.approx(114_000)
    assert edges[("B", "B")].transition_count == 1
    assert edges[("B", "C")].transition_count == 2
    assert edges[("A", "D")].transition_count == 1
    assert edges[("D", "C")].transition_count == 1


def test_calculate_dfg_uses_sequence_tie_breaker(
    golden_connection: DuckDBPyConnection,
) -> None:
    golden_connection.executemany(
        """
        INSERT INTO curated.event_log (
            event_id, case_id, activity, event_ts, source_sequence, ingest_sequence
        ) VALUES (?, ?, ?, ?, ?, ?)
        """,
        [
            ("T002", "CASE-TIE", "Y", "2026-01-02T09:00:00", 2, 12),
            ("T001", "CASE-TIE", "X", "2026-01-02T09:00:00", 1, 11),
        ],
    )

    result = calculate_dfg(golden_connection)
    edges = {(edge.source, edge.target): edge for edge in result.edges}

    assert ("X", "Y") in edges
    assert ("Y", "X") not in edges

