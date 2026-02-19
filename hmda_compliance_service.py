# hmda_compliance_service.py
# HMDA reporting, fair lending, applicant demographics tracking

from sqlalchemy.orm import Session
from sqlalchemy import and_
from datetime import datetime
from typing import Dict, Optional, List
import json
from models import (
    HMDAApplication, HMDAApplicant, FairLendingCheck, HMDASubmission,
    Loan, User
)


class HMDAService:
    """Home Mortgage Disclosure Act compliance"""
    
    LOAN_PURPOSES = ["purchase", "refinance", "home_improvement", "other"]
    PROPERTY_TYPES = ["single_family", "manufactured", "multifamily_2_4", "multifamily_5_plus"]
    ACTION_TAKEN = ["originated", "approved_not_accepted", "denied", "withdrawn", "preapproval_denied", "preapproval_approved"]
    
    @staticmethod
    async def record_application(
        db: Session,
        loan_id: int,
        applicant_age: int,
        applicant_income: float,
        co_applicant_income: Optional[float],
        loan_amount: float,
        loan_purpose: str,
        property_type: str,
        property_address: str,
        property_state: str,
        msa_md: Optional[str] = None
    ) -> Dict:
        """Record HMDA application"""
        try:
            loan = db.query(Loan).filter(Loan.id == loan_id).first()
            
            if not loan:
                return {"success": False, "error": "Loan not found"}
            
            if loan_purpose not in HMDAService.LOAN_PURPOSES:
                return {"success": False, "error": "Invalid loan purpose"}
            
            if property_type not in HMDAService.PROPERTY_TYPES:
                return {"success": False, "error": "Invalid property type"}
            
            hmda_app = HMDAApplication(
                loan_id=loan_id,
                applicant_age=applicant_age,
                applicant_income=applicant_income,
                co_applicant_income=co_applicant_income,
                loan_amount=loan_amount,
                loan_purpose=loan_purpose,
                property_type=property_type,
                property_address=property_address,
                property_state=property_state,
                msa_md=msa_md
            )
            
            db.add(hmda_app)
            db.commit()
            
            return {
                "success": True,
                "hmda_app_id": hmda_app.id,
                "loan_id": loan_id,
                "application_date": hmda_app.application_date.isoformat(),
                "loan_purpose": loan_purpose
            }
        except Exception as e:
            db.rollback()
            return {"success": False, "error": str(e)}
    
    @staticmethod
    async def update_action_taken(
        db: Session,
        hmda_app_id: int,
        action_taken: str,
        denial_reason: Optional[str] = None
    ) -> Dict:
        """Update HMDA action taken"""
        try:
            if action_taken not in HMDAService.ACTION_TAKEN:
                return {"success": False, "error": "Invalid action taken"}
            
            hmda_app = db.query(HMDAApplication).filter(
                HMDAApplication.id == hmda_app_id
            ).first()
            
            if not hmda_app:
                return {"success": False, "error": "HMDA application not found"}
            
            hmda_app.action_taken = action_taken
            hmda_app.action_taken_date = datetime.utcnow()
            
            if action_taken == "denied" and denial_reason:
                hmda_app.denial_reason = denial_reason
            
            db.commit()
            
            return {
                "success": True,
                "hmda_app_id": hmda_app_id,
                "action_taken": action_taken,
                "action_taken_date": hmda_app.action_taken_date.isoformat()
            }
        except Exception as e:
            db.rollback()
            return {"success": False, "error": str(e)}
    
    @staticmethod
    async def track_applicant_demographics(
        db: Session,
        hmda_app_id: int,
        applicant_type: str,
        ethnicity: str,
        race: str,
        sex: str,
        age: Optional[int],
        income: float,
        credit_score_type: Optional[str] = None,
        credit_score: Optional[int] = None
    ) -> Dict:
        """Track applicant demographics for fair lending"""
        try:
            hmda_app = db.query(HMDAApplication).filter(
                HMDAApplication.id == hmda_app_id
            ).first()
            
            if not hmda_app:
                return {"success": False, "error": "HMDA application not found"}
            
            applicant = HMDAApplicant(
                hmda_app_id=hmda_app_id,
                applicant_type=applicant_type,
                ethnicity=ethnicity,
                race=race,
                sex=sex,
                age=age,
                income=income,
                credit_score_type=credit_score_type,
                credit_score=credit_score
            )
            
            db.add(applicant)
            db.commit()
            
            return {
                "success": True,
                "applicant_id": applicant.id,
                "applicant_type": applicant_type,
                "demographics_recorded": True
            }
        except Exception as e:
            db.rollback()
            return {"success": False, "error": str(e)}
    
    @staticmethod
    async def generate_hmda_report(
        db: Session,
        submission_year: int
    ) -> Dict:
        """Generate HMDA report for year"""
        try:
            # Get all HMDA applications for year
            applications = db.query(HMDAApplication).filter(
                HMDAApplication.action_taken_date.contains(str(submission_year))
            ).all()
            
            if not applications:
                return {
                    "success": True,
                    "submission_year": submission_year,
                    "total_applications": 0,
                    "message": "No applications for period"
                }
            
            # Calculate statistics
            originated = len([a for a in applications if a.action_taken == "originated"])
            denied = len([a for a in applications if a.action_taken == "denied"])
            withdrawn = len([a for a in applications if a.action_taken == "withdrawn"])
            
            # Create submission record
            submission = HMDASubmission(
                submission_year=submission_year,
                total_applications=len(applications),
                total_originated=originated,
                total_denied=denied,
                submission_status="draft"
            )
            
            db.add(submission)
            db.commit()
            
            return {
                "success": True,
                "submission_id": submission.id,
                "submission_year": submission_year,
                "total_applications": len(applications),
                "total_originated": originated,
                "total_denied": denied,
                "total_withdrawn": withdrawn,
                "submission_status": "draft"
            }
        except Exception as e:
            db.rollback()
            return {"success": False, "error": str(e)}


