"""
Reconciliation service for startup verification and balance integrity checks.
"""

import logging
from typing import Dict, List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from balance_service_ledger import BalanceServiceLedger
from models import Account

log = logging.getLogger(__name__)


class ReconciliationService:
    """Verify that ledger-based balances match stored account balances."""

    @staticmethod
    async def check_account_balance(db: AsyncSession, account_id: int) -> Dict[str, object]:
        """Return balance reconciliation details for one account."""
        account_result = await db.execute(select(Account).where(Account.id == account_id))
        account = account_result.scalar_one_or_none()

        if not account:
            return {"is_valid": False, "error": "Account not found"}

        stored_balance = float(account.balance or 0)
        ledger_balance = await BalanceServiceLedger.get_account_balance(db, account_id)
        discrepancy = abs(stored_balance - ledger_balance)

        return {
            "account_id": account_id,
            "account_number": account.account_number,
            "stored_balance": stored_balance,
            "ledger_balance": ledger_balance,
            "discrepancy": discrepancy,
            "is_valid": discrepancy < 0.01,
        }

    @staticmethod
    async def verify_all_accounts(db: AsyncSession) -> Dict[str, object]:
        """Run a reconciliation pass over all accounts."""
        accounts_result = await db.execute(select(Account))
        accounts = accounts_result.scalars().all()

        results = {
            "total": len(accounts),
            "valid": 0,
            "invalid": 0,
            "invalid_accounts": [],
        }

        for account in accounts:
            check = await ReconciliationService.check_account_balance(db, account.id)
            if check.get("is_valid"):
                results["valid"] += 1
            else:
                results["invalid"] += 1
                results["invalid_accounts"].append({
                    "id": account.id,
                    "account_number": account.account_number,
                    "discrepancy": check.get("discrepancy", 0.0),
                })

        if results["invalid"]:
            log.warning("Balance reconciliation found %s inconsistent account(s)", results["invalid"])
        else:
            log.info("Balance reconciliation passed for %s account(s)", results["total"])

        return results
