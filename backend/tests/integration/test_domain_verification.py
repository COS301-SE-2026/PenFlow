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

from app.main import app
from app.models.user import app
from app.models.user import User

class FakeDnsServer:
    # Real authorized dns server on 127.0.0.1

    
    def __init__(self) -> None:
        self.records: dict[str,str| None] = {}
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(("127.0.0.1",0))
        self.port = self.sock.getsockname()[1]
        self.sock.settimeout(0.5)
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._serve,daemon=True)
        self._thread.start()

    def stop(self) -> None :
        self._stop.set()
        self._thread.join(timeout=2)
        self.sock.close()

    def self_txt(self, domain:str , value:str | None ) -> None:
    #no record publish
     self.records[domain.rstrip(".").lower()] = value

    def _serve(self) -> None:
        while not self._stop.is_set():
            try:
                data, addr  = self.sock.recvfrom(4096)
            except socket.timeout:
                continue
            try:
               request =dns.message.from_wire(data)
               self.sock.sendto(self._answer(request).to_wire(),addr)
            except Exception:
                continue

    def _answer(self, request: dns.message.Message) -> dns.message.Message
        response = dns.message.make_response(request)
        qname = request.question[0].name
        value =self.records.get(qname.to_text().rstrip(".").lower())

        if value is None:
            response.set_rcode(dns.rcode.NXDOMAIN)
            return response

        response.answer.append(
            dns.rrset.from_text(qname,60,dns.rdataclass.IN,dns.rdatatype.TXT,f'"{value}"')
        )
        return response