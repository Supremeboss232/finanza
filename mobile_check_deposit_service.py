# mobile_check_deposit_service.py
# Mobile check deposit service for photo-based check deposits

from sqlalchemy.orm import Session
from datetime import datetime
from typing import Optional
import logging
import hashlib
from base64 import b64encode

log = logging.getLogger(__name__)


class MobileDepositService:
    """Service for initiating and managing mobile check deposits"""
    
    @staticmethod
    async def initiate_deposit(
        db: Session,
        account_id: int,
        check_amount: float,
        check_number: str,
        created_by: Optional[int] = None
    ) -> dict:
        """
        Initiate a mobile check deposit
        
        Returns:
            {"success": bool, "deposit_id": int, "session_token": str}
        """
        try:
            from models import MobileDeposit
            
            # Create deposit record
            deposit = MobileDeposit(
                account_id=account_id,
                check_amount=check_amount,
                check_number=check_number,
                status="initiated",
                created_by=created_by,
                created_at=datetime.utcnow()
            )
            
            db.add(deposit)
            db.commit()
            db.refresh(deposit)
            
            # Generate session token
            session_token = hashlib.sha256(
                f"{deposit.id}_{datetime.utcnow().isoformat()}".encode()
            ).hexdigest()
            
            log.info(f"Mobile deposit initiated: {deposit.id} for ${check_amount}")
            
            return {
                "success": True,
                "deposit_id": deposit.id,
                "session_token": session_token,
                "status": "initiated",
                "amount": check_amount
            }
        except Exception as e:
            db.rollback()
            log.error(f"Error initiating deposit: {e}")
            return {"success": False, "error": str(e)}
    
    @staticmethod
    async def upload_check_front(
        db: Session,
        deposit_id: int,
        image_data: bytes,
        image_type: str = "front"
    ) -> dict:
        """
        Upload front side of check image
        
        Args:
            image_data: Raw image bytes
            image_type: "front" or "back"
        
        Returns:
            {"success": bool, "image_id": int}
        """
        try:
            from models import CheckImage, MobileDeposit
            
            # Verify deposit exists
            deposit = db.query(MobileDeposit).filter(
                MobileDeposit.id == deposit_id
            ).first()
            
            if not deposit:
                return {"success": False, "error": "Deposit not found"}
            
            # Calculate image hash
            image_hash = hashlib.sha256(image_data).hexdigest()
            
            # Store image
            check_image = CheckImage(
                deposit_id=deposit_id,
                image_side=image_type,
                image_data=image_data,
                image_hash=image_hash,
                image_size=len(image_data),
                upload_date=datetime.utcnow()
            )
            
            db.add(check_image)
            
            # Update deposit status
            if image_type == "front":
                deposit.front_image_captured = True
            else:
                deposit.back_image_captured = True
            
            db.commit()
            db.refresh(check_image)
            
            log.info(f"Check {image_type} image uploaded: {check_image.id}")
            
            return {
                "success": True,
                "image_id": check_image.id,
                "image_side": image_type,
                "size": len(image_data)
            }
        except Exception as e:
            db.rollback()
            log.error(f"Error uploading check image: {e}")
            return {"success": False, "error": str(e)}
    
    @staticmethod
    async def submit_deposit(
        db: Session,
        deposit_id: int
    ) -> dict:
        """
        Submit deposit for processing after both images uploaded
        
        Returns:
            {"success": bool, "deposit_id": int, "processing_started": bool}
        """
        try:
            from models import MobileDeposit, DepositProcessing
            
            deposit = db.query(MobileDeposit).filter(
                MobileDeposit.id == deposit_id
            ).first()
            
            if not deposit:
                return {"success": False, "error": "Deposit not found"}
            
            # Verify both images captured
            if not (deposit.front_image_captured and deposit.back_image_captured):
                return {"success": False, "error": "Both check images required"}
            
            # Create processing record
            processing = DepositProcessing(
                deposit_id=deposit_id,
                status="submitted",
                submitted_at=datetime.utcnow()
            )
            
            db.add(processing)
            
            # Update deposit status
            deposit.status = "submitted"
            deposit.submitted_at = datetime.utcnow()
            
            db.commit()
            
            log.info(f"Mobile deposit submitted: {deposit_id}")
            
            return {
                "success": True,
                "deposit_id": deposit_id,
                "status": "submitted",
                "processing_started": True
            }
        except Exception as e:
            db.rollback()
            log.error(f"Error submitting deposit: {e}")
            return {"success": False, "error": str(e)}


