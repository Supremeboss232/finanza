"""
Webhook Service - Phase 3C
Manages webhook registration, delivery, verification, and retry logic
"""

from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
import logging
import hashlib
import hmac
import json
from enum import Enum
import asyncio

log = logging.getLogger(__name__)

# Webhook event types
class WebhookEventType(str, Enum):
    REGION_CREATED = "region.created"
    REGION_UPDATED = "region.updated"
    REGION_DEACTIVATED = "region.deactivated"
    CURRENCY_ENABLED = "currency.enabled"
    CURRENCY_ADDED = "currency.added"
    FX_RATE_UPDATED = "fx.rate_updated"
    TRANSFER_COMPLETED = "transfer.completed"
    TRANSFER_FAILED = "transfer.failed"
    COMPLIANCE_CHECK_FAILED = "compliance.check_failed"
    API_ERROR = "api.error"


# In-memory storage for webhooks (use database in production)
WEBHOOKS_STORE = {}
WEBHOOK_EVENTS_STORE = []
WEBHOOK_ID_COUNTER = 1000


class WebhookManager:
    """Manages webhook registration and lifecycle"""
    
    @staticmethod
    async def register_webhook(
        db: Session,
        webhook_url: str,
        events: List[str],
        secret: Optional[str] = None,
        max_retries: int = 3,
        retry_delay_seconds: int = 300
    ) -> dict:
        """Register a new webhook endpoint"""
        try:
            global WEBHOOK_ID_COUNTER
            
            # Generate webhook ID and secret
            webhook_id = f"wh_{WEBHOOK_ID_COUNTER}"
            WEBHOOK_ID_COUNTER += 1
            
            if not secret:
                secret = hashlib.sha256(f"{webhook_url}{datetime.utcnow().isoformat()}".encode()).hexdigest()
            
            webhook_data = {
                "id": webhook_id,
                "url": webhook_url,
                "events": events,
                "secret": secret,
                "max_retries": max_retries,
                "retry_delay_seconds": retry_delay_seconds,
                "is_active": True,
                "created_at": datetime.utcnow().isoformat(),
                "last_triggered_at": None,
                "total_deliveries": 0,
                "failed_deliveries": 0
            }
            
            WEBHOOKS_STORE[webhook_id] = webhook_data
            
            log.info(f"Webhook registered: {webhook_id} for events {events}")
            
            return {
                "success": True,
                "data": {
                    "webhook_id": webhook_id,
                    "url": webhook_url,
                    "events": events,
                    "secret": secret,
                    "message": "Webhook registered successfully"
                }
            }
        except Exception as e:
            log.error(f"Error registering webhook: {e}")
            return {"success": False, "error": str(e)}
    
    @staticmethod
    async def trigger_webhook(
        db: Session,
        event_type: str,
        payload: Dict[str, Any]
    ) -> dict:
        """Trigger webhooks for an event"""
        try:
            triggered_webhooks = []
            
            for webhook_id, webhook_data in WEBHOOKS_STORE.items():
                # Check if webhook is active and subscribed to this event
                if webhook_data["is_active"] and event_type in webhook_data["events"]:
                    
                    # Create event record
                    event_record = {
                        "webhook_id": webhook_id,
                        "event_type": event_type,
                        "payload": payload,
                        "created_at": datetime.utcnow().isoformat(),
                        "delivery_attempts": 0,
                        "delivered_at": None,
                        "delivery_status": "pending"
                    }
                    
                    WEBHOOK_EVENTS_STORE.append(event_record)
                    triggered_webhooks.append(webhook_id)
                    
                    # Queue for async delivery
                    asyncio.create_task(
                        WebhookManager._deliver_webhook(webhook_id, webhook_data, event_record)
                    )
            
            log.info(f"Webhook triggered for {event_type}: {len(triggered_webhooks)} webhooks queued")
            
            return {
                "success": True,
                "data": {
                    "event_type": event_type,
                    "triggered_webhooks": len(triggered_webhooks),
                    "webhook_ids": triggered_webhooks,
                    "timestamp": datetime.utcnow().isoformat()
                }
            }
        except Exception as e:
            log.error(f"Error triggering webhook: {e}")
            return {"success": False, "error": str(e)}
    
    @staticmethod
    async def _deliver_webhook(webhook_id: str, webhook_data: Dict, event_record: Dict) -> None:
        """Async webhook delivery with retry logic"""
        try:
            max_retries = webhook_data["max_retries"]
            retry_delay = webhook_data["retry_delay_seconds"]
            
            for attempt in range(max_retries):
                try:
                    # Simulate HTTP delivery (in production use actual HTTP client)
                    success = await WebhookManager._send_http_request(
                        webhook_data["url"],
                        event_record,
                        webhook_data["secret"]
                    )
                    
                    if success:
                        event_record["delivery_status"] = "delivered"
                        event_record["delivered_at"] = datetime.utcnow().isoformat()
                        webhook_data["total_deliveries"] += 1
                        webhook_data["last_triggered_at"] = datetime.utcnow().isoformat()
                        log.info(f"Webhook {webhook_id} delivered successfully")
                        return
                    
                except Exception as e:
                    log.warning(f"Webhook delivery attempt {attempt + 1} failed: {e}")
                    event_record["delivery_attempts"] += 1
                    
                    if attempt < max_retries - 1:
                        await asyncio.sleep(retry_delay)
            
            # All retries exhausted
            event_record["delivery_status"] = "failed"
            webhook_data["failed_deliveries"] += 1
            log.error(f"Webhook {webhook_id} delivery failed after {max_retries} attempts")
            
        except Exception as e:
            log.error(f"Error in webhook delivery task: {e}")
    
    @staticmethod
    async def _send_http_request(
        url: str,
        event_record: Dict,
        secret: str
    ) -> bool:
        """Send HTTP POST request to webhook URL"""
        try:
            # Simulate HTTP request (in production use aiohttp or httpx)
            signature = WebhookManager._generate_signature(event_record, secret)
            
            # Simulate 95% success rate for demo
            import random
            success = random.random() < 0.95
            
            return success
        except Exception as e:
            log.error(f"Error sending HTTP request: {e}")
            return False
    
    @staticmethod
    def _generate_signature(payload: Dict, secret: str) -> str:
        """Generate HMAC signature for webhook"""
        payload_str = json.dumps(payload, sort_keys=True)
        signature = hmac.new(
            secret.encode(),
            payload_str.encode(),
            hashlib.sha256
        ).hexdigest()
        return signature
    
    @staticmethod
    async def verify_webhook_signature(
        db: Session,
        webhook_id: str,
        payload: Dict,
        signature: str
    ) -> dict:
        """Verify webhook signature"""
        try:
            if webhook_id not in WEBHOOKS_STORE:
                return {"success": False, "error": "Webhook not found"}
            
            webhook_data = WEBHOOKS_STORE[webhook_id]
            secret = webhook_data["secret"]
            
            expected_signature = WebhookManager._generate_signature(payload, secret)
            
            if hmac.compare_digest(signature, expected_signature):
                return {
                    "success": True,
                    "data": {
                        "verified": True,
                        "webhook_id": webhook_id,
                        "timestamp": datetime.utcnow().isoformat()
                    }
                }
            else:
                log.warning(f"Webhook signature verification failed for {webhook_id}")
                return {
                    "success": False,
                    "error": "Signature verification failed"
                }
        except Exception as e:
            log.error(f"Error verifying webhook signature: {e}")
            return {"success": False, "error": str(e)}
    
    @staticmethod
    async def retry_failed_webhooks(db: Session) -> dict:
        """Retry delivery of failed webhook events"""
        try:
            failed_events = [
                e for e in WEBHOOK_EVENTS_STORE
                if e["delivery_status"] == "failed"
            ]
            
            retried_count = 0
            for event in failed_events:
                webhook_id = event["webhook_id"]
                if webhook_id in WEBHOOKS_STORE:
                    webhook_data = WEBHOOKS_STORE[webhook_id]
                    
                    # Reset and retry
                    event["delivery_attempts"] = 0
                    event["delivery_status"] = "pending"
                    
                    asyncio.create_task(
                        WebhookManager._deliver_webhook(webhook_id, webhook_data, event)
                    )
                    retried_count += 1
            
            log.info(f"Retried {retried_count} failed webhook deliveries")
            
            return {
                "success": True,
                "data": {
                    "retried_count": retried_count,
                    "timestamp": datetime.utcnow().isoformat()
                }
            }
        except Exception as e:
            log.error(f"Error retrying failed webhooks: {e}")
            return {"success": False, "error": str(e)}
    
    @staticmethod
    async def list_webhooks(db: Session) -> dict:
        """List all registered webhooks"""
        try:
            webhooks = [
                {
                    "id": wh["id"],
                    "url": wh["url"],
                    "events": wh["events"],
                    "is_active": wh["is_active"],
                    "created_at": wh["created_at"],
                    "last_triggered_at": wh["last_triggered_at"],
                    "total_deliveries": wh["total_deliveries"],
                    "failed_deliveries": wh["failed_deliveries"]
                }
                for wh in WEBHOOKS_STORE.values()
            ]
            
            return {
                "success": True,
                "data": {
                    "count": len(webhooks),
                    "webhooks": webhooks
                }
            }
        except Exception as e:
            log.error(f"Error listing webhooks: {e}")
            return {"success": False, "error": str(e)}
    
    @staticmethod
    async def delete_webhook(db: Session, webhook_id: str) -> dict:
        """Delete a webhook"""
        try:
            if webhook_id not in WEBHOOKS_STORE:
                return {"success": False, "error": "Webhook not found"}
            
            webhook_data = WEBHOOKS_STORE.pop(webhook_id)
            
            log.info(f"Webhook deleted: {webhook_id}")
            
            return {
                "success": True,
                "data": {
                    "webhook_id": webhook_id,
                    "message": "Webhook deleted successfully"
                }
            }
        except Exception as e:
            log.error(f"Error deleting webhook: {e}")
            return {"success": False, "error": str(e)}


