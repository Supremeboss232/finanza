from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Optional
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from deps import get_current_admin_user, get_async_session as get_db_session
from models import FormSubmission, FormSubmissionCreate, User
from crud import get_form_submission, create_form_submission

forms_router = APIRouter(prefix="/forms", tags=["forms"])


@forms_router.post("/", response_model=FormSubmission, status_code=status.HTTP_201_CREATED)
async def submit_form(
    form_submission: FormSubmissionCreate,
    db_session: AsyncSession = Depends(get_db_session),
    current_user: Optional[User] = Depends(get_current_admin_user)  # use admin user
):
    """
    Submit a new form. Optional admin user for authentication.
    """
    user_id = current_user.id if current_user else None
    db_submission = await create_form_submission(
        db_session=db_session,
        submission=form_submission,
        user_id=user_id
    )
    # Convert ORM object to Pydantic model
    return FormSubmission.from_orm(db_submission)


@forms_router.get("/", response_model=List[FormSubmission])
async def read_admin_form_submissions(
    db_session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_admin_user),
    skip: int = 0,
    limit: int = 100
):
    """
    Get all form submissions accessible to the admin user.
    """
    result = await db_session.execute(
        select(FormSubmission).offset(skip).limit(limit)
    )
    submissions = result.scalars().all()
    return [FormSubmission.from_orm(sub) for sub in submissions]


@forms_router.get("/{submission_id}", response_model=FormSubmission)
async def read_form_submission_by_id(
    submission_id: int,
    db_session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_admin_user)
):
    """
    Get a single form submission by ID. Only accessible to the admin user.
    """
    db_submission = await get_form_submission(db_session, submission_id)
    if not db_submission:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Form submission not found")
    return FormSubmission.from_orm(db_submission)
