#Phase 2 intergration test
#create a local dns server that answers the txt lookup to show dns txt 
#no mock

import socket
import threading
from uuid import UUID

import dns.asyncresolver
import dns.message
import dns.rcode
import dns.rdataclass
import dns.rdatatype
import dns.rrset
import pytest
import pytest_asyncio
from fastapi import status

from app.api.middleware.auth import get_current_user
from app.main import app
from app.models.user import User


class FakeDnsServer:
    # Real authorized dns server on 127.0.0.1

    def __init__(self) -> None:
        self.records: dict[str, str | None] = {}
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(("127.0.0.1", 0))
        self.port = self.sock.getsockname()[1]
        self.sock.settimeout(0.5)
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._serve, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        self._thread.join(timeout=2)
        self.sock.close()

    def set_txt(self, domain: str, value: str | None) -> None:  
        # no record publish
        self.records[domain.rstrip(".").lower()] = value  

    def _serve(self) -> None:
        while not self._stop.is_set():
            try:
                data, addr = self.sock.recvfrom(4096)
            except socket.timeout:
                continue
            try:
                request = dns.message.from_wire(data)
                self.sock.sendto(self._answer(request).to_wire(), addr)
            except Exception:
                continue

    def _answer(self, request: dns.message.Message) -> dns.message.Message:
        response = dns.message.make_response(request)
        qname = request.question[0].name
        value = self.records.get(qname.to_text().rstrip(".").lower())

        if value is None:
            response.set_rcode(dns.rcode.NXDOMAIN)
            return response

        response.answer.append(
            dns.rrset.from_text(qname, 60, dns.rdataclass.IN, dns.rdatatype.TXT, f'"{value}"')
        )
        return response



@pytest.fixture
def fake_dns_server():
    #Point the resolver at our fake server for the test, then restore it.
    server = FakeDnsServer()
    original_resolver = dns.asyncresolver.default_resolver

    test_resolver = dns.asyncresolver.Resolver(configure=False)
    test_resolver.nameservers = ["127.0.0.1"]
    test_resolver.port = server.port
    dns.asyncresolver.default_resolver = test_resolver

    yield server

    dns.asyncresolver.default_resolver = original_resolver
    server.stop()


async def _fake_user() -> dict:  
    return {"sub": "12345678-1234-5678-1234-567812345678", "role": "client"}


@pytest_asyncio.fixture(autouse=True)  #
async def _authenticated(db_session):
    """Every test runs as this user."""
    db_session.add(
        User(
            id=UUID("12345678-1234-5678-1234-567812345679"),
            auth_provider="keycloak",
            auth_provider_id="12345678-1234-5678-1234-567812345678",
            email="myemail@gmail.com",
            full_name="test user",
            role="client",
        )  
    )
    await db_session.flush()

    app.dependency_overrides[get_current_user] = _fake_user  
    yield
    app.dependency_overrides.pop(get_current_user, None)


async def _add_domain(test_client, domain: str) -> dict: 
    response = await test_client.post("/api/v1/domains/", json={"domain": domain})
    assert response.status_code == status.HTTP_201_CREATED
    return response.json()


#verify success when adding a domain real-dns-pass.com
#phase2
#POST /domains/{domain_id}/verify ,happy path verify domain fake dns
@pytest.mark.asyncio
async def test_verify_success(fake_dns_server, test_client):
    domain = await _add_domain(test_client, "real-dns-pass.com")
    fake_dns_server.set_txt("real-dns-pass.com", domain["verification_token"])

    response = await test_client.post(f"/api/v1/domains/{domain['id']}/verify")

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["status"]==  "verified"

#verify it token mismatch
@pytest.mark.asyncio
async def test_verify_token_mismatch(fake_dns_server, test_client):
    domain = await _add_domain(test_client, "real-dns-mismatch.com")
    fake_dns_server.set_txt("real-dns-mismatch.com", "penflow-verification=wrong-token")

    response = await test_client.post(f"/api/v1/domains/{domain['id']}/verify")

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "did not match" in response.json()["detail"]


#Error path
#verify when record not found
@pytest.mark.asyncio
async def test_verify_record_not_found( fake_dns_server, test_client):
    domain = await _add_domain( test_client, "real-dns-norecord.com")
    fake_dns_server.set_txt("real-dns-norecord.com", None)

    response = await test_client.post(f"/api/v1/domains/{domain['id']}/verify")

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "could not be found" in response.json()["detail"]


@pytest.mark.asyncio
async def test_verify_domain_not_found(test_client):
    fake_id = "00000000-0000-0000-0000-000000000000"

    response = await test_client.post(f"/api/v1/domains/{fake_id}/verify")

    assert response.status_code == status.HTTP_404_NOT_FOUND

#Error path
#test when a user is not authed 
@pytest.mark.asyncio
async def test_add_domain_requires_auth(test_client):
    app.dependency_overrides.pop(get_current_user, None)

    response = await test_client.post("/api/v1/domains/", json={"domain": "unauthed.com"})

    assert response.status_code == status.HTTP_401_UNAUTHORIZED

