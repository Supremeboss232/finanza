"""Insurance API endpoints for policies and claims."""

from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession

from deps import get_current_user, SessionDep
from models import User
from crud import (
    create_policy,
    get_user_policies,
    get_policy,
    update_policy,
    delete_policy,
    create_claim,
    get_policy_claims,
    get_claim,
    update_claim,
)
from schemas import (
    Policy,
    PolicyCreate,
    Claim,
    ClaimCreate,
)

router = APIRouter(
    prefix="/api/v1/insurance",
    tags=["insurance"],
    dependencies=[Depends(get_current_user)]
)

# ===== POLICIES =====

@router.post("/policies", response_model=Policy)
async def create_policy_endpoint(
    policy: PolicyCreate,
    db_session: SessionDep,
    current_user: User = Depends(get_current_user),
):
    """Create a new insurance policy."""
    return await create_policy(db_session, policy, current_user.id)

@router.get("/policies", response_model=List[Policy])
async def list_policies(
    skip: int = 0,
    limit: int = 100,
    db_session: SessionDep = None,
    current_user: User = Depends(get_current_user),
):
    """Get all insurance policies for the current user."""
    return await get_user_policies(db_session, current_user.id, skip, limit)

@router.get("/policies/{policy_id}", response_model=Policy)
async def get_policy_detail(
    policy_id: int,
    db_session: SessionDep,
    current_user: User = Depends(get_current_user),
):
    """Get a specific insurance policy."""
    policy = await get_policy(db_session, policy_id)
    if not policy or policy.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Policy not found")
    return policy

@router.put("/policies/{policy_id}", response_model=Policy)
async def update_policy_endpoint(
    policy_id: int,
    policy_data: dict,
    db_session: SessionDep,
    current_user: User = Depends(get_current_user),
):
    """Update an insurance policy."""
    policy = await get_policy(db_session, policy_id)
    if not policy or policy.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Policy not found")
    return await update_policy(db_session, policy_id, policy_data)

@router.delete("/policies/{policy_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_policy_endpoint(
    policy_id: int,
    db_session: SessionDep,
    current_user: User = Depends(get_current_user),
):
    """Delete an insurance policy."""
    policy = await get_policy(db_session, policy_id)
    if not policy or policy.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Policy not found")
    await delete_policy(db_session, policy_id)

# ===== CLAIMS =====

@router.post("/policies/{policy_id}/claims", response_model=Claim)
async def create_claim_endpoint(
    policy_id: int,
    claim: ClaimCreate,
    db_session: SessionDep,
    current_user: User = Depends(get_current_user),
):
    """Submit a claim for a policy."""
    policy = await get_policy(db_session, policy_id)
    if not policy or policy.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Policy not found")
    return await create_claim(db_session, claim, policy_id)

@router.get("/policies/{policy_id}/claims", response_model=List[Claim])
async def list_policy_claims(
    policy_id: int,
    db_session: SessionDep,
    current_user: User = Depends(get_current_user),
):
    """Get all claims for a specific policy."""
    policy = await get_policy(db_session, policy_id)
    if not policy or policy.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Policy not found")
    return await get_policy_claims(db_session, policy_id)

@router.get("/claims/{claim_id}", response_model=Claim)
async def get_claim_detail(
    claim_id: int,
    db_session: SessionDep,
    current_user: User = Depends(get_current_user),
):
    """Get a specific claim."""
    claim = await get_claim(db_session, claim_id)
    if not claim:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Claim not found")
    # Verify user owns the policy
    policy = await get_policy(db_session, claim.policy_id)
    if not policy or policy.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Claim not found")
    return claim

@router.put("/claims/{claim_id}", response_model=Claim)
async def update_claim_endpoint(
    claim_id: int,
    claim_data: dict,
    db_session: SessionDep,
    current_user: User = Depends(get_current_user),
):
    """Update a claim."""
    claim = await get_claim(db_session, claim_id)
    if not claim:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Claim not found")
    # Verify user owns the policy
    policy = await get_policy(db_session, claim.policy_id)
    if not policy or policy.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Claim not found")
    return await update_claim(db_session, claim_id, claim_data)
