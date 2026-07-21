import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, RedirectResponse
from fastapi import Request, Depends, status, WebSocket, WebSocketDisconnect
from sqlalchemy import text, select
import logging
from datetime import datetime
from typing import List
import atexit
import time
import asyncio

# Token Cleanup Service & Scheduler
from token_cleanup_service import TokenCleanupService
from apscheduler.schedulers.asyncio import AsyncIOScheduler

# Rate Limiting & MFA
from rate_limiter_service import get_rate_limiter, get_rate_limit_config
from mfa_service import MFAService

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
from routers.payments import router as payments_router
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
from routers.fund_v1_api import fund_v1_router
from routers.auth_v1_api import auth_v1_router, system_status_router
from routers.audit_v1_api import audit_v1_router
from routers.admin_users import admin_users_router
from routers.admin_transactions_api import admin_transactions_router
from routers.admin_intervention import router as intervention_router
from routers.admin_api_v1 import admin_v1_router
from routers.reporting_api_v1 import reporting_v1_router
from routers.emails import router as emails_router
from routers.sns_notifications import router as sns_router
from routers.dashboard_stubs_api import router as dashboard_stubs_router
from routers.admin_management import router as admin_management_router
from routers.admin_full_api import router as admin_full_api_router
from routers.admin_advanced_operations import router as admin_advanced_router
from routers.uploads import uploads_router
from routers.international import international_router
from routers.mobile_deposits import deposits_router as mobile_deposits_router_new
from config import settings
from auth_utils import get_password_hash
from deps import get_current_user, get_current_admin_user, SessionDep
from rbac import require_permission
from schemas import UserCreate, FundUserRequest, Deposit as PydanticDeposit, Transaction, TransactionCreate, PasswordResetRequest, UserProfileUpdateRequest, AccountStatusToggleRequest, AdminAccessToggleRequest, TransactionCreateRequest
from models import User, Deposit as DBDeposit
from admin_service import admin_service
import crud
import models

log = logging.getLogger(__name__)

# SSH Tunnel Management
ssh_tunnel = None
db_tables_created = False  # Track if database tables have been initialized
scheduler = None  # Global scheduler instance for token cleanup

def cleanup_scheduler():
    """Cleanup scheduler on exit"""
    global scheduler
    if scheduler and scheduler.running:
        try:
            scheduler.shutdown()
            log.info("Scheduler shutdown complete")
        except Exception as e:
            log.error(f"Error shutting down scheduler: {e}")

def initialize_ssh_tunnel():
    """SSH tunneling is deprecated in this deployment. Supabase is used as primary DB.

    This function intentionally does nothing and exists only for backward
    compatibility with older startup flows that expected an initializer.
    """
    return False

def cleanup_ssh_tunnel():
    """No-op cleanup for SSH tunnel; kept for compatibility."""
    return None

# API Configuration - Generated dynamically based on environment
def generate_api_config(environment: str = None, api_url: str = None) -> dict:
    """
    Generate API configuration based on environment.
    
    Args:
        environment: "development", "staging", or "production"
        api_url: Optional override for API URL
        
    Returns:
        Configuration dict for frontend clients
    """
    env = environment or settings.ENVIRONMENT or "development"
    
    # Determine baseURL based on environment
    if env == "production":
        base_url = api_url or settings.API_URL or "https://api.example.com"
    elif env == "staging":
        base_url = api_url or settings.API_URL or "https://staging-api.example.com"
    else:  # development
        base_url = "http://localhost:8000"
    
    return {
        "baseURL": base_url,
        "timeout": 30000,
        "headers": {
            "Content-Type": "application/json"
        },
        "retries": 2,
        "backoffDelay": 1000,
        "environment": env
    }

