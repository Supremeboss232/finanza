# 🔧 DEBUGGING & TROUBLESHOOTING GUIDE

**Purpose**: Diagnose problems encountered during implementation  
**Usage**: Search for your error, follow the diagnosis steps, apply the fix

---

## SECTION 1: INSTALLATION & DEPENDENCY ISSUES

### Problem: "ModuleNotFoundError: No module named 'boto3'"

**Diagnosis:**
```bash
python -c "import boto3"
# Error: ModuleNotFoundError
```

**Cause**: boto3 not installed or wrong environment

**Fix**:
```bash
# Method 1: Install directly
pip install boto3==1.28.85

# Method 2: Install from requirements
pip install -r requirements.txt --upgrade

# Method 3: Check environment
python -c "import sys; print(sys.prefix)"
# Should show your virtual environment path

# Verify
pip list | grep boto3
# Should show: boto3  1.28.85
```

---

### Problem: "Requirement already satisfied, but version conflicts"

**Diagnosis:**
```bash
pip install -r requirements.txt
# ERROR: pip's dependency resolver does not currently take into account all the packages
```

**Cause**: Version conflicts between packages

**Fix**:
```bash
# Method 1: Clean install
pip uninstall -y fastapi uvicorn sqlalchemy asyncpg
pip install -r requirements.txt

# Method 2: Use specific versions
pip install fastapi==0.104.1 uvicorn==0.24.0 sqlalchemy==2.0.23

# Method 3: Check compatibility
pip check
# Lists any version conflicts
```

---

### Problem: "psycopg2 import fails" or "asyncpg connection errors"

**Diagnosis:**
```bash
python -c "import asyncpg"
# ModuleNotFoundError or build error

python -c "import psycopg2"  
# Error: psycopg2 is not installed
```

**Cause**: PostgreSQL development libraries missing (Windows-specific)

**Fix**:
```bash
# Windows: Install via pre-compiled wheels
pip install asyncpg --only-binary :all:

# Verify PostgreSQL libs available
psql --version
# Should show PostgreSQL version

# If missing, download from postgresql.org
```

---

## SECTION 2: DATABASE CONNECTION ISSUES

### Problem: "Can't connect to database - connection refused"

**Diagnosis**:
```bash
# Check if database running
python ./check_db.py
# Error: Failed to connect to finanza.db
```

**Cause**: Database service not running or wrong connection string

**Fix**:
```bash
# Method 1: Check database status
psql -U postgres -h localhost
# If fails, database not running

# Method 2: Verify connection string in config.py
# Should show: postgresql+asyncpg://user:pass@host/db

# Method 3: Try direct connection
python -c "
import asyncpg
import asyncio

async def test():
    try:
        conn = await asyncpg.connect('postgresql://localhost/finanza')
        print('✓ Connected')
    except Exception as e:
        print(f'✗ Error: {e}')

asyncio.run(test())
"

# Method 4: Test with sqlite (fallback)
# Change DATABASE_URL to: sqlite:///finanza.db
```

---

### Problem: "SSL certificate verify failed"

**Diagnosis**:
```bash
# App startup shows:
# ssl.SSLError: _ssl.c:1129: CERTIFICATE_VERIFY_FAILED
```

**Cause**: SSL verification enabled but certificates invalid

**Fix in config.py**:
```python
# Change from:
DATABASE_URL = "postgresql+asyncpg://user:pass@host/db?ssl=require"

# To:
DATABASE_URL = "postgresql+asyncpg://user:pass@host/db?ssl=prefer"
# or
DATABASE_URL = "postgresql+asyncpg://user:pass@host/db?ssl=disable"
```

---

### Problem: "Alembic migration fails"

**Diagnosis**:
```bash
alembic upgrade head
# Error: Target database is not up to date...
```

**Cause**: Migration issues from previous changes

