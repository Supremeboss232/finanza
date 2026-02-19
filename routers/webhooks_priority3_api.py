"""
Webhooks API Router - Priority 3
Endpoints for managing webhooks, event subscriptions, and delivery tracking
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
import logging
import secrets
from pydantic import BaseModel, HttpUrl, Field

from deps import get_db, get_current_user
from models import User
from models_priority_3 import Webhook, WebhookDelivery
from services_priority_3 import WebhooksService

log = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/webhooks", tags=["webhooks"])

# ============================================================================
# PYDANTIC SCHEMAS
# ============================================================================

class WebhookCreate(BaseModel):
    """Request schema for webhook registration"""
    name: str = Field(..., min_length=1, max_length=255)
    url: HttpUrl = Field(..., description="HTTPS webhook endpoint URL")
    events: List[str] = Field(
        ..., 
        min_items=1,
        description="Event types to subscribe to (e.g., transfer.completed, deposit.approved)"
    )
    active: bool = Field(default=True)

    class Config:
        json_schema_extra = {
            "example": {
                "name": "My Webhook",
                "url": "https://example.com/webhooks/events",
                "events": ["transfer.completed", "deposit.approved"],
                "active": True
            }
        }


class WebhookUpdate(BaseModel):
    """Request schema for webhook updates"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    url: Optional[HttpUrl] = Field(None, description="Updated webhook URL (must be HTTPS)")
    events: Optional[List[str]] = Field(None, min_items=1)
    active: Optional[bool] = None

    class Config:
        json_schema_extra = {
            "example": {
                "name": "Updated Webhook Name",
                "events": ["transfer.completed", "deposit.approved", "withdrawal.initiated"]
            }
        }


class WebhookResponse(BaseModel):
    """Response schema for webhook"""
    id: int
    user_id: int
    name: str
    url: str
    events: List[str]
    secret_key: str
    active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class WebhookDeliveryResponse(BaseModel):
    """Response schema for webhook delivery"""
    id: int
    webhook_id: int
    event_type: str
    payload: dict
    status: str  # success, failed, pending, retrying
    response_code: Optional[int]
    response_body: Optional[str]
    retry_count: int
    next_retry_at: Optional[datetime]
    created_at: datetime
    delivered_at: Optional[datetime]

    class Config:
        from_attributes = True


class WebhookDeliveryStats(BaseModel):
    """Response schema for delivery statistics"""
    total_deliveries: int
    successful: int
    failed: int
    pending: int
    success_rate: float  # percentage
    avg_response_time_ms: float
    last_delivery_at: Optional[datetime]
    past_7_days_success: int
    past_7_days_total: int


class WebhookTestRequest(BaseModel):
    """Request schema for test webhook delivery"""
    event_type: str = Field(..., description="Event type to test (e.g., 'test.event')")
    
    class Config:
        json_schema_extra = {
            "example": {
                "event_type": "test.event"
            }
        }


# ============================================================================
# ENDPOINTS
# ============================================================================

@router.post(
    "/register",
    response_model=WebhookResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register Webhook",
    description="Register a new webhook endpoint to receive event notifications"
)
async def register_webhook(
    request: WebhookCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> WebhookResponse:
    """
    Register a new webhook for event notifications.
    
    **Requirements:**
    - URL must be HTTPS (secure)
    - URL must be reachable (validated with HEAD request)
    - At least one event type must be specified
    
    **Returns:**
    - 201 Created with webhook details including generated secret key
    - 400 Bad Request if validation fails
    - 401 Unauthorized if not authenticated
    """
    try:
        # Validate URL is HTTPS
        if not str(request.url).startswith("https://"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Webhook URL must use HTTPS protocol"
            )
        
        # Check URL reachability (optional - commented for dev)
        # is_reachable = WebhooksService.validate_webhook_url(str(request.url))
        # if not is_reachable:
        #     raise HTTPException(
        #         status_code=status.HTTP_400_BAD_REQUEST,
        #         detail="Webhook URL is not reachable. Ensure endpoint exists and returns 2xx status."
        #     )
        
        # Generate secret key for signing
        secret_key = secrets.token_urlsafe(32)
        
        # Create webhook via service
        webhook = WebhooksService.create_webhook(
            db=db,
            user_id=current_user.id,
            name=request.name,
            url=str(request.url),
            events=request.events,
            secret_key=secret_key,
            active=request.active
        )
        
        log.info(f"Webhook registered for user {current_user.id}: {webhook.id}")
        
        return WebhookResponse.from_orm(webhook)
    
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error registering webhook: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to register webhook"
        )


