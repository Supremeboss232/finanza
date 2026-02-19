# 🏗️ ARCHITECTURE DEEP DIVE - COMPLETE SYSTEM ANALYSIS

**Date**: February 13, 2026  
**Scope**: Pages, Navigation, Routes, Imports, Modules, Core, Files  
**Level**: Enterprise Banking System (FastAPI + PostgreSQL + React-style Frontend)

---

## 📑 TABLE OF CONTENTS

1. [System Architecture Overview](#system-architecture-overview)
2. [Frontend Structure & Navigation](#frontend-structure--navigation)
3. [Backend API Routes & Structure](#backend-api-routes--structure)
4. [Database & Models](#database--models)
5. [Core Services & Business Logic](#core-services--business-logic)
6. [Authentication & Security](#authentication--security)
7. [Data Flow Patterns](#data-flow-patterns)
8. [Module Dependency Graph](#module-dependency-graph)
9. [Import Analysis](#import-analysis)
10. [File Organization Summary](#file-organization-summary)

---

## SYSTEM ARCHITECTURE OVERVIEW

### Three-Tier Architecture

```
┌─────────────────────────────────────────────────────────┐
│  🎨 PRESENTATION LAYER (Frontend)                        │
│  - Static HTML pages (/static)                           │
│  - User pages (/private/user)                            │
│  - Admin dashboard (/private/admin)                      │
│  - JavaScript clients + Guards                           │
└─────────────────────────────────────────────────────────┘
                    ↑ HTTP/REST ↓
┌─────────────────────────────────────────────────────────┐
│  🔧 APPLICATION LAYER (Backend - FastAPI)               │
│  - 45+ API endpoint routers                              │
│  - Authentication & Authorization                       │
│  - Business Logic Services                              │
│  - Data Access Layer (CRUD)                             │
└─────────────────────────────────────────────────────────┘
                    ↑ SQL ↓
┌─────────────────────────────────────────────────────────┐
│  💾 DATA LAYER (PostgreSQL)                              │
│  - 30+ SQLAlchemy models/tables                          │
│  - Ledger accounting system                             │
│  - Double-entry bookkeeping                             │
└─────────────────────────────────────────────────────────┘
```

---

## FRONTEND STRUCTURE & NAVIGATION

### 1. Public Pages (`/static`) - 14 pages
Unauthenticated user pages served directly from `/static`:

```
Static Pages:
├── index.html              → Home page
├── about.html              → About company
├── service.html            → Services overview
├── contact.html            → Contact form
├── signin.html             → Login page
├── signup.html             → Registration
├── feature.html            → Features
├── team.html               → Team info
├── testimonial.html        → Testimonials
├── corporate.html          → Corporate banking
├── personal.html           → Personal banking
├── deposits.html           → Deposit products
├── cards.html              → Card products
├── loans.html              → Loan products
└── investments.html        → Investment products
```

**Navigation Pattern**: Simple header navbar with links to main sections
**Auth**: None required - publicly accessible

### 2. User Pages (`/private/user`) - 38 pages
Authenticated user dashboard pages:

```
User Pages (Prefix: /user):
├── dashboard.html          → Main user dashboard
├── account.html            → Account management
├── profile.html            → User profile
├── cards.html              → Cards management
├── deposits.html           → Deposits view
├── loans.html              → Loans view
├── loans_enhanced.html     → Enhanced loans interface
├── investments.html        → Investments view
├── transfers.html          → Money transfers
├── bill_pay.html           → Bill payments
├── scheduled_transfers.html → Recurring transfers
├── international_transfers.html
├── alerts.html             → Alert settings
├── notifications.html      → Notification center
├── analytics.html          → Business analysis
├── blockchain.html         → Blockchain view
├── currency_exchange.html  → Foreign exchange
├── fraud_detection.html    → Fraud alerts
├── insurance.html          → Insurance products
├── kyc_form.html           → KYC submission
├── kyc_pending.html        → KYC status: pending
├── kyc_rejected.html       → KYC status: rejected
├── kyc_success.html        → KYC status: approved
├── transactions.html       → Transaction history
├── settings.html           → Account settings
├── security.html           → Security settings
├── treasury_portfolio.html → Treasury view
├── contact.html            → Support/contact
├── financial_planning.html → Financial planning
├── project.html            → Projects view
└── ... (10+ more)
```

**Navigation Pattern**: Navbar with dropdown menus
```
NAVBAR STRUCTURE:
├── Dashboard
├── Account
├── KYC
├── Products (dropdown)
│   ├── Cards
│   ├── Deposits
│   ├── Loans
│   ├── Investments
│   └── Transfers
├── Services (dropdown)
│   ├── Business Analysis
│   ├── Financial Planning
│   ├── Insurance
│   └── Projects
└── More (dropdown)
    ├── Profile
    ├── Settings
    ├── Notifications
    ├── Transactions
    ├── Security
    ├── Alerts
    ├── Contact
    └── Logout
```

**Auth**: Requires JWT token in cookie or Authorization header

### 3. Admin Pages (`/private/admin`) - 22 pages
Admin management dashboard:

```
Admin Pages (Prefix: /user/admin):
├── admin_dashboard_hub.html        → Admin main hub
├── admin_users.html                → User management
├── admin_kyc.html                  → KYC approvals
├── admin_fund.html                 → User funding
├── admin_transactions.html         → Transaction logs
├── admin_reports.html              → Reports
├── admin_bill_pay.html             → Bill pay management
├── admin_webhooks.html             → Webhook config
├── admin_blockchain.html           → Blockchain ops
├── admin_fraud_detection.html     → Fraud monitoring
├── admin_settlement.html           → Settlement
├── admin_reporting.html            → Advanced reporting
├── admin_international_compliance → Compliance
├── admin_monitoring.html           → System monitoring
├── admin_currency_exchange.html   → Currency mgmt
├── admin_treasury.html             → Treasury ops
├── admin_lending.html              → Lending mgmt
├── admin_lending_compliance.html  → Lending compliance
├── admin_hmda.html                 → HMDA reporting
├── admin_mobile_deposit.html      → Mobile deposit
├── admin_ach_management.html      → ACH processing
└── admin_settings.html             → System settings
```

**Navigation Pattern**: Navbar with all features visible
**Auth**: Requires `is_admin=True` + valid JWT token

---

## BACKEND API ROUTES & STRUCTURE

### Route Organization (45+ routers)

```
/routers/ - 57 API endpoint modules
├── admin.py                    (21 endpoints) - Admin operations
│   ├── POST   /api/admin/users/{id}/fund
│   ├── POST   /api/admin/kyc/{id}/approve
│   ├── POST   /api/admin/kyc/{id}/reject
│   ├── GET    /api/admin/users
│   ├── GET    /api/admin/data/kyc
│   └── ... (16 more)
│
├── kyc.py                      - KYC operations
│   ├── POST   /api/v1/kyc/verify
│   ├── GET    /api/v1/kyc/status/{user_id}
│   └── ... (5+ more)
│
├── transfers.py                - Money transfers
│   ├── POST   /api/transfers
│   ├── GET    /api/transfers/history
│   └── ... (3+ more)
│
├── loans.py                    - Loan management
│   ├── GET    /api/v1/loans
│   ├── POST   /api/v1/loans
│   └── ... (8+ more)
│
├── cards.py                    - Card operations
│   ├── GET    /api/v1/cards
│   ├── POST   /api/v1/cards
│   └── ... (6+ more)
│
├── deposits.py                 - Deposit management
│   ├── GET    /api/v1/deposits
│   ├── POST   /api/v1/deposits
│   └── ... (5+ more)
│
├── investments.py              - Investment operations
│   ├── GET    /api/v1/investments
│   ├── POST   /api/v1/investments
│   └── ... (6+ more)
│
├── account.py                  - Account operations
│   ├── GET    /api/v1/accounts
│   ├── POST   /api/v1/accounts
│   └── ... (5+ more)
│
├── fund_ledger.py              - Ledger-based funding
│   ├── POST   /api/fund/transfer
│   └── GET    /api/fund/balance
│
├── private.py                  - UI page routes
│   ├── GET    /user/dashboard
│   ├── GET    /user/cards
│   ├── GET    /user/admin/dashboard
│   └── ... (28+ more)
│
├── user_pages.py               - User page routing
│   ├── GET    /user/*
│
├── users.py                    - User API
│   ├── GET    /api/v1/users
│   ├── POST   /api/v1/users
│   └── ... (8+ more)
│
├── auth.py                     - Authentication
│   ├── POST   /auth/token
│   ├── POST   /auth/signup
│   ├── GET    /logout
│   └── ... (5+ more)
│
└── ... (37+ more routers for other features)
```

### Route Prefixes & Organization

```
/auth                   → Core authentication endpoints
/api/v1/*              → Versioned API (prod-ready)
/api/admin/*           → Admin-specific operations
/user/*                → Protected user pages
/api/*                 → User-facing financial operations
```

---

## DATABASE & MODELS

### 30+ SQLAlchemy Models

**Core Models**:
```python
class User(Base):
    id, email, hashed_password, full_name
    is_admin, is_active, is_verified
    kyc_status  # "not_started", "pending", "approved", "rejected"
    account_number, account_type
    → relationships: accounts, transactions, kyc_info, investments, loans

class Account(Base):
    id, account_number, account_type, balance, currency
    owner_id (FK → User)
    status, kyc_level, is_admin_account
    → relationships: owner, transactions

class Transaction(Base):
    id, user_id (FK), account_id (FK)
    amount, transaction_type, direction, status
    # Status: pending, blocked, completed, failed, cancelled
    kyc_status_at_time
    → relationships: user, account

class KYCInfo(Base):
    id, user_id (FK, unique)
    document_type, document_number, status
    kyc_status, kyc_submitted, submission_locked
    id_front_path, id_back_path, ssn_path, proof_of_address_path
    → relationships: user

class KYCSubmission(Base):
    id, user_id (FK), document_type, document_file_path
    status, submitted_at, reviewed_at

class Ledger(Base):
    id, user_id (FK), account_id (FK)
    entry_type (credit/debit), amount, status
    transaction_id, reference, created_at

class Card(Base):
    id, user_id (FK), card_number, card_type, status

class Loan(Base):
    id, user_id (FK), principal, interest_rate, status

class Investment(Base):
    id, user_id (FK), investment_type, amount, status

class Deposit(Base):
    id, user_id (FK), account_id (FK), amount, status

... (20+ more models)
```

### Database Connection
```python
# config.py
DATABASE_URL = "postgresql+asyncpg://finbank:password@localhost:5432/postgres?ssl=require"

# database.py
engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    poolclass=NullPool,
    connect_args={
        "timeout": 30,
        "ssl": "prefer"
    }
)
```

---

## CORE SERVICES & BUSINESS LOGIC

### 1. TransactionGate Service
**File**: `transaction_gate.py`
**Purpose**: Enforces 3 critical financial transaction rules

```python
class TransactionGate:
    
    RULE 1: No account → No money
    - Validate account exists
    - Validate ownership
    
    RULE 2: No KYC → No completed transactions
    - Check user.kyc_status == "approved"
    - Block if pending/rejected
    
    RULE 3: Balance = derived, not stored
    - Calculated from ledger entries
    - Never manually assigned (read-only)
    
    Methods:
    ├── validate_deposit(user_id, amount) → (can_complete, status, reason)
    ├── validate_transfer(sender_id, recipient_id, amount)
    └── validate_withdrawal(user_id, amount, account_id)
```

### 2. BalanceServiceLedger
**File**: `balance_service_ledger.py`
**Purpose**: Single source of truth for all balances

```python
class BalanceServiceLedger:
    
    PRINCIPLE: Balance = sum(credits) - sum(debits)
    
    Methods:
    ├── get_user_balance(db, user_id) → float
    ├── get_account_balance(db, account_id) → float
    ├── get_ledger_entries(db, user_id) → List[Ledger]
    └── verify_balance_integrity(db, user_id) → bool
    
    Usage:
    - All balance reads go through this service
    - Prevents N+1 queries (pre-fetch all balances)
    - Used by: admin_router, transfers, deposits
```

### 3. KYCService
**File**: `kyc_service.py`
**Purpose**: Document upload, validation, and status management

```python
class KYCService:
    
    UPLOAD_DIR: /private/uploads/kyc
    ALLOWED_EXTENSIONS: .pdf, .jpg, .jpeg, .png
    MAX_FILE_SIZE: 5MB
    
    Methods:
    ├── save_document(db, user_id, doc_type, file_bytes, filename)
    ├── validate_document(filename, file_size) → (valid, error)
    ├── approve_kyc(db, user_id) → (success, message)
    ├── reject_kyc(db, user_id, reason) → (success, message)
    └── get_kyc_status(db, user_id) → KYCInfo
    
    Document Types:
    - id_front: Government ID front
    - id_back: Government ID back
    - ssn_tax_id: Tax identification
    - proof_of_address: Utility bill, lease, etc.
```

### 4. SystemFundService
**File**: `system_fund_service.py`
**Purpose**: Admin funding operations (system → user)

```python
class SystemFundService:
    
    Methods:
    ├── fund_user(db, user_id, amount, fund_source, notes)
    ├── create_ledger_entries(db, user_id, amount)
    └── verify_system_reserve_account() → bool
    
    Fund Sources:
    - system_reserve: Admin system reserve account
    - promotional: Promotional funds
    - bonus: Bonus/gift funds
    - correction: Balance correction
```

### 5. AdminService
**File**: `admin_service.py`
**Purpose**: Centralized admin operations

```python
class AdminService:
    
    Methods:
    ├── get_admin_dashboard_metrics(db) → AdminDashboardMetrics
    ├── get_all_users_with_balances(db) → List[User]
    ├── get_pending_kyc_submissions(db) → List[KYCSubmission]
    ├── get_user_profile(db, user_id) → UserProfile
    ├── freeze_account(db, account_id) → bool
    ├── unlock_user_profile(db, user_id) → bool
    └── get_audit_log(db, filters) → List[AuditLog]
```

### 6. LedgerService
**File**: `ledger_service.py`
**Purpose**: Double-entry bookkeeping

```python
class LedgerService:
    
    Methods:
    ├── create_entry(db, user_id, account_id, entry_type, amount, reference)
    ├── post_entry(db, ledger_id) → bool
    ├── reverse_entry(db, ledger_id) → bool
    └── get_entries(db, user_id, filters) → List[Ledger]
    
    Entry States:
    - pending: Created but not posted
    - posted: Active (affects balance)
    - reversed: Cancelled with reversal entry
```

---

## AUTHENTICATION & SECURITY

### Authentication Flow

```
1. USER LOGIN
   ├── POST /auth/token
   │   ├── Username (email or account_number)
   │   └── Password
   │
   └─→ auth.py::login_for_access_token()
       ├── Verify credentials
       ├── Ensure admin email always has admin rights
       ├── Generate JWT token
       └── Set access_token cookie

2. PROTECTED REQUESTS
   ├── Request includes token in:
   │   ├── Cookie: access_token=<JWT>
   │   └── OR Header: Authorization: Bearer <JWT>
   │
   ├── deps.py::get_current_user()
   │   ├── Extract token
   │   ├── Decode JWT
   │   └── Fetch User from DB
   │
   └─→ Route executed with current_user context

3. ADMIN PROTECTION
   ├── deps.py::get_current_admin_user()
   │   ├── Call get_current_user()
   │   ├── Check is_admin == True
   │   └── Raise 403 if not admin
   │
   └─→ Admin route executed

4. LOGOUT
   ├── GET /logout
   └─→ Clear access_token cookie + redirect to signin
```

### Security Components

**auth_utils.py**:
```python
- create_access_token(email, expires_delta) → JWT
- decode_access_token(token) → email
- get_password_hash(password) → hashed
- verify_password(plain, hashed) → bool
```

**deps.py**:
```python
- get_current_user() → User (from token)
- get_current_admin_user() → User (admin-only)
- SessionDep → SQLAlchemy AsyncSession
```

**Security Features**:
- ✅ JWT token-based authentication
- ✅ Argon2 password hashing
- ✅ Cookie + Bearer token support
- ✅ Admin role enforcement
- ✅ Session management with db refresh
- ✅ Token expiration (30 minutes default)

---

## DATA FLOW PATTERNS

### Pattern 1: User Deposit

```
User Dashboard (cash_deposit.js)
  ↓ POST /api/v1/deposits
    ├─ deposits.py::create_deposit()
    │  ├─ Extract amount
    │  ├─ Get current_user from token
    │  ├─ Get user's account
    │  │
    │  ├─ TransactionGate.validate_deposit()
    │  │  ├─ Check account exists (RULE 1)
    │  │  └─ Check KYC approved if over limit (RULE 2)
    │  │
    │  ├─ Create Transaction record
    │  │  └─ status="completed"
    │  │
    │  ├─ LedgerService.create_entry()
    │  │  ├─ entry_type="credit"
    │  │  ├─ user_id=user.id
    │  │  └─ status="posted"
    │  │
    │  └─ Return 201 + TransactionResponse
    │
    └─ Dashboard refreshes balance
       └─ GET /api/v1/users/me -> BalanceServiceLedger
          └─ Reads new ledger entry
```

### Pattern 2: Admin Fund User

```
Admin Dashboard (admin_fund.js)
  ↓ POST /api/admin/users/{id}/fund
    ├─ admin.py::admin_fund_user()
    │  ├─ Extract amount, fund_source, notes
    │  ├─ Authenticate admin (JWT)
    │  ├─ Get target user
    │  │
    │  ├─ SystemFundService.fund_user()
    │  │  ├─ Validate system_reserve account exists
    │  │  ├─ Create debit from SYS-RESERVE
    │  │  ├─ Create credit to user
    │  │  ├─ LedgerService.post_entry()
    │  │  └─ Broadcast WebSocket event
    │  │
    │  └─ Return 200 + FundUserResponse
    │
    └─ Admin/User dashboards update
       └─ Both fetch fresh balances from BalanceServiceLedger
```

### Pattern 3: KYC Approval

```
Admin KYC Page (admin_kyc.js)
  ↓ POST /api/admin/kyc-submissions/{id}/approve
    ├─ admin.py::approve_kyc_submission_admin()
    │  ├─ Fetch KYCSubmission record
    │  ├─ UPDATE kyc_submission.status="approved"
    │  ├─ Get associated User
    │  ├─ UPDATE user.kyc_status="approved"  ✓ FIX #2
    │  ├─ db.commit()
    │  └─ Broadcast WebSocket event
    │
    └─ TransactionGate now sees kyc_status="approved"
       └─ User's pending transactions can now complete
```

### Pattern 4: Transfer Between Users

```
User Dashboard (transfer.js)
  ↓ POST /api/transfers
    ├─ transfers.py::create_transfer()
    │  ├─ Get sender (current_user)
    │  ├─ Get recipient (from recipient_id)
    │  │
    │  ├─ TransactionValidator.validate_transfer()
    │  │  ├─ Check both have accounts (RULE 1)
    │  │  ├─ Check both have approved KYC (RULE 2)
    │  │  └─ Check sender has balance (RULE 3)
    │  │
    │  ├─ LedgerService.create_entry(debit from sender)
    │  ├─ LedgerService.create_entry(credit to recipient)
    │  ├─ Both entries status="posted"
    │  │
    │  ├─ Create Transaction records (both)
    │  ├─ Broadcast WebSocket events
    │  └─ Return 201 + TransactionResponse
    │
    └─ Both users' dashboards update
       └─ Fetch balances from BalanceServiceLedger (reflects both entries)
```

---

## MODULE DEPENDENCY GRAPH

### Core Dependencies

```
┌─ ENTRY POINT ─────────────────────┐
│  main.py                           │
└─ Imports ─────────────────────────┘
    ├─→ config.py (Settings)
    ├─→ database.py (SQLAlchemy engine, SessionLocal, Base)
    ├─→ models.py (User, Account, Transaction, etc.)
    ├─→ auth.py (get_current_user_from_cookie, auth_router)
    ├─→ deps.py (get_current_user, get_current_admin_user)
    │
    └─→ ROUTERS (45+)
        ├─→ routers/admin.py
        │   ├─→ models.py (User, KYCSubmission, Ledger)
        │   ├─→ deps.py (get_current_admin_user, SessionDep)
        │   ├─→ balance_service_ledger.py (get_user_balance)
        │   ├─→ kyc_service.py (reject_kyc, approve_kyc)
        │   ├─→ admin_service.py (dashboard metrics)
        │   ├─→ cms.py (CRUD operations)
        │   └─→ ws_manager.py (WebSocket broadcasts)
        │
        ├─→ routers/kyc.py
        │   ├─→ models.py (KYCInfo, KYCSubmission, User)
        │   ├─→ kyc_service.py (save_document, validate)
        │   └─→ deps.py (get_current_user)
        │
        ├─→ routers/transfers.py
        │   ├─→ transaction_gate.py (validate_transfer)
        │   ├─→ balance_service_ledger.py (get_user_balance)
        │   ├─→ ledger_service.py (create_entry, post_entry)
        │   ├─→ account_id_enforcement.py (validate_ownership)
        │   ├─→ transaction_validator.py (validate_transfer)
        │   └─→ ws_manager.py (broadcast events)
        │
        ├─→ routers/deposits.py
        │   ├─→ transaction_gate.py (validate_deposit)
        │   ├─→ balance_service_ledger.py
        │   └─→ ledger_service.py
        │
        ├─→ routers/loans.py
        │   ├─→ models.py (Loan, User, Account)
        │   ├─→ account_id_enforcement.py (validate_ownership)
        │   └─→ balance_service_ledger.py
        │
        ├─→ routers/private.py
        │   ├─→ Jinja2Templates (/private/user, /private/admin)
        │   └─→ deps.py (get_current_user, get_current_admin_user)
        │
        └─→ ... (40+ more routers)

┌─ SERVICES ────────────────────────┐
│  Core business logic               │
├─ transaction_gate.py              │ Validates financial rules
├─ balance_service_ledger.py        │ Single source of truth
├─ kyc_service.py                   │ KYC document management
├─ system_fund_service.py           │ Admin funding
├─ admin_service.py                 │ Admin operations
├─ ledger_service.py                │ Double-entry bookkeeping
├─ account_id_enforcement.py        │ Account ownership
├─ transaction_validator.py         │ Transaction validation
└─ ... (20+ more services)          │

┌─ DATA ACCESS ─────────────────────┐
│  crud.py                           │
├─ get_user(), create_user()        │
├─ get_transactions()               │
├─ approve_kyc_submission()         │
└─ ... (50+ CRUD functions)         │

┌─ DATABASE ────────────────────────┐
│  models.py                         │ SQLAlchemy ORM
│  database.py                       │ AsyncSession, engine
└─ PostgreSQL (finanza_bank)        │
```

---

## IMPORT ANALYSIS

### Import Patterns

**1. Configuration & Database**
```python
from config import settings          # Environment variables
from database import SessionLocal, Base, engine  # Database engine
```

**2. Models & Schemas**
```python
from models import User, Account, Transaction  # Database models
from schemas import UserCreate, User, Transaction  # Pydantic validation
```

**3. Authentication & Authorization**
```python
from auth import get_current_user_from_cookie  # Cookie-based
from deps import (                   # Dependency injection
    get_current_user,
    get_current_admin_user,
    SessionDep,
    CurrentUserDep
)
```

**4. Business Logic Services**
```python
from transaction_gate import TransactionGate
from balance_service_ledger import BalanceServiceLedger
from kyc_service import KYCService
from system_fund_service import SystemFundService
from admin_service import admin_service
from ledger_service import LedgerService
```

**5. Data Access**
```python
import crud  # All CRUD operations
from crud import (
    get_user, create_user, get_transactions,
    approve_kyc_submission, reject_kyc_submission
)
```

**6. Real-time Communication**
```python
from ws_manager import manager  # WebSocket broadcasts
```

### Import Dependency Chains

```
Request → Route Handler
  ├─ Depends(get_current_user)
  │  └─→ auth_utils.decode_access_token()
  │      └─→ config.settings.SECRET_KEY
  │
  ├─ Depends(SessionDep)
  │  └─→ database.SessionLocal()
  │
  └─→ Route Logic
      ├─→ TransactionGate.validate_*()
      ├─→ BalanceServiceLedger.get_balance()
      ├─→ LedgerService.create_entry()
      ├─→ crud.* CRUD operations
      │   └─→ models.* SQLAlchemy queries
      │       └─→ database.engine (PostgreSQL)
      │
      └─→ manager.broadcast() WebSocket event
```

---

## FILE ORGANIZATION SUMMARY

### Root Directory Structure

```
financial-services-website-template/
│
├── 📁 app/                         → Alternative app structure (legacy)
│   ├── auth.py
│   ├── models.py
│   └── templates/
│
├── 📁 routers/                     → 57 API endpoint modules
│   ├── admin.py                    → Admin operations
│   ├── kyc.py                      → KYC management
│   ├── transfers.py                → Money transfers
│   ├── loans.py                    → Loan management
│   ├── cards.py                    → Card operations
│   ├── deposits.py                 → Deposit operations
│   ├── investments.py              → Investment management
│   ├── users.py                    → User API
│   ├── account.py                  → Account management
│   ├── private.py                  → Private/authenticated UI routes
│   ├── user_pages.py               → User page routes
│   └── ... (47+ more)
│
├── 📁 private/                     → Protected frontend
│   ├── user/                       → User dashboard pages (38 HTML)
│   │   ├── dashboard.html
│   │   ├── cards.html
│   │   ├── loans.html
│   │   └── ... (35+ more)
│   ├── admin/                      → Admin dashboard pages (22 HTML)
│   │   ├── admin_dashboard_hub.html
│   │   ├── admin_users.html
│   │   ├── admin_kyc.html
│   │   └── ... (19+ more)
│   ├── admin_static/               → Admin assets
│   └── uploads/kyc/                → KYC document storage
│
├── 📁 static/                      → Public frontend
│   ├── index.html, about.html, service.html, etc. (14 pages)
│   ├── 📁 css/                     → Stylesheets
│   ├── 📁 js/                      → JavaScript
│   │   ├── admin-client.js         → Admin API client
│   │   ├── user-client.js          → User API client
│   │   ├── admin-guard.js          → Admin auth guard
│   │   ├── user-guard.js           → User auth guard
│   │   ├── main.js, realtime.js, page-sync.js
│   ├── 📁 img/                     → Images
│   ├── 📁 lib/                     → Libraries
│   └── 📁 scss/                    → SCSS/CSS source
│
├── 📁 migrations/                  → Alembic database migrations
│
├── 🐍 Core Python Files
│   ├── main.py                     → FastAPI app entry point
│   ├── auth.py                     → Authentication router
│   ├── auth_utils.py               → JWT, password utilities
│   ├── config.py                   → Environment settings
│   ├── database.py                 → SQLAlchemy setup
│   ├── models.py                   → 30+ SQLAlchemy models (1136 lines)
│   ├── schemas.py                  → Pydantic validation schemas
│   ├── deps.py                     → Dependency injection
│   ├── crud.py                     → Data access layer (818 lines)
│   ├── public.py                   → Public routes (legacy)
│   └── ws_manager.py               → WebSocket manager
│
├── 🎯 Core Services
│   ├── transaction_gate.py         → Transaction validation
│   ├── balance_service_ledger.py   → Balance calculation
│   ├── balance_service.py          → OLD balance system (deprecated)
│   ├── kyc_service.py              → KYC management
│   ├── system_fund_service.py      → Admin funding
│   ├── admin_service.py            → Admin operations (704 lines)
│   ├── ledger_service.py           → Double-entry bookkeeping
│   ├── account_id_enforcement.py   → Account ownership
│   ├── transaction_validator.py    → Transaction validation
│   └── ... (30+ more services)
│
├── 🛠️ Utility & Helper Files
│   ├── email_utils.py              → Email operations
│   ├── email_templates.py          → Email templates
│   ├── payment_utils.py            → Payment helpers
│   ├── init_db.py                  → Database initialization
│   ├── crud.py                     → CRUD operations
│   └── ... (15+ utilities)
│
├── 🔧 Configuration Files
│   ├── alembic.ini                 → Alembic config
│   ├── requirements.txt            → Python dependencies
│   ├── .env                        → Environment variables
│   ├── config.py                   → App settings
│   └── DEPLOYMENT_SCRIPT.ps1       → AWS deployment
│
├── 📚 Database Files
│   ├── finanza.db                  → SQLite (dev)
│   ├── finbank.db                  → SQLite (secondary)
│   └── *.backup                    → Backups
│
├── 📋 Documentation Files
│   ├── CORE_ARCHITECTURE_ANALYSIS.md
│   ├── QUICK_REFERENCE.md
│   ├── IMPLEMENTATION_CHECKLIST.md
│   ├── DEBUGGING_GUIDE.md
│   ├── START_HERE.md
│   ├── FINAL_STATUS_REPORT.txt
│   └── ... (20+ docs)
│
└── 🔍 Debugging & Verification Scripts
    ├── verify_kyc_system.py
    ├── verify_system_reserve.py
    ├── check_db.py
    ├── debug_fund_transfer.py
    └── ... (30+ scripts)
```

---

## NAVIGATION FLOW DIAGRAM

### User Journey

```
┌────────────────────────────────────┐
│  Landing Page (/)                  │
│  ├─ About (/about)                 │
│ └─ Services (/service)             │
└────────────────────────────────────┘
            ↓
┌────────────────────────────────────┐
│  Sign In (/signin)                 │
│  OR Sign Up (/signup)              │
└────────────────────────────────────┘
            ↓ JWT Token
┌────────────────────────────────────┐
│  Dashboard (/user/dashboard) ✓     │
│  ├─ Account (/user/account)        │
│  ├─ Profile (/user/profile)        │
│  ├─ Cards (/user/cards)            │
│  ├─ Deposits (/user/deposits)      │
│  ├─ Loans (/user/loans)            │
│  ├─ Investments (/user/investments)│
│  ├─ Transfers (/user/transfers)    │
│  ├─ KYC (/user/kyc_form)           │
│  │  └─ Success/Pending/Rejected    │
│  ├─ Settings (/user/settings)      │
│  └─ Logout (/logout)               │
└────────────────────────────────────┘
            ↓ Admin User Only
┌────────────────────────────────────┐
│  Admin Hub (/user/admin/dashboard) │
│  ├─ Users (/user/admin/admin_users)│
│  ├─ KYC Approvals (/user/admin/kyc)│
│  ├─ Funding (/user/admin/fund)     │
│  ├─ Reports (/user/admin/reports)  │
│  ├─ Transactions (history)         │
│  └─ Settings (/user/admin/settings)│
└────────────────────────────────────┘
```

---

## ROUTE PREFIX SUMMARY

```
Prefix          | Purpose                  | Auth Required | Examples
────────────────┼──────────────────────────┼───────────────┼────────────────────
/               | Public pages             | ❌ No         | /, /about, /service
/auth           | Authentication           | ❌ Most       | POST /auth/token
/api/v1         | Versioned API            | ✅ Yes        | /api/v1/users, /api/v1/kyc
/api/admin      | Admin API                | ✅ Admin      | /api/admin/users/{id}/fund
/api            | User API                 | ✅ Yes        | /api/transfers, /api/deposits
/user           | User UI routes           | ✅ Yes        | /user/dashboard, /user/cards
/user/admin     | Admin UI routes          | ✅ Admin      | /user/admin/dashboard, /kyc
```

---

## KEY INSIGHTS

### Architectural Patterns

✅ **Clean Separation of Concerns**
- Routers (endpoints) separate from services (logic)
- Services separate from data (CRUD layer)
- Models provide clear data contracts

✅ **Dependency Injection**
- FastAPI `Depends()` for authentication
- SessionDep for database access
- Clean request/response flow

✅ **Double-Entry Accounting**
- Ledger service for financial transactions
- Credit/debit entries for accuracy
- Atomic operations with db.commit()

✅ **Role-Based Access Control**
- `get_current_user` for all authenticated routes
- `get_current_admin_user` for admin-only routes
- Clear permission boundaries

### Data Flow Highlights

**Consistency**: All balances flow through `BalanceServiceLedger`
**Validation**: `TransactionGate` enforces 3 core financial rules
**Traceability**: Web sockets broadcast all significant events
**Atomicity**: All changes committed in single transaction

### Module Strength

- **Modularity**: 57 separate router/service files = low coupling
- **Reusability**: Services used across multiple routers
- **Testability**: Each service can be tested independently
- **Scalability**: Async/await throughout = production-ready

---

## SUMMARY

This is an **enterprise-grade financial services platform** with:
- ✅ Comprehensive frontend (74 HTML pages)
- ✅ Extensive API (45+ routers, 100+ endpoints)
- ✅ Sophisticated business logic (20+ service classes)
- ✅ Proper authentication & authorization
- ✅ Double-entry accounting system
- ✅ KYC/AML compliance framework
- ✅ Real-time WebSocket communication
- ✅ Admin management dashboard

**Current Status**: 70% complete, requires critical issue fixes before production deployment.
