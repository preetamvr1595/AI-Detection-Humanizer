from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, EmailStr, Field


class UserCreate(BaseModel):
    full_name: str
    email: EmailStr
    password: str = Field(min_length=8)
    institution: Optional[str] = "GM University"


class UserLogin(BaseModel):
    email: EmailStr
    password: str
    totp_code: Optional[str] = None


class UserOut(BaseModel):
    user_id: str
    full_name: str
    email: str
    role: str
    institution: str
    mfa_enabled: bool = False

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class DocumentOut(BaseModel):
    doc_id: str
    file_name: str
    file_type: str
    scan_status: str
    uploaded_at: datetime

    class Config:
        from_attributes = True


class PlagiarismMatchOut(BaseModel):
    matched_source: str
    similarity_score: float
    match_type: Optional[str] = None
    segment_preview: str

    class Config:
        from_attributes = True


class JobOut(BaseModel):
    job_id: str
    doc_id: str
    file_name: Optional[str] = None
    status: str
    ai_score: Optional[float] = None
    plagiarism_score: Optional[float] = None
    fact_check_score: Optional[float] = None
    readability_grade: Optional[str] = None
    started_at: datetime
    completed_at: Optional[datetime] = None
    plagiarism_matches: List[PlagiarismMatchOut] = []

    ai_detection_detail: Optional[Dict[str, Any]] = None
    grammar_readability_detail: Optional[Dict[str, Any]] = None
    citation_detail: Optional[Dict[str, Any]] = None
    paraphrase_detail: Optional[Dict[str, Any]] = None
    extraction_diagnostics: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True


class DashboardSummary(BaseModel):
    total_submissions: int
    ai_flagged_rate: float
    avg_plagiarism_score: float
    security_incidents: int


class AuditChainStatus(BaseModel):
    valid: bool
    entries_checked: Optional[int] = None
    broken_at: Optional[str] = None
    reason: Optional[str] = None
