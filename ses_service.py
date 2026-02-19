# ses_service.py
# AWS SES Service for transactional emails

import boto3
import logging
from typing import List, Optional, Dict, Any
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from botocore.exceptions import ClientError
from config import settings

log = logging.getLogger(__name__)

class SESEmailService:
    """AWS Simple Email Service for sending transactional emails"""
    
    def __init__(self):
        """Initialize SES client"""
        self.ses_client = boto3.client(
            'ses',
            region_name=settings.AWS_REGION,
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY
        )
        self.sender_email = settings.SES_SENDER_EMAIL
        self.sender_name = settings.SES_SENDER_NAME
    
    async def send_email(
        self,
        to_email: str,
        subject: str,
        html_body: str,
        text_body: Optional[str] = None,
        cc: Optional[List[str]] = None,
        bcc: Optional[List[str]] = None,
        reply_to: Optional[str] = None,
        tags: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Send a transactional email via AWS SES
        
        Args:
            to_email: Recipient email address
            subject: Email subject
            html_body: HTML email body
            text_body: Plain text fallback
            cc: CC recipients
            bcc: BCC recipients
            reply_to: Reply-to email address
            tags: Email tags for tracking
            
        Returns:
            Response dict with MessageId
        """
        try:
            # Build email params
            email_params = {
                'Source': f'{self.sender_name} <{self.sender_email}>',
                'Destination': {
                    'ToAddresses': [to_email]
                },
                'Message': {
                    'Subject': {
                        'Data': subject,
                        'Charset': 'UTF-8'
                    },
                    'Body': {
                        'Html': {
                            'Data': html_body,
                            'Charset': 'UTF-8'
                        }
                    }
                }
            }
            
            # Add plain text if provided
            if text_body:
                email_params['Message']['Body']['Text'] = {
                    'Data': text_body,
                    'Charset': 'UTF-8'
                }
            
            # Add CC recipients
            if cc:
                email_params['Destination']['CcAddresses'] = cc
            
            # Add BCC recipients
            if bcc:
                email_params['Destination']['BccAddresses'] = bcc
            
            # Add reply-to address
            if reply_to:
                email_params['ReplyToAddresses'] = [reply_to]
            
            # Add tags if provided (for tracking and filtering)
            if tags:
                email_params['Tags'] = [
                    {'Name': key, 'Value': value}
                    for key, value in tags.items()
                ]
            
            # Send email
            response = self.ses_client.send_email(**email_params)
            
            log.info(f"Email sent successfully to {to_email}. MessageId: {response['MessageId']}")
            return {
                'success': True,
                'message_id': response['MessageId'],
                'to_email': to_email
            }
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = e.response['Error']['Message']
            log.error(f"SES error sending email to {to_email}: {error_code} - {error_message}")
            return {
                'success': False,
                'error': error_code,
                'message': error_message
            }
        except Exception as e:
            log.error(f"Unexpected error sending email to {to_email}: {str(e)}")
            return {
                'success': False,
                'error': 'UNKNOWN_ERROR',
                'message': str(e)
            }
    
    async def send_bulk_email(
        self,
        to_emails: List[str],
        subject: str,
        html_body: str,
        text_body: Optional[str] = None,
        tags: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Send the same email to multiple recipients
        
        Args:
            to_emails: List of recipient email addresses
            subject: Email subject
            html_body: HTML email body
            text_body: Plain text fallback
            tags: Email tags for tracking
            
        Returns:
            Response dict with success/failure counts
        """
        results = {
            'total': len(to_emails),
            'successful': 0,
            'failed': 0,
            'failures': []
        }
        
        for email in to_emails:
            response = await self.send_email(
                to_email=email,
                subject=subject,
                html_body=html_body,
                text_body=text_body,
                tags=tags
            )
            
            if response['success']:
                results['successful'] += 1
            else:
                results['failed'] += 1
                results['failures'].append({
                    'email': email,
                    'error': response.get('error'),
                    'message': response.get('message')
                })
        
        log.info(f"Bulk email sent: {results['successful']}/{results['total']} successful")
        return results
    
    async def send_with_attachment(
        self,
        to_email: str,
        subject: str,
        html_body: str,
        attachment_path: str,
        attachment_name: Optional[str] = None,
        text_body: Optional[str] = None,
        tags: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Send email with attachment via SES
        
        Args:
            to_email: Recipient email address
            subject: Email subject
            html_body: HTML email body
            attachment_path: Path to file to attach
            attachment_name: Display name for attachment
            text_body: Plain text fallback
            tags: Email tags for tracking
            
        Returns:
            Response dict with MessageId
        """
        try:
            # Read attachment
            with open(attachment_path, 'rb') as attachment:
                attachment_data = attachment.read()
            
            if not attachment_name:
                attachment_name = attachment_path.split('/')[-1]
            
            # Create message
            msg = MIMEMultipart('mixed')
            msg['Subject'] = subject
            msg['From'] = f'{self.sender_name} <{self.sender_email}>'
            msg['To'] = to_email
            
            # Add body
            msg_alternative = MIMEMultipart('alternative')
            msg.attach(msg_alternative)
            
            if text_body:
                part_text = MIMEText(text_body, 'plain')
                msg_alternative.attach(part_text)
            
            part_html = MIMEText(html_body, 'html')
            msg_alternative.attach(part_html)
            
            # Add attachment
            attachment_part = MIMEText(attachment_data, 'base64')
            attachment_part.add_header('Content-Disposition', 'attachment', filename=attachment_name)
            msg.attach(attachment_part)
            
            # Send raw email
            response = self.ses_client.send_raw_email(
                Source=f'{self.sender_name} <{self.sender_email}>',
                Destinations=[to_email],
                RawMessage={'Data': msg.as_string()}
            )
            
            log.info(f"Email with attachment sent to {to_email}. MessageId: {response['MessageId']}")
            return {
                'success': True,
                'message_id': response['MessageId'],
                'to_email': to_email
            }
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = e.response['Error']['Message']
            log.error(f"SES error sending email with attachment to {to_email}: {error_code} - {error_message}")
            return {
                'success': False,
                'error': error_code,
                'message': error_message
            }
        except Exception as e:
            log.error(f"Error sending email with attachment to {to_email}: {str(e)}")
            return {
                'success': False,
                'error': 'UNKNOWN_ERROR',
                'message': str(e)
            }
    
    def verify_email_identity(self, email: str) -> bool:
        """
        Verify an email identity with SES (required in sandbox mode)
        
        Args:
            email: Email address to verify
            
        Returns:
            True if successful
        """
        try:
            self.ses_client.verify_email_identity(EmailAddress=email)
            log.info(f"Email verification initiated for {email}")
            return True
        except ClientError as e:
            log.error(f"Error verifying email {email}: {e}")
            return False
    
    def get_send_quota(self) -> Dict[str, Any]:
        """Get SES send quota and usage stats"""
        try:
            response = self.ses_client.get_account_send_quota()
            return {
                'max_24_hour_send': response['Max24HourSend'],
                'max_send_rate': response['MaxSendRate'],
                'sent_24_hour': response['Sent24Hour']
            }
        except ClientError as e:
            log.error(f"Error getting send quota: {e}")
            return {}


# Singleton instance
ses_service = SESEmailService()