class CheckProcessingService:
    """Service for OCR processing and check validation"""
    
    @staticmethod
    async def read_check_details(
        db: Session,
        deposit_id: int
    ) -> dict:
        """
        Extract check details via OCR (simulated)
        
        Returns:
            {"success": bool, "ocr_data": {...}}
        """
        try:
            from models import CheckOCRData, CheckImage
            
            # Get check images
            images = db.query(CheckImage).filter(
                CheckImage.deposit_id == deposit_id
            ).all()
            
            if len(images) < 2:
                return {"success": False, "error": "Both check images required"}
            
            # Simulate OCR extraction
            ocr_data = CheckOCRData(
                deposit_id=deposit_id,
                routing_number="021000021",  # Simulated
                account_number="1234567890",  # Simulated
                check_number="1001",  # Simulated
                amount=None,  # Would be extracted from image
                date_field=None,  # Would be extracted
                payee=None,  # Would be extracted
                extracted_at=datetime.utcnow(),
                confidence_score=0.95
            )
            
            db.add(ocr_data)
            db.commit()
            db.refresh(ocr_data)
            
            log.info(f"Check OCR completed: {ocr_data.id}")
            
            return {
                "success": True,
                "ocr_data_id": ocr_data.id,
                "routing_number": ocr_data.routing_number,
                "account_number": ocr_data.account_number,
                "check_number": ocr_data.check_number,
                "confidence_score": ocr_data.confidence_score
            }
        except Exception as e:
            db.rollback()
            log.error(f"Error reading check details: {e}")
            return {"success": False, "error": str(e)}
    
    @staticmethod
    async def validate_check(
        db: Session,
        deposit_id: int
    ) -> dict:
        """
        Validate check routing and account numbers
        
        Returns:
            {"success": bool, "valid": bool, "issues": [...]}
        """
        try:
            from models import MobileDeposit, CheckOCRData
            
            deposit = db.query(MobileDeposit).filter(
                MobileDeposit.id == deposit_id
            ).first()
            
            ocr_data = db.query(CheckOCRData).filter(
                CheckOCRData.deposit_id == deposit_id
            ).first()
            
            if not ocr_data:
                return {"success": False, "error": "OCR data not found"}
            
            issues = []
            
            # Validate routing number (basic check)
            if not ocr_data.routing_number or len(ocr_data.routing_number) != 9:
                issues.append("Invalid routing number")
            
            # Validate account number
            if not ocr_data.account_number or len(ocr_data.account_number) < 8:
                issues.append("Invalid account number")
            
            # Validate amount matches
            if deposit.check_amount and ocr_data.amount:
                if abs(deposit.check_amount - ocr_data.amount) > 0.01:
                    issues.append("Amount mismatch between deposit and check")
            
            # Check for future date
            if ocr_data.date_field:
                if ocr_data.date_field > datetime.utcnow().date():
                    issues.append("Check is post-dated")
            
            valid = len(issues) == 0
            
            log.info(f"Check validation: {deposit_id} - Valid: {valid}")
            
            return {
                "success": True,
                "valid": valid,
                "issues": issues
            }
        except Exception as e:
            db.rollback()
            log.error(f"Error validating check: {e}")
            return {"success": False, "error": str(e)}
    
    @staticmethod
    async def detect_fraud(
        db: Session,
        deposit_id: int
    ) -> dict:
        """
        Perform fraud detection on check deposit
        
        Returns:
            {"success": bool, "risk_level": str, "flags": [...]}
        """
        try:
            from models import MobileDeposit, CheckImage
            
            deposit = db.query(MobileDeposit).filter(
                MobileDeposit.id == deposit_id
            ).first()
            
            flags = []
            risk_score = 0
            
            # Check for duplicate deposits (past 30 days)
            from datetime import timedelta
            recent_deposits = db.query(MobileDeposit).filter(
                MobileDeposit.account_id == deposit.account_id,
                MobileDeposit.check_number == deposit.check_number,
                MobileDeposit.created_at > datetime.utcnow() - timedelta(days=30),
                MobileDeposit.id != deposit_id
            ).first()
            
            if recent_deposits:
                flags.append("Duplicate check detected in past 30 days")
                risk_score += 3
            
            # Check high amount (threshold: $10,000)
            if deposit.check_amount > 10000:
                flags.append("High amount deposit")
                risk_score += 1
            
            # Check image quality flags
            images = db.query(CheckImage).filter(
                CheckImage.deposit_id == deposit_id
            ).all()
            
            for img in images:
                if img.image_size < 50000:  # Less than 50KB
                    flags.append(f"Low quality {img.image_side} image")
                    risk_score += 1
            
            # Determine risk level
            if risk_score >= 3:
                risk_level = "high"
            elif risk_score >= 1:
                risk_level = "medium"
            else:
                risk_level = "low"
            
            log.info(f"Fraud detection: {deposit_id} - Risk: {risk_level}")
            
            return {
                "success": True,
                "risk_level": risk_level,
                "risk_score": risk_score,
                "flags": flags
            }
        except Exception as e:
            log.error(f"Error detecting fraud: {e}")
            return {"success": False, "error": str(e)}


