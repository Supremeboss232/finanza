#!/usr/bin/env python3
"""
CloudWatch Monitoring Dashboard Setup for Finanza Real-Time Services

Creates a comprehensive dashboard with:
- Lambda metrics (invocations, errors, duration)
- RDS metrics (connections, queries, latency)
- SNS metrics (messages, delivery)
- Custom application metrics
- Alarms status
- X-Ray service map
"""

import json
import boto3
from datetime import datetime

cloudwatch = boto3.client('cloudwatch')


def create_monitoring_dashboard(environment='dev', region='eu-north-1'):
    """Create comprehensive monitoring dashboard"""
    
    dashboard_name = f'finanza-realtime-{environment}-dashboard'
    
    dashboard_body = {
        "widgets": [
            {
                "type": "metric",
                "x": 0,
                "y": 0,
                "width": 12,
                "height": 6,
                "properties": {
                    "title": "Lambda - KYC Dispatcher Health",
                    "metrics": [
                        ["AWS/Lambda", "Invocations", {"stat": "Sum", "label": "Invocations"}],
                        [".", "Errors", {"stat": "Sum", "label": "Errors"}],
                        [".", "Throttles", {"stat": "Sum", "label": "Throttles"}],
                        [".", "Duration", {"stat": "Average", "label": "Avg Duration (ms)"}]
                    ],
                    "period": 300,
                    "stat": "Average",
                    "region": region,
                    "dimensions": {
                        "FunctionName": f"finanza-realtime-dispatcher"
                    },
                    "yAxis": {"left": {"min": 0}}
                }
            },
            {
                "type": "metric",
                "x": 12,
                "y": 0,
                "width": 12,
                "height": 6,
                "properties": {
                    "title": "Lambda - Fraud Detector Performance",
                    "metrics": [
                        ["AWS/Lambda", "Invocations", {"stat": "Sum", "label": "Invocations"}],
                        [".", "Errors", {"stat": "Sum", "label": "Errors"}],
                        [".", "Duration", {"stat": "Average", "label": "Avg Duration (ms)"}],
                        [".", "ConcurrentExecutions", {"stat": "Maximum", "label": "Peak Concurrency"}]
                    ],
                    "period": 300,
                    "stat": "Average",
                    "region": region,
                    "dimensions": {
                        "FunctionName": "finanza-fraud-detector"
                    }
                }
            },
            {
                "type": "metric",
                "x": 0,
                "y": 6,
                "width": 12,
                "height": 6,
                "properties": {
                    "title": "Lambda - Settlement Processor",
                    "metrics": [
                        ["AWS/Lambda", "Invocations", {"stat": "Sum", "label": "Settlements"}],
                        [".", "Errors", {"stat": "Sum", "label": "Errors"}],
                        [".", "Duration", {"stat": "Average", "label": "Avg Duration (ms)"}]
                    ],
                    "period": 300,
                    "stat": "Average",
                    "region": region,
                    "dimensions": {
                        "FunctionName": "finanza-settlement-processor"
                    }
                }
            },
            {
                "type": "metric",
                "x": 12,
                "y": 6,
                "width": 12,
                "height": 6,
                "properties": {
                    "title": "SNS - Event Publishing",
                    "metrics": [
                        ["AWS/SNS", "Publish", {"stat": "Sum", "label": "Messages Sent"}],
                        [".", "PublishSize", {"stat": "Average", "label": "Avg Message Size (bytes)"}]
                    ],
                    "period": 300,
                    "stat": "Average",
                    "region": region
                }
            },
            {
                "type": "metric",
                "x": 0,
                "y": 12,
                "width": 12,
                "height": 6,
                "properties": {
                    "title": "RDS Database - Query Performance",
                    "metrics": [
                        ["AWS/RDS", "DatabaseConnections", {"stat": "Average"}],
                        [".", "CPUUtilization", {"stat": "Average"}],
                        [".", "DatabaseConnections", {"stat": "Maximum", "label": "Max Connections"}]
                    ],
                    "period": 300,
                    "stat": "Average",
                    "region": region,
                    "dimensions": {
                        "DBInstanceIdentifier": "database-1"
                    }
                }
            },
            {
                "type": "metric",
                "x": 12,
                "y": 12,
                "width": 12,
                "height": 6,
                "properties": {
                    "title": "RDS Database - Storage & Replication",
                    "metrics": [
                        ["AWS/RDS", "FreeStorageSpace", {"stat": "Average"}],
                        [".", "ReadLatency", {"stat": "Average"}],
                        [".", "WriteLatency", {"stat": "Average"}]
                    ],
                    "period": 60,
                    "stat": "Average",
                    "region": region,
                    "dimensions": {
                        "DBInstanceIdentifier": "database-1"
                    }
                }
            },
            {
                "type": "log",
                "x": 0,
                "y": 18,
                "width": 24,
                "height": 6,
                "properties": {
                    "title": "Application Errors (Last 1 Hour)",
                    "query": f"""
                    fields @timestamp, @message, @logStream
                    | filter @message like /ERROR/
                    | stats count() as error_count by @logStream
                    """,
                    "region": region,
                    "queryId": ""
                }
            },
            {
                "type": "metric",
                "x": 0,
                "y": 24,
                "width": 8,
                "height": 4,
                "properties": {
                    "title": "KYC Processing Success Rate",
                    "metrics": [
                        ["Finanza/RealTime", "KycApproved", {"stat": "Sum"}],
                        [".", "KycRejected", {"stat": "Sum"}]
                    ],
                    "period": 300,
                    "stat": "Sum",
                    "region": region,
                    "yAxis": {"left": {"min": 0}}
                }
            },
            {
                "type": "metric",
                "x": 8,
                "y": 24,
                "width": 8,
                "height": 4,
                "properties": {
                    "title": "Fraud Detection Metrics",
                    "metrics": [
                        ["Finanza/FraudDetector", "FraudCheckCompleted", {"stat": "Sum"}],
                        [".", "HighRiskDetected", {"stat": "Sum"}]
                    ],
                    "period": 300,
                    "stat": "Sum",
                    "region": region
                }
            },
            {
                "type": "metric",
                "x": 16,
                "y": 24,
                "width": 8,
                "height": 4,
                "properties": {
                    "title": "Settlement Processing",
                    "metrics": [
                        ["Finanza/Settlement", "SettlementCompleted", {"stat": "Sum"}],
                        [".", "SettlementFailed", {"stat": "Sum"}]
                    ],
                    "period": 300,
                    "stat": "Sum",
                    "region": region
                }
            }
        ]
    }
    
    try:
        response = cloudwatch.put_dashboard(
            DashboardName=dashboard_name,
            DashboardBody=json.dumps(dashboard_body)
        )
        print(f"✓ Dashboard created: {dashboard_name}")
        return response
    except Exception as e:
        print(f"✗ Failed to create dashboard: {e}")
        return None


