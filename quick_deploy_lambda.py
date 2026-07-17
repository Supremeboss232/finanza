#!/usr/bin/env python3
"""
Quick Lambda Deployment via AWS CLI
Deploys all three Lambda functions to AWS
"""

import subprocess
import json
import sys
import os

def deploy_lambda(function_name, handler_path, region='eu-north-1'):
    """Deploy a single Lambda function"""
    print(f"\n{'='*70}")
    print(f"Deploying: {function_name}")
    print(f"{'='*70}")
    
    # Read the handler file
    try:
        with open(handler_path, 'r') as f:
            code = f.read()
    except FileNotFoundError:
        print(f"✗ Handler not found: {handler_path}")
        return False
    
    # For simplicity, we'll use a basic deployment
    # In production, you'd zip the code with dependencies
    
    # Create a simple zip with just the handler
    import zipfile
    import tempfile
    
    with tempfile.NamedTemporaryFile(suffix='.zip', delete=False) as tmp:
        with zipfile.ZipFile(tmp.name, 'w') as zf:
            # Add handler
            handler_filename = os.path.basename(handler_path)
            zf.writestr(handler_filename, code)
            
            # Add dependencies if available
            if os.path.exists('src/requirements.txt'):
                with open('src/requirements.txt', 'r') as req_file:
                    zf.writestr('requirements.txt', req_file.read())
        
        zip_path = tmp.name
    
    # Upload to Lambda
    cmd = [
        'aws', 'lambda', 'update-function-code',
        '--function-name', function_name,
        '--zip-file', f'fileb://{zip_path}',
        '--region', region
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✓ {function_name} deployed successfully!")
            response = json.loads(result.stdout)
            print(f"  CodeSha256: {response.get('CodeSha256', 'N/A')}")
            os.unlink(zip_path)
            return True
        else:
            print(f"✗ Deployment failed: {result.stderr}")
            os.unlink(zip_path)
            return False
    except Exception as e:
        print(f"✗ Exception: {e}")
        os.unlink(zip_path)
        return False


def main():
    print("\n" + "="*70)
    print("FINANZA LAMBDA DEPLOYMENT")
    print("="*70)
    
    functions = [
        ('finanza-realtime-dispatcher', 'src/lambda_kyc_dispatcher.py'),
        # ('finanza-fraud-detector', 'src/lambda_fraud_detector.py'),
        # ('finanza-settlement-processor', 'src/lambda_settlement_processor.py'),
    ]
    
    region = 'eu-north-1'
    deployed = 0
    failed = 0
    
    for func_name, handler_path in functions:
        if deploy_lambda(func_name, handler_path, region):
            deployed += 1
        else:
            failed += 1
    
    print("\n" + "="*70)
    print(f"RESULTS: {deployed} deployed, {failed} failed")
    print("="*70 + "\n")
    
    return 0 if failed == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
