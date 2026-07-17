import pytest
import pytest_asyncio
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from models import Base, User, Account, Ledger, Transaction
from ledger_service import LedgerService
from services.realtime_webhook_receiver import PaymentWebhookProcessor


@pytest_asyncio.fixture
async def db_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        yield session

    await engine.dispose()


@pytest_asyncio.fixture
async def seeded_user_account(db_session):
    system_user = User(
        id=1,
        full_name="System Account",
        email="system@example.com",
        hashed_password="hashed",
        is_active=True,
        kyc_status="approved",
    )
    db_session.add(system_user)
    await db_session.flush()

    user = User(
        full_name="Payment User",
        email="payment@example.com",
        hashed_password="hashed",
        is_active=True,
        kyc_status="approved",
    )
    db_session.add(user)
    await db_session.flush()

    account = Account(
        account_number="PAY-1001",
        account_type="checking",
        balance=Decimal("0.00"),
        currency="USD",
        owner_id=user.id,
        status="active",
        kyc_level="full",
    )
    db_session.add(account)
    await db_session.commit()

    return user, account


@pytest.mark.asyncio
async def test_create_deposit_creates_transaction_and_ledger_entries(db_session, seeded_user_account):
    user, account = seeded_user_account

    tx = Transaction(
        user_id=user.id,
        account_id=account.id,
        amount=Decimal("25.50"),
        transaction_type="deposit",
        direction="credit",
        status="completed",
        description="Stripe deposit",
        reference_number="pi_test_123",
    )
    db_session.add(tx)
    await db_session.flush()

    await LedgerService.create_deposit(
        db=db_session,
        user_id=user.id,
        amount=Decimal("25.50"),
        description="Stripe deposit",
        transaction_id=tx.id,
        reference_number="pi_test_123",
    )

    entries = (await db_session.execute(
        __import__('sqlalchemy').select(Ledger).where(Ledger.transaction_id == tx.id)
    )).scalars().all()

    assert len(entries) == 2
    assert {entry.entry_type for entry in entries} == {"debit", "credit"}
    assert await LedgerService.get_user_balance(db_session, user.id) == 25.50


@pytest.mark.asyncio
async def test_process_stripe_payment_creates_deposit_record(db_session, seeded_user_account):
    user, account = seeded_user_account

    result = await PaymentWebhookProcessor.process_stripe_payment(
        db_session,
        {
            "charge": {
                "id": "ch_test_123",
                "amount": 2550,
                "customer": "cus_test_123",
                "description": "Stripe deposit",
            },
            "metadata": {"user_id": user.id},
        },
    )

    assert result["success"] is True
    assert result["provider"] == "stripe"

    tx = (await db_session.execute(
        __import__('sqlalchemy').select(Transaction).where(Transaction.reference_number == "ch_test_123")
    )).scalars().first()

    assert tx is not None
    assert tx.transaction_type == "deposit"
    assert tx.amount == Decimal("25.50")

    entries = (await db_session.execute(
        __import__('sqlalchemy').select(Ledger).where(Ledger.transaction_id == tx.id)
    )).scalars().all()

    assert len(entries) == 2
