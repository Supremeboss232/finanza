from fastapi import Depends, HTTPException, status
from typing import Callable, List, Dict, Any
import json

from deps import get_current_user

# =============================================================================
# AUTHORITATIVE 5-TIER ADMIN ROLE & PRIVILEGE MATRIX
# =============================================================================

ROLE_MATRIX: Dict[str, Dict[str, Any]] = {
    "SUPER_ADMIN": {
        "role": "SUPER_ADMIN",
        "title": "Chief Executive / Root Super Admin",
        "badge_color": "#dc2626",
        "summary": "Unrestricted root authority across all banking, treasury, compliance, and system administration modules.",
        "can_do": [
            "Create, promote, demote, and revoke other Administrator accounts",
            "Grant or deny granular custom permissions & reset Admin passwords/MFA",
            "Configure global System Settings, Database Backups, and Vendor API keys",
            "Manage Primary Reserve (SYS-RESERVE-0001), Treasury Portfolios & Clearing Pools",
            "Fund/adjust user balances, approve/reject KYC, underwrite loans, and settle wires",
            "Execute Bulk Operations, view/export all Audit Logs, and delete user records",
        ],
        "cannot_do": [
            "Cannot revoke own SUPER_ADMIN status or delete own root account (self-lockout protection)",
        ],
        "allowed_pages": ["*"],
        "restricted_pages": [],
        "permissions": [
            "*",
            # User Management
            "users:view", "user:view", "user:create", "user:edit", "user:suspend", "user:delete",
            # Balance & Ledger
            "ledger:adjust", "balance:adjust", "balance:limit_change",
            # KYC
            "kyc:review", "kyc:view", "kyc:approve", "kyc:reject", "kyc:verify",
            # Transactions & Payments
            "transactions:view", "transactions:create", "transaction:view", "transaction:create",
            "transaction:reverse", "transaction:cancel", "payments:settle",
            # Products (Deposits, Loans, Investments, Cards)
            "deposits:view", "deposits:approve", "loans:credit_decision", "loans:underwrite",
            "loans:disburse", "investments:view", "investments:manage", "cards:view", "cards:approve",
            # Treasury & Compliance & Reporting
            "treasury:view", "treasury:manage", "aml:view", "compliance:report",
            "reporting:view", "audit:view", "audit:export", "support:manage",
            # System & Admin Governance
            "admin:manage", "admin:view", "admin:approve", "system:config",
        ],
    },
    "ADMIN": {
        "role": "ADMIN",
        "title": "Operations & Customer Banking Admin",
        "badge_color": "#2563eb",
        "summary": "Day-to-day banking operations: customer management, KYC review, transaction oversight, lending, and reporting.",
        "can_do": [
            "View, create, edit, suspend/activate, and freeze/unfreeze customer accounts",
            "Place and release compliance/operational holds on customer accounts",
            "Review, approve, and reject customer KYC identity verification submissions",
            "View all transactions, release/cancel pending transfers, and manage Bill Pay & Mobile Deposits",
            "Underwrite, approve, deny, and disburse customer loan applications & cards",
            "Run Bulk Operations, Advanced Search, BI Reports, and view Activity/Audit logs",
        ],
        "cannot_do": [
            "Cannot create, revoke, or modify roles/permissions of other Administrators",
            "Cannot modify global System Settings, Backups, or Vendor Integration credentials",
            "Cannot reallocate Primary Reserve or Institutional Treasury Portfolios",
            "Cannot permanently delete user accounts from the database",
        ],
        "allowed_pages": [
            "/user/admin/dashboard", "/user/admin/users", "/user/admin/kyc",
            "/user/admin/transactions", "/user/admin/fund", "/user/admin/lending",
            "/user/admin/lending_compliance", "/user/admin/bill_pay", "/user/admin/mobile_deposit",
            "/user/admin/bulk_operations", "/user/admin/advanced_search", "/user/admin/reporting",
            "/user/admin/activity_dashboard", "/user/admin/monitoring", "/user/admin/profile",
            "/user/admin/mfa_setup",
        ],
        "restricted_pages": [
            "/user/admin/management_panel", "/user/admin/settings", "/user/admin/vendor_hub",
            "/user/admin/treasury", "/user/admin/bank-connect",
        ],
        "permissions": [
            "users:view", "user:view", "user:create", "user:edit", "user:suspend",
            "ledger:adjust", "balance:adjust", "balance:limit_change",
            "kyc:review", "kyc:view", "kyc:approve", "kyc:reject", "kyc:verify",
            "transactions:view", "transactions:create", "transaction:view", "transaction:create",
            "transaction:reverse", "transaction:cancel", "payments:settle",
            "deposits:view", "deposits:approve", "loans:credit_decision", "loans:underwrite",
            "loans:disburse", "investments:view", "investments:manage", "cards:view", "cards:approve",
            "treasury:view", "reporting:view", "audit:view", "admin:view", "support:manage",
        ],
    },
    "TREASURY": {
        "role": "TREASURY",
        "title": "Treasury, Liquidity & Settlement Officer",
        "badge_color": "#059669",
        "summary": "Controls bank liquidity, Primary Reserve allocations, inter-bank clearing pools, ACH/Wire settlement, FX, and Web3 rails.",
        "can_do": [
            "Fund and adjust user account balances from Primary Reserve (SYS-RESERVE-0001)",
            "Manage Institutional Treasury Portfolios, Liquidity Positions, and Risk Parameters",
            "Operate Inter-Bank Settlement (ACH, SWIFT, FedNow, RTP) and Payrail Clearing Pools",
            "Manage Live FX Exchange Rates, Blockchain/Web3 Rails, and Bank Connections",
            "Approve High-Value Deposits & Investments and view Financial/Audit Reports",
        ],
        "cannot_do": [
            "Cannot approve or reject customer KYC identity verification documents",
            "Cannot create, edit, suspend, or delete customer user profiles",
            "Cannot create/revoke Administrators or change Admin roles",
            "Cannot modify global System Settings",
        ],
        "allowed_pages": [
            "/user/admin/dashboard", "/user/admin/treasury", "/user/admin/settlement",
            "/user/admin/ach_management", "/user/admin/bank-connect", "/user/admin/fund",
            "/user/admin/currency_exchange", "/user/admin/blockchain", "/user/admin/transactions",
            "/user/admin/reporting", "/user/admin/monitoring", "/user/admin/profile",
            "/user/admin/mfa_setup",
        ],
        "restricted_pages": [
            "/user/admin/management_panel", "/user/admin/settings", "/user/admin/kyc",
            "/user/admin/bulk_operations",
        ],
        "permissions": [
            "payments:settle", "deposits:view", "deposits:approve",
            "ledger:adjust", "balance:adjust", "balance:limit_change",
            "treasury:view", "treasury:manage",
            "investments:view", "investments:manage",
            "transactions:view", "transactions:create", "transaction:view", "transaction:create",
            "users:view", "user:view", "reporting:view", "audit:view", "admin:view",
        ],
    },
    "COMPLIANCE": {
        "role": "COMPLIANCE",
        "title": "AML, KYC & Regulatory Compliance Officer",
        "badge_color": "#7c3aed",
        "summary": "Oversees CIP/KYC identity verification, OFAC/SDN sanctions screening, AML fraud detection, HMDA, and audit exports.",
        "can_do": [
            "Review, approve, and reject customer KYC identity submissions & documents",
            "Operate Fraud Detection Engine, OFAC/SDN Sanctions Screening, and AML alerts",
            "Manage International Compliance, Lending Compliance, and HMDA Regulatory LAR",
            "Freeze suspicious accounts and place compliance holds to prevent illicit outflows",
            "View and export full Audit Logs, Activity Dashboards, and Compliance Reports",
        ],
        "cannot_do": [
            "Cannot fund accounts, adjust ledger balances, or move Treasury/Reserve funds",
            "Cannot create or delete customer accounts",
            "Cannot create/revoke Administrators or alter Admin roles",
            "Cannot modify System Settings or Vendor API credentials",
        ],
        "allowed_pages": [
            "/user/admin/dashboard", "/user/admin/kyc", "/user/admin/fraud_detection",
            "/user/admin/international_compliance", "/user/admin/lending_compliance",
            "/user/admin/hmda", "/user/admin/activity_dashboard", "/user/admin/reporting",
            "/user/admin/users", "/user/admin/transactions", "/user/admin/advanced_search",
            "/user/admin/profile", "/user/admin/mfa_setup",
        ],
        "restricted_pages": [
            "/user/admin/management_panel", "/user/admin/settings", "/user/admin/vendor_hub",
            "/user/admin/treasury", "/user/admin/fund", "/user/admin/settlement",
        ],
        "permissions": [
            "kyc:review", "kyc:view", "kyc:approve", "kyc:reject", "kyc:verify",
            "aml:view", "compliance:report",
            "audit:view", "audit:export", "reporting:view", "admin:view",
            "users:view", "user:view", "user:suspend",
            "transactions:view", "transaction:view",
        ],
    },
    "SUPPORT": {
        "role": "SUPPORT",
        "title": "Customer Support & Concierge Specialist",
        "badge_color": "#0891b2",
        "summary": "Frontline customer assistance: read-only account/transaction lookup, password resets, session revocation, and ticket resolution.",
        "can_do": [
            "View customer profiles, account numbers, balances, and hold/freeze status",
            "View customer transaction ledger history and generate receipts",
            "View customer KYC verification status (read-only)",
            "Assist customers with password resets, session revocation, and support tickets",
            "View Admin Activity Dashboard and System Health status",
        ],
        "cannot_do": [
            "Cannot fund accounts or adjust customer balances",
            "Cannot approve or reject KYC documents",
            "Cannot suspend, freeze, or delete customer accounts",
            "Cannot access Treasury, Settlement, Lending Underwriting, Bulk Ops, Admin Management, or Settings",
        ],
        "allowed_pages": [
            "/user/admin/dashboard", "/user/admin/users", "/user/admin/transactions",
            "/user/admin/advanced_search", "/user/admin/activity_dashboard",
            "/user/admin/profile", "/user/admin/mfa_setup",
        ],
        "restricted_pages": [
            "/user/admin/management_panel", "/user/admin/settings", "/user/admin/vendor_hub",
            "/user/admin/treasury", "/user/admin/fund", "/user/admin/settlement",
            "/user/admin/ach_management", "/user/admin/kyc", "/user/admin/bulk_operations",
        ],
        "permissions": [
            "users:view", "user:view",
            "transactions:view", "transaction:view",
            "kyc:view",
            "support:manage",
            "audit:view", "admin:view",
        ],
    },
}

