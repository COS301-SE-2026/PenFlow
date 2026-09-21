from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel

#the attack graph element
GraphNodeType = Literal["domain", "asset", "service", "technology", "finding"]
GraphEdgeType = Literal["RESOLVES_TO", "EXPOSES", "RUNS", "AFFECTED_BY"]


class GraphRisk(BaseModel):
    severity: Literal["critical", "high", "medium", "low", "info"] | None = None
    max_cvss: float | None = None
    finding_count: int = 0

class GraphNode(BaseModel):
    id: str
    entity_id: UUID | None
    type: GraphNodeType
    label: str
    risk: GraphRisk
    metadata: dict[str, Any] = {}

class GraphEdgeProvenance(BaseModel):
    source: str
    observed_at: datetime | None = None
    confidence: float | None = None

class GraphEdge(BaseModel):
    id: str
    source: str
    target: str
    type: GraphEdgeType
    provenance: GraphEdgeProvenance

class GraphResponse(BaseModel):
    scan_id: UUID
    domain: str
    generated_at: datetime
    nodes: list[GraphNode]
    edge: list[GraphEdge]

class GraphFindingSummary(BaseModel):
    id: UUID
    title: str
    severity: Literal["critical", "high", "medium", "low", "info"]
    cvss_score: float | None = None
    cve_id: str | None = None
    status: str

class GraphNodeRelationshipCounts(BaseModel):
    incoming: int
    outgoing: int

class GraphNodeDetailResponse(BaseModel):
    node: GraphNode
    relationships: GraphNodeRelationshipCounts
    findings: list[GraphFindingSummary]
    provenance: list[GraphEdgeProvenance] = []

class GraphSummaryCounts(BaseModel):
    domains: int
    assets: int
    service: int
    technologies: int
    findings: int
    edges: int

class GraphSummaryRisk(BaseModel):
    critical_findings: int
    high_findings: int
    medium_findings: int
    low_findings: int
    affected_assets: int
    highest_risk_node_id: str | None = None
    