class DepositStatusService:
    """Service for tracking deposit status and holds"""
    
    @staticmethod
    async def get_deposit_status(
        db: Session,
        deposit_id: int
    ) -> dict:
        """
        Get current status of deposit
        
        Returns:
            {"success": bool, "status": str, "details": {...}}
        """
        try:
            from models import MobileDeposit, DepositProcessing, DepositHold
            
            deposit = db.query(MobileDeposit).filter(
                MobileDeposit.id == deposit_id
            ).first()
            
            if not deposit:
                return {"success": False, "error": "Deposit not found"}
            
            processing = db.query(DepositProcessing).filter(
                DepositProcessing.deposit_id == deposit_id
            ).first()
            
            hold = db.query(DepositHold).filter(
                DepositHold.deposit_id == deposit_id
            ).first()
            
            return {
                "success": True,
                "deposit_id": deposit_id,
                "status": deposit.status,
                "amount": deposit.check_amount,
                "processing_status": processing.status if processing else None,
                "hold_amount": hold.hold_amount if hold else 0,
                "hold_until": hold.hold_until.isoformat() if hold else None,
                "created_at": deposit.created_at.isoformat(),
                "submitted_at": deposit.submitted_at.isoformat() if deposit.submitted_at else None
            }
        except Exception as e:
            log.error(f"Error getting deposit status: {e}")
            return {"success": False, "error": str(e)}
    
    @staticmethod
    async def get_hold_information(
        db: Session,
        account_id: int
    ) -> dict:
        """
        Get all active holds for account
        
        Returns:
            {"success": bool, "holds": [...], "total_held": float}
        """
        try:
            from models import DepositHold
            
            holds = db.query(DepositHold).filter(
                DepositHold.account_id == account_id,
                DepositHold.status == "active"
            ).all()
            
            total_held = sum(h.hold_amount for h in holds)
            
            return {
                "success": True,
                "hold_count": len(holds),
                "total_held": total_held,
                "holds": [
                    {
                        "hold_id": h.id,
                        "deposit_id": h.deposit_id,
                        "hold_amount": h.hold_amount,
                        "hold_until": h.hold_until.isoformat(),
                        "reason": h.hold_reason
                    }
                    for h in holds
                ]
            }
        except Exception as e:
            log.error(f"Error getting hold information: {e}")
            return {"success": False, "error": str(e)}
    
    @staticmethod
    async def get_available_funds(
        db: Session,
        account_id: int
    ) -> dict:
        """
        Get available funds considering holds
        
        Returns:
            {"success": bool, "available_balance": float, "on_hold": float}
        """
        try:
            from models import Account, DepositHold
            
            account = db.query(Account).filter(
                Account.id == account_id
            ).first()
            
            if not account:
                return {"success": False, "error": "Account not found"}
            
            # Sum all active holds
            holds = db.query(DepositHold).filter(
                DepositHold.account_id == account_id,
                DepositHold.status == "active"
            ).all()
            
            total_on_hold = sum(h.hold_amount for h in holds)
            available = account.available_balance - total_on_hold
            
            return {
                "success": True,
                "account_balance": account.balance,
                "available_balance": account.available_balance,
                "on_hold": total_on_hold,
                "net_available": available
            }
        except Exception as e:
            log.error(f"Error getting available funds: {e}")
            return {"success": False, "error": str(e)}


