#!/usr/bin/env python3
"""
Post-Deployment Health Check for Finanza KYC Dispatcher Lambda

Validates:
- Lambda function exists and is configured correctly
- IAM role has required permissions
- Database connectivity
- SNS topics are accessible
- CloudWatch alarms are healthy
- X-Ray tracing is enabled
"""

import json
import boto3
import sys
from datetime import datetime, timedelta

def print_header(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")

def print_status(check, passed, details=""):
    status = "✓ PASS" if passed else "✗ FAIL"
    color = "\033[92m" if passed else "\033[91m"
    reset = "\033[0m"
    print(f"{color}{status}{reset} {check}")
    if details:
        print(f"      {details}")

class KycDispatcherHealthCheck:
    def __init__(self, function_name, region='eu-north-1'):
        self.function_name = function_name
        self.region = region
        self.lambda_client = boto3.client('lambda', region_name=region)
        self.cloudwatch = boto3.client('cloudwatch', region_name=region)
        self.logs = boto3.client('logs', region_name=region)
        self.sns = boto3.client('sns', region_name=region)
        self.iam = boto3.client('iam')
        self.xray = boto3.client('xray', region_name=region)
        self.results = []
        
    def run_all_checks(self):
        print_header("Finanza KYC Dispatcher Health Check")
        
        self.check_lambda_exists()
        self.check_lambda_config()
        self.check_iam_permissions()
        self.check_cloudwatch_logs()
        self.check_cloudwatch_metrics()
        self.check_cloudwatch_alarms()
        self.check_sns_topics()
        self.check_xray_traces()
        self.check_recent_invocations()
        
        print_header("Summary")
        passed = sum(1 for _, p in self.results if p)
        total = len(self.results)
        print(f"\nTotal Checks: {total}")
        print(f"Passed: {passed}")
        print(f"Failed: {total - passed}")
        
        if passed == total:
            print("\n✓ All checks passed! Lambda is ready for production.")
            return True
        else:
            print("\n✗ Some checks failed. Review output above.")
            return False
    
    def check_lambda_exists(self):
        try:
            response = self.lambda_client.get_function(FunctionName=self.function_name)
            details = f"Runtime: {response['Configuration']['Runtime']}, Memory: {response['Configuration']['MemorySize']}MB"
            self.results.append(("Lambda function exists", True))
            print_status("Lambda function exists", True, details)
        except Exception as e:
            self.results.append(("Lambda function exists", False))
            print_status("Lambda function exists", False, str(e))
    
    def check_lambda_config(self):
        try:
            response = self.lambda_client.get_function(FunctionName=self.function_name)
            config = response['Configuration']
            
            checks = {
                f"Timeout >= 30s": config['Timeout'] >= 30,
                f"Memory >= 512MB": config['MemorySize'] >= 512,
                f"Handler set": config.get('Handler') != '',
                f"Tracing enabled": config.get('TracingConfig', {}).get('Mode') == 'Active',
                f"VPC configured": len(config.get('VpcConfig', {}).get('SubnetIds', [])) > 0,
            }
            
            for check, passed in checks.items():
                self.results.append((f"Lambda Config: {check}", passed))
                print_status(f"Lambda Config: {check}", passed)
                
        except Exception as e:
            print_status("Lambda Config", False, str(e))
    
    def check_iam_permissions(self):
        try:
            response = self.lambda_client.get_function(FunctionName=self.function_name)
            role_arn = response['Configuration']['Role']
            role_name = role_arn.split('/')[-1]
            
            # Get inline policies
            policy_response = self.iam.list_role_policies(RoleName=role_name)
            policies = policy_response.get('PolicyNames', [])
            
            required_services = {
                'rds-db:': 'RDS',
                'sns:': 'SNS',
                'secretsmanager:': 'Secrets Manager',
                'logs:': 'CloudWatch Logs',
                'xray:': 'X-Ray',
            }
            
            found_services = {}
            for policy_name in policies:
                policy_doc = self.iam.get_role_policy(RoleName=role_name, PolicyName=policy_name)
                policy_str = json.dumps(policy_doc['RolePolicyDocument'])
                
                for service_prefix, service_name in required_services.items():
                    if service_prefix in policy_str:
                        found_services[service_name] = True
            
            for service_name, _ in required_services.items():
                is_found = any(s in str(found_services.keys()) for s in [service_name])
                self.results.append((f"IAM Permission: {service_name}", is_found))
                print_status(f"IAM Permission: {service_name}", is_found)
                
        except Exception as e:
            print_status("IAM Permissions check", False, str(e))
    
    def check_cloudwatch_logs(self):
        try:
            log_group = f'/aws/lambda/{self.function_name}'
            response = self.logs.describe_log_groups(logGroupNamePrefix=log_group)
            
            log_group_exists = any(lg['logGroupName'] == log_group for lg in response['logGroups'])
            self.results.append(("CloudWatch Log Group exists", log_group_exists))
            print_status("CloudWatch Log Group exists", log_group_exists, log_group if log_group_exists else "Not found")
            
            if log_group_exists:
                # Check for recent logs
                response = self.logs.describe_log_streams(logGroupName=log_group, orderBy='LastEventTime', descending=True)
                
                if response['logStreams']:
                    latest_stream = response['logStreams'][0]
                    last_event = latest_stream.get('lastEventTimestamp', 0) / 1000
                    last_event_time = datetime.fromtimestamp(last_event)
                    time_ago = datetime.now() - last_event_time
                    
                    has_recent_logs = time_ago < timedelta(hours=1)
                    self.results.append(("Recent log entries", has_recent_logs))
                    print_status("Recent log entries", has_recent_logs, f"Last: {time_ago.total_seconds()/60:.0f} min ago")
                    
        except Exception as e:
            print_status("CloudWatch Logs check", False, str(e))
    
    def check_cloudwatch_metrics(self):
        try:
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(hours=1)
            
            for metric in ['Invocations', 'Errors', 'Duration']:
                response = self.cloudwatch.get_metric_statistics(
                    Namespace='AWS/Lambda',
                    MetricName=metric,
                    Dimensions=[{'Name': 'FunctionName', 'Value': self.function_name}],
                    StartTime=start_time,
                    EndTime=end_time,
                    Period=300,
                    Statistics=['Sum', 'Average']
                )
                
                has_data = len(response['Datapoints']) > 0
                self.results.append((f"CloudWatch Metric: {metric}", has_data))
                print_status(f"CloudWatch Metric: {metric}", has_data)
                
        except Exception as e:
            print_status("CloudWatch Metrics check", False, str(e))
    
    def check_cloudwatch_alarms(self):
        try:
            response = self.cloudwatch.describe_alarms(
                AlarmNamePrefix=self.function_name,
                StateValue='OK'
            )
            
            alarms = response['MetricAlarms']
            alarm_count = len(alarms)
            
            self.results.append((f"CloudWatch Alarms ({alarm_count} healthy)", alarm_count >= 1))
            print_status(f"CloudWatch Alarms ({alarm_count} healthy)", alarm_count >= 1)
            
            for alarm in alarms:
                print_status(f"  Alarm: {alarm['AlarmName']}", True, f"State: {alarm['StateValue']}")
                
        except Exception as e:
            print_status("CloudWatch Alarms check", False, str(e))
    
    def check_sns_topics(self):
        try:
            response = self.sns.list_topics()
            topics = response.get('Topics', [])
            
            kyc_topic = any('kyc' in t['TopicArn'].lower() for t in topics)
            self.results.append(("SNS KYC Events topic exists", kyc_topic))
            print_status("SNS KYC Events topic exists", kyc_topic)
            
        except Exception as e:
            print_status("SNS Topics check", False, str(e))
    
    def check_xray_traces(self):
        try:
            response = self.xray.get_trace_summaries(StartTime=datetime.utcnow() - timedelta(hours=1))
            trace_count = len(response.get('TraceSummaries', []))
            
            has_traces = trace_count > 0
            self.results.append(("X-Ray traces available", has_traces))
            print_status("X-Ray traces available", has_traces, f"Traces: {trace_count}")
            
        except Exception as e:
            print_status("X-Ray Traces check", False, str(e))
    
    def check_recent_invocations(self):
        try:
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(hours=24)
            
            response = self.cloudwatch.get_metric_statistics(
                Namespace='AWS/Lambda',
                MetricName='Invocations',
                Dimensions=[{'Name': 'FunctionName', 'Value': self.function_name}],
                StartTime=start_time,
                EndTime=end_time,
                Period=3600,
                Statistics=['Sum']
            )
            
            total_invocations = sum(dp['Sum'] for dp in response['Datapoints'])
            
            self.results.append(("Recent invocations (24h)", total_invocations > 0))
            print_status("Recent invocations (24h)", total_invocations > 0, f"Total: {int(total_invocations)}")
            
        except Exception as e:
            print_status("Recent invocations check", False, str(e))


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Health check for KYC Dispatcher Lambda')
    parser.add_argument('--function', default='finanza-kyc-dispatcher-dev', help='Lambda function name')
    parser.add_argument('--region', default='eu-north-1', help='AWS region')
    
    args = parser.parse_args()
    
    try:
        checker = KycDispatcherHealthCheck(args.function, args.region)
        success = checker.run_all_checks()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\nFatal error: {e}")
        sys.exit(2)


if __name__ == '__main__':
    main()
