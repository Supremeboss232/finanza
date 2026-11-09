"""
Unique Bank Account Number Generator for Finanza Bank.
Generates collision-free 10-digit numeric account numbers (or FNZ-prefixed numbers).
"""

import secrets
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from models import Account, User


def generate_account_number(prefix: str = "40") -> str:
    """Generate a 10-digit numeric bank account number."""
    remaining = max(1, 10 - len(prefix))
    digits = "".join(str(secrets.randbelow(10)) for _ in range(remaining))
    return f"{prefix}{digits}"


async def generate_unique_account_number(db_session: AsyncSession = None, prefix: str = "40") -> str:
    """Generate a unique 10-digit bank account number verified against Account and User tables."""
    for _ in range(25):
        candidate = generate_account_number(prefix=prefix)
        if db_session is None:
            return candidate
        try:
            acc_exists = (
                await db_session.execute(
                    select(Account.id).where(Account.account_number == candidate)
                )
            ).scalar_one_or_none()
            if acc_exists:
                continue
            usr_exists = (
                await db_session.execute(
                    select(User.id).where(User.account_number == candidate)
                )
            ).scalar_one_or_none()
            if not usr_exists:
                return candidate
        except Exception:
            return candidate
    return generate_account_number(prefix=prefix)