class QualityCheckService:
    """Service for check image quality and validation"""
    
    @staticmethod
    async def check_image_quality(
        db: Session,
        deposit_id: int
    ) -> dict:
        """
        Validate check image quality
        
        Returns:
            {"success": bool, "quality_score": float, "issues": [...]}
        """
        try:
            from models import CheckImage
            
            images = db.query(CheckImage).filter(
                CheckImage.deposit_id == deposit_id
            ).all()
            
            issues = []
            quality_score = 1.0
            
            for img in images:
                # Check image size (minimum 100KB recommended)
                if img.image_size < 100000:
                    issues.append(f"{img.image_side} image too small ({img.image_size} bytes)")
                    quality_score -= 0.2
                
                # Check image size (maximum 5MB)
                if img.image_size > 5000000:
                    issues.append(f"{img.image_side} image too large")
                    quality_score -= 0.2
            
            quality_score = max(0, min(1, quality_score))
            
            log.info(f"Image quality check: {deposit_id} - Score: {quality_score}")
            
            return {
                "success": True,
                "quality_score": quality_score,
                "issues": issues,
                "acceptable": quality_score >= 0.7
            }
        except Exception as e:
            log.error(f"Error checking image quality: {e}")
            return {"success": False, "error": str(e)}
    
    @staticmethod
    async def verify_endorsement(
        db: Session,
        deposit_id: int
    ) -> dict:
        """
        Verify check is properly endorsed
        
        Returns:
            {"success": bool, "endorsed": bool, "issues": [...]}
        """
        try:
            from models import MobileDeposit, CheckImage
            
            deposit = db.query(MobileDeposit).filter(
                MobileDeposit.id == deposit_id
            ).first()
            
            if not deposit:
                return {"success": False, "error": "Deposit not found"}
            
            # Get back image (endorsement typically on back)
            back_image = db.query(CheckImage).filter(
                CheckImage.deposit_id == deposit_id,
                CheckImage.image_side == "back"
            ).first()
            
            issues = []
            endorsed = True
            
            if not back_image:
                issues.append("Back image not available for endorsement verification")
                endorsed = False
            
            # In real scenario, would use OCR to detect endorsement text
            # For now, log the check
            
            log.info(f"Endorsement verification: {deposit_id} - Endorsed: {endorsed}")
            
            return {
                "success": True,
                "endorsed": endorsed,
                "issues": issues
            }
        except Exception as e:
            log.error(f"Error verifying endorsement: {e}")
            return {"success": False, "error": str(e)}
    
    @staticmethod
    async def flag_suspicious(
        db: Session,
        deposit_id: int,
        reason: str
    ) -> dict:
        """
        Flag deposit for manual review
        
        Returns:
            {"success": bool, "deposit_id": int}
        """
        try:
            from models import MobileDeposit, DepositException
            
            deposit = db.query(MobileDeposit).filter(
                MobileDeposit.id == deposit_id
            ).first()
            
            if not deposit:
                return {"success": False, "error": "Deposit not found"}
            
            # Create exception record
            exception = DepositException(
                deposit_id=deposit_id,
                exception_type="suspicious_activity",
                description=reason,
                status="flagged",
                created_at=datetime.utcnow()
            )
            
            db.add(exception)
            
            # Update deposit status
            deposit.status = "flagged_for_review"
            
            db.commit()
            
            log.warning(f"Deposit flagged as suspicious: {deposit_id} - {reason}")
            
            return {
                "success": True,
                "deposit_id": deposit_id,
                "status": "flagged_for_review",
                "reason": reason
            }
        except Exception as e:
            db.rollback()
            log.error(f"Error flagging suspicious deposit: {e}")
            return {"success": False, "error": str(e)}
