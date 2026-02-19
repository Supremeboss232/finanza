# crud.py
# Contains database operations (Create, Read, Update, Delete) for all models.

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from . import models, schemas
from .auth_utils import get_password_hash

async def get_user(db: AsyncSession, user_id: int):
    result = await db.execute(select(models.User).filter(models.User.id == user_id))
    return result.scalar_one_or_none()

async def get_user_by_email(db: AsyncSession, email: str):
    result = await db.execute(select(models.User).filter(models.User.email == email))
    return result.scalar_one_or_none()

async def get_user_by_account_number(db: AsyncSession, account_number: str):
    result = await db.execute(select(models.User).filter(models.User.account_number == account_number))
    return result.scalar_one_or_none()

async def get_user_by_username(db: AsyncSession, username: str):
    # Assuming username is the email for login purposes
    result = await db.execute(select(models.User).filter(models.User.email == username))
    return result.scalar_one_or_none()

async def get_users(db: AsyncSession, skip: int = 0, limit: int = 100):
    result = await db.execute(select(models.User).offset(skip).limit(limit))
    return result.scalars().all()

async def create_user(db: AsyncSession, user: schemas.UserCreate):
    """
    ATOMIC OPERATION: Create User with Primary Account
    
    ⚠️ CORE RULE (NON-NEGOTIABLE):
    Every user must have BOTH a User ID and an Account ID.
    Not "optional", not "generated later", not "after KYC".
    
    This function enforces: User creation = User + Account binding
    If either fails → entire operation rolls back.
    """
    hashed_password = get_password_hash(user.password)
    db_user = models.User(
        email=user.email,
        hashed_password=hashed_password,
        full_name=user.full_name,
        account_number=getattr(user, 'account_number', None),
        kyc_status='not_started'  # Explicit: User can't transact until KYC approved
    )
    db.add(db_user)
    await db.flush()  # Get the user ID WITHOUT committing yet
    
    # Generate primary account for this user
    # Account number format: ACC + timestamp + user_id for uniqueness
    import time
    primary_account_number = f"ACC{db_user.id}_{int(time.time() * 1000000) % 1000000}"
    
    db_account = models.Account(
        owner_id=db_user.id,  # Link account to user
        account_number=primary_account_number,
        account_type='primary',  # Primary checking account
        balance=0.0,
        currency='USD'
    )
    db.add(db_account)
    await db.flush()  # Verify account created
    
    # Store primary account number on user for quick reference
    if not db_user.account_number:
        db_user.account_number = primary_account_number
    
    # NOW commit both together - atomic operation
    await db.commit()
    await db.refresh(db_user)
    return db_user

async def update_user(db: AsyncSession, user_id: int, user: schemas.UserUpdate):
    db_user = await get_user(db, user_id)
    if db_user:
        for var, value in vars(user).items():
            if value is not None:
                setattr(db_user, var, value)
        db.add(db_user)
        await db.commit()
        await db.refresh(db_user)
    return db_user

async def delete_user(db: AsyncSession, user_id: int):
    db_user = await get_user(db, user_id)
    if db_user:
        await db.delete(db_user)
        await db.commit()
    return db_user

# Generic CRUD for other models

async def get_transactions(db: AsyncSession, skip: int = 0, limit: int = 100):
    result = await db.execute(select(models.Transaction).offset(skip).limit(limit))
    return result.scalars().all()

async def get_user_transactions(db: AsyncSession, user_id: int, skip: int = 0, limit: int = 100):
    result = await db.execute(select(models.Transaction).filter(models.Transaction.user_id == user_id).offset(skip).limit(limit))
    return result.scalars().all()

async def create_user_transaction(db: AsyncSession, transaction: schemas.TransactionCreate, user_id: int):
    db_transaction = models.Transaction(**transaction.model_dump(), user_id=user_id)
    db.add(db_transaction)
    await db.commit()
    await db.refresh(db_transaction)
    return db_transaction

async def get_transaction(db: AsyncSession, transaction_id: int):
    result = await db.execute(select(models.Transaction).filter(models.Transaction.id == transaction_id))
    return result.scalar_one_or_none()

