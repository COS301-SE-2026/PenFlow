import logging
import secrets

import dns.resolver
import dns.exception

from app.models.verified_domain import DomainVerificationCode

class VerificationService:
    @staticmethod
    def generate_txt_token() -> str:
        """Generates a secure, random token for DNS TXT verification."""
        return f"penflow-verification={secrets.token_hex(32)}"


    @staticmethod
    def verify_dns_txt(domain: str, expected_token: str) -> DomainVerificationCode:
        """
        Queries the domain's TXT records.
        Returns True if the expected token is found, otherwise False.
        """
        try:
            answers = dns.resolver.resolve(domain, 'TXT')

            for rdata in answers:

                txt_record = b"".join(rdata.strings).decode('utf-8')

                if txt_record == expected_token:
                    return DomainVerificationCode.VERIFIED
                
            return DomainVerificationCode.TOKEN_MISMATCH

        except(dns.resolver.NXDOMAIN, dns.resolver.NoAnswer):
            return DomainVerificationCode.RECORD_NOT_FOUND
        
        except(dns.resolver.NoNameservers, dns.exception.Timeout):
            return DomainVerificationCode.LOOKUP_FAILED
        
        except Exception:
            return DomainVerificationCode.LOOKUP_FAILED