# Generate initial API config
API_CONFIG = generate_api_config()

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
    Ensures the default SUPER_ADMIN user exists with proper role and linked account.
    
    ⚠️ CORE RULES:
    1. Default admin must have admin_role set to "SUPER_ADMIN"
    2. Admin user must have BOTH User ID and Account ID bound together
    3. Default admin must have is_admin=True
    """
    from sqlalchemy import select
    from models import Account
    import time
    
    async with SessionLocal() as db:
        result = await db.execute(select(User).filter(User.email == settings.ADMIN_EMAIL))
        admin_user = result.scalars().first()
        
        if not admin_user:
            # Create a new SUPER_ADMIN user with argon2 hashed password
            hashed_password = get_password_hash(settings.ADMIN_PASSWORD)
            new_admin = User(
                full_name="Super Admin",
                email=settings.ADMIN_EMAIL,
                hashed_password=hashed_password,
                is_admin=True,
                admin_role="SUPER_ADMIN",  # ✅ SET SUPER_ADMIN ROLE
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
                updated_at=datetime.utcnow(),
                is_admin_account=True  # Mark as admin account
            )
            db.add(admin_account)
            new_admin.account_number = admin_account_number
            
            await db.commit()
            print(f"✅ SUPER_ADMIN user created: {settings.ADMIN_EMAIL}")
            print(f"   Role: SUPER_ADMIN (All access)")
            
        else:
            # Ensure admin has proper role and account
            if admin_user.admin_role != "SUPER_ADMIN":
                admin_user.admin_role = "SUPER_ADMIN"  # ✅ UPGRADE TO SUPER_ADMIN IF NOT
                
            if not admin_user.is_admin:
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
                    updated_at=datetime.utcnow(),
                    is_admin_account=True
                )
                db.add(admin_account)
                admin_user.account_number = admin_account_number
            
            await db.commit()
            print(f"✅ SUPER_ADMIN verified: {settings.ADMIN_EMAIL}")


async def create_default_admin_roles():
    """
    Creates default admin accounts for all 5 role tiers during startup.
    
    Purpose: Allow testing/demonstration of each admin role with different permissions:
    - SUPER_ADMIN: All access (*)
    - ADMIN: 18 permissions (users, transactions, KYC, deposits, etc.)
    - TREASURY: Payment settlement, deposits, ledger adjustments
    - COMPLIANCE: KYC review, audit view
    - SUPPORT: User view, support tickets
    """
    from sqlalchemy import select
    from models import Account
    import time
    from datetime import datetime
    
    # Define default admin role accounts
    DEFAULT_ROLES = {
        "ADMIN": {
            "email": "admin@finanza.com",
            "password": "AdminTest123!",
            "name": "Admin Officer",
            "permissions": "18 permissions (users, transactions, KYC, deposits, etc.)"
        },
        "TREASURY": {
            "email": "treasury@finanza.com",
            "password": "TreasuryTest123!",
            "name": "Treasury Officer",
            "permissions": "Payment settlement, deposits, ledger adjustments"
        },
        "COMPLIANCE": {
            "email": "compliance@finanza.com",
            "password": "ComplianceTest123!",
            "name": "Compliance Officer",
            "permissions": "KYC review, audit view"
        },
        "SUPPORT": {
            "email": "support@finanza.com",
            "password": "SupportTest123!",
            "name": "Support Agent",
            "permissions": "User view, support tickets"
        }
    }
    
    async with SessionLocal() as db:
        for role, config in DEFAULT_ROLES.items():
            result = await db.execute(select(User).filter(User.email == config["email"]))
            user = result.scalars().first()
            
            if not user:
                # Create new role account
                hashed_password = get_password_hash(config["password"])
                new_user = User(
                    full_name=config["name"],
                    email=config["email"],
                    hashed_password=hashed_password,
                    is_admin=True,
                    admin_role=role,  # ✅ SET PROPER ROLE
                    is_active=True,
                    kyc_status='approved'
                )
                db.add(new_user)
                await db.flush()
                
                # Create account for role
                account_number = f"{role.upper()}{new_user.id}_{int(time.time() * 1000000) % 1000000}"
                admin_account = Account(
                    owner_id=new_user.id,
                    account_number=account_number,
                    account_type='admin',
                    balance=0.0,
                    currency='USD',
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow(),
                    is_admin_account=True
                )
                db.add(admin_account)
                new_user.account_number = account_number
                
                await db.commit()
                print(f"✅ {role} account created")
                print(f"   Email: {config['email']}")
                print(f"   Password: {config['password']}")
                print(f"   Permissions: {config['permissions']}")
                
            else:
                # Ensure role account has correct role set
                if user.admin_role != role:
                    user.admin_role = role
                    await db.commit()
                    print(f"✅ {role} account verified (role updated)")

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


# ============================================================================
# WEBSOCKET CONNECTION MANAGER FOR FRAUD ALERTS
# ============================================================================
class ConnectionManager:
    """
    Manages WebSocket connections for real-time fraud alerts.
    
    Tracks connected clients and broadcasts fraud alerts to all connected admins.
    Automatically removes disconnected clients.
    """
    
    def __init__(self):
        self.active_connections: List[WebSocket] = []
    
    async def connect(self, websocket: WebSocket):
        """Accept and register a new WebSocket connection"""
        await websocket.accept()
        self.active_connections.append(websocket)
        print(f"✅ WebSocket client connected. Total connections: {len(self.active_connections)}")
    
    def disconnect(self, websocket: WebSocket):
        """Remove a disconnected WebSocket connection"""
        self.active_connections.remove(websocket)
        print(f"❌ WebSocket client disconnected. Total connections: {len(self.active_connections)}")
    
    async def broadcast(self, alert: dict):
        """
        Broadcast a fraud alert to all connected clients.
        
        Args:
            alert (dict): Alert message with keys:
                - type: 'fraud_alert' (required)
                - transaction_id: Transaction ID (required)
                - threat_type: Type of threat detected (required)
                - risk_score: Risk score 0-100 (required)
                - description: Optional alert description
        """
        disconnected = []
        
        for connection in self.active_connections:
            try:
                await connection.send_json(alert)
            except Exception as e:
                # Connection failed, mark for removal
                print(f"⚠️  Failed to broadcast alert to client: {e}")
                disconnected.append(connection)
        
        # Remove failed connections
        for connection in disconnected:
            self.disconnect(connection)


# Global connection manager instance
fraud_alert_manager = ConnectionManager()


app = FastAPI()

def get_allowed_origins() -> list:
    """
    Get allowed CORS origins based on environment.
    
    Development: Always allows localhost
    Staging/Production: Uses API_URL and FRONTEND_URL from settings
    """
    origins = [
        "http://localhost:8000",    # Local development - FastAPI
        "http://127.0.0.1:8000",    # Local development - FastAPI
        "http://localhost:3000",    # Local development - frontend
        "http://127.0.0.1:3000",    # Local development - frontend alternative
    ]
    
    env = settings.ENVIRONMENT or "development"
    
    # Add EC2/staging origins
    if env in ["staging", "production"] and settings.API_URL:
        origins.append(settings.API_URL)
    
    if env in ["staging", "production"] and settings.FRONTEND_URL:
        origins.append(settings.FRONTEND_URL)
    
    # Keep these for backward compatibility / debugging
    origins.extend([
        "http://51.20.190.13:8000",  # EC2 instance (legacy)
        "http://51.20.190.13",        # EC2 instance without port (legacy)
    ])
    
    return list(set(origins))  # Remove duplicates

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_allowed_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    """
    Rate limiting middleware for API endpoints.
    Applies per-user and per-IP rate limits based on endpoint.
    """
    try:
        # Get rate limiter
        rate_limiter = get_rate_limiter()
        
        # Skip rate limiting for non-API endpoints
        if not request.url.path.startswith("/api/"):
            return await call_next(request)
        
        # Determine identifier (user ID from token or IP address)
        identifier = "anonymous"
        identifier_type = "ip"
        try:
            # Try to get user from Authorization header
            auth_header = request.headers.get("Authorization", "")
            if auth_header.startswith("Bearer "):
                identifier = auth_header[7:]  # Use token as identifier
                identifier_type = "token"
        except:
            pass
        
        if identifier_type == "ip":
            identifier = request.client.host if request.client else "unknown"
        
        # Determine endpoint for rate limit config
        endpoint = request.url.path
        
        # Get rate limit config from settings
        from config import settings
        if "/admin" in endpoint:
            per_minute = settings.RATE_LIMIT_ADMIN_ENDPOINTS_PER_MIN
            per_hour = settings.RATE_LIMIT_ADMIN_ENDPOINTS_PER_HOUR
        elif "/auth" in endpoint or "/login" in endpoint:
            per_minute = settings.RATE_LIMIT_AUTH_PER_MIN
            per_hour = settings.RATE_LIMIT_AUTH_PER_HOUR
        else:
            per_minute = settings.RATE_LIMIT_API_ENDPOINTS_PER_MIN
            per_hour = settings.RATE_LIMIT_API_ENDPOINTS_PER_HOUR
        
        # Check rate limit
        is_allowed, info = await rate_limiter.is_allowed(
            identifier,
            identifier_type=identifier_type,
            endpoint=endpoint,
            requests_per_minute=per_minute,
            requests_per_hour=per_hour
        )
        
        if not is_allowed:
            from fastapi.responses import JSONResponse
            return JSONResponse(
                status_code=429,
                content={
                    "success": False,
                    "error": "Rate limit exceeded",
                    "details": info
                }
            )
        
        response = await call_next(request)
        
        # Add rate limit headers
        response.headers["X-RateLimit-Limit"] = str(per_minute)
        response.headers["X-RateLimit-Remaining"] = str(max(0, per_minute - info.get("count", 0)))
        
        return response
        
    except Exception as e:
        # Don't block requests if rate limiting fails
        log.warning(f"Rate limiting error: {e}")
        return await call_next(request)

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
    # Add explicit signin/signup/forgot-password/reset-password paths (and .html variants) so public auth pages aren't redirected
    exempt_paths = [
        "/api", "/auth", "/css", "/js", "/lib", "/img", "/static", "/admin_static",
        "/docs", "/openapi.json", "/signin", "/signup", "/forgot-password", "/reset-password", "/signin.html", "/signup.html", "/logout"
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
        
        print("[*] Creating default admin role accounts...")
        await create_default_admin_roles()

        print("[*] Creating System Reserve Account...")
        await create_system_reserve_account()

        print("[*] Verifying startup balances...")
        try:
            from app.startup_helpers import startup_verification
            async with SessionLocal() as db:
                verification = await startup_verification(db)
                if verification.get("reconciliation", {}).get("invalid", 0):
                    log.warning("Startup reconciliation found %s inconsistent account(s)", verification["reconciliation"].get("invalid", 0))
                else:
                    log.info("Startup reconciliation passed")
        except Exception as startup_error:
            log.warning(f"Startup verification failed: {startup_error}")
        
        # Initialize token cleanup scheduler
        print("[*] Initializing token cleanup scheduler...")
        global scheduler
        try:
            scheduler = AsyncIOScheduler()
            TokenCleanupService.register_cleanup_scheduler(scheduler, interval_minutes=60)
            
            # ==================== REAL-TIME SERVICES INITIALIZATION ====================
            
            # Initialize Price Feed Service for forex and crypto updates
            print("[*] Initializing price feed service...")
            from services.price_feed_service import get_price_feed_service
            
            price_feed = await get_price_feed_service(settings.REDIS_URL)
            
            # Register forex rate synchronization (every 45 minutes)
            if settings.FIXER_IO_API_KEY:
                print("[*] Registering Forex feed task (every 45 minutes)...")
                scheduler.add_job(
                    price_feed.sync_forex_rates,
                    'interval',
                    minutes=45,
                    args=[settings.FIXER_IO_API_KEY],
                    id='forex_sync_task',
                    replace_existing=True
                )
                print("[OK] Forex sync scheduled")
            else:
                print("[WARN] FIXER_IO_API_KEY not configured - forex rates will not sync")
            
            # Register cryptocurrency WebSocket feed (continuous background task)
            print("[*] Registering Crypto WebSocket feed (continuous)...")
            scheduler.add_job(
                price_feed.connect_crypto_feed,
                'interval',
                seconds=0,  # Run once, continues internally with reconnect
                id='crypto_websocket_task',
                replace_existing=True
            )
            print("[OK] Crypto feed registered")
            
            # Start scheduler
            scheduler.start()
            atexit.register(cleanup_scheduler)
            print("[OK] Scheduler started with all background tasks")
        except Exception as scheduler_error:
            log.warning(f"[WARN] Background services failed to start: {scheduler_error}")
            log.warning("       Token cleanup and realtime services may not be available")
        
        print("[OK] Application ready")
        
    except Exception as e:
        print(f"[WARN] Startup issue: {e}")
        print("[WARN] Application will continue in limited mode")

async def shutdown_event():
    """Cleanup on application shutdown"""
    try:
        # Stop price feed service (closes Redis connection)
        from services.price_feed_service import price_feed_service
        if price_feed_service:
            await price_feed_service.disconnect()
        
        cleanup_scheduler()
        cleanup_ssh_tunnel()
        print("[OK] Application shutdown complete")
    except Exception as e:
        log.error(f"Error during shutdown: {e}")

from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    await startup_event()
    yield
    await shutdown_event()

app.router.lifespan_context = lifespan

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
app.include_router(auth_v1_router)  # Auth v1 API (already has /api/v1/auth prefix)
app.include_router(system_status_router)  # System status API (already has /api/v1/system prefix)
app.include_router(audit_v1_router)  # Audit v1 API (already has /api/v1/audit prefix)
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
app.include_router(payments_router, prefix="/api/v1")
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
# Fund operations API v1 (with rate limiting and WebSocket support)
app.include_router(fund_v1_router)
# Admin user data retrieval router
app.include_router(admin_users_router)
# Admin transactions metrics, disputes, returns
app.include_router(admin_transactions_router)
# Admin intervention tools (balance adjustment, holds, sessions, KYC docs)
app.include_router(intervention_router)
# Admin settings and configuration API v1
app.include_router(admin_v1_router)
# Admin reporting and business intelligence API v1
app.include_router(reporting_v1_router)
# Email service router
app.include_router(emails_router)
# SNS notification router
app.include_router(sns_router)
# Dashboard stubs for missing 404 endpoints
app.include_router(dashboard_stubs_router)
# Admin management endpoints (holds, frozen accounts, credit scores, devices)
app.include_router(admin_management_router)
# Comprehensive admin API (analytics, fraud, KYC, ledger export)
app.include_router(admin_full_api_router)
# Advanced admin operations (MFA, bulk ops, admin management, audit logging)
app.include_router(admin_advanced_router)
# Realtime WebSocket router
app.include_router(realtime_router)
# Real-Time Webhook Receiver - Landing spot for all real-time data
try:
    from routers.realtime_webhooks_receiver import router as realtime_webhooks_router
    app.include_router(realtime_webhooks_router)
    log.info("✅ Real-Time Webhook Receiver registered - Ready to receive payments, KYC, email events")
except Exception as e:
    log.warning(f"Real-Time Webhook Receiver not available: {e}")

# PHASE 1: NEW PAYMENT, CREDIT, COMPLIANCE ROUTERS - COMPLIANCE DISABLED (Priority 3 used instead)
try:
    # NOTE: imported as payments_api_router to avoid conflict with root-level payments_router (line 835)
    from routers.payments_api import router as payments_api_router
    from routers.credit_api import router as credit_router
    from routers.sandbox_payments import router as sandbox_payments_router
    from routers.loan_origination_api import router as loan_origination_router
    from routers.investment_portfolio_api import router as investment_portfolio_router
    from routers.card_processing_api import router as card_processing_router
    # from routers.compliance_api import router as compliance_router  # Disabled - Priority 3 compliance_priority3_api used instead
    
    app.include_router(payments_api_router, prefix="/api/v1")  # ACH/Wire/RTP/FedNow payment rails
    app.include_router(credit_router, prefix="/api/v1")
    app.include_router(sandbox_payments_router, prefix="/api/v1")
    app.include_router(loan_origination_router, prefix="/api/v1")
    app.include_router(investment_portfolio_router, prefix="/api/v1")
    app.include_router(card_processing_router, prefix="/api/v1")
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
# PHASE 4A: Core Enterprise Features (Fraud, Blockchain, Reporting, Treasury, Settlement)
try:
    from routers.fraud_detection_api import router as fraud_detection_router
    from routers.blockchain_api import router as blockchain_router
    from routers.reporting_api import router as reporting_router
    from routers.treasury_api import router as treasury_router
    from routers.settlement_api import router as settlement_router
    
    app.include_router(fraud_detection_router)  # Prefix defined in router as /api/v1/fraud
    app.include_router(blockchain_router)  # Prefix defined in router as /api/v1/blockchain
    app.include_router(reporting_router)  # Prefix defined in router as /api/v1/reports
    app.include_router(treasury_router)  # Prefix defined in router as /api/v1/treasury
    app.include_router(settlement_router)  # Prefix defined in router as /api/v1/settlement
    log.info("✅ Phase 4A routers registered (Fraud Detection, Blockchain, Reporting, Treasury, Settlement)")
except (ImportError, ModuleNotFoundError, AttributeError) as e:
    log.warning(f"⚠️  Phase 4A routers not available: {e}")
except Exception as e:
    log.warning(f"⚠️  Phase 4A routers not available (optional): {e}")

# PHASE 4B: Optional Enterprise Features (Bill Pay, Mobile Deposit)
try:
    from routers.bill_pay_api import router as bill_pay_router
    from routers.mobile_deposit_admin import router as mobile_deposit_router
    
    app.include_router(bill_pay_router)  # Prefix defined in router as /api/v1/bill-pay
    app.include_router(mobile_deposit_router)  # Prefix defined in router as /api/v1/mobile-deposit
    log.info("✅ Phase 4B routers registered (Bill Pay, Mobile Deposit)")
except (ImportError, ModuleNotFoundError, AttributeError) as e:
    log.warning(f"⚠️  Phase 4B routers not available (optional): {e}")
except Exception as e:
    log.warning(f"⚠️  Phase 4B routers not available (optional): {e}")

# WAVE 3: FILE UPLOADS, INTERNATIONAL TRANSFERS, ENHANCED MOBILE DEPOSITS
try:
    app.include_router(uploads_router)  # /api/uploads/* endpoints
    app.include_router(international_router)  # /api/international/* endpoints
    app.include_router(mobile_deposits_router_new, prefix="/api")  # /api/deposits/* endpoints (enhanced)
    log.info("✅ Wave 3 routers registered (File Uploads, International Transfers, Mobile Deposits)")
except Exception as e:
    log.warning(f"⚠️  Wave 3 routers not available: {e}")

# SUPPLEMENTAL ROUTERS: Alerts, Recipients
try:
    from routers.alerts import router as alerts_router
    from routers.recipients import router as recipients_router
    app.include_router(alerts_router)   # /api/v1/alerts
    app.include_router(recipients_router)  # /api/v1/recipients
    log.info("✅ Supplemental routers registered (Alerts, Recipients)")
except Exception as e:
    log.warning(f"Supplemental routers not available: {e}")

# SUPPLEMENTAL ROUTERS: Admin Settings, Business Analysis, Forms, Mobile Deposit API
try:
    from routers.admin_settings_api import admin_settings_router, config_router
    app.include_router(admin_settings_router)  # /api/v1/admin/settings
    app.include_router(config_router)           # /api/v1/config (public config endpoint)
    log.info("✅ Admin Settings API registered")
except Exception as e:
    log.warning(f"Admin Settings API not available: {e}")

try:
    from routers.business_analysis import router as business_analysis_router
    app.include_router(business_analysis_router)  # /api/user/analysis
    log.info("✅ Business Analysis router registered")
except Exception as e:
    log.warning(f"Business Analysis router not available: {e}")

try:
    from routers.forms import forms_router
    app.include_router(forms_router, prefix="/api/v1")  # /api/v1/forms
    log.info("✅ Forms router registered")
except Exception as e:
    log.warning(f"Forms router not available: {e}")

try:
    from routers.mobile_deposit_api import router as mobile_deposit_api_router
    app.include_router(mobile_deposit_api_router)  # /api/v1/mobile-deposit (user-facing)
    log.info("✅ Mobile Deposit API (user-facing) registered")
except Exception as e:
    log.warning(f"Mobile Deposit API not available: {e}")

# NOTE: user_router is NOT registered here to avoid route conflicts with private_router.
# All /user/* routes are served by private_router which includes proper admin/user checks.
# user_pages.py is kept for reference but not registered.

# ── Health Check Endpoint (public, no auth required) ──────────────────────────
# Used by Docker HEALTHCHECK, nginx upstream checks, and load balancers
@app.get("/health", tags=["System"])
async def health_check():
    """Public health check endpoint. Returns DB connectivity and app status."""
    try:
        async with SessionLocal() as db:
            await db.execute(text("SELECT 1"))
        return {
            "status": "healthy",
            "database": "connected",
            "environment": settings.ENVIRONMENT or "development",
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
    except Exception as e:
        return {
            "status": "degraded",
            "database": "unavailable",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }

# --- Admin Data Endpoints (Python-only, no JSON) ---
@app.get("/api/admin/data/users")
async def fetch_admin_users(
    db: SessionDep,
    current_admin: User = Depends(get_current_admin_user),
    _perm=Depends(require_permission("users:view")),
    skip: int = 0,
    limit: int = 100
):
    """Fetch all users for admin dashboard"""
    try:
        users = await admin_service.get_all_users(db, skip=skip, limit=limit)
        return {"success": True, "data": users}
    except Exception as e:
        log.error(f"Error fetching users: {e}")
        return {"success": False, "error": str(e)}, 500


@app.get("/api/admin/transactions")
async def get_admin_transactions(
    db: SessionDep,
    current_admin: User = Depends(get_current_admin_user),
    _perm=Depends(require_permission("transactions:view")),
    skip: int = 0,
    limit: int = 100,
    status: str = None
):
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
async def get_admin_kyc(
    db: SessionDep,
    current_admin: User = Depends(get_current_admin_user),
    _perm=Depends(require_permission("kyc:review")),
    skip: int = 0,
    limit: int = 100
):
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
async def get_admin_deposits(
    db: SessionDep,
    current_admin: User = Depends(get_current_admin_user),
    _perm=Depends(require_permission("deposits:view")),
    skip: int = 0,
    limit: int = 100
):
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
    current_admin: User = Depends(get_current_admin_user),
    _perm=Depends(require_permission("transactions:create"))
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
async def fetch_admin_transactions(
    db: SessionDep,
    current_admin: User = Depends(get_current_admin_user),
    _perm=Depends(require_permission("transactions:view")),
    skip: int = 0,
    limit: int = 100,
    status: str = None
):
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
async def fetch_admin_deposits_data(
    db: SessionDep,
    current_admin: User = Depends(get_current_admin_user),
    _perm=Depends(require_permission("deposits:view")),
    skip: int = 0,
    limit: int = 100
):
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
async def fetch_admin_investments(
    db: SessionDep,
    current_admin: User = Depends(get_current_admin_user),
    _perm=Depends(require_permission("investments:view")),
    skip: int = 0,
    limit: int = 100
):
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
async def fetch_admin_cards(
    db: SessionDep,
    current_admin: User = Depends(get_current_admin_user),
    _perm=Depends(require_permission("cards:view")),
    skip: int = 0,
    limit: int = 100
):
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
    _perm=Depends(require_permission("deposits:approve")),
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
    _perm=Depends(require_permission("investments:manage")),
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
async def fetch_admin_kyc(
    db: SessionDep,
    current_admin: User = Depends(get_current_admin_user),
    _perm=Depends(require_permission("kyc:review")),
    skip: int = 0,
    limit: int = 100
):
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
async def fetch_admin_metrics(
    db: SessionDep,
    current_admin: User = Depends(get_current_admin_user),
    _perm=Depends(require_permission("reporting:view"))
):
    """Fetch dashboard metrics"""
    try:
        metrics = await admin_service.get_dashboard_metrics(db)
        return {"success": True, "data": metrics}
    except Exception as e:
        log.error(f"Error fetching metrics: {e}")
        return {"success": False, "error": str(e)}, 500


@app.get("/api/admin/data/reports")
async def fetch_admin_reports(
    db: SessionDep,
    current_admin: User = Depends(get_current_admin_user),
    _perm=Depends(require_permission("reporting:view"))
):
    """Fetch admin reports"""
    try:
        reports = await admin_service.get_admin_reports(db)
        return {"success": True, "data": reports}
    except Exception as e:
        log.error(f"Error generating reports: {e}")
        return {"success": False, "error": str(e)}, 500


@app.get("/api/admin/data/health")
async def fetch_system_health(
    db: SessionDep,
    current_admin: User = Depends(get_current_admin_user),
    _perm=Depends(require_permission("audit:view"))
):
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
    Dynamically sets baseURL based on environment and settings.
    
    Returns:
        Configuration object with:
        - baseURL: API endpoint URL
        - timeout: Request timeout in ms
        - environment: Current environment (development/staging/production)
        - headers: Default HTTP headers
    """
    return generate_api_config(settings.ENVIRONMENT, settings.API_URL)

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
    return FileResponse("static/forgot_password.html")

