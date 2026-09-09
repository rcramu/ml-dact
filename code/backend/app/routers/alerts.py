"""Alerts — Slack/PagerDuty-style notifications (req.md Sec. 37-38)."""
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from .. import models
from .. import serializers as ser
from ..database import get_db

router = APIRouter(prefix="/alerts", tags=["Alerts"])


@router.get("", summary="List alerts")
def list_alerts(db: Session = Depends(get_db), severity: str | None = None, resolved: bool | None = None, limit: int = Query(100, le=500)):
    q = db.query(models.Alert)
    if severity:
        q = q.filter(models.Alert.severity == severity.upper())
    if resolved is not None:
        q = q.filter(models.Alert.resolved == resolved)
    rows = q.order_by(models.Alert.created_at.desc()).limit(limit).all()
    return [ser.alert_dict(a) for a in rows]


@router.post("/{alert_id}/resolve", summary="Mark an alert resolved")
def resolve_alert(alert_id: str, db: Session = Depends(get_db)):
    alert = db.query(models.Alert).filter_by(id=alert_id).one_or_none()
    if alert is None:
        raise HTTPException(404, "alert not found")
    alert.resolved = True
    alert.resolved_at = datetime.utcnow()
    db.commit()
    return {"id": alert.id, "resolved": True}
