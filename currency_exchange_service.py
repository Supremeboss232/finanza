# currency_exchange_service.py
# Multi-currency support and currency exchange service

from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import Optional, Tuple
import logging
import aiohttp

log = logging.getLogger(__name__)


class CurrencyService:
    """Service for managing multi-currency accounts"""
    
    @staticmethod
    async def create_multi_currency_account(
        db: Session,
        account_id: int,
        base_currency: str,
        secondary_currencies: Optional[list] = None,
        created_by: Optional[int] = None
    ) -> dict:
        """
        Enable multi-currency support on account
        
        Args:
            base_currency: Primary currency (USD, CAD, GBP, EUR, etc.)
            secondary_currencies: List of additional supported currencies
        
        Returns:
            {"success": bool, "account_id": int}
        """
        try:
            from models import Account, MultiCurrencyAccount
            
            # Verify account exists
            account = db.query(Account).filter(Account.id == account_id).first()
            if not account:
                return {"success": False, "error": "Account not found"}
            
            # Check if already multi-currency
            existing = db.query(MultiCurrencyAccount).filter(
                MultiCurrencyAccount.account_id == account_id
            ).first()
            
            if existing:
                return {"success": False, "error": "Account already multi-currency"}
            
            # Create multi-currency record
            mca = MultiCurrencyAccount(
                account_id=account_id,
                base_currency=base_currency,
                secondary_currencies=",".join(secondary_currencies) if secondary_currencies else None,
                is_active=True,
                created_by=created_by,
                created_at=datetime.utcnow()
            )
            
            db.add(mca)
            
            # Create currency sub-accounts
            if secondary_currencies:
                from models import CurrencySubAccount
                
                for currency in secondary_currencies:
                    sub_account = CurrencySubAccount(
                        account_id=account_id,
                        currency=currency,
                        balance=0.0,
                        created_at=datetime.utcnow()
                    )
                    db.add(sub_account)
            
            db.commit()
            
            log.info(f"Multi-currency account created: {account_id} - {base_currency}")
            
            return {
                "success": True,
                "account_id": account_id,
                "base_currency": base_currency,
                "secondary_currencies": secondary_currencies or []
            }
        except Exception as e:
            db.rollback()
            log.error(f"Error creating multi-currency account: {e}")
            return {"success": False, "error": str(e)}
    
    @staticmethod
    async def get_currency_balances(
        db: Session,
        account_id: int
    ) -> dict:
        """
        Get all currency balances for multi-currency account
        
        Returns:
            {"success": bool, "balances": {...}}
        """
        try:
            from models import Account, MultiCurrencyAccount, CurrencySubAccount
            
            account = db.query(Account).filter(Account.id == account_id).first()
            if not account:
                return {"success": False, "error": "Account not found"}
            
            mca = db.query(MultiCurrencyAccount).filter(
                MultiCurrencyAccount.account_id == account_id
            ).first()
            
            if not mca:
                return {"success": False, "error": "Not a multi-currency account"}
            
            # Get base currency balance
            balances = {
                mca.base_currency: account.balance
            }
            
            # Get secondary currency balances
            sub_accounts = db.query(CurrencySubAccount).filter(
                CurrencySubAccount.account_id == account_id
            ).all()
            
            for sub in sub_accounts:
                balances[sub.currency] = sub.balance
            
            return {
                "success": True,
                "account_id": account_id,
                "base_currency": mca.base_currency,
                "balances": balances,
                "total_currencies": len(balances)
            }
        except Exception as e:
            log.error(f"Error getting currency balances: {e}")
            return {"success": False, "error": str(e)}
    
    @staticmethod
    async def add_currency_to_account(
        db: Session,
        account_id: int,
        currency: str,
        created_by: Optional[int] = None
    ) -> dict:
        """
        Add new currency to multi-currency account
        
        Returns:
            {"success": bool, "currency": str}
        """
        try:
            from models import MultiCurrencyAccount, CurrencySubAccount
            
            mca = db.query(MultiCurrencyAccount).filter(
                MultiCurrencyAccount.account_id == account_id
            ).first()
            
            if not mca:
                return {"success": False, "error": "Not a multi-currency account"}
            
            # Check if currency already exists
            existing = db.query(CurrencySubAccount).filter(
                CurrencySubAccount.account_id == account_id,
                CurrencySubAccount.currency == currency
            ).first()
            
            if existing:
                return {"success": False, "error": f"Account already has {currency}"}
            
            # Add new currency sub-account
            sub_account = CurrencySubAccount(
                account_id=account_id,
                currency=currency,
                balance=0.0,
                created_at=datetime.utcnow()
            )
            
            db.add(sub_account)
            
            # Update secondary currencies list
            currencies = mca.secondary_currencies.split(",") if mca.secondary_currencies else []
            if currency not in currencies:
                currencies.append(currency)
                mca.secondary_currencies = ",".join(currencies)
            
            db.commit()
            
            log.info(f"Currency added to account: {account_id} - {currency}")
            
            return {
                "success": True,
                "account_id": account_id,
                "currency": currency,
                "balance": 0.0
            }
        except Exception as e:
            db.rollback()
            log.error(f"Error adding currency: {e}")
            return {"success": False, "error": str(e)}