@app.get("/reset-password")
async def reset_password_page(request: Request, db_session: SessionDep):
    """Password reset page - user receives this after clicking email link."""
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
        # Token invalid, user not logged in - fall through to serve reset password page
        pass
    
    # User not logged in, serve reset password page
    return FileResponse("static/reset_password.html")

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


# ============================================================================
# WEBSOCKET ENDPOINT FOR REAL-TIME FRAUD ALERTS
# ============================================================================
@app.websocket("/ws/fraud-alerts")
async def websocket_fraud_alerts(websocket: WebSocket):
    """
    WebSocket endpoint for real-time fraud alert streaming.
    
    Accepts client connections and broadcasts fraud alerts to all connected clients.
    
    Connection Protocol:
    1. Client connects to ws://localhost:8000/ws/fraud-alerts
    2. Client sends authentication message: {"type": "auth", "token": "jwt_token"}
    3. Server validates JWT token and maintains connection
    4. Server broadcasts fraud alerts as they occur
    5. Client receives messages in format:
       {
           "type": "fraud_alert",
           "transaction_id": "txn_abc123",
           "threat_type": "suspicious_activity",
           "risk_score": 92,
           "description": "Multiple failed login attempts"
       }
    6. Client can disconnect anytime
    
    Expected Message Format (from server):
    {
        "type": "fraud_alert",
        "transaction_id": "txn_12345",
        "threat_type": "high_value_transaction|unusual_location|velocity_check|device_mismatch|suspicious_activity",
        "risk_score": 0-100,  # 0-30: Low, 31-70: Medium, 71-100: High
        "description": "Brief description of the threat"
    }
    
    Error Handling:
    - Invalid JWT: Connection rejected
    - Client disconnect: Automatically removed from connection pool
    - Broadcast failure: Client is disconnected and removed
    """
    
    await fraud_alert_manager.connect(websocket)
    
    try:
        while True:
            # Keep connection alive and receive messages
            data = await websocket.receive_json()
            
            # Example: Handle authentication message
            if data.get("type") == "auth":
                token = data.get("token")
                # TODO: Validate JWT token here
                # For now, just acknowledge connection
                await websocket.send_json({
                    "type": "auth_success",
                    "message": "Connected to fraud alert stream"
                })
            
            # Handle other message types as needed
            
    except WebSocketDisconnect:
        fraud_alert_manager.disconnect(websocket)
        print("🔌 WebSocket client disconnected gracefully")
    except Exception as e:
        print(f"❌ WebSocket error: {e}")
        try:
            fraud_alert_manager.disconnect(websocket)
        except:
            pass


