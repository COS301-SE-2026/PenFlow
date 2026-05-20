from unittest.mock import patch, MagicMock
from app.services.dns_whois_service import run_dns_whois

#live happy path
@patch("app.services.dns_whois_service.whois.whois")
@patch("app.services.dns_whois_service.dns.resolver.resolve")
@patch("app.services.dns_whois_service.SCAN_MODE", "LIVE")
def test_dns_whois_live_happy_path(mock_dns, mock_whois):
    """Test that native DNS and WHOIS libraries execute and parse correctly."""
    
    #fake dns responses based on query type using a side_effect function
    def dns_side_effect(_domain, qtype):
        if qtype == 'MX':
            mock_mx = MagicMock()
            mock_mx.__str__.return_value = "10 aspmx.l.google.com"
            return [mock_mx]
        elif qtype == 'TXT':
            m1 = MagicMock()
            m1.__str__.return_value = "v=spf1 include:_spf.google.com ~all"
            m2 = MagicMock()
            m2.__str__.return_value = "v=dmarc1; p=none"
            m3 = MagicMock()
            m3.__str__.return_value = "slack-domain-verification=123"
            return [m1, m2, m3]
        raise ValueError("No records found")
        
    mock_dns.side_effect = dns_side_effect

    #fake whois response
    mock_w = MagicMock()
    mock_w.registrar = "GoDaddy"
    mock_w.creation_date = ["2000-01-01"]
    mock_w.expiration_date = "2025-01-01"
    mock_w.name_servers = ["ns1.google.com"]
    mock_whois.return_value = mock_w

    #execution
    result = run_dns_whois("acorns.com")

    #assertions
    assert result["status"] == "completed"
    assert mock_dns.call_count == 2
    assert mock_whois.called
    security_data = result["raw_result"]["domain_security"]
    assert "Google Workspace" in security_data["detected_services"]
    assert "Slack" in security_data["detected_services"]
    
    #verify findings logic works (should pass MX, SPF, DMARC so 0 findings)
    assert len(result["findings"]) == 0


#sad path for network/library outage
@patch("app.services.dns_whois_service.whois.whois")
@patch("app.services.dns_whois_service.dns.resolver.resolve")
@patch("app.services.dns_whois_service.SCAN_MODE", "LIVE")
def test_dns_whois_live_failure(mock_dns, mock_whois):
    """Test that missing records and WHOIS crashes are handled gracefully."""
    
    #force both libraries to throw exceptions
    mock_dns.side_effect = ValueError("DNS Timeout")
    mock_whois.side_effect = ValueError("WHOIS Socket Error")
    result = run_dns_whois("acorns.com")
    assert result["status"] == "completed"
    #should return empty lists and error messages, not crash
    #verify DNS failure is handled
    assert len(result["findings"]) == 2
    finding_titles = [f["title"] for f in result["findings"]]
    assert "Missing SPF Record" in finding_titles
    assert "Missing DMARC Record" in finding_titles


#mock fallback path
@patch("app.services.dns_whois_service.whois.whois")
@patch("app.services.dns_whois_service.dns.resolver.resolve")
@patch("app.services.dns_whois_service.SCAN_MODE", "MOCK")
def test_dns_whois_fallback_to_mock(mock_dns, mock_whois):
    """Test that MOCK mode safely bypasses native libraries and loads local data."""
    
    #execution
    result = run_dns_whois("acorns.com")
    assert not mock_dns.called
    assert not mock_whois.called
    assert result["status"] == "completed"