def create_alarms(environment='dev', region='eu-north-1'):
    """Create CloudWatch alarms for critical metrics"""
    
    alarms = [
        {
            "AlarmName": f"finanza-kyc-dispatcher-errors-{environment}",
            "MetricName": "Errors",
            "Namespace": "AWS/Lambda",
            "Statistic": "Sum",
            "Period": 300,
            "EvaluationPeriods": 1,
            "Threshold": 5,
            "ComparisonOperator": "GreaterThanThreshold",
            "Dimensions": [{"Name": "FunctionName", "Value": "finanza-realtime-dispatcher"}],
            "TreatMissingData": "notBreaching"
        },
        {
            "AlarmName": f"finanza-kyc-dispatcher-throttles-{environment}",
            "MetricName": "Throttles",
            "Namespace": "AWS/Lambda",
            "Statistic": "Sum",
            "Period": 60,
            "EvaluationPeriods": 1,
            "Threshold": 1,
            "ComparisonOperator": "GreaterThanOrEqualToThreshold",
            "Dimensions": [{"Name": "FunctionName", "Value": "finanza-realtime-dispatcher"}],
            "TreatMissingData": "notBreaching"
        },
        {
            "AlarmName": f"finanza-kyc-dispatcher-duration-{environment}",
            "MetricName": "Duration",
            "Namespace": "AWS/Lambda",
            "Statistic": "Average",
            "Period": 300,
            "EvaluationPeriods": 2,
            "Threshold": 25000,  # 25 seconds (out of 30s timeout)
            "ComparisonOperator": "GreaterThanThreshold",
            "Dimensions": [{"Name": "FunctionName", "Value": "finanza-realtime-dispatcher"}],
            "TreatMissingData": "notBreaching"
        },
        {
            "AlarmName": f"finanza-rds-connections-{environment}",
            "MetricName": "DatabaseConnections",
            "Namespace": "AWS/RDS",
            "Statistic": "Average",
            "Period": 300,
            "EvaluationPeriods": 2,
            "Threshold": 80,  # 80% of max (max is usually 100)
            "ComparisonOperator": "GreaterThanThreshold",
            "Dimensions": [{"Name": "DBInstanceIdentifier", "Value": "database-1"}],
            "TreatMissingData": "notBreaching"
        },
        {
            "AlarmName": f"finanza-fraud-detector-errors-{environment}",
            "MetricName": "Errors",
            "Namespace": "AWS/Lambda",
            "Statistic": "Sum",
            "Period": 300,
            "EvaluationPeriods": 1,
            "Threshold": 3,
            "ComparisonOperator": "GreaterThanThreshold",
            "Dimensions": [{"Name": "FunctionName", "Value": "finanza-fraud-detector"}],
            "TreatMissingData": "notBreaching"
        },
        {
            "AlarmName": f"finanza-settlement-processor-errors-{environment}",
            "MetricName": "Errors",
            "Namespace": "AWS/Lambda",
            "Statistic": "Sum",
            "Period": 300,
            "EvaluationPeriods": 1,
            "Threshold": 3,
            "ComparisonOperator": "GreaterThanThreshold",
            "Dimensions": [{"Name": "FunctionName", "Value": "finanza-settlement-processor"}],
            "TreatMissingData": "notBreaching"
        }
    ]
    
    created_alarms = []
    for alarm_config in alarms:
        try:
            cloudwatch.put_metric_alarm(
                AlarmName=alarm_config["AlarmName"],
                MetricName=alarm_config["MetricName"],
                Namespace=alarm_config["Namespace"],
                Statistic=alarm_config["Statistic"],
                Period=alarm_config["Period"],
                EvaluationPeriods=alarm_config["EvaluationPeriods"],
                Threshold=alarm_config["Threshold"],
                ComparisonOperator=alarm_config["ComparisonOperator"],
                Dimensions=alarm_config["Dimensions"],
                TreatMissingData=alarm_config["TreatMissingData"],
                AlarmActions=[]  # Add SNS ARN for notifications
            )
            print(f"✓ Alarm created: {alarm_config['AlarmName']}")
            created_alarms.append(alarm_config["AlarmName"])
        except Exception as e:
            print(f"✗ Failed to create alarm {alarm_config['AlarmName']}: {e}")
    
    return created_alarms


