"""Startup helpers for reserve account creation and system verification."""

import logging
from datetime import datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from auth_utils import get_password_hash
from models import Account, Ledger, Transaction, User
from services.reconciliation_service import ReconciliationService

log = logging.getLogger(__name__)


async def ensure_system_reserve_account(db: AsyncSession) -> bool:
    """Ensure the treasury reserve account exists and is seeded."""
    try:
        system_user_result = await db.execute(select(User).where(User.id == 1))
        system_user = system_user_result.scalar_one_or_none()
        if not system_user:
            system_user = User(
                id=1,
                full_name="System Reserve / Treasury",
                email="sysreserve@finanza.com",
                hashed_password=get_password_hash("Supposedbe5"),
                is_active=True,
                is_admin=True,
                is_verified=True,
                kyc_status="approved",
            )
            db.add(system_user)
            await db.flush()
            log.info("Created system reserve user")

        reserve_result = await db.execute(
            select(Account).where(Account.account_number == "SYS-RESERVE-0001")
        )
        reserve_account = reserve_result.scalar_one_or_none()

        if reserve_account:
            log.info("System reserve account already exists")
            return True

        reserve_account = Account(
            owner_id=1,
            account_number="SYS-RESERVE-0001",
            account_type="treasury",
            balance=10_000_000.0,
            currency="USD",
            status="active",
            kyc_level="full",
            is_admin_account=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        db.add(reserve_account)
        await db.flush()

        seed_transaction = Transaction(
            user_id=1,
            account_id=reserve_account.id,
            amount=10_000_000.0,
            transaction_type="system_seed",
            direction="credit",
            status="completed",
            description="System Reserve Account initialization seed",
        )
        db.add(seed_transaction)
        await db.flush()

        db.add(
            Ledger(
                user_id=1,
                entry_type="credit",
                amount=Decimal("10000000.00"),
                transaction_id=seed_transaction.id,
                description="System Reserve Account initialization seed",
                status="posted",
            )
        )

        await db.commit()
        log.info("Created system reserve account SYS-RESERVE-0001")
        return True

    except Exception as exc:
        await db.rollback()
        log.exception("Failed to create system reserve account: %s", exc)
        return False


async def startup_verification(db: AsyncSession) -> dict:
    """Run startup safety checks for reserve balances and reconciliation."""
    try:
        reserve_ok = await ensure_system_reserve_account(db)
        results = await ReconciliationService.verify_all_accounts(db)

        return {
            "reserve_account_ok": reserve_ok,
            "reconciliation": results,
        }
    except Exception as exc:
        log.exception("Startup verification failed: %s", exc)
        return {"reserve_account_ok": False, "reconciliation": {"invalid": 1}, "error": str(exc)}
