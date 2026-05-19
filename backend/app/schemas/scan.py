from pydantic import BaseModel, Field, EmailStr, field_validator
from uuid import UUID
from enum import Enum
import re

class ScanStatus(str, Enum):
      PENDING = "pending"
      RUNNING = "running"
      COMPLETED = "completed"
      FAILED = "failed"

def _sanitize_domain(value: str) -> str:
    # Strip protocol (http:// or https://) 
      value = re.sub(r'^https?://', '', value, flags=re.IGNORECASE)
      # Strip paths and query parameters (e.g., example.com/api/login -> example.com)
      value = value.split('/')[0]
      # Strip explicit port numbers (e.g., example.com:8080 -> example.com)
      value = value.split(':')[0]
      # Strip simple HTML tags to prevent basic injection before deeper validation
      value = re.sub(r'<[^>]*>', '', value)
      # Remove surrounding whitespace and normalize to lowercase for DNS compatibility
      return value.strip().lower()

    
  _DOMAIN_REGEX = re.compile(
      r'^(?:[a-zA-Z0-9](?:[a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,63}$'
  )

# initiate scan report
class InitiateScanRequest(BaseModel):
      domain: str = Field(..., description="The target domain to scan", example="example.com")
      email: EmailStr | None = Field(None, description="Email to send the report to")

      @field_validator("domain", mode="before")
      @classmethod
      def sanitize_and_validate_domain(cls, v: str) -> str:
          cleaned = _sanitize_domain(v)
          if not cleaned:
              raise ValueError("Domain cannot be empty")
          if re.search(r'[<>"\';&]', cleaned):
              raise ValueError("Domain contains invalid characters")
          if len(cleaned) > 253:
              raise ValueError("Domain name is too long")
          if not _DOMAIN_REGEX.match(cleaned):
              raise ValueError("Invalid domain format — use example.com")
          return cleaned

