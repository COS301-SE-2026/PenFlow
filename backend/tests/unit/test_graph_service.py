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

#error path when get nodes
@pytest.mark.asyncio
async def test_get_node_raises_404_for_unknown_node():
    scan = _scan()
    db = _make_db([], [], [], [])

    with pytest.raises(HTTPException) as exc_info:
        await GraphService.get_node(db, scan, "asset:does-not-exist")

    assert exc_info.value.status_code == 404

#happy path for get summary
@pytest.mark.asyncio
async def test_get_summary_counts_and_concentrations():
    scan = _scan()
    asset = _asset(scan.id)
    service = _service(scan.id, asset.id)
    findings = [
        _finding(scan.id, asset_id=asset.id, service_id=service.id, severity=Severity.CRITICAL),
        _finding(scan.id, asset_id=asset.id, service_id=service.id, severity=Severity.HIGH),
    ]

    db = _make_db([asset], [service], [], findings)

    summary = await GraphService.get_summary(db, scan)

    assert summary.counts.assets == 1
    assert summary.counts.services == 1
    assert summary.counts.findings == 2
    assert summary.risk.critical_findings == 1
    assert summary.risk.high_findings == 1
    assert summary.risk.affected_assets == 1
    assert len(summary.concentrations) >= 1
    assert summary.concentrations[0].finding_count == 2

#graph service denies non owner  
@pytest.mark.asyncio
@patch("app.services.graph_service.ScanRepository.get_scan_by_id", new_callable=AsyncMock)
async def test_require_scan_access_denies_non_owner(mock_get_scan):
    scan = _scan(user_id=uuid4())
    mock_get_scan.return_value = scan
    other_user = SimpleNamespace(id=uuid4(), role="client")

    with pytest.raises(HTTPException) as exc_info:
        await GraphService.require_scan_access(AsyncMock(), scan.id, other_user)

    assert exc_info.value.status_code == 404


# happy-path for get path
@pytest.mark.asyncio
async def test_get_paths_traces_domain_to_finding_chain():
    scan = _scan()
    asset = _asset(scan.id)
    service = _service(scan.id, asset.id)
    finding = _finding(scan.id, asset_id=asset.id, service_id=service.id)

    db = _make_db([asset], [service], [], [finding])

    result = await GraphService.get_paths(db, scan)

    assert len(result.paths) == 1
    path = result.paths[0]
    assert path.nodes == [
        f"domain:{scan.domain}",
        f"asset:{asset.id}",
        f"service:{service.id}",
        f"finding:{finding.id}",
    ]
    assert len(path.edges) == 3

#test filtering of get path
@pytest.mark.asyncio
async def test_get_paths_filters_by_severity_and_respects_limit():
    scan = _scan()
    asset = _asset(scan.id)
    critical = _finding(scan.id, asset_id=asset.id, severity=Severity.CRITICAL)
    low = _finding(scan.id, asset_id=asset.id, severity=Severity.LOW)

    db = _make_db([asset], [], [], [critical, low])

    result = await GraphService.get_paths(db, scan, severity="high")

    assert len(result.paths) == 1
    assert result.paths[0].nodes[-1] == f"finding:{critical.id}"

#test get get_neighborhood
@pytest.mark.asyncio
async def test_get_neighborhood_depth_one_excludes_grandchildren():
    scan = _scan()
    asset = _asset(scan.id)
    service = _service(scan.id, asset.id)
    finding = _finding(scan.id, service_id=service.id)

    db = _make_db([asset], [service], [], [finding])

    result = await GraphService.get_neighborhood(
        db, scan, f"asset:{asset.id}", depth=1
    )

    node_ids = {n.id for n in result.nodes}
    assert node_ids == {f"domain:{scan.domain}", f"asset:{asset.id}", f"service:{service.id}"}
    assert f"finding:{finding.id}" not in node_ids

#error path of get neighbourhood
@pytest.mark.asyncio
async def test_get_neighborhood_unknown_node_raises_404():
    scan = _scan()
    db = _make_db([], [], [], [])

    with pytest.raises(HTTPException) as exc_info:
        await GraphService.get_neighborhood(db, scan, "asset:does-not-exist")

    assert exc_info.value.status_code == 404

#compare action after change node 
@pytest.mark.asyncio
async def test_compare_scans_detects_added_removed_and_changed():
    current_scan = _scan(domain="example.com")
    previous_scan = _scan(domain="example.com")

    # same logical asset exists in both scans, but its DB id differs
    current_asset = _asset(current_scan.id, identifier="203.0.113.10")
    previous_asset = _asset(previous_scan.id, identifier="203.0.113.10")

    # finding only present in the current scan , plus another finding
    #on the same asset so its finding_count differs from the previous scan
    new_finding = _finding(
        current_scan.id, asset_id=current_asset.id, title="New critical finding"
    )
    extra_finding = _finding(
        current_scan.id, asset_id=current_asset.id, title="Second finding on asset"
    )
    # finding only present in the previous scan 
    old_finding = _finding(
        previous_scan.id, asset_id=previous_asset.id, title="Old resolved finding"
    )

    # compare_scans loads the current scan's data first, then the previous
    db = AsyncMock()
    results = iter(
        [
            _ScalarsResult([current_asset]),
            _ScalarsResult([]),
            _ScalarsResult([]),
            _ScalarsResult([new_finding, extra_finding]),
            _ScalarsResult([previous_asset]),
            _ScalarsResult([]),
            _ScalarsResult([]),
            _ScalarsResult([old_finding]),
        ]
    )
    db.execute = AsyncMock(side_effect=lambda *_a, **_k: next(results))

    result = await GraphService.compare_scans(db, current_scan, previous_scan)

    assert set(result.added_nodes) == {
        f"finding:{new_finding.id}",
        f"finding:{extra_finding.id}",
    }
    assert result.removed_nodes == [f"finding:{old_finding.id}"]

    # the asset itself is unchanged in identity but its finding_count changed
    changed_ids = {c.node_id for c in result.changed_nodes}
    assert any(cid.startswith("asset:") for cid in changed_ids)

    assert result.risk_change["critical_findings"].current == 2
    assert result.risk_change["critical_findings"].previous == 1