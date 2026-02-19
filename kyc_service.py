"""
KYC Service - Handles document uploads, validation, and status management
"""

import os
import shutil
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, Tuple
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models import KYCInfo, User, KYCSubmission

# Upload directory for KYC documents
KYC_UPLOAD_DIR = Path("private/uploads/kyc")
KYC_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# File validation
ALLOWED_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png"}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB


class KYCService:
    """Service for managing KYC document uploads and verification"""
    
    @staticmethod
    async def save_document(
        db_session: AsyncSession,
        user_id: int,
        document_type: str,
        file_content: bytes,
        filename: str
    ) -> Tuple[bool, str, Optional[str]]:
        """
        Save a KYC document and update user's KYC tracking.
        
        Args:
            db_session: Database session
            user_id: User ID
            document_type: Type of document (id_front, id_back, ssn_tax_id, proof_of_address)
            file_content: File bytes
            filename: Original filename
            
        Returns:
            (success: bool, message: str, file_path: Optional[str])
        """
        try:
            # Validate file
            is_valid, error_msg = KYCService._validate_file(filename, len(file_content))
            if not is_valid:
                return False, error_msg, None
            
            # Get or create KYC info
            result = await db_session.execute(
                select(KYCInfo).where(KYCInfo.user_id == user_id)
            )
            kyc_info = result.scalars().first()
            
            if not kyc_info:
                kyc_info = KYCInfo(
                    user_id=user_id,
                    kyc_status="pending_documents"
                )
                db_session.add(kyc_info)
            
            # Check if KYC is already submitted (form is locked)
            if kyc_info.kyc_submitted or kyc_info.submission_locked:
                return False, "Cannot upload documents: KYC has already been submitted. Verification is in progress.", None
            
            # Save file
            timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
            safe_filename = f"user_{user_id}_{timestamp}_{filename}".replace(" ", "_")
            file_path = KYC_UPLOAD_DIR / safe_filename
            
            with open(file_path, "wb") as f:
                f.write(file_content)
            
            # Update KYC info based on document type
            if document_type == "id_front":
                kyc_info.id_front_uploaded = True
                kyc_info.id_front_path = str(file_path)
                message = "ID front uploaded successfully!"
            elif document_type == "id_back":
                kyc_info.id_back_uploaded = True
                kyc_info.id_back_path = str(file_path)
                message = "ID back uploaded successfully!"
            elif document_type == "ssn_tax_id":
                kyc_info.ssn_uploaded = True
                kyc_info.ssn_path = str(file_path)
                message = "SSN/Tax ID document uploaded successfully!"
            elif document_type == "proof_of_address":
                kyc_info.proof_of_address_uploaded = True
                kyc_info.proof_of_address_path = str(file_path)
                message = "Proof of address uploaded successfully!"
            else:
                return False, f"Unknown document type: {document_type}", None
            
            # Check if all required documents are uploaded
            if KYCService._all_documents_uploaded(kyc_info):
                kyc_info.kyc_status = "submitted"
                kyc_info.documents_submitted_at = datetime.utcnow()
            
            # Save to database
            db_session.add(kyc_info)
            await db_session.commit()
            await db_session.refresh(kyc_info)
            
            return True, message, str(file_path)
            
        except Exception as e:
            await db_session.rollback()
            return False, f"Error saving document: {str(e)}", None
    
    @staticmethod
    def _validate_file(filename: str, file_size: int) -> Tuple[bool, str]:
        """Validate file size and extension"""
        if file_size > MAX_FILE_SIZE:
            return False, f"File size exceeds 5MB limit. Size: {file_size / 1024 / 1024:.2f}MB"
        
        file_ext = Path(filename).suffix.lower()
        if file_ext not in ALLOWED_EXTENSIONS:
            allowed = ", ".join(ALLOWED_EXTENSIONS)
            return False, f"File type not allowed. Allowed: {allowed}"
        
        return True, ""
    
    @staticmethod
    def _all_documents_uploaded(kyc_info: KYCInfo) -> bool:
        """Check if all required documents have been uploaded"""
        return (
            kyc_info.id_front_uploaded and
            kyc_info.id_back_uploaded and
            kyc_info.ssn_uploaded and
            kyc_info.proof_of_address_uploaded
        )
    
    @staticmethod
    async def get_kyc_status(db_session: AsyncSession, user_id: int) -> dict:
        """Get detailed KYC status for a user"""
        # Get user to check their kyc_status field (source of truth for approval)
        user_result = await db_session.execute(
            select(User).where(User.id == user_id)
        )
        user = user_result.scalars().first()
        
        result = await db_session.execute(
            select(KYCInfo).where(KYCInfo.user_id == user_id)
        )
        kyc_info = result.scalars().first()
        
        if not kyc_info:
            # Check if user is verified (approved) even without KYCInfo record
            kyc_status = user.kyc_status if user else "not_started"
            return {
                "kyc_status": kyc_status,
                "documents_uploaded": False,
                "documents": {
                    "id_front": False,
                    "id_back": False,
                    "ssn": False,
                    "proof_of_address": False
                },
                "all_required_uploaded": False,
                "submission_date": None,
                "review_status": None
            }
        
        # Use user.kyc_status as source of truth (set by approval process)
        final_kyc_status = user.kyc_status if user and user.kyc_status else kyc_info.kyc_status
        
        return {
            "kyc_status": final_kyc_status,
            "documents_uploaded": kyc_info.documents_submitted_at is not None,
            "documents": {
                "id_front": kyc_info.id_front_uploaded,
                "id_back": kyc_info.id_back_uploaded,
                "ssn": kyc_info.ssn_uploaded,
                "proof_of_address": kyc_info.proof_of_address_uploaded
            },
            "all_required_uploaded": KYCService._all_documents_uploaded(kyc_info),
            "submission_date": kyc_info.documents_submitted_at.isoformat() if kyc_info.documents_submitted_at else None,
            "review_status": kyc_info.status,
            "approval_date": kyc_info.approved_at.isoformat() if kyc_info.approved_at else None,
            "rejection_reason": kyc_info.rejection_reason
        }
    
    @staticmethod
    async def validate_kyc_documents(
        db_session: AsyncSession,
        user_id: int,
        date_of_birth: Optional[datetime] = None,
        id_expiry_date: Optional[datetime] = None,
        proof_of_address_date: Optional[datetime] = None
    ) -> Tuple[bool, str]:
        """
        Validate KYC documents for age, ID expiry, and address recency.
        
        Returns:
            (is_valid: bool, error_message: str)
        """
        errors = []
        
        # Check age >= 18
        if date_of_birth:
            age = (datetime.utcnow() - date_of_birth).days / 365.25
            if age < 18:
                errors.append(f"User must be at least 18 years old (Currently {age:.1f} years)")
        
        # Check ID not expired
        if id_expiry_date:
            if id_expiry_date < datetime.utcnow():
                errors.append("Government ID is expired")
        
        # Check proof of address is recent (within 3 months)
        if proof_of_address_date:
            days_old = (datetime.utcnow() - proof_of_address_date).days
            if days_old > 90:
                errors.append(f"Proof of address is too old ({days_old} days). Must be within 3 months.")
        
        if errors:
            return False, " | ".join(errors)
        
        return True, ""
    
    @staticmethod
    async def approve_kyc(
        db_session: AsyncSession,
        user_id: int,
        reviewer_notes: str = ""
    ) -> Tuple[bool, str]:
        """Approve a KYC submission"""
        try:
            result = await db_session.execute(
                select(KYCInfo).where(KYCInfo.user_id == user_id)
            )
            kyc_info = result.scalars().first()
            
            if not kyc_info:
                return False, "KYC info not found"
            
            if not KYCService._all_documents_uploaded(kyc_info):
                return False, "Not all required documents have been uploaded"
            
            kyc_info.kyc_status = "approved"
            kyc_info.status = "approved"
            kyc_info.reviewed_at = datetime.utcnow()
            kyc_info.approved_at = datetime.utcnow()
            
            # Update user's kyc_status in User table
            user_result = await db_session.execute(
                select(User).where(User.id == user_id)
            )
            user = user_result.scalars().first()
            if user:
                user.kyc_status = "approved"
            
            db_session.add(kyc_info)
            if user:
                db_session.add(user)
            await db_session.commit()
            
            return True, "KYC approved successfully"
            
        except Exception as e:
            await db_session.rollback()
            return False, f"Error approving KYC: {str(e)}"
    
    @staticmethod
    async def reject_kyc(
        db_session: AsyncSession,
        user_id: int,
        rejection_reason: str
    ) -> Tuple[bool, str]:
        """
        Reject a KYC submission with reason.
        
        Sets:
        - kyc_status = 'rejected'
        - rejection_reason = provided reason
        - Unlocks form (kyc_submitted = False, submission_locked = False)
        
        User can now resubmit KYC.
        """
        try:
            result = await db_session.execute(
                select(KYCInfo).where(KYCInfo.user_id == user_id)
            )
            kyc_info = result.scalars().first()
            
            if not kyc_info:
                return False, "KYC info not found"
            
            kyc_info.kyc_status = "rejected"
            kyc_info.status = "rejected"
            kyc_info.rejection_reason = rejection_reason
            kyc_info.reviewed_at = datetime.utcnow()
            # Unlock form for resubmission
            kyc_info.kyc_submitted = False
            kyc_info.submission_locked = False
            
            # Update user's kyc_status in User table
            user_result = await db_session.execute(
                select(User).where(User.id == user_id)
            )
            user = user_result.scalars().first()
            if user:
                user.kyc_status = "rejected"
            
            db_session.add(kyc_info)
            if user:
                db_session.add(user)
            await db_session.commit()
            
            return True, "KYC rejected with reason provided. User can now resubmit their KYC."
            
        except Exception as e:
            await db_session.rollback()
            return False, f"Error rejecting KYC: {str(e)}"

    @staticmethod
    async def submit_kyc_form(
        db_session: AsyncSession,
        user_id: int,
        email: str = None,
        document_type: str = None,
        document_number: str = None
    ) -> Tuple[bool, str, dict]:
        """
        Finalize and lock KYC submission.
        
        Accepts and stores:
        1. Email address from user
        2. Document type (e.g., passport, national_id)
        3. Document number (ID number)
        
        Validates:
        1. All required documents are uploaded
        2. Sets kyc_submitted = True (form lock flag)
        3. Sets submission_locked = True (prevents edits)
        4. Updates kyc_status = 'submitted'
        5. Records submission_timestamp
        6. Stores email, document_type, document_number to KYCInfo
        
        After this, user cannot modify documents or personal details
        until admin approves or rejects.
        
        Returns:
            (success: bool, message: str, kyc_data: dict)
        """
        try:
            # Get current user's KYC info
            result = await db_session.execute(
                select(KYCInfo).where(KYCInfo.user_id == user_id)
            )
            kyc_info = result.scalars().first()
            
            if not kyc_info:
                return False, "No KYC record found. Please upload documents first.", {}
            
            # Check if already submitted
            if kyc_info.kyc_submitted:
                return False, "KYC has already been submitted. Verification is in progress.", {
                    "submission_timestamp": kyc_info.submission_timestamp.isoformat() if kyc_info.submission_timestamp else None
                }
            
            # Check if all required documents are uploaded
            if not KYCService._all_documents_uploaded(kyc_info):
                missing = []
                if not kyc_info.id_front_uploaded:
                    missing.append("Government ID - Front")
                if not kyc_info.id_back_uploaded:
                    missing.append("Government ID - Back")
                if not kyc_info.ssn_uploaded:
                    missing.append("SSN/Tax ID")
                if not kyc_info.proof_of_address_uploaded:
                    missing.append("Proof of Address")
                
                return False, f"Cannot submit: Missing documents - {', '.join(missing)}", {}
            
            # Store email, document_type, and document_number (submitted from form)
            if email:
                kyc_info.email = email  # Store for reference (if column exists)
            if document_type:
                kyc_info.document_type = document_type
            if document_number:
                kyc_info.document_number = document_number
            
            # Log what we're storing
            print(f"\n💾 Storing KYC submission data:")
            print(f"   User ID: {user_id}")
            print(f"   Email: {email}")
            print(f"   Document Type: {document_type}")
            print(f"   Document Number: {document_number}")
            
            # Lock the form
            kyc_info.kyc_submitted = True
            kyc_info.submission_locked = True
            kyc_info.kyc_status = "submitted"
            kyc_info.submission_timestamp = datetime.utcnow()
            kyc_info.documents_submitted_at = datetime.utcnow()
            
            # Also update user's kyc_status in users table
            result = await db_session.execute(
                select(User).where(User.id == user_id)
            )
            user = result.scalars().first()
            
            if user:
                user.kyc_status = "submitted"
            
            db_session.add(kyc_info)
            if user:
                db_session.add(user)
            
            # Create a KYCSubmission record for admin dashboard visibility
            try:
                kyc_submission = KYCSubmission(
                    user_id=user_id,
                    document_type=document_type or "unknown",
                    document_file_path=f"kyc_info_{kyc_info.id}",
                    status="pending"
                )
                db_session.add(kyc_submission)
                print(f"✅ Created KYCSubmission for user {user_id}")
            except Exception as ks_error:
                print(f"⚠️  Could not create KYCSubmission: {str(ks_error)}")
                # Continue anyway - KYCInfo is the primary record
            
            await db_session.commit()
            
            return True, "KYC submitted successfully! Your documents are now under review and cannot be modified.", {
                "submission_timestamp": kyc_info.submission_timestamp.isoformat() if kyc_info.submission_timestamp else None,
                "kyc_id": kyc_info.id,
                "email": email,
                "document_type": document_type,
                "document_number": document_number
            }
            
        except Exception as e:
            await db_session.rollback()
            print(f"❌ Error in submit_kyc_form: {str(e)}")
            return False, f"Error submitting KYC: {str(e)}", {}

    @staticmethod
    async def unlock_kyc_for_resubmission(
        db_session: AsyncSession,
        user_id: int
    ) -> Tuple[bool, str]:
        """
        Unlock KYC form after rejection to allow user to resubmit.
        
        Sets:
        - kyc_submitted = False
        - submission_locked = False
        - kyc_status = 'rejected' (already set by reject_kyc)
        
        Returns:
            (success: bool, message: str)
        """
        try:
            result = await db_session.execute(
                select(KYCInfo).where(KYCInfo.user_id == user_id)
            )
            kyc_info = result.scalars().first()
            
            if not kyc_info:
                return False, "No KYC record found"
            
            # Unlock the form
            kyc_info.kyc_submitted = False
            kyc_info.submission_locked = False
            
            db_session.add(kyc_info)
            await db_session.commit()
            
            return True, "KYC unlocked for resubmission"
            
        except Exception as e:
            await db_session.rollback()
            return False, f"Error unlocking KYC: {str(e)}"

