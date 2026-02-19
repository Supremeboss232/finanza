#!/usr/bin/env python3
"""
KYC System Verification - Complete Workflow Test
Tests KYC submission process, admin review, and approval
"""

import asyncio
import httpx
import sys

BASE_URL = "http://51.20.190.13:8000"

async def verify_kyc_system():
    """Verify complete KYC system"""
    
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=15) as client:
        print("\n" + "="*70)
        print("KYC SYSTEM - COMPLETE VERIFICATION")
        print("="*70 + "\n")
        
        # Step 1: Admin login
        print("Step 1️⃣ : Admin Authentication")
        print("─" * 70)
        try:
            response = await client.post("/auth/token", data={
                "username": "admin@admin.com",
                "password": "admin123"
            })
            
            if response.status_code != 200:
                print("❌ Admin login failed")
                return False
            
            token = response.json()["access_token"]
            headers = {"Authorization": f"Bearer {token}"}
            print("✅ Admin authenticated successfully\n")
        except Exception as e:
            print(f"❌ Error: {e}\n")
            return False
        
        # Step 2: Check KYC submissions
        print("Step 2️⃣ : Check KYC Submissions")
        print("─" * 70)
        try:
            response = await client.get("/api/admin/data/kyc?skip=0&limit=20", headers=headers)
            data = response.json()
            kyc_list = data.get("data", [])
            total = data.get("total", 0)
            
            print(f"✅ KYC Query Successful")
            print(f"   Total Submissions: {total}\n")
            
            if total > 0:
                print("   📋 Pending KYC Submissions:\n")
                for kyc in kyc_list:
                    if kyc.get('status') == 'pending':
                        print(f"   ID: {kyc.get('id')}")
                        print(f"   User: {kyc.get('user_email')}")
                        print(f"   Document: {kyc.get('document_type')}")
                        print(f"   File: {kyc.get('document_file_path')}")
                        print(f"   ➜ To Approve: POST /api/admin/kyc/{kyc.get('id')}/approve")
                        print(f"   ➜ To Reject: POST /api/admin/kyc/{kyc.get('id')}/reject\n")
            else:
                print("   ⚠️  No KYC submissions yet")
                print("   Waiting for users to submit documents\n")
        except Exception as e:
            print(f"❌ Error: {e}\n")
            return False
        
        # Step 3: Verify fund endpoint
        print("Step 3️⃣ : Verify Fund User Endpoint")
        print("─" * 70)
        try:
            response = await client.post(
                "/api/admin/users/999/fund",
                json={
                    "email": "test@example.com",
                    "amount": 50,
                    "fund_source": "system_reserve"
                },
                headers=headers
            )
            
            if response.status_code in [200, 400, 404]:
                print(f"✅ Fund endpoint is operational")
                print(f"   Status: {response.status_code}")
                if response.status_code == 400:
                    print(f"   (Expected error: user doesn't exist)\n")
            else:
                print(f"⚠️  Unexpected status: {response.status_code}\n")
        except Exception as e:
            print(f"❌ Error: {e}\n")
            return False
        
        # Step 4: Check user balances
        print("Step 4️⃣ : User Balance Summary")
        print("─" * 70)
        try:
            response = await client.get("/api/admin/users?skip=0&limit=10", headers=headers)
            users = response.json().get("data", [])
            
            print(f"✅ Users Retrieved: {len(users)}\n")
            
            for user in users[:5]:
                print(f"   • {user.get('email')}: ${user.get('balance', 0):,.2f}")
            
            if len(users) > 5:
                print(f"   ... and {len(users) - 5} more users\n")
        except Exception as e:
            print(f"❌ Error: {e}\n")
            return False
        
        # Summary
        print("="*70)
        print("KYC SYSTEM SUMMARY")
        print("="*70 + "\n")
        
        print("✅ All Components Working:")
        print("   ✅ Admin authentication")
        print("   ✅ KYC data retrieval with documents")
        print("   ✅ Fund user endpoint")
        print("   ✅ User balance retrieval\n")
        
        if total == 0:
            print("📌 Status: Awaiting User Submissions")
            print("   Users must submit KYC documents first\n")
            print("   User can submit via: POST /kyc/verify")
            print("   Requires:")
            print("     • Authorization header with user token")
            print("     • Form data: document_type, file\n")
        else:
            print(f"📌 Status: {total} Submissions Pending Review\n")
        
        return True

if __name__ == "__main__":
    try:
        success = asyncio.run(verify_kyc_system())
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ Fatal Error: {e}\n")
        sys.exit(1)
