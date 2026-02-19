#!/usr/bin/env python
"""
QUICK START GUIDE - KYC DOCUMENT TRACKING SYSTEM
==================================================

This guide shows how to use the new KYC document tracking and verification system.
All the issues with "uploaded successfully but backend shows empty" are now fixed!
"""

# 1. SETUP - Run the migration to add new database columns
# =========================================================
# python run_kyc_document_migration.py

# 2. USER UPLOADING DOCUMENTS
# ============================
# User uploads 4 documents via the KYC form:
# - ID Front
# - ID Back  
# - SSN/Tax ID
# - Proof of Address

# Each upload goes to: POST /api/v1/kyc/verify
# With FormData:
# - document_type: "id_front" | "id_back" | "ssn_tax_id" | "proof_of_address"
# - file: <binary file content>

# 3. BACKEND AUTOMATICALLY TRACKS DOCUMENTS
# ==========================================
# After each upload, the system:
# 1. Validates file (type, size ≤ 5MB)
# 2. Saves file to disk
# 3. Updates database flags:
#    - id_front_uploaded = True
#    - id_back_uploaded = True
#    - ssn_uploaded = True
#    - proof_of_address_uploaded = True
# 4. Auto-updates kyc_status:
#    - 1st doc: kyc_status = "pending_documents"
#    - 4th doc: kyc_status = "submitted" + documents_submitted_at timestamp

# 4. GET CURRENT KYC STATUS
# ==========================
# GET /api/v1/kyc/status
# 
# Returns:
# {
#   "kyc_status": "submitted",
#   "documents_uploaded": true,
#   "documents": {
#     "id_front": true,
#     "id_back": true,
#     "ssn": true,
#     "proof_of_address": true
#   },
#   "all_required_uploaded": true,
#   "submission_date": "2025-12-16T13:15:35.554868+00:00"
# }

# 5. VALIDATION ENDPOINTS
# ========================
# POST /api/v1/kyc/validate
# 
# Validates:
# - Age >= 18 years
# - Government ID not expired
# - Proof of address <= 3 months old
#
# Form parameters:
# - date_of_birth: "1990-01-15"
# - id_expiry_date: "2030-01-15"
# - proof_of_address_date: "2025-10-16"

# 6. ADMIN REVIEW & APPROVAL
# ===========================

# APPROVE KYC:
# POST /api/v1/kyc/admin/approve
# Form parameters:
# - user_id: 28
# - reviewer_notes: "Documents verified successfully"
#
# Response: 
# {
#   "status": "success",
#   "kyc_status": "approved",
#   "message": "KYC approved successfully"
# }

# REJECT KYC:
# POST /api/v1/kyc/admin/reject
# Form parameters:
# - user_id: 28
# - rejection_reason: "ID appears to be forged"
#
# Response:
# {
#   "status": "success",
#   "kyc_status": "rejected",
#   "rejection_reason": "ID appears to be forged"
# }

# 7. KEY FEATURES
# ===============

# ✅ AUTOMATIC STATUS TRACKING
# Documents are tracked in real-time:
# - Frontend shows: "✓ ID front uploaded successfully!"
# - Backend shows: id_front_uploaded = True
# - No more mismatch!

# ✅ CLEAR STATE MACHINE
# not_started → pending_documents → submitted → approved/rejected
# Each transition is automatic and audited

# ✅ BUILT-IN VALIDATION
# Age, ID expiry, address recency all validated server-side
# Can't fake documents or bypass requirements

# ✅ ADMIN WORKFLOW
# Clear endpoints for review, approval, rejection
# All decisions tracked with timestamps and reasons

# ✅ AUDIT TRAIL
# Every document tracked:
# - File path stored for security audit
# - All timestamps recorded
# - Rejection reasons saved
# - Admin reviews tracked

# 8. DATABASE SCHEMA
# ==================

"""
kyc_info table now includes:

Document Tracking:
- id_front_uploaded (Boolean)
- id_back_uploaded (Boolean) 
- ssn_uploaded (Boolean)
- proof_of_address_uploaded (Boolean)

File Paths:
- id_front_path (String)
- id_back_path (String)
- ssn_path (String)
- proof_of_address_path (String)

Validation Fields:
- id_expiry_date (DateTime)
- proof_of_address_date (DateTime)
- date_of_birth (DateTime)

Status & Workflow:
- kyc_status (String) - tracks: not_started, pending_documents, submitted, approved, rejected
- rejection_reason (String) - stores rejection reason

Timestamps:
- submitted_at (DateTime) - when record created
- documents_submitted_at (DateTime) - when all docs uploaded
- reviewed_at (DateTime) - when admin reviewed
- approved_at (DateTime) - when admin approved

Index:
- idx_kyc_status - for fast queries by status
"""

# 9. FILE STORAGE
# ================

"""
Location: private/uploads/kyc/

Format: user_{user_id}_{timestamp}_{original_filename}

Example: 
- user_28_20251216141534_id_front.pdf
- user_28_20251216141535_id_back.jpg
- user_28_20251216141535_ssn_doc.pdf
- user_28_20251216141535_address_proof.jpg

Files are:
- Outside web root (private/)
- Timestamped (prevents collisions)
- User-ID organized
- Stored for audit trail
"""

# 10. TESTING
# ===========
# python test_kyc_workflow.py
#
# Tests verify:
# ✅ Document uploads tracked correctly
# ✅ Status auto-transitions work
# ✅ Age validation enforces 18+
# ✅ ID expiry validation works
# ✅ Address recency validation (3 months) works
# ✅ Admin approval workflow works
# ✅ Admin rejection workflow works

# 11. WHAT CHANGED FROM BEFORE
# ==============================

# BEFORE:
# - Frontend: "✓ Document uploaded successfully!"
# - Backend: kyc_info.document_file_path stored, but...
# - Dashboard: "No documents submitted yet"
# - Problem: Frontend and backend completely disconnected

# AFTER:
# - Frontend: "✓ Document uploaded successfully!"
# - Backend: Document flags set (id_front_uploaded=True), kyc_status updated
# - Dashboard: Shows exact document status from database
# - Result: Perfect sync between frontend and backend!

# 12. MIGRATION CHECKLIST
# ========================
# [ ] Run: python run_kyc_document_migration.py
# [ ] Verify: Check kyc_info table has new columns
# [ ] Test: python test_kyc_workflow.py
# [ ] Deploy: Push to production
# [ ] Notify: Users can now upload documents with proper tracking

print(__doc__)