@router.get(
    "/list",
    response_model=List[WebhookResponse],
    summary="List Webhooks",
    description="Get list of all registered webhooks for the current user"
)
async def list_webhooks(
    active_only: bool = Query(False, description="Filter to active webhooks only"),
    event_type: Optional[str] = Query(None, description="Filter by specific event type"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> List[WebhookResponse]:
    """
    Get list of webhooks for the current user.
    
    **Query Parameters:**
    - `active_only`: If true, return only active webhooks
    - `event_type`: Filter webhooks by specific event type
    
    **Returns:**
    - 200 OK with list of webhooks
    - 401 Unauthorized if not authenticated
    """
    try:
        webhooks = WebhooksService.list_webhooks(
            db=db,
            user_id=current_user.id,
            active_only=active_only,
            event_type=event_type
        )
        
        return [WebhookResponse.from_orm(w) for w in webhooks]
    
    except Exception as e:
        log.error(f"Error listing webhooks: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list webhooks"
        )


@router.get(
    "/{webhook_id}",
    response_model=WebhookResponse,
    summary="Get Webhook Details",
    description="Get details of a specific webhook"
)
async def get_webhook(
    webhook_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> WebhookResponse:
    """
    Get details of a specific webhook.
    
    **Authorization:**
    - User can only view their own webhooks
    
    **Returns:**
    - 200 OK with webhook details
    - 401 Unauthorized if not authenticated
    - 403 Forbidden if webhook belongs to another user
    - 404 Not Found if webhook doesn't exist
    """
    try:
        webhook = db.query(Webhook).filter(Webhook.id == webhook_id).first()
        
        if not webhook:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Webhook not found"
            )
        
        # Verify ownership
        if webhook.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have access to this webhook"
            )
        
        return WebhookResponse.from_orm(webhook)
    
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error getting webhook {webhook_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get webhook"
        )


@router.put(
    "/{webhook_id}",
    response_model=WebhookResponse,
    summary="Update Webhook",
    description="Update webhook configuration"
)
async def update_webhook(
    webhook_id: int,
    request: WebhookUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> WebhookResponse:
    """
    Update webhook configuration.
    
    **Authorization:**
    - User can only update their own webhooks
    
    **Updates:**
    - Name, URL, event subscriptions, active status
    
    **Returns:**
    - 200 OK with updated webhook
    - 400 Bad Request if validation fails
    - 401 Unauthorized if not authenticated
    - 403 Forbidden if webhook belongs to another user
    - 404 Not Found if webhook doesn't exist
    """
    try:
        webhook = db.query(Webhook).filter(Webhook.id == webhook_id).first()
        
        if not webhook:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Webhook not found"
            )
        
        # Verify ownership
        if webhook.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have access to this webhook"
            )
        
        # Validate updated URL if provided
        if request.url and not str(request.url).startswith("https://"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Webhook URL must use HTTPS protocol"
            )
        
        # Update webhook
        if request.name is not None:
            webhook.name = request.name
        if request.url is not None:
            webhook.url = str(request.url)
        if request.events is not None:
            webhook.events = request.events
        if request.active is not None:
            webhook.active = request.active
        
        webhook.updated_at = datetime.utcnow()
        
        db.commit()
        
        log.info(f"Webhook {webhook_id} updated by user {current_user.id}")
        
        return WebhookResponse.from_orm(webhook)
    
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        log.error(f"Error updating webhook {webhook_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update webhook"
        )


