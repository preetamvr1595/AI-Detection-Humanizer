"""
SQLAlchemy models — mirror the ER Diagram in the Phase 2 Software Design
document (USERS, DOCUMENTS, ANALYSIS_JOBS, *_RESULTS, REPORTS, AUDIT_LOGS).
"""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Float, Text, JSON, Integer
from sqlalchemy.orm import relationship
from app.core.database import Base


def gen_uuid():
    return str(uuid.uuid4())


class User(Base):
    __tablename__ = "users"
    user_id = Column(String, primary_key=True, default=gen_uuid)
    full_name = Column(String(150), nullable=False)
    email = Column(String(150), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(50), default="Student")  # Student | Researcher | Admin | Analyst
    institution = Column(String(150), default="GM University")
    mfa_enabled = Column(Boolean, default=False)
    mfa_secret = Column(String(64), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    documents = relationship("Document", back_populates="owner")


class Document(Base):
    __tablename__ = "documents"
    doc_id = Column(String, primary_key=True, default=gen_uuid)
    user_id = Column(String, ForeignKey("users.user_id"), nullable=False)
    file_name = Column(String(255), nullable=False)
    file_type = Column(String(10), nullable=False)
    file_hash = Column(String(64), unique=True, nullable=False)
    storage_uri = Column(Text, nullable=False)
    scan_status = Column(String(20), default="CLEAN")  # PENDING | CLEAN | INFECTED
    scan_engine = Column(String(50), nullable=True)  # e.g. "ClamAV 1.5.3"
    yara_findings = Column(JSON, nullable=True)
    uploaded_at = Column(DateTime, default=datetime.utcnow)

    owner = relationship("User", back_populates="documents")
    job = relationship("AnalysisJob", back_populates="document", uselist=False)


class AnalysisJob(Base):
    __tablename__ = "analysis_jobs"
    job_id = Column(String, primary_key=True, default=gen_uuid)
    doc_id = Column(String, ForeignKey("documents.doc_id"), nullable=False)
    status = Column(String(20), default="QUEUED")  # QUEUED | RUNNING | COMPLETE | FAILED
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    ai_score = Column(Float, nullable=True)
    plagiarism_score = Column(Float, nullable=True)
    fact_check_score = Column(Float, nullable=True)
    readability_grade = Column(String(50), nullable=True)

    ai_detection_detail = Column(JSON, nullable=True)
    grammar_readability_detail = Column(JSON, nullable=True)
    citation_detail = Column(JSON, nullable=True)
    paraphrase_detail = Column(JSON, nullable=True)
    plagiarism_match_matrix = Column(JSON, nullable=True)
    extraction_diagnostics = Column(JSON, nullable=True)

    document = relationship("Document", back_populates="job")
    report = relationship("Report", back_populates="job", uselist=False)
    plagiarism_matches = relationship("PlagiarismResult", back_populates="job")


class PlagiarismResult(Base):
    __tablename__ = "plagiarism_results"
    result_id = Column(String, primary_key=True, default=gen_uuid)
    job_id = Column(String, ForeignKey("analysis_jobs.job_id"), nullable=False)
    matched_source = Column(String(255))
    similarity_score = Column(Float)
    match_type = Column(String(50), nullable=True)
    segment_preview = Column(Text)

    job = relationship("AnalysisJob", back_populates="plagiarism_matches")


class Report(Base):
    __tablename__ = "reports"
    report_id = Column(String, primary_key=True, default=gen_uuid)
    job_id = Column(String, ForeignKey("analysis_jobs.job_id"), nullable=False)
    file_uri = Column(Text, nullable=False)
    signature_hash = Column(String(64))  # SHA-256 digest of the plaintext PDF
    rsa_signature = Column(Text, nullable=True)  # base64 RSA-PSS signature over the digest
    aes_encrypted_path = Column(Text, nullable=True)  # path to AES-256-GCM encrypted copy at rest
    generated_at = Column(DateTime, default=datetime.utcnow)

    job = relationship("AnalysisJob", back_populates="report")


class AuditLog(Base):
    __tablename__ = "audit_logs"
    log_id = Column(String, primary_key=True, default=gen_uuid)
    user_id = Column(String, ForeignKey("users.user_id"), nullable=True)
    action = Column(String(100), nullable=False)
    resource = Column(String(255))
    timestamp = Column(DateTime, default=datetime.utcnow)
    ts_float = Column(Float, nullable=True)
    prev_hash = Column(String(64), nullable=True)
    entry_hash = Column(String(64), nullable=True)
