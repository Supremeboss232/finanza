"""
Database models for production-ready admin settings system.
Add these models to your models.py file.
"""

from sqlalchemy import Column, String, Text, DateTime, Boolean, Integer, ForeignKey, Enum, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

# Add these imports to models.py:
# from enum import Enum as PyEnum
# from datetime import datetime


class SettingCategory(str, enum.Enum):
    """Setting categories."""
    GENERAL = "general"
    SECURITY = "security"
    EMAIL = "email"
    NOTIFICATIONS = "notifications"
    KYC = "kyc"
    PAYMENT = "payment"
    API = "api"
    MAINTENANCE = "maintenance"
    BACKUP = "backup"


# ============================================================================
# SystemSetting Model
# ============================================================================

class SystemSetting:
    """
    System-wide configuration settings.
    Replaces environment variables with database-backed settings.
    """
    __tablename__ = "system_settings"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    key = Column(String(255), unique=True, nullable=False, index=True)
    value = Column(Text, nullable=False)  # Stored as JSON string for complex values
    category = Column(String(50), default="general")
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    
    # Audit fields
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    modified_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    updated_by_admin_id = Column(String(36), ForeignKey("user.id"), nullable=True)

    # Relationship
    updated_by_admin = relationship("User", backref="settings_updated")

    def __repr__(self):
        return f"<SystemSetting {self.key}={self.value}>"


# ============================================================================
# AuditLog Model
# ============================================================================

class AuditLog:
    """
    Immutable audit trail for all settings changes.
    Required for compliance (SOX, PCI-DSS, etc).
    """
    __tablename__ = "audit_logs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Admin who made the change
    admin_id = Column(String(36), ForeignKey("user.id"), nullable=False, index=True)
    admin = relationship("User", backref="audit_logs")
    
    # Action details
    action = Column(String(255), nullable=False, index=True)  # e.g., "updated_maintenance_mode"
    resource_type = Column(String(100), nullable=False, default="system_setting")
    resource_id = Column(String(255), nullable=False, index=True)  # The setting key
    
    # Change tracking
    old_value = Column(Text, nullable=True)  # Previous value (masked if sensitive)
    new_value = Column(Text, nullable=True)  # New value (masked if sensitive)
    
    # Network info for security
    ip_address = Column(String(45), nullable=True)  # IPv4 or IPv6
    user_agent = Column(Text, nullable=True)
    
    # Metadata
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    details = Column(JSON, nullable=True)  # Extra metadata

    def __repr__(self):
        return f"<AuditLog {self.action} by {self.admin_id} at {self.timestamp}>"


# ============================================================================
# BackupTask Model
# ============================================================================

class BackupTask:
    """
    Tracks asynchronous database backup operations.
    Allows monitoring and downloading completed backups.
    """
    __tablename__ = "backup_tasks"

    id = Column(String(36), primary_key=True)  # Task UUID
    
    # Admin who triggered backup
    initiated_by_admin_id = Column(String(36), ForeignKey("user.id"), nullable=False)
    initiated_by_admin = relationship("User", backref="backup_tasks_initiated")
    
    # Status tracking
    status = Column(String(20), default="queued", index=True)  # queued, running, completed, failed
    progress_percent = Column(Integer, default=0, minimum=0, maximum=100)
    
    # Timing
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    
    # Result
    backup_file_path = Column(Text, nullable=True)  # Path to backup file
    backup_file_size = Column(Integer, nullable=True)  # Bytes
    error_message = Column(Text, nullable=True)  # If status == 'failed'
    
    # Network info
    ip_address = Column(String(45), nullable=True)

    def __repr__(self):
        return f"<BackupTask {self.id} {self.status}>"


# ============================================================================
# Add to your User model relationships
# ============================================================================

"""
In your existing User model, add these relationships:

    # Settings
    settings_updated = relationship("SystemSetting", backref="admin")
    audit_logs = relationship("AuditLog", backref="admin")
    backup_tasks_initiated = relationship("BackupTask", backref="admin")
"""


# ============================================================================
# Alembic Migration Script
# ============================================================================

MIGRATION_UP = """
-- Create system_settings table
CREATE TABLE system_settings (
    id VARCHAR(36) PRIMARY KEY,
    key VARCHAR(255) UNIQUE NOT NULL,
    value TEXT NOT NULL,
    category VARCHAR(50) DEFAULT 'general',
    description TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    modified_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    updated_by_admin_id VARCHAR(36),
    FOREIGN KEY (updated_by_admin_id) REFERENCES user(id),
    INDEX idx_key (key),
    INDEX idx_category (category)
);

-- Create audit_logs table
CREATE TABLE audit_logs (
    id VARCHAR(36) PRIMARY KEY,
    admin_id VARCHAR(36) NOT NULL,
    action VARCHAR(255) NOT NULL,
    resource_type VARCHAR(100) NOT NULL DEFAULT 'system_setting',
    resource_id VARCHAR(255) NOT NULL,
    old_value TEXT,
    new_value TEXT,
    ip_address VARCHAR(45),
    user_agent TEXT,
    timestamp DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    details JSON,
    FOREIGN KEY (admin_id) REFERENCES user(id),
    INDEX idx_admin_id (admin_id),
    INDEX idx_action (action),
    INDEX idx_resource_id (resource_id),
    INDEX idx_timestamp (timestamp)
);

-- Create backup_tasks table
CREATE TABLE backup_tasks (
    id VARCHAR(36) PRIMARY KEY,
    initiated_by_admin_id VARCHAR(36) NOT NULL,
    status VARCHAR(20) DEFAULT 'queued',
    progress_percent INT DEFAULT 0,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    started_at DATETIME,
    completed_at DATETIME,
    backup_file_path TEXT,
    backup_file_size INT,
    error_message TEXT,
    ip_address VARCHAR(45),
    FOREIGN KEY (initiated_by_admin_id) REFERENCES user(id),
    INDEX idx_status (status),
    INDEX idx_created_at (created_at)
);

-- Insert default settings
INSERT INTO system_settings (id, key, value, category, description, is_active) VALUES
('1', 'platform_name', '"Finanza"', 'general', 'System platform name', TRUE),
('2', 'maintenance_mode', 'false', 'maintenance', 'Enable/disable maintenance mode', TRUE),
('3', 'maintenance_message', '"System under maintenance"', 'maintenance', 'Message shown during maintenance', TRUE),
('4', 'allow_signups', 'true', 'general', 'Allow new user registrations', TRUE),
('5', 'require_2fa', 'true', 'security', 'Require 2FA for admin accounts', TRUE),
('6', 'session_timeout_mins', '30', 'security', 'Admin session timeout in minutes', TRUE),
('7', 'max_login_attempts', '5', 'security', 'Login attempts before lockout', TRUE),
('8', 'password_expiry_days', '90', 'security', 'Password expiry in days', TRUE),
('9', 'require_kyc_deposits', 'true', 'kyc', 'Require KYC for deposits', TRUE),
('10', 'require_kyc_transfers', 'true', 'kyc', 'Require KYC for transfers', TRUE),
('11', 'kyc_auto_approve_score', '85', 'kyc', 'Auto-approve KYC if score above this', TRUE),
('12', 'kyc_verification_duration_days', '365', 'kyc', 'KYC re-verification period', TRUE),
('13', 'enable_deposits', 'true', 'payment', 'Enable deposits', TRUE),
('14', 'enable_withdrawals', 'true', 'payment', 'Enable withdrawals', TRUE),
('15', 'min_deposit_amount', '10', 'payment', 'Minimum deposit amount', TRUE),
('16', 'max_withdrawal_amount', '100000', 'payment', 'Maximum withdrawal amount', TRUE),
('17', 'smtp_host', '""', 'email', 'SMTP host for email', TRUE),
('18', 'smtp_port', '587', 'email', 'SMTP port', TRUE),
('19', 'smtp_username', '""', 'email', 'SMTP username', TRUE),
('20', 'smtp_password', '""', 'email', 'SMTP password (encrypted)', TRUE),
('21', 'from_email', '""', 'email', 'From email address', TRUE),
('22', 'notify_new_user_registration', 'true', 'notifications', 'Notify on new user', TRUE),
('23', 'notify_kyc_submission', 'true', 'notifications', 'Notify on KYC submission', TRUE),
('24', 'notify_large_transactions', 'true', 'notifications', 'Notify on large transactions', TRUE),
('25', 'large_transaction_threshold', '10000', 'notifications', 'Large transaction threshold', TRUE),
('26', 'auto_backup_enabled', 'true', 'backup', 'Enable automatic backups', TRUE),
('27', 'backup_schedule', '"daily_2am"', 'backup', 'Backup schedule', TRUE);
"""

MIGRATION_DOWN = """
DROP TABLE IF EXISTS backup_tasks;
DROP TABLE IF EXISTS audit_logs;
DROP TABLE IF EXISTS system_settings;
"""
