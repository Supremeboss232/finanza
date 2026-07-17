from fastapi import APIRouter
from pydantic import BaseModel

from services.loan_origination_service import LoanOriginationService

router = APIRouter(prefix="/loan-origination", tags=["loan-origination"])


class LoanQuoteRequest(BaseModel):
    principal: float
    annual_rate: float
    term_months: int


@router.post("/quote")
async def quote_loan(request: LoanQuoteRequest):
    """Generate a deterministic loan quote and amortization schedule."""
    return LoanOriginationService.generate_schedule(
        request.principal,
        request.annual_rate,
        request.term_months,
    )
