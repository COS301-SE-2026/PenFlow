from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.models.base import FindingStatus, Severity
from app.services.graph_service import GraphService

#define mock data
def _scan(**overrides):
    defaults = {
        "id": uuid4(),
        "domain" : "example.com",
        "user_id" : uuid4(),
    }
    defaults.update(overrides)
    return SimpleNamespace(**defaults)

def _asset(scan_id, **overrides):
    defaults = {
        "id": uuid4(),
        "scan_id": scan_id,
        "identifier": "203.0.113.10",
        "asset_type": "ip",
        "asset_metadata": {},
        "created_at": datetime.now(timezone.utc),
    }
    defaults.update(overrides)
    return SimpleNamespace(**defaults)

def _service(scan_id, asset_id, **overrides):
    defaults = {
        "id": uuid4(),
        "scan_id": scan_id,
        "asset_id": asset_id,
        "host": "203.0.113.10",
        "port": 443,
        "protocol": "tcp",
        "service_name": "https",
        "product": "nginx",
        "version": "1.20",
        "tls_enabled": True,
        "state": "open",
        "created_at": datetime.now(timezone.utc),
    }
    defaults.update(overrides)
    return SimpleNamespace(**defaults)

def _finding(scan_id, *, asset_id=None, service_id=None, **overrides):
    defaults = {
        "id": uuid4(),
        "scan_id": scan_id,
        "asset_id": asset_id,
        "service_id": service_id,
        "severity": Severity.CRITICAL,
        "cvss_score": 9.8,
        "cve_id": "CVE-2024-0001",
        "status": FindingStatus.OPEN,
        "title": "Example finding",
        "source": "nmap",
        "is_verified": True,
        "evidence": {},
        "created_at": datetime.now(timezone.utc),
    }
    defaults.update(overrides)
    return SimpleNamespace(**defaults)

class _ScalarsResult:
    def __init__(self, items):
        self._items = items

    def scalars(self):
        return self

    def all(self):
        return self._items

def _make_db(assets, services, technologies, findings):
    db = AsyncMock()
    results = iter(
        [
            _ScalarsResult(assets),
            _ScalarsResult(services),
            _ScalarsResult(technologies),
            _ScalarsResult(findings),
        ]
    )
    db.execute = AsyncMock(side_effect=lambda *_a, **_k: next(results))
    return db

#happy path for get graph
@pytest.mark.asyncio
async def test_get_graph_builds_domain_asset_service_finding_chain():
    scan = _scan()
    asset = _asset(scan.id)
    service = _service(scan.id, asset.id)
    finding = _finding(scan.id, asset_id=asset.id, service_id=service.id)

    db = _make_db([asset], [service], [], [finding])

    result = await GraphService.get_graph(db, scan)
    #assert the node
    node_types = {n.type for n in result.nodes}
    assert node_types == {"domain", "asset", "service", "finding"}

    domain_node = next(n for n in result.nodes if n.type == "domain")
    asset_node = next(n for n in result.nodes if n.type == "asset")
    service_node = next(n for n in result.nodes if n.type == "service")

    # risk add up from the finding to asset/service/domain
    assert domain_node.risk.finding_count == 1
    assert asset_node.risk.severity == "critical"
    assert service_node.risk.max_cvss == 9.8

    edge_types = {e.type for e in result.edges}
    assert edge_types == {"RESOLVES_TO", "EXPOSES", "AFFECTED_BY"}

#empty scan for get graph
@pytest.mark.asyncio
async def test_get_graph_skips_technology_node_when_no_data():
    scan = _scan()
    db = _make_db([], [], [], [])

    result = await GraphService.get_graph(db, scan)

    assert len(result.nodes) == 1
    assert result.nodes[0].type == "domain"
    assert result.edges == []

#happy path for GraphService.get_node
@pytest.mark.asyncio
async def test_get_node_returns_relationship_counts_and_findings():
    scan = _scan()
    asset = _asset(scan.id)
    finding = _finding(scan.id, asset_id=asset.id)

    db = _make_db([asset], [], [], [finding])

    detail = await GraphService.get_node(db, scan, f"asset:{asset.id}")

    assert detail.relationships.incoming == 1
    assert detail.relationships.outgoing == 1
    assert len(detail.findings) == 1
    assert detail.findings[0].id == finding.id

#404 when get nodes
@pytest.mark.asyncio
async def test_get_node_raises_404_for_unknown_node():
    scan = _scan()
    db = _make_db([], [], [], [])

    with pytest.raises(HTTPException) as exc_info:
        await GraphService.get_node(db, scan, "asset:does-not-exist")

    assert exc_info.value.status_code == 404