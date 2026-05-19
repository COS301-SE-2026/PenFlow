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
      value = re.sub(r'^https?://', '', value, flags=re.IGNORECASE)
      value = value.split('/')[0]
      value = value.split(':')[0]
      value = re.sub(r'<[^>]*>', '', value)
      return value.strip().lower()

  _DOMAIN_REGEX = re.compile(
      r'^(?:[a-zA-Z0-9](?:[a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,63}$'
  )

