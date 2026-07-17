"""
Email Notification Service
Sends email notifications for all admin actions
"""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from typing import Optional
import logging
from config import settings

logger = logging.getLogger(__name__)


class EmailNotificationService:
    """Handle email notifications for admin actions"""
    
    # Email templates for different actions
    TEMPLATES = {
        'user_suspended': {
            'subject': 'User Account Suspended',
            'body': 'User {user_email} has been suspended by admin {admin_email}.\nReason: {reason}\nTime: {timestamp}'
        },
        'user_frozen': {
            'subject': 'User Account Frozen',
            'body': 'User {user_email} account has been frozen by admin {admin_email}.\nReason: {reason}\nTime: {timestamp}'
        },
        'balance_adjusted': {
            'subject': 'Balance Adjustment Made',
            'body': 'User {user_email} balance adjusted by {amount} by admin {admin_email}.\nReason: {reason}\nNew Balance: {new_balance}\nTime: {timestamp}'
        },
        'kyc_approved': {
            'subject': 'KYC Approval',
            'body': 'User {user_email} KYC has been approved by admin {admin_email}.\nTime: {timestamp}'
        },
        'kyc_rejected': {
            'subject': 'KYC Rejection',
            'body': 'User {user_email} KYC has been rejected by admin {admin_email}.\nReason: {reason}\nTime: {timestamp}'
        },
        'mfa_enabled': {
            'subject': 'MFA Enabled',
            'body': 'MFA (2FA) has been enabled for user {user_email} by admin {admin_email}.\nTime: {timestamp}'
        },
        'admin_created': {
            'subject': 'New Admin Account Created',
            'body': 'New admin account created.\nEmail: {admin_email}\nRole: {role}\nCreated by: {created_by}\nTime: {timestamp}'
        },
        'admin_revoked': {
            'subject': 'Admin Access Revoked',
            'body': 'Admin access has been revoked for {admin_email}.\nRevoked by: {revoked_by}\nReason: {reason}\nTime: {timestamp}'
        },
        'approval_request': {
            'subject': 'Approval Required: High-Value Balance Adjustment',
            'body': 'A balance adjustment requires your approval.\n\nUser: {user_email}\nAmount: {amount}\nRequested by: {requested_by}\nReason: {reason}\nApprove link: {approval_link}\n\nTime: {timestamp}'
        },
    }
    
    def __init__(self):
        self.smtp_server = settings.SMTP_SERVER or "smtp.gmail.com"
        self.smtp_port = settings.SMTP_PORT or 587
        self.sender_email = settings.SENDER_EMAIL or "noreply@financialservices.com"
        self.sender_password = settings.SENDER_PASSWORD or ""
        self.enabled = bool(self.sender_password)
    
    async def send_notification(
        self,
        recipient: str,
        action_type: str,
        **kwargs
    ) -> bool:
        """
        Send email notification for admin action
        
        Args:
            recipient: Email address to send to
            action_type: Type of action (key in TEMPLATES)
            **kwargs: Template variables
        
        Returns:
            True if sent successfully, False otherwise
        """
        if not self.enabled:
            logger.warning(f"Email notifications disabled - would send to {recipient}")
            return False
        
        if action_type not in self.TEMPLATES:
            logger.error(f"Unknown email template: {action_type}")
            return False
        
        try:
            template = self.TEMPLATES[action_type]
            kwargs['timestamp'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC")
            
            subject = template['subject']
            body = template['body'].format(**kwargs)
            
            # Create message
            message = MIMEMultipart("alternative")
            message["Subject"] = subject
            message["From"] = self.sender_email
            message["To"] = recipient
            
            # Add plain text
            part = MIMEText(body, "plain")
            message.attach(part)
            
            # Add HTML version (optional)
            html_body = self._create_html_email(subject, body)
            part = MIMEText(html_body, "html")
            message.attach(part)
            
            # Send email
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.sender_email, self.sender_password)
                server.sendmail(self.sender_email, recipient, message.as_string())
            
            logger.info(f"Email sent to {recipient} - Action: {action_type}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email to {recipient}: {e}")
            return False
    
    async def send_bulk_notification(
        self,
        recipients: list,
        action_type: str,
        **kwargs
    ) -> int:
        """Send same notification to multiple recipients"""
        count = 0
        for recipient in recipients:
            if await self.send_notification(recipient, action_type, **kwargs):
                count += 1
        return count
    
    def _create_html_email(self, subject: str, body: str) -> str:
        """Create HTML version of email"""
        html = f"""
        <html>
            <body style="font-family: Arial, sans-serif; background-color: #f5f5f5; padding: 20px;">
                <div style="background-color: white; padding: 20px; border-radius: 8px; max-width: 600px; margin: 0 auto;">
                    <h2 style="color: #333; border-bottom: 2px solid #007bff; padding-bottom: 10px;">
                        {subject}
                    </h2>
                    <p style="color: #666; line-height: 1.6; white-space: pre-wrap;">
                        {body}
                    </p>
                    <hr style="border: none; border-top: 1px solid #eee; margin: 20px 0;">
                    <p style="color: #999; font-size: 12px;">
                        This is an automated notification from Financial Services Admin System
                    </p>
                </div>
            </body>
        </html>
        """
        return html


# Singleton instance
_email_service: Optional[EmailNotificationService] = None


def get_email_notification_service() -> EmailNotificationService:
    """Get or create email notification service"""
    global _email_service
    if _email_service is None:
        _email_service = EmailNotificationService()
    return _email_service
