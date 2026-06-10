from pydantic import BaseModel
from typing import Literal


class TraceRequest(BaseModel):
    lot_id: str
    direction: Literal["forward", "backward"] = "forward"


class GraphNode(BaseModel):
    id: str
    type: Literal["ingredient_lot", "batch", "fg_lot", "case", "shipment", "dc", "retailer", "store"]
    label: str
    units: int | None = None
    status: Literal["in_channel", "sold_through", "recalled"] | None = None


class GraphEdge(BaseModel):
    source: str
    target: str


class ScopePanel(BaseModel):
    lots_affected: int
    skus_affected: int
    cases_in_channel: int
    cases_sold_through: int
    cost_low: float
    cost_high: float
    notification_list: list[str]


class TraceResult(BaseModel):
    lot_id: str
    nodes: list[GraphNode]
    edges: list[GraphEdge]
    scope: ScopePanel


class ScenarioGraph(BaseModel):
    id: Literal["A", "B", "C"]
    title: str
    description: str
    result: TraceResult
