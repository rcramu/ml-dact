"""Governance / audit trail (req.md Sec. 48)."""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from .. import models as m
from .. import serializers as ser
from ..database import get_db

router = APIRouter(prefix="/audit", tags=["Governance & Audit"])


@router.get("", summary="List audit log entries — every promote/reject/rollback/block decision")
def list_audit(db: Session = Depends(get_db), action: str | None = None, limit: int = Query(100, le=500)):
    q = db.query(m.AuditLog)
    if action:
        q = q.filter(m.AuditLog.action == action)
    rows = q.order_by(m.AuditLog.created_at.desc()).limit(limit).all()
    return [ser.audit_log_dict(a) for a in rows]
