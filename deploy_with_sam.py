#!/usr/bin/env python3
"""
SAM Deployment Automation Script for Finanza Real-Time Services

Automates the complete deployment of:
- KYC Dispatcher Lambda
- Fraud Detector Lambda
- Settlement Processor Lambda
- SNS Topics
- EventBridge Rules
- CloudWatch Alarms
- Monitoring Dashboard
"""

import subprocess
import sys
import json
import time
from datetime import datetime

class SAMDeployer:
    def __init__(self, environment='dev', region='eu-north-1', profile=None):
        self.environment = environment
        self.region = region
        self.profile = profile
        self.aws_cmd_prefix = ['aws'] if not profile else ['aws', '--profile', profile]
        self.stack_name = f'finanza-realtime-{environment}'
        self.template = 'sam-template-optimized.yaml'
        
    def print_step(self, step_num, title):
        print(f"\n{'='*70}")
        print(f"STEP {step_num}: {title}")
        print(f"{'='*70}\n")
    
    def run_command(self, cmd, description):
        """Run a shell command and handle output"""
        print(f"→ {description}...")
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, shell=False)
            if result.returncode == 0:
                print(f"✓ {description} succeeded")
                return result.stdout.strip()
            else:
                print(f"✗ {description} failed")
                print(f"Error: {result.stderr}")
                return None
        except Exception as e:
            print(f"✗ Exception: {e}")
            return None
    
    def validate_template(self):
        """Validate SAM template"""
        self.print_step(1, "Validate SAM Template")
        
        cmd = self.aws_cmd_prefix + [
            'cloudformation', 'validate-template',
            '--template-body', f'file://{self.template}',
            '--region', self.region
        ]
        
        output = self.run_command(cmd, "Validating SAM template")
        if output:
            print("Template validation successful!")
            return True
        return False
    
    def build_template(self):
        """Build SAM application"""
        self.print_step(2, "Build SAM Application")
        
        cmd = ['sam', 'build', '--template', self.template]
        
        output = self.run_command(cmd, "Building SAM application")
        if output:
            print("Build complete!")
            return True
        return False
    
    def create_s3_bucket(self):
        """Create S3 bucket for SAM artifacts"""
        self.print_step(3, "Create S3 Bucket for Deployment Artifacts")
        
        bucket_name = f'finanza-sam-artifacts-{self.environment}-{int(time.time())}'
        
        cmd = self.aws_cmd_prefix + [
            's3', 'mb', f's3://{bucket_name}',
            '--region', self.region
        ]
        
        output = self.run_command(cmd, f"Creating S3 bucket: {bucket_name}")
        if output or "BucketAlreadyExists" in str(output):
            print(f"Using bucket: {bucket_name}")
            return bucket_name
        return None
    
    def package_template(self, s3_bucket):
        """Package SAM template"""
        self.print_step(4, "Package SAM Template")
        
        output_template = 'packaged.yaml'
        cmd = ['sam', 'package',
               '--template-file', '.aws-sam/build/template.yaml',
               '--s3-bucket', s3_bucket,
               '--output-template-file', output_template,
               '--region', self.region
        ]
        
        output = self.run_command(cmd, "Packaging SAM template")
        if output:
            print(f"Template packaged to: {output_template}")
            return output_template
        return None
    
    def deploy_template(self, packaged_template):
        """Deploy SAM template"""
        self.print_step(5, "Deploy SAM Stack")
        
        cmd = ['sam', 'deploy',
               '--template-file', packaged_template,
               '--stack-name', self.stack_name,
               '--parameter-overrides',
               f'Environment={self.environment}',
               '--capabilities', 'CAPABILITY_IAM', 'CAPABILITY_NAMED_IAM',
               '--region', self.region,
               '--no-confirm-changeset'
        ]
        
        output = self.run_command(cmd, f"Deploying stack: {self.stack_name}")
        if output:
            print("Deployment complete!")
            return True
        return False
    
    def get_stack_outputs(self):
        """Get CloudFormation stack outputs"""
        self.print_step(6, "Retrieve Stack Outputs")
        
        cmd = self.aws_cmd_prefix + [
            'cloudformation', 'describe-stacks',
            '--stack-name', self.stack_name,
            '--region', self.region,
            '--query', 'Stacks[0].Outputs',
            '--output', 'json'
        ]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, shell=False)
            if result.returncode == 0:
                outputs = json.loads(result.stdout)
                print("\nStack Outputs:")
                print("-" * 70)
                for output in outputs:
                    key = output.get('OutputKey', 'N/A')
                    value = output.get('OutputValue', 'N/A')
                    print(f"{key:30} {value}")
                print("-" * 70)
                return outputs
        except Exception as e:
            print(f"Error retrieving outputs: {e}")
        
        return None
    
    def setup_monitoring(self):
        """Setup monitoring dashboard and alarms"""
        self.print_step(7, "Setup Monitoring Dashboard")
        
        cmd = ['python', 'setup_monitoring_dashboard.py',
               '--environment', self.environment,
               '--region', self.region
        ]
        
        output = self.run_command(cmd, "Creating monitoring dashboard")
        if output:
            print("Monitoring setup complete!")
            return True
        return False
    
    def run_health_check(self):
        """Run Lambda health check"""
        self.print_step(8, "Run Lambda Health Check")
        
        function_name = 'finanza-realtime-dispatcher'
        cmd = ['python', 'health_check_lambda.py',
               '--function', function_name,
               '--region', self.region
        ]
        
        output = self.run_command(cmd, "Running health check")
        if output:
            print("Health check complete!")
            return True
        return False
    
    def deploy(self):
        """Run full deployment pipeline"""
        print("\n" + "="*70)
        print("FINANZA REALTIME SERVICES - SAM DEPLOYMENT")
        print("="*70)
        print(f"Environment: {self.environment}")
        print(f"Region: {self.region}")
        print(f"Stack: {self.stack_name}")
        print("="*70)
        
        # Step 1: Validate
        if not self.validate_template():
            print("\n✗ Template validation failed. Aborting.")
            return False
        
        # Step 2: Build
        if not self.build_template():
            print("\n✗ Build failed. Aborting.")
            return False
        
        # Step 3: Create S3 bucket
        s3_bucket = self.create_s3_bucket()
        if not s3_bucket:
            print("\n✗ S3 bucket creation failed. Aborting.")
            return False
        
        # Step 4: Package
        packaged_template = self.package_template(s3_bucket)
        if not packaged_template:
            print("\n✗ Packaging failed. Aborting.")
            return False
        
        # Step 5: Deploy
        if not self.deploy_template(packaged_template):
            print("\n✗ Deployment failed. Aborting.")
            return False
        
        # Step 6: Get outputs
        outputs = self.get_stack_outputs()
        
        # Step 7: Setup monitoring
        self.setup_monitoring()
        
        # Step 8: Health check
        self.run_health_check()
        
        # Summary
        print("\n" + "="*70)
        print("DEPLOYMENT COMPLETE!")
        print("="*70)
        print("\nNext Steps:")
        print("1. Configure EventBridge rules for KYC providers")
        print("2. Setup SNS subscriptions for alerts")
        print("3. Configure payment provider webhooks")
        print("4. Run end-to-end tests")
        print("\nMonitoring:")
        print("- CloudWatch Dashboard: finanza-realtime-{}-dashboard".format(self.environment))
        print("- Lambda Logs: /aws/lambda/finanza-realtime-dispatcher")
        print("- X-Ray Service Map: AWS Console → X-Ray → Service Map")
        print("="*70 + "\n")
        
        return True


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Deploy Finanza Real-Time Services with SAM')
    parser.add_argument('--environment', default='dev', choices=['dev', 'staging', 'prod'],
                       help='Deployment environment')
    parser.add_argument('--region', default='eu-north-1',
                       help='AWS region')
    parser.add_argument('--profile', default=None,
                       help='AWS CLI profile (optional)')
    parser.add_argument('--skip-health-check', action='store_true',
                       help='Skip health check after deployment')
    parser.add_argument('--skip-monitoring', action='store_true',
                       help='Skip monitoring setup')
    
    args = parser.parse_args()
    
    deployer = SAMDeployer(
        environment=args.environment,
        region=args.region,
        profile=args.profile
    )
    
    # Conditionally skip steps
    if args.skip_monitoring:
        deployer.setup_monitoring = lambda: True
    if args.skip_health_check:
        deployer.run_health_check = lambda: True
    
    success = deployer.deploy()
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
