# routers/sns_notifications.py
# SNS notification router for push notifications, SMS, and subscriptions

from fastapi import APIRouter, Depends, HTTPException, status
from typing import Optional, List
from pydantic import BaseModel, EmailStr
import logging

from sns_service import sns_service
from notification_templates import (
    get_transaction_notification,
    get_kyc_notification,
    get_loan_notification,
    get_security_alert,
    get_payment_reminder,
    get_card_activation,
    get_investment_notification,
    get_deposit_notification,
    get_account_notification,
    get_promotional_notification
)
from deps import get_current_user, SessionDep
from models import User

log = logging.getLogger(__name__)

router = APIRouter(prefix="/api/sns", tags=["sns-notifications"])


# Request/Response models
class SendSMSRequest(BaseModel):
    phone_number: str  # E.164 format: +1234567890
    message: str
    sender_id: Optional[str] = None
    message_type: str = "Transactional"


class SubscribeTopicRequest(BaseModel):
    topic_arn: str
    protocol: str  # email, sms, http, https
    endpoint: str


class UnsubscribeRequest(BaseModel):
    subscription_arn: str


class NotificationResponse(BaseModel):
    success: bool
    message: Optional[str] = None
    error: Optional[str] = None


class SendPushNotificationRequest(BaseModel):
    endpoint_arn: str
    message: str
    title: Optional[str] = None
    data: Optional[dict] = None


class RegisterDeviceRequest(BaseModel):
    platform_app_arn: str
    device_token: str
    custom_data: Optional[str] = None


# ==================== Topic Management ====================

@router.post("/topics", response_model=NotificationResponse)
async def create_topic(
    topic_name: str,
    current_user: User = Depends(get_current_user)
):
    """Create SNS topic (admin only)"""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    result = await sns_service.create_topic(topic_name)
    
    if result['success']:
        return NotificationResponse(success=True, message=f"Topic created: {result['topic_arn']}")
    else:
        return NotificationResponse(success=False, error=result['message'])


@router.get("/topics")
async def list_topics(current_user: User = Depends(get_current_user)):
    """List all SNS topics (admin only)"""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    topics = await sns_service.list_topics()
    return {"topics": topics}


# ==================== SMS Notifications ====================

@router.post("/send-sms", response_model=NotificationResponse)
async def send_sms(
    request: SendSMSRequest,
    current_user: User = Depends(get_current_user)
):
    """Send SMS notification"""
    result = await sns_service.send_sms(
        phone_number=request.phone_number,
        message=request.message,
        sender_id=request.sender_id,
        message_type=request.message_type
    )
    
    if result['success']:
        return NotificationResponse(success=True, message=f"SMS sent to {result['phone']}")
    else:
        return NotificationResponse(success=False, error=result['message'])


# ==================== Subscription Management ====================

@router.post("/subscribe", response_model=NotificationResponse)
async def subscribe_to_topic(
    request: SubscribeTopicRequest,
    current_user: User = Depends(get_current_user)
):
    """Subscribe to SNS topic"""
    result = await sns_service.subscribe(
        topic_arn=request.topic_arn,
        protocol=request.protocol,
        endpoint=request.endpoint
    )
    
    if result['success']:
        return NotificationResponse(success=True, message=f"Subscribed: {result['protocol']} -> {result['endpoint']}")
    else:
        return NotificationResponse(success=False, error=result['message'])


@router.post("/unsubscribe", response_model=NotificationResponse)
async def unsubscribe_from_topic(
    request: UnsubscribeRequest,
    current_user: User = Depends(get_current_user)
):
    """Unsubscribe from SNS topic"""
    success = await sns_service.unsubscribe(request.subscription_arn)
    
    if success:
        return NotificationResponse(success=True, message="Unsubscribed")
    else:
        return NotificationResponse(success=False, error="Failed to unsubscribe")