def setup_log_insights_queries(environment='dev', region='eu-north-1'):
    """Print recommended CloudWatch Logs Insights queries"""
    
    queries = {
        "KYC Processing Errors (Last 24h)": """
            fields @timestamp, @message, @logStream
            | filter @message like /ERROR/ and @logStream like /kyc/
            | stats count() as error_count, max(@duration) as max_duration by @logStream
        """,
        
        "Lambda Performance Summary": """
            fields @duration, @initDuration, @memorySize, @maxMemoryUsed
            | stats avg(@duration) as avg_duration, max(@duration) as max_duration, 
                    pct(@duration, 99) as p99_duration, avg(@memoryUsed) as avg_memory
        """,
        
        "KYC Approval Rate": """
            fields @message
            | filter @message like /approved|rejected/
            | stats count() as total, 
                    sum(case when @message like /approved/ then 1 else 0 end) as approved,
                    sum(case when @message like /rejected/ then 1 else 0 end) as rejected
        """,
        
        "Fraud Detection Results": """
            fields @message, fraud_score, risk_level
            | filter @message like /HIGH|LOW/
            | stats count() as checks, 
                    sum(case when risk_level = 'HIGH' then 1 else 0 end) as high_risk,
                    avg(fraud_score) as avg_score
        """,
        
        "Settlement Processing Time": """
            fields @timestamp, @duration
            | filter @message like /settlement/
            | stats avg(@duration) as avg_settlement_time,
                    pct(@duration, 95) as p95_time,
                    max(@duration) as max_time
        """,
        
        "Database Connection Errors": """
            fields @message
            | filter @message like /FATAL|connection|timeout/
            | stats count() as error_count by @logStream
        """,
        
        "Average Response Time by Hour": """
            fields @timestamp, @duration
            | stats avg(@duration) as avg_duration by bin(5m)
        """
    }
    
    print("\n" + "="*70)
    print("RECOMMENDED CLOUDWATCH LOGS INSIGHTS QUERIES")
    print("="*70 + "\n")
    
    for query_name, query in queries.items():
        print(f"Query: {query_name}")
        print(f"Command:")
        print(f"  aws logs start-query \\")
        print(f"    --log-group-name /aws/lambda/finanza-realtime-dispatcher \\")
        print(f"    --start-time $(date -d '24 hours ago' +%s) \\")
        print(f"    --end-time $(date +%s) \\")
        print(f'    --query-string \'{query.strip()}\'')
        print()


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Setup CloudWatch monitoring for Finanza')
    parser.add_argument('--environment', default='dev', choices=['dev', 'staging', 'prod'])
    parser.add_argument('--region', default='eu-north-1')
    
    args = parser.parse_args()
    
    print("\n" + "="*70)
    print("CLOUDWATCH MONITORING SETUP")
    print("="*70 + "\n")
    
    print(f"Environment: {args.environment}")
    print(f"Region: {args.region}\n")
    
    # Create dashboard
    print("[1/3] Creating monitoring dashboard...")
    create_monitoring_dashboard(args.environment, args.region)
    
    # Create alarms
    print("\n[2/3] Creating CloudWatch alarms...")
    alarms = create_alarms(args.environment, args.region)
    print(f"  Created {len(alarms)} alarms")
    
    # Print Log Insights queries
    print("\n[3/3] CloudWatch Logs Insights queries...")
    setup_log_insights_queries(args.environment, args.region)
    
    print("\n" + "="*70)
    print("SETUP COMPLETE!")
    print("="*70)
    print("\nNext steps:")
    print("1. View dashboard: AWS Console → CloudWatch → Dashboards → finanza-realtime-{env}-dashboard")
    print("2. Subscribe to alarms: AWS Console → SNS → Subscriptions")
    print("3. Run test invocations to populate metrics")


if __name__ == '__main__':
    main()