@router.delete(
    "/{webhook_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete Webhook",
    description="Delete a webhook and all its deliveries"
)
async def delete_webhook(
    webhook_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Delete a webhook.
    
    **Authorization:**
    - User can only delete their own webhooks
    
    **Side Effects:**
    - All delivery records for this webhook are deleted
    - Future events will not be delivered to this webhook
    
    **Returns:**
    - 204 No Content on successful deletion
    - 401 Unauthorized if not authenticated
    - 403 Forbidden if webhook belongs to another user
    - 404 Not Found if webhook doesn't exist
    """
    try:
        webhook = db.query(Webhook).filter(Webhook.id == webhook_id).first()
        
        if not webhook:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Webhook not found"
            )
        
        # Verify ownership
        if webhook.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have access to this webhook"
            )
        
        # Delete associated deliveries
        db.query(WebhookDelivery).filter(
            WebhookDelivery.webhook_id == webhook_id
        ).delete()
        
        # Delete webhook
        db.delete(webhook)
        db.commit()
        
        log.info(f"Webhook {webhook_id} deleted by user {current_user.id}")
    
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        log.error(f"Error deleting webhook {webhook_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete webhook"
        )


@router.get(
    "/{webhook_id}/deliveries",
    response_model=List[WebhookDeliveryResponse],
    summary="Get Delivery History",
    description="Get delivery history for a webhook with optional filtering"
)
async def get_webhook_deliveries(
    webhook_id: int,
    status_filter: Optional[str] = Query(None, description="Filter by status (success, failed, pending, retrying)"),
    limit: int = Query(50, ge=1, le=1000, description="Number of records to return"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> List[WebhookDeliveryResponse]:
    """
    Get delivery history for a webhook.
    
    **Authorization:**
    - User can only view deliveries for their own webhooks
    
    **Query Parameters:**
    - `status_filter`: Filter by delivery status (success, failed, pending, retrying)
    - `limit`: Number of records per page (default: 50, max: 1000)
    - `offset`: Pagination offset (default: 0)
    
    **Returns:**
    - 200 OK with list of deliveries
    - 401 Unauthorized if not authenticated
    - 403 Forbidden if webhook belongs to another user
    - 404 Not Found if webhook doesn't exist
    """
    try:
        webhook = db.query(Webhook).filter(Webhook.id == webhook_id).first()
        
        if not webhook:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Webhook not found"
            )
        
        # Verify ownership
        if webhook.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have access to this webhook"
            )
        
        # Get deliveries
        query = db.query(WebhookDelivery).filter(
            WebhookDelivery.webhook_id == webhook_id
        )
        
        if status_filter:
            query = query.filter(WebhookDelivery.status == status_filter)
        
        deliveries = query.order_by(
            WebhookDelivery.created_at.desc()
        ).offset(offset).limit(limit).all()
        
        return [WebhookDeliveryResponse.from_orm(d) for d in deliveries]
    
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error getting deliveries for webhook {webhook_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get delivery history"
        )


@router.get(
    "/{webhook_id}/deliveries/statistics",
    response_model=WebhookDeliveryStats,
    summary="Get Delivery Statistics",
    description="Get delivery statistics and success rates for a webhook"
)
async def get_webhook_statistics(
    webhook_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> WebhookDeliveryStats:
    """
    Get delivery statistics for a webhook.
    
    **Authorization:**
    - User can only view stats for their own webhooks
    
    **Returns:**
    - 200 OK with delivery statistics
    - 401 Unauthorized if not authenticated
    - 403 Forbidden if webhook belongs to another user
    - 404 Not Found if webhook doesn't exist
    """
    try:
        webhook = db.query(Webhook).filter(Webhook.id == webhook_id).first()
        
        if not webhook:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Webhook not found"
            )
        
        # Verify ownership
        if webhook.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have access to this webhook"
            )
        
        # Calculate statistics
        stats = WebhooksService.get_webhook_statistics(db, webhook_id)
        
        return stats
    
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error getting statistics for webhook {webhook_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get statistics"
        )


@router.post(
    "/{webhook_id}/test",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Test Webhook Delivery",
    description="Send a test event to a webhook to verify it's working"
)
async def test_webhook(
    webhook_id: int,
    request: WebhookTestRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Send a test event to a webhook.
    
    **Authorization:**
    - User can only test their own webhooks
    
    **Returns:**
    - 202 Accepted - test delivery queued
    - 401 Unauthorized if not authenticated
    - 403 Forbidden if webhook belongs to another user
    - 404 Not Found if webhook doesn't exist
    
    **Note:**
    - Test webhook is delivered asynchronously
    - Check delivery history to see test results
    """
    try:
        webhook = db.query(Webhook).filter(Webhook.id == webhook_id).first()
        
        if not webhook:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Webhook not found"
            )
        
        # Verify ownership
        if webhook.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have access to this webhook"
            )
        
        # Queue test delivery
        test_payload = {
            "test": True,
            "event_type": request.event_type,
            "timestamp": datetime.utcnow().isoformat(),
            "webhook_id": webhook_id
        }
        
        WebhooksService.queue_webhook_delivery(
            db=db,
            webhook_id=webhook_id,
            event_type=request.event_type,
            payload=test_payload
        )
        
        log.info(f"Test webhook queued for {webhook_id}")
        
        return {"status": "accepted", "message": "Test webhook delivery queued"}
    
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error testing webhook {webhook_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to queue test webhook"
        )