# Backwards-compatible lower-case ROLES dict
ROLES = {k.lower(): {"permissions": v["permissions"]} for k, v in ROLE_MATRIX.items()}

ADMIN_ROLE_ALIASES = {
    "SUPER_ADMIN": "SUPER_ADMIN",
    "SUPERADMIN": "SUPER_ADMIN",
    "ADMIN": "ADMIN",
    "TREASURY": "TREASURY",
    "COMPLIANCE": "COMPLIANCE",
    "SUPPORT": "SUPPORT",
    "STANDARD": "SUPPORT",
}

PERMISSION_SYNONYMS = {
    "users:view": ["user:view", "users:view", "perm:users:view"],
    "user:view": ["user:view", "users:view", "perm:users:view"],
    "user:create": ["user:create", "users:create"],
    "user:edit": ["user:edit", "users:edit"],
    "user:suspend": ["user:suspend", "users:suspend", "perm:users:suspend"],
    "user:delete": ["user:delete", "users:delete"],
    "ledger:adjust": ["ledger:adjust", "balance:adjust", "perm:balance:adjust"],
    "balance:adjust": ["ledger:adjust", "balance:adjust", "perm:balance:adjust"],
    "kyc:review": ["kyc:review", "kyc:view", "kyc:approve", "kyc:reject", "kyc:verify"],
    "kyc:view": ["kyc:view", "kyc:review"],
    "kyc:approve": ["kyc:approve", "kyc:review", "perm:kyc:approve"],
    "kyc:reject": ["kyc:reject", "kyc:review", "perm:kyc:reject"],
    "transactions:view": ["transactions:view", "transaction:view", "perm:transactions:view"],
    "transaction:view": ["transactions:view", "transaction:view", "perm:transactions:view"],
    "transactions:create": ["transactions:create", "transaction:create"],
    "transaction:create": ["transactions:create", "transaction:create"],
    "audit:view": ["audit:view", "admin:view", "perm:audit:view"],
    "admin:view": ["admin:view", "audit:view", "users:view"],
}


