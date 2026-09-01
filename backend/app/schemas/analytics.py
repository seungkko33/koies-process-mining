from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator


class EventFilters(BaseModel):
    model_config = ConfigDict(extra="forbid")

    date_from: datetime | None = None
    date_to: datetime | None = None

    @model_validator(mode="after")
    def validate_range(self) -> EventFilters:
        if self.date_from and self.date_to and self.date_from >= self.date_to:
            raise ValueError("date_from must be earlier than date_to")
        return self


class DFGNode(BaseModel):
    activity: str
    event_count: int
    case_count: int
    case_share: float


class DFGEdge(BaseModel):
    source: str
    target: str
    transition_count: int
    case_count: int
    case_share: float
    median_transition_ms: float
    p90_transition_ms: float


class DFGResult(BaseModel):
    total_cases: int
    total_events: int
    node_count: int
    edge_count: int
    nodes: list[DFGNode] = Field(default_factory=list)
    edges: list[DFGEdge] = Field(default_factory=list)


class OverviewResult(BaseModel):
    case_count: int
    event_count: int
    activity_count: int
    median_throughput_ms: float | None
    p90_throughput_ms: float | None
    rework_rate: float


class QueryMeta(BaseModel):
    query_ms: int
    rows: int
    filter_signature: str
    mapping_version: str
    dataset_id: str | None = None
    semantic_contract_version: str | None = None
    activity_mapping_version: str | None = None
    normalization_version: str | None = None
    activity_level: str = "source"
    unique_source_activities: int | None = None
    business_activities: int | None = None
    event_mapping_coverage: float | None = None


class OverviewEnvelope(BaseModel):
    data: OverviewResult
    meta: QueryMeta
    warnings: list[str] = Field(default_factory=list)


class DFGEnvelope(BaseModel):
    data: DFGResult
    meta: QueryMeta
    warnings: list[str] = Field(default_factory=list)


class HealthResponse(BaseModel):
    status: str
    service: str
