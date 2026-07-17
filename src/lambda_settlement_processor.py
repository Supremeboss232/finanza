"""
Lambda: Settlement Processing for Financial Transactions

Processes fund transfers and settlement operations:
- Validates transaction details
- Executes inter-bank transfers
- Updates ledger entries
- Tracks settlement status
- Publishes settlement confirmations

Event Source: SNS from Payment Webhook Receiver
Triggered by: Stripe/Paystack transfer events
Integration: RDS ledger + DynamoDB settlement state
"""

import json
import boto3
import psycopg2
from datetime import datetime, timedelta
import os
from aws_lambda_powertools import Logger, Tracer, Metrics
from aws_lambda_powertools.utilities.data_classes.sns_event import SNSEvent
from aws_lambda_powertools.utilities.typing import LambdaContext

logger = Logger()
tracer = Tracer()
metrics = Metrics()

sns = boto3.client('sns')
dynamodb = boto3.resource('dynamodb')
secretsmanager = boto3.client('secretsmanager')
ssm = boto3.client('ssm')


class SettlementProcessor:
    def __init__(self):
        self.db_conn = None
        self.settlement_table = dynamodb.Table(os.getenv('SETTLEMENT_TABLE', 'settlement_status'))
        self.settlement_timeout = int(os.getenv('SETTLEMENT_TIMEOUT_HOURS', '24'))
        
    async def initialize(self):
        """Establish database connection and fetch configuration"""
        secret = await self._get_secret('finanza/rds/password')
        self.db_conn = psycopg2.connect(
            host=os.getenv('RDS_HOST'),
            database='finanza',
            user=os.getenv('RDS_USER', 'postgres'),
            password=secret['password'],
            port=5432,
            connect_timeout=5
        )
        logger.info("Settlement processor initialized")
    
    async def process_settlement(self, event):
        """Main settlement processing flow"""
        try:
            # Parse SNS message
            record = event['Records'][0]
            message = json.loads(record['Sns']['Message'])
            
            transfer_id = message.get('transfer_id')
            user_id = message.get('user_id')
            amount = message.get('amount')
            recipient_bank = message.get('recipient_bank')
            recipient_account = message.get('recipient_account')
            
            logger.info(f"Processing settlement: {transfer_id} for user {user_id}")
            metrics.add_metric(name="SettlementStarted", unit="Count", value=1)
            
            # 1. Validate transaction
            is_valid = await self._validate_transaction(transfer_id, user_id, amount)
            if not is_valid:
                logger.warning(f"Settlement validation failed: {transfer_id}")
                await self._update_settlement_status(transfer_id, 'VALIDATION_FAILED')
                metrics.add_metric(name="SettlementValidationFailed", unit="Count", value=1)
                return {'statusCode': 400, 'error': 'Validation failed'}
            
            # 2. Check compliance
            is_compliant = await self._check_aml_compliance(user_id, amount)
            if not is_compliant:
                logger.warning(f"AML check failed: {transfer_id}")
                await self._update_settlement_status(transfer_id, 'AML_BLOCKED')
                metrics.add_metric(name="SettlementAMLBlocked", unit="Count", value=1)
                return {'statusCode': 403, 'error': 'AML compliance check failed'}
            
            # 3. Execute transfer
            transfer_result = await self._execute_transfer(
                transfer_id, user_id, amount, 
                recipient_bank, recipient_account
            )
            
            if not transfer_result['success']:
                logger.error(f"Transfer execution failed: {transfer_id}")
                await self._update_settlement_status(transfer_id, 'TRANSFER_FAILED')
                metrics.add_metric(name="SettlementTransferFailed", unit="Count", value=1)
                return {'statusCode': 500, 'error': 'Transfer failed'}
            
            # 4. Update ledger
            ledger_entry_id = await self._record_ledger_entry(
                transfer_id, user_id, amount, 
                'DEBIT', 'settlement', transfer_result['reference']
            )
            
            # 5. Update settlement status to completed
            await self._update_settlement_status(transfer_id, 'COMPLETED')
            
            # 6. Publish confirmation
            await self._publish_settlement_confirmation(
                transfer_id, user_id, amount, 
                transfer_result['reference'], 'SUCCESS'
            )
            
            metrics.add_metric(name="SettlementCompleted", unit="Count", value=1)
            metrics.add_metric(name="SettlementAmount", unit="None", value=amount)
            
            logger.info(f"Settlement completed: {transfer_id}")
            return {
                'statusCode': 200,
                'transfer_id': transfer_id,
                'status': 'COMPLETED',
                'reference': transfer_result['reference'],
                'ledger_entry': ledger_entry_id
            }
            
        except Exception as e:
            logger.exception(f"Settlement processing failed: {e}")
            metrics.add_metric(name="SettlementError", unit="Count", value=1)
            raise
    
    async def _validate_transaction(self, transfer_id, user_id, amount):
        """Validate transaction details against business rules"""
        try:
            cursor = self.db_conn.cursor()
            
            # Check user account status
            cursor.execute("""
                SELECT account_status, balance
                FROM accounts
                WHERE user_id = %s
                LIMIT 1
            """, (user_id,))
            
            result = cursor.fetchone()
            if not result:
                logger.warning(f"Account not found: {user_id}")
                return False
            
            account_status, balance = result
            cursor.close()
            
            # Validations
            if account_status != 'active':
                logger.warning(f"Account not active: {user_id}")
                return False
            
            if balance < amount:
                logger.warning(f"Insufficient balance: {user_id}")
                return False
            
            if amount <= 0:
                logger.warning(f"Invalid amount: {amount}")
                return False
            
            if amount > 1000000:  # Single transaction limit
                logger.warning(f"Amount exceeds limit: {amount}")
                return False
            
            logger.info(f"Transaction validation passed: {transfer_id}")
            return True
            
        except Exception as e:
            logger.error(f"Validation error: {e}")
            return False
    
    async def _check_aml_compliance(self, user_id, amount):
        """Check AML/Sanctions screening"""
        try:
            cursor = self.db_conn.cursor()
            
            # Check if user on sanctions list
            cursor.execute("""
                SELECT COUNT(*)
                FROM sanctions_list
                WHERE user_id = %s
                AND active = true
            """, (user_id,))
            
            sanctions_count = cursor.fetchone()[0]
            cursor.close()
            
            if sanctions_count > 0:
                logger.warning(f"User on sanctions list: {user_id}")
                return False
            
            # Could integrate with external AML provider here
            # For now, simple check
            
            logger.info(f"AML compliance check passed: {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"AML compliance check error: {e}")
            return False  # Fail safe
    
    async def _execute_transfer(self, transfer_id, user_id, amount, recipient_bank, recipient_account):
        """Execute actual fund transfer to recipient bank"""
        try:
            # In production, this would call your payment processor
            # For now, simulate transfer
            
            logger.info(f"Executing transfer: {transfer_id} to {recipient_bank}")
            
            # Simulate external API call
            transfer_reference = f"FT-{transfer_id[:8]}-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
            
            # Record in DynamoDB settlement state
            self.settlement_table.put_item(
                Item={
                    'settlement_id': transfer_id,
                    'user_id': user_id,
                    'amount': amount,
                    'recipient_bank': recipient_bank,
                    'recipient_account': recipient_account,
                    'reference': transfer_reference,
                    'status': 'IN_PROGRESS',
                    'initiated_at': datetime.utcnow().isoformat(),
                    'timeout_at': (datetime.utcnow() + timedelta(hours=self.settlement_timeout)).isoformat()
                }
            )
            
            # Would call payment processor API here
            # payment_service.initiate_transfer(...)
            
            logger.info(f"Transfer initiated: {transfer_reference}")
            return {
                'success': True,
                'reference': transfer_reference,
                'status': 'IN_PROGRESS'
            }
            
        except Exception as e:
            logger.error(f"Transfer execution error: {e}")
            return {'success': False, 'error': str(e)}
    
    async def _record_ledger_entry(self, transfer_id, user_id, amount, debit_credit, entry_type, reference):
        """Record transaction in ledger"""
        try:
            cursor = self.db_conn.cursor()
            
            cursor.execute("""
                INSERT INTO ledger_entries 
                (user_id, transaction_id, amount, debit_credit, entry_type, reference, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, NOW())
                RETURNING id
            """, (user_id, transfer_id, amount, debit_credit, entry_type, reference))
            
            ledger_id = cursor.fetchone()[0]
            self.db_conn.commit()
            cursor.close()
            
            logger.info(f"Ledger entry created: {ledger_id}")
            return ledger_id
            
        except Exception as e:
            logger.error(f"Ledger recording error: {e}")
            self.db_conn.rollback()
            raise
    
    async def _update_settlement_status(self, settlement_id, status):
        """Update settlement status in table"""
        try:
            self.settlement_table.update_item(
                Key={'settlement_id': settlement_id},
                UpdateExpression="SET #status = :status, updated_at = :now",
                ExpressionAttributeNames={'#status': 'status'},
                ExpressionAttributeValues={
                    ':status': status,
                    ':now': datetime.utcnow().isoformat()
                }
            )
            logger.info(f"Settlement status updated: {settlement_id} -> {status}")
        except Exception as e:
            logger.error(f"Failed to update settlement status: {e}")
    
    async def _publish_settlement_confirmation(self, settlement_id, user_id, amount, reference, result):
        """Publish settlement confirmation to SNS"""
        try:
            sns.publish(
                TopicArn=os.getenv('SETTLEMENT_CONFIRMATION_TOPIC'),
                Subject=f'Settlement Confirmation: {result}',
                Message=json.dumps({
                    'settlement_id': settlement_id,
                    'user_id': user_id,
                    'amount': amount,
                    'reference': reference,
                    'status': result,
                    'timestamp': datetime.utcnow().isoformat(),
                    'action': 'credit_user' if result == 'SUCCESS' else 'investigate'
                })
            )
            logger.info(f"Settlement confirmation published: {settlement_id}")
        except Exception as e:
            logger.error(f"Failed to publish settlement confirmation: {e}")
    
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
processor = SettlementProcessor()


@tracer.capture_lambda_handler
@logger.inject_lambda_context
async def lambda_handler(event, context: LambdaContext):
    """Lambda handler for settlement processing"""
    try:
        await processor.initialize()
        result = await processor.process_settlement(event)
        return {
            'statusCode': result.get('statusCode', 200),
            'body': json.dumps(result)
        }
    except Exception as e:
        logger.exception(f"Lambda handler error: {e}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }
    finally:
        await processor.cleanup()


# For testing
if __name__ == '__main__':
    import asyncio
    
    test_event = {
        'Records': [{
            'Sns': {
                'Message': json.dumps({
                    'transfer_id': 'TXN-123456',
                    'user_id': '550e8400-e29b-41d4-a716-446655440000',
                    'amount': 1000.00,
                    'recipient_bank': 'NORDEA',
                    'recipient_account': 'SE1234567890'
                })
            }
        }]
    }
    
    result = asyncio.run(lambda_handler(test_event, None))
    print(json.dumps(result, indent=2))
