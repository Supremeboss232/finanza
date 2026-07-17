"""
File Upload Service

Handles secure file uploads for:
- Profile pictures
- KYC documents (ID, proof of address, SSN)
- Supporting documents

Files are stored locally in organized directories with metadata tracking.
"""

import os
import json
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import UploadFile
from models import User, KYCInfo
import logging

logger = logging.getLogger(__name__)

# Base upload directory (should be configured in production)
UPLOAD_BASE_DIR = os.getenv("UPLOAD_DIR", "/tmp/uploads")
PROFILE_PICS_DIR = os.path.join(UPLOAD_BASE_DIR, "profile_pictures")
KYC_DOCS_DIR = os.path.join(UPLOAD_BASE_DIR, "kyc_documents")
ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "pdf", "gif"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB


class FileUploadService:
    """Service for handling file uploads with validation and tracking."""

    @staticmethod
    def _ensure_directories():
        """Ensure upload directories exist."""
        for directory in [PROFILE_PICS_DIR, KYC_DOCS_DIR]:
            os.makedirs(directory, exist_ok=True)
            logger.info(f"Upload directory ready: {directory}")

    @staticmethod
    def _get_file_extension(filename: str) -> str:
        """Extract file extension."""
        return filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

    @staticmethod
    def _validate_file(file: UploadFile) -> Tuple[bool, str]:
        """Validate uploaded file."""
        if not file.filename:
            return False, "No filename provided"

        ext = FileUploadService._get_file_extension(file.filename)
        if ext not in ALLOWED_EXTENSIONS:
            return False, f"File type .{ext} not allowed. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"

        if file.size and file.size > MAX_FILE_SIZE:
            return False, f"File too large. Max size: {MAX_FILE_SIZE / (1024*1024):.1f} MB"

        return True, "OK"

    @staticmethod
    async def upload_profile_picture(
        user_id: int,
        file: UploadFile,
        db: AsyncSession
    ) -> Dict:
        """
        Upload a profile picture for a user.

        Returns dict with upload status and file path.
        """
        FileUploadService._ensure_directories()

        # Validate file
        is_valid, reason = FileUploadService._validate_file(file)
        if not is_valid:
            return {"success": False, "error": reason}

        try:
            # Generate safe filename: user_id_timestamp.ext
            ext = FileUploadService._get_file_extension(file.filename)
            filename = f"user_{user_id}_{int(datetime.utcnow().timestamp())}.{ext}"
            filepath = os.path.join(PROFILE_PICS_DIR, filename)

            # Read and save file
            contents = await file.read()
            with open(filepath, "wb") as f:
                f.write(contents)

            logger.info(f"Profile picture uploaded for user {user_id}: {filepath}")

            # Update user record
            user = await db.get(User, user_id)
            if user:
                # Store file path in preferences or new field
                user.preferences = json.dumps({"profile_picture_path": filepath})
                db.add(user)
                await db.commit()

            return {
                "success": True,
                "user_id": user_id,
                "filename": filename,
                "filepath": filepath,
                "size": len(contents),
                "uploaded_at": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            logger.error(f"Profile picture upload failed for user {user_id}: {str(e)}")
            return {"success": False, "error": f"Upload failed: {str(e)}"}

    @staticmethod
    async def upload_kyc_document(
        user_id: int,
        document_type: str,  # "id_front", "id_back", "ssn", "proof_of_address"
        file: UploadFile,
        db: AsyncSession
    ) -> Dict:
        """
        Upload a KYC document for a user.

        document_type must be one of: id_front, id_back, ssn, proof_of_address
        """
        FileUploadService._ensure_directories()

        # Validate file
        is_valid, reason = FileUploadService._validate_file(file)
        if not is_valid:
            return {"success": False, "error": reason}

        if document_type not in ["id_front", "id_back", "ssn", "proof_of_address"]:
            return {"success": False, "error": f"Invalid document type: {document_type}"}

        try:
            # Generate safe filename: user_id_doctype_timestamp.ext
            ext = FileUploadService._get_file_extension(file.filename)
            filename = f"user_{user_id}_{document_type}_{int(datetime.utcnow().timestamp())}.{ext}"
            filepath = os.path.join(KYC_DOCS_DIR, filename)

            # Read and save file
            contents = await file.read()
            file_hash = hashlib.sha256(contents).hexdigest()
            with open(filepath, "wb") as f:
                f.write(contents)

            logger.info(f"KYC document uploaded for user {user_id} ({document_type}): {filepath}")

            # Update KYC info record
            kyc_info = await db.get(KYCInfo, user_id)
            if not kyc_info:
                kyc_info = KYCInfo(user_id=user_id)
                db.add(kyc_info)

            # Map document type to model fields
            field_mapping = {
                "id_front": ("id_front_path", "id_front_uploaded"),
                "id_back": ("id_back_path", "id_back_uploaded"),
                "ssn": ("ssn_path", "ssn_uploaded"),
                "proof_of_address": ("proof_of_address_path", "proof_of_address_uploaded"),
            }

            if document_type in field_mapping:
                path_field, uploaded_field = field_mapping[document_type]
                setattr(kyc_info, path_field, filepath)
                setattr(kyc_info, uploaded_field, True)

            db.add(kyc_info)
            await db.commit()

            return {
                "success": True,
                "user_id": user_id,
                "document_type": document_type,
                "filename": filename,
                "filepath": filepath,
                "file_hash": file_hash,
                "size": len(contents),
                "uploaded_at": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            logger.error(f"KYC document upload failed for user {user_id}: {str(e)}")
            return {"success": False, "error": f"Upload failed: {str(e)}"}

    @staticmethod
    async def delete_file(filepath: str, user_id: int) -> Dict:
        """
        Delete an uploaded file (with security checks).

        Ensures file belongs to the user and is in allowed directory.
        """
        try:
            # Security check: ensure path is within allowed directories
            real_path = os.path.realpath(filepath)
            allowed_dirs = [
                os.path.realpath(PROFILE_PICS_DIR),
                os.path.realpath(KYC_DOCS_DIR),
            ]

            if not any(real_path.startswith(d) for d in allowed_dirs):
                return {"success": False, "error": "Invalid file path"}

            # Additional check: filename contains user_id
            if f"user_{user_id}" not in os.path.basename(filepath):
                return {"success": False, "error": "File does not belong to this user"}

            if os.path.exists(real_path):
                os.remove(real_path)
                logger.info(f"File deleted for user {user_id}: {filepath}")
                return {"success": True, "deleted_file": filepath}
            else:
                return {"success": False, "error": "File not found"}

        except Exception as e:
            logger.error(f"File deletion failed: {str(e)}")
            return {"success": False, "error": f"Deletion failed: {str(e)}"}

    @staticmethod
    async def get_user_uploads(user_id: int) -> Dict:
        """Get list of all uploads for a user."""
        FileUploadService._ensure_directories()

        uploads = {"profile_pictures": [], "kyc_documents": []}

        try:
            # List profile pictures
            for filename in os.listdir(PROFILE_PICS_DIR):
                if f"user_{user_id}" in filename:
                    filepath = os.path.join(PROFILE_PICS_DIR, filename)
                    stat = os.stat(filepath)
                    uploads["profile_pictures"].append({
                        "filename": filename,
                        "path": filepath,
                        "size": stat.st_size,
                        "uploaded_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    })

            # List KYC documents
            for filename in os.listdir(KYC_DOCS_DIR):
                if f"user_{user_id}" in filename:
                    filepath = os.path.join(KYC_DOCS_DIR, filename)
                    stat = os.stat(filepath)
                    uploads["kyc_documents"].append({
                        "filename": filename,
                        "path": filepath,
                        "size": stat.st_size,
                        "uploaded_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    })

            return {"success": True, "user_id": user_id, "uploads": uploads}

        except Exception as e:
            logger.error(f"Failed to list uploads for user {user_id}: {str(e)}")
            return {"success": False, "error": str(e)}
