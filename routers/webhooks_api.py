"""
Webhooks API Router - Phase 3C
Endpoints for managing webhooks and event subscriptions
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
import logging

from deps import get_db
from webhook_service import WebhookManager, WebhookEventQueue, WebhookEventType

log = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/webhooks", tags=["webhooks"])


class WebhookRequest:
    def __init__(self, url: str, events: List[str], secret: Optional[str] = None):
        self.url = url
        self.events = events
        self.secret = secret


class WebhookTestRequest:
    def __init__(self, event_type: str, payload: dict):
        self.event_type = event_type
        self.payload = payload


@router.post("/register", summary="Register Webhook")
async def register_webhook(
    url: str = Query(..., description="Webhook URL"),
    events: str = Query(..., description="Comma-separated event types"),
    secret: Optional[str] = Query(None, description="Webhook secret for signature verification"),
    db: Session = Depends(get_db)
):
    """Register a new webhook endpoint for event notifications"""
    try:
        event_list = [e.strip() for e in events.split(",")]
        
        # Validate events
        valid_events = [e.value for e in WebhookEventType]
        invalid_events = [e for e in event_list if e not in valid_events]
        if invalid_events:
            raise HTTPException(status_code=400, detail=f"Invalid events: {invalid_events}")
        
        result = await WebhookManager.register_webhook(
            db,
            webhook_url=url,
            events=event_list,
            secret=secret
        )
        
        if not result["success"]:
            raise HTTPException(status_code=400, detail=result.get("error"))
        
        return result["data"]
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error registering webhook: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/list", summary="List Webhooks")
async def list_webhooks(db: Session = Depends(get_db)):
    """Get list of all registered webhooks"""
    try:
        result = await WebhookManager.list_webhooks(db)
        
        if not result["success"]:
            raise HTTPException(status_code=400, detail=result.get("error"))
        
        return result["data"]
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error listing webhooks: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/test", summary="Test Webhook")
async def test_webhook(
    webhook_id: str = Query(..., description="Webhook ID"),
    event_type: str = Query(..., description="Event type to test"),
    db: Session = Depends(get_db)
):
    """Send a test event to a webhook"""
    try:
        # Validate event type
        valid_events = [e.value for e in WebhookEventType]
        if event_type not in valid_events:
            raise HTTPException(status_code=400, detail=f"Invalid event type: {event_type}")
        
        # Create test payload
        test_payload = {
            "test": True,
            "event_type": event_type,
            "timestamp": datetime.utcnow().isoformat(),
            "data": {"message": "This is a test webhook event"}
        }
        
        result = await WebhookManager.trigger_webhook(db, event_type, test_payload)
        
        if not result["success"]:
            raise HTTPException(status_code=400, detail=result.get("error"))
        
        return {
            "message": "Test webhook sent",
            "webhook_id": webhook_id,
            "event_type": event_type,
            "data": result["data"]
        }
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error testing webhook: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/delete/{webhook_id}", summary="Delete Webhook")
async def delete_webhook(
    webhook_id: str,
    db: Session = Depends(get_db)
):
    """Delete a registered webhook"""
    try:
        result = await WebhookManager.delete_webhook(db, webhook_id)
        
        if not result["success"]:
            raise HTTPException(status_code=404, detail=result.get("error"))
        
        return result["data"]
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error deleting webhook: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/events/{event_type}/status", summary="Get Event Status")
async def get_event_status(
    event_type: str,
    db: Session = Depends(get_db)
):
    """Get delivery status for a specific event type"""
    try:
        # Validate event type
        valid_events = [e.value for e in WebhookEventType]
        if event_type not in valid_events:
            raise HTTPException(status_code=400, detail=f"Invalid event type: {event_type}")
        
        result = await WebhookEventQueue.get_event_status(db, event_type)
        
        if not result["success"]:
            raise HTTPException(status_code=400, detail=result.get("error"))
        
        return result["data"]
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error getting event status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/retry-failed", summary="Retry Failed Webhook Deliveries")
async def retry_failed_webhooks(db: Session = Depends(get_db)):
    """Retry delivery of failed webhook events"""
    try:
        result = await WebhookManager.retry_failed_webhooks(db)
        
        if not result["success"]:
            raise HTTPException(status_code=400, detail=result.get("error"))
        
        return result["data"]
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error retrying failed webhooks: {e}")
        raise HTTPException(status_code=500, detail=str(e))
