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
    """Service for managing exchange rates, backed by live Fixer.io data."""

    # Common currency pairs refreshed by refresh_all_rates()
    COMMON_PAIRS = [
        ("USD", "EUR"),
        ("USD", "GBP"),
        ("USD", "CAD"),
        ("USD", "JPY"),
        ("USD", "AUD"),
        ("USD", "CHF"),
        ("USD", "NGN"),
        ("USD", "ZAR"),
        ("GBP", "EUR"),
    ]

    # How long a cached rate is considered fresh before hitting the live API
    CACHE_TTL_HOURS = 4

    @staticmethod
    async def fetch_live_rate(
        from_currency: str,
        to_currency: str
    ) -> Optional[float]:
        """
        Fetch a live exchange rate from live FX providers (ExchangeRate-API,
        ECB Frankfurter, and Fixer.io if configured with a paid key).
        """
        from_currency = from_currency.upper().strip()
        to_currency = to_currency.upper().strip()
        if from_currency == to_currency:
            return 1.0

        timeout = aiohttp.ClientTimeout(total=10)
        try:
            async with aiohttp.ClientSession(timeout=timeout) as session:
                # 1. Primary Live Feed: Open ExchangeRate-API (160+ currencies including NGN, ZAR, EUR, GBP, JPY)
                er_url = f"https://open.er-api.com/v6/latest/{from_currency}"
                async with session.get(er_url) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        rates = data.get("rates", {})
                        if to_currency in rates and rates[to_currency] is not None:
                            return float(rates[to_currency])

                # 2. Secondary Live Feed: European Central Bank (Frankfurter API)
                fk_url = f"https://api.frankfurter.app/latest?from={from_currency}&to={to_currency}"
                async with session.get(fk_url) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        rates = data.get("rates", {})
                        if to_currency in rates and rates[to_currency] is not None:
                            return float(rates[to_currency])

                # 3. Optional Fixer.io feed
                from config import settings
                api_key = getattr(settings, "FIXER_IO_API_KEY", None)
                if api_key and not str(api_key).startswith("fx_live_"):
                    fx_url = (
                        f"https://data.fixer.io/api/latest"
                        f"?access_key={api_key}&base={from_currency}&symbols={to_currency}"
                    )
                    async with session.get(fx_url) as resp:
                        data = await resp.json()
                        if data.get("success") and to_currency in data.get("rates", {}):
                            return float(data["rates"][to_currency])
        except Exception as exc:
            log.warning("fetch_live_rate failed for %s/%s: %s", from_currency, to_currency, exc)
        return None

    @staticmethod
    async def get_exchange_rate(
        db: Session,
        from_currency: str,
        to_currency: str
    ) -> dict:
        """
        Get the current exchange rate between two currencies.

        Cache strategy (4-hour TTL):
        1. If a DB record exists and is **fresh** (≤ 4 h old)  → return it with
           ``source: "live_cached"``.
        2. If cache is **stale or absent**, call :meth:`fetch_live_rate`:
           - On success: upsert the DB record, return ``source: "live"``.
           - On failure with a stale record: return stale with
             ``source: "stale_cache"`` and a ``warning`` key.
           - On failure with no record at all: return a structured error dict.

        Fake / invented rates are **never** written to the database.

        Returns:
            A dict with at minimum ``{"success": bool}`` and, on success,
            ``{"rate": float, "source": str, "timestamp": str}``.
        """
        try:
            from models import ExchangeRate

            now = datetime.utcnow()
            fresh_cutoff = now - timedelta(hours=ExchangeRateService.CACHE_TTL_HOURS)

            # ------------------------------------------------------------------
            # 1. Look up any existing record (fresh or stale)
            # ------------------------------------------------------------------
            rate_record = db.query(ExchangeRate).filter(
                ExchangeRate.from_currency == from_currency,
                ExchangeRate.to_currency == to_currency,
            ).first()

            # Determine the timestamp field — the model uses either
            # ``last_updated`` or ``updated_at`` depending on migration history.
            def _record_timestamp(rec) -> Optional[datetime]:
                return getattr(rec, "last_updated", None) or getattr(rec, "updated_at", None)

            cache_is_fresh = False
            if rate_record:
                ts = _record_timestamp(rate_record)
                cache_is_fresh = ts is not None and ts >= fresh_cutoff

            # ------------------------------------------------------------------
            # 2. Return early if cache is still fresh
            # ------------------------------------------------------------------
            if cache_is_fresh:
                ts = _record_timestamp(rate_record)
                return {
                    "success": True,
                    "from_currency": from_currency,
                    "to_currency": to_currency,
                    "rate": rate_record.rate,
                    "timestamp": ts.isoformat(),
                    "source": "live_cached",
                }

            # ------------------------------------------------------------------
            # 3. Cache is stale or missing — try a live fetch
            # ------------------------------------------------------------------
            live_rate = await ExchangeRateService.fetch_live_rate(
                from_currency, to_currency
            )

            if live_rate is not None:
                # Upsert DB record with the real live rate
                if rate_record:
                    rate_record.rate = live_rate
                    rate_record.source = "live"
                    if hasattr(rate_record, "last_updated"):
                        rate_record.last_updated = now
                    if hasattr(rate_record, "updated_at"):
                        rate_record.updated_at = now
                else:
                    rate_record = ExchangeRate(
                        from_currency=from_currency,
                        to_currency=to_currency,
                        rate=live_rate,
                        source="live",
                        **(
                            {"last_updated": now}
                            if hasattr(ExchangeRate, "last_updated")
                            else {"updated_at": now}
                        ),
                    )
                    db.add(rate_record)

                db.commit()
                log.info(
                    "Live FX rate updated: %s/%s = %.6f",
                    from_currency, to_currency, live_rate,
                )
                return {
                    "success": True,
                    "from_currency": from_currency,
                    "to_currency": to_currency,
                    "rate": live_rate,
                    "timestamp": now.isoformat(),
                    "source": "live",
                }

            # ------------------------------------------------------------------
            # 4. Live fetch failed — fall back to stale cache if available
            # ------------------------------------------------------------------
            if rate_record:
                ts = _record_timestamp(rate_record)
                log.warning(
                    "Live rate unavailable for %s/%s; serving stale cache "
                    "(last updated: %s)",
                    from_currency, to_currency, ts,
                )
                return {
                    "success": True,
                    "from_currency": from_currency,
                    "to_currency": to_currency,
                    "rate": rate_record.rate,
                    "timestamp": ts.isoformat() if ts else None,
                    "source": "stale_cache",
                    "warning": (
                        "Live exchange rate unavailable. "
                        "Showing cached rate which may be outdated."
                    ),
                }

            # ------------------------------------------------------------------
            # 5. No rate at all — structured error
            # ------------------------------------------------------------------
            log.error(
                "Exchange rate completely unavailable for %s/%s",
                from_currency, to_currency,
            )
            return {
                "success": False,
                "error": (
                    "Exchange rate unavailable. "
                    "FIXER_IO_API_KEY not configured or provider unreachable."
                ),
                "rate": None,
            }

        except Exception as exc:
            log.error("Error getting exchange rate: %s", exc)
            return {"success": False, "error": str(exc)}

    @classmethod
    async def refresh_all_rates(
        cls,
        db: Session
    ) -> dict:
        """
        Fetch and persist live rates for all :attr:`COMMON_PAIRS`.

        Calls :meth:`fetch_live_rate` for each pair and upserts the result
        into the database.  Pairs where the live fetch fails are skipped
        without affecting the others.

        Args:
            db: Active SQLAlchemy session.

        Returns:
            ``{"USD/EUR": 0.91, ...}`` — only pairs that were successfully
            fetched and stored are included.
        """
        from models import ExchangeRate

        results: dict = {}
        now = datetime.utcnow()

        for from_currency, to_currency in cls.COMMON_PAIRS:
            pair_label = f"{from_currency}/{to_currency}"
            try:
                live_rate = await cls.fetch_live_rate(from_currency, to_currency)

                if live_rate is None:
                    log.warning("refresh_all_rates: no rate returned for %s", pair_label)
                    continue

                # Upsert
                record = db.query(ExchangeRate).filter(
                    ExchangeRate.from_currency == from_currency,
                    ExchangeRate.to_currency == to_currency,
                ).first()

                if record:
                    record.rate = live_rate
                    record.source = "live"
                    if hasattr(record, "last_updated"):
                        record.last_updated = now
                    if hasattr(record, "updated_at"):
                        record.updated_at = now
                else:
                    record = ExchangeRate(
                        from_currency=from_currency,
                        to_currency=to_currency,
                        rate=live_rate,
                        source="live",
                        **(
                            {"last_updated": now}
                            if hasattr(ExchangeRate, "last_updated")
                            else {"updated_at": now}
                        ),
                    )
                    db.add(record)

                db.commit()
                results[pair_label] = live_rate
                log.info("refresh_all_rates: %s = %.6f ✓", pair_label, live_rate)

            except Exception as exc:
                log.error("refresh_all_rates: failed for %s — %s", pair_label, exc)
                try:
                    db.rollback()
                except Exception:
                    pass

        log.info(
            "refresh_all_rates complete: %d/%d pairs refreshed",
            len(results), len(cls.COMMON_PAIRS),
        )
        return results

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
            
            log.info(f"Cross-currency transfer: {amount} {from_currency} -> {converted_amount} {to_currency} (fee: {fx_fee})")
            
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
                    
                    if rate_result and rate_result.get("success"):
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
