# routers/hmda_api.py
# HMDA compliance and fair lending API endpoints

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime
from pydantic import BaseModel
from deps import get_db
from hmda_compliance_service import (
    HMDAService,
    FairLendingService,
    HMDAReportingService
)
from audit_service import AuditService

# Pydantic models
class HMDAApplicationRequest(BaseModel):
    applicant_id: int
    property_address: str
    property_type: str  # 1-4 family, condominium, manufactured, multi-family
    loan_purpose: str  # home_purchase, refinancing, home_improvement
    loan_amount: float
    rate_spread: Optional[float] = None
    action_taken_date: Optional[datetime] = None

class HMDAActionTakenRequest(BaseModel):
    action_taken: str  # originated, approved_not_accepted, denied, withdrawn, file_incomplete
    action_date: Optional[datetime] = None

class DemographicsRequest(BaseModel):
    applicant_id: int
    ethnicity_1: str  # hispanic_latino, not_hispanic_latino, not_provided
    ethnicity_2: Optional[str] = None
    race_1: str  # american_indian, asian, black, hawaiian, white, not_provided
    race_2: Optional[str] = None
    sex: str  # male, female, not_provided
    age: int

class FlagForReviewRequest(BaseModel):
    application_id: int
    reason: str
    details: Optional[str] = None

class RemediationPlanRequest(BaseModel):
    application_id: int
    issue: str
    remediation_action: str
    target_completion_date: datetime

router = APIRouter(
    prefix="/api/v1/hmda",
    tags=["hmda"],
    responses={404: {"description": "Not found"}}
)


# ==================== APPLICATIONS ====================