def resolve_admin_role(current_user) -> str:
    """Resolve the canonical 5-tier role name for an admin user."""
    if not current_user:
        return "SUPPORT"
    email = (getattr(current_user, "email", "") or "").lower().strip()
    raw_role = (getattr(current_user, "admin_role", None) or "").upper().strip()

    if email == "admin@admin.com" or raw_role in ("SUPER_ADMIN", "SUPERADMIN"):
        return "SUPER_ADMIN"
    if raw_role in ("ADMIN", "TREASURY", "COMPLIANCE", "SUPPORT"):
        return raw_role
    if email.startswith("treasury@"):
        return "TREASURY"
    if email.startswith("compliance@"):
        return "COMPLIANCE"
    if email.startswith("support@"):
        return "SUPPORT"
    if getattr(current_user, "is_admin", False):
        # Generic admin accounts with default 'STANDARD' or None get operational ADMIN role
        return "ADMIN"
    return "SUPPORT"


def get_effective_permissions(current_user) -> List[str]:
    """
    Calculate the effective list of permissions for an admin user,
    combining role defaults with any custom_permissions overrides stored on the User model.
    """
    role = resolve_admin_role(current_user)
    role_spec = ROLE_MATRIX.get(role, ROLE_MATRIX["SUPPORT"])
    effective = list(role_spec["permissions"])

    custom_raw = getattr(current_user, "custom_permissions", None)
    if custom_raw:
        try:
            parsed = json.loads(custom_raw) if isinstance(custom_raw, str) else custom_raw
            if isinstance(parsed, dict):
                # If explicit replacement list is stored
                if "permissions" in parsed and isinstance(parsed["permissions"], list):
                    effective = list(parsed["permissions"])
                for g in parsed.get("granted", []):
                    if g not in effective:
                        effective.append(g)
                for d in parsed.get("denied", []):
                    effective = [p for p in effective if p != d]
            elif isinstance(parsed, list):
                effective = list(parsed)
        except Exception:
            pass

    return effective


