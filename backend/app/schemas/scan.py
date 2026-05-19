from pydantic import BaseModel, Field, EmailStr, field_validator
from uuid import UUID
from enum import Enum
import re

class ScanStatus(str, Enum):
      PENDING = "pending"
      RUNNING = "running"
      COMPLETED = "completed"
      FAILED = "failed"