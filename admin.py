"""
Unified Admin Module
This module consolidates all admin operations using admin_service.
All operations are handled through admin_service without any JSON dependencies.
"""

from admin_service import admin_service, AdminService

# Export all admin service functionality
__all__ = ['admin_service', 'AdminService']
