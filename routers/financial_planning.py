"""Financial Planning API endpoints for budgets and goals."""

from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession

from deps import get_current_user, SessionDep, CurrentUserDep
from models import User
from crud import (
    create_budget,
    get_user_budgets,
    get_budget,
    update_budget,
    delete_budget,
    create_goal,
    get_user_goals,
    get_goal,
    update_goal,
    delete_goal,
)
from schemas import (
    Budget,
    BudgetCreate,
    Goal,
    GoalCreate,
)

router = APIRouter(
    prefix="/api/user/planning",
    tags=["financial-planning"],
    dependencies=[Depends(get_current_user)]
)

# ===== RECOMMENDATIONS =====

@router.get("/recommendations")
async def get_planning_recommendations(
    db_session: SessionDep,
    current_user: User = Depends(get_current_user),
):
    """Get financial planning recommendations for the user."""
    try:
        # TODO: Implement recommendation engine based on user's financial profile
        return {
            "recommendations": [
                {"title": "Increase Emergency Fund", "description": "Build 6 months of expenses", "priority": "high"},
                {"title": "Start Retirement Planning", "description": "Contribute to retirement accounts", "priority": "medium"}
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# ===== GOALS SUMMARY =====

@router.get("/goals/summary")
async def get_goals_summary(
    db_session: SessionDep,
    current_user: User = Depends(get_current_user),
):
    """Get summary of all user's financial goals."""
    try:
        goals = await get_user_goals(db_session, current_user.id, 0, 100)
        goals_data = []
        for goal in goals:
            progress_percent = 0
            if hasattr(goal, 'target_amount') and goal.target_amount > 0:
                current = getattr(goal, 'current_amount', 0) or 0
                progress_percent = int((current / goal.target_amount) * 100)
            
            goals_data.append({
                "id": goal.id,
                "title": getattr(goal, 'title', 'Goal'),
                "target_amount": getattr(goal, 'target_amount', 0),
                "current_amount": getattr(goal, 'current_amount', 0),
                "progress_percent": progress_percent
            })
        return {"goals": goals_data}
    except Exception as e:
        return {"goals": [], "error": str(e)}

# ===== RETIREMENT PLANNING =====

@router.get("/retirement-planning")
async def get_retirement_planning(
    retirement_age: int = 65,
    db_session: SessionDep = None,
    current_user: User = Depends(get_current_user),
):
    """Get retirement planning projections."""
    try:
        # Retirement planning projections to be implemented
        return {
            "retirement_age": retirement_age,
            "projected_retirement_balance": 0.0,
            "years_to_retirement": max(0, retirement_age - 30),
            "message": "Retirement planning projections to be calculated from actual user data"
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# ===== BUDGETS =====

@router.post("/budgets", response_model=Budget)
async def create_budget_endpoint(
    budget: BudgetCreate,
    db_session: SessionDep,
    current_user: User = Depends(get_current_user),
):
    """Create a new budget for the current user."""
    return await create_budget(db_session, budget, current_user.id)

@router.get("/budgets", response_model=List[Budget])
async def list_budgets(
    month: str = None,
    db_session: SessionDep = None,
    current_user: User = Depends(get_current_user),
):
    """Get all budgets for the current user, optionally filtered by month."""
    return await get_user_budgets(db_session, current_user.id, month)

@router.get("/budgets/{budget_id}", response_model=Budget)
async def get_budget_detail(
    budget_id: int,
    db_session: SessionDep,
    current_user: User = Depends(get_current_user),
):
    """Get a specific budget."""
    budget = await get_budget(db_session, budget_id)
    if not budget or budget.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Budget not found")
    return budget

@router.put("/budgets/{budget_id}", response_model=Budget)
async def update_budget_endpoint(
    budget_id: int,
    budget_data: dict,
    db_session: SessionDep,
    current_user: User = Depends(get_current_user),
):
    """Update a budget."""
    budget = await get_budget(db_session, budget_id)
    if not budget or budget.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Budget not found")
    return await update_budget(db_session, budget_id, budget_data)

@router.delete("/budgets/{budget_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_budget_endpoint(
    budget_id: int,
    db_session: SessionDep,
    current_user: User = Depends(get_current_user),
):
    """Delete a budget."""
    budget = await get_budget(db_session, budget_id)
    if not budget or budget.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Budget not found")
    await delete_budget(db_session, budget_id)

# ===== GOALS =====

@router.post("/goals", response_model=Goal)
async def create_goal_endpoint(
    goal: GoalCreate,
    db_session: SessionDep,
    current_user: User = Depends(get_current_user),
):
    """Create a new financial goal."""
    return await create_goal(db_session, goal, current_user.id)

@router.get("/goals", response_model=List[Goal])
async def list_goals(
    skip: int = 0,
    limit: int = 100,
    db_session: SessionDep = None,
    current_user: User = Depends(get_current_user),
):
    """Get all financial goals for the current user."""
    return await get_user_goals(db_session, current_user.id, skip, limit)

@router.get("/goals/{goal_id}", response_model=Goal)
async def get_goal_detail(
    goal_id: int,
    db_session: SessionDep,
    current_user: User = Depends(get_current_user),
):
    """Get a specific financial goal."""
    goal = await get_goal(db_session, goal_id)
    if not goal or goal.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Goal not found")
    return goal

@router.put("/goals/{goal_id}", response_model=Goal)
async def update_goal_endpoint(
    goal_id: int,
    goal_data: dict,
    db_session: SessionDep,
    current_user: User = Depends(get_current_user),
):
    """Update a financial goal."""
    goal = await get_goal(db_session, goal_id)
    if not goal or goal.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Goal not found")
    return await update_goal(db_session, goal_id, goal_data)

@router.delete("/goals/{goal_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_goal_endpoint(
    goal_id: int,
    db_session: SessionDep,
    current_user: User = Depends(get_current_user),
):
    """Delete a financial goal."""
    goal = await get_goal(db_session, goal_id)
    if not goal or goal.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Goal not found")
    await delete_goal(db_session, goal_id)
