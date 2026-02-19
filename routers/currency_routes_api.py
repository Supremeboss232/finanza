"""
Currency Exchange API Routes - Phase 3B
REST endpoints for multi-currency accounts and cross-currency transfers
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional
from pydantic import BaseModel
from deps import get_db
from currency_exchange_service import (
    CurrencyService, ExchangeRateService, CurrencyConversionService
)
import logging

log = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["currency-exchange"])


# ==================== PYDANTIC MODELS ====================

class EnableMultiCurrencyRequest(BaseModel):
    """Schema for enabling multi-currency on an account"""
    account_id: int
    base_currency: str = "USD"
    secondary_currencies: Optional[str] = None


class AddCurrencyRequest(BaseModel):
    """Schema for adding a currency to an account"""
    account_id: int
    currency: str
    initial_balance: float = 0.0


class CurrencyConversionRequest(BaseModel):
    """Schema for currency conversion"""
    amount: float
    from_currency: str
    to_currency: str
    fee_type: str = "standard"


class CrossCurrencyTransferRequest(BaseModel):
    """Schema for cross-currency transfer"""
    from_account_id: int
    to_account_id: int
    from_currency: str
    to_currency: str
    amount: float
    fee_type: str = "standard"


# ==================== MULTI-CURRENCY ENDPOINTS ====================

@router.post("/currencies/enable", summary="Enable multi-currency on account")
async def enable_multi_currency(
    request: EnableMultiCurrencyRequest,
    db: Session = Depends(get_db),
    current_user_id: Optional[int] = None
):
    """
    Enable multi-currency support on an account.
    
    This allows the account to hold and manage balances in multiple currencies.
    
    Request body:
    - account_id: Target account ID
    - base_currency: Primary currency (default: USD)
    - secondary_currencies: Comma-separated list of additional currencies (e.g., "CAD,GBP,EUR")
    """
    try:
        result = await CurrencyService.create_multi_currency_account(
            db=db,
            account_id=request.account_id,
            base_currency=request.base_currency,
            secondary_currencies=request.secondary_currencies,
            created_by=current_user_id
        )
        
        if not result["success"]:
            raise HTTPException(status_code=400, detail=result["error"])
        
        log.info(f"Multi-currency enabled for account {request.account_id} by user {current_user_id}")
        return result
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error enabling multi-currency: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/currencies/{account_id}/balances", summary="Get currency balances")
async def get_currency_balances(
    account_id: int,
    db: Session = Depends(get_db)
):
    """
    Get balance in all enabled currencies for an account.
    
    Returns:
    - Base currency
    - Total balance in base currency
    - Individual balances for each enabled currency
    - Last transaction date for each currency
    
    Path Parameters:
    - account_id: Account ID to check balances for
    """
    try:
        result = await CurrencyService.get_currency_balances(
            db=db,
            account_id=account_id
        )
        
        if not result["success"]:
            raise HTTPException(status_code=404, detail=result["error"])
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error getting currency balances: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/currencies/{account_id}/add", summary="Add currency to account")
async def add_currency_to_account(
    account_id: int,
    request: AddCurrencyRequest,
    db: Session = Depends(get_db),
    current_user_id: Optional[int] = None
):
    """
    Add a new currency to a multi-currency account.
    
    The account must have multi-currency enabled first.
    
    Path Parameters:
    - account_id: Account ID to add currency to
    
    Request body:
    - currency: ISO 4217 currency code (USD, CAD, GBP, EUR, AUD, JPY, etc.)
    - initial_balance: Starting balance in this currency (default: 0.0)
    """
    try:
        result = await CurrencyService.add_currency_to_account(
            db=db,
            account_id=account_id,
            currency=request.currency,
            initial_balance=request.initial_balance
        )
        
        if not result["success"]:
            raise HTTPException(status_code=400, detail=result["error"])
        
        log.info(f"Currency {request.currency} added to account {account_id} by user {current_user_id}")
        return result
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error adding currency: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


# ==================== EXCHANGE RATE ENDPOINTS ====================

@router.get("/fx/rates/{from_currency}/{to_currency}", summary="Get exchange rate")
async def get_exchange_rate(
    from_currency: str,
    to_currency: str,
    db: Session = Depends(get_db)
):
    """
    Get current exchange rate between two currencies.
    
    Rates are cached with a 1-hour TTL for performance.
    
    Path Parameters:
    - from_currency: Source currency code (e.g., USD)
    - to_currency: Target currency code (e.g., CAD)
    
    Returns:
    - Exchange rate (1 unit of from_currency = X units of to_currency)
    - Whether the rate is from cache
    - Timestamp of the rate
    """
    try:
        result = await ExchangeRateService.get_exchange_rate(
            db=db,
            from_currency=from_currency,
            to_currency=to_currency
        )
        
        if not result["success"]:
            raise HTTPException(status_code=400, detail=result["error"])
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error getting exchange rate: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/fx/history/{from_currency}/{to_currency}", summary="Get exchange rate history")
async def get_rate_history(
    from_currency: str,
    to_currency: str,
    days: int = Query(30, ge=1, le=365, description="Number of days of history (1-365)"),
    db: Session = Depends(get_db)
):
    """
    Get historical exchange rate data for analysis.
    
    Path Parameters:
    - from_currency: Source currency code
    - to_currency: Target currency code
    
    Query Parameters:
    - days: Number of days of history to retrieve (1-365, default: 30)
    
    Returns:
    - Historical rates with high/low for period
    - Timestamps for each rate
    - Analysis-ready data
    """
    try:
        result = await ExchangeRateService.get_rate_history(
            db=db,
            from_currency=from_currency,
            to_currency=to_currency,
            days=days
        )
        
        if not result["success"]:
            raise HTTPException(status_code=404, detail=result["error"])
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error getting rate history: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/fx/all-rates/{base_currency}", summary="Get all major currency rates")
async def get_all_fx_rates(
    base_currency: str,
    db: Session = Depends(get_db)
):
    """
    Get exchange rates for all major currencies from a base currency.
    
    Major currencies: USD, CAD, GBP, EUR, AUD, JPY
    
    Path Parameters:
    - base_currency: Base currency for rate conversion (e.g., USD)
    
    Returns:
    - Rates for all major currencies relative to base
    - Current timestamp
    """
    try:
        result = await CurrencyConversionService.get_fx_rates(
            db=db,
            base_currency=base_currency
        )
        
        if not result["success"]:
            raise HTTPException(status_code=400, detail=result["error"])
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error getting FX rates: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


# ==================== CONVERSION & TRANSFER ENDPOINTS ====================

@router.post("/fx/convert", summary="Convert currency amount")
async def convert_currency(
    request: CurrencyConversionRequest,
    db: Session = Depends(get_db)
):
    """
    Convert an amount from one currency to another.
    
    Includes FX fees based on tier (standard: 1%, premium: 0.5%, vip: 0.25%)
    
    Request body:
    - amount: Amount to convert
    - from_currency: Source currency code
    - to_currency: Target currency code
    - fee_type: Fee tier - "standard" (1%), "premium" (0.5%), "vip" (0.25%)
    
    Returns:
    - Original amount and currency
    - Converted amount and final amount after fees
    - Exchange rate used
    - FX fee charged
    """
    try:
        result = await CurrencyConversionService.convert_currency(
            db=db,
            amount=request.amount,
            from_currency=request.from_currency,
            to_currency=request.to_currency,
            fee_type=request.fee_type
        )
        
        if not result["success"]:
            raise HTTPException(status_code=400, detail=result["error"])
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error converting currency: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/fx/transfer", summary="Execute cross-currency transfer")
async def cross_currency_transfer(
    request: CrossCurrencyTransferRequest,
    db: Session = Depends(get_db),
    current_user_id: Optional[int] = None
):
    """
    Execute a cross-currency transfer between two accounts.
    
    Both accounts must have multi-currency enabled for their respective currencies.
    
    Request body:
    - from_account_id: Source account ID
    - to_account_id: Destination account ID
    - from_currency: Source currency code
    - to_currency: Target currency code
    - amount: Amount to transfer in source currency
    - fee_type: Fee tier - "standard" (1%), "premium" (0.5%), "vip" (0.25%)
    
    Returns:
    - Transfer ID
    - From and to amounts
    - Exchange rate applied
    - FX fee charged
    - Final amount received
    - Reference number for tracking
    - Transfer status
    """
    try:
        result = await CurrencyConversionService.cross_currency_transfer(
            db=db,
            from_account_id=request.from_account_id,
            to_account_id=request.to_account_id,
            from_currency=request.from_currency,
            to_currency=request.to_currency,
            amount=request.amount,
            fee_type=request.fee_type,
            created_by=current_user_id
        )
        
        if not result["success"]:
            raise HTTPException(status_code=400, detail=result["error"])
        
        log.info(
            f"Cross-currency transfer: {request.amount} {request.from_currency} -> "
            f"{result['data']['final_to_amount']} {request.to_currency} by user {current_user_id}"
        )
        return result
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error in cross-currency transfer: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
