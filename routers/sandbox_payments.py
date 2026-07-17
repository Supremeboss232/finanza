from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from deps import SessionDep
from services.sandbox_payment_rail import SandboxPaymentRailService

router = APIRouter(prefix="/sandbox/payments", tags=["sandbox-payments"])


class SandboxDepositRequest(BaseModel):
    user_id: int
    amount: float
    description: Optional[str] = "Sandbox deposit"
    reference_number: Optional[str] = None


@router.post("/deposit")
async def create_sandbox_deposit(request: SandboxDepositRequest, db: SessionDep):
    """Create a deterministic sandbox deposit for local testing."""
    result = await SandboxPaymentRailService.create_sandbox_deposit(
        db=db,
        user_id=request.user_id,
        amount=request.amount,
        description=request.description,
        reference_number=request.reference_number,
    )
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result.get("error", "Sandbox deposit failed"))
    return result


@router.post("/settle/{transaction_id}")
async def simulate_sandbox_settlement(transaction_id: int, db: SessionDep):
    """Mark a sandbox transaction as completed for QA flows."""
    result = await SandboxPaymentRailService.simulate_settlement(db, transaction_id)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result.get("error", "Settlement update failed"))
    return result