class ExchangeRateService:
    """Service for managing exchange rates"""
    
    @staticmethod
    async def get_exchange_rate(
        db: Session,
        from_currency: str,
        to_currency: str
    ) -> dict:
        """
        Get current exchange rate between currencies
        
        Returns:
            {"success": bool, "rate": float, "timestamp": str}
        """
        try:
            from models import ExchangeRate
            
            # Check cache first (within last hour)
            cutoff_time = datetime.utcnow() - timedelta(hours=1)
            
            rate_record = db.query(ExchangeRate).filter(
                ExchangeRate.from_currency == from_currency,
                ExchangeRate.to_currency == to_currency,
                ExchangeRate.last_updated >= cutoff_time
            ).first()
            
            if rate_record:
                return {
                    "success": True,
                    "from_currency": from_currency,
                    "to_currency": to_currency,
                    "rate": rate_record.rate,
                    "timestamp": rate_record.last_updated.isoformat(),
                    "source": "cached"
                }
            
            # Rate not in cache - would fetch from external API in production
            # For now, return simulated rate
            simulated_rate = await ExchangeRateService._get_simulated_rate(
                from_currency,
                to_currency
            )
            
            # Store in cache
            if not rate_record:
                rate_record = ExchangeRate(
                    from_currency=from_currency,
                    to_currency=to_currency,
                    rate=simulated_rate,
                    last_updated=datetime.utcnow()
                )
                db.add(rate_record)
            else:
                rate_record.rate = simulated_rate
                rate_record.last_updated = datetime.utcnow()
            
            db.commit()
            
            log.info(f"Exchange rate retrieved: {from_currency}/{to_currency} = {simulated_rate}")
            
            return {
                "success": True,
                "from_currency": from_currency,
                "to_currency": to_currency,
                "rate": simulated_rate,
                "timestamp": datetime.utcnow().isoformat(),
                "source": "live"
            }
        except Exception as e:
            log.error(f"Error getting exchange rate: {e}")
            return {"success": False, "error": str(e)}
    
    @staticmethod
    async def _get_simulated_rate(
        from_currency: str,
        to_currency: str
    ) -> float:
        """
        Get simulated exchange rate (would call external API in production)
        
        Common rates as of 2024:
        - USD/CAD: 1.35
        - USD/GBP: 0.79
        - USD/EUR: 0.92
        - USD/AUD: 1.51
        - USD/JPY: 110.50
        """
        rates = {
            ("USD", "CAD"): 1.35,
            ("USD", "GBP"): 0.79,
            ("USD", "EUR"): 0.92,
            ("USD", "AUD"): 1.51,
            ("USD", "JPY"): 110.50,
            ("CAD", "USD"): 0.74,
            ("GBP", "USD"): 1.27,
            ("EUR", "USD"): 1.09,
            ("AUD", "USD"): 0.66,
            ("JPY", "USD"): 0.009,
        }
        
        # Return rate or inverse if available
        if (from_currency, to_currency) in rates:
            return rates[(from_currency, to_currency)]
        elif (to_currency, from_currency) in rates:
            return 1 / rates[(to_currency, from_currency)]
        else:
            # Default to 1.0 if not in mapping
            return 1.0
    
    @staticmethod
    async def get_rate_history(
        db: Session,
        from_currency: str,
        to_currency: str,
        days: int = 30
    ) -> dict:
        """
        Get exchange rate history
        
        Returns:
            {"success": bool, "history": [...]}
        """
        try:
            from models import ExchangeRateHistory
            
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            history = db.query(ExchangeRateHistory).filter(
                ExchangeRateHistory.from_currency == from_currency,
                ExchangeRateHistory.to_currency == to_currency,
                ExchangeRateHistory.timestamp >= cutoff_date
            ).order_by(ExchangeRateHistory.timestamp).all()
            
            return {
                "success": True,
                "from_currency": from_currency,
                "to_currency": to_currency,
                "days": days,
                "record_count": len(history),
                "history": [
                    {
                        "date": h.timestamp.date().isoformat(),
                        "rate": h.rate,
                        "high": h.high_rate,
                        "low": h.low_rate
                    }
                    for h in history
                ]
            }
        except Exception as e:
            log.error(f"Error getting rate history: {e}")
            return {"success": False, "error": str(e)}


