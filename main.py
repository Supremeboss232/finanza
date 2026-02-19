import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, RedirectResponse
from fastapi import Request, Depends, status
from sqlalchemy import text, select
import logging
from datetime import datetime
from typing import List
import atexit
import time
import asyncio

from auth import get_current_user_from_cookie
from database import SessionLocal, Base, engine
from auth import auth_router # Use the root auth.py for API endpoints
from routers.private import private_router
from routers.users import users_router
try:
    from routers.admin import admin_router
except ImportError:
    admin_router = None
from routers.user_pages import router as user_router
from routers.api_users import router as api_users_router
from routers.kyc import kyc_router
from routers.cards import cards_router
from routers.deposits import deposits_router
from routers.loans import loans_router
from routers.investments import investments_router
from routers.realtime import realtime_router
from routers.account import router as account_router
from routers.financial_planning import router as financial_planning_router
from routers.insurance import router as insurance_router
from routers.notifications import router as notifications_router
from routers.settings import router as settings_router
from routers.support import router as support_router
from routers.projects import router as projects_router
from routers.transfers import router as transfers_router
from routers.security import router as security_router
from routers.fund_ledger import fund_router
from routers.admin_users import admin_users_router
from routers.emails import router as emails_router
from routers.sns_notifications import router as sns_router
from config import settings
from auth_utils import get_password_hash
from deps import get_current_user, get_current_admin_user, SessionDep
from schemas import UserCreate, FundUserRequest, Deposit as PydanticDeposit, Transaction, TransactionCreate, PasswordResetRequest, UserProfileUpdateRequest, AccountStatusToggleRequest, AdminAccessToggleRequest, TransactionCreateRequest
from models import User, Deposit as DBDeposit
from admin_service import admin_service
import crud
import models

log = logging.getLogger(__name__)

# SSH Tunnel Management
ssh_tunnel = None
db_tables_created = False  # Track if database tables have been initialized

def initialize_ssh_tunnel():
    """Initialize SSH tunnel if configured"""
    global ssh_tunnel
    
    if not settings.USE_SSH_TUNNEL:
        print("ℹ️  SSH tunnel disabled. Using direct database connection.")
        return True
    
    try:
        from ssh_tunnel import SSHTunnelManager
        
        print("🔐 Setting up SSH tunnel...")
        ssh_tunnel = SSHTunnelManager(
            ec2_host=settings.SSH_HOST,
            key_path=settings.SSH_KEY_PATH,
            rds_host=settings.RDS_REMOTE_HOST,
            rds_port=settings.RDS_REMOTE_PORT,
            local_port=5432
        )
        
        if ssh_tunnel.start():
            # Register cleanup on exit
            atexit.register(cleanup_ssh_tunnel)
            print("✅ SSH tunnel established successfully!")
            # Give tunnel time to fully establish
            time.sleep(1)
            return True
        else:
            print("❌ Failed to setup SSH tunnel - proceeding with direct connection")
            ssh_tunnel = None
            return False
            
    except ImportError:
        print("⚠️  SSH tunnel not available - proceeding with direct connection")
        return False
    except Exception as e:
        print(f"⚠️  SSH tunnel error: {e}")
        print("   Proceeding with direct connection")
        return False

def cleanup_ssh_tunnel():
    """Cleanup SSH tunnel on exit"""
    global ssh_tunnel
    if ssh_tunnel:
        try:
            ssh_tunnel.stop()
        except Exception as e:
            print(f"Error stopping tunnel: {e}")

# API Configuration served dynamically
API_CONFIG = {
    "baseURL": "http://localhost:8000",
    "timeout": 30000,
    "headers": {
        "Content-Type": "application/json"
    },
    "retries": 2,
    "backoffDelay": 1000
}

async def create_db_and_tables():
    """Creates all database tables defined in models.py."""
    global db_tables_created
    
    if db_tables_created:
        return  # Already created, skip
    
    try:
        print("  Connecting to database for table creation...")
        async with engine.begin() as conn:
            print("  Running metadata.create_all()...")
            await conn.run_sync(Base.metadata.create_all)
        db_tables_created = True
        print("  Tables created successfully")
    except Exception as e:
        print(f"  Error creating tables: {type(e).__name__}: {e}")
        raise

async def test_db_connection():
    """Tests the database connection."""
    try:
        async with SessionLocal() as db:
            await db.execute(text("SELECT 1"))
            print("Database connection successful!")
            return True
    except Exception as e:
        print(f"Database connection failed: {e}")
        return False

