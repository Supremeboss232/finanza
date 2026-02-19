# email_utils.py
# Helper functions for sending emails (verification, password reset, notifications).

from fastapi_mail import FastMail, MessageSchema, ConnectionConfig
from config import settings # Assuming config.py defines email settings

conf = ConnectionConfig(
    MAIL_USERNAME=settings.MAIL_USERNAME,
    MAIL_PASSWORD=settings.MAIL_PASSWORD,
    MAIL_FROM=settings.MAIL_FROM,
    MAIL_PORT=settings.MAIL_PORT,
    MAIL_SERVER=settings.MAIL_SERVER,
    MAIL_TLS=settings.MAIL_TLS,
    MAIL_SSL=settings.MAIL_SSL,
    USE_CREDENTIALS=settings.USE_CREDENTIALS,
    VALIDATE_CERTS=settings.VALIDATE_CERTS
)

async def send_email(subject: str, recipients: list, body: str, subtype: str = "html"):
    message = MessageSchema(
        subject=subject,
        recipients=recipients,
        body=body,
        subtype=subtype
    )
    fm = FastMail(conf)
    await fm.send_message(message)
