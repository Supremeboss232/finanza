import pytest
import pytest_asyncio
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy import select

from models import Base, User, Account, Loan, Investment, Card, Transaction, Ledger
from loan_origination_service import LoanOriginationService
from investment_management_service import InvestmentManagementService
from card_processing_service import CardProcessingService
from payment_processing_service import PaymentProcessingService


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
async def seeded_users_accounts(db_session):
    system_user = User(
        id=1,
        full_name="System Account",
        email="system@example.com",
        hashed_password="hashed",
        is_active=True,
        kyc_status="approved",
        is_admin=True,
    )
    db_session.add(system_user)
    await db_session.flush()

    admin_user = User(
        full_name="Admin User",
        email="admin@example.com",
        hashed_password="hashed",
        is_active=True,
        kyc_status="approved",
        is_admin=True,
    )
    db_session.add(admin_user)
    await db_session.flush()

    user_one = User(
        full_name="Loan Customer",
        email="loan_user@example.com",
        hashed_password="hashed",
        is_active=True,
        kyc_status="approved",
    )
    db_session.add(user_one)
    await db_session.flush()

    user_two = User(
        full_name="Investment Customer",
        email="investment_user@example.com",
        hashed_password="hashed",
        is_active=True,
        kyc_status="approved",
    )
    db_session.add(user_two)
    await db_session.flush()

    account_one = Account(
        account_number="ACC-1001",
        account_type="checking",
        balance=Decimal("1000.00"),
        currency="USD",
        owner_id=user_one.id,
        status="active",
        kyc_level="full",
    )
    account_two = Account(
        account_number="ACC-1002",
        account_type="checking",
        balance=Decimal("1000.00"),
        currency="USD",
        owner_id=user_two.id,
        status="active",
        kyc_level="full",
    )
    db_session.add_all([account_one, account_two])
    await db_session.commit()

    return {
        "system": system_user,
        "admin": admin_user,
        "user_one": user_one,
        "user_two": user_two,
        "account_one": account_one,
        "account_two": account_two,
    }


@pytest.mark.asyncio
async def test_loan_origination_and_repayment_flow(db_session, seeded_users_accounts):
    admin = seeded_users_accounts["admin"]
    user = seeded_users_accounts["user_one"]
    account = seeded_users_accounts["account_one"]

    application = await LoanOriginationService.submit_application(
        db=db_session,
        user_id=user.id,
        loan_type="personal",
        amount=Decimal("1000.00"),
        term_months=24,
        purpose="home improvement",
    )

    assert application["success"] is True
    loan_id = application["loan_id"]
    assert application["status"] == "application"

    score = await LoanOriginationService.perform_credit_decisioning(
        db=db_session,
        loan_id=loan_id,
    )
    assert score["success"] is True
    assert score["status"] == "underwriting"
    assert score["interest_rate"] > 0

    approval = await LoanOriginationService.underwrite_loan(
        db=db_session,
        loan_id=loan_id,
        admin_id=admin.id,
        approved=True,
        notes="Approved for disbursement",
    )
    assert approval["success"] is True
    assert approval["status"] == "approved"

    disbursement = await LoanOriginationService.disburse_funds(
        db=db_session,
        loan_id=loan_id,
        to_account_id=account.id,
    )
    assert disbursement["success"] is True
    assert disbursement["status"] == "active"

    updated_account = await db_session.get(Account, account.id)
    assert updated_account.balance == Decimal("2000.00")

    payment = await LoanOriginationService.record_payment(
        db=db_session,
        loan_id=loan_id,
        amount=Decimal("250.00"),
    )
    assert payment["success"] is True
    assert payment["remaining_balance"] == pytest.approx(750.00)

    updated_loan = await db_session.get(Loan, loan_id)
    assert updated_loan.status == "active"
    assert updated_loan.paid_amount == Decimal("250.00")

    updated_account = await db_session.get(Account, account.id)
    assert updated_account.balance == Decimal("1750.00")

    disbursement_entries = (await db_session.execute(
        select(Ledger).where(Ledger.reference_number == f"LOAN-{loan_id}"))
    ).scalars().all()
    assert len(disbursement_entries) == 2


@pytest.mark.asyncio
async def test_investment_portfolio_lifecycle(db_session, seeded_users_accounts):
    user = seeded_users_accounts["user_two"]
    account = seeded_users_accounts["account_two"]

    investment = await InvestmentManagementService.create_investment(
        db=db_session,
        user_id=user.id,
        investment_type="stocks",
        amount=Decimal("500.00"),
    )

    assert investment["success"] is True
    assert investment["status"] == "active"
    assert investment["amount"] == 500.0

    updated_account = await db_session.get(Account, account.id)
    assert updated_account.balance == Decimal("500.00")

    invest_id = investment["investment_id"]
    entries = (await db_session.execute(
        select(Ledger).where(Ledger.reference_number == f"INV-{invest_id}"))
    ).scalars().all()
    assert len(entries) == 2

    accrual = await InvestmentManagementService.accrue_returns(
        db=db_session,
        investment_id=invest_id,
        days_elapsed=10,
    )
    assert accrual["success"] is True
    assert accrual["new_value"] > 500.0

    summary = await InvestmentManagementService.get_portfolio_summary(
        db=db_session,
        user_id=user.id,
    )
    assert summary["success"] is True
    assert summary["total_portfolio_value"] > 500.0
    assert summary["investments_count"] == 1

    liquidation = await InvestmentManagementService.liquidate_investment(
        db=db_session,
        investment_id=invest_id,
        user_id=user.id,
    )
    assert liquidation["success"] is True
    assert liquidation["status"] == "liquidated"

    updated_account = await db_session.get(Account, account.id)
    expected_balance = Decimal("500.00") + Decimal(str(accrual["new_value"]))
    assert abs(updated_account.balance - expected_balance) < Decimal("0.01")


@pytest.mark.asyncio
async def test_investment_rebalance_adjusts_allocations(db_session, seeded_users_accounts):
    user = seeded_users_accounts["user_two"]

    first = await InvestmentManagementService.create_investment(
        db=db_session,
        user_id=user.id,
        investment_type="stocks",
        amount=Decimal("300.00"),
    )
    second = await InvestmentManagementService.create_investment(
        db=db_session,
        user_id=user.id,
        investment_type="bonds",
        amount=Decimal("200.00"),
    )

    assert first["success"] is True
    assert second["success"] is True

    result = await InvestmentManagementService.rebalance_portfolio(
        db=db_session,
        user_id=user.id,
        target_profile="moderate",
    )
    assert result["success"] is True
    assert result["total_portfolio_value"] == pytest.approx(500.00)
    assert "stocks" in result["adjustments"] or "bonds" in result["adjustments"]

    summary = await InvestmentManagementService.get_portfolio_summary(db=db_session, user_id=user.id)
    assert summary["success"] is True
    assert summary["total_portfolio_value"] == pytest.approx(500.0)
    assert summary["allocation"]["stocks"] == pytest.approx(66.67, abs=0.01)
    assert summary["allocation"]["bonds"] == pytest.approx(33.33, abs=0.01)