@router.get("/subscriptions")
async def list_subscriptions(
    topic_arn: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """List subscriptions (admin only)"""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    subscriptions = await sns_service.list_subscriptions(topic_arn)
    return {"subscriptions": subscriptions}


# ==================== Mobile Push Notifications ====================

@router.post("/register-device", response_model=NotificationResponse)
async def register_device(
    request: RegisterDeviceRequest,
    current_user: User = Depends(get_current_user)
):
    """Register device for push notifications"""
    result = await sns_service.create_platform_endpoint(
        platform_app_arn=request.platform_app_arn,
        token=request.device_token,
        custom_data=request.custom_data
    )
    
    if result['success']:
        return NotificationResponse(success=True, message=f"Device registered: {result['endpoint_arn']}")
    else:
        return NotificationResponse(success=False, error=result['message'])


@router.post("/send-push", response_model=NotificationResponse)
async def send_push_notification(
    request: SendPushNotificationRequest,
    current_user: User = Depends(get_current_user)
):
    """Send push notification to device"""
    result = await sns_service.publish_to_mobile(
        target_arn=request.endpoint_arn,
        message=request.message,
        title=request.title,
        data=request.data
    )
    
    if result['success']:
        return NotificationResponse(success=True, message=f"Push sent: {result['message_id']}")
    else:
        return NotificationResponse(success=False, error=result['message'])


# ==================== Notification Triggers ====================

@router.post("/transaction-update", response_model=NotificationResponse)
async def send_transaction_notification(
    transaction_type: str,
    amount: str,
    status: str,
    current_user: User = Depends(get_current_user)
):
    """Send transaction update notification"""
    notifications = get_transaction_notification(transaction_type, amount, status)
    
    # Send as SMS (if user has phone)
    if hasattr(current_user, 'phone') and current_user.phone:
        await sns_service.send_sms(current_user.phone, notifications['sms'])
    
    return NotificationResponse(success=True, message="Transaction notification sent")


@router.post("/kyc-update", response_model=NotificationResponse)
async def send_kyc_notification(
    status: str,
    message: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """Send KYC status notification"""
    notifications = get_kyc_notification(status, message or "")
    
    # Send as SMS if user has phone
    if hasattr(current_user, 'phone') and current_user.phone:
        await sns_service.send_sms(current_user.phone, notifications['sms'])
    
    return NotificationResponse(success=True, message="KYC notification sent")


@router.post("/security-alert", response_model=NotificationResponse)
async def send_security_alert(
    alert_type: str,
    description: str,
    current_user: User = Depends(get_current_user)
):
    """Send security alert"""
    notifications = get_security_alert(alert_type, description)
    
    # Send as SMS (urgent)
    if hasattr(current_user, 'phone') and current_user.phone:
        await sns_service.send_sms(
            current_user.phone,
            notifications['sms'],
            message_type='Transactional'
        )
    
    return NotificationResponse(success=True, message="Security alert sent")


@router.post("/payment-reminder", response_model=NotificationResponse)
async def send_payment_reminder(
    payment_id: str,
    amount: str,
    due_date: str,
    current_user: User = Depends(get_current_user)
):
    """Send payment reminder"""
    notifications = get_payment_reminder(payment_id, amount, due_date)
    
    # Send as SMS
    if hasattr(current_user, 'phone') and current_user.phone:
        await sns_service.send_sms(current_user.phone, notifications['sms'])
    
    return NotificationResponse(success=True, message="Reminder sent")


@router.post("/loan-update", response_model=NotificationResponse)
async def send_loan_notification(
    loan_id: str,
    status: str,
    amount: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """Send loan application update"""
    notifications = get_loan_notification(loan_id, status, amount or "")
    
    # Send as SMS
    if hasattr(current_user, 'phone') and current_user.phone:
        await sns_service.send_sms(current_user.phone, notifications['sms'])
    
    return NotificationResponse(success=True, message="Loan notification sent")


@router.post("/card-activation", response_model=NotificationResponse)
async def send_card_activation(
    card_type: str,
    last_four: str,
    current_user: User = Depends(get_current_user)
):
    """Send card activation notification"""
    notifications = get_card_activation(card_type, last_four)
    
    # Send as SMS
    if hasattr(current_user, 'phone') and current_user.phone:
        await sns_service.send_sms(current_user.phone, notifications['sms'])
    
    return NotificationResponse(success=True, message="Card activation sent")


# ==================== Admin Bulk Notifications ====================

@router.post("/broadcast", response_model=NotificationResponse)
async def broadcast_notification(
    message: str,
    topic_arn: str,
    subject: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """Send broadcast notification to topic (admin only)"""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    result = await sns_service.publish_message(
        topic_arn=topic_arn,
        message=message,
        subject=subject
    )
    
    if result['success']:
        return NotificationResponse(success=True, message=f"Broadcast sent: {result['message_id']}")
    else:
        return NotificationResponse(success=False, error=result['message'])


@router.post("/promote", response_model=NotificationResponse)
async def send_promotional(
    title: str,
    message: str,
    offer: Optional[str] = None,
    topic_arn: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """Send promotional notification (admin only)"""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    notifications = get_promotional_notification(title, message, offer or "")
    
    if topic_arn:
        result = await sns_service.publish_message(
            topic_arn=topic_arn,
            message=notifications['email'],
            subject=title
        )
        
        if result['success']:
            return NotificationResponse(success=True, message=f"Promotion sent: {result['message_id']}")
        else:
            return NotificationResponse(success=False, error=result['message'])
    
    return NotificationResponse(success=False, error="Topic ARN required")