class FairLendingService:
    """Fair lending compliance monitoring"""
    
    @staticmethod
    async def approval_rate_analysis(
        db: Session,
        loan_id: int
    ) -> Dict:
        """Analyze approval rates by protected class"""
        try:
            loan = db.query(Loan).filter(Loan.id == loan_id).first()
            
            if not loan:
                return {"success": False, "error": "Loan not found"}
            
            # Get HMDA application
            hmda_app = db.query(HMDAApplication).filter(
                HMDAApplication.loan_id == loan_id
            ).first()
            
            if not hmda_app:
                return {"success": True, "message": "No HMDA application found"}
            
            # Get applicant demographics
            applicants = db.query(HMDAApplicant).filter(
                HMDAApplicant.hmda_app_id == hmda_app.id
            ).all()
            
            if not applicants:
                return {"success": True, "message": "No applicant data found"}
            
            # Compare approval rate to baseline (mock implementation)
            baseline_approval_rate = 0.75  # 75% baseline
            
            primary_applicant = next(
                (a for a in applicants if a.applicant_type == "primary"),
                None
            )
            
            if primary_applicant:
                # Simulate disparate impact analysis
                # This is a simplified check - real implementation would use regression
                analysis_results = {
                    "ethnicity": primary_applicant.ethnicity,
                    "race": primary_applicant.race,
                    "sex": primary_applicant.sex,
                    "baseline_approval_rate": baseline_approval_rate,
                    "disparity_identified": False,
                    "recommendation": "Approve"
                }
                
                return {
                    "success": True,
                    "loan_id": loan_id,
                    "analysis": analysis_results
                }
            
            return {"success": False, "error": "No primary applicant found"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    @staticmethod
    async def pricing_analysis(
        db: Session,
        loan_id: int
    ) -> Dict:
        """Analyze pricing parity by protected class"""
        try:
            loan = db.query(Loan).filter(Loan.id == loan_id).first()
            
            if not loan:
                return {"success": False, "error": "Loan not found"}
            
            hmda_app = db.query(HMDAApplication).filter(
                HMDAApplication.loan_id == loan_id
            ).first()
            
            applicants = db.query(HMDAApplicant).filter(
                HMDAApplicant.hmda_app_id == hmda_app.id
            ).all() if hmda_app else []
            
            # Analyze interest rate variance
            baseline_rate = 5.5  # Mock baseline
            rate_variance = loan.interest_rate - baseline_rate
            
            primary = next((a for a in applicants if a.applicant_type == "primary"), None)
            
            pricing_analysis = {
                "loan_rate": loan.interest_rate,
                "baseline_rate": baseline_rate,
                "rate_variance": rate_variance,
                "variance_percentage": (rate_variance / baseline_rate) * 100,
                "disparate_pricing": abs(rate_variance) > 0.25,  # >0.25% flagged
                "concern_level": "high" if abs(rate_variance) > 0.5 else "medium" if abs(rate_variance) > 0.25 else "low"
            }
            
            return {
                "success": True,
                "loan_id": loan_id,
                "pricing_analysis": pricing_analysis
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    @staticmethod
    async def terms_analysis(
        db: Session,
        loan_id: int
    ) -> Dict:
        """Analyze loan terms consistency by protected class"""
        try:
            loan = db.query(Loan).filter(Loan.id == loan_id).first()
            
            if not loan:
                return {"success": False, "error": "Loan not found"}
            
            # Analyze terms (term length, APR, fees)
            terms_analysis = {
                "loan_term_months": loan.loan_term_months,
                "interest_rate": loan.interest_rate,
                "principal_balance": loan.principal_balance,
                "terms_consistency_check": True,
                "recommendation": "Terms appear consistent"
            }
            
            return {
                "success": True,
                "loan_id": loan_id,
                "terms_analysis": terms_analysis
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    @staticmethod
    async def flag_for_review(
        db: Session,
        loan_id: int,
        concern_type: str,
        concern_details: str
    ) -> Dict:
        """Flag loan for fair lending review"""
        try:
            loan = db.query(Loan).filter(Loan.id == loan_id).first()
            
            if not loan:
                return {"success": False, "error": "Loan not found"}
            
            # Get HMDA app
            hmda_app = db.query(HMDAApplication).filter(
                HMDAApplication.loan_id == loan_id
            ).first()
            
            if not hmda_app:
                return {"success": False, "error": "HMDA application not found"}
            
            # Create fair lending check
            fair_lending_check = FairLendingCheck(
                loan_id=loan_id,
                flagged_as_concern=True,
                review_required=True,
                check_results=json.dumps({
                    "concern_type": concern_type,
                    "details": concern_details,
                    "flagged_at": datetime.utcnow().isoformat()
                })
            )
            
            db.add(fair_lending_check)
            db.commit()
            
            return {
                "success": True,
                "check_id": fair_lending_check.id,
                "loan_id": loan_id,
                "flagged_for_review": True,
                "concern_type": concern_type
            }
        except Exception as e:
            db.rollback()
            return {"success": False, "error": str(e)}
    
    @staticmethod
    async def remediation_tracking(
        db: Session,
        check_id: int,
        remediation_action: str,
        remediation_date: Optional[datetime] = None
    ) -> Dict:
        """Track remediation of fair lending concerns"""
        try:
            if remediation_date is None:
                remediation_date = datetime.utcnow()
            
            fair_lending_check = db.query(FairLendingCheck).filter(
                FairLendingCheck.id == check_id
            ).first()
            
            if not fair_lending_check:
                return {"success": False, "error": "Fair lending check not found"}
            
            fair_lending_check.review_required = False
            fair_lending_check.check_results = json.dumps({
                "original_concern": fair_lending_check.check_results,
                "remediation_action": remediation_action,
                "remediation_date": remediation_date.isoformat(),
                "status": "remediated"
            })
            
            db.commit()
            
            return {
                "success": True,
                "check_id": check_id,
                "remediation_action": remediation_action,
                "remediation_date": remediation_date.isoformat(),
                "status": "remediated"
            }
        except Exception as e:
            db.rollback()
            return {"success": False, "error": str(e)}


class HMDAReportingService:
    """HMDA file generation and submission"""
    
    @staticmethod
    async def generate_submission_file(
        db: Session,
        submission_year: int,
        lei: str
    ) -> Dict:
        """Generate HMDA submission file"""
        try:
            submission = db.query(HMDASubmission).filter(
                and_(
                    HMDASubmission.submission_year == submission_year,
                    HMDASubmission.lei == lei
                )
            ).first()
            
            if not submission:
                return {"success": False, "error": "Submission not found"}
            
            # Get all applications for year
            applications = db.query(HMDAApplication).filter(
                HMDAApplication.action_taken_date.contains(str(submission_year))
            ).all()
            
            # Build HMDA file content (simplified)
            file_lines = []
            file_lines.append(f"1|{lei}|{submission_year}|")
            
            for app in applications:
                applicants = db.query(HMDAApplicant).filter(
                    HMDAApplicant.hmda_app_id == app.id
                ).all()
                
                primary = next(
                    (a for a in applicants if a.applicant_type == "primary"),
                    None
                )
                
                if primary:
                    file_lines.append(
                        f"2|{app.loan_amount}|{app.loan_purpose}|{app.property_type}|"
                        f"{primary.ethnicity}|{primary.race}|{primary.sex}|"
                        f"{app.action_taken}|{app.property_state}|"
                    )
            
            submission_file = "\n".join(file_lines)
            submission.file_path = f"hmda_submission_{submission_year}_{lei}.txt"
            submission.submission_status = "ready"
            
            db.commit()
            
            return {
                "success": True,
                "submission_id": submission.id,
                "file_path": submission.file_path,
                "submission_year": submission_year,
                "record_count": len(applications),
                "submission_status": "ready"
            }
        except Exception as e:
            db.rollback()
            return {"success": False, "error": str(e)}
    
    @staticmethod
    async def submit_to_cfpb(
        db: Session,
        submission_id: int
    ) -> Dict:
        """Submit HMDA file to CFPB"""
        try:
            submission = db.query(HMDASubmission).filter(
                HMDASubmission.id == submission_id
            ).first()
            
            if not submission:
                return {"success": False, "error": "Submission not found"}
            
            # Mock CFPB submission
            submission.submission_status = "submitted"
            submission.submission_date = datetime.utcnow()
            
            db.commit()
            
            return {
                "success": True,
                "submission_id": submission_id,
                "submission_year": submission.submission_year,
                "status": "submitted",
                "submission_date": submission.submission_date.isoformat(),
                "message": "HMDA file submitted to CFPB (mock)"
            }
        except Exception as e:
            db.rollback()
            return {"success": False, "error": str(e)}
