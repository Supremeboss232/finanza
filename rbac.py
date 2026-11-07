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
        "title": "Super Administrator",
        "default_account": "admin@admin.com",
        "badge_color": "#dc2626",
        "summary": "Unrestricted executive authority across all users, treasury, compliance, payment rails, vendor gateways, and admin governance.",
        "can_do": [
            "Create, promote, change roles, reset passwords, and revoke other Administrators",
            "Override granular permissions and manage Admin MFA / 2FA security",
            "Create, edit, suspend, freeze, unfreeze, and permanently delete user accounts",
            "Fund, credit, debit, adjust, and reconcile user and institutional reserve balances",
            "Approve or reject KYC submissions, loans, mobile deposits, and high-value wires",
            "Configure bank gateways, vendor API credentials, webhooks, and system settings",
        ],
        "cannot_do": [
            "Cannot bypass immutable Audit Log recording (all Super Admin actions are logged)",
            "Cannot revoke own SUPER_ADMIN status or delete own root account (self-lockout protection)",
        ],
        "allowed_pages": ["*"],
        "restricted_pages": [],
        "permissions": [
            "*",
            # User Management
            "users:view", "user:view", "users:create", "user:create", "users:edit", "user:edit",
            "users:suspend", "user:suspend", "users:freeze", "user:freeze", "users:delete", "user:delete",
            "users:bulk_actions",
            # Balance & Ledger
            "ledger:adjust", "balance:adjust", "users:adjust_balance", "balance:reconcile",
            "balance:limit_change", "fund:transfer",
            # KYC
            "kyc:review", "kyc:view", "kyc:approve", "kyc:reject", "kyc:verify",
            # Transactions & Payments
            "transactions:view", "transaction:view", "transactions:create", "transaction:create",
            "transactions:approve", "transaction:approve", "transactions:reject", "transaction:reject",
            "transactions:reverse", "transaction:reverse", "transaction:cancel",
            "payments:settle", "settlement:manage", "ach:manage", "fx:manage",
            # Products (Deposits, Loans, Investments, Cards)
            "deposits:view", "deposits:approve", "loans:view", "loans:approve", "loans:reject",
            "loans:credit_decision", "loans:underwrite", "loans:disburse",
            "investments:view", "investments:manage", "cards:view", "cards:approve", "cards:manage",
            # Treasury & Compliance & Reporting
            "treasury:view", "treasury:manage", "aml:view", "compliance:view", "compliance:manage",
            "compliance:report", "fraud:manage", "reports:view", "reports:generate", "reporting:view",
            "audit:view", "audit:export", "support:manage",
            # System & Admin Governance
            "admin:manage", "admin:create", "admin:view", "admin:approve", "system:config", "settings:edit",
        ],
    },
    "ADMIN": {
        "role": "ADMIN",
        "title": "Operations Administrator",
        "default_account": "admin@finanza.com",
        "badge_color": "#2563eb",
        "summary": "Day-to-day banking operations across customer accounts, KYC verification, lending, deposits, cards, and support.",
        "can_do": [
            "View, create, edit, suspend, freeze, and unfreeze customer accounts",
            "Review, approve, and reject KYC identity verification submissions",
            "Review and approve/reject loan applications, mobile check deposits, and cards",
            "View transactions, approve pending transfers, and execute bulk user operations",
            "Access Advanced Search, Activity Dashboard, and operational reports",
        ],
        "cannot_do": [
            "Cannot create, revoke, or change roles of other Admin accounts",
            "Cannot modify institutional Treasury reserves or global Risk Parameters",
            "Cannot permanently delete user accounts or alter core system/vendor API keys",
        ],
        "allowed_pages": [
            "/user/admin/dashboard", "/user/admin/users", "/user/admin/kyc",
            "/user/admin/transactions", "/user/admin/fund", "/user/admin/lending",
            "/user/admin/lending_compliance", "/user/admin/hmda", "/user/admin/bill_pay",
            "/user/admin/mobile_deposit", "/user/admin/bulk_operations", "/user/admin/advanced_search",
            "/user/admin/reporting", "/user/admin/activity_dashboard", "/user/admin/monitoring",
            "/user/admin/profile", "/user/admin/mfa_setup",
        ],
        "restricted_pages": [
            "/user/admin/management_panel", "/user/admin/settings", "/user/admin/vendor_hub",
            "/user/admin/treasury", "/user/admin/bank_connect", "/user/admin/webhooks",
        ],
        "permissions": [
            "users:view", "user:view", "users:create", "user:create", "users:edit", "user:edit",
            "users:suspend", "user:suspend", "users:freeze", "user:freeze", "users:bulk_actions",
            "ledger:adjust", "balance:adjust", "users:adjust_balance", "balance:limit_change",
            "kyc:review", "kyc:view", "kyc:approve", "kyc:reject", "kyc:verify",
            "transactions:view", "transaction:view", "transactions:create", "transaction:create",
            "transactions:approve", "transaction:approve", "transactions:reject", "transaction:reject",
            "transactions:reverse", "transaction:reverse", "transaction:cancel", "payments:settle",
            "deposits:view", "deposits:approve", "loans:view", "loans:approve", "loans:reject",
            "loans:credit_decision", "loans:underwrite", "loans:disburse",
            "investments:view", "investments:manage", "cards:view", "cards:approve", "cards:manage",
            "treasury:view", "reports:view", "reporting:view", "audit:view", "aml:view", "admin:view", "support:manage",
        ],
    },
    "TREASURY": {
        "role": "TREASURY",
        "title": "Treasury & Settlement Officer",
        "default_account": "treasury@finanza.com",
        "badge_color": "#059669",
        "summary": "Controls institutional liquidity, customer balance funding/adjustments, ACH/Wire/FedNow settlement, FX rates, and investments.",
        "can_do": [
            "Credit, debit, and adjust customer account balances and manage account holds",
            "Manage institutional Treasury portfolios, liquidity pools, and risk parameters",
            "Process ACH batches, Wire settlements, FedNow/RTP clearing, and NSF fee actions",
            "Manage live FX exchange rates, currency exchange, and blockchain settlement",
            "Approve deposits, disburse approved loans, and generate financial/treasury reports",
        ],
        "cannot_do": [
            "Cannot create, modify, or revoke Admin accounts or change role permissions",
            "Cannot approve or reject customer KYC identity documents",
            "Cannot delete customer accounts or edit system-wide vendor secrets",
        ],
        "allowed_pages": [
            "/user/admin/dashboard", "/user/admin/treasury", "/user/admin/settlement",
            "/user/admin/ach_management", "/user/admin/bank_connect", "/user/admin/fund",
            "/user/admin/currency_exchange", "/user/admin/blockchain", "/user/admin/transactions",
            "/user/admin/lending", "/user/admin/mobile_deposit", "/user/admin/bill_pay",
            "/user/admin/reporting", "/user/admin/monitoring", "/user/admin/profile",
            "/user/admin/mfa_setup",
        ],
        "restricted_pages": [
            "/user/admin/management_panel", "/user/admin/settings", "/user/admin/vendor_hub",
            "/user/admin/kyc", "/user/admin/bulk_operations", "/user/admin/fraud_detection",
            "/user/admin/international_compliance",
        ],
        "permissions": [
            "users:view", "user:view", "ledger:adjust", "balance:adjust", "users:adjust_balance",
            "balance:reconcile", "balance:limit_change", "fund:transfer",
            "transactions:view", "transaction:view", "transactions:create", "transaction:create",
            "transactions:approve", "transaction:approve", "transactions:reject", "transaction:reject",
            "transactions:reverse", "transaction:reverse", "payments:settle",
            "treasury:view", "treasury:manage", "settlement:manage", "ach:manage", "fx:manage",
            "deposits:view", "deposits:approve", "investments:view", "investments:manage",
            "loans:view", "loans:disburse", "cards:view", "reports:view", "reports:generate",
            "reporting:view", "audit:view", "admin:view",
        ],
    },
    "COMPLIANCE": {
        "role": "COMPLIANCE",
        "title": "Compliance & AML Officer",
        "default_account": "compliance@finanza.com",
        "badge_color": "#d97706",
        "summary": "Oversees KYC/KYB verification, OFAC sanctions screening, fraud detection, HMDA/lending compliance, and regulatory reporting.",
        "can_do": [
            "Review, verify, approve, and reject customer KYC/KYB identity submissions",
            "Run OFAC SDN sanctions checks, PEP screening, and international compliance reviews",
            "Investigate Fraud Detection alerts and freeze/flag high-risk accounts",
            "Audit HMDA LAR records, Lending Compliance, and immutable Admin Audit Logs",
            "Generate and export regulatory, AML, and compliance reports",
        ],
        "cannot_do": [
            "Cannot credit, debit, or adjust customer or treasury monetary balances",
            "Cannot create, edit, or revoke Admin accounts",
            "Cannot process ACH/Wire settlement batches or change vendor API keys",
        ],
        "allowed_pages": [
            "/user/admin/dashboard", "/user/admin/kyc", "/user/admin/fraud_detection",
            "/user/admin/international_compliance", "/user/admin/lending_compliance",
            "/user/admin/hmda", "/user/admin/activity_dashboard", "/user/admin/reporting",
            "/user/admin/users", "/user/admin/transactions", "/user/admin/advanced_search",
            "/user/admin/monitoring", "/user/admin/profile", "/user/admin/mfa_setup",
        ],
        "restricted_pages": [
            "/user/admin/management_panel", "/user/admin/settings", "/user/admin/vendor_hub",
            "/user/admin/treasury", "/user/admin/fund", "/user/admin/settlement",
            "/user/admin/ach_management", "/user/admin/blockchain", "/user/admin/currency_exchange",
            "/user/admin/bulk_operations",
        ],
        "permissions": [
            "users:view", "user:view", "users:suspend", "user:suspend", "users:freeze", "user:freeze",
            "kyc:review", "kyc:view", "kyc:approve", "kyc:reject", "kyc:verify",
            "transactions:view", "transaction:view", "deposits:view", "loans:view",
            "compliance:view", "compliance:manage", "compliance:report", "aml:view", "fraud:manage",
            "reports:view", "reports:generate", "reporting:view", "audit:view", "audit:export", "admin:view",
        ],
    },
    "SUPPORT": {
        "role": "SUPPORT",
        "title": "Customer Support Specialist",
        "default_account": "support@finanza.com",
        "badge_color": "#7c3aed",
        "summary": "Read-only customer service access across profiles, balances, transactions, and KYC status, plus customer password/lockout assistance.",
        "can_do": [
            "Search and view customer profiles, account status, and verification progress",
            "View transaction history, card status, bill pay records, and deposit status",
            "Assist customers with password resets and account lockout recovery",
            "View activity logs and basic operational dashboards",
        ],
        "cannot_do": [
            "Cannot credit, debit, or adjust any customer or institutional balances",
            "Cannot approve or reject KYC documents, loans, or transactions",
            "Cannot suspend, freeze, or delete user accounts",
            "Cannot create or manage Admin accounts, Treasury, or System Settings",
        ],
        "allowed_pages": [
            "/user/admin/dashboard", "/user/admin/users", "/user/admin/transactions",
            "/user/admin/advanced_search", "/user/admin/activity_dashboard",
            "/user/admin/monitoring", "/user/admin/profile", "/user/admin/mfa_setup",
        ],
        "restricted_pages": [
            "/user/admin/management_panel", "/user/admin/settings", "/user/admin/vendor_hub",
            "/user/admin/treasury", "/user/admin/fund", "/user/admin/settlement",
            "/user/admin/ach_management", "/user/admin/kyc", "/user/admin/bulk_operations",
            "/user/admin/lending", "/user/admin/lending_compliance", "/user/admin/hmda",
            "/user/admin/fraud_detection", "/user/admin/international_compliance",
            "/user/admin/blockchain", "/user/admin/currency_exchange", "/user/admin/bank_connect",
            "/user/admin/webhooks",
        ],
        "permissions": [
            "users:view", "user:view", "kyc:view",
            "transactions:view", "transaction:view",
            "deposits:view", "loans:view", "investments:view", "cards:view",
            "reports:view", "reporting:view", "audit:view", "admin:view", "support:manage",
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
    "users:create": ["user:create", "users:create"],
    "user:edit": ["user:edit", "users:edit"],
    "users:edit": ["user:edit", "users:edit"],
    "user:suspend": ["user:suspend", "users:suspend", "users:freeze", "user:freeze", "perm:users:suspend"],
    "users:suspend": ["user:suspend", "users:suspend", "users:freeze", "user:freeze", "perm:users:suspend"],
    "users:freeze": ["user:suspend", "users:suspend", "users:freeze", "user:freeze"],
    "user:delete": ["user:delete", "users:delete"],
    "users:delete": ["user:delete", "users:delete"],
    "users:bulk_actions": ["users:bulk_actions", "user:edit", "users:edit"],
    "ledger:adjust": ["ledger:adjust", "balance:adjust", "users:adjust_balance", "perm:balance:adjust"],
    "balance:adjust": ["ledger:adjust", "balance:adjust", "users:adjust_balance", "perm:balance:adjust"],
    "users:adjust_balance": ["ledger:adjust", "balance:adjust", "users:adjust_balance", "perm:balance:adjust"],
    "balance:reconcile": ["balance:reconcile", "treasury:manage", "ledger:adjust"],
    "kyc:review": ["kyc:review", "kyc:view", "kyc:approve", "kyc:reject", "kyc:verify"],
    "kyc:view": ["kyc:view", "kyc:review"],
    "kyc:approve": ["kyc:approve", "kyc:review", "perm:kyc:approve"],
    "kyc:reject": ["kyc:reject", "kyc:review", "perm:kyc:reject"],
    "kyc:verify": ["kyc:verify", "kyc:review", "kyc:approve"],
    "transactions:view": ["transactions:view", "transaction:view", "perm:transactions:view"],
    "transaction:view": ["transactions:view", "transaction:view", "perm:transactions:view"],
    "transactions:create": ["transactions:create", "transaction:create"],
    "transaction:create": ["transactions:create", "transaction:create"],
    "transaction:approve": ["transaction:approve", "transactions:approve", "payments:settle"],
    "transactions:approve": ["transaction:approve", "transactions:approve", "payments:settle"],
    "transaction:reject": ["transaction:reject", "transactions:reject", "transaction:cancel"],
    "transactions:reject": ["transaction:reject", "transactions:reject", "transaction:cancel"],
    "transaction:reverse": ["transaction:reverse", "transactions:reverse"],
    "transactions:reverse": ["transaction:reverse", "transactions:reverse"],
    "payments:settle": ["payments:settle", "settlement:manage", "ach:manage", "transaction:approve"],
    "audit:view": ["audit:view", "admin:view", "perm:audit:view"],
    "admin:view": ["admin:view", "audit:view", "users:view"],
    "admin:create": ["admin:create", "admin:manage"],
    "admin:manage": ["admin:manage", "admin:create"],
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


def normalize_admin_page_path(path: str) -> str:
    """Normalize an admin route path to canonical `/user/admin/<module>` form."""
    if not path:
        return "/user/admin/dashboard"
    clean = path.split("?")[0].rstrip("/")
    if not clean or clean in ("/user/admin", "/user/superadmin/dashboard"):
        return "/user/admin/dashboard"
    if clean.endswith(".html"):
        clean = clean[:-5]
    parts = clean.split("/")
    slug = parts[-1].replace("-", "_")
    if slug.startswith("admin_") and slug != "admin_management_panel":
        slug = slug[len("admin_"):]
    alias_map = {
        "dashboard_hub": "dashboard",
        "superadmin_dashboard": "dashboard",
        "overview": "monitoring",
        "executive_dashboard": "monitoring",
        "reports": "reporting",
        "submissions": "kyc",
        "compliance": "international_compliance",
        "wire_transfer": "settlement",
    }
    slug = alias_map.get(slug, slug)
    return f"/user/admin/{slug}"


def can_access_admin_page(current_user, page_path: str) -> bool:
    """
    Determine whether `current_user` is permitted to open `page_path` according to ROLE_MATRIX
    and any custom permissions granted to the admin.
    """
    if not current_user or not getattr(current_user, "is_admin", False):
        return False
    role = resolve_admin_role(current_user)
    if role == "SUPER_ADMIN":
        return True

    canonical = normalize_admin_page_path(page_path)
    always_allowed = {
        "/user/admin/dashboard",
        "/user/admin/profile",
        "/user/admin/mfa_setup",
    }
    if canonical in always_allowed:
        return True

    # Check if custom permissions explicitly unlock a module
    page_perm_map = {
        "/user/admin/management_panel": "admin:manage",
        "/user/admin/settings": "system:config",
        "/user/admin/vendor_hub": "system:config",
        "/user/admin/treasury": "treasury:view",
        "/user/admin/fund": "balance:adjust",
        "/user/admin/settlement": "payments:settle",
        "/user/admin/ach_management": "payments:settle",
        "/user/admin/kyc": "kyc:view",
        "/user/admin/bulk_operations": "users:bulk_actions",
    }

    role_spec = ROLE_MATRIX.get(role, ROLE_MATRIX["SUPPORT"])
    restricted = {normalize_admin_page_path(p) for p in role_spec.get("restricted_pages", [])}
    allowed = role_spec.get("allowed_pages", [])

    if canonical in restricted:
        # Allow if admin was granted explicit custom permission for this page
        req_perm = page_perm_map.get(canonical)
        if req_perm and getattr(current_user, "custom_permissions", None) and has_permission(current_user, req_perm):
            return True
        return False

    if "*" in allowed:
        return True

    normalized_allowed = {normalize_admin_page_path(p) for p in allowed}
    if canonical in normalized_allowed:
        return True

    return True


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
