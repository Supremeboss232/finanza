import pytest
import pytest_asyncio
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from crud import approve_kyc_submission
from models import Account, Base, KYCSubmission, User
from system_fund_service import SystemFundService


@pytest_asyncio.fixture
async def db_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session

    await engine.dispose()


@pytest.mark.asyncio
async def test_system_fund_service_rejects_insufficient_reserve_balance(db_session):
    admin = User(
        full_name="Admin",
        email="admin@example.com",
        hashed_password="x",
        is_active=True,
        is_admin=True,
        kyc_status="approved",
    )
    target = User(
        full_name="Target",
        email="target@example.com",
        hashed_password="x",
        is_active=True,
        kyc_status="approved",
    )
    db_session.add_all([admin, target])
    await db_session.commit()
    await db_session.refresh(admin)
    await db_session.refresh(target)

    reserve = Account(
        account_number="SYS-RESERVE-0001",
        account_type="treasury",
        balance=Decimal("10.00"),
        currency="USD",
        owner_id=admin.id,
        status="active",
        is_admin_account=True,
        is_system_account=True,
    )
    target_account = Account(
        account_number="AC-TEST-001",
        account_type="checking",
        balance=Decimal("0.00"),
        currency="USD",
        owner_id=target.id,
        status="active",
        kyc_level="full",
    )

    db_session.add_all([reserve, target_account])
    await db_session.commit()

    result = await SystemFundService.fund_user_from_system(
        db=db_session,
        target_user_id=target.id,
        target_account_id=target_account.id,
        amount=100.0,
        admin_user_id=admin.id,
        reason="Test reserve safeguard",
    )

    assert result["success"] is False
    assert "reserve" in result["error"].lower()


@pytest.mark.asyncio
async def test_approve_kyc_submission_unlocks_account_for_transactions(db_session):
    user = User(
        full_name="Verified User",
        email="verified@example.com",
        hashed_password="x",
        is_active=False,
        is_verified=False,
        kyc_status="pending",
    )
    account = Account(
        account_number="AC-UNLOCK-001",
        account_type="checking",
        balance=Decimal("0.00"),
        currency="USD",
        owner_id=0,
        status="pending",
        kyc_level="basic",
    )
    submission = KYCSubmission(user_id=0, document_type="passport", document_file_path="/tmp/id.png", status="pending")

    db_session.add_all([user, account, submission])
    await db_session.commit()
    await db_session.refresh(user)

    account.owner_id = user.id
    submission.user_id = user.id
    await db_session.commit()

    result = await approve_kyc_submission(db_session, submission.id)

    refreshed_user = await db_session.get(User, user.id)
    refreshed_account = await db_session.get(Account, account.id)

    assert result is not None
    assert refreshed_user.is_verified is True
    assert refreshed_user.is_active is True
    assert refreshed_user.kyc_status == "approved"
    assert refreshed_account.status == "active"
    assert refreshed_account.kyc_level == "full"
