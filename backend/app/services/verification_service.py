import secrets
import dns.resolver
from fastapi import HTTPException, status

class VerificationService:
    @staticmethod
    def generate_txt_token() -> str:
        """Generates a secure, random token for DNS TXT verification."""
        return f"penflow-verification={secrets.token_hex(32)}"

    @staticmethod
    def verify_dns_txt(domain: str, expected_token: str) -> bool:
        """
        Queries the domain's TXT records.
        Returns True if the expected token is found, otherwise False.
        """
        try:
            answers = dns.resolver.resolve(domain, 'TXT')

            for rdata in answers:
                txt_record = b"".join(rdata.strings).decode('utf-8')

                if txt_record == expected_token:
                    return True
            return False

        except dns.resolver.NXDOMAIN:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Domain does not exist.")
        except (dns.resolver.NoAnswer, dns.resolver.NoNameservers):
            return False
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"DNS lookup failed: {str(e)}")