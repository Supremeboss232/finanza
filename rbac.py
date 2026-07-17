from fastapi import Depends, HTTPException, status
from typing import Callable, List, Optional

from deps import get_current_user

# Role definitions and permission matrix.
# Uses both `admin_role` on the User model and optional lower-level role strings.
ROLES = {
    "super_admin": {
        "permissions": ["*"]
    },
    "admin": {
        "permissions": [
            "loans:credit_decision",
            "loans:underwrite",
            "loans:disburse",
            "payments:settle",
            "cards:approve",
            "kyc:review",
            "ledger:adjust",
            "transactions:view",
            "transactions:create",
            "deposits:view",
            "deposits:approve",
            "investments:view",
            "investments:manage",
            "cards:view",
            "reporting:view",
            "audit:view",
            "users:view",
        ]
    },
    "treasury": {
        "permissions": [
            "payments:settle",
            "deposits:approve",
            "ledger:adjust",
            "transactions:view",
            "transactions:create",
        ]
    },
    "compliance": {
        "permissions": [
            "kyc:review",
            "audit:view",
            "transactions:view",
        ]
    },
    "support": {
        "permissions": [
            "users:view",
            "support:manage",
        ]
    }
}

ADMIN_ROLE_ALIASES = {
    "SUPER_ADMIN": "super_admin",
    "ADMIN": "admin",
    "TREASURY": "treasury",
    "COMPLIANCE": "compliance",
    "SUPPORT": "support",
    "STANDARD": "support",
}


def _normalize_roles(current_user) -> List[str]:
    roles: List[str] = []

    admin_role = getattr(current_user, "admin_role", None)
    if isinstance(admin_role, str):
        mapped = ADMIN_ROLE_ALIASES.get(admin_role.upper(), admin_role.lower())
        roles.append(mapped)

    user_roles = getattr(current_user, "roles", None) or getattr(current_user, "role", None)
    if user_roles:
        if isinstance(user_roles, str):
            roles.extend([user_roles.lower()])
        elif isinstance(user_roles, list):
            roles.extend([str(r).lower() for r in user_roles])

    return [role for role in roles if role]


def require_permission(permission: str) -> Callable:
    async def _checker(current_user = Depends(get_current_user)):
        # Admin shortcut: any admin user can perform actions unless explicitly restricted
        if getattr(current_user, "is_admin", False):
            return True

        normalized_roles = _normalize_roles(current_user)
        if not normalized_roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied")

        for role in normalized_roles:
            permissions = ROLES.get(role, {}).get("permissions", [])
            if "*" in permissions or permission in permissions:
                return True

        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied")

    return _checker