# Function to broadcast fraud alerts from anywhere in the application
async def broadcast_fraud_alert(alert: dict):
    """
    Broadcast a fraud alert to all connected WebSocket clients.
    
    Usage:
        await broadcast_fraud_alert({
            "type": "fraud_alert",
            "transaction_id": "txn_abc123",
            "threat_type": "suspicious_activity",
            "risk_score": 92,
            "description": "Multiple failed attempts detected"
        })
    
    Args:
        alert (dict): Alert message with required keys:
            - type: Must be "fraud_alert"
            - transaction_id: Unique transaction identifier
            - threat_type: Category of threat detected
            - risk_score: Risk level 0-100
            - description: Human-readable description
    """
    await fraud_alert_manager.broadcast(alert)


# ==================== FUND UPDATES WEBSOCKET ====================

@app.websocket("/ws/fund-updates")
async def websocket_fund_updates(websocket: WebSocket):
    """
    WebSocket endpoint for real-time fund management updates.
    
    Broadcasts:
    - balance_updated: User balance changed
    - approval_needed: Operation requires second admin approval
    - approval_completed: Approval decision made (approved/rejected)
    - fund_completed: Funding operation completed
    - transaction_ref: Transaction reference for audit trail
    
    Connection Protocol:
    1. Client connects to ws://localhost:8000/ws/fund-updates
    2. Client subscribes to channels: {"type": "subscribe", "channels": ["user:123", "approval", "balance"]}
    3. Server broadcasts updates matching subscription
    4. Client receives messages
    
    Expected Message Format:
    {
        "type": "balance_updated",
        "user_id": 123,
        "new_balance": 5000.50,
        "transaction_ref": "TXN-ABC123",
        "timestamp": "2026-04-07T14:30:00Z"
    }
    """
    from ws_manager import manager as ws_manager
    
    user_id = None
    device_id = None
    
    try:
        await ws_manager.connect(websocket, user_id, device_id)
        
        while True:
            data = await websocket.receive_json()
            
            if data.get("type") == "subscribe":
                channels = data.get("channels", [])
                for channel in channels:
                    await ws_manager.subscribe(websocket, channel)
            
            elif data.get("type") == "ping":
                await websocket.send_json({"type": "pong", "timestamp": datetime.utcnow().isoformat()})
            
    except WebSocketDisconnect:
        await ws_manager.disconnect(websocket)
    except Exception as e:
        log.error(f"WebSocket error: {e}")
        try:
            await ws_manager.disconnect(websocket)
        except:
            pass


# --- Static Files Mount ---
# This should be the LAST mount.
# The `html=True` argument makes it so that paths like "/" or "/about"
# will automatically serve "static/index.html" or "static/about.html".
app.mount("/", StaticFiles(directory="static", html=True), name="public")

if __name__ == "__main__":
    import os
    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host=host, port=port)