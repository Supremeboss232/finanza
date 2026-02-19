"""Projects API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession

from deps import get_current_user, SessionDep
from models import User
from crud import (
    create_project,
    get_user_projects,
    get_project,
    update_project,
    delete_project,
)
from schemas import (
    Project,
    ProjectCreate,
)

router = APIRouter(
    prefix="/api/v1/projects",
    tags=["projects"],
    dependencies=[Depends(get_current_user)]
)

@router.post("", response_model=Project)
async def create_project_endpoint(
    project: ProjectCreate,
    db_session: SessionDep,
    current_user: User = Depends(get_current_user),
):
    """Create a new project."""
    return await create_project(db_session, project, current_user.id)

@router.get("", response_model=List[Project])
async def list_projects(
    skip: int = 0,
    limit: int = 100,
    db_session: SessionDep = None,
    current_user: User = Depends(get_current_user),
):
    """Get all projects for the current user."""
    return await get_user_projects(db_session, current_user.id, skip, limit)

@router.get("/{project_id}", response_model=Project)
async def get_project_detail(
    project_id: int,
    db_session: SessionDep,
    current_user: User = Depends(get_current_user),
):
    """Get a specific project."""
    project = await get_project(db_session, project_id)
    if not project or project.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return project

@router.put("/{project_id}", response_model=Project)
async def update_project_endpoint(
    project_id: int,
    project_data: dict,
    db_session: SessionDep,
    current_user: User = Depends(get_current_user),
):
    """Update a project."""
    project = await get_project(db_session, project_id)
    if not project or project.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return await update_project(db_session, project_id, project_data)

@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project_endpoint(
    project_id: int,
    db_session: SessionDep,
    current_user: User = Depends(get_current_user),
):
    """Delete a project."""
    project = await get_project(db_session, project_id)
    if not project or project.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    await delete_project(db_session, project_id)
