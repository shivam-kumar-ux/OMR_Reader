"""
Admin API: Audit Logs and System Settings.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional, List, Dict, Any
from pydantic import BaseModel

from backend.app.db.session import get_db
from backend.app.api.deps import get_current_user, require_admin
from backend.app.models.models import User, AuditLog
from backend.app.core.config import settings

router = APIRouter(prefix="/admin", tags=["Admin"])


class SettingsUpdateSchema(BaseModel):
    BUBBLE_FILL_THRESHOLD: Optional[float] = None
    BUBBLE_UNCERTAIN_LOW: Optional[float] = None
    OCR_NAME_SIMILARITY_THRESHOLD: Optional[float] = None


@router.get("/audit-logs")
def get_audit_logs(
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    action: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    Retrieve system audit logs for administrative tracking.
    """
    query = db.query(AuditLog)
    if action:
        query = query.filter(AuditLog.action == action)
    
    total = query.count()
    logs = query.order_by(AuditLog.timestamp.desc()).offset(offset).limit(limit).all()

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "items": [
            {
                "id": log.id,
                "user_id": log.user_id,
                "action": log.action,
                "entity_type": log.entity_type,
                "entity_id": log.entity_id,
                "old_values": log.old_values,
                "new_values": log.new_values,
                "ip_address": log.ip_address,
                "timestamp": log.timestamp.isoformat() if log.timestamp else None
            }
            for log in logs
        ]
    }


@router.get("/settings")
def get_system_settings(current_user: User = Depends(require_admin)):
    """
    Get current recognition and threshold settings.
    """
    return {
        "BUBBLE_FILL_THRESHOLD": settings.BUBBLE_FILL_THRESHOLD,
        "BUBBLE_UNCERTAIN_LOW": settings.BUBBLE_UNCERTAIN_LOW,
        "OCR_NAME_SIMILARITY_THRESHOLD": settings.OCR_NAME_SIMILARITY_THRESHOLD,
        "STORAGE_PROVIDER": settings.STORAGE_PROVIDER,
        "ENVIRONMENT": settings.ENVIRONMENT
    }


@router.put("/settings")
def update_system_settings(
    payload: SettingsUpdateSchema,
    current_user: User = Depends(require_admin)
):
    """
    Update runtime recognition thresholds.
    """
    if payload.BUBBLE_FILL_THRESHOLD is not None:
        settings.BUBBLE_FILL_THRESHOLD = payload.BUBBLE_FILL_THRESHOLD
    if payload.BUBBLE_UNCERTAIN_LOW is not None:
        settings.BUBBLE_UNCERTAIN_LOW = payload.BUBBLE_UNCERTAIN_LOW
    if payload.OCR_NAME_SIMILARITY_THRESHOLD is not None:
        settings.OCR_NAME_SIMILARITY_THRESHOLD = payload.OCR_NAME_SIMILARITY_THRESHOLD

    return {
        "message": "Settings updated successfully",
        "settings": {
            "BUBBLE_FILL_THRESHOLD": settings.BUBBLE_FILL_THRESHOLD,
            "BUBBLE_UNCERTAIN_LOW": settings.BUBBLE_UNCERTAIN_LOW,
            "OCR_NAME_SIMILARITY_THRESHOLD": settings.OCR_NAME_SIMILARITY_THRESHOLD
        }
    }