@pytest.mark.asyncio
async def test_card_lifecycle_and_credit_payment(db_session, seeded_users_accounts):
    admin = seeded_users_accounts["admin"]
    user = seeded_users_accounts["user_one"]
    account = seeded_users_accounts["account_one"]

    debit_card = await CardProcessingService.request_card(
        db=db_session,
        user_id=user.id,
        card_type="debit",
        billing_address="100 Main St",
    )
    assert debit_card["success"] is True
    debit_card_id = debit_card["card_id"]

    approve_debit = await CardProcessingService.approve_card_request(
        db=db_session,
        card_id=debit_card_id,
        admin_id=admin.id,
    )
    assert approve_debit["success"] is True

    activate_debit = await CardProcessingService.activate_card(
        db=db_session,
        card_id=debit_card_id,
        user_id=user.id,
    )
    assert activate_debit["success"] is True

    auth = await CardProcessingService.authorize_transaction(
        db=db_session,
        card_id=debit_card_id,
        amount=Decimal("100.00"),
        merchant="Merchant A",
        description="Debit purchase",
    )
    assert auth["success"] is True

    settle = await CardProcessingService.settle_transaction(
        db=db_session,
        card_id=debit_card_id,
        auth_code=auth["auth_code"],
        amount=Decimal("100.00"),
        merchant="Merchant A",
        description="Debit purchase",
    )
    assert settle["success"] is True

    updated_account = await db_session.get(Account, account.id)
    assert updated_account.balance == Decimal("900.00")

    credit_card = await CardProcessingService.request_card(
        db=db_session,
        user_id=user.id,
        card_type="credit",
        billing_address="100 Main St",
    )
    assert credit_card["success"] is True
    credit_card_id = credit_card["card_id"]

    approve_credit = await CardProcessingService.approve_card_request(
        db=db_session,
        card_id=credit_card_id,
        admin_id=admin.id,
    )
    assert approve_credit["success"] is True

    activate_credit = await CardProcessingService.activate_card(
        db=db_session,
        card_id=credit_card_id,
        user_id=user.id,
    )
    assert activate_credit["success"] is True

    auth_credit = await CardProcessingService.authorize_transaction(
        db=db_session,
        card_id=credit_card_id,
        amount=Decimal("150.00"),
        merchant="Merchant B",
        description="Credit purchase",
    )
    assert auth_credit["success"] is True

    settle_credit = await CardProcessingService.settle_transaction(
        db=db_session,
        card_id=credit_card_id,
        auth_code=auth_credit["auth_code"],
        amount=Decimal("150.00"),
        merchant="Merchant B",
        description="Credit purchase",
    )
    assert settle_credit["success"] is True

    credit_card_record = await db_session.get(Card, credit_card_id)
    assert credit_card_record.balance == Decimal("150.00")

    payment = await CardProcessingService.pay_credit_card_balance(
        db=db_session,
        card_id=credit_card_id,
        payment_amount=Decimal("50.00"),
    )
    assert payment["success"] is True
    assert payment["new_balance"] == Decimal("100.00")

    updated_account = await db_session.get(Account, account.id)
    assert updated_account.balance == Decimal("850.00")

    card_details = await CardProcessingService.get_card_details(
        db=db_session,
        card_id=credit_card_id,
        user_id=user.id,
    )
    assert card_details["success"] is True
    assert card_details["card_number"].startswith("**** **** ****")


@pytest.mark.asyncio
async def test_payment_processing_settlement_and_reconciliation(db_session, seeded_users_accounts):
    user_one = seeded_users_accounts["user_one"]
    user_two = seeded_users_accounts["user_two"]
    account_one = seeded_users_accounts["account_one"]
    account_two = seeded_users_accounts["account_two"]

    initiation = await PaymentProcessingService.initiate_payment(
        db=db_session,
        user_id=user_one.id,
        recipient_user_id=user_two.id,
        amount=Decimal("100.00"),
        payment_type="ach_credit",
        description="Test transfer",
    )
    assert initiation["success"] is True
    assert initiation["status"] == "pending"
    assert initiation["total_debit"] == 100.50

    transaction_id = initiation["transaction_id"]

    settlement = await PaymentProcessingService.settle_payment(
        db=db_session,
        transaction_id=transaction_id,
    )
    assert settlement["success"] is True
    assert settlement["status"] == "completed"

    updated_sender = await db_session.get(Account, account_one.id)
    updated_recipient = await db_session.get(Account, account_two.id)
    assert updated_sender.balance == Decimal("899.50")
    assert updated_recipient.balance == Decimal("1100.00")

    status = await PaymentProcessingService.get_payment_status(
        db=db_session,
        transaction_id=transaction_id,
    )
    assert status["success"] is True
    assert status["recipient_user_id"] == user_two.id

    history = await PaymentProcessingService.get_user_payment_history(
        db=db_session,
        user_id=user_one.id,
    )
    assert history["success"] is True
    assert history["count"] == 1

    reconciliation = await PaymentProcessingService.reconcile_payments(db=db_session)
    assert reconciliation["success"] is True
    assert reconciliation["reconciled"] is True
    assert reconciliation["difference"] == 0.0
