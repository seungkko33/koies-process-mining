import pytest
from app.analytics.dfg import calculate_dfg
from duckdb import DuckDBPyConnection


def test_calculate_dfg_matches_golden_fixture(
    golden_connection: DuckDBPyConnection,
) -> None:
    result = calculate_dfg(golden_connection)
    nodes = {node.activity: node for node in result.nodes}
    edges = {(edge.source, edge.target): edge for edge in result.edges}

    assert result.total_cases == 3
    assert result.total_events == 10
    assert result.node_count == 4
    assert result.edge_count == 5
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


def test_calculate_dfg_is_deterministically_ordered(
    golden_connection: DuckDBPyConnection,
) -> None:
    first = calculate_dfg(golden_connection)
    second = calculate_dfg(golden_connection)

    assert first == second
    assert [node.activity for node in first.nodes] == ["A", "B", "C", "D"]
    assert [(edge.source, edge.target) for edge in first.edges] == [
        ("A", "B"),
        ("B", "C"),
        ("A", "D"),
        ("B", "B"),
        ("D", "C"),
    ]


def test_calculate_dfg_handles_empty_event_log(
    empty_connection: DuckDBPyConnection,
) -> None:
    result = calculate_dfg(empty_connection)

    assert result.total_cases == 0
    assert result.total_events == 0
    assert result.node_count == 0
    assert result.edge_count == 0
    assert result.nodes == []
    assert result.edges == []


def test_calculate_dfg_applies_bounded_graph_limits(
    golden_connection: DuckDBPyConnection,
) -> None:
    result = calculate_dfg(golden_connection, max_nodes=2, max_edges=1)

    assert [node.activity for node in result.nodes] == ["A", "B"]
    assert [(edge.source, edge.target) for edge in result.edges] == [("A", "B")]
    assert result.node_count == 2
    assert result.edge_count == 1