class CurrencyConversionService:
    """Service for currency conversions and transfers"""
    
    @staticmethod
    async def convert_currency(
        db: Session,
        amount: float,
        from_currency: str,
        to_currency: str
    ) -> dict:
        """
        Convert amount from one currency to another
        
        Returns:
            {"success": bool, "converted_amount": float, "rate": float}
        """
        try:
            # Get exchange rate
            rate_result = await ExchangeRateService.get_exchange_rate(
                db=db,
                from_currency=from_currency,
                to_currency=to_currency
            )
            
            if not rate_result["success"]:
                return {"success": False, "error": rate_result["error"]}
            
            rate = rate_result["rate"]
            converted_amount = amount * rate
            
            log.info(f"Currency conversion: {amount} {from_currency} = {converted_amount} {to_currency}")
            
            return {
                "success": True,
                "original_amount": amount,
                "original_currency": from_currency,
                "converted_amount": round(converted_amount, 2),
                "converted_currency": to_currency,
                "exchange_rate": rate
            }
        except Exception as e:
            log.error(f"Error converting currency: {e}")
            return {"success": False, "error": str(e)}
    
    @staticmethod
    async def cross_currency_transfer(
        db: Session,
        from_account_id: int,
        to_account_id: int,
        from_currency: str,
        to_currency: str,
        amount: float,
        fee_type: str = "standard"
    ) -> dict:
        """
        Transfer funds between accounts in different currencies
        
        Args:
            fee_type: standard (1%), premium (0.5%), vip (0.25%)
        
        Returns:
            {"success": bool, "transaction_id": int}
        """
        try:
            from models import Account, Transaction, CurrencyTransfer
            
            # Verify accounts exist
            from_account = db.query(Account).filter(Account.id == from_account_id).first()
            to_account = db.query(Account).filter(Account.id == to_account_id).first()
            
            if not from_account or not to_account:
                return {"success": False, "error": "Account not found"}
            
            # Convert currency
            conversion = await CurrencyConversionService.convert_currency(
                db=db,
                amount=amount,
                from_currency=from_currency,
                to_currency=to_currency
            )
            
            if not conversion["success"]:
                return {"success": False, "error": conversion["error"]}
            
            converted_amount = conversion["converted_amount"]
            exchange_rate = conversion["exchange_rate"]
            
            # Calculate FX fee
            fee_rates = {
                "standard": 0.01,
                "premium": 0.005,
                "vip": 0.0025
            }
            fx_fee = amount * fee_rates.get(fee_type, 0.01)
            fx_fee_converted = fx_fee * exchange_rate
            
            # Verify sufficient balance
            if from_account.available_balance < amount:
                return {"success": False, "error": "Insufficient balance"}
            
            # Execute transfer
            from_account.available_balance -= amount
            from_account.balance -= amount
            
            to_account.available_balance += converted_amount
            to_account.balance += converted_amount
            
            # Record transactions
            from_transaction = Transaction(
                account_id=from_account_id,
                user_id=from_account.owner_id,
                amount=amount,
                transaction_type="cross_currency_transfer_out",
                direction="debit",
                status="completed",
                description=f"Cross-currency transfer to {to_account_id} ({to_currency})",
                created_at=datetime.utcnow()
            )
            
            to_transaction = Transaction(
                account_id=to_account_id,
                user_id=to_account.owner_id,
                amount=converted_amount,
                transaction_type="cross_currency_transfer_in",
                direction="credit",
                status="completed",
                description=f"Cross-currency transfer from {from_account_id} ({from_currency})",
                created_at=datetime.utcnow()
            )
            
            db.add(from_transaction)
            db.add(to_transaction)
            
            # Record currency transfer details
            currency_transfer = CurrencyTransfer(
                from_account_id=from_account_id,
                to_account_id=to_account_id,
                from_currency=from_currency,
                to_currency=to_currency,
                from_amount=amount,
                to_amount=converted_amount,
                exchange_rate=exchange_rate,
                fx_fee=fx_fee,
                fee_type=fee_type,
                from_transaction_id=from_transaction.id,
                to_transaction_id=to_transaction.id,
                transfer_date=datetime.utcnow()
            )
            
            db.add(currency_transfer)
            db.commit()
            
            log.info(f"Cross-currency transfer: {amount} {from_currency} → {converted_amount} {to_currency} (fee: {fx_fee})")
            
            return {
                "success": True,
                "from_transaction_id": from_transaction.id,
                "to_transaction_id": to_transaction.id,
                "from_amount": amount,
                "to_amount": converted_amount,
                "exchange_rate": exchange_rate,
                "fx_fee": fx_fee,
                "fee_type": fee_type
            }
        except Exception as e:
            db.rollback()
            log.error(f"Error in cross-currency transfer: {e}")
            return {"success": False, "error": str(e)}
    
    @staticmethod
    async def get_fx_rates(
        db: Session,
        base_currency: str
    ) -> dict:
        """
        Get FX rates for all major currencies from base
        
        Returns:
            {"success": bool, "rates": {...}}
        """
        try:
            major_currencies = ["USD", "CAD", "GBP", "EUR", "AUD", "JPY"]
            rates = {}
            
            for currency in major_currencies:
                if currency != base_currency:
                    rate_result = await ExchangeRateService.get_exchange_rate(
                        db=db,
                        from_currency=base_currency,
                        to_currency=currency
                    )
                    
                    if rate_result["success"]:
                        rates[currency] = rate_result["rate"]
            
            return {
                "success": True,
                "base_currency": base_currency,
                "timestamp": datetime.utcnow().isoformat(),
                "rates": rates
            }
        except Exception as e:
            log.error(f"Error getting FX rates: {e}")
            return {"success": False, "error": str(e)}
