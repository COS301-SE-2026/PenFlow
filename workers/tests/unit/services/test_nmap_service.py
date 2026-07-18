from unittest.mock import MagicMock, patch

import nmap
import pytest

from app.services.nmap_service import run_live_nmap_scan


#Happy Path 1
#Valid target with multiple open ports should return data
@patch("app.services.nmap_service.nmap.PortScanner")
def test_run_live_nmap_scan_success(mock_scanner):

    scanner = MagicMock()
    mock_scanner.return_value = scanner
    scanner.all_hosts.return_value = ["1.1.1.1"]
    host = MagicMock()
    host.state.return_value = "up"
    host.__contains__.side_effect = \
    (
        lambda key: key in
        [
            "hostnames",
            "tcp",
        ]
    )

    host.__getitem__.side_effect = lambda key: \
    {
        "hostnames":
        [
            {"name": "hackerone.com"}
        ],
        "tcp":
        {
            22:
            {
                "state": "open",
                "name": "ssh",
                "product": "CoolSSH",
                "version": "9.0",
                "extrainfo": "Ubuntu",
                "script": {},
            },
            80:
            {
                "state": "open",
                "name": "http",
                "product": "Apache",
                "version": "2.4",
                "extrainfo": "",
                "script": {},
            },
        },
    }[key]

    scanner.__getitem__.return_value = host

    result = run_live_nmap_scan\
    (
        "1.1.1.1",
        "standard",
    )

    assert result["status"] == "up"
    assert len(result["ports"]) == 2
    assert result["ports"][0]["service"] == "ssh"
    assert result["ports"][1]["service"] == "http"


#Sad Path 1
#Unsupported scan profile
def test_invalid_profile():

    with (pytest.raises(ValueError)):

        run_live_nmap_scan\
        (
            "1.1.1.1",
            "invalid",
        )


#Sad Path 2
#Host does not respond
@patch("app.services.nmap_service.nmap.PortScanner")
def test_host_down(mock_scanner):

    scanner = MagicMock()
    mock_scanner.return_value = scanner
    scanner.all_hosts.return_value = []
    result = run_live_nmap_scan\
    (
        "1.1.1.1",
        "standard",
    )

    assert result["status"] == "down"
    assert result["ports"] == []


#Happy Path 2
#IPv6 target
@patch("app.services.nmap_service.nmap.PortScanner")
def test_ipv6_adds_dash6(mock_scanner):

    scanner = MagicMock()
    mock_scanner.return_value = scanner

    scanner.all_hosts.return_value = []

    run_live_nmap_scan\
    (
        "2001:0df8:00f2::06ee:0000:0f11",
        "standard",
    )
    #needed for ipv6
    assert "-6" in scanner.scan.call_args.kwargs["arguments"]


#Sad Path 3
#Nmap error
@patch("app.services.nmap_service.nmap.PortScanner")
def test_portscanner_error(mock_scanner):

    scanner = MagicMock()
    mock_scanner.return_value = scanner
    scanner.scan.side_effect = nmap.PortScannerError("Whoops")
    with (pytest.raises(nmap.PortScannerError)):

        run_live_nmap_scan\
        (
            "1.1.1.1",
            "standard",
        )