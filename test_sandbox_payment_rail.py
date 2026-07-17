import pytest
import pytest_asyncio
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from models import Base, User, Account, Transaction, Ledger
from services.sandbox_payment_rail import SandboxPaymentRailService


@pytest_asyncio.fixture
async def db_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with session_factory() as session:
        yield session

    await engine.dispose()


@pytest_asyncio.fixture
async def sandbox_user(db_session):
    system_user = User(id=1, full_name="System", email="system@example.com", hashed_password="x", is_active=True, kyc_status="approved")
    db_session.add(system_user)
    await db_session.flush()

    user = User(full_name="Sandbox User", email="sandbox@example.com", hashed_password="x", is_active=True, kyc_status="approved")
    db_session.add(user)
    await db_session.flush()

    account = Account(account_number="SANDBOX-001", account_type="checking", balance=Decimal("0.00"), currency="USD", owner_id=user.id, status="active", kyc_level="full")
    db_session.add(account)
    await db_session.commit()

    return user, account


@pytest.mark.asyncio
async def test_sandbox_deposit_creates_transaction_and_ledger(db_session, sandbox_user):
    user, account = sandbox_user

    result = await SandboxPaymentRailService.create_sandbox_deposit(
        db=db_session,
        user_id=user.id,
        amount=Decimal("42.50"),
        description="Sandbox test deposit",
        reference_number="sandbox-001",
    )

    assert result["success"] is True
    assert result["transaction_id"] is not None

    tx = await db_session.get(Transaction, result["transaction_id"])
    assert tx is not None
    assert tx.transaction_type == "deposit"

    ledger_entries = (await db_session.execute(__import__('sqlalchemy').select(Ledger).where(Ledger.transaction_id == tx.id))).scalars().all()
    assert len(ledger_entries) == 2
    assert {entry.entry_type for entry in ledger_entries} == {"debit", "credit"}


@pytest.mark.asyncio
async def test_sandbox_settlement_marks_completed(db_session, sandbox_user):
    user, _ = sandbox_user

    result = await SandboxPaymentRailService.create_sandbox_deposit(
        db=db_session,
        user_id=user.id,
        amount=Decimal("10.00"),
        description="Sandbox settlement test",
        reference_number="sandbox-002",
    )

    tx = await db_session.get(Transaction, result["transaction_id"])
    updated = await SandboxPaymentRailService.simulate_settlement(db_session, tx.id, status="completed")

    assert updated["success"] is True
    assert updated["status"] == "completed"
