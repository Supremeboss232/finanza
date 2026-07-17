#!/usr/bin/env python
"""
Test script for admin dashboard endpoints
Tests authentication and data retrieval
"""

import requests
import json
import time
from datetime import datetime

BASE_URL = "http://localhost:8000"

def test_admin_endpoints():
    """Test admin endpoints"""
    
    print("=" * 80)
    print("ADMIN DASHBOARD ENDPOINT TESTS")
    print("=" * 80)
    print(f"Timestamp: {datetime.now()}")
    print(f"Base URL: {BASE_URL}\n")
    
    # Step 1: Check if server is running
    print("[1] Checking if server is running...")
    try:
        response = requests.get(f"{BASE_URL}/docs", timeout=2)
        if response.status_code == 200:
            print("✓ Server is running\n")
        else:
            print(f"✗ Server returned status {response.status_code}\n")
            return
    except requests.ConnectionError:
        print("✗ Cannot connect to server. Make sure it's running on port 8000\n")
        print("  Start with: python main.py\n")
        return
    
    # Step 2: Get authentication token
    print("[2] Testing authentication...")
    print("  Attempting login as admin...")
    
    login_response = requests.post(
        f"{BASE_URL}/auth/token",
        data={
            "username": "admin@admin.com",
            "password": "admin123"
        }
    )
    
    if login_response.status_code == 200:
        token_data = login_response.json()
        access_token = token_data.get('access_token')
        if access_token:
            print(f"✓ Login successful\n")
        else:
            print(f"✗ No token in response: {token_data}\n")
            return
    else:
        print(f"✗ Login failed with status {login_response.status_code}")
        print(f"  Response: {login_response.text}\n")
        return
    
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }
    
    # Step 3: Test endpoints
    endpoints = [
        ('/api/admin/metrics', 'Dashboard Metrics'),
        ('/api/admin/users?limit=5', 'Users List'),
        ('/api/admin/holds?limit=5', 'Account Holds'),
        ('/api/admin/accounts/frozen?limit=5', 'Frozen Accounts'),
        ('/api/admin/credit/scores?limit=5', 'Credit Scores'),
        ('/api/admin/devices/all?limit=5', 'Device Fingerprints'),
    ]
    
    print("[3] Testing Admin Endpoints...\n")
    
    for endpoint, name in endpoints:
        print(f"  Testing: {name}")
        print(f"  Endpoint: {endpoint}")
        
        try:
            response = requests.get(
                f"{BASE_URL}{endpoint}",
                headers=headers,
                timeout=5
            )
            
            print(f"  Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                
                # Show sample of response
                if isinstance(data, dict):
                    if 'data' in data:
                        count = len(data.get('data', []))
                        print(f"  ✓ Success - {count} items returned")
                    else:
                        keys = list(data.keys())[:5]
                        print(f"  ✓ Success - Fields: {', '.join(keys)}")
                        if 'total_users' in data:
                            print(f"    - total_users: {data.get('total_users')}")
                        if 'active_users' in data:
                            print(f"    - active_users: {data.get('active_users')}")
                        if 'kyc_verified' in data:
                            print(f"    - kyc_verified: {data.get('kyc_verified')}")
                        if 'account_holds' in data:
                            print(f"    - account_holds: {data.get('account_holds')}")
                else:
                    print(f"  ✓ Success - Data type: {type(data).__name__}")
                    
            elif response.status_code == 401:
                print(f"  ✗ Unauthorized (401) - Check authentication token")
            elif response.status_code == 403:
                print(f"  ✗ Forbidden (403) - User is not admin")
            else:
                print(f"  ✗ Error: {response.text[:100]}")
                
        except requests.Timeout:
            print(f"  ✗ Timeout - Server took too long to respond")
        except requests.ConnectionError:
            print(f"  ✗ Connection error")
        except Exception as e:
            print(f"  ✗ Error: {str(e)}")
        
        print()
    
    print("=" * 80)
    print("TEST COMPLETE")
    print("=" * 80)
    print("\nIf all endpoints returned 200, the admin dashboard should work!")
    print("\nIf you see 401 or 403 errors:")
    print("  1. Check if authentication is working")
    print("  2. Verify the admin user exists in the database")
    print("  3. Try logging in through /signin in your browser\n")

if __name__ == '__main__':
    test_admin_endpoints()
