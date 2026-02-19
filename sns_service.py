# sns_service.py
# AWS SNS Service for push notifications, SMS, and subscriptions

import boto3
import logging
import json
from typing import List, Optional, Dict, Any
from botocore.exceptions import ClientError
from config import settings

log = logging.getLogger(__name__)


class SNSNotificationService:
    """AWS Simple Notification Service for notifications and subscriptions"""
    
    def __init__(self):
        """Initialize SNS client"""
        self.sns_client = boto3.client(
            'sns',
            region_name=settings.AWS_REGION,
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY
        )
    
    # ==================== Topic Management ====================
    
    async def create_topic(self, topic_name: str, attributes: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """
        Create SNS topic
        
        Args:
            topic_name: Name of the topic
            attributes: Optional attributes (display name, etc.)
            
        Returns:
            Response with TopicArn
        """
        try:
            params = {'Name': topic_name}
            if attributes:
                params['Attributes'] = attributes
            
            response = self.sns_client.create_topic(**params)
            topic_arn = response['TopicArn']
            
            log.info(f"SNS topic created: {topic_arn}")
            return {
                'success': True,
                'topic_arn': topic_arn,
                'topic_name': topic_name
            }
        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = e.response['Error']['Message']
            log.error(f"Error creating SNS topic: {error_code} - {error_message}")
            return {
                'success': False,
                'error': error_code,
                'message': error_message
            }
    
    async def delete_topic(self, topic_arn: str) -> bool:
        """Delete SNS topic"""
        try:
            self.sns_client.delete_topic(TopicArn=topic_arn)
            log.info(f"SNS topic deleted: {topic_arn}")
            return True
        except ClientError as e:
            log.error(f"Error deleting SNS topic: {e}")
            return False
    
    async def list_topics(self) -> List[Dict[str, str]]:
        """List all SNS topics"""
        try:
            response = self.sns_client.list_topics()
            topics = []
            for topic in response.get('Topics', []):
                topics.append({
                    'arn': topic['TopicArn'],
                    'name': topic['TopicArn'].split(':')[-1]
                })
            return topics
        except ClientError as e:
            log.error(f"Error listing SNS topics: {e}")
            return []
    
    # ==================== Publishing ====================
    
    async def publish_message(
        self,
        topic_arn: str,
        message: str,
        subject: Optional[str] = None,
        message_attributes: Optional[Dict[str, Any]] = None,
        message_structure: str = 'json'
    ) -> Dict[str, Any]:
        """
        Publish message to SNS topic
        
        Args:
            topic_arn: ARN of the topic
            message: Message content
            subject: Optional subject (for email subscriptions)
            message_attributes: Optional message attributes for filtering
            message_structure: 'json' for structured messages
            
        Returns:
            Response with MessageId
        """
        try:
            params = {
                'TopicArn': topic_arn,
                'Message': message
            }
            
            if subject:
                params['Subject'] = subject
            
            if message_attributes:
                params['MessageAttributes'] = message_attributes
            
            if message_structure:
                params['MessageStructure'] = message_structure
            
            response = self.sns_client.publish(**params)
            
            log.info(f"Message published to {topic_arn}. MessageId: {response['MessageId']}")
            return {
                'success': True,
                'message_id': response['MessageId'],
                'topic_arn': topic_arn
            }
        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = e.response['Error']['Message']
            log.error(f"Error publishing SNS message: {error_code} - {error_message}")
            return {
                'success': False,
                'error': error_code,
                'message': error_message
            }
    
    async def publish_to_multiple_topics(
        self,
        topic_arns: List[str],
        message: str,
        subject: Optional[str] = None
    ) -> Dict[str, Any]:
        """Publish same message to multiple topics"""
        results = {
            'total': len(topic_arns),
            'successful': 0,
            'failed': 0,
            'failures': []
        }
        
        for topic_arn in topic_arns:
            response = await self.publish_message(topic_arn, message, subject)
            if response['success']:
                results['successful'] += 1
            else:
                results['failed'] += 1
                results['failures'].append({
                    'topic_arn': topic_arn,
                    'error': response.get('error')
                })
        
        return results
    
    # ==================== Subscriptions ====================
    
    async def subscribe(
        self,
        topic_arn: str,
        protocol: str,
        endpoint: str,
        attributes: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Subscribe to SNS topic
        
        Args:
            topic_arn: Topic ARN
            protocol: email, sms, http, https, sqs, lambda, application
            endpoint: Email, phone number, URL, or ARN
            attributes: Optional subscription attributes
            
        Returns:
            Subscription ARN
        """
        try:
            params = {
                'TopicArn': topic_arn,
                'Protocol': protocol,
                'Endpoint': endpoint,
                'ReturnSubscriptionArn': True
            }
            
            if attributes:
                params['Attributes'] = attributes
            
            response = self.sns_client.subscribe(**params)
            subscription_arn = response['SubscriptionArn']
            
            log.info(f"Subscription created: {protocol} -> {endpoint}")
            return {
                'success': True,
                'subscription_arn': subscription_arn,
                'protocol': protocol,
                'endpoint': endpoint
            }
        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = e.response['Error']['Message']
            log.error(f"Error subscribing to SNS topic: {error_code} - {error_message}")
            return {
                'success': False,
                'error': error_code,
                'message': error_message
            }
    
    async def unsubscribe(self, subscription_arn: str) -> bool:
        """Unsubscribe from SNS topic"""
        try:
            self.sns_client.unsubscribe(SubscriptionArn=subscription_arn)
            log.info(f"Unsubscribed: {subscription_arn}")
            return True
        except ClientError as e:
            log.error(f"Error unsubscribing: {e}")
            return False
    
    async def list_subscriptions(self, topic_arn: Optional[str] = None) -> List[Dict[str, str]]:
        """List subscriptions for a topic"""
        try:
            if topic_arn:
                response = self.sns_client.list_subscriptions_by_topic(TopicArn=topic_arn)
            else:
                response = self.sns_client.list_subscriptions()
            
            subscriptions = []
            for sub in response.get('Subscriptions', []):
                subscriptions.append({
                    'arn': sub['SubscriptionArn'],
                    'topic_arn': sub['TopicArn'],
                    'protocol': sub['Protocol'],
                    'endpoint': sub['Endpoint'],
                    'owner': sub['Owner']
                })
            return subscriptions
        except ClientError as e:
            log.error(f"Error listing SNS subscriptions: {e}")
            return []
    
    # ==================== SMS Notifications ====================
    
    async def send_sms(
        self,
        phone_number: str,
        message: str,
        sender_id: Optional[str] = None,
        message_type: str = 'Transactional'
    ) -> Dict[str, Any]:
        """
        Send SMS via SNS
        
        Args:
            phone_number: Recipient phone (E.164 format: +1234567890)
            message: SMS content (max 160 chars for SMS, 1000 for MMS)
            sender_id: Optional sender ID
            message_type: Transactional or Promotional
            
        Returns:
            Response with MessageId
        """
        try:
            # Validate phone format
            if not phone_number.startswith('+'):
                log.error(f"Invalid phone format: {phone_number}. Use E.164 format: +country_code...")
                return {
                    'success': False,
                    'error': 'INVALID_PHONE_FORMAT',
                    'message': 'Phone must be in E.164 format (+1234567890)'
                }
            
            params = {
                'PhoneNumber': phone_number,
                'Message': message,
                'MessageStructure': 'String'
            }
            
            # Set message attributes
            message_attributes = {
                'AWS.SNS.SMS.MessageType': {
                    'DataType': 'String',
                    'StringValue': message_type
                }
            }
            
            if sender_id:
                message_attributes['AWS.SNS.SMS.SenderID'] = {
                    'DataType': 'String',
                    'StringValue': sender_id
                }
            
            params['MessageAttributes'] = message_attributes
            
            response = self.sns_client.publish(**params)
            
            log.info(f"SMS sent to {phone_number}. MessageId: {response['MessageId']}")
            return {
                'success': True,
                'message_id': response['MessageId'],
                'phone': phone_number
            }
        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = e.response['Error']['Message']
            log.error(f"Error sending SMS: {error_code} - {error_message}")
            return {
                'success': False,
                'error': error_code,
                'message': error_message
            }
    
    # ==================== Topic Attributes ====================
    
    async def set_topic_attributes(
        self,
        topic_arn: str,
        attribute_name: str,
        attribute_value: str
    ) -> bool:
        """Set topic attributes (DisplayName, Policy, etc.)"""
        try:
            self.sns_client.set_topic_attributes(
                TopicArn=topic_arn,
                AttributeName=attribute_name,
                AttributeValue=attribute_value
            )
            log.info(f"Topic attribute set: {attribute_name}")
            return True
        except ClientError as e:
            log.error(f"Error setting topic attribute: {e}")
            return False
    
    async def get_topic_attributes(self, topic_arn: str) -> Dict[str, Any]:
        """Get all topic attributes"""
        try:
            response = self.sns_client.get_topic_attributes(TopicArn=topic_arn)
            return response.get('Attributes', {})
        except ClientError as e:
            log.error(f"Error getting topic attributes: {e}")
            return {}
    
    # ==================== Mobile Push Notifications ====================
    
    async def create_platform_application(
        self,
        name: str,
        platform: str,  # GCM, APNS, APNS_SANDBOX, ADM, Baidu
        attributes: Dict[str, str]
    ) -> Dict[str, Any]:
        """
        Create platform app for mobile push notifications
        
        Args:
            name: Application name
            platform: Mobile platform (GCM for Android, APNS for iOS)
            attributes: Platform credentials
            
        Returns:
            Platform application ARN
        """
        try:
            response = self.sns_client.create_platform_application(
                Name=name,
                Platform=platform,
                Attributes=attributes
            )
            
            app_arn = response['PlatformApplicationArn']
            log.info(f"Platform app created: {app_arn}")
            return {
                'success': True,
                'app_arn': app_arn
            }
        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = e.response['Error']['Message']
            log.error(f"Error creating platform app: {error_code} - {error_message}")
            return {
                'success': False,
                'error': error_code,
                'message': error_message
            }
    
    async def create_platform_endpoint(
        self,
        platform_app_arn: str,
        token: str,
        custom_data: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Register device for push notifications
        
        Args:
            platform_app_arn: Platform app ARN
            token: Device token (FCM token for Android, APNS for iOS)
            custom_data: Custom data for the endpoint
            
        Returns:
            Endpoint ARN
        """
        try:
            params = {
                'PlatformApplicationArn': platform_app_arn,
                'Token': token
            }
            
            if custom_data:
                params['CustomUserData'] = custom_data
            
            response = self.sns_client.create_platform_endpoint(**params)
            
            endpoint_arn = response['EndpointArn']
            log.info(f"Device endpoint registered: {endpoint_arn}")
            return {
                'success': True,
                'endpoint_arn': endpoint_arn
            }
        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = e.response['Error']['Message']
            log.error(f"Error creating endpoint: {error_code} - {error_message}")
            return {
                'success': False,
                'error': error_code,
                'message': error_message
            }
    
    async def publish_to_mobile(
        self,
        target_arn: str,
        message: str,
        title: Optional[str] = None,
        data: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Send push notification to mobile device
        
        Args:
            target_arn: Endpoint ARN
            message: Notification message
            title: Notification title
            data: Custom data payload
            
        Returns:
            Response with MessageId
        """
        try:
            # Build message structure for different platforms
            message_obj = {
                'default': message,
                'GCM': json.dumps({
                    'notification': {
                        'title': title or 'Finanza Bank',
                        'body': message,
                        'sound': 'default'
                    },
                    'data': data or {}
                }),
                'APNS': json.dumps({
                    'aps': {
                        'alert': {
                            'title': title or 'Finanza Bank',
                            'body': message
                        },
                        'sound': 'default'
                    },
                    'data': data or {}
                })
            }
            
            response = self.sns_client.publish(
                TargetArn=target_arn,
                Message=json.dumps(message_obj),
                MessageStructure='json'
            )
            
            log.info(f"Push notification sent. MessageId: {response['MessageId']}")
            return {
                'success': True,
                'message_id': response['MessageId']
            }
        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = e.response['Error']['Message']
            log.error(f"Error sending push notification: {error_code} - {error_message}")
            return {
                'success': False,
                'error': error_code,
                'message': error_message
            }
    
    # ==================== Monitoring & Attributes ====================
    
    def get_endpoint_attributes(self, endpoint_arn: str) -> Dict[str, Any]:
        """Get endpoint attributes"""
        try:
            response = self.sns_client.get_endpoint_attributes(EndpointArn=endpoint_arn)
            return response.get('Attributes', {})
        except ClientError as e:
            log.error(f"Error getting endpoint attributes: {e}")
            return {}
    
    def delete_endpoint(self, endpoint_arn: str) -> bool:
        """Disable or remove endpoint"""
        try:
            self.sns_client.delete_endpoint(EndpointArn=endpoint_arn)
            log.info(f"Endpoint deleted: {endpoint_arn}")
            return True
        except ClientError as e:
            log.error(f"Error deleting endpoint: {e}")
            return False


# Singleton instance
sns_service = SNSNotificationService()
