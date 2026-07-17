"""
Lambda: Fraud Detection for KYC-Approved Users

Triggers after KYC approval to perform fraud risk assessment.
- Checks transaction patterns
- Analyzes device fingerprinting
- Scores fraud risk (0-1)
- Updates user risk profile in RDS
- Returns fraud verdict to SNS

Event Source: SNS from KYC Dispatcher
Environment: FRAUD_SCORE_THRESHOLD, RDS_HOST, RDS_USER
"""

import json
import boto3
import psycopg2
import asyncio
from datetime import datetime, timedelta
from aws_lambda_powertools import Logger, Tracer, Metrics
from aws_lambda_powertools.utilities.data_classes.sns_event import SNSEvent
from aws_lambda_powertools.utilities.typing import LambdaContext

logger = Logger()
tracer = Tracer()
metrics = Metrics()

rds_client = boto3.client('rds')
secretsmanager = boto3.client('secretsmanager')
sns = boto3.client('sns')
dynamodb = boto3.resource('dynamodb')


class FraudDetector:
    def __init__(self):
        self.db_conn = None
        self.fraud_threshold = float(os.getenv('FRAUD_SCORE_THRESHOLD', '0.7'))
        self.risk_profile_table = dynamodb.Table(os.getenv('RISK_PROFILE_TABLE', 'user_risk_profiles'))
        
    async def initialize(self):
        """Fetch secrets and establish DB connection"""
        secret = await self._get_secret('finanza/rds/password')
        self.db_conn = psycopg2.connect(
            host=os.getenv('RDS_HOST'),
            database='finanza',
            user=os.getenv('RDS_USER', 'postgres'),
            password=secret['password'],
            port=5432,
            connect_timeout=5
        )
        logger.info("Fraud detector initialized")
    
    async def detect_fraud(self, event):
        """Main fraud detection flow"""
        try:
            # Parse SNS message
            record = event['Records'][0]
            message = json.loads(record['Sns']['Message'])
            
            user_id = message['user_id']
            provider = message.get('provider', 'unknown')
            
            logger.info(f"Analyzing fraud risk for user {user_id}")
            metrics.add_metric(name="FraudCheckStarted", unit="Count", value=1)
            
            # Run concurrent checks
            fraud_score = await asyncio.gather(
                self._check_velocity_fraud(user_id),
                self._check_device_fraud(user_id),
                self._check_geographic_fraud(user_id),
                self._check_identity_fraud(user_id)
            )
            
            # Average scores with weights
            weighted_score = (
                fraud_score[0] * 0.35 +  # Velocity (velocity patterns strong indicator)
                fraud_score[1] * 0.25 +  # Device (hardware changes risky)
                fraud_score[2] * 0.25 +  # Geographic (location changes suspicious)
                fraud_score[3] * 0.15    # Identity (document validity lower weight)
            )
            
            risk_level = 'HIGH' if weighted_score > self.fraud_threshold else 'LOW'
            
            # Update risk profile
            await self._update_risk_profile(user_id, weighted_score, risk_level)
            
            # Publish result to SNS
            await self._publish_fraud_result(user_id, weighted_score, risk_level, provider)
            
            metrics.add_metric(name="FraudCheckCompleted", unit="Count", value=1)
            metrics.add_metric(name="FraudScore", unit="None", value=weighted_score)
            
            return {
                'statusCode': 200,
                'user_id': user_id,
                'fraud_score': weighted_score,
                'risk_level': risk_level
            }
            
        except Exception as e:
            logger.exception(f"Fraud detection failed: {e}")
            metrics.add_metric(name="FraudCheckError", unit="Count", value=1)
            raise
    
    async def _check_velocity_fraud(self, user_id):
        """Check if user has suspicious transaction velocity"""
        try:
            cursor = self.db_conn.cursor()
            
            # Count transactions in last 24 hours
            cursor.execute("""
                SELECT COUNT(*) as tx_count, SUM(amount) as total_amount
                FROM transactions
                WHERE user_id = %s 
                AND created_at > NOW() - INTERVAL '24 hours'
                AND status = 'completed'
            """, (user_id,))
            
            result = cursor.fetchone()
            tx_count = result[0] if result else 0
            total_amount = result[1] if result else 0
            
            cursor.close()
            
            # Scoring logic
            if tx_count > 50 or total_amount > 100000:
                return 0.8  # High velocity suspicious
            elif tx_count > 20 or total_amount > 50000:
                return 0.5  # Medium velocity
            else:
                return 0.1  # Normal velocity
                
        except Exception as e:
            logger.error(f"Velocity check failed: {e}")
            return 0.3  # Default medium risk on error
    
    async def _check_device_fraud(self, user_id):
        """Check for suspicious device changes"""
        try:
            response = self.risk_profile_table.get_item(Key={'user_id': user_id})
            
            if 'Item' in response:
                profile = response['Item']
                last_device_id = profile.get('last_device_id')
                current_device_id = profile.get('current_device_id')
                
                if last_device_id and current_device_id != last_device_id:
                    # Device changed recently
                    days_since_change = (datetime.now() - profile.get('last_device_change', datetime.now())).days
                    
                    if days_since_change < 7:
                        return 0.7  # Recent device change risky
                    else:
                        return 0.3  # Older device change acceptable
            
            return 0.1  # First device or no change
            
        except Exception as e:
            logger.error(f"Device check failed: {e}")
            return 0.2
    
    async def _check_geographic_fraud(self, user_id):
        """Check for suspicious geographic patterns"""
        try:
            cursor = self.db_conn.cursor()
            
            cursor.execute("""
                SELECT country, created_at
                FROM user_locations
                WHERE user_id = %s
                ORDER BY created_at DESC
                LIMIT 2
            """, (user_id,))
            
            locations = cursor.fetchall()
            cursor.close()
            
            if len(locations) >= 2:
                last_country = locations[0][0]
                prev_country = locations[1][0]
                time_diff = (locations[0][1] - locations[1][1]).total_seconds() / 3600  # hours
                
                if last_country != prev_country and time_diff < 24:
                    # Impossible travel (changed countries in <24h)
                    return 0.9
                elif last_country != prev_country:
                    return 0.4  # Country changed but reasonable timeframe
            
            return 0.1  # Same country or first location
            
        except Exception as e:
            logger.error(f"Geographic check failed: {e}")
            return 0.2
    
    async def _check_identity_fraud(self, user_id):
        """Check identity document validity"""
        try:
            cursor = self.db_conn.cursor()
            
            cursor.execute("""
                SELECT document_status, document_type
                FROM kyc_documents
                WHERE user_id = %s
                ORDER BY created_at DESC
                LIMIT 1
            """, (user_id,))
            
            result = cursor.fetchone()
            cursor.close()
            
            if result:
                status, doc_type = result
                
                if status == 'rejected':
                    return 0.6  # Document was rejected once
                elif status == 'verified' and doc_type in ['passport', 'national_id']:
                    return 0.1  # Strong document types
                else:
                    return 0.3  # Other document types
            
            return 0.5  # No documents found
            
        except Exception as e:
            logger.error(f"Identity check failed: {e}")
            return 0.3
    
    async def _update_risk_profile(self, user_id, score, level):
        """Update user's risk profile in DynamoDB"""
        try:
            self.risk_profile_table.update_item(
                Key={'user_id': user_id},
                UpdateExpression="""
                    SET fraud_score = :score,
                        risk_level = :level,
                        last_fraud_check = :now,
                        check_count = if_not_exists(check_count, :zero) + :one
                """,
                ExpressionAttributeValues={
                    ':score': score,
                    ':level': level,
                    ':now': datetime.utcnow().isoformat(),
                    ':zero': 0,
                    ':one': 1
                }
            )
            logger.info(f"Risk profile updated: {user_id} -> {level}")
        except Exception as e:
            logger.error(f"Failed to update risk profile: {e}")
    
    async def _publish_fraud_result(self, user_id, score, level, provider):
        """Publish fraud verdict to SNS for downstream processing"""
        try:
            sns.publish(
                TopicArn=os.getenv('FRAUD_RESULTS_TOPIC'),
                Subject=f'Fraud Assessment: {level}',
                Message=json.dumps({
                    'user_id': user_id,
                    'fraud_score': score,
                    'risk_level': level,
                    'provider': provider,
                    'timestamp': datetime.utcnow().isoformat(),
                    'action': 'block_account' if level == 'HIGH' else 'proceed'
                })
            )
            logger.info(f"Fraud result published: {user_id}")
        except Exception as e:
            logger.error(f"Failed to publish fraud result: {e}")
    
    async def _get_secret(self, secret_id):
        """Fetch secret from AWS Secrets Manager"""
        response = secretsmanager.get_secret_value(SecretId=secret_id)
        return json.loads(response['SecretString'])
    
    async def cleanup(self):
        """Close database connection"""
        if self.db_conn:
            self.db_conn.close()
            logger.info("Database connection closed")


# Global instance
detector = FraudDetector()


@tracer.capture_lambda_handler
@logger.inject_lambda_context
async def lambda_handler(event, context: LambdaContext):
    """Lambda handler for fraud detection"""
    try:
        await detector.initialize()
        result = await detector.detect_fraud(event)
        return {
            'statusCode': 200,
            'body': json.dumps(result)
        }
    except Exception as e:
        logger.exception(f"Lambda handler error: {e}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }
    finally:
        await detector.cleanup()


# For testing
if __name__ == '__main__':
    import os
    
    test_event = {
        'Records': [{
            'Sns': {
                'Message': json.dumps({
                    'user_id': '550e8400-e29b-41d4-a716-446655440000',
                    'status': 'completed',
                    'provider': 'jumio'
                })
            }
        }]
    }
    
    result = asyncio.run(lambda_handler(test_event, None))
    print(json.dumps(result, indent=2))
