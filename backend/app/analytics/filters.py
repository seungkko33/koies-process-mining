from __future__ import annotations

from app.schemas.analytics import EventFilters


def build_event_filter(filters: EventFilters) -> tuple[str, list[object]]:
    """Build a fixed-column WHERE clause and bind values separately."""
    clauses: list[str] = []
    parameters: list[object] = []

    if filters.date_from is not None:
        clauses.append("event_ts >= ?")
        parameters.append(filters.date_from)
    if filters.date_to is not None:
        clauses.append("event_ts < ?")
        parameters.append(filters.date_to)

    return (" AND ".join(clauses) if clauses else "TRUE", parameters)