def has_permission(current_user, permission: str) -> bool:
    """Check whether `current_user` holds `permission` (supporting wildcards & synonyms)."""
    if not current_user or not getattr(current_user, "is_admin", False):
        return False

    role = resolve_admin_role(current_user)
    if role == "SUPER_ADMIN":
        return True

    effective = get_effective_permissions(current_user)
    if "*" in effective or permission in effective:
        return True

    synonyms = PERMISSION_SYNONYMS.get(permission, [])
    return any(s in effective for s in synonyms)


def get_role_matrix() -> Dict[str, Any]:
    """Return the complete 5-tier Admin Role & Privilege Matrix."""
    return ROLE_MATRIX


def _normalize_roles(current_user) -> List[str]:
    return [resolve_admin_role(current_user).lower()]


def require_permission(permission: str) -> Callable:
    """
    FastAPI Dependency that verifies the current user is an admin with `permission`
    and returns the `current_user` object (so routes can access `current_admin.id`, etc.).
    """
    async def _checker(current_user=Depends(get_current_user)):
        if not current_user or not getattr(current_user, "is_admin", False):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin access required",
            )

        if has_permission(current_user, permission):
            return current_user

        role = resolve_admin_role(current_user)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Role '{role}' does not have required permission '{permission}'",
        )

    return _checker