**Fix**:
```bash
# Method 1: Reset migrations (DEV ONLY!)
rm -rf alembic/versions/*.py
alembic revision --autogenerate -m "Initial"
alembic upgrade head

# Method 2: Check migration status
alembic current
alembic heads

# Method 3: Manual table creation
python ./init_db.py
```

---

## SECTION 3: STARTUP & INITIALIZATION ISSUES

### Problem: "Admin user already exists" error

**Diagnosis**:
```bash
# App startup shows:
# IntegrityError: duplicate key value violates unique constraint
```

**Cause**: Admin user created twice or leftover from old run

**Fix**:
```bash
# Method 1: Delete and recreate
DELETE FROM users WHERE email='admin@supreme.com';
DELETE FROM accounts WHERE owner_id=1;
# Restart app

# Method 2: Skip creation check
# In main.py create_admin_user(), verify user exists first:
admin_check = await db.execute(select(User).where(User.email == 'admin@supreme.com'))
if admin_check.scalars().first():
    return  # Already exists, skip
```

---

### Problem: "System Reserve Account creation fails after startup"

**Diagnosis**:
```bash
# App startup runs fine, but system funding fails:
# KeyError: 'SYS-RESERVE-0001'
```

**Cause**: System Reserve not created or app crashed before creation completed

**Fix**:
```bash
# Method 1: Force recreation
python -c "
import asyncio
from database import SessionLocal
from models import Account
from sqlalchemy import select

async def create_reserve():
    async with SessionLocal() as db:
        # Delete if exists
        await db.execute(
            'DELETE FROM accounts WHERE account_number = \\'SYS-RESERVE-0001\\''
        )
        
        # Create new
        acc = Account(
            owner_id=1,
            account_number='SYS-RESERVE-0001',
            account_type='system',
            is_admin_account=True
        )
        db.add(acc)
        await db.commit()
        print('✓ System Reserve created')

asyncio.run(create_reserve())
"

# Method 2: Check if exists
SELECT * FROM accounts WHERE account_number='SYS-RESERVE-0001';
# If empty, run above script
```

---

### Problem: "SSH tunnel initialization hangs"

**Diagnosis**:
```bash
# App startup hangs for 30+ seconds:
# print("Setting up SSH tunnel...")
# [hangs here]
```

**Cause**: SSH tunnel can't connect to bastion host

**Fix in config.py**:
```python
# Change from:
USE_SSH_TUNNEL = True

# To:
USE_SSH_TUNNEL = False  # Disable if not needed

# Or provide working bastion details:
SSH_HOST = "bastion.company.com"  # Must be accessible
SSH_USER = "ec2-user"
SSH_PRIVATE_KEY = "/path/to/key.pem"
```

---

## SECTION 4: BALANCE SYSTEM ISSUES

### Problem: "Balance mismatch - ledger shows $100 but transactions show $50"

**Diagnosis**:
```bash
# Run verification:
SELECT SUM(amount) FROM transactions WHERE user_id=1 AND status='completed';
# Returns: 50

SELECT SUM(CASE WHEN entry_type='credit' THEN amount ELSE -amount END) 
FROM ledger WHERE user_id=1 AND status='posted';
# Returns: 100

# MISMATCH!
```

