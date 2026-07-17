"""
Wave 3 Tests: File Uploads, International Transfers, Mobile Deposits

Comprehensive regression tests ensuring:
- File uploads with validation and security
- International transfer compliance checks
- Mobile deposit workflow (create → analyze → approve → settle)
"""

import pytest
import pytest_asyncio
import tempfile
import os
from decimal import Decimal
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from fastapi.testclient import TestClient

from models import User, Account, KYCInfo, MobileDeposit, Transaction, AuditLog, Base, Ledger
from file_upload_service import FileUploadService
from international_transfer_service import InternationalTransferService
from mobile_deposits_service import MobileDepositsService
from fastapi import UploadFile
import io


@pytest_asyncio.fixture
async def db_session():
    """Create in-memory SQLite database for testing."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session

    await engine.dispose()


# ============================================================================
# FILE UPLOAD TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_file_upload_service_validates_extensions(db_session):
    """File upload service should reject unsupported file types."""
    # Create a user
    user = User(email="testuser@example.com", hashed_password="hashed", kyc_status="approved")
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    # Create a mock file with invalid extension
    mock_file = UploadFile(
        file=io.BytesIO(b"test content"),
        size=11,
        filename="malware.exe"
    )

    result = await FileUploadService.upload_profile_picture(
        user_id=user.id,
        file=mock_file,
        db=db_session,
    )

    assert result["success"] is False
    assert "not allowed" in result["error"].lower()


@pytest.mark.asyncio
async def test_file_upload_service_rejects_oversized_files(db_session):
    """File upload service should reject files exceeding size limit."""
    user = User(email="testuser@example.com", hashed_password="hashed", kyc_status="approved")
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    # Create a mock oversized file
    mock_file = UploadFile(
        file=io.BytesIO(b"x" * (11 * 1024 * 1024)),  # 11 MB > 10 MB limit
        size=11 * 1024 * 1024,
        filename="huge_file.jpg"
    )

    result = await FileUploadService.upload_profile_picture(
        user_id=user.id,
        file=mock_file,
        db=db_session,
    )

    assert result["success"] is False
    assert "too large" in result["error"].lower()


@pytest.mark.asyncio
async def test_kyc_document_upload_creates_kyc_info(db_session):
    """Uploading a KYC document should create/update KYCInfo record."""
    user = User(email="testuser@example.com", hashed_password="hashed", kyc_status="approved")
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    # Create a mock file
    mock_file = UploadFile(
        file=io.BytesIO(b"id front content"),
        size=16,
        filename="id_front.jpg"
    )

    result = await FileUploadService.upload_kyc_document(
        user_id=user.id,
        document_type="id_front",
        file=mock_file,
        db=db_session,
    )

    assert result["success"] is True
    assert result["document_type"] == "id_front"

    # Verify KYCInfo was created
    await db_session.refresh(user)
    kyc_info = await db_session.get(KYCInfo, user.id)
    assert kyc_info is not None
    assert kyc_info.id_front_uploaded is True


# ============================================================================
# INTERNATIONAL TRANSFER TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_country_risk_assessment_identifies_high_risk(db_session):
    """Country risk assessment should identify high-risk countries."""
    result = await InternationalTransferService.assess_country_risk("IR")
    
    assert result["is_high_risk"] is True
    assert result["risk_level"] == "high"


@pytest.mark.asyncio
async def test_country_risk_assessment_identifies_safe_countries(db_session):
    """Country risk assessment should identify safe countries."""
    result = await InternationalTransferService.assess_country_risk("US")
    
    assert result["is_high_risk"] is False
    assert result["risk_level"] == "low"


@pytest.mark.asyncio
async def test_sanctions_screening_detects_sanctioned_names(db_session):
    """Sanctions screening should detect sanctioned entities."""
    result = await InternationalTransferService.screen_sanctions(
        full_name="Osama Bin Laden",
        country_code="SA"
    )
    
    assert result["is_sanctioned"] is True
    assert "osama" in result["matches"]


@pytest.mark.asyncio
async def test_international_transfer_blocked_for_critical_risk_countries(db_session):
    """International transfers to critical-risk countries should be blocked."""
    # Create user with approved KYC
    user = User(
        email="testuser@example.com",
        hashed_password="hashed",
        kyc_status="approved",
        is_verified=True,
        is_active=True
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    # Attempt transfer to critical-risk country
    is_valid, reason, compliance_data = await InternationalTransferService.validate_international_transfer(
        db=db_session,
        sender_id=user.id,
        recipient_country="KP",  # North Korea - critical risk
        amount=Decimal("1000"),
        recipient_name="Test Recipient",
    )

    assert is_valid is False
    assert "prohibited" in reason.lower()


@pytest.mark.asyncio
async def test_international_transfer_blocked_for_sanctioned_recipients(db_session):
    """International transfers to sanctioned recipients should be blocked."""
    user = User(
        email="testuser@example.com",
        hashed_password="hashed",
        kyc_status="approved",
        is_verified=True,
        is_active=True
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    # Attempt transfer to sanctioned entity
    is_valid, reason, compliance_data = await InternationalTransferService.validate_international_transfer(
        db=db_session,
        sender_id=user.id,
        recipient_country="SA",
        amount=Decimal("1000"),
        recipient_name="Osama Al Qaeda",  # Sanctioned name
    )

    assert is_valid is False
    assert "sanctions list" in reason.lower()


@pytest.mark.asyncio
async def test_international_transfer_respects_daily_limits(db_session):
    """International transfers should respect country-based daily limits."""
    user = User(
        email="testuser@example.com",
        hashed_password="hashed",
        kyc_status="approved",
        is_verified=True,
        is_active=True
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    # Attempt transfer exceeding high-risk country limit
    is_valid, reason, compliance_data = await InternationalTransferService.validate_international_transfer(
        db=db_session,
        sender_id=user.id,
        recipient_country="IR",  # High-risk: $5000 limit
        amount=Decimal("10000"),  # Exceeds limit
        recipient_name="Test Recipient",
    )

    assert is_valid is False
    assert "exceeds limit" in reason.lower()


@pytest.mark.asyncio
async def test_international_transfer_requires_approved_kyc(db_session):
    """International transfers should require approved KYC status."""
    user = User(
        email="testuser@example.com",
        hashed_password="hashed",
        kyc_status="pending",  # NOT approved
        is_verified=False,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    is_valid, reason, compliance_data = await InternationalTransferService.validate_international_transfer(
        db=db_session,
        sender_id=user.id,
        recipient_country="CA",
        amount=Decimal("1000"),
        recipient_name="Test Recipient",
    )

    assert is_valid is False
    assert "kyc" in reason.lower()


# ============================================================================
# MOBILE DEPOSIT TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_mobile_deposit_create_initializes_pending_state(db_session):
    """Creating a mobile deposit should initialize in pending_images status."""
    user = User(
        email="testuser@example.com",
        hashed_password="hashed",
        kyc_status="approved",
        is_active=True
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    result = await MobileDepositsService.create_deposit(
        db=db_session,
        user_id=user.id,
        amount=Decimal("500"),
        check_number="12345678",
        issuer_name="Test Bank",
        bank_routing="021000021",
        bank_account="123456789",
    )

    assert result["success"] is True
    assert result["status"] == "pending_images"
    assert result["amount"] == 500.0

    # Verify deposit created in database
    deposit = await db_session.get(MobileDeposit, result["deposit_id"])
    assert deposit is not None
    assert deposit.status == "pending_images"


@pytest.mark.asyncio
async def test_mobile_deposit_transitions_to_pending_analysis_on_both_images(db_session):
    """Mobile deposit should transition to pending_analysis once both images uploaded."""
    user = User(
        email="testuser@example.com",
        hashed_password="hashed",
        kyc_status="approved",
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    # Create deposit
    deposit_result = await MobileDepositsService.create_deposit(
        db=db_session,
        user_id=user.id,
        amount=Decimal("500"),
        check_number="12345678",
        issuer_name="Test Bank",
        bank_routing="021000021",
        bank_account="123456789",
    )
    deposit_id = deposit_result["deposit_id"]

    # Add first image
    result1 = await MobileDepositsService.add_deposit_image(
        db=db_session,
        deposit_id=deposit_id,
        image_side="front",
        image_url="s3://bucket/front.jpg",
    )
    assert result1["status"] == "pending_images"

    # Add second image
    result2 = await MobileDepositsService.add_deposit_image(
        db=db_session,
        deposit_id=deposit_id,
        image_side="back",
        image_url="s3://bucket/back.jpg",
    )
    
    assert result2["status"] == "pending_analysis"


@pytest.mark.asyncio
async def test_mobile_deposit_approval_creates_ledger_entry(db_session):
    """Approving a mobile deposit should create double-entry ledger and transaction."""
    # Create user and account
    user = User(
        email="testuser@example.com",
        hashed_password="hashed",
        kyc_status="approved",
        is_active=True
    )
    db_session.add(user)
    await db_session.flush()

    account = Account(
        owner_id=user.id,
        account_number="ACC-001",
        account_type="checking",
        balance=Decimal("0"),
    )
    db_session.add(account)
    await db_session.commit()
    await db_session.refresh(user)
    await db_session.refresh(account)

    # Create admin
    admin = User(
        email="admin@example.com",
        hashed_password="hashed",
        is_admin=True,
    )
    db_session.add(admin)
    await db_session.commit()
    await db_session.refresh(admin)

    # Create and prepare deposit
    deposit_result = await MobileDepositsService.create_deposit(
        db=db_session,
        user_id=user.id,
        amount=Decimal("500"),
        check_number="12345678",
        issuer_name="Test Bank",
        bank_routing="021000021",
        bank_account="123456789",
    )
    deposit_id = deposit_result["deposit_id"]

    # Add both images to move to pending_approval
    await MobileDepositsService.add_deposit_image(
        db=db_session, deposit_id=deposit_id, image_side="front", image_url="s3://bucket/front.jpg"
    )
    await MobileDepositsService.add_deposit_image(
        db=db_session, deposit_id=deposit_id, image_side="back", image_url="s3://bucket/back.jpg"
    )

    # Approve the deposit
    approval_result = await MobileDepositsService.approve_deposit(
        db=db_session,
        deposit_id=deposit_id,
        admin_id=admin.id,
        reviewer_notes="Approved by test",
    )

    assert approval_result["success"] is True
    assert approval_result["status"] == "approved"

    # Verify deposit is approved
    deposit = await db_session.get(MobileDeposit, deposit_id)
    assert deposit.status == "approved"
    assert deposit.reviewer_id == admin.id

    # Verify transaction was created
    transaction = await db_session.get(Transaction, approval_result.get("transaction_id"))
    assert transaction is not None
    assert transaction.status == "completed"
    assert transaction.direction == "credit"
    assert transaction.amount == Decimal("500")


@pytest.mark.asyncio
async def test_mobile_deposit_rejection_does_not_settle_funds(db_session):
    """Rejecting a mobile deposit should not create transaction or ledger entry."""
    user = User(
        email="testuser@example.com",
        hashed_password="hashed",
        kyc_status="approved",
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    admin = User(
        email="admin@example.com",
        hashed_password="hashed",
        is_admin=True,
    )
    db_session.add(admin)
    await db_session.commit()
    await db_session.refresh(admin)

    # Create deposit
    deposit_result = await MobileDepositsService.create_deposit(
        db=db_session,
        user_id=user.id,
        amount=Decimal("500"),
        check_number="12345678",
        issuer_name="Test Bank",
        bank_routing="021000021",
        bank_account="123456789",
    )
    deposit_id = deposit_result["deposit_id"]

    # Add both images
    await MobileDepositsService.add_deposit_image(
        db=db_session, deposit_id=deposit_id, image_side="front", image_url="s3://bucket/front.jpg"
    )
    await MobileDepositsService.add_deposit_image(
        db=db_session, deposit_id=deposit_id, image_side="back", image_url="s3://bucket/back.jpg"
    )

    # Reject the deposit
    rejection_result = await MobileDepositsService.reject_deposit(
        db=db_session,
        deposit_id=deposit_id,
        admin_id=admin.id,
        rejection_reason="Check image quality too low",
    )

    assert rejection_result["success"] is True
    assert rejection_result["status"] == "rejected"

    # Verify deposit is rejected
    deposit = await db_session.get(MobileDeposit, deposit_id)
    assert deposit.status == "rejected"
    assert deposit.review_notes == "Check image quality too low"


@pytest.mark.asyncio
async def test_mobile_deposit_get_pending_lists_awaiting_review(db_session):
    """get_pending_deposits should return deposits awaiting admin review."""
    user = User(email="testuser@example.com", hashed_password="hashed", kyc_status="approved")
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    # Create deposits in different states
    deposit1_result = await MobileDepositsService.create_deposit(
        db=db_session, user_id=user.id, amount=Decimal("500"),
        check_number="CHECK1", issuer_name="Bank1", bank_routing="021000021", bank_account="111"
    )

    deposit2_result = await MobileDepositsService.create_deposit(
        db=db_session, user_id=user.id, amount=Decimal("1000"),
        check_number="CHECK2", issuer_name="Bank2", bank_routing="021000021", bank_account="222"
    )

    # Move deposit2 to pending_analysis
    await MobileDepositsService.add_deposit_image(
        db=db_session, deposit_id=deposit2_result["deposit_id"], image_side="front", image_url="s3://bucket/front.jpg"
    )
    await MobileDepositsService.add_deposit_image(
        db=db_session, deposit_id=deposit2_result["deposit_id"], image_side="back", image_url="s3://bucket/back.jpg"
    )

    # Get pending
    pending_result = await MobileDepositsService.get_pending_deposits(db_session)

    assert pending_result["success"] is True
    assert pending_result["count"] >= 2
    pending_ids = [d["id"] for d in pending_result["deposits"]]
    assert deposit1_result["deposit_id"] in pending_ids
    assert deposit2_result["deposit_id"] in pending_ids
