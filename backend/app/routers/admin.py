from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.core.database import get_db
from app.core.security import require_admin
from app.security.audit_log import AuditLog
from app import models, schemas

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.get("/summary", response_model=schemas.DashboardSummary)
def summary(db: Session = Depends(get_db), admin=Depends(require_admin)):
    total = db.query(models.AnalysisJob).count()
    flagged = db.query(models.AnalysisJob).filter(models.AnalysisJob.ai_score >= 50).count()
    avg_plag = db.query(func.avg(models.AnalysisJob.plagiarism_score)).scalar() or 0.0
    incidents = db.query(models.Document).filter(models.Document.scan_status == "INFECTED").count()

    return schemas.DashboardSummary(
        total_submissions=total,
        ai_flagged_rate=round((flagged / total * 100), 1) if total else 0.0,
        avg_plagiarism_score=round(avg_plag, 1),
        security_incidents=incidents,
    )


@router.get("/users", response_model=list[schemas.UserOut])
def list_users(db: Session = Depends(get_db), admin=Depends(require_admin)):
    return db.query(models.User).all()


@router.get("/audit-logs")
def audit_logs(db: Session = Depends(get_db), admin=Depends(require_admin)):
    logs = db.query(models.AuditLog).order_by(models.AuditLog.timestamp.desc()).limit(200).all()
    return [
        {
            "log_id": l.log_id,
            "user_id": l.user_id,
            "action": l.action,
            "resource": l.resource,
            "timestamp": l.timestamp,
            "entry_hash": l.entry_hash,
        }
        for l in logs
    ]


@router.get("/audit-logs/verify", response_model=schemas.AuditChainStatus)
def verify_audit_chain(db: Session = Depends(get_db), admin=Depends(require_admin)):
    """Walks the full hash-chained audit log and confirms no entry has been
    tampered with, reordered, or removed (FR-19/FR-20 tamper-evidence proof)."""
    result = AuditLog(db).verify_chain()
    return schemas.AuditChainStatus(**result)