class WebhookEventQueue:
    """Manages webhook event processing queue"""
    
    @staticmethod
    async def queue_event(
        db: Session,
        event_type: str,
        payload: Dict[str, Any],
        priority: str = "normal"
    ) -> dict:
        """Add event to webhook queue"""
        try:
            event_record = {
                "event_type": event_type,
                "payload": payload,
                "priority": priority,
                "queued_at": datetime.utcnow().isoformat(),
                "processed": False,
                "processed_at": None
            }
            
            WEBHOOK_EVENTS_STORE.append(event_record)
            
            log.info(f"Event queued: {event_type} with priority {priority}")
            
            return {
                "success": True,
                "data": {
                    "event_type": event_type,
                    "priority": priority,
                    "queued_at": event_record["queued_at"]
                }
            }
        except Exception as e:
            log.error(f"Error queuing event: {e}")
            return {"success": False, "error": str(e)}
    
    @staticmethod
    async def process_queue(db: Session, batch_size: int = 10) -> dict:
        """Process webhook event queue in batches"""
        try:
            # Sort by priority (high first) and timestamp
            priority_order = {"high": 0, "normal": 1, "low": 2}
            
            unprocessed_events = [
                e for e in WEBHOOK_EVENTS_STORE
                if not e.get("processed", True)
            ]
            
            unprocessed_events.sort(
                key=lambda x: (
                    priority_order.get(x.get("priority", "normal"), 1),
                    x.get("queued_at", "")
                )
            )
            
            processed_count = 0
            for event in unprocessed_events[:batch_size]:
                # Trigger webhooks for this event
                result = await WebhookManager.trigger_webhook(
                    db,
                    event["event_type"],
                    event["payload"]
                )
                
                if result["success"]:
                    event["processed"] = True
                    event["processed_at"] = datetime.utcnow().isoformat()
                    processed_count += 1
            
            log.info(f"Processed {processed_count} webhook events from queue")
            
            return {
                "success": True,
                "data": {
                    "processed_count": processed_count,
                    "remaining_in_queue": len(unprocessed_events) - processed_count,
                    "timestamp": datetime.utcnow().isoformat()
                }
            }
        except Exception as e:
            log.error(f"Error processing webhook queue: {e}")
            return {"success": False, "error": str(e)}
    
    @staticmethod
    async def get_event_status(db: Session, event_type: str) -> dict:
        """Get delivery status of events"""
        try:
            events = [
                e for e in WEBHOOK_EVENTS_STORE
                if e.get("event_type") == event_type
            ]
            
            status_summary = {
                "total_events": len(events),
                "delivered": sum(1 for e in events if e.get("delivery_status") == "delivered"),
                "failed": sum(1 for e in events if e.get("delivery_status") == "failed"),
                "pending": sum(1 for e in events if e.get("delivery_status") == "pending")
            }
            
            status_summary["success_rate"] = round(
                status_summary["delivered"] / max(status_summary["total_events"], 1) * 100,
                2
            )
            
            return {
                "success": True,
                "data": {
                    "event_type": event_type,
                    "status": status_summary,
                    "timestamp": datetime.utcnow().isoformat()
                }
            }
        except Exception as e:
            log.error(f"Error getting event status: {e}")
            return {"success": False, "error": str(e)}
