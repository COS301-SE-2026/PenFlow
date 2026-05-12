#I am just going to implement a rought draft so long until we get the worker logic figured out

from pydamic import BaseModel,Field,EmailStr #The email logic here is for the download we discussed, not any sort of auth
from uuid import UUID
from enum import Enum

class ScanStatus(str,Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"

class InitiateScanRequest(BaseModel):
    domain: str = Field(...,description="The target domain to scan",example="exmpl.com")
    email: EmailStr | None = Field(None,description="email to send the report to")

class InitiateScanResponse(BaseModel):
    scan_id: UUID
    status: ScanStatus