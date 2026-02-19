#!/usr/bin/env python3
"""
Check KYC Documents in Database
Queries the database to see:
1. How many KYC submissions exist
2. What documents are there
3. Whether document_file_path is populated
"""

import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select, text
import sys

# Database URL (matches main config)
DATABASE_URL = "postgresql+asyncpg://finbank:Supposedbe5@localhost:5432/finanza_bank"

async def check_kyc_documents():
    """Check KYC documents in database"""
    
    # Create engine
    engine = create_async_engine(DATABASE_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    try:
        print("\n" + "="*70)
        print("KYC DOCUMENTS CHECK")
        print("="*70 + "\n")
        
        async with async_session() as db:
            # Check 1: Count total KYC submissions
            print("1️⃣  Counting total KYC submissions...")
            result = await db.execute(text("SELECT COUNT(*) FROM kyc_submissions"))
            total_kyc = result.scalar()
            print(f"   Total KYC submissions: {total_kyc}\n")
            
            # Check 2: List all KYC submissions with details
            if total_kyc > 0:
                print("2️⃣  Listing KYC submissions:")
                result = await db.execute(text("""
                    SELECT 
                        id, 
                        user_id, 
                        document_type, 
                        status, 
                        document_file_path,
                        submitted_at,
                        reviewed_at
                    FROM kyc_submissions
                    ORDER BY submitted_at DESC
                    LIMIT 20
                """))
                
                rows = result.fetchall()
                for row in rows:
                    kyc_id, user_id, doc_type, status, doc_path, submitted, reviewed = row
                    print(f"\n   KYC #{kyc_id}:")
                    print(f"     - User ID: {user_id}")
                    print(f"     - Document Type: {doc_type}")
                    print(f"     - Status: {status}")
                    print(f"     - Document Path: {doc_path if doc_path else '(None/Empty)'}")
                    print(f"     - Submitted: {submitted}")
                    print(f"     - Reviewed: {reviewed}")
                
                # Check 3: Count documents with file paths
                print("\n\n3️⃣  Document Status Summary:")
                result = await db.execute(text("""
                    SELECT 
                        status,
                        COUNT(*) as count,
                        SUM(CASE WHEN document_file_path IS NOT NULL THEN 1 ELSE 0 END) as with_documents
                    FROM kyc_submissions
                    GROUP BY status
                """))
                
                summary = result.fetchall()
                for status, count, with_docs in summary:
                    without_docs = count - (with_docs or 0)
                    print(f"\n   Status: {status}")
                    print(f"     - Total: {count}")
                    print(f"     - With documents: {with_docs or 0}")
                    print(f"     - Without documents: {without_docs}")
                
                # Check 4: Verify document storage
                print("\n\n4️⃣  Document Storage Check:")
                result = await db.execute(text("""
                    SELECT 
                        COUNT(*) as total,
                        COUNT(CASE WHEN document_file_path IS NOT NULL THEN 1 END) as has_path,
                        COUNT(CASE WHEN document_file_path = '' THEN 1 END) as empty_path
                    FROM kyc_submissions
                """))
                
                total, has_path, empty_path = result.fetchone()
                print(f"   - Total KYC records: {total}")
                print(f"   - With file path: {has_path}")
                print(f"   - Empty path: {empty_path}")
                
                # Check 5: User information for KYC
                print("\n\n5️⃣  KYC Submissions by User:")
                result = await db.execute(text("""
                    SELECT 
                        k.user_id,
                        u.email,
                        COUNT(*) as submission_count,
                        MAX(k.submitted_at) as latest_submission,
                        MAX(CASE WHEN document_file_path IS NOT NULL THEN 1 ELSE 0 END) as has_documents
                    FROM kyc_submissions k
                    LEFT JOIN "user" u ON k.user_id = u.id
                    GROUP BY k.user_id, u.email
                    ORDER BY latest_submission DESC
                    LIMIT 10
                """))
                
                user_kyc = result.fetchall()
                for user_id, email, count, latest, has_docs in user_kyc:
                    print(f"\n   User: {email} (ID: {user_id})")
                    print(f"     - Submissions: {count}")
                    print(f"     - Latest: {latest}")
                    print(f"     - Has documents: {'Yes' if has_docs else 'No'}")
                
            else:
                print("   ❌ No KYC submissions found in database!\n")
                print("   This means:")
                print("     - Users haven't submitted KYC documents yet, OR")
                print("     - KYC table is empty\n")
                print("   Next steps:")
                print("     1. Have users submit KYC documents via the application")
                print("     2. Check if KYC submission endpoint is working")
                print("     3. Verify document upload is functioning\n")
            
        print("\n" + "="*70)
        print("END OF REPORT")
        print("="*70 + "\n")
        
    except Exception as e:
        print(f"\n❌ Database Error: {str(e)}\n")
        print("Troubleshooting:")
        print("  - Is SSH tunnel open? (port 5432 should be listening)")
        print("  - Are credentials correct? (finbank:Supposedbe5)")
        print("  - Database URL: postgresql+asyncpg://finbank:Supposedbe5@localhost:5432/finanza_bank\n")
        return False
    finally:
        await engine.dispose()
    
    return True

if __name__ == "__main__":
    try:
        success = asyncio.run(check_kyc_documents())
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ Error: {e}\n")
        sys.exit(1)
