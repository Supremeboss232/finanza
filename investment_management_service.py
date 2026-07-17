"""
Investment Management Service

Handles investment lifecycle:
1. Portfolio setup and account opening
2. Asset allocation and diversification
3. Automatic rebalancing
4. Performance tracking and reporting
5. Dividend and interest accrual
6. Withdrawal and liquidation
"""

from decimal import Decimal
from typing import Dict, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timedelta
import json
import random
import logging

from models import User, Investment, Account, Transaction, Ledger, AuditLog

logger = logging.getLogger(__name__)


class InvestmentManagementService:
    """Service for managing user investments and portfolios."""

    # Asset classes with risk profiles and expected returns
    ASSET_CLASSES = {
        "stocks": {"risk": 0.8, "annual_return": 0.09, "allocation_min": 0.0, "allocation_max": 1.0},
        "bonds": {"risk": 0.3, "annual_return": 0.04, "allocation_min": 0.0, "allocation_max": 1.0},
        "real_estate": {"risk": 0.5, "annual_return": 0.06, "allocation_min": 0.0, "allocation_max": 0.5},
        "commodities": {"risk": 0.7, "annual_return": 0.05, "allocation_min": 0.0, "allocation_max": 0.3},
        "cash": {"risk": 0.0, "annual_return": 0.03, "allocation_min": 0.0, "allocation_max": 0.2},
    }

    # Risk profiles: conservative, moderate, aggressive
    RISK_PROFILES = {
        "conservative": {"stocks": 0.20, "bonds": 0.50, "real_estate": 0.15, "commodities": 0.05, "cash": 0.10},
        "moderate": {"stocks": 0.50, "bonds": 0.25, "real_estate": 0.15, "commodities": 0.05, "cash": 0.05},
        "aggressive": {"stocks": 0.70, "bonds": 0.10, "real_estate": 0.15, "commodities": 0.05, "cash": 0.00},
    }

    @staticmethod
    async def create_investment(
        db: AsyncSession,
        user_id: int,
        investment_type: str,
        amount: Decimal,
        annual_return_rate: Decimal = None,
    ) -> Dict:
        """
        Create a new investment.
        
        Investment Types: stocks, bonds, real_estate, commodities, cash, mutual_fund, etf
        """
        try:
            user = await db.get(User, user_id)
            if not user:
                return {"success": False, "error": "User not found"}

            if user.kyc_status != "approved":
                return {"success": False, "error": "KYC approval required"}

            # Get user's primary account
            result = await db.execute(
                select(Account).where(Account.owner_id == user_id).limit(1)
            )
            account = result.scalar_one_or_none()

            if not account:
                return {"success": False, "error": "User account not found"}

            # Validate account has sufficient funds
            if account.balance < amount:
                return {"success": False, "error": "Insufficient funds"}

            # Set return rate based on investment type
            if annual_return_rate is None:
                    if investment_type in InvestmentManagementService.ASSET_CLASSES:
                        annual_return_rate = Decimal(str(InvestmentManagementService.ASSET_CLASSES[investment_type]["annual_return"]))
                    annual_return_rate = Decimal("0.05")  # Default 5%

            # Create investment record
            investment = Investment(
                user_id=user_id,
                investment_type=investment_type,
                amount=amount,
                current_value=amount,
                annual_return_rate=annual_return_rate,
                status="active",
            )
            db.add(investment)
            await db.flush()

            # Create transaction
            transaction = Transaction(
                user_id=user_id,
                account_id=account.id,
                transaction_type="investment_purchase",
                amount=amount,
                direction="debit",
                status="completed",
                description=f"Investment in {investment_type}",
                reference_number=f"INV-{investment.id}",
            )
            db.add(transaction)
            await db.flush()

            # Create ledger entries
            now = datetime.utcnow()

            debit = Ledger(
                user_id=user_id,
                entry_type="debit",
                amount=amount,
                transaction_id=transaction.id,
                source_user_id=user_id,
                destination_user_id=1,  # System account (investment reserve)
                description=f"Debit: Investment in {investment_type}",
                reference_number=f"INV-{investment.id}",
                status="posted",
                posted_at=now,
            )
            db.add(debit)
            await db.flush()

            credit = Ledger(
                user_id=1,
                entry_type="credit",
                amount=amount,
                transaction_id=transaction.id,
                related_entry_id=debit.id,
                source_user_id=user_id,
                destination_user_id=1,
                description=f"Credit: Investment in {investment_type}",
                reference_number=f"INV-{investment.id}",
                status="posted",
                posted_at=now,
            )
            db.add(credit)
            await db.flush()

            debit.related_entry_id = credit.id
            db.add(debit)

            # Update account balance
            account.balance = account.balance - amount
            db.add(account)

            await db.commit()

            logger.info(f"Investment {investment.id} created for user {user_id}: ${amount} {investment_type}")

            return {
                "success": True,
                "investment_id": investment.id,
                "investment_type": investment_type,
                "amount": float(amount),
                "current_value": float(amount),
                "annual_return_rate": float(annual_return_rate),
                "status": "active",
            }

        except Exception as e:
            await db.rollback()
            logger.error(f"Investment creation failed: {str(e)}")
            return {"success": False, "error": str(e)}

    @staticmethod
    async def accrue_returns(
        db: AsyncSession,
        investment_id: int,
        days_elapsed: int = 1,
    ) -> Dict:
        """
        Accrue investment returns (daily compounding).
        
        In production: call via scheduled job (daily).
        """
        try:
            investment = await db.get(Investment, investment_id)
            if not investment:
                return {"success": False, "error": "Investment not found"}

            if investment.status != "active":
                return {"success": False, "error": f"Cannot accrue returns for {investment.status} investment"}

            # Calculate daily return
            daily_rate = investment.annual_return_rate / 365
            accrued_value = investment.current_value * (1 + daily_rate) ** days_elapsed
            accrued_return = accrued_value - investment.current_value

            # Update investment
            investment.current_value = accrued_value
            investment.interest_earned = (investment.interest_earned or 0) + accrued_return
            db.add(investment)
            await db.commit()

            logger.info(f"Investment {investment_id} accrued: ${accrued_return:.2f}")

            return {
                "success": True,
                "investment_id": investment_id,
                "accrued_return": float(accrued_return),
                "new_value": float(accrued_value),
            }

        except Exception as e:
            await db.rollback()
            logger.error(f"Return accrual failed: {str(e)}")
            return {"success": False, "error": str(e)}

    @staticmethod
    async def rebalance_portfolio(
        db: AsyncSession,
        user_id: int,
        target_profile: str = "moderate",
    ) -> Dict:
        """
        Rebalance user's portfolio to target allocation.
        
        Target Profiles: conservative, moderate, aggressive
        """
        try:
            user = await db.get(User, user_id)
            if not user:
                return {"success": False, "error": "User not found"}

            if target_profile not in InvestmentManagementService.RISK_PROFILES:
                return {"success": False, "error": f"Invalid profile: {target_profile}"}

            # Get all user investments
            result = await db.execute(
                select(Investment).where(
                    Investment.user_id == user_id,
                    Investment.status == "active"
                )
            )
            investments = result.scalars().all()

            if not investments:
                return {"success": False, "error": "No active investments found"}

            # Calculate total portfolio value
            total_value = sum(inv.current_value for inv in investments)

            # Get target allocation and normalize it for the assets the user actually holds
            target_allocation = InvestmentManagementService.RISK_PROFILES[target_profile]
            present_types = {inv.investment_type for inv in investments}
            raw_total = sum(target_allocation.get(inv_type, 0) for inv_type in present_types)

            normalized_allocation = {}
            for inv_type in present_types:
                raw_pct = target_allocation.get(inv_type, 0)
                normalized_allocation[inv_type] = (
                    Decimal(str(raw_pct)) / Decimal(str(raw_total))
                    if raw_total > 0 else Decimal("0")
                )

            adjustments = {}
            for investment in investments:
                inv_type = investment.investment_type
                target_pct = normalized_allocation.get(inv_type, Decimal("0"))
                target_value = (total_value * target_pct).quantize(Decimal("0.01"))
                adjustment_needed = target_value - investment.current_value

                if abs(adjustment_needed) > Decimal("10"):
                    investment.current_value = target_value
                    db.add(investment)
                    adjustments[inv_type] = float(adjustment_needed)

            await db.commit()

            logger.info(f"Portfolio for user {user_id} rebalanced to {target_profile}")

            return {
                "success": True,
                "user_id": user_id,
                "target_profile": target_profile,
                "total_portfolio_value": float(total_value),
                "adjustments": adjustments,
            }

        except Exception as e:
            await db.rollback()
            logger.error(f"Portfolio rebalancing failed: {str(e)}")
            return {"success": False, "error": str(e)}

    @staticmethod
    async def liquidate_investment(
        db: AsyncSession,
        investment_id: int,
        user_id: int,
    ) -> Dict:
        """Liquidate an investment and return proceeds to user account."""
        try:
            investment = await db.get(Investment, investment_id)
            if not investment or investment.user_id != user_id:
                return {"success": False, "error": "Investment not found"}

            if investment.status != "active":
                return {"success": False, "error": f"Cannot liquidate {investment.status} investment"}

            # Get user account
            result = await db.execute(
                select(Account).where(Account.owner_id == user_id).limit(1)
            )
            account = result.scalar_one_or_none()

            if not account:
                return {"success": False, "error": "User account not found"}

            liquidation_value = investment.current_value

            # Create transaction
            transaction = Transaction(
                user_id=user_id,
                account_id=account.id,
                transaction_type="investment_liquidation",
                amount=liquidation_value,
                direction="credit",
                status="completed",
                description=f"Liquidation of {investment.investment_type} investment",
                reference_number=f"LIQ-{investment_id}",
            )
            db.add(transaction)
            await db.flush()

            # Create ledger entries
            now = datetime.utcnow()

            debit = Ledger(
                user_id=1,
                entry_type="debit",
                amount=liquidation_value,
                transaction_id=transaction.id,
                source_user_id=1,
                destination_user_id=user_id,
                description="Debit: Investment liquidation",
                reference_number=f"LIQ-{investment_id}",
                status="posted",
                posted_at=now,
            )
            db.add(debit)
            await db.flush()

            credit = Ledger(
                user_id=user_id,
                entry_type="credit",
                amount=liquidation_value,
                transaction_id=transaction.id,
                related_entry_id=debit.id,
                source_user_id=1,
                destination_user_id=user_id,
                description="Credit: Investment liquidation proceeds",
                reference_number=f"LIQ-{investment_id}",
                status="posted",
                posted_at=now,
            )
            db.add(credit)
            await db.flush()

            debit.related_entry_id = credit.id
            db.add(debit)

            # Update investment status
            investment.status = "liquidated"
            db.add(investment)

            # Update account balance
            account.balance = account.balance + liquidation_value
            db.add(account)

            await db.commit()

            logger.info(f"Investment {investment_id} liquidated: ${liquidation_value}")

            return {
                "success": True,
                "investment_id": investment_id,
                "liquidation_value": float(liquidation_value),
                "status": "liquidated",
            }

        except Exception as e:
            await db.rollback()
            logger.error(f"Investment liquidation failed: {str(e)}")
            return {"success": False, "error": str(e)}

    @staticmethod
    async def get_portfolio_summary(db: AsyncSession, user_id: int) -> Dict:
        """Get user's complete portfolio summary."""
        try:
            result = await db.execute(
                select(Investment).where(Investment.user_id == user_id)
            )
            investments = result.scalars().all()

            active_investments = [inv for inv in investments if inv.status == "active"]

            total_value = sum(inv.current_value for inv in active_investments)
            total_invested = sum(inv.amount for inv in active_investments)
            total_returns = sum(inv.interest_earned or 0 for inv in active_investments)

            allocation = {}
            for investment in active_investments:
                inv_type = investment.investment_type
                pct = (investment.current_value / total_value * 100) if total_value > 0 else 0
                allocation[inv_type] = round(float(pct), 2)

            return {
                "success": True,
                "user_id": user_id,
                "total_portfolio_value": float(total_value),
                "total_invested": float(total_invested),
                "total_returns": float(total_returns),
                "return_percentage": float((total_returns / total_invested * 100)) if total_invested > 0 else 0,
                "allocation": allocation,
                "investments_count": len(active_investments),
                "investments": [
                    {
                        "investment_id": inv.id,
                        "investment_type": inv.investment_type,
                        "amount": float(inv.amount),
                        "current_value": float(inv.current_value),
                        "interest_earned": float(inv.interest_earned or 0),
                        "annual_return_rate": float(inv.annual_return_rate),
                        "status": inv.status,
                    }
                    for inv in active_investments
                ],
            }

        except Exception as e:
            logger.error(f"Failed to get portfolio summary: {str(e)}")
            return {"success": False, "error": str(e)}
