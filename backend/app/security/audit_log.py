"""
Tamper-Evident Audit Logging & Compliance (FR-19, FR-20, CERT-In) — a
hash-chained, append-only audit trail per PRD Section 6.6. Each entry
embeds the SHA-256 hash of the previous entry, so altering or deleting any
past entry breaks the chain and is detectable via verify_chain().

Backed by the AUDIT_LOGS table (SQLAlchemy) rather than an in-memory store,
so the chain survives process restarts, matching the >=180-day retention
requirement (NFR-10).
"""
import hashlib
import json
import time
from dataclasses import dataclass, asdict
from sqlalchemy.orm import Session
from sqlalchemy import asc

from app import models

GENESIS = "GENESIS"


@dataclass
class AuditEntry:
    ts: float
    actor: str
    action: str
    detail: str
    prev_hash: str

    def compute_hash(self) -> str:
        payload = json.dumps(asdict(self), sort_keys=True).encode()
        return hashlib.sha256(payload).hexdigest()


class AuditLog:
    """Append-only, hash-chained audit trail (FR-19/FR-20, retained >= 180 days)."""

    def __init__(self, db: Session):
        self.db = db

    def _get_last_hash(self) -> str:
        last = (
            self.db.query(models.AuditLog)
            .order_by(models.AuditLog.timestamp.desc())
            .first()
        )
        return last.entry_hash if last and last.entry_hash else GENESIS

    def record(self, actor: str, action: str, detail: str) -> str:
        prev_hash = self._get_last_hash()
        entry = AuditEntry(ts=time.time(), actor=actor or "anonymous", action=action, detail=detail or "", prev_hash=prev_hash)
        entry_hash = entry.compute_hash()

        row = models.AuditLog(
            user_id=actor if actor and actor != "anonymous" else None,
            action=action,
            resource=detail,
            ts_float=entry.ts,
            prev_hash=prev_hash,
            entry_hash=entry_hash,
        )
        self.db.add(row)
        self.db.commit()
        return entry_hash

    def verify_chain(self) -> dict:
        """Walks the full chain and confirms no entry's content was altered and no
        entry was reordered or removed. Recomputes each entry's hash from its
        exact stored fields (ts_float, actor, action, detail, prev_hash) and
        compares against the stored entry_hash — any DB-level tampering with a
        row's content, not just chain linkage, is detected."""
        rows = self.db.query(models.AuditLog).order_by(asc(models.AuditLog.timestamp)).all()
        prev = GENESIS
        for row in rows:
            entry = AuditEntry(
                ts=row.ts_float if row.ts_float is not None else 0.0,
                actor=row.user_id or "anonymous",
                action=row.action,
                detail=row.resource or "",
                prev_hash=row.prev_hash or GENESIS,
            )
            if row.prev_hash != prev:
                return {"valid": False, "broken_at": row.log_id, "reason": "chain linkage broken (prev_hash mismatch)"}
            if entry.compute_hash() != row.entry_hash:
                return {"valid": False, "broken_at": row.log_id, "reason": "entry content does not match stored hash (tampered)"}
            prev = row.entry_hash
        return {"valid": True, "entries_checked": len(rows)}
