from enum import Enum
from typing import Optional
from pydantic import BaseModel


class LeadStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"
    REVIEW = "review"
    JUNK = "junk"


class Lead(BaseModel):
    id: str
    email: str
    name: Optional[str] = ""
    school: Optional[str] = ""
    district: Optional[str] = ""
    state: Optional[str] = ""
    phone: Optional[str] = ""
    designation: Optional[str] = ""
    grade: Optional[str] = ""
    subject: Optional[str] = ""
    source: Optional[str] = ""
    status: LeadStatus = LeadStatus.PENDING


class PipelineResult(BaseModel):
    run_id: str
    lead_id: str
    status: str
    context: dict = {}
