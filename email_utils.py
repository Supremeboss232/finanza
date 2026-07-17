# email_utils.py
# Helper functions for sending emails (verification, password reset, notifications).
# Uses Gmail SMTP for real email delivery

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from config import settings
import logging

log = logging.getLogger(__name__)

async def send_email(subject: str, recipients: list, body: str, subtype: str = "html"):
    """
    Send email via Gmail SMTP
    
    Args:
        subject: Email subject line
        recipients: List of recipient email addresses
        body: Email body content
        subtype: 'html' for HTML emails, 'plain' for text emails
    
    Returns:
        dict with status information
    """
    if not settings.MAIL_USERNAME or not settings.MAIL_PASSWORD:
        log.error("❌ Gmail credentials not configured in .env")
        log.error(f"MAIL_USERNAME: {settings.MAIL_USERNAME}")
        log.error(f"MAIL_PASSWORD: {'*' * len(settings.MAIL_PASSWORD) if settings.MAIL_PASSWORD else 'NOT SET'}")
        raise ValueError("Gmail SMTP credentials not configured in .env")
    
    try:
        log.info(f"📧 Sending email via Gmail SMTP to {recipients}")
        log.info(f"Subject: {subject}")
        log.info(f"From: {settings.MAIL_FROM}")
        
        # Create message
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"{settings.MAIL_FROM_NAME} <{settings.MAIL_FROM}>"
        msg["To"] = ", ".join(recipients)
        
        # Attach body (HTML preferred, fallback to plain text)
        if subtype == "html":
            msg.attach(MIMEText(body, "html"))
        else:
            msg.attach(MIMEText(body, "plain"))
        
        # Connect to Gmail SMTP server and send
        log.info(f"🔗 Connecting to {settings.MAIL_SERVER}:{settings.MAIL_PORT}")
        
        with smtplib.SMTP(settings.MAIL_SERVER, settings.MAIL_PORT, timeout=10) as server:
            # Start TLS encryption
            if settings.MAIL_STARTTLS:
                log.info("🔐 Starting TLS encryption")
                server.starttls()
            
            # Login with credentials
            log.info(f"🔑 Authenticating with {settings.MAIL_USERNAME}")
            server.login(settings.MAIL_USERNAME, settings.MAIL_PASSWORD)
            
            # Send email
            log.info(f"📤 Sending email to {recipients}")
            server.sendmail(settings.MAIL_FROM, recipients, msg.as_string())
        
        log.info(f"✅ Email sent successfully to {recipients}")
        return {"success": True, "message": f"Email sent to {recipients}"}
        
    except smtplib.SMTPAuthenticationError as e:
        log.error(f"❌ Gmail authentication failed: {e}", exc_info=True)
        log.error("   Check: 1) Gmail address is correct 2) App Password is correct 3) 2FA enabled")
        raise ValueError("Gmail authentication failed. Check credentials and ensure 2FA is enabled.")
    
    except smtplib.SMTPException as e:
        log.error(f"❌ SMTP error: {e}", exc_info=True)
        raise
    
    except Exception as e:
        log.error(f"❌ Unexpected error sending email: {e}", exc_info=True)
        raise
