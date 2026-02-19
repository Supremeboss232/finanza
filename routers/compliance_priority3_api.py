"""
Compliance & Risk Management API Router - Priority 3
Endpoints for sanctions screening, transaction flagging, country risk assessment, and compliance reporting
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query, Path
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timedelta
import logging
from pydantic import BaseModel, Field

from deps import get_db, get_current_user
from models import User
from models_priority_3 import (
    FlaggedTransaction, SanctionsScreening, CountryRiskAssessment
)
from services_priority_3 import ComplianceService

log = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/compliance", tags=["compliance"])

# ============================================================================
# PYDANTIC SCHEMAS
# ============================================================================

class SanctionsScreeningRequest(BaseModel):
    """Request schema for sanctions screening"""
    full_name: str = Field(..., min_length=1, max_length=255)
    country: Optional[str] = Field(None, max_length=100)
    date_of_birth: Optional[str] = Field(None, description="ISO format date string")

    class Config:
        json_schema_extra = {
            "example": {
                "full_name": "John Doe",
                "country": "United States",
                "date_of_birth": "1980-01-15"
            }
        }


class SanctionsScreeningResponse(BaseModel):
    """Response schema for sanctions screening result"""
    id: int
    screening_type: str  # OFAC, UN, EU, UK
    name: str
    match_score: float  # 0-100
    risk_level: str  # low, medium, high
    status: str  # clean, potential_match, confirmed_match
    details: Optional[dict]
    created_at: datetime

    class Config:
        from_attributes = True


class FlagTransactionRequest(BaseModel):
    """Request schema for flagging a transaction"""
    transaction_id: int
    reason: str = Field(..., min_length=10, max_length=1000)
    risk_level: str = Field(..., description="low, medium, or high")
    rule_triggered: Optional[str] = Field(None, max_length=500)

    class Config:
        json_schema_extra = {
            "example": {
                "transaction_id": 123,
                "reason": "Transaction amount exceeds daily threshold and sender has multiple recent transfers",
                "risk_level": "medium",
                "rule_triggered": "THRESHOLD_EXCEED"
            }
        }


class FlagTransactionResponse(BaseModel):
    """Response schema for flagged transaction"""
    id: int
    transaction_id: int
    user_id: int
    reason: str
    risk_level: str  # low, medium, high
    status: str  # open, under_investigation, resolved, false_positive
    rule_triggered: Optional[str]
    investigation_notes: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class UpdateFlagRequest(BaseModel):
    """Request schema for updating flagged transaction"""
    status: Optional[str] = Field(None, description="open, under_investigation, resolved, false_positive")
    investigation_notes: Optional[str] = Field(None, max_length=2000)
    risk_level: Optional[str] = Field(None, description="low, medium, or high")

    class Config:
        json_schema_extra = {
            "example": {
                "status": "resolved",
                "investigation_notes": "Verified with compliance team - legitimate business transfer",
                "risk_level": "low"
            }
        }


class CountryRiskResponse(BaseModel):
    """Response schema for country risk assessment"""
    id: int
    country_code: str
    country_name: str
    risk_level: str  # low, medium, high, very_high
    aml_rating: float  # 0-10 (higher = riskier)
    sanctions_active: bool
    terrorist_financing_risk: bool
    last_updated: datetime

    class Config:
        from_attributes = True


class ComplianceReportRequest(BaseModel):
    """Request schema for compliance report"""
    start_date: str = Field(..., description="ISO format date string")
    end_date: str = Field(..., description="ISO format date string")
    report_type: str = Field(default="summary", description="summary or detailed")

    class Config:
        json_schema_extra = {
            "example": {
                "start_date": "2026-01-01",
                "end_date": "2026-01-31",
                "report_type": "summary"
            }
        }


class ComplianceReportResponse(BaseModel):
    """Response schema for compliance report"""
    report_period: str
    total_transactions: int
    total_flagged: int
    flagged_by_risk_level: dict  # {low: 5, medium: 3, high: 1}
    investigations_open: int
    investigations_resolved: int
    sanctions_screenings_total: int
    sanctions_matches: int
    top_risk_countries: List[str]
    recommendations: List[str]
    generated_at: datetime

    class Config:
        from_attributes = True


class AdminComplianceStats(BaseModel):
    """Response schema for admin compliance dashboard statistics"""
    total_flagged_transactions: int
    open_investigations: int
    resolved_investigations: int
    high_risk_count: int
    medium_risk_count: int
    low_risk_count: int
    sanctions_matches_total: int
    sanctions_matches_this_month: int
    average_investigation_time_hours: float
    pending_reviews: int
    last_30_days_flag_trend: List[dict]  # {date: count}

    class Config:
        from_attributes = True


class RiskDistribution(BaseModel):
    """Response schema for risk level distribution"""
    high_risk: int
    medium_risk: int
    low_risk: int
    clean: int
    total: int
    percentages: dict  # {high: 5.2, medium: 12.1, low: 82.7}


# ============================================================================
# ENDPOINTS - SANCTIONS SCREENING
# ============================================================================

@router.post(
    "/screen-sanctions",
    response_model=List[SanctionsScreeningResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Screen Against Sanctions Lists",
    description="Screen a person against OFAC, UN, EU, and UK sanctions lists"
)
async def screen_sanctions(
    request: SanctionsScreeningRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> List[SanctionsScreeningResponse]:
    """
    Screen a person against multiple sanctions lists.
    
    **Sanctions Lists Checked:**
    - OFAC (Office of Foreign Assets Control)
    - UN (United Nations)
    - EU (European Union)
    - UK (United Kingdom)
    
    **Authorization:**
    - Authenticated users only
    
    **Returns:**
    - 201 Created with screening results
    - 400 Bad Request if data is invalid
    - 401 Unauthorized if not authenticated
    """
    try:
        # Perform sanctions screening
        results = ComplianceService.screen_against_sanctions(
            db=db,
            full_name=request.full_name,
            country=request.country,
            date_of_birth=request.date_of_birth,
            screening_user_id=current_user.id
        )
        
        log.info(f"Sanctions screening performed by user {current_user.id} for {request.full_name}")
        
        return [SanctionsScreeningResponse.from_orm(r) for r in results]
    
    except Exception as e:
        log.error(f"Error screening sanctions: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to perform sanctions screening"
        )


@router.get(
    "/sanctions/{screening_id}",
    response_model=SanctionsScreeningResponse,
    summary="Get Sanctions Screening Result",
    description="Get details of a specific sanctions screening result"
)
async def get_sanctions_screening(
    screening_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SanctionsScreeningResponse:
    """
    Get details of a sanctions screening result.
    
    **Returns:**
    - 200 OK with screening details
    - 401 Unauthorized if not authenticated
    - 404 Not Found if screening doesn't exist
    """
    try:
        screening = db.query(SanctionsScreening).filter(
            SanctionsScreening.id == screening_id
        ).first()
        
        if not screening:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Sanctions screening not found"
            )
        
        return SanctionsScreeningResponse.from_orm(screening)
    
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error getting sanctions screening {screening_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get screening result"
        )


# ============================================================================
# ENDPOINTS - TRANSACTION FLAGGING
# ============================================================================

@router.post(
    "/flag-transaction",
    response_model=FlagTransactionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Flag Transaction for Investigation",
    description="Flag a transaction for compliance review and investigation"
)
async def flag_transaction(
    request: FlagTransactionRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> FlagTransactionResponse:
    """
    Flag a transaction for compliance review.
    
    **Authorization:**
    - Authenticated users and compliance officers
    
    **Risk Levels:**
    - low: Standard review
    - medium: Priority review
    - high: Urgent review with potential account suspension
    
    **Returns:**
    - 201 Created with flag details
    - 400 Bad Request if validation fails
    - 401 Unauthorized if not authenticated
    """
    try:
        # Create flag
        flag = ComplianceService.flag_transaction(
            db=db,
            transaction_id=request.transaction_id,
            user_id=current_user.id,
            reason=request.reason,
            risk_level=request.risk_level,
            rule_triggered=request.rule_triggered
        )
        
        log.info(f"Transaction {request.transaction_id} flagged by user {current_user.id}")
        
        return FlagTransactionResponse.from_orm(flag)
    
    except Exception as e:
        db.rollback()
        log.error(f"Error flagging transaction: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to flag transaction"
        )


@router.get(
    "/flagged-transactions",
    response_model=List[FlagTransactionResponse],
    summary="List Flagged Transactions",
    description="Get list of flagged transactions (admin only)"
)
async def list_flagged_transactions(
    status_filter: Optional[str] = Query(None, description="Filter by status"),
    risk_level_filter: Optional[str] = Query(None, description="Filter by risk level"),
    limit: int = Query(50, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> List[FlagTransactionResponse]:
    """
    Get list of flagged transactions.
    
    **Authorization:**
    - Admin/Compliance staff only
    
    **Query Parameters:**
    - `status_filter`: Filter by status (open, under_investigation, resolved, false_positive)
    - `risk_level_filter`: Filter by risk level (low, medium, high)
    - `limit`: Results per page (default: 50, max: 1000)
    - `offset`: Pagination offset
    
    **Returns:**
    - 200 OK with list of flagged transactions
    - 401 Unauthorized if not authenticated
    - 403 Forbidden if not an admin
    """
    try:
        # Admin check
        if not current_user.is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only administrators can access this endpoint"
            )
        
        query = db.query(FlaggedTransaction)
        
        if status_filter:
            query = query.filter(FlaggedTransaction.status == status_filter)
        
        if risk_level_filter:
            query = query.filter(FlaggedTransaction.risk_level == risk_level_filter)
        
        flags = query.order_by(
            FlaggedTransaction.created_at.desc()
        ).offset(offset).limit(limit).all()
        
        return [FlagTransactionResponse.from_orm(f) for f in flags]
    
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error listing flagged transactions: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list flagged transactions"
        )


@router.get(
    "/flagged-transactions/{flag_id}",
    response_model=FlagTransactionResponse,
    summary="Get Flagged Transaction Details",
    description="Get details of a specific flagged transaction"
)
async def get_flagged_transaction(
    flag_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> FlagTransactionResponse:
    """
    Get details of a flagged transaction.
    
    **Authorization:**
    - Admin/Compliance staff only
    
    **Returns:**
    - 200 OK with flag details
    - 401 Unauthorized if not authenticated
    - 403 Forbidden if not an admin
    - 404 Not Found if flag doesn't exist
    """
    try:
        if not current_user.is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only administrators can access this endpoint"
            )
        
        flag = db.query(FlaggedTransaction).filter(
            FlaggedTransaction.id == flag_id
        ).first()
        
        if not flag:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Flagged transaction not found"
            )
        
        return FlagTransactionResponse.from_orm(flag)
    
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error getting flagged transaction {flag_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get flagged transaction"
        )


@router.put(
    "/flagged-transactions/{flag_id}",
    response_model=FlagTransactionResponse,
    summary="Update Flagged Transaction",
    description="Update investigation status and notes on a flagged transaction"
)
async def update_flagged_transaction(
    flag_id: int,
    request: UpdateFlagRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> FlagTransactionResponse:
    """
    Update a flagged transaction's investigation status.
    
    **Authorization:**
    - Admin/Compliance staff only
    
    **Status Transitions:**
    - open → under_investigation → resolved
    - open/under_investigation → false_positive
    
    **Returns:**
    - 200 OK with updated flag
    - 400 Bad Request if validation fails
    - 401 Unauthorized if not authenticated
    - 403 Forbidden if not an admin
    - 404 Not Found if flag doesn't exist
    """
    try:
        if not current_user.is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only administrators can access this endpoint"
            )
        
        flag = db.query(FlaggedTransaction).filter(
            FlaggedTransaction.id == flag_id
        ).first()
        
        if not flag:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Flagged transaction not found"
            )
        
        # Update fields
        if request.status is not None:
            flag.status = request.status
        if request.investigation_notes is not None:
            flag.investigation_notes = request.investigation_notes
        if request.risk_level is not None:
            flag.risk_level = request.risk_level
        
        flag.updated_at = datetime.utcnow()
        
        db.commit()
        
        log.info(f"Flagged transaction {flag_id} updated by admin {current_user.id}")
        
        return FlagTransactionResponse.from_orm(flag)
    
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        log.error(f"Error updating flagged transaction {flag_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update flagged transaction"
        )


# ============================================================================
# ENDPOINTS - COUNTRY RISK ASSESSMENT
# ============================================================================

@router.get(
    "/country-risk/{country_code}",
    response_model=CountryRiskResponse,
    summary="Get Country Risk Assessment",
    description="Get risk assessment for a specific country"
)
async def get_country_risk(
    country_code: str = Path(..., min_length=2, max_length=2, description="ISO 3166-1 alpha-2 country code"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CountryRiskResponse:
    """
    Get risk assessment for a country.
    
    **Authorization:**
    - Authenticated users only
    
    **Country Code Format:**
    - ISO 3166-1 alpha-2 (e.g., US, GB, CN)
    
    **Returns:**
    - 200 OK with country risk details
    - 401 Unauthorized if not authenticated
    - 404 Not Found if country not found
    """
    try:
        risk_assessment = db.query(CountryRiskAssessment).filter(
            CountryRiskAssessment.country_code == country_code.upper()
        ).first()
        
        if not risk_assessment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Risk assessment not found for country {country_code}"
            )
        
        return CountryRiskResponse.from_orm(risk_assessment)
    
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error getting country risk for {country_code}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get country risk assessment"
        )


@router.get(
    "/country-risk/list",
    response_model=List[CountryRiskResponse],
    summary="List Country Risk Assessments",
    description="Get list of country risk assessments with optional filtering"
)
async def list_country_risks(
    risk_level_filter: Optional[str] = Query(None, description="Filter by risk level"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> List[CountryRiskResponse]:
    """
    Get list of country risk assessments.
    
    **Query Parameters:**
    - `risk_level_filter`: Filter by risk level (low, medium, high, very_high)
    - `limit`: Results per page (default: 100, max: 1000)
    - `offset`: Pagination offset
    
    **Returns:**
    - 200 OK with list of countries
    - 401 Unauthorized if not authenticated
    """
    try:
        query = db.query(CountryRiskAssessment)
        
        if risk_level_filter:
            query = query.filter(CountryRiskAssessment.risk_level == risk_level_filter)
        
        countries = query.order_by(
            CountryRiskAssessment.country_name
        ).offset(offset).limit(limit).all()
        
        return [CountryRiskResponse.from_orm(c) for c in countries]
    
    except Exception as e:
        log.error(f"Error listing country risks: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list country risk assessments"
        )


# ============================================================================
# ENDPOINTS - COMPLIANCE REPORTING
# ============================================================================

@router.post(
    "/report",
    response_model=ComplianceReportResponse,
    summary="Generate Compliance Report",
    description="Generate compliance report for a date range"
)
async def generate_compliance_report(
    request: ComplianceReportRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ComplianceReportResponse:
    """
    Generate a compliance report for a date range.
    
    **Authorization:**
    - Admin/Compliance staff only
    
    **Report Types:**
    - summary: High-level overview
    - detailed: Complete transaction details
    
    **Returns:**
    - 200 OK with compliance report
    - 400 Bad Request if dates are invalid
    - 401 Unauthorized if not authenticated
    - 403 Forbidden if not an admin
    """
    try:
        if not current_user.is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only administrators can access this endpoint"
            )
        
        report = ComplianceService.generate_compliance_report(
            db=db,
            start_date=request.start_date,
            end_date=request.end_date,
            report_type=request.report_type
        )
        
        log.info(f"Compliance report generated by admin {current_user.id}")
        
        return report
    
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error generating compliance report: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate compliance report"
        )


@router.get(
    "/admin/statistics",
    response_model=AdminComplianceStats,
    summary="Get Compliance Dashboard Statistics",
    description="Get admin dashboard statistics for compliance monitoring"
)
async def get_compliance_statistics(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AdminComplianceStats:
    """
    Get compliance dashboard statistics.
    
    **Authorization:**
    - Admin/Compliance staff only
    
    **Metrics Included:**
    - Total flagged transactions
    - Open vs resolved investigations
    - Risk level distribution
    - Sanctions matches
    - Average investigation time
    - 30-day trend data
    
    **Returns:**
    - 200 OK with dashboard statistics
    - 401 Unauthorized if not authenticated
    - 403 Forbidden if not an admin
    """
    try:
        if not current_user.is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only administrators can access this endpoint"
            )
        
        stats = ComplianceService.get_admin_statistics(db)
        
        return stats
    
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error getting compliance statistics: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get statistics"
        )


@router.get(
    "/risk-distribution",
    response_model=RiskDistribution,
    summary="Get Risk Level Distribution",
    description="Get distribution of risk levels across all flagged transactions"
)
async def get_risk_distribution(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> RiskDistribution:
    """
    Get distribution of risk levels.
    
    **Authorization:**
    - Admin/Compliance staff only
    
    **Returns:**
    - 200 OK with risk distribution breakdown
    - 401 Unauthorized if not authenticated
    - 403 Forbidden if not an admin
    """
    try:
        if not current_user.is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only administrators can access this endpoint"
            )
        
        distribution = ComplianceService.get_risk_distribution(db)
        
        return distribution
    
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error getting risk distribution: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get risk distribution"
        )
