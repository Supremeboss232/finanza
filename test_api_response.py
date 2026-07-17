#!/usr/bin/env python3
import asyncio
import sys
import json
sys.path.insert(0, 'C:\\Users\\Aweh\\Downloads\\supreme\\financial-services-website-template')

from admin_management_service import AdminManagementService
from database import SessionLocal

async def test_get_admins():
    """Test what get_all_admins returns"""
    async with SessionLocal() as session:
        admins = await AdminManagementService.get_all_admins(session)
        print(f"Returned admins: {len(admins)}")
        print(json.dumps(admins, indent=2, default=str))

if __name__ == "__main__":
    asyncio.run(test_get_admins())