async def get_form_submissions(db: AsyncSession, skip: int = 0, limit: int = 100):
    result = await db.execute(select(models.FormSubmission).offset(skip).limit(limit))
    return result.scalars().all()

async def create_form_submission(db: AsyncSession, submission: schemas.FormSubmissionCreate, user_id: int | None = None):
    db_submission = models.FormSubmission(**submission.model_dump(), user_id=user_id)
    db.add(db_submission)
    await db.commit()
    await db.refresh(db_submission)
    return db_submission

async def get_form_submission(db: AsyncSession, submission_id: int):
    result = await db.execute(select(models.FormSubmission).filter(models.FormSubmission.id == submission_id))
    return result.scalar_one_or_none()

# Placeholder CRUD for other routers to prevent import errors

async def get_user_deposits(db: AsyncSession, user_id: int, skip: int = 0, limit: int = 100):
    result = await db.execute(select(models.Deposit).filter(models.Deposit.user_id == user_id).offset(skip).limit(limit))
    return result.scalars().all()

async def create_user_deposit(db: AsyncSession, deposit: schemas.DepositCreate, user_id: int):
    db_deposit = models.Deposit(**deposit.model_dump(), user_id=user_id)
    db.add(db_deposit)
    await db.commit()
    await db.refresh(db_deposit)
    return db_deposit

async def get_deposit(db: AsyncSession, deposit_id: int):
    result = await db.execute(select(models.Deposit).filter(models.Deposit.id == deposit_id))
    return result.scalar_one_or_none()

async def get_user_loans(db: AsyncSession, user_id: int, skip: int = 0, limit: int = 100):
    result = await db.execute(select(models.Loan).filter(models.Loan.user_id == user_id).offset(skip).limit(limit))
    return result.scalars().all()

async def create_user_loan(db: AsyncSession, loan: schemas.LoanCreate, user_id: int):
    db_loan = models.Loan(**loan.model_dump(), user_id=user_id)
    db.add(db_loan)
    await db.commit()
    await db.refresh(db_loan)
    return db_loan

async def get_loan(db: AsyncSession, loan_id: int):
    result = await db.execute(select(models.Loan).filter(models.Loan.id == loan_id))
    return result.scalar_one_or_none()

async def get_user_investments(db: AsyncSession, user_id: int, skip: int = 0, limit: int = 100):
    result = await db.execute(select(models.Investment).filter(models.Investment.user_id == user_id).offset(skip).limit(limit))
    return result.scalars().all()

async def create_user_investment(db: AsyncSession, investment: schemas.InvestmentCreate, user_id: int):
    db_investment = models.Investment(**investment.model_dump(), user_id=user_id)
    db.add(db_investment)
    await db.commit()
    await db.refresh(db_investment)
    return db_investment

async def get_investment(db: AsyncSession, investment_id: int):
    result = await db.execute(select(models.Investment).filter(models.Investment.id == investment_id))
    return result.scalar_one_or_none()

async def get_user_cards(db: AsyncSession, user_id: int, skip: int = 0, limit: int = 100):
    result = await db.execute(select(models.Card).filter(models.Card.user_id == user_id).offset(skip).limit(limit))
    return result.scalars().all()

async def create_user_card(db: AsyncSession, card: schemas.CardCreate, user_id: int):
    db_card = models.Card(**card.model_dump(), user_id=user_id)
    db.add(db_card)
    await db.commit()
    await db.refresh(db_card)
    return db_card

async def get_card(db: AsyncSession, card_id: int):
    result = await db.execute(select(models.Card).filter(models.Card.id == card_id))
    return result.scalar_one_or_none()

async def authenticate_user(db: AsyncSession, email: str, password: str) -> models.User | None:
    """
    Authenticates a user.

    1. Fetches the user by email.
    2. Verifies the provided password against the stored hash.
    3. Returns the user object on success, otherwise None.
    """
    user = await get_user_by_email(db, email=email)
    if not user:
        return None
    from .auth_utils import verify_password
    if not verify_password(password, user.hashed_password):
        return None
    return user
