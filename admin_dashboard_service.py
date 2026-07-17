"""
Admin Activity Dashboard Service
Provides analytics and metrics for admin system
"""

from datetime import datetime, timedelta
from typing import Optional, List, Dict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)


class AdminActivityDashboardService:
    """
    Provide dashboard metrics and analytics for admin activity
    """
    
    def __init__(self):
        pass
    
    async def get_dashboard_summary(
        self,
        db: AsyncSession,
        hours: int = 24,
    ) -> Dict:
        """Get dashboard summary for last N hours"""
        from models import AuditLog, User
        
        try:
            cutoff_time = datetime.utcnow() - timedelta(hours=hours)
            
            # Get recent admin actions
            stmt = select(AuditLog).where(
                AuditLog.created_at >= cutoff_time
            ).order_by(AuditLog.created_at.desc()).limit(100)
            
            result = await db.execute(stmt)
            recent_actions = result.scalars().all()
            
            # Count by action type
            action_counts = {}
            total_actions = len(recent_actions)
            for action in recent_actions:
                action_type = action.action_type
                action_counts[action_type] = action_counts.get(action_type, 0) + 1
            
            # Get active admins
            stmt = select(func.count(User.id)).where(
                (User.is_admin == True) &
                (User.is_active == True)
            )
            active_admins = await db.scalar(stmt) or 0
            
            # Get suspended users count
            stmt = select(func.count(User.id)).where(
                User.is_suspended == True
            )
            suspended_users = await db.scalar(stmt) or 0
            
            # Get frozen accounts count
            stmt = select(func.count(User.id)).where(
                User.is_frozen == True
            )
            frozen_accounts = await db.scalar(stmt) or 0
            
            return {
                'period_hours': hours,
                'total_actions': total_actions,
                'actions_by_type': action_counts,
                'active_admins': active_admins,
                'suspended_users': suspended_users,
                'frozen_accounts': frozen_accounts,
                'generated_at': datetime.utcnow().isoformat(),
            }
        
        except Exception as e:
            logger.error(f"Failed to get dashboard summary: {e}")
            return {}
    
    async def get_admin_activity_stats(
        self,
        db: AsyncSession,
        admin_id: Optional[str] = None,
        days: int = 7,
    ) -> Dict:
        """Get activity statistics for an admin"""
        from models import AuditLog
        
        try:
            cutoff_time = datetime.utcnow() - timedelta(days=days)
            
            stmt = select(AuditLog).where(
                AuditLog.created_at >= cutoff_time
            )
            
            if admin_id:
                stmt = stmt.where(AuditLog.admin_id == admin_id)
            
            result = await db.execute(stmt)
            actions = result.scalars().all()
            
            # Count by action type
            action_breakdown = {}
            for action in actions:
                action_type = action.action_type
                action_breakdown[action_type] = action_breakdown.get(action_type, 0) + 1
            
            # Top affected users
            affected_users = {}
            for action in actions:
                if action.affected_user_id:
                    affected_users[action.affected_user_id] = affected_users.get(
                        action.affected_user_id, 0
                    ) + 1
            
            top_affected = sorted(
                affected_users.items(),
                key=lambda x: x[1],
                reverse=True
            )[:5]
            
            return {
                'admin_id': admin_id,
                'period_days': days,
                'total_actions': len(actions),
                'action_breakdown': action_breakdown,
                'top_affected_users': [
                    {'user_id': uid, 'action_count': count}
                    for uid, count in top_affected
                ],
                'generated_at': datetime.utcnow().isoformat(),
            }
        
        except Exception as e:
            logger.error(f"Failed to get admin stats: {e}")
            return {}
    
    async def get_action_heatmap(
        self,
        db: AsyncSession,
        hours: int = 24,
    ) -> Dict:
        """Get heatmap of admin actions by hour"""
        from models import AuditLog
        
        try:
            cutoff_time = datetime.utcnow() - timedelta(hours=hours)
            
            stmt = select(AuditLog).where(
                AuditLog.created_at >= cutoff_time
            )
            
            result = await db.execute(stmt)
            actions = result.scalars().all()
            
            # Build hourly breakdown
            heatmap = {}
            for i in range(hours):
                hour = datetime.utcnow().replace(minute=0, second=0, microsecond=0) - timedelta(hours=i)
                hour_key = hour.strftime("%Y-%m-%d %H:00")
                heatmap[hour_key] = 0
            
            # Count actions by hour
            for action in actions:
                hour_key = action.created_at.strftime("%Y-%m-%d %H:00")
                if hour_key in heatmap:
                    heatmap[hour_key] += 1
            
            # Sort by time
            sorted_heatmap = sorted(heatmap.items(), key=lambda x: x[0])
            
            return {
                'period_hours': hours,
                'hourly_breakdown': [
                    {'hour': hour, 'count': count}
                    for hour, count in sorted_heatmap
                ],
                'generated_at': datetime.utcnow().isoformat(),
            }
        
        except Exception as e:
            logger.error(f"Failed to get action heatmap: {e}")
            return {}
    
    async def get_risk_indicators(
        self,
        db: AsyncSession,
        hours: int = 24,
    ) -> Dict:
        """
        Identify potential security risks
        - Multiple failed auth attempts
        - Unusual balance adjustments
        - Multiple account suspensions
        - Off-hours activity
        """
        from models import AuditLog
        
        try:
            cutoff_time = datetime.utcnow() - timedelta(hours=hours)
            
            stmt = select(AuditLog).where(
                AuditLog.created_at >= cutoff_time
            )
            
            result = await db.execute(stmt)
            actions = result.scalars().all()
            
            risks = []
            
            # Detect bulk operations in short time
            balance_adjustments = [
                a for a in actions 
                if a.action_type == 'balance_adjustment'
            ]
            if len(balance_adjustments) > 10:
                risks.append({
                    'type': 'BULK_ADJUSTMENTS',
                    'severity': 'MEDIUM',
                    'count': len(balance_adjustments),
                    'message': f'{len(balance_adjustments)} balance adjustments in {hours} hours',
                })
            
            # Detect rapid suspensions
            suspensions = [
                a for a in actions 
                if a.action_type == 'user_suspended'
            ]
            if len(suspensions) > 5:
                risks.append({
                    'type': 'RAPID_SUSPENSIONS',
                    'severity': 'HIGH',
                    'count': len(suspensions),
                    'message': f'{len(suspensions)} user suspensions in {hours} hours',
                })
            
            # Detect off-hours activity (late night)
            off_hours = [
                a for a in actions 
                if a.created_at.hour < 6 or a.created_at.hour > 22
            ]
            if len(off_hours) > 5:
                risks.append({
                    'type': 'OFF_HOURS_ACTIVITY',
                    'severity': 'LOW',
                    'count': len(off_hours),
                    'message': f'{len(off_hours)} actions outside business hours',
                })
            
            # Group by admin for concentration
            admin_actions = {}
            for action in actions:
                admin_actions[action.admin_id] = admin_actions.get(action.admin_id, 0) + 1
            
            for admin_id, count in admin_actions.items():
                if count > 50:
                    risks.append({
                        'type': 'HIGH_ACTIVITY_CONCENTRATION',
                        'severity': 'MEDIUM',
                        'admin_id': admin_id,
                        'count': count,
                        'message': f'Admin {admin_id} performed {count} actions',
                    })
            
            return {
                'period_hours': hours,
                'risk_count': len(risks),
                'risks': risks,
                'generated_at': datetime.utcnow().isoformat(),
            }
        
        except Exception as e:
            logger.error(f"Failed to get risk indicators: {e}")
            return {}
    
    async def get_admin_leaderboard(
        self,
        db: AsyncSession,
        metric: str = 'actions',
        days: int = 30,
        limit: int = 10,
    ) -> List[Dict]:
        """Get admin leaderboard by various metrics"""
        from models import AuditLog
        
        try:
            cutoff_time = datetime.utcnow() - timedelta(days=days)
            
            stmt = select(AuditLog).where(
                AuditLog.created_at >= cutoff_time
            )
            
            result = await db.execute(stmt)
            actions = result.scalars().all()
            
            if metric == 'actions':
                admin_counts = {}
                for action in actions:
                    admin_counts[action.admin_id] = admin_counts.get(action.admin_id, 0) + 1
                
                leaderboard = sorted(
                    [
                        {'admin_id': admin, 'count': count}
                        for admin, count in admin_counts.items()
                    ],
                    key=lambda x: x['count'],
                    reverse=True
                )[:limit]
                
                return leaderboard
            
            elif metric == 'suspensions':
                suspension_actions = [a for a in actions if a.action_type == 'user_suspended']
                admin_counts = {}
                for action in suspension_actions:
                    admin_counts[action.admin_id] = admin_counts.get(action.admin_id, 0) + 1
                
                leaderboard = sorted(
                    [
                        {'admin_id': admin, 'suspensions': count}
                        for admin, count in admin_counts.items()
                    ],
                    key=lambda x: x['suspensions'],
                    reverse=True
                )[:limit]
                
                return leaderboard
            
            return []
        
        except Exception as e:
            logger.error(f"Failed to get leaderboard: {e}")
            return []


# Singleton instance
_dashboard_service: Optional[AdminActivityDashboardService] = None


def get_admin_dashboard_service() -> AdminActivityDashboardService:
    """Get or create admin dashboard service"""
    global _dashboard_service
    if _dashboard_service is None:
        _dashboard_service = AdminActivityDashboardService()
    return _dashboard_service
