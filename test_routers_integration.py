import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from fastapi import FastAPI
from models import Base, User, Account
import deps as deps_mod

# Create a minimal test app that only mounts the routers we need for fast, focused tests
app = FastAPI()
from routers.loans import loans_router
app.include_router(loans_router, prefix="/api/v1")


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
async def seeded_db(db_session: AsyncSession):
    # Create a system/admin and regular user
    system = User(id=1, full_name="System", email="system@example.com", hashed_password="x", is_admin=True, is_active=True, kyc_status="approved")
    admin = User(full_name="Admin", email="admin@example.com", hashed_password="x", is_admin=True, is_active=True, kyc_status="approved")
    user = User(full_name="User", email="user@example.com", hashed_password="x", is_admin=False, is_active=True, kyc_status="approved")

    db_session.add_all([system, admin, user])
    await db_session.flush()

    acct1 = Account(account_number="ACC-INT-1", owner_id=user.id, account_type="checking", balance=1000.0, currency="USD")
    acct2 = Account(account_number="ACC-INT-2", owner_id=admin.id, account_type="checking", balance=1000.0, currency="USD")
    db_session.add_all([acct1, acct2])
    await db_session.commit()

    return {
        "session": db_session,
        "system": system,
        "admin": admin,
        "user": user,
        "acct_user": acct1,
        "acct_admin": acct2,
    }


@pytest.mark.asyncio
async def test_loans_router_apply_and_admin_flow(seeded_db):
    session: AsyncSession = seeded_db["session"]

    async def override_get_db():
        yield session

    async def override_get_current_user():
        # Return regular user for non-admin actions
        return seeded_db["user"]

    # Call the router handler functions directly (simulate endpoint invocation)
    from routers.loans import apply_for_loan, run_credit_decisioning, underwrite_loan

    # Submit loan application as regular user
    result = await apply_for_loan(
        loan_type="personal",
        amount=500.0,
        term_months=12,
        purpose="testing",
        current_user=seeded_db["user"],
        db_session=session,
    )
    assert result["success"] is True
    loan_id = result["loan_id"]

    # Run credit decisioning as admin
    credit_result = await run_credit_decisioning(
        loan_id=loan_id,
        current_user=seeded_db["admin"],
        db_session=session,
    )
    assert credit_result["success"] is True

    # Underwrite
    underwrite_result = await underwrite_loan(
        loan_id=loan_id,
        approved=True,
        notes="OK",
        current_user=seeded_db["admin"],
        db_session=session,
    )
    assert underwrite_result["success"] is True

    # Clear overrides (no-op here)
    app.dependency_overrides.clear()