**Cause**: Ledger and Transaction table out of sync (likely from Issue #1 not being fixed properly)

**Fix**:
```bash
# Method 1: Find discrepancy source
SELECT 'TRANSACTIONS' as source, user_id, COUNT(*), SUM(amount)
FROM transactions 
WHERE user_id=1 AND status='completed'
GROUP BY user_id

UNION ALL

SELECT 'LEDGER' as source, user_id, COUNT(*), SUM(amount)
FROM ledger 
WHERE user_id=1 AND status='posted'
GROUP BY user_id;

# Method 2: Identify orphaned entries
-- Ledger entries without corresponding transaction?
SELECT l.* FROM ledger l
LEFT JOIN transactions t ON l.related_transaction_id = t.id
WHERE t.id IS NULL AND l.status='posted';

# Delete orphaned ledger entries
DELETE FROM ledger 
WHERE related_transaction_id NOT IN (SELECT id FROM transactions);

# Method 3: Recreate balance from transactions (NUCLEAR OPTION)
-- Delete all ledger for user
DELETE FROM ledger WHERE user_id=1;

-- Recreate from transactions
INSERT INTO ledger (user_id, amount, entry_type, source_account, status, ...)
SELECT user_id, amount, 'credit', 'transaction', 'posted', ...
FROM transactions 
WHERE user_id=1 AND status='completed';
```

---

### Problem: "Account.balance shows stale data"

**Diagnosis**:
```bash
# Dashboard shows: balance=$100
# Create deposit: +$50
# Dashboard shows: still $100 (should be $150)
```

**Cause**: Account.balance not synced with ledger after transaction

**Fix**:
```python
# In any endpoint that changes balance, add:
from balance_service_ledger import BalanceServiceLedger

# After creating transaction:
account = ...
account._balance_cached = await BalanceServiceLedger.get_user_balance(db, user_id)
db.add(account)
await db.commit()

# Or use synced endpoint:
# GET /users/me/dashboard-data
# This will recalculate balance from ledger
```

---

## SECTION 5: KYC & TRANSACTION ISSUES

### Problem: "KYC approved but transactions still blocked"

**Diagnosis**:
```bash
# Admin approves KYC:
POST /api/admin/kyc/1/approve
# Response: 200 OK

# User tries transfer:
POST /transfers {amount: 100}
# Error: KYC not approved

# Check database:
SELECT kyc_status FROM users WHERE id=1;
# Shows: pending (should be approved)
```

**Cause**: KYC approval fix (Issue #2) not applied - only kyc_info updated, not user

**Fix**:
```python
# In routers/admin.py approve_kyc_submission() endpoint:
# After: kyc_info.kyc_status = "approved"

# Add:
from sqlalchemy import select
from models import DBUser

user_result = await db_session.execute(
    select(DBUser).where(DBUser.id == kyc_info.user_id)
)
user = user_result.scalar_one_or_none()

if user:
    user.kyc_status = "approved"
    db_session.add(user)

await db_session.commit()
```

---

### Problem: "KYC submission lock not releasing"

**Diagnosis**:
```bash
# User uploads 4 documents, tries to reupload:
POST /kyc/verify {documents...}
# Error: KYC submission locked after upload

# Check DB:
SELECT submission_locked_at FROM kyc_info WHERE user_id=1;
# Shows: 2024-01-15 10:30:00 (never cleared)
```

**Cause**: Approval doesn't clear submission_locked_at flag

**Fix in routers/admin.py**:
```python
# In approve_kyc_submission():
kyc_info.kyc_status = "approved"
kyc_info.submission_locked_at = None  # ADD THIS
db.add(kyc_info)
```

---

### Problem: "Transaction stays in 'pending' status forever"

**Diagnosis**:
```bash
# Check transaction status:
SELECT status FROM transactions WHERE id=1;
# Shows: pending (should be completed or failed)
```

**Cause**: Transaction gateway validation logic stuck or database not committing

**Fix**:
```bash
# Method 1: Force complete transaction
UPDATE transactions SET status='completed' WHERE id=1;

# Method 2: Force fail transaction
UPDATE transactions SET status='failed', status_reason='Manual test completion' WHERE id=1;

# Method 3: Check transaction_gate logs
grep -n "validate_transaction" server.log
# Look for exceptions

# Method 4: Manually test validation
python -c "
import asyncio
from transaction_gate import TransactionGate
from database import SessionLocal

async def test():
    async with SessionLocal() as db:
        result = await TransactionGate.validate_transfer(
            db=db,
            sender_id=1,
            receiver_id=2,
            amount=100
        )
        print(f'Validation result: {result}')

asyncio.run(test())
"
```

---

## SECTION 6: ACCOUNT OWNERSHIP ISSUES

### Problem: "User can access another user's loan/card/investment"

**Diagnosis**:
```bash
# As User 1, access User 2's loan:
GET /api/v1/loans/999
# Returns: 200 OK with User 2's data (BUG!)

# Should return: 403 Forbidden
```

**Cause**: Ownership enforcement (Issue #5) not applied to this endpoint

**Fix**:
```python
# In routers/loans.py (or applicable router):

@loans_router.post("/{loan_id}")
async def update_loan(
    loan_id: int,
    loan_update: LoanUpdate,
    current_user: CurrentUserDep,  # <- User making request
    db_session: SessionDep
):
    db_loan = await db_session.get(Loan, loan_id)
    
    # ADD OWNERSHIP CHECK:
    if db_loan.user_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="Not authorized to access this resource"
        )
    
    # Continue with update...
```

---

### Problem: "Ownership check works locally but not in production"

**Diagnosis**:
```bash
# Local: 403 Forbidden ✓
# Production: 200 OK ✗
```

**Cause**: Fix applied locally but not deployed, or different code versions

**Fix**:
```bash
# Method 1: Verify deployment
ssh prod-server
grep -n "Not authorized" routers/loans.py
# If not found, code not deployed

# Method 2: Redeploy
git pull
git log --oneline -1
# Verify latest commits are there

# Method 3: Check running process
ps aux | grep python
# See which file is running

# Method 4: Verify fix in running code
python -c "
import importlib.util
spec = importlib.util.spec_from_file_location('loans', '/path/to/routers/loans.py')
loans = importlib.util.module_from_spec(spec)
print('update_loan' in dir(loans))
"
```

---

## SECTION 7: PERFORMANCE ISSUES

### Problem: "App startup takes 30+ seconds"

**Diagnosis**:
```bash
# Time app startup:
time python main.py
# real    0m45.123s

# Check logs:
print("Startup event starting...")  # Shows timestamp
print("Startup event complete")      # Shows timestamp 45 seconds later
```

**Cause**: Balance verification or database query slow

**Fix**:
```python
# In main.py startup event, make verification async:

@app.on_event("startup")
async def verify_balance_systems_consistent():
    print("🔍 Verifying balance systems...")
    
    # REMOVE: await db.execute(select(...)) in loop
    # Instead: Use faster checks
    
    # Option 1: Skip full verification on startup
    print("✓ Balance check postponed to background")
    # Create task to check later
    
    # Option 2: Do quick check only
    result = await db.execute(select(func.count(User)))
    user_count = result.scalar()
    print(f"✓ {user_count} users in system")
```

---

### Problem: "Balance API endpoint times out (> 5 seconds)"

**Diagnosis**:
```bash
curl http://localhost:8000/users/me/dashboard-data
# Takes 5+ seconds to respond
```

**Cause**: N+1 query problem or missing indexes

**Fix**:
```python
# Method 1: Add database indexes
# In models.py Account class:
balance_idx = Column(Float, index=True)  # <- Add index

# Rebuild database:
alembic revision --autogenerate -m "Add balance index"
alembic upgrade head

# Method 2: Batch load balances
# Instead of querying per user in loop
users = await db.execute(select(User))
for user in users:
    balance = await BalanceServiceLedger.get_user_balance(db, user.id)  # SLOW

# Use:
users_with_balances = await db.execute(
    select(User, 
        select(func.sum(...)).correlate(User).scalar_subquery())
)

# Method 3: Add query logging
import logging
logging.basicConfig()
logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)
# See all SQL queries and timing
```

---

## SECTION 8: DEPLOYMENT & PRODUCTION ISSUES

### Problem: "Code works in dev but fails in production"

**Diagnosis**:
```bash
# Dev: Works fine
# Prod: Error 500 in specific endpoint
```

**Cause**: Different environment setup

**Fix**:
```bash
# Method 1: Check environment variables
echo $DATABASE_URL
echo $SECRET_KEY
# Verify all required vars set

# Method 2: Check dependencies installed
pip list | wc -l  # Dev should match prod

# Method 3: Check database schema
# Dev: Different schema version than prod?
alembic current  # Shows migration version
# Must be same in prod

# Method 4: Check file permissions
ls -la /path/to/private/uploads
# Must be readable by app user

# Method 5: Check logs
tail -f /var/log/app/error.log
# Look for actual error message
```

---

### Problem: "Balance inconsistency appears in production but not dev"

**Diagnosis**:
```bash
# Production monitoring shows:
# ⚠️ MISMATCH User 42: Ledger=$500.50, TX=$500.25

# Same data in dev shows: ✓ All balances consistent
```

**Cause**: Race condition in production (concurrent transactions), not in dev

**Fix**:
```python
# Add locks to prevent race conditions
from sqlalchemy import select, for_update

async def get_user_balance_with_lock(db, user_id):
    # Lock the user row
    user = await db.execute(
        select(User).where(User.id == user_id).with_for_update()
    )
    # Now calculate balance safely
    ...

# Or use database transactions
async with db.begin():
    # All queries in this block execute atomically
    transaction = await db.execute(...)
    ledger = await db.execute(...)
    account = await db.execute(...)
    # All succeed or all fail together
```

---

## SECTION 9: QUICK DIAGNOSTICS

### Run all checks at once:

```bash
# Create diagnostic script:
cat > diagnose.py << 'EOF'
import asyncio
from sqlalchemy import select, func, text
from database import SessionLocal
from models import User, Account, Transaction, Ledger, KYCInfo

async def diagnose():
    async with SessionLocal() as db:
        print("\n=== DIAGNOSTIC REPORT ===\n")
        
        # 1. Database connectivity
        try:
            await db.execute(text("SELECT 1"))
            print("✓ Database connected")
        except Exception as e:
            print(f"✗ Database error: {e}")
            return
        
        # 2. User count
        users_result = await db.execute(select(func.count(User.id)))
        user_count = users_result.scalar()
        print(f"✓ {user_count} users in system")
        
        # 3. System Reserve Account
        reserve_result = await db.execute(
            select(Account).where(Account.account_number == 'SYS-RESERVE-0001')
        )
        if reserve_result.scalars().first():
            print("✓ System Reserve Account exists")
        else:
            print("✗ System Reserve Account MISSING")
        
        # 4. KYC Status
        kyc_approved = (await db.execute(
            select(func.count(User.id)).where(User.kyc_status == 'approved')
        )).scalar()
        print(f"✓ {kyc_approved} users KYC approved")
        
        # 5. Balance mismatches
        mismatches = 0
        users = (await db.execute(select(User))).scalars().all()
        for user in users[:5]:  # Check first 5 users only
            tx_result = await db.execute(
                select(func.sum(Transaction.amount)).where(
                    Transaction.user_id == user.id,
                    Transaction.status == 'completed'
                )
            )
            tx_balance = float(tx_result.scalar() or 0)
            
            ledger_result = await db.execute(
                select(func.sum(Ledger.amount)).where(
                    Ledger.user_id == user.id,
                    Ledger.status == 'posted'
                )
            )
            ledger_balance = float(ledger_result.scalar() or 0)
            
            if abs(tx_balance - ledger_balance) > 0.01:
                mismatches += 1
        
        if mismatches == 0:
            print("✓ Balance systems consistent")
        else:
            print(f"✗ {mismatches} balance mismatches found")
        
        print("\n=== END DIAGNOSTIC ===\n")

asyncio.run(diagnose())
EOF

# Run it:
python diagnose.py
```

---

## FINAL CHECKLIST

Before declaring "FIXED", verify:

```
[ ] No errors in startup logs
[ ] Database connectivity confirmed
[ ] System Reserve Account exists  
[ ] KYC approval updates both tables
[ ] Balance systems consistent
[ ] Account ownership enforced
[ ] No balance mismatches
[ ] All 5 issues resolved
[ ] Tests passing
[ ] E2E flow working
```

If any item ✗, follow troubleshooting for that section.