@router.post("/application")
async def record_application(
    request: HMDAApplicationRequest,
    db: Session = Depends(get_db)
) -> dict:
    """
    Record HMDA mortgage application
    Captures loan-level data: purpose, type, amount, property details
    """
    try:
        result = await HMDAService.record_application(
            db=db,
            applicant_id=request.applicant_id,
            property_address=request.property_address,
            property_type=request.property_type,
            loan_purpose=request.loan_purpose,
            loan_amount=request.loan_amount,
            rate_spread=request.rate_spread,
            action_taken_date=request.action_taken_date
        )
        
        if result["success"]:
            await AuditService.log_compliance_action(
                db=db,
                action="hmda_application_recorded",
                details={
                    "application_id": result.get("application_id"),
                    "loan_purpose": request.loan_purpose,
                    "amount": request.loan_amount
                }
            )
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/application/{application_id}")
async def get_application(
    application_id: int,
    db: Session = Depends(get_db)
) -> dict:
    """
    Get HMDA application details
    """
    try:
        from models import HMDAApplication
        
        app = db.query(HMDAApplication).filter(
            HMDAApplication.id == application_id
        ).first()
        
        if not app:
            return {"success": False, "error": "Application not found"}
        
        return {
            "success": True,
            "application_id": application_id,
            "applicant_id": app.applicant_id,
            "property_address": app.property_address,
            "property_type": app.property_type,
            "loan_purpose": app.loan_purpose,
            "loan_amount": app.loan_amount,
            "rate_spread": app.rate_spread,
            "action_taken": app.action_taken,
            "action_taken_date": app.action_taken_date.isoformat() if app.action_taken_date else None,
            "application_date": app.application_date.isoformat(),
            "fair_lending_flagged": app.fair_lending_flagged
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/application/{application_id}/action-taken")
async def update_action_taken(
    application_id: int,
    request: HMDAActionTakenRequest,
    db: Session = Depends(get_db)
) -> dict:
    """
    Update action taken on application (originated, denied, approved_not_accepted, withdrawn, file_incomplete)
    Triggers fair lending analysis
    """
    try:
        result = await HMDAService.update_action_taken(
            db=db,
            application_id=application_id,
            action_taken=request.action_taken,
            action_date=request.action_taken_date
        )
        
        if result["success"]:
            await AuditService.log_compliance_action(
                db=db,
                action="hmda_action_taken_updated",
                details={
                    "application_id": application_id,
                    "action": request.action_taken
                }
            )
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== DEMOGRAPHICS ====================

@router.post("/demographics")
async def record_demographics(
    request: DemographicsRequest,
    db: Session = Depends(get_db)
) -> dict:
    """
    Record applicant demographics (protected class information)
    Ethnicity: Hispanic/Latino, Not Hispanic/Latino, Not Provided
    Race: American Indian/Alaska Native, Asian, Black/African American, Native Hawaiian/Pac Islander, White, Not Provided
    """
    try:
        result = await HMDAService.track_applicant_demographics(
            db=db,
            applicant_id=request.applicant_id,
            ethnicity_1=request.ethnicity_1,
            ethnicity_2=request.ethnicity_2,
            race_1=request.race_1,
            race_2=request.race_2,
            sex=request.sex,
            age=request.age
        )
        
        if result["success"]:
            await AuditService.log_compliance_action(
                db=db,
                action="demographics_recorded",
                details={
                    "applicant_id": request.applicant_id,
                    "ethnicity": request.ethnicity_1,
                    "race": request.race_1,
                    "sex": request.sex
                }
            )
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== FAIR LENDING ====================

@router.get("/fair-lending/approval-rate-analysis")
async def get_approval_rate_analysis(
    start_date: datetime = Query(...),
    end_date: datetime = Query(...),
    min_threshold: float = Query(0.25, ge=0, le=1),
    db: Session = Depends(get_db)
) -> dict:
    """
    Analyze approval rates by protected class
    Flags for review if variance > 0.25% (default threshold)
    """
    try:
        result = await FairLendingService.approval_rate_analysis(
            db=db,
            start_date=start_date,
            end_date=end_date,
            variance_threshold=min_threshold
        )
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/fair-lending/pricing-analysis")
async def get_pricing_analysis(
    start_date: datetime = Query(...),
    end_date: datetime = Query(...),
    min_threshold: float = Query(0.20, ge=0, le=1),
    db: Session = Depends(get_db)
) -> dict:
    """
    Analyze pricing (rate) disparities by protected class
    Flags for review if approval rate parity gap > 20% (default)
    """
    try:
        result = await FairLendingService.pricing_analysis(
            db=db,
            start_date=start_date,
            end_date=end_date,
            variance_threshold=min_threshold
        )
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/fair-lending/terms-analysis")
async def get_terms_analysis(
    start_date: datetime = Query(...),
    end_date: datetime = Query(...),
    db: Session = Depends(get_db)
) -> dict:
    """
    Analyze loan terms disparities (amortization, fees, etc.) by protected class
    """
    try:
        result = await FairLendingService.terms_analysis(
            db=db,
            start_date=start_date,
            end_date=end_date
        )
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/fair-lending/flag-for-review")
async def flag_for_review(
    request: FlagForReviewRequest,
    db: Session = Depends(get_db)
) -> dict:
    """
    Flag application for fair lending review
    """
    try:
        result = await FairLendingService.flag_for_review(
            db=db,
            application_id=request.application_id,
            flag_reason=request.reason,
            details=request.details
        )
        
        if result["success"]:
            await AuditService.log_compliance_action(
                db=db,
                action="fair_lending_review_flagged",
                details={
                    "application_id": request.application_id,
                    "reason": request.reason
                }
            )
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/fair-lending/flagged-applications")
async def get_flagged_applications(
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db)
) -> dict:
    """
    Get all applications flagged for fair lending review
    """
    try:
        from models import HMDAApplication
        
        flagged = db.query(HMDAApplication).filter(
            HMDAApplication.fair_lending_flagged == True
        ).order_by(HMDAApplication.application_date.desc()).limit(limit).all()
        
        return {
            "success": True,
            "flagged_count": len(flagged),
            "applications": [
                {
                    "application_id": app.id,
                    "applicant_id": app.applicant_id,
                    "loan_amount": app.loan_amount,
                    "action_taken": app.action_taken,
                    "flagged_date": app.flagged_date.isoformat() if app.flagged_date else None
                }
                for app in flagged
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== REMEDIATION ====================

@router.post("/remediation-plan")
async def create_remediation_plan(
    request: RemediationPlanRequest,
    db: Session = Depends(get_db)
) -> dict:
    """
    Create remediation plan for fair lending issues
    """
    try:
        result = await FairLendingService.remediation_tracking(
            db=db,
            application_id=request.application_id,
            issue=request.issue,
            remediation_action=request.remediation_action,
            target_completion_date=request.target_completion_date
        )
        
        if result["success"]:
            await AuditService.log_compliance_action(
                db=db,
                action="remediation_plan_created",
                details={
                    "application_id": request.application_id,
                    "issue": request.issue,
                    "target_date": request.target_completion_date.isoformat()
                }
            )
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== REPORTING ====================

@router.post("/submission")
async def submit_hmda_report(
    year: int = Query(...),
    quarter: Optional[int] = None,
    db: Session = Depends(get_db)
) -> dict:
    """
    Generate and submit HMDA report to CFPB
    """
    try:
        result = await HMDAReportingService.generate_submission_file(
            db=db,
            year=year,
            quarter=quarter
        )
        
        if result["success"]:
            # Submit to CFPB
            submission = await HMDAReportingService.submit_to_cfpb(
                db=db,
                report_id=result.get("report_id")
            )
            
            await AuditService.log_compliance_action(
                db=db,
                action="hmda_report_submitted",
                details={
                    "year": year,
                    "quarter": quarter,
                    "application_count": result.get("application_count")
                }
            )
            
            return submission
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/report-status")
async def get_report_submission_status(
    year: int = Query(...),
    quarter: Optional[int] = None,
    db: Session = Depends(get_db)
) -> dict:
    """
    Get HMDA report submission status
    """
    try:
        from models import HMDASubmission
        
        query = db.query(HMDASubmission).filter(
            HMDASubmission.submission_year == year
        )
        
        if quarter:
            query = query.filter(HMDASubmission.submission_quarter == quarter)
        
        submission = query.order_by(HMDASubmission.submission_date.desc()).first()
        
        if not submission:
            return {
                "success": True,
                "status": "not_submitted",
                "year": year,
                "quarter": quarter
            }
        
        return {
            "success": True,
            "status": submission.submission_status,
            "year": year,
            "quarter": quarter,
            "submission_date": submission.submission_date.isoformat(),
            "application_count": submission.total_applications,
            "cfpb_confirmation": submission.cfpb_confirmation_id
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/compliance-summary")
async def get_compliance_summary(
    start_date: datetime = Query(...),
    end_date: datetime = Query(...),
    db: Session = Depends(get_db)
) -> dict:
    """
    Get HMDA compliance summary for period
    """
    try:
        result = await HMDAService.generate_hmda_report(
            db=db,
            start_date=start_date,
            end_date=end_date
        )
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== HEALTH ====================

@router.get("/health")
async def health() -> dict:
    """Health check for HMDA API"""
    return {"status": "healthy", "service": "hmda_api"}
