"""
Finanza Real-Time KYC Event Dispatcher

Coordinates KYC validation events from providers and routes them to appropriate processors.

Event sources:
- EventBridge rules from KYC providers
- SNS subscriptions from webhook receivers
- Direct Lambda invocations

Responsibilities:
1. Parse and validate KYC events
2. Update user KYC status in RDS
3. Trigger fraud detection for KYC approvals
4. Send notifications to users
5. Invoke post-processing Lambda functions
6. Log all events for audit trail
"""

import json
import logging
import asyncio
import os
from typing import Dict, Any, Optional, Tuple
from datetime import datetime
from decimal import Decimal
import boto3
import psycopg2
from psycopg2 import sql
import aws_lambda_powertools
from aws_lambda_powertools import Logger, Tracer, Metrics
from aws_lambda_powertools.utilities.typing import LambdaContext
from aws_lambda_powertools.utilities.data_classes.event_source_data_class import EventBridgeDetailType

# ==================== AWS Clients ====================
lambda_client = boto3.client('lambda')
sns_client = boto3.client('sns')
ses_client = boto3.client('ses')
secretsmanager_client = boto3.client('secretsmanager')

# ==================== Logging & Monitoring ====================
logger = Logger()
tracer = Tracer()
metrics = Metrics()

ENVIRONMENT = os.getenv('ENVIRONMENT', 'dev')
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
logger.setLevel(LOG_LEVEL)

# ==================== Configuration ====================
RDS_ENDPOINT = os.getenv('RDS_ENDPOINT')
RDS_PORT = int(os.getenv('RDS_PORT', 5432))
RDS_DATABASE = os.getenv('RDS_DATABASE', 'Finanza')
RDS_USERNAME = os.getenv('RDS_USERNAME', 'postgres')
LAMBDA_FRAUD_DETECTOR = os.getenv('LAMBDA_FRAUD_DETECTOR')
LAMBDA_SETTLEMENT_PROCESSOR = os.getenv('LAMBDA_SETTLEMENT_PROCESSOR')
SNS_KYC_TOPIC = os.getenv('SNS_KYC_TOPIC')
SES_SENDER_EMAIL = os.getenv('SES_SENDER_EMAIL', 'noreply@finanzabank.com')
SES_REGION = os.getenv('SES_REGION', 'eu-north-1')

# Metrics
METRIC_KYC_APPROVED = 'KycApproved'
METRIC_KYC_REJECTED = 'KycRejected'
METRIC_PROCESSING_TIME = 'ProcessingTime'
METRIC_DATABASE_ERRORS = 'DatabaseErrors'


