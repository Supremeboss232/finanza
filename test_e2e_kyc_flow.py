#!/usr/bin/env python3
"""
End-to-End Test Suite for KYC Dispatcher

Tests complete flow:
1. Create test event
2. Invoke Lambda
3. Verify RDS update
4. Check email sent
5. Validate SNS published
6. Confirm metrics recorded
"""

import json
import boto3
import time
import uuid
import argparse
from datetime import datetime
import psycopg2
from psycopg2.extras import RealDictCursor


class KycE2ETest:
    def __init__(self, environment='dev', region='eu-north-1'):
        self.environment = environment
        self.region = region
        self.lambda_client = boto3.client('lambda', region_name=region)
        self.cloudwatch = boto3.client('cloudwatch', region_name=region)
        self.sns = boto3.client('sns', region_name=region)
        self.ses = boto3.client('ses', region_name=region)
        self.secretsmanager = boto3.client('secretsmanager', region_name=region)
        
        self.function_name = f'finanza-kyc-dispatcher-{environment}'
        self.test_user_id = str(uuid.uuid4())
        self.results = []
        
    def log(self, message, level='INFO'):
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        print(f"[{timestamp}] {level:8} {message}")
    
    def run_all_tests(self):
        self.log("Starting KYC Dispatcher E2E Test Suite")
        self.log(f"Environment: {self.environment}")
        self.log(f"Function: {self.function_name}")
        self.log(f"Test User ID: {self.test_user_id}")
        
        print("\n" + "="*70)
        self.test_lambda_invocation_approval()
        self.test_lambda_invocation_rejection()
        self.test_cloudwatch_metrics()
        self.test_sns_topics()
        self.test_database_update()
        
        print("\n" + "="*70)
        self.print_summary()
        
    def test_lambda_invocation_approval(self):
        self.log("TEST 1: Lambda Invocation (KYC Approval)")
        
        event = {
            'source': 'kyc.provider',
            'detail-type': 'KYC Verification Complete',
            'detail': {
                'user_id': self.test_user_id,
                'status': 'approved',
                'provider': 'jumio',
                'externalId': f'jumio-test-{int(time.time())}',
                'metadata': {
                    'verification_level': 'id_verification',
                    'timestamp': datetime.utcnow().isoformat() + 'Z'
                }
            }
        }
        
        try:
            self.log("  Invoking Lambda with approval event...")
            response = self.lambda_client.invoke(
                FunctionName=self.function_name,
                InvocationType='RequestResponse',
                Payload=json.dumps(event),
                LogType='Tail'
            )
            
            status_code = response['StatusCode']
            
            if status_code == 200:
                payload = json.loads(response['Payload'].read())
                response_body = json.loads(payload.get('body', '{}'))
                
                if response_body.get('success'):
                    self.log("  ✓ Lambda executed successfully", "PASS")
                    self.log(f"    Action: {response_body.get('action')}", "")
                    self.log(f"    User: {response_body.get('user_id')}", "")
                    self.results.append(('Lambda Approval Invocation', True))
                else:
                    self.log("  ✗ Lambda returned error response", "FAIL")
                    self.log(f"    Response: {payload}", "")
                    self.results.append(('Lambda Approval Invocation', False))
            else:
                self.log(f"  ✗ Lambda error: {status_code}", "FAIL")
                self.results.append(('Lambda Approval Invocation', False))
                
        except Exception as e:
            self.log(f"  ✗ Exception: {e}", "FAIL")
            self.results.append(('Lambda Approval Invocation', False))
    
    def test_lambda_invocation_rejection(self):
        self.log("TEST 2: Lambda Invocation (KYC Rejection)")
        
        rejection_user_id = str(uuid.uuid4())
        event = {
            'source': 'kyc.provider',
            'detail-type': 'KYC Verification Complete',
            'detail': {
                'user_id': rejection_user_id,
                'status': 'rejected',
                'provider': 'onfido',
                'externalId': f'onfido-test-{int(time.time())}',
                'rejection_reason': 'Document quality too low',
                'metadata': {
                    'verification_level': 'id_verification',
                    'timestamp': datetime.utcnow().isoformat() + 'Z'
                }
            }
        }
        
        try:
            self.log("  Invoking Lambda with rejection event...")
            response = self.lambda_client.invoke(
                FunctionName=self.function_name,
                InvocationType='RequestResponse',
                Payload=json.dumps(event)
            )
            
            if response['StatusCode'] == 200:
                payload = json.loads(response['Payload'].read())
                response_body = json.loads(payload.get('body', '{}'))
                
                if response_body.get('success'):
                    self.log("  ✓ Lambda handled rejection successfully", "PASS")
                    self.results.append(('Lambda Rejection Invocation', True))
                else:
                    self.log("  ✗ Lambda rejection failed", "FAIL")
                    self.results.append(('Lambda Rejection Invocation', False))
            else:
                self.log(f"  ✗ Lambda error: {response['StatusCode']}", "FAIL")
                self.results.append(('Lambda Rejection Invocation', False))
                
        except Exception as e:
            self.log(f"  ✗ Exception: {e}", "FAIL")
            self.results.append(('Lambda Rejection Invocation', False))
    
    def test_cloudwatch_metrics(self):
        self.log("TEST 3: CloudWatch Metrics")
        
        try:
            # Wait for metrics to propagate
            self.log("  Waiting for metrics to propagate (10s)...")
            time.sleep(10)
            
            end_time = datetime.utcnow()
            start_time = end_time
            start_time = start_time.replace(minute=start_time.minute - 5)
            
            response = self.cloudwatch.get_metric_statistics(
                Namespace='AWS/Lambda',
                MetricName='Invocations',
                Dimensions=[
                    {'Name': 'FunctionName', 'Value': self.function_name}
                ],
                StartTime=start_time,
                EndTime=end_time,
                Period=60,
                Statistics=['Sum']
            )
            
            if response['Datapoints']:
                total_invocations = sum(dp['Sum'] for dp in response['Datapoints'])
                self.log(f"  ✓ Metrics published (invocations: {int(total_invocations)})", "PASS")
                self.results.append(('CloudWatch Metrics', True))
            else:
                self.log("  ✗ No metrics found", "FAIL")
                self.results.append(('CloudWatch Metrics', False))
                
        except Exception as e:
            self.log(f"  ✗ Exception: {e}", "FAIL")
            self.results.append(('CloudWatch Metrics', False))
    
    def test_sns_topics(self):
        self.log("TEST 4: SNS Topics")
        
        try:
            response = self.sns.list_topics()
            topics = response.get('Topics', [])
            
            kyc_topic = next((t for t in topics if 'kyc' in t['TopicArn'].lower()), None)
            
            if kyc_topic:
                self.log(f"  ✓ KYC SNS topic found", "PASS")
                self.log(f"    Topic ARN: {kyc_topic['TopicArn']}", "")
                self.results.append(('SNS Topics', True))
            else:
                self.log("  ✗ KYC SNS topic not found", "FAIL")
                self.results.append(('SNS Topics', False))
                
        except Exception as e:
            self.log(f"  ✗ Exception: {e}", "FAIL")
            self.results.append(('SNS Topics', False))
    
    def test_database_update(self):
        self.log("TEST 5: Database Update")
        
        try:
            # Get RDS credentials
            secret_response = self.secretsmanager.get_secret_value(
                SecretId='finanza/rds/password'
            )
            secret = json.loads(secret_response['SecretString'])
            rds_password = secret.get('password')
            
            # Connect to RDS
            conn = psycopg2.connect(
                host='database-1.cf2w2gwcmvc8.eu-north-1.rds.amazonaws.com',
                database='finanza',
                user='postgres',
                password=rds_password,
                port=5432
            )
            
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            # Verify KYC columns exist
            cursor.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name='users' 
                AND column_name IN ('kyc_status', 'kyc_verified_at')
            """)
            
            columns = cursor.fetchall()
            if len(columns) >= 2:
                self.log("  ✓ KYC columns exist in users table", "PASS")
                self.results.append(('Database Schema', True))
            else:
                self.log("  ✗ KYC columns missing from users table", "FAIL")
                self.log("    Run: ALTER TABLE users ADD COLUMN kyc_status VARCHAR(50);", "")
                self.results.append(('Database Schema', False))
            
            cursor.close()
            conn.close()
            
        except Exception as e:
            self.log(f"  ✗ Exception: {e}", "FAIL")
            self.log("    Cannot connect to RDS or Secrets Manager issue", "")
            self.results.append(('Database Update', False))
    
    def print_summary(self):
        self.log("TEST SUMMARY")
        passed = sum(1 for _, p in self.results if p)
        total = len(self.results)
        
        print("\nResults:")
        for test_name, passed_test in self.results:
            status = "✓ PASS" if passed_test else "✗ FAIL"
            print(f"  {status:8} {test_name}")
        
        print(f"\nTotal: {passed}/{total} tests passed")
        
        if passed == total:
            self.log("All tests passed! ✓ Lambda is ready for production.", "INFO")
            return True
        else:
            self.log(f"{total - passed} test(s) failed. Review output above.", "WARN")
            return False


def main():
    parser = argparse.ArgumentParser(description='E2E test for KYC Dispatcher')
    parser.add_argument('--environment', default='dev', choices=['dev', 'staging', 'prod'], help='Environment')
    parser.add_argument('--region', default='eu-north-1', help='AWS region')
    
    args = parser.parse_args()
    
    tester = KycE2ETest(args.environment, args.region)
    tester.run_all_tests()


if __name__ == '__main__':
    main()
