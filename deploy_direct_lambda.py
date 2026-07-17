#!/usr/bin/env python3
"""
Direct Lambda Deployment Script (No SAM Required)

Deploys Lambda functions directly to AWS without SAM:
1. Packages Python code + dependencies
2. Creates Lambda functions
3. Configures IAM roles
4. Sets environment variables
5. Wires up EventBridge/SNS

Fast alternative to SAM when CLI is unavailable
"""

import json
import subprocess
import boto3
import zipfile
import os
from pathlib import Path

class DirectLambdaDeployer:
    def __init__(self, environment='dev', region='eu-north-1', account_id=None):
        self.environment = environment
        self.region = region
        self.lambda_client = boto3.client('lambda', region_name=region)
        self.iam_client = boto3.client('iam')
        self.sns_client = boto3.client('sns', region_name=region)
        self.account_id = account_id or self._get_account_id()
        
    def _get_account_id(self):
        """Get AWS account ID"""
        try:
            sts = boto3.client('sts')
            return sts.get_caller_identity()['Account']
        except Exception as e:
            print(f"Error getting account ID: {e}")
            return None
    
    def create_deployment_package(self, handler_file, requirements_file=None):
        """Package Lambda code with dependencies"""
        print(f"📦 Creating deployment package from {handler_file}...")
        
        # Create temp directory
        package_dir = Path('lambda_package')
        package_dir.mkdir(exist_ok=True)
        
        # Copy handler
        handler_name = Path(handler_file).stem
        copy_cmd = f'copy {handler_file} {package_dir}\\lambda_function.py'
        subprocess.run(copy_cmd, shell=True, capture_output=True)
        
        # Install dependencies if requirements exists
        if requirements_file and os.path.exists(requirements_file):
            pip_cmd = f'pip install -r {requirements_file} -t {package_dir} --quiet'
            print("  Installing dependencies...")
            subprocess.run(pip_cmd, shell=True, capture_output=True)
        
        # Create ZIP
        zip_path = f'{handler_name}.zip'
        print(f"  Zipping to {zip_path}...")
        
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            for root, dirs, files in os.walk(package_dir):
                for file in files:
                    file_path = Path(root) / file
                    arcname = file_path.relative_to(package_dir)
                    zf.write(file_path, arcname)
        
        print(f"✓ Package ready: {zip_path}")
        return zip_path
    
    def create_iam_role(self, role_name):
        """Create IAM role for Lambda"""
        print(f"🔐 Creating IAM role: {role_name}...")
        
        trust_policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": {"Service": "lambda.amazonaws.com"},
                    "Action": "sts:AssumeRole"
                }
            ]
        }
        
        try:
            response = self.iam_client.create_role(
                RoleName=role_name,
                AssumeRolePolicyDocument=json.dumps(trust_policy),
                Description=f'Lambda execution role for {role_name}'
            )
            role_arn = response['Role']['Arn']
            print(f"✓ Role created: {role_arn}")
            
            # Attach basic permissions
            self.iam_client.attach_role_policy(
                RoleName=role_name,
                PolicyArn='arn:aws:iam::aws:policy/service-role/AWSLambdaVPCAccessExecutionRole'
            )
            
            return role_arn
        except self.iam_client.exceptions.EntityAlreadyExistsException:
            print(f"✓ Role already exists: {role_name}")
            response = self.iam_client.get_role(RoleName=role_name)
            return response['Role']['Arn']
        except Exception as e:
            print(f"✗ Error creating role: {e}")
            return None
    
    def deploy_lambda(self, function_config):
        """Deploy Lambda function"""
        name = function_config['name']
        zip_path = function_config['zip']
        handler = function_config.get('handler', 'lambda_function.lambda_handler')
        role_arn = function_config.get('role_arn')
        env_vars = function_config.get('env_vars', {})
        vpc_config = function_config.get('vpc_config', {})
        
        print(f"\n🚀 Deploying Lambda: {name}...")
        
        # Read ZIP
        with open(zip_path, 'rb') as f:
            zip_content = f.read()
        
        try:
            # Check if function exists
            try:
                self.lambda_client.get_function(FunctionName=name)
                
                # Update existing function
                print(f"  Updating existing function...")
                response = self.lambda_client.update_function_code(
                    FunctionName=name,
                    ZipFile=zip_content
                )
                
                # Update configuration
                self.lambda_client.update_function_configuration(
                    FunctionName=name,
                    Handler=handler,
                    Runtime='python3.12',
                    Timeout=30,
                    MemorySize=512,
                    Environment={'Variables': env_vars},
                    VpcConfig=vpc_config if vpc_config else {'SecurityGroupIds': [], 'SubnetIds': []},
                    TracingConfig={'Mode': 'Active'}
                )
                
                print(f"✓ Function updated: {name}")
                
            except self.lambda_client.exceptions.ResourceNotFoundException:
                # Create new function
                print(f"  Creating new function...")
                response = self.lambda_client.create_function(
                    FunctionName=name,
                    Runtime='python3.12',
                    Role=role_arn,
                    Handler=handler,
                    Code={'ZipFile': zip_content},
                    Description=f'Finanza {name}',
                    Timeout=30,
                    MemorySize=512,
                    Environment={'Variables': env_vars},
                    Tracing='Active',
                    Tags={'Environment': self.environment}
                )
                
                if vpc_config:
                    self.lambda_client.update_function_configuration(
                        FunctionName=name,
                        VpcConfig=vpc_config
                    )
                
                print(f"✓ Function created: {name}")
            
            return response['FunctionArn']
            
        except Exception as e:
            print(f"✗ Deployment failed: {e}")
            return None
    
    def deploy_all(self):
        """Deploy all Lambda functions"""
        print("\n" + "="*70)
        print("FINANZA REALTIME SERVICES - DIRECT LAMBDA DEPLOYMENT")
        print("="*70 + "\n")
        
        # Create IAM role
        role_name = f'finanza-lambda-role-{self.environment}'
        role_arn = self.create_iam_role(role_name)
        
        if not role_arn:
            print("✗ Failed to create IAM role. Aborting.")
            return False
        
        # Deploy KYC Dispatcher
        print("\n[1/3] KYC Dispatcher Lambda")
        kyc_zip = self.create_deployment_package(
            'src/lambda_kyc_dispatcher.py',
            'src/requirements.txt'
        )
        
        kyc_arn = self.deploy_lambda({
            'name': 'finanza-realtime-dispatcher',
            'zip': kyc_zip,
            'role_arn': role_arn,
            'handler': 'lambda_kyc_dispatcher.lambda_handler',
            'env_vars': {
                'RDS_HOST': 'database-1.cf2w2gwcmvc8.eu-north-1.rds.amazonaws.com',
                'RDS_USER': 'postgres',
                'LAMBDA_FRAUD_DETECTOR': 'finanza-fraud-detector',
                'SNS_TOPIC_ARN': f'arn:aws:sns:{self.region}:{self.account_id}:finanza-kyc-events'
            }
        })
        
        if not kyc_arn:
            print("✗ KYC Dispatcher deployment failed")
            return False
        
        # Deploy Fraud Detector
        print("\n[2/3] Fraud Detector Lambda")
        fraud_zip = self.create_deployment_package(
            'src/lambda_fraud_detector.py',
            'src/requirements.txt'
        )
        
        fraud_arn = self.deploy_lambda({
            'name': 'finanza-fraud-detector',
            'zip': fraud_zip,
            'role_arn': role_arn,
            'handler': 'lambda_fraud_detector.lambda_handler',
            'env_vars': {
                'RDS_HOST': 'database-1.cf2w2gwcmvc8.eu-north-1.rds.amazonaws.com',
                'RDS_USER': 'postgres',
                'FRAUD_SCORE_THRESHOLD': '0.7'
            }
        })
        
        # Deploy Settlement Processor
        print("\n[3/3] Settlement Processor Lambda")
        settlement_zip = self.create_deployment_package(
            'src/lambda_settlement_processor.py',
            'src/requirements.txt'
        )
        
        settlement_arn = self.deploy_lambda({
            'name': 'finanza-settlement-processor',
            'zip': settlement_zip,
            'role_arn': role_arn,
            'handler': 'lambda_settlement_processor.lambda_handler',
            'env_vars': {
                'RDS_HOST': 'database-1.cf2w2gwcmvc8.eu-north-1.rds.amazonaws.com',
                'RDS_USER': 'postgres',
                'SETTLEMENT_TIMEOUT_HOURS': '24'
            }
        })
        
        print("\n" + "="*70)
        print("✓ DEPLOYMENT COMPLETE!")
        print("="*70)
        print(f"\nLambda Functions Deployed:")
        print(f"  1. KYC Dispatcher: {kyc_arn}")
        print(f"  2. Fraud Detector: {fraud_arn}")
        print(f"  3. Settlement Processor: {settlement_arn}")
        print(f"\nRole: {role_arn}")
        print("\nNext Steps:")
        print("1. Update RDS Secrets Manager with password")
        print("2. Create SNS topics and subscriptions")
        print("3. Configure EventBridge rules")
        print("4. Setup monitoring dashboard")
        print("="*70 + "\n")
        
        return True


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Deploy Lambda functions directly to AWS')
    parser.add_argument('--environment', default='dev', choices=['dev', 'staging', 'prod'])
    parser.add_argument('--region', default='eu-north-1')
    
    args = parser.parse_args()
    
    deployer = DirectLambdaDeployer(args.environment, args.region)
    success = deployer.deploy_all()
    
    import sys
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