async def create_admin_user():
    """
    Ensures the default admin user exists with a linked account.
    
    ⚠️ CORE RULE (NON-NEGOTIABLE):
    Admin user must have BOTH User ID and Account ID bound together.
    """
    from sqlalchemy import select
    from models import Account
    import time
    
    async with SessionLocal() as db:
        result = await db.execute(select(User).filter(User.email == settings.ADMIN_EMAIL))
        admin_user = result.scalars().first()
        
        if not admin_user:
            # Create a new admin user with an argon2 hashed password if one doesn't exist
            hashed_password = get_password_hash(settings.ADMIN_PASSWORD)
            new_admin = User(
                full_name="Admin User",
                email=settings.ADMIN_EMAIL,
                hashed_password=hashed_password,
                is_admin=True,
                is_active=True,
                kyc_status='approved'  # Admin is pre-approved
            )
            db.add(new_admin)
            await db.flush()  # Get the admin ID
            
            # Create admin's primary account (REQUIRED - no admin without account)
            admin_account_number = f"ADMIN{new_admin.id}_{int(time.time() * 1000000) % 1000000}"
            from datetime import datetime
            admin_account = Account(
                owner_id=new_admin.id,
                account_number=admin_account_number,
                account_type='admin',
                balance=0.0,
                currency='USD',
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            db.add(admin_account)
            new_admin.account_number = admin_account_number
            
            await db.commit()
            print("✅ Default admin user and account created successfully.")
            
        elif not admin_user.is_admin:
            # If admin user exists but is not marked as admin, update them
            admin_user.is_admin = True
            
            # Check if admin has account - if not, create one
            account_check = await db.execute(
                select(Account).filter(Account.owner_id == admin_user.id)
            )
            if not account_check.scalars().first():
                import time
                from datetime import datetime
                admin_account_number = f"ADMIN{admin_user.id}_{int(time.time() * 1000000) % 1000000}"
                admin_account = Account(
                    owner_id=admin_user.id,
                    account_number=admin_account_number,
                    account_type='admin',
                    balance=0.0,
                    currency='USD',
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                )
                db.add(admin_account)
                admin_user.account_number = admin_account_number
            
            await db.commit()
            print("✅ Admin user updated and account ensured.")
        else:
            # Verify admin has an account
            account_check = await db.execute(
                select(Account).filter(Account.owner_id == admin_user.id)
            )
            if not account_check.scalars().first():
                import time
                from datetime import datetime
                admin_account_number = f"ADMIN{admin_user.id}_{int(time.time() * 1000000) % 1000000}"
                admin_account = Account(
                    owner_id=admin_user.id,
                    account_number=admin_account_number,
                    account_type='admin',
                    balance=0.0,
                    currency='USD',
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                )
                db.add(admin_account)
                admin_user.account_number = admin_account_number
                await db.commit()
                print("✅ Admin account was missing and has been created.")
            else:
                print("✅ Admin user and account already exist.")

async def create_system_reserve_account():
    """
    Creates a system reserve account for treasury/funding operations.
    
    ⚠️ SYSTEM ACCOUNT - Core Financial Component
    
    System User Details:
    - ID: 1 (reserved)
    - Name: System Reserve / Treasury
    - Email: sysreserve@finanza.com
    - Password: Supposedbe5
    - Role: admin / system
    - Status: Active
    - KYC: approved
    
    System Reserve Account Details:
    - Account Number: SYS-RESERVE-0001
    - Account Type: treasury
    - Owner: System User (User ID = 1)
    - Balance: $10,000,000 (seed amount for testing/live ops)
    - Currency: USD
    - Status: Active
    - KYC Level: full
    - Is Admin Account: True
    
    Purpose: Single source for all admin credit operations
    """
    from sqlalchemy import select
    from models import Account, Ledger
    from decimal import Decimal
    
    async with SessionLocal() as db:
        try:
            # Step 1: Create or verify system user (ID = 1)
            result = await db.execute(select(User).filter(User.id == 1))
            system_user = result.scalars().first()
            
            if not system_user:
                # Create the system user with exact specifications
                system_user = User(
                    id=1,  # Explicitly set ID to 1 (reserved)
                    full_name="System Reserve / Treasury",
                    email="sysreserve@finanza.com",
                    hashed_password=get_password_hash("Supposedbe5"),  # Exact password from spec
                    is_active=True,
                    is_admin=True,
                    is_verified=True,
                    kyc_status='approved'  # System is pre-approved
                )
                db.add(system_user)
                await db.flush()
                print("✅ System User (ID=1) created successfully")
                print(f"   → Name: {system_user.full_name}")
                print(f"   → Email: {system_user.email}")
                print(f"   → Role: admin/system")
            else:
                print("✅ System User (ID=1) already exists")
            
            # Step 2: Create or verify system reserve account
            result = await db.execute(
                select(Account).filter(Account.account_number == "SYS-RESERVE-0001")
            )
            reserve_account = result.scalars().first()
            
            SEED_BALANCE = 10_000_000.0  # $10M seed for testing/demo
            
            if not reserve_account:
                # Create the system reserve account with exact specifications
                from datetime import datetime
                reserve_account = Account(
                    owner_id=1,  # Owned by system user
                    account_number="SYS-RESERVE-0001",
                    account_type="treasury",  # Exact type from spec
                    balance=SEED_BALANCE,  # $10M seed amount
                    currency="USD",
                    status="active",
                    kyc_level="full",  # Full KYC as per spec
                    is_admin_account=True,
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                )
                db.add(reserve_account)
                await db.flush()
                
                # Step 3: Create initial transaction and ledger entry for seed balance
                # This represents the initial funding of the reserve account
                from models import Transaction
                
                seed_transaction = Transaction(
                    user_id=1,  # System user
                    account_id=reserve_account.id,
                    amount=SEED_BALANCE,
                    transaction_type="system_seed",
                    direction="credit",
                    status="completed",
                    description="System Reserve Account initialization seed"
                )
                db.add(seed_transaction)
                await db.flush()  # Get transaction.id
                
                seed_ledger = Ledger(
                    user_id=1,  # System user
                    entry_type="credit",  # Money coming into the system
                    amount=Decimal(str(SEED_BALANCE)),
                    transaction_id=seed_transaction.id,  # Link to seed transaction
                    description="System Reserve Account initialization seed",
                    status="posted"
                )
                db.add(seed_ledger)
                
                await db.commit()
                print("✅ System Reserve Account (SYS-RESERVE-0001) created successfully")
                print(f"   → Account Number: SYS-RESERVE-0001")
                print(f"   → Owner: System User (ID=1)")
                print(f"   → Account Type: treasury")
                print(f"   → Balance: ${SEED_BALANCE:,.2f}")
                print(f"   → KYC Level: full")
                print(f"   → Status: Active and ready for use")
            else:
                print("✅ System Reserve Account (SYS-RESERVE-0001) already exists")
                print(f"   → Current Balance: ${reserve_account.balance:,.2f}")
        
        except Exception as e:
            print(f"⚠️  Error creating system reserve account: {e}")
            await db.rollback()
            raise


app = FastAPI()
origins = [
    "http://localhost:8000",  # FastAPI app
    "http://127.0.0.1:8000", # FastAPI app
    "http://51.20.190.13:8000",  # EC2 instance
    "http://51.20.190.13",  # EC2 instance without port
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def ensure_db_tables(request: Request, call_next):
    """Ensure database tables are created on first request."""
    global db_tables_created
    
    # Only create tables on actual API requests (not static files)
    if not db_tables_created and request.url.path.startswith(("/api", "/auth", "/user")):
        try:
            await create_db_and_tables()
        except Exception as e:
            print(f"Error initializing database tables: {e}")
            # Continue anyway, endpoint will handle database errors
    
    response = await call_next(request)
    return response


@app.middleware("http")
async def user_jail_middleware(request: Request, call_next):
    """
    This middleware enforces that authenticated users can only access routes
    under /user/ or exempt paths.
    """
    # Paths that do not require this check
    # Add explicit signin/signup/forgot-password paths (and .html variants) so public auth pages aren't redirected
    exempt_paths = [
        "/api", "/auth", "/css", "/js", "/lib", "/img", "/static", "/admin_static",
        "/docs", "/openapi.json", "/signin", "/signup", "/forgot-password", "/signin.html", "/signup.html", "/logout"
    ]
    is_exempt = any(request.url.path.startswith(p) for p in exempt_paths)
    
    try:
        if not is_exempt:
            user = await get_current_user_from_cookie(request)
            if user:
                # Only redirect if trying to access non-/user path
                if not request.url.path.startswith("/user"):
                    # Redirect to appropriate dashboard
                    dashboard_url = "/user/admin/dashboard" if (user.email == settings.ADMIN_EMAIL or user.is_admin) else "/user/dashboard"
                    return RedirectResponse(url=dashboard_url)
    except Exception as e:
        # Log middleware errors but don't crash
        print(f"Middleware error: {e}")
    
    response = await call_next(request)
    return response


@app.on_event("startup")
async def startup_event():
    try:
        # Initialize SSH tunnel if configured
        print("[*] Initializing application...")
        initialize_ssh_tunnel()
        
        # Create database tables during startup
        print("[*] Connecting to database for table creation...")
        await create_db_and_tables()
        
        # Test database connection
        print("[*] Testing database connection...")
        await test_db_connection()
        
        # ISSUE #3 FIX: Create admin user and system reserve account
        print("[*] Setting up admin and system accounts...")
        await create_admin_user()
        
        print("[*] Creating System Reserve Account...")
        await create_system_reserve_account()
        
        print("[OK] Application ready")
        
    except Exception as e:
        print(f"[WARN] Startup issue: {e}")
        print("[WARN] Application will continue in limited mode")

# --- Static Files & Routers ---

# User-facing static assets (CSS, JS, Lib, Img)
app.mount("/css", StaticFiles(directory="static/css"), name="css")
app.mount("/js", StaticFiles(directory="static/js"), name="js")
app.mount("/lib", StaticFiles(directory="static/lib"), name="lib")
app.mount("/img", StaticFiles(directory="static/img"), name="img")
# Admin static assets (for aws-config.js and other admin-specific files)
app.mount("/admin_static", StaticFiles(directory="admin_static"), name="admin_static")
# Also mount the full `static` directory at `/static` to support templates
# that reference `/static/...` paths.
app.mount("/static", StaticFiles(directory="static"), name="static")

# Include API routers
app.include_router(auth_router, prefix="/auth")
app.include_router(private_router, prefix="/user") # Handles authenticated UI routes under /user/* and /user/admin/*
app.include_router(users_router, prefix="/api/v1/users")
if admin_router:
    app.include_router(admin_router, prefix="/api/admin")
app.include_router(api_users_router)  # /api/user/* endpoints
# Mount product routers under /api/v1 to serve JSON for user pages
app.include_router(kyc_router, prefix="/api/v1")
app.include_router(cards_router, prefix="/api/v1")
app.include_router(deposits_router, prefix="/api/v1")
app.include_router(loans_router, prefix="/api/v1")
app.include_router(investments_router, prefix="/api/v1")
# Account router (uploads, profile updates)
app.include_router(account_router, prefix="/api/v1")
# Feature routers
app.include_router(financial_planning_router)
app.include_router(insurance_router)
app.include_router(notifications_router)
app.include_router(settings_router)
app.include_router(support_router)
app.include_router(projects_router)
app.include_router(transfers_router)  # Transfers and bill pay
app.include_router(security_router)  # Security endpoints
# Fund management router
app.include_router(fund_router)
# Admin user data retrieval router
app.include_router(admin_users_router)
# Email service router
app.include_router(emails_router)
# SNS notification router
app.include_router(sns_router)
# Realtime WebSocket router
app.include_router(realtime_router)

# PHASE 1: NEW PAYMENT, CREDIT, COMPLIANCE ROUTERS - COMPLIANCE DISABLED (Priority 3 used instead)
try:
    from routers.payments_api import router as payments_router
    from routers.credit_api import router as credit_router
    # from routers.compliance_api import router as compliance_router  # Disabled - Priority 3 compliance_priority3_api used instead
    
    app.include_router(payments_router, prefix="/api/v1")
    app.include_router(credit_router, prefix="/api/v1")
    # app.include_router(compliance_router, prefix="/api/v1")  # Disabled - Priority 3 version active
    log.info("Phase 1 Payment and Credit routers registered (Compliance uses Priority 3)")
except Exception as e:
    log.warning(f"Phase 1 routers not available: {e}")

# PHASE 2B: ACCOUNT MANAGEMENT, LENDING, RETURNS, HMDA ROUTERS
try:
    from routers.accounts_api import router as accounts_router
    from routers.lending_api import router as lending_router
    from routers.returns_api import router as returns_router
    from routers.hmda_api import router as hmda_router
    
    app.include_router(accounts_router)  # Prefix defined in router as /api/v1/accounts
    app.include_router(lending_router)  # Prefix defined in router as /api/v1/loans
    app.include_router(returns_router)  # Prefix defined in router as /api/v1/returns
    app.include_router(hmda_router)  # Prefix defined in router as /api/v1/hmda
    log.info("Phase 2B Account Management, Lending, Returns, and HMDA routers registered")
except ImportError as e:
    log.warning(f"Phase 2B routers not available: {e}")

# PRIORITY 3 API: NEW SCHEDULED TRANSFERS, WEBHOOKS, MOBILE DEPOSITS, COMPLIANCE
try:
    from routers.scheduled_transfers_api_new import router as scheduled_transfers_priority3_router
    from routers.webhooks_priority3_api import router as webhooks_priority3_router
    from routers.mobile_deposit_admin_api import router as mobile_deposits_priority3_router
    from routers.compliance_priority3_api import router as compliance_priority3_router
    
    log.info(f"About to register scheduled transfers router with {len(scheduled_transfers_priority3_router.routes)} routes")
    app.include_router(scheduled_transfers_priority3_router)
    log.info(f"About to register webhooks router with {len(webhooks_priority3_router.routes)} routes")
    app.include_router(webhooks_priority3_router)
    log.info(f"About to register mobile deposits router with {len(mobile_deposits_priority3_router.routes)} routes")
    app.include_router(mobile_deposits_priority3_router)
    log.info(f"About to register compliance router with {len(compliance_priority3_router.routes)} routes")
    app.include_router(compliance_priority3_router)
    log.info("✅ Priority 3 APIs registered: Scheduled Transfers, Webhooks, Mobile Deposits, Compliance")
except Exception as e:
    log.warning(f"Priority 3 APIs not available: {e}")
    import traceback
    log.warning(traceback.format_exc())

# PHASE 3A: SCHEDULED TRANSFERS, BILL PAY, MOBILE DEPOSIT ROUTERS (Legacy) - DISABLED (Priority 3 versions used instead)
try:
    # Legacy routers disabled - Priority 3 versions (scheduled_transfers_api_new, mobile_deposit_admin_api) are used instead
    pass
    log.info("Phase 3A legacy routers disabled (Priority 3 versions active)")
except Exception as e:
    log.warning(f"Phase 3A routers not available: {e}")

# PHASE 3B: GEOGRAPHIC EXPANSION & MULTI-CURRENCY ROUTERS
try:
    from routers.geo_routes_api import router as geo_router
    from routers.currency_routes_api import router as currency_router
    
    app.include_router(geo_router)  # Prefix defined in router as /api/v1
    app.include_router(currency_router)  # Prefix defined in router as /api/v1
    log.info("Phase 3B Geographic Expansion and Currency Exchange routers registered")
except (ImportError, ModuleNotFoundError) as e:
    log.warning(f"Phase 3B routers not available: {e}")
except Exception as e:
    log.warning(f"Phase 3B routers not available (optional dependency): {e}")

# PHASE 3C: PERFORMANCE OPTIMIZATION & REAL-TIME ROUTERS
try:
    from routers.webhooks_api import router as webhooks_router
    from routers.monitoring_api import router as monitoring_router
    from routers.realtime_api import router as realtime_update_router
    from routers.optimization_api import router as optimization_router
    
    app.include_router(webhooks_router)  # Prefix defined in router as /api/v1/webhooks
    app.include_router(monitoring_router)  # Prefix defined in router as /api/v1/monitoring
    app.include_router(realtime_update_router)  # Prefix defined in router as /api/v1/realtime
    app.include_router(optimization_router)  # Prefix defined in router as /api/v1/optimization
    log.info("Phase 3C Performance Optimization and Real-Time routers registered")
except ImportError as e:
    log.warning(f"Phase 3C routers not available: {e}")

# PHASE 4: ENTERPRISE FEATURES - FRAUD DETECTION, BLOCKCHAIN, REPORTING, TREASURY, SETTLEMENT
try:
    from routers.fraud_detection_api import router as fraud_detection_router
    from routers.blockchain_api import router as blockchain_router
    from routers.reporting_api import router as reporting_router
    from routers.treasury_api import router as treasury_router
    from routers.settlement_api import router as settlement_router
    
    app.include_router(fraud_detection_router)  # Prefix defined in router as /api/v1/fraud
    app.include_router(blockchain_router)  # Prefix defined in router as /api/v1/blockchain
    app.include_router(reporting_router)  # Prefix defined in router as /api/v1/reporting
    app.include_router(treasury_router)  # Prefix defined in router as /api/v1/treasury
    app.include_router(settlement_router)  # Prefix defined in router as /api/v1/settlement
    log.info("Phase 4 Enterprise Features routers registered (Fraud Detection, Blockchain, Reporting, Treasury, Settlement)")
except (ImportError, ModuleNotFoundError, AttributeError) as e:
    log.warning(f"Phase 4 routers not available: {e}")
except Exception as e:
    log.warning(f"Phase 4 routers not available (optional): {e}")

# Include user-facing pages (prefix defined in router as /user)
app.include_router(user_router)

# --- Admin Data Endpoints (Python-only, no JSON) ---
@app.get("/api/admin/data/users")
async def fetch_admin_users(db: SessionDep, current_admin: User = Depends(get_current_admin_user), skip: int = 0, limit: int = 100):
    """Fetch all users for admin dashboard"""
    try:
        users = await admin_service.get_all_users(db, skip=skip, limit=limit)
        return {"success": True, "data": users}
    except Exception as e:
        log.error(f"Error fetching users: {e}")
        return {"success": False, "error": str(e)}, 500


@app.get("/api/admin/transactions")
async def get_admin_transactions(db: SessionDep, current_admin: User = Depends(get_current_admin_user), skip: int = 0, limit: int = 100, status: str = None):
    """
    Get transactions for admin dashboard.
    
    Filters:
    - status=None: All transaction statuses (completed, pending, blocked, failed, cancelled)
    - status='completed': Only completed (settled) transactions
    - status='held': Pending + blocked (held funds, not settled)
    
    Admin sees ALL statuses by default.
    """
    try:
        status_filter = 'pending_or_blocked' if status == 'held' else status
        transactions = await admin_service.get_all_transactions(
            db, 
            skip=skip, 
            limit=limit,
            status_filter=status_filter
        )
        return transactions
    except Exception as e:
        log.error(f"Error fetching transactions: {e}")
        return {"success": False, "error": str(e)}, 500


@app.get("/api/admin/kyc")
async def get_admin_kyc(db: SessionDep, current_admin: User = Depends(get_current_admin_user), skip: int = 0, limit: int = 100):
    """Get KYC submissions for admin dashboard with complete document information"""
    try:
        result = await db.execute(
            select(models.KYCSubmission)
            .offset(skip)
            .limit(limit)
            .order_by(models.KYCSubmission.submitted_at.desc())
        )
        kyc_submissions = result.scalars().all()
        
        # Build complete response with user information
        kyc_list = []
        for kyc in kyc_submissions:
            # Get user details
            user_result = await db.execute(select(models.User).filter(models.User.id == kyc.user_id))
            user = user_result.scalar_one_or_none()
            
            kyc_list.append({
                "id": kyc.id,
                "user_id": kyc.user_id,
                "user_email": user.email if user else "Unknown",
                "user_name": user.full_name if user else "Unknown",
                "document_type": kyc.document_type,
                "document_file_path": kyc.document_file_path,
                "status": kyc.status,
                "submitted_at": kyc.submitted_at,
                "reviewed_at": kyc.reviewed_at
            })
        
        return {
            "success": True,
            "data": kyc_list,
            "total": len(kyc_list)
        }
    except Exception as e:
        log.error(f"Error fetching KYC: {e}")
        return {"success": False, "error": str(e)}, 500


@app.get("/api/admin/deposits")
async def get_admin_deposits(db: SessionDep, current_admin: User = Depends(get_current_admin_user), skip: int = 0, limit: int = 100):
    """Get deposits for admin dashboard"""
    try:
        result = await db.execute(
            select(models.Deposit)
            .offset(skip)
            .limit(limit)
        )
        deposits = result.scalars().all()
        return {
            "success": True,
            "data": [
                {
                    "id": deposit.id,
                    "user_id": deposit.user_id,
                    "amount": float(deposit.amount),
                    "status": deposit.status,
                    "created_at": deposit.created_at
                }
                for deposit in deposits
            ]
        }
    except Exception as e:
        log.error(f"Error fetching deposits: {e}")
        return {"success": False, "error": str(e)}, 500


@app.post("/api/admin/transactions")
async def create_admin_transaction(
    request: TransactionCreateRequest,
    db: SessionDep, 
    current_admin: User = Depends(get_current_admin_user)
):
    """Create a transaction for a user (admin only)"""
    try:
        # Find user by email
        result = await db.execute(select(models.User).filter(models.User.email == request.user_email))
        user = result.scalar_one_or_none()
        
        if not user:
            return {"success": False, "error": "User not found"}, 404
        
        # Get or create user account
        # PRINCIPLE: Money must never land without an account
        account_result = await db.execute(
            select(models.Account).filter(models.Account.owner_id == user.id)
        )
        account = account_result.scalars().first()
        
        if not account:
            # Create account if user doesn't have one
            account = models.Account(
                account_number=f"ACC-{user.id}-{int(__import__('time').time())}",
                balance=0.0,  # Start with 0 - will be calculated from transactions
                currency="USD",
                owner_id=user.id
            )
            db.add(account)
            await db.flush()
        
        # Create transaction - THIS IS THE SOURCE OF TRUTH FOR BALANCE
        transaction_data = TransactionCreate(
            transaction_type=request.transaction_type,
            amount=request.amount,
            description=request.description,
            status="completed",
            user_id=user.id,  # REQUIRED
            account_id=account.id  # REQUIRED
        )
        
        db_transaction = await crud.create_user_transaction(db, transaction_data, user.id, account.id)
        
        # IMPORTANT: Do NOT manually update account.balance
        # Balance is ALWAYS calculated from transactions via BalanceService
        
        await db.commit()
        await db.refresh(db_transaction)
        return {"success": True, "data": Transaction.model_validate(db_transaction)}
    except Exception as e:
        await db.rollback()
        log.error(f"Error creating transaction: {e}")
        return {"success": False, "error": str(e)}, 500


@app.get("/api/admin/data/transactions")
async def fetch_admin_transactions(db: SessionDep, current_admin: User = Depends(get_current_admin_user), skip: int = 0, limit: int = 100, status: str = None):
    """Fetch transactions for admin dashboard with optional status filtering"""
    try:
        status_filter = 'pending_or_blocked' if status == 'held' else status
        transactions = await admin_service.get_all_transactions(
            db, 
            skip=skip, 
            limit=limit,
            status_filter=status_filter
        )
        return {"success": True, "data": transactions}
    except Exception as e:
        log.error(f"Error fetching transactions: {e}")
        return {"success": False, "error": str(e)}, 500


@app.get("/api/admin/data/deposits")
async def fetch_admin_deposits_data(db: SessionDep, current_admin: User = Depends(get_current_admin_user), skip: int = 0, limit: int = 100):
    """Fetch deposits for admin dashboard (data endpoint)"""
    try:
        result = await db.execute(
            select(models.Deposit)
            .offset(skip)
            .limit(limit)
        )
        deposits = result.scalars().all()
        return {
            "success": True,
            "data": [
                {
                    "id": deposit.id,
                    "user_id": deposit.user_id,
                    "amount": float(deposit.amount),
                    "status": deposit.status,
                    "created_at": deposit.created_at
                }
                for deposit in deposits
            ]
        }
    except Exception as e:
        log.error(f"Error fetching deposits: {e}")
        return {"success": False, "error": str(e)}, 500



@app.get("/api/admin/data/investments")
async def fetch_admin_investments(db: SessionDep, current_admin: User = Depends(get_current_admin_user), skip: int = 0, limit: int = 100):
    """Fetch all investments for admin dashboard"""
    try:
        result = await db.execute(
            select(models.Investment)
            .offset(skip)
            .limit(limit)
        )
        investments = result.scalars().all()
        return {"success": True, "data": investments}
    except Exception as e:
        log.error(f"Error fetching investments: {e}")
        return {"success": False, "error": str(e)}, 500


@app.get("/api/admin/data/cards")
async def fetch_admin_cards(db: SessionDep, current_admin: User = Depends(get_current_admin_user), skip: int = 0, limit: int = 100):
    """Fetch all cards for admin dashboard"""
    try:
        result = await db.execute(
            select(models.Card)
            .offset(skip)
            .limit(limit)
        )
        cards = result.scalars().all()
        return {"success": True, "data": cards}
    except Exception as e:
        log.error(f"Error fetching cards: {e}")
        return {"success": False, "error": str(e)}, 500


@app.get("/api/admin/users/{user_id}/data")
async def fetch_user_all_data(
    user_id: int,
    db: SessionDep,
    current_admin: User = Depends(get_current_admin_user)
):
    """Fetch all financial data for a specific user (admin view)"""
    try:
        # Get user
        user_result = await db.execute(select(models.User).filter(models.User.id == user_id))
        user = user_result.scalar_one_or_none()
        
        if not user:
            return {"success": False, "error": "User not found"}, 404
        
        # Get all user financial data
        deposits_result = await db.execute(
            select(models.Deposit).filter(models.Deposit.user_id == user_id)
        )
        loans_result = await db.execute(
            select(models.Loan).filter(models.Loan.user_id == user_id)
        )
        investments_result = await db.execute(
            select(models.Investment).filter(models.Investment.user_id == user_id)
        )
        cards_result = await db.execute(
            select(models.Card).filter(models.Card.user_id == user_id)
        )
        transactions_result = await db.execute(
            select(models.Transaction).filter(models.Transaction.user_id == user_id)
        )
        
        return {
            "success": True,
            "data": {
                "user": user,
                "deposits": deposits_result.scalars().all(),
                "loans": loans_result.scalars().all(),
                "investments": investments_result.scalars().all(),
                "cards": cards_result.scalars().all(),
                "transactions": transactions_result.scalars().all()
            }
        }
    except Exception as e:
        log.error(f"Error fetching user data: {e}")
        return {"success": False, "error": str(e)}, 500


@app.post("/api/admin/deposits/{deposit_id}/update")
async def admin_update_deposit(
    deposit_id: int,
    db: SessionDep,
    current_admin: User = Depends(get_current_admin_user),
    status: str = None,
    interest_rate: float = None,
    current_balance: float = None
):
    """Admin update deposit details"""
    try:
        result = await db.execute(select(models.Deposit).filter(models.Deposit.id == deposit_id))
        deposit = result.scalar_one_or_none()
        
        if not deposit:
            return {"success": False, "error": "Deposit not found"}, 404
        
        if status:
            deposit.status = status
        if interest_rate is not None:
            deposit.interest_rate = interest_rate
        if current_balance is not None:
            deposit.current_balance = current_balance
        
        db.add(deposit)
        await db.commit()
        await db.refresh(deposit)
        
        return {"success": True, "data": deposit}
    except Exception as e:
        await db.rollback()
        log.error(f"Error updating deposit: {e}")
        return {"success": False, "error": str(e)}, 500


@app.post("/api/admin/investments/{investment_id}/update")
async def admin_update_investment(
    investment_id: int,
    db: SessionDep,
    current_admin: User = Depends(get_current_admin_user),
    status: str = None,
    current_value: float = None,
    interest_earned: float = None,
    annual_return_rate: float = None
):
    """Admin update investment details"""
    try:
        result = await db.execute(select(models.Investment).filter(models.Investment.id == investment_id))
        investment = result.scalar_one_or_none()
        
        if not investment:
            return {"success": False, "error": "Investment not found"}, 404
        
        if status:
            investment.status = status
        if current_value is not None:
            investment.current_value = current_value
        if interest_earned is not None:
            investment.interest_earned = interest_earned
        if annual_return_rate is not None:
            investment.annual_return_rate = annual_return_rate
        
        db.add(investment)
        await db.commit()
        await db.refresh(investment)
        
        return {"success": True, "data": investment}
    except Exception as e:
        await db.rollback()
        log.error(f"Error updating investment: {e}")
        return {"success": False, "error": str(e)}, 500


@app.get("/api/admin/data/kyc")
async def fetch_admin_kyc(db: SessionDep, current_admin: User = Depends(get_current_admin_user), skip: int = 0, limit: int = 100):
    """Fetch KYC submissions for admin dashboard"""
    try:
        result = await db.execute(
            select(models.KYCSubmission)
            .offset(skip)
            .limit(limit)
        )
        kyc_submissions = result.scalars().all()
        return {
            "success": True,
            "data": [
                {
                    "id": kyc.id,
                    "user_id": kyc.user_id,
                    "document_type": kyc.document_type,
                    "status": kyc.status,
                    "submitted_at": kyc.submitted_at,
                    "reviewed_at": kyc.reviewed_at
                }
                for kyc in kyc_submissions
            ]
        }
    except Exception as e:
        log.error(f"Error fetching KYC submissions: {e}")
        return {"success": False, "error": str(e)}, 500


@app.get("/api/admin/data/metrics")
async def fetch_admin_metrics(db: SessionDep, current_admin: User = Depends(get_current_admin_user)):
    """Fetch dashboard metrics"""
    try:
        metrics = await admin_service.get_dashboard_metrics(db)
        return {"success": True, "data": metrics}
    except Exception as e:
        log.error(f"Error fetching metrics: {e}")
        return {"success": False, "error": str(e)}, 500


@app.get("/api/admin/data/reports")
async def fetch_admin_reports(db: SessionDep, current_admin: User = Depends(get_current_admin_user)):
    """Fetch admin reports"""
    try:
        reports = await admin_service.get_admin_reports(db)
        return {"success": True, "data": reports}
    except Exception as e:
        log.error(f"Error generating reports: {e}")
        return {"success": False, "error": str(e)}, 500


@app.get("/api/admin/data/health")
async def fetch_system_health(db: SessionDep, current_admin: User = Depends(get_current_admin_user)):
    """Get system health status"""
    try:
        health = await admin_service.get_system_health(db)
        return {"success": True, "data": health}
    except Exception as e:
        log.error(f"Error checking system health: {e}")
        return {"success": False, "error": str(e)}, 500


@app.post("/api/admin/users")
async def admin_create_user_endpoint(user: UserCreate, db: SessionDep):
    """Create a new user (admin only)"""
    try:
        created = await admin_service.create_new_user(db, user)
        return {"success": True, "data": created}
    except ValueError as e:
        return {"success": False, "error": str(e)}, 400
    except Exception as e:
        log.error(f"Error creating user: {e}")
        return {"success": False, "error": str(e)}, 500


@app.put("/api/admin/users/{user_id}")
async def update_admin_user(
    user_id: int, 
    updates: dict, 
    db: SessionDep,
    current_admin: User = Depends(get_current_admin_user)
):
    """Update user (admin only)"""
    try:
        updated = await admin_service.update_user(db, user_id, updates)
        return {"success": True, "data": updated}
    except ValueError as e:
        return {"success": False, "error": str(e)}, 404
    except Exception as e:
        log.error(f"Error updating user: {e}")
        return {"success": False, "error": str(e)}, 500


@app.delete("/api/admin/users/{user_id}")
async def delete_admin_user(user_id: int, db: SessionDep, current_admin: User = Depends(get_current_admin_user)):
    """Delete user (admin only)"""
    try:
        result = await admin_service.delete_user(db, user_id)
        return {"success": True, "data": result}
    except ValueError as e:
        return {"success": False, "error": str(e)}, 404
    except Exception as e:
        log.error(f"Error deleting user: {e}")
        return {"success": False, "error": str(e)}, 500


# --- Comprehensive User Profile Management ---
@app.get("/api/admin/users/{user_id}/profile")
async def get_user_profile(
    user_id: int,
    db: SessionDep,
    current_admin: User = Depends(get_current_admin_user)
):
    """Get complete user profile for admin editing"""
    try:
        result = await db.execute(select(models.User).filter(models.User.id == user_id))
        user = result.scalar_one_or_none()
        
        if not user:
            return {"success": False, "error": "User not found"}, 404
        
        return {
            "success": True,
            "data": {
                "id": user.id,
                "full_name": user.full_name,
                "email": user.email,
                "phone": user.phone,
                "address": user.address,
                "region": user.region,
                "country": user.country,
                "account_number": user.account_number,
                "account_type": user.account_type,
                "is_active": user.is_active,
                "is_admin": user.is_admin,
                "kyc_status": user.kyc_status,
                "kyc_verified": user.kyc_verified,
                "created_at": user.created_at,
                "updated_at": user.updated_at
            }
        }
    except Exception as e:
        log.error(f"Error fetching user profile: {e}")
        return {"success": False, "error": str(e)}, 500


@app.post("/api/admin/users/{user_id}/profile/update")
async def update_user_profile(
    user_id: int,
    request: UserProfileUpdateRequest,
    db: SessionDep,
    current_admin: User = Depends(get_current_admin_user)
):
    """Update user profile information"""
    try:
        result = await db.execute(select(models.User).filter(models.User.id == user_id))
        user = result.scalar_one_or_none()
        
        if not user:
            return {"success": False, "error": "User not found"}, 404
        
        # Update fields that were provided
        if request.full_name is not None:
            user.full_name = request.full_name
        if request.email is not None:
            # Check if email is already in use
            email_check = await db.execute(
                select(models.User).filter(
                    models.User.email == request.email,
                    models.User.id != user_id
                )
            )
            if email_check.scalar_one_or_none():
                return {"success": False, "error": "Email already in use"}, 400
            user.email = request.email
        if request.phone is not None:
            user.phone = request.phone
        if request.address is not None:
            user.address = request.address
        if request.region is not None:
            user.region = request.region
        if request.country is not None:
            user.country = request.country
        if request.account_type is not None:
            user.account_type = request.account_type
        if request.account_number is not None:
            user.account_number = request.account_number
        if request.is_active is not None:
            user.is_active = request.is_active
        if request.is_admin is not None:
            user.is_admin = request.is_admin
        
        user.updated_at = datetime.utcnow()
        db.add(user)
        await db.commit()
        await db.refresh(user)
        
        return {
            "success": True,
            "data": {
                "id": user.id,
                "full_name": user.full_name,
                "email": user.email,
                "phone": user.phone,
                "address": user.address,
                "region": user.region,
                "country": user.country,
                "account_number": user.account_number,
                "account_type": user.account_type,
                "is_active": user.is_active,
                "is_admin": user.is_admin,
                "updated_at": user.updated_at
            }
        }
    except Exception as e:
        await db.rollback()
        log.error(f"Error updating user profile: {e}")
        return {"success": False, "error": str(e)}, 500


@app.post("/api/admin/users/{user_id}/password/reset")
async def admin_reset_user_password(
    user_id: int,
    request: PasswordResetRequest,
    db: SessionDep,
    current_admin: User = Depends(get_current_admin_user)
):
    """Admin reset user password"""
    try:
        if not request.new_password or len(request.new_password.strip()) == 0:
            return {"success": False, "error": "New password is required"}, 400
        
        result = await db.execute(select(models.User).filter(models.User.id == user_id))
        user = result.scalar_one_or_none()
        
        if not user:
            return {"success": False, "error": "User not found"}, 404
        
        # Hash and update password
        user.hashed_password = get_password_hash(request.new_password)
        user.updated_at = datetime.utcnow()
        
        db.add(user)
        await db.commit()
        await db.refresh(user)
        
        return {
            "success": True,
            "message": f"Password reset successfully for user {user.email}",
            "data": {
                "id": user.id,
                "email": user.email,
                "updated_at": user.updated_at
            }
        }
    except Exception as e:
        await db.rollback()
        log.error(f"Error resetting user password: {e}")
        return {"success": False, "error": str(e)}, 500


@app.post("/api/admin/users/{user_id}/account-status/toggle")
async def toggle_user_account_status(
    user_id: int,
    request: AccountStatusToggleRequest,
    db: SessionDep,
    current_admin: User = Depends(get_current_admin_user)
):
    """Toggle user account active/inactive status"""
    try:
        result = await db.execute(select(models.User).filter(models.User.id == user_id))
        user = result.scalar_one_or_none()
        
        if not user:
            return {"success": False, "error": "User not found"}, 404
        
        # If is_active not provided, toggle current status
        if request.is_active is None:
            user.is_active = not user.is_active
        else:
            user.is_active = request.is_active
        
        user.updated_at = datetime.utcnow()
        db.add(user)
        await db.commit()
        await db.refresh(user)
        
        status_text = "activated" if user.is_active else "deactivated"
        return {
            "success": True,
            "message": f"User account {status_text} successfully",
            "data": {
                "id": user.id,
                "email": user.email,
                "is_active": user.is_active,
                "updated_at": user.updated_at
            }
        }
    except Exception as e:
        await db.rollback()
        log.error(f"Error toggling user status: {e}")
        return {"success": False, "error": str(e)}, 500


@app.post("/api/admin/users/{user_id}/admin-access/toggle")
async def toggle_user_admin_access(
    user_id: int,
    request: AdminAccessToggleRequest,
    db: SessionDep,
    current_admin: User = Depends(get_current_admin_user)
):
    """Grant or revoke admin access for a user"""
    try:
        result = await db.execute(select(models.User).filter(models.User.id == user_id))
        user = result.scalar_one_or_none()
        
        if not user:
            return {"success": False, "error": "User not found"}, 404
        
        # Prevent removing admin access from the current admin
        if user.id == current_admin.id and request.is_admin == False:
            return {"success": False, "error": "Cannot revoke your own admin access"}, 400
        
        # If is_admin not provided, toggle current status
        if request.is_admin is None:
            user.is_admin = not user.is_admin
        else:
            user.is_admin = request.is_admin
        
        user.updated_at = datetime.utcnow()
        db.add(user)
        await db.commit()
        await db.refresh(user)
        
        access_text = "granted" if user.is_admin else "revoked"
        return {
            "success": True,
            "message": f"Admin access {access_text} for {user.email}",
            "data": {
                "id": user.id,
                "email": user.email,
                "is_admin": user.is_admin,
                "updated_at": user.updated_at
            }
        }
    except Exception as e:
        await db.rollback()
        log.error(f"Error toggling admin access: {e}")
        return {"success": False, "error": str(e)}, 500


@app.get("/api/admin/users")
async def get_all_users(
    db: SessionDep,
    current_admin: User = Depends(get_current_admin_user),
    skip: int = 0,
    limit: int = 100
):
    """Get all users with pagination and accurate balance from ledger"""
    try:
        # Use admin_service.get_all_users which uses BalanceServiceLedger for accurate balances
        users = await admin_service.get_all_users(db, skip=skip, limit=limit)
        return {
            "success": True,
            "data": users
        }
    except Exception as e:
        log.error(f"Error fetching users: {e}")
        return {"success": False, "error": str(e)}, 500


@app.post("/api/admin/users/{user_id}/fund")
async def fund_user_account(
    user_id: int,
    request: FundUserRequest,
    db: SessionDep,
    current_admin: User = Depends(get_current_admin_user)
):
    """Fund a user account from System Reserve (admin only)"""
    try:
        result = await admin_service.fund_user_account(db, request, current_admin.id)
        return {"success": True, "message": result.message, "data": result.model_dump()}
    except ValueError as e:
        return {"success": False, "error": str(e)}, 400
    except Exception as e:
        log.error(f"Error funding user: {e}")
        return {"success": False, "error": str(e)}, 500


@app.get("/api/admin/fund")
async def get_fund_operations(
    db: SessionDep,
    current_admin: User = Depends(get_current_admin_user),
    user_id: int = None
):
    """Get fund operation history (admin only)"""
    try:
        result = await admin_service.get_fund_operations(db, user_id=user_id)
        return {"success": True, "data": result}
    except Exception as e:
        log.error(f"Error fetching fund operations: {e}")
        return {"success": False, "error": str(e)}, 500


@app.post("/api/admin/kyc/{submission_id}/approve")
async def approve_kyc_submission(
    submission_id: int,
    db: SessionDep,
    current_admin: User = Depends(get_current_admin_user)
):
    """Approve KYC submission (admin only)"""
    try:
        result = await admin_service.approve_kyc(db, submission_id)
        return {"success": True, "data": result}
    except ValueError as e:
        return {"success": False, "error": str(e)}, 404
    except Exception as e:
        log.error(f"Error approving KYC: {e}")
        return {"success": False, "error": str(e)}, 500


@app.post("/api/admin/kyc/{submission_id}/reject")
async def reject_kyc_submission(
    submission_id: int,
    db: SessionDep,
    current_admin: User = Depends(get_current_admin_user),
    reason: str = ""
):
    """Reject KYC submission (admin only)"""
    try:
        result = await admin_service.reject_kyc(db, submission_id, reason)
        return {"success": True, "data": result}
    except ValueError as e:
        return {"success": False, "error": str(e)}, 404
    except Exception as e:
        log.error(f"Error rejecting KYC: {e}")
        return {"success": False, "error": str(e)}, 500


# --- Admin Loan Management Endpoints ---
@app.get("/api/admin/data/loans/pending")
async def fetch_admin_pending_loans(db: SessionDep, current_admin: User = Depends(get_current_admin_user), skip: int = 0, limit: int = 100):
    """Fetch pending loan applications for admin review"""
    try:
        result = await db.execute(
            select(models.Loan)
            .filter(models.Loan.status == "pending")
            .offset(skip)
            .limit(limit)
        )
        loans = result.scalars().all()
        return {"success": True, "data": loans}
    except Exception as e:
        log.error(f"Error fetching pending loans: {e}")
        return {"success": False, "error": str(e)}, 500


@app.post("/api/admin/loans/{loan_id}/approve")
async def approve_loan_application(
    loan_id: int,
    db: SessionDep,
    current_admin: User = Depends(get_current_admin_user),
    interest_rate: float = 0.0,
    monthly_payment: float = 0.0
):
    """Approve a pending loan application and set terms"""
    try:
        result = await db.execute(select(models.Loan).filter(models.Loan.id == loan_id))
        loan = result.scalar_one_or_none()
        
        if not loan:
            return {"success": False, "error": "Loan not found"}, 404
        
        if loan.status != "pending":
            return {"success": False, "error": f"Loan status is {loan.status}, not pending"}, 400
        
        # Update loan with approval details
        loan.status = "approved"
        loan.interest_rate = interest_rate
        loan.monthly_payment = monthly_payment or (loan.amount / loan.term_months)
        loan.approved_at = datetime.utcnow()
        
        db.add(loan)
        await db.commit()
        await db.refresh(loan)
        
        return {"success": True, "data": loan}
    except Exception as e:
        await db.rollback()
        log.error(f"Error approving loan: {e}")
        return {"success": False, "error": str(e)}, 500


@app.post("/api/admin/loans/{loan_id}/reject")
async def reject_loan_application(
    loan_id: int,
    db: SessionDep,
    current_admin: User = Depends(get_current_admin_user),
    reason: str = ""
):
    """Reject a pending loan application"""
    try:
        result = await db.execute(select(models.Loan).filter(models.Loan.id == loan_id))
        loan = result.scalar_one_or_none()
        
        if not loan:
            return {"success": False, "error": "Loan not found"}, 404
        
        if loan.status != "pending":
            return {"success": False, "error": f"Loan status is {loan.status}, not pending"}, 400
        
        # Update loan status to rejected
        loan.status = "rejected"
        loan.purpose = f"{loan.purpose or 'Loan application'} - Rejected: {reason}" if reason else loan.purpose
        
        db.add(loan)
        await db.commit()
        await db.refresh(loan)
        
        return {"success": True, "data": loan}
    except Exception as e:
        await db.rollback()
        log.error(f"Error rejecting loan: {e}")
        return {"success": False, "error": str(e)}, 500


@app.post("/api/admin/loans/{loan_id}/activate")
async def activate_approved_loan(
    loan_id: int,
    db: SessionDep,
    current_admin: User = Depends(get_current_admin_user)
):
    """Activate an approved loan (disburse funds to user)"""
    try:
        result = await db.execute(select(models.Loan).filter(models.Loan.id == loan_id))
        loan = result.scalar_one_or_none()
        
        if not loan:
            return {"success": False, "error": "Loan not found"}, 404
        
        if loan.status != "approved":
            return {"success": False, "error": f"Loan must be approved first, current status: {loan.status}"}, 400
        
        # Update loan to active status
        loan.status = "active"
        db.add(loan)
        await db.commit()
        await db.refresh(loan)
        
        return {"success": True, "data": loan}
    except Exception as e:
        await db.rollback()
        log.error(f"Error activating loan: {e}")
        return {"success": False, "error": str(e)}, 500

# --- Public Facing HTML Routes ---
@app.get("/api/config")
async def get_api_config():
    """
    Serves the API configuration to clients.
    Dynamically sets baseURL based on current host.
    """
    config = API_CONFIG.copy()
    
    # Update baseURL based on the request origin
    if settings.ENVIRONMENT == "production":
        config["baseURL"] = settings.API_URL or "https://api.example.com"
    else:
        # For development, use the current domain
        config["baseURL"] = "http://localhost:8000"
    
    return config

@app.get("/signin")
async def signin_page(request: Request, db_session: SessionDep):
    """Signin page - redirects logged-in users back to dashboard (locks them in)."""
    # Check if user is already logged in
    try:
        token = request.cookies.get("access_token")
        if token:
            # Token exists, verify it's valid
            email = auth_utils.decode_access_token(token)
            if email:
                # Valid token - user is logged in, redirect to dashboard
                # Determine if user is admin
                result = await db_session.execute(select(User).filter(User.email == email))
                user = result.scalar_one_or_none()
                if user:
                    if user.is_admin:
                        return RedirectResponse(url="/user/admin/dashboard", status_code=status.HTTP_302_FOUND)
                    else:
                        return RedirectResponse(url="/user/dashboard", status_code=status.HTTP_302_FOUND)
    except Exception:
        # Token invalid, user not logged in - fall through to serve signin page
        pass
    
    # User not logged in, serve signin page
    return FileResponse("static/signin.html")

@app.get("/signup")
async def signup_page(request: Request, db_session: SessionDep):
    """Signup page - redirects logged-in users back to dashboard (locks them in)."""
    # Check if user is already logged in
    try:
        token = request.cookies.get("access_token")
        if token:
            # Token exists, verify it's valid
            email = auth_utils.decode_access_token(token)
            if email:
                # Valid token - user is logged in, redirect to dashboard
                # Determine if user is admin
                result = await db_session.execute(select(User).filter(User.email == email))
                user = result.scalar_one_or_none()
                if user:
                    if user.is_admin:
                        return RedirectResponse(url="/user/admin/dashboard", status_code=status.HTTP_302_FOUND)
                    else:
                        return RedirectResponse(url="/user/dashboard", status_code=status.HTTP_302_FOUND)
    except Exception:
        # Token invalid, user not logged in - fall through to serve signup page
        pass
    
    # User not logged in, serve signup page
    return FileResponse("static/signup.html")

@app.get("/forgot-password")
async def forgot_password_page(request: Request, db_session: SessionDep):
    """Forgot password page - redirects logged-in users back to dashboard (locks them in)."""
    # Check if user is already logged in
    try:
        token = request.cookies.get("access_token")
        if token:
            # Token exists, verify it's valid
            email = auth_utils.decode_access_token(token)
            if email:
                # Valid token - user is logged in, redirect to dashboard
                # Determine if user is admin
                result = await db_session.execute(select(User).filter(User.email == email))
                user = result.scalar_one_or_none()
                if user:
                    if user.is_admin:
                        return RedirectResponse(url="/user/admin/dashboard", status_code=status.HTTP_302_FOUND)
                    else:
                        return RedirectResponse(url="/user/dashboard", status_code=status.HTTP_302_FOUND)
    except Exception:
        # Token invalid, user not logged in - fall through to serve forgot password page
        pass
    
    # User not logged in, serve forgot password page
    return FileResponse("forgot_password.html")

@app.get("/logout")
async def logout_page(request: Request):
    """Logs out the user by clearing the access token cookie and redirecting to signin."""
    response = RedirectResponse(url="/signin", status_code=status.HTTP_303_SEE_OTHER)
    response.delete_cookie(key="access_token", path="/")
    return response


# --- Held Funds & Balance Endpoints ---

@app.get("/api/user/held-funds")
async def get_user_held_funds(
    current_user: User = Depends(get_current_user),
    db: SessionDep = None
):
    """
    Get held funds summary for current user.
    
    Held funds = pending + blocked transactions (not yet settled)
    Available balance = completed transactions only (RULE 3)
    
    Returns: {
        'available_balance': float (completed transactions only),
        'held_funds': float (pending + blocked),
        'total_funds': float (available + held),
        'pending_count': int (pending transactions),
        'blocked_count': int (blocked transactions)
    }
    
    User sees this to understand why balance may be lower than expected.
    Blocked transactions often occur due to missing KYC or account issues.
    """
    try:
        from balance_service_ledger import BalanceServiceLedger
        
        summary = await BalanceServiceLedger.get_user_fund_summary(db, current_user.id)
        
        return {
            "success": True,
            "data": summary
        }
    except Exception as e:
        log.error(f"Error fetching held funds: {e}")
        return {"success": False, "error": str(e)}, 500


@app.get("/api/admin/held-funds")
async def get_admin_held_funds(
    user_id: int = None,
    db: SessionDep = None,
    current_admin: User = Depends(get_current_admin_user)
):
    """
    Get held funds for all users or specific user (admin only).
    
    Admin endpoint to monitor:
    - How much money is pending/blocked across the platform
    - How many transactions are held
    - Per-user breakdown if user_id provided
    
    Query params:
    - user_id: Optional. If provided, get held funds for specific user only.
    
    Returns: {
        'data': [
            {
                'user_id': int,
                'user_email': str,
                'available_balance': float,
                'held_funds': float,
                'total_funds': float,
                'pending_count': int,
                'blocked_count': int
            }
        ]
    }
    """
    try:
        from balance_service_ledger import BalanceServiceLedger
        from sqlalchemy import select
        
        if user_id:
            # Get for specific user
            user = await db.get(User, user_id)
            if not user:
                return {"success": False, "error": f"User {user_id} not found"}, 404
            
            summary = await BalanceServiceLedger.get_user_fund_summary(db, user_id)
            return {
                "success": True,
                "data": [
                    {
                        "user_id": user.id,
                        "user_email": user.email,
                        **summary
                    }
                ]
            }
        else:
            # Get for all users
            result = await db.execute(select(User))
            users = result.scalars().all()
            
            data = []
            for user in users:
                summary = await BalanceServiceLedger.get_user_fund_summary(db, user.id)
                data.append({
                    "user_id": user.id,
                    "user_email": user.email,
                    **summary
                })
            
            return {
                "success": True,
                "data": data
            }
    except Exception as e:
        log.error(f"Error fetching admin held funds: {e}")
        return {"success": False, "error": str(e)}, 500


@app.get("/api/admin/fund-summary")
async def get_admin_fund_summary(
    db: SessionDep = None,
    current_admin: User = Depends(get_current_admin_user)
):
    """
    Get platform-wide fund summary (admin dashboard).
    
    Shows:
    - Total available balance (all completed transactions)
    - Total held funds (all pending + blocked)
    - Total funds in system
    - Number of users with held funds
    - Number of blocked transactions awaiting resolution
    
    Returns: {
        'total_available': float,
        'total_held': float,
        'total_in_system': float,
        'users_with_held_funds': int,
        'blocked_transaction_count': int,
        'pending_transaction_count': int
    }
    """
    try:
        from sqlalchemy import select, func, and_
        from balance_service_ledger import BalanceServiceLedger
        
        # Get all users
        result = await db.execute(select(User))
        users = result.scalars().all()
        
        total_available = 0.0
        total_held = 0.0
        users_with_held = set()
        
        for user in users:
            balance = await BalanceService.get_user_balance(db, user.id)
            held = await BalanceService.get_user_held_funds(db, user.id)
            total_available += balance
            total_held += held
            if held > 0:
                users_with_held.add(user.id)
        
        # Count blocked and pending transactions
        blocked_result = await db.execute(
            select(func.count(models.Transaction.id)).where(
                models.Transaction.status == "blocked"
            )
        )
        blocked_count = blocked_result.scalar() or 0
        
        pending_result = await db.execute(
            select(func.count(models.Transaction.id)).where(
                models.Transaction.status == "pending"
            )
        )
        pending_count = pending_result.scalar() or 0
        
        return {
            "success": True,
            "data": {
                "total_available": total_available,
                "total_held": total_held,
                "total_in_system": total_available + total_held,
                "users_with_held_funds": len(users_with_held),
                "blocked_transaction_count": int(blocked_count),
                "pending_transaction_count": int(pending_count)
            }
        }
    except Exception as e:
        log.error(f"Error fetching fund summary: {e}")
        return {"success": False, "error": str(e)}, 500


# --- Static Files Mount ---
# This should be the LAST mount.
# The `html=True` argument makes it so that paths like "/" or "/about"
# will automatically serve "static/index.html" or "static/about.html".
app.mount("/", StaticFiles(directory="static", html=True), name="public")

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)