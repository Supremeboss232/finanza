"""
Reporting API v1 - Legacy compatibility router
All real reporting functionality has been moved to routers/reporting_api.py
This router is maintained for backward compatibility only.
"""

from fastapi import APIRouter

reporting_v1_router = APIRouter(prefix="/api/v1/reporting-v1", tags=["reporting-v1"])

# This router is deprecated. Use /api/v1/reports endpoints instead.
# All real implementation is in routers/reporting_api.py
