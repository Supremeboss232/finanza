"""
Geographic Expansion API Routes - Phase 3B
REST endpoints for multi-region support and compliance management
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional, List
from pydantic import BaseModel
from deps import get_db
from geo_expansion_service import RegionService, ComplianceService, RegionRoutingService
import logging

log = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["geographic-expansion"])


# ==================== PYDANTIC MODELS ====================

class RegionCreate(BaseModel):
    """Schema for creating a region"""
    region_code: str
    region_name: str
    country: str
    timezone: str = "UTC"
    currency: str = "USD"
    regulatory_framework: str = "FDIC"
    compliance_level: str = "standard"


class RegionUpdate(BaseModel):
    """Schema for updating a region"""
    region_name: Optional[str] = None
    timezone: Optional[str] = None
    compliance_level: Optional[str] = None
    is_active: Optional[bool] = None


class ComplianceCheckRequest(BaseModel):
    """Schema for checking account compliance"""
    account_id: int
    region_code: str


class DataResidencyRequest(BaseModel):
    """Schema for enforcing data residency"""
    account_id: int
    region_code: str


class TransactionRoutingRequest(BaseModel):
    """Schema for routing a transaction"""
    account_id: int
    transaction_type: str
    amount: float


# ==================== REGIONS ENDPOINTS ====================

@router.post("/regions", summary="Create a new geographic region")
async def create_region(
    region_data: RegionCreate,
    db: Session = Depends(get_db),
    current_user_id: Optional[int] = None
):
    """
    Create a new geographic region for the platform.
    
    Supported regions: US (USA), CA (Canada), UK (United Kingdom), EU (European Union), AU (Australia)
    
    Regulatory frameworks: FDIC, OCC, FINRA, FCA, ASIC, etc.
    
    Compliance levels: basic, standard, enhanced
    """
    try:
        result = await RegionService.create_region(
            db=db,
            region_code=region_data.region_code,
            region_name=region_data.region_name,
            country=region_data.country,
            timezone=region_data.timezone,
            currency=region_data.currency,
            regulatory_framework=region_data.regulatory_framework,
            compliance_level=region_data.compliance_level,
            created_by=current_user_id
        )
        
        if not result["success"]:
            raise HTTPException(status_code=400, detail=result["error"])
        
        log.info(f"Region created: {region_data.region_code} by user {current_user_id}")
        return result
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error creating region: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/regions", summary="List all geographic regions")
async def list_regions(
    active_only: bool = Query(True, description="Filter only active regions"),
    db: Session = Depends(get_db)
):
    """
    List all geographic regions configured in the platform.
    
    Query Parameters:
    - active_only: If true, return only active regions (default: true)
    """
    try:
        result = await RegionService.list_regions(db=db, active_only=active_only)
        
        if not result["success"]:
            raise HTTPException(status_code=404, detail=result["error"])
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error listing regions: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/regions/{region_code}", summary="Get region details")
async def get_region(
    region_code: str,
    db: Session = Depends(get_db)
):
    """
    Get detailed information about a specific geographic region.
    
    Path Parameters:
    - region_code: The region code (e.g., US, CA, UK, EU, AU)
    """
    try:
        result = await RegionService.get_region(db=db, region_code=region_code)
        
        if not result["success"]:
            raise HTTPException(status_code=404, detail=result["error"])
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error retrieving region: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.put("/regions/{region_code}", summary="Update region configuration")
async def update_region(
    region_code: str,
    region_data: RegionUpdate,
    db: Session = Depends(get_db),
    current_user_id: Optional[int] = None
):
    """
    Update configuration for an existing geographic region.
    
    Only specified fields will be updated.
    """
    try:
        result = await RegionService.update_region(
            db=db,
            region_code=region_code,
            region_name=region_data.region_name,
            timezone=region_data.timezone,
            compliance_level=region_data.compliance_level,
            is_active=region_data.is_active
        )
        
        if not result["success"]:
            raise HTTPException(status_code=400, detail=result["error"])
        
        log.info(f"Region updated: {region_code} by user {current_user_id}")
        return result
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error updating region: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


# ==================== COMPLIANCE ENDPOINTS ====================

@router.get("/compliance/{region_code}", summary="Get compliance requirements")
async def get_compliance_requirements(
    region_code: str,
    db: Session = Depends(get_db)
):
    """
    Get compliance requirements for a specific region.
    
    Returns KYC levels, AML thresholds, CTF requirements, data residency rules, etc.
    """
    try:
        result = await ComplianceService.get_compliance_requirements(
            db=db,
            region_code=region_code
        )
        
        if not result["success"]:
            raise HTTPException(status_code=404, detail=result["error"])
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error getting compliance requirements: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/compliance/check", summary="Check account compliance")
async def check_account_compliance(
    request: ComplianceCheckRequest,
    db: Session = Depends(get_db)
):
    """
    Check if an account meets the compliance requirements for a specific region.
    
    Validates KYC status, AML compliance, and other regional requirements.
    """
    try:
        result = await ComplianceService.check_account_compliance(
            db=db,
            account_id=request.account_id,
            region_code=request.region_code
        )
        
        if not result["success"]:
            raise HTTPException(status_code=400, detail=result["error"])
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error checking compliance: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/compliance/enforce-residency", summary="Enforce data residency")
async def enforce_data_residency(
    request: DataResidencyRequest,
    db: Session = Depends(get_db),
    current_user_id: Optional[int] = None
):
    """
    Enforce data residency requirement for an account.
    
    Marks an account as required to store data in a specific geographic region.
    """
    try:
        result = await ComplianceService.enforce_data_residency(
            db=db,
            account_id=request.account_id,
            region_code=request.region_code
        )
        
        if not result["success"]:
            raise HTTPException(status_code=400, detail=result["error"])
        
        log.info(f"Data residency enforced for account {request.account_id} by user {current_user_id}")
        return result
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error enforcing residency: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


# ==================== ROUTING ENDPOINTS ====================

@router.get("/routing/account/{account_id}/region", summary="Get account region")
async def get_account_region(
    account_id: int,
    db: Session = Depends(get_db)
):
    """
    Determine which geographic region an account belongs to.
    
    Returns region code, name, country, currency, etc.
    """
    try:
        result = await RegionRoutingService.get_account_region(
            db=db,
            account_id=account_id
        )
        
        if not result["success"]:
            raise HTTPException(status_code=404, detail=result["error"])
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error getting account region: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/routing/route-transaction", summary="Route transaction to processor")
async def route_transaction(
    request: TransactionRoutingRequest,
    db: Session = Depends(get_db)
):
    """
    Route a transaction to the appropriate regional processor.
    
    Determines the correct payment processor based on account region and transaction type.
    
    Supported transaction types:
    - ach_transfer: US domestic ACH
    - wire_transfer: International wire
    - bill_payment: Bill payment
    - mobile_deposit: Mobile check deposit
    - eft_transfer: Canadian EFT
    - faster_payment: UK Faster Payments
    - sepa_transfer: EU SEPA transfer
    - bpay: Australian BPAY
    """
    try:
        result = await RegionRoutingService.route_transaction(
            db=db,
            account_id=request.account_id,
            transaction_type=request.transaction_type,
            amount=request.amount
        )
        
        if not result["success"]:
            raise HTTPException(status_code=400, detail=result["error"])
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error routing transaction: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/routing/availability/{region_code}/{service_name}", summary="Check service availability")
async def check_region_availability(
    region_code: str,
    service_name: str,
    db: Session = Depends(get_db)
):
    """
    Check if a specific service is available in a region.
    
    Path Parameters:
    - region_code: Geographic region code (US, CA, UK, EU, AU)
    - service_name: Service name (scheduled_transfers, bill_pay, mobile_deposit, wire_transfer, etc.)
    
    Returns availability status, launch date, and processor information.
    """
    try:
        result = await RegionRoutingService.check_region_availability(
            db=db,
            region_code=region_code,
            service_name=service_name
        )
        
        if not result["success"]:
            raise HTTPException(status_code=404, detail=result["error"])
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error checking availability: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