class KycEventDispatcher:
    """
    Main dispatcher class for handling KYC events.
    """
    
    def __init__(self):
        self.db_connection = None
        self.rds_password = None
        self.event_start_time = datetime.utcnow()
    
    async def initialize(self):
        """Initialize database connection and fetch secrets"""
        try:
            # Fetch RDS password from Secrets Manager
            secret_response = secretsmanager_client.get_secret_value(
                SecretId=f'finanza/rds/password'
            )
            self.rds_password = json.loads(secret_response['SecretString']).get('password')
            
            if not self.rds_password:
                logger.error("RDS password not found in Secrets Manager")
                raise ValueError("RDS password not configured")
            
            logger.info("Secrets loaded successfully")
        except Exception as e:
            logger.exception(f"Failed to initialize secrets: {e}")
            raise
    
    def get_db_connection(self):
        """Get or create database connection"""
        try:
            if not self.db_connection or self.db_connection.closed:
                self.db_connection = psycopg2.connect(
                    host=RDS_ENDPOINT,
                    port=RDS_PORT,
                    database=RDS_DATABASE,
                    user=RDS_USERNAME,
                    password=self.rds_password,
                    connect_timeout=10
                )
                logger.info(f"Connected to RDS: {RDS_ENDPOINT}")
            return self.db_connection
        except Exception as e:
            logger.exception(f"Database connection failed: {e}")
            metrics.add_metric(name=METRIC_DATABASE_ERRORS, unit='Count', value=1)
            raise
    
    def close_db_connection(self):
        """Close database connection"""
        if self.db_connection and not self.db_connection.closed:
            self.db_connection.close()
            logger.info("Database connection closed")
    
    async def process_kyc_event(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main event processor.
        
        Event Structure (from EventBridge or SNS):
        {
            "source": "kyc.provider",
            "detail": {
                "user_id": "uuid",
                "status": "approved|rejected",
                "provider": "jumio|onfido|idology",
                "externalId": "provider-ref",
                "metadata": {
                    "verification_level": "id_verification|enhanced",
                    "timestamp": "2024-01-01T12:00:00Z"
                }
            }
        }
        """
        try:
            # Extract event details
            detail = self._extract_event_detail(event)
            logger.info(f"Processing KYC event for user {detail['user_id']}", extra={
                "user_id": detail['user_id'],
                "status": detail['status'],
                "provider": detail['provider']
            })
            
            # Validate event
            validation_errors = self._validate_kyc_event(detail)
            if validation_errors:
                logger.warning(f"Event validation failed: {validation_errors}")
                return self._create_response(400, {"errors": validation_errors})
            
            # Get database connection
            conn = self.get_db_connection()
            
            # Process based on status
            if detail['status'].lower() in ['approved', 'verified', 'success']:
                result = await self._handle_kyc_approval(conn, detail)
            elif detail['status'].lower() in ['rejected', 'failed', 'declined']:
                result = await self._handle_kyc_rejection(conn, detail)
            else:
                logger.warning(f"Unknown KYC status: {detail['status']}")
                result = {
                    'success': True,
                    'action': 'no_update',
                    'reason': f"Status '{detail['status']}' does not require action"
                }
            
            # Record event in audit log
            await self._log_audit_event(conn, detail, result)
            conn.commit()
            
            # Publish to SNS for downstream processing
            await self._publish_to_sns(detail, result)
            
            # Record metrics
            if detail['status'].lower() in ['approved', 'verified', 'success']:
                metrics.add_metric(name=METRIC_KYC_APPROVED, unit='Count', value=1)
            else:
                metrics.add_metric(name=METRIC_KYC_REJECTED, unit='Count', value=1)
            
            processing_time = (datetime.utcnow() - self.event_start_time).total_seconds()
            metrics.add_metric(name=METRIC_PROCESSING_TIME, unit='Milliseconds', 
                             value=processing_time * 1000)
            
            return self._create_response(200, result)
        
        except Exception as e:
            logger.exception(f"Event processing failed: {e}")
            metrics.add_metric(name='ProcessingErrors', unit='Count', value=1)
            if self.db_connection and not self.db_connection.closed:
                self.db_connection.rollback()
            return self._create_response(500, {"error": str(e)})
    
    def _extract_event_detail(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Extract KYC details from various event formats"""
        # EventBridge format
        if 'detail' in event:
            return event['detail']
        
        # SNS wrapped format
        if 'Message' in event:
            try:
                message = json.loads(event['Message'])
                if 'detail' in message:
                    return message['detail']
                return message
            except:
                pass
        
        # Direct format
        return event
    
    def _validate_kyc_event(self, detail: Dict[str, Any]) -> list:
        """Validate required fields in KYC event"""
        errors = []
        required_fields = ['user_id', 'status', 'provider']
        
        for field in required_fields:
            if field not in detail or not detail[field]:
                errors.append(f"Missing required field: {field}")
        
        # Validate status
        valid_statuses = ['approved', 'rejected', 'verified', 'success', 'failed', 'declined']
        if detail.get('status', '').lower() not in valid_statuses:
            errors.append(f"Invalid status: {detail.get('status')}")
        
        return errors
    
    async def _handle_kyc_approval(self, conn, detail: Dict[str, Any]) -> Dict[str, Any]:
        """Handle KYC approval"""
        user_id = detail['user_id']
        provider = detail['provider']
        external_id = detail.get('externalId', '')
        
        try:
            # Update user KYC status
            cursor = conn.cursor()
            cursor.execute(
                sql.SQL("""
                    UPDATE "user" 
                    SET kyc_status = %s, 
                        updated_at = %s,
                        kyc_verified_at = %s,
                        kyc_provider = %s,
                        kyc_external_id = %s
                    WHERE id = %s
                    RETURNING id, email, full_name
                """),
                ('approved', datetime.utcnow(), datetime.utcnow(), provider, external_id, user_id)
            )
            
            result = cursor.fetchone()
            if not result:
                logger.warning(f"User {user_id} not found in database")
                return {'success': False, 'error': 'User not found'}
            
            user_email, user_name = result[1], result[2]
            cursor.close()
            
            logger.info(f"User {user_id} KYC approved via {provider}")
            
            # Send approval email
            await self._send_kyc_approval_email(user_email, user_name)
            
            # Invoke fraud detector for new approved user
            if LAMBDA_FRAUD_DETECTOR:
                await self._invoke_lambda_async(
                    LAMBDA_FRAUD_DETECTOR,
                    {
                        'source': 'kyc.dispatcher',
                        'detail': {
                            'user_id': user_id,
                            'event_type': 'kyc_approved',
                            'provider': provider
                        }
                    }
                )
            
            return {
                'success': True,
                'action': 'approved',
                'user_id': user_id,
                'provider': provider
            }
        
        except Exception as e:
            logger.exception(f"Failed to approve KYC for user {user_id}: {e}")
            return {'success': False, 'error': str(e)}
    
    async def _handle_kyc_rejection(self, conn, detail: Dict[str, Any]) -> Dict[str, Any]:
        """Handle KYC rejection"""
        user_id = detail['user_id']
        provider = detail['provider']
        rejection_reason = detail.get('rejection_reason', 'Document verification failed')
        external_id = detail.get('externalId', '')
        
        try:
            # Update user KYC status
            cursor = conn.cursor()
            cursor.execute(
                sql.SQL("""
                    UPDATE "user" 
                    SET kyc_status = %s,
                        kyc_rejection_reason = %s,
                        updated_at = %s,
                        kyc_provider = %s,
                        kyc_external_id = %s,
                        kyc_rejected_at = %s
                    WHERE id = %s
                    RETURNING id, email, full_name
                """),
                ('rejected', rejection_reason, datetime.utcnow(), provider, 
                 external_id, datetime.utcnow(), user_id)
            )
            
            result = cursor.fetchone()
            if not result:
                logger.warning(f"User {user_id} not found in database")
                return {'success': False, 'error': 'User not found'}
            
            user_email, user_name = result[1], result[2]
            cursor.close()
            
            logger.warning(f"User {user_id} KYC rejected via {provider}: {rejection_reason}")
            
            # Send rejection email with reason
            await self._send_kyc_rejection_email(user_email, user_name, rejection_reason)
            
            return {
                'success': True,
                'action': 'rejected',
                'user_id': user_id,
                'provider': provider,
                'reason': rejection_reason
            }
        
        except Exception as e:
            logger.exception(f"Failed to reject KYC for user {user_id}: {e}")
            return {'success': False, 'error': str(e)}
    
    async def _log_audit_event(self, conn, detail: Dict[str, Any], 
                              result: Dict[str, Any]):
        """Log KYC event to audit trail"""
        try:
            cursor = conn.cursor()
            cursor.execute(
                sql.SQL("""
                    INSERT INTO audit_log (
                        admin_id, user_id, action_type, reason, 
                        details, status, created_at
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """),
                (
                    1,  # System user
                    detail['user_id'],
                    'kyc_event_received',
                    f"KYC {detail['status']} from {detail['provider']}",
                    json.dumps({
                        'provider': detail['provider'],
                        'status': detail['status'],
                        'externalId': detail.get('externalId'),
                        'result': result
                    }),
                    'success',
                    datetime.utcnow()
                )
            )
            cursor.close()
        except Exception as e:
            logger.warning(f"Failed to log audit event: {e}")
    
    async def _publish_to_sns(self, detail: Dict[str, Any], result: Dict[str, Any]):
        """Publish KYC event to SNS for downstream processors"""
        try:
            if not SNS_KYC_TOPIC:
                logger.debug("SNS topic not configured, skipping publish")
                return
            
            message = {
                'source': 'kyc.dispatcher',
                'detail': detail,
                'result': result,
                'timestamp': datetime.utcnow().isoformat()
            }
            
            sns_client.publish(
                TopicArn=SNS_KYC_TOPIC,
                Subject=f"KYC Event: {detail['status'].upper()} - {detail.get('provider', 'unknown')}",
                Message=json.dumps(message),
                MessageAttributes={
                    'EventType': {'DataType': 'String', 'StringValue': detail['status']},
                    'Provider': {'DataType': 'String', 'StringValue': detail.get('provider', 'unknown')},
                    'UserId': {'DataType': 'String', 'StringValue': detail['user_id']}
                }
            )
            
            logger.info(f"Published KYC event to SNS: {SNS_KYC_TOPIC}")
        except Exception as e:
            logger.warning(f"Failed to publish to SNS: {e}")
    
    async def _send_kyc_approval_email(self, email: str, name: str):
        """Send approval email via SES"""
        try:
            ses_client.send_email(
                Source=SES_SENDER_EMAIL,
                Destination={'ToAddresses': [email]},
                Message={
                    'Subject': {'Data': 'Your Account is Now Verified - Finanza Bank'},
                    'Body': {
                        'Html': {
                            'Data': f"""
                            <html>
                                <body>
                                    <h1>Welcome to Finanza Bank!</h1>
                                    <p>Hi {name},</p>
                                    <p>Your identity verification is complete and your account has been approved.</p>
                                    <p>You can now access all features of Finanza Bank:</p>
                                    <ul>
                                        <li>Make transfers and payments</li>
                                        <li>Withdraw funds</li>
                                        <li>Access all banking products</li>
                                    </ul>
                                    <p>Best regards,<br>Finanza Bank Team</p>
                                </body>
                            </html>
                            """
                        }
                    }
                }
            )
            logger.info(f"KYC approval email sent to {email}")
        except Exception as e:
            logger.warning(f"Failed to send approval email: {e}")
    
    async def _send_kyc_rejection_email(self, email: str, name: str, reason: str):
        """Send rejection email via SES"""
        try:
            ses_client.send_email(
                Source=SES_SENDER_EMAIL,
                Destination={'ToAddresses': [email]},
                Message={
                    'Subject': {'Data': 'Account Verification Update - Finanza Bank'},
                    'Body': {
                        'Html': {
                            'Data': f"""
                            <html>
                                <body>
                                    <h1>Account Verification Status</h1>
                                    <p>Hi {name},</p>
                                    <p>Your identity verification could not be completed at this time.</p>
                                    <p><strong>Reason:</strong> {reason}</p>
                                    <p>Please ensure:</p>
                                    <ul>
                                        <li>Your document is clear and in focus</li>
                                        <li>All text is readable</li>
                                        <li>Your face is visible in any selfie</li>
                                    </ul>
                                    <p>Please try again with a clearer document or contact support for assistance.</p>
                                    <p>Best regards,<br>Finanza Bank Team</p>
                                </body>
                            </html>
                            """
                        }
                    }
                }
            )
            logger.info(f"KYC rejection email sent to {email}")
        except Exception as e:
            logger.warning(f"Failed to send rejection email: {e}")
    
    async def _invoke_lambda_async(self, function_name: str, payload: Dict[str, Any]):
        """Invoke another Lambda function asynchronously"""
        try:
            lambda_client.invoke(
                FunctionName=function_name,
                InvocationType='Event',  # Async invocation
                Payload=json.dumps(payload)
            )
            logger.info(f"Invoked Lambda function: {function_name}")
        except Exception as e:
            logger.warning(f"Failed to invoke Lambda {function_name}: {e}")
    
    def _create_response(self, status_code: int, body: Dict[str, Any]) -> Dict[str, Any]:
        """Create standardized Lambda response"""
        return {
            'statusCode': status_code,
            'body': json.dumps(body),
            'headers': {
                'Content-Type': 'application/json',
                'X-Lambda-Function': 'finanza-kyc-dispatcher'
            }
        }


# ==================== Lambda Handler ====================
dispatcher = KycEventDispatcher()


@tracer.capture_lambda_handler
@logger.inject_lambda_context
async def lambda_handler(event: Dict[str, Any], context: LambdaContext) -> Dict[str, Any]:
    """
    AWS Lambda handler for KYC event processing.
    
    Supports multiple event sources:
    - EventBridge rules
    - SNS subscriptions
    - Direct Lambda invocations
    """
    try:
        logger.info(f"Received event from {event.get('source', 'unknown')}")
        logger.debug(f"Event: {json.dumps(event)}", extra={"event": event})
        
        # Initialize dispatcher
        await dispatcher.initialize()
        
        # Process event
        response = await dispatcher.process_kyc_event(event)
        
        return response
    
    except Exception as e:
        logger.exception(f"Lambda handler error: {e}")
        metrics.add_metric(name='UnhandledErrors', unit='Count', value=1)
        return {
            'statusCode': 500,
            'body': json.dumps({'error': 'Internal server error'})
        }
    
    finally:
        # Cleanup
        dispatcher.close_db_connection()
        metrics.flush()


# ==================== Async Wrapper ====================
def lambda_handler_sync(event: Dict[str, Any], context: LambdaContext) -> Dict[str, Any]:
    """
    Synchronous wrapper for async handler.
    
    AWS Lambda doesn't natively support async handlers, so we wrap it.
    """
    return asyncio.run(lambda_handler(event, context))
