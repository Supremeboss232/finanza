# email_templates.py
# Email templates for transactional emails

from typing import Dict, Any


def get_welcome_email_template(user_name: str, verification_link: str) -> Dict[str, str]:
    """Welcome email template"""
    html_body = f"""
    <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; text-align: center; border-radius: 5px; }}
                .content {{ padding: 20px; background: #f9f9f9; }}
                .button {{ display: inline-block; padding: 12px 24px; background: #667eea; color: white; text-decoration: none; border-radius: 5px; margin: 20px 0; }}
                .footer {{ text-align: center; font-size: 12px; color: #666; padding-top: 20px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Welcome to Finanza Bank</h1>
                </div>
                <div class="content">
                    <p>Hello {user_name},</p>
                    <p>Thank you for signing up with Finanza Bank! We're excited to have you on board.</p>
                    <p>To complete your registration, please verify your email address by clicking the button below:</p>
                    <a href="{verification_link}" class="button">Verify Email Address</a>
                    <p>If you didn't create this account, please ignore this email.</p>
                    <p>Best regards,<br>The Finanza Bank Team</p>
                </div>
                <div class="footer">
                    <p>&copy; 2025 Finanza Bank. All rights reserved.</p>
                </div>
            </div>
        </body>
    </html>
    """
    
    text_body = f"""
Welcome to Finanza Bank

Hello {user_name},

Thank you for signing up with Finanza Bank! We're excited to have you on board.

To complete your registration, please verify your email address:
{verification_link}

If you didn't create this account, please ignore this email.

Best regards,
The Finanza Bank Team
    """
    
    return {
        'html': html_body,
        'text': text_body
    }


def get_password_reset_email_template(user_name: str, reset_link: str, expiry_hours: int = 24) -> Dict[str, str]:
    """Password reset email template"""
    html_body = f"""
    <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: #ff6b6b; color: white; padding: 20px; text-align: center; border-radius: 5px; }}
                .content {{ padding: 20px; background: #f9f9f9; }}
                .button {{ display: inline-block; padding: 12px 24px; background: #ff6b6b; color: white; text-decoration: none; border-radius: 5px; margin: 20px 0; }}
                .warning {{ background: #fff3cd; border-left: 4px solid #ffc107; padding: 10px; margin: 20px 0; }}
                .footer {{ text-align: center; font-size: 12px; color: #666; padding-top: 20px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Password Reset Request</h1>
                </div>
                <div class="content">
                    <p>Hello {user_name},</p>
                    <p>We received a request to reset the password for your Finanza Bank account.</p>
                    <p>Click the button below to reset your password. This link will expire in {expiry_hours} hours:</p>
                    <a href="{reset_link}" class="button">Reset Password</a>
                    <div class="warning">
                        <strong>Security Notice:</strong> If you didn't request a password reset, please ignore this email and your password will remain unchanged.
                    </div>
                    <p>If the button above doesn't work, copy and paste this link into your browser:<br>{reset_link}</p>
                    <p>Best regards,<br>The Finanza Bank Security Team</p>
                </div>
                <div class="footer">
                    <p>&copy; 2025 Finanza Bank. All rights reserved.</p>
                </div>
            </div>
        </body>
    </html>
    """
    
    text_body = f"""
Password Reset Request

Hello {user_name},

We received a request to reset the password for your Finanza Bank account.

Click the link below to reset your password. This link will expire in {expiry_hours} hours:
{reset_link}

SECURITY NOTICE: If you didn't request a password reset, please ignore this email and your password will remain unchanged.

Best regards,
The Finanza Bank Security Team
    """
    
    return {
        'html': html_body,
        'text': text_body
    }


def get_kyc_submission_template(user_name: str, status: str, message: str = "") -> Dict[str, str]:
    """KYC submission status email template"""
    status_color = "#28a745" if status.lower() == "approved" else "#ffc107" if status.lower() == "pending" else "#dc3545"
    
    html_body = f"""
    <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: {status_color}; color: white; padding: 20px; text-align: center; border-radius: 5px; }}
                .content {{ padding: 20px; background: #f9f9f9; }}
                .status-badge {{ display: inline-block; padding: 8px 16px; background: {status_color}; color: white; border-radius: 20px; font-weight: bold; }}
                .footer {{ text-align: center; font-size: 12px; color: #666; padding-top: 20px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>KYC Verification Update</h1>
                </div>
                <div class="content">
                    <p>Hello {user_name},</p>
                    <p>Your KYC (Know Your Customer) submission status has been updated:</p>
                    <p><span class="status-badge">{status.upper()}</span></p>
                    {f'<p>{message}</p>' if message else ''}
                    <p>You can check the detailed status in your account dashboard.</p>
                    <p>If you have any questions, please contact our support team.</p>
                    <p>Best regards,<br>The Finanza Bank Compliance Team</p>
                </div>
                <div class="footer">
                    <p>&copy; 2025 Finanza Bank. All rights reserved.</p>
                </div>
            </div>
        </body>
    </html>
    """
    
    text_body = f"""
KYC Verification Update

Hello {user_name},

Your KYC (Know Your Customer) submission status has been updated:

Status: {status.upper()}

{message}

You can check the detailed status in your account dashboard.

If you have any questions, please contact our support team.

Best regards,
The Finanza Bank Compliance Team
    """
    
    return {
        'html': html_body,
        'text': text_body
    }


def get_transaction_confirmation_template(user_name: str, transaction_type: str, amount: str, recipient: str = "", reference_id: str = "") -> Dict[str, str]:
    """Transaction confirmation email template"""
    html_body = f"""
    <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: #667eea; color: white; padding: 20px; text-align: center; border-radius: 5px; }}
                .content {{ padding: 20px; background: #f9f9f9; }}
                .transaction-details {{ background: white; border: 1px solid #ddd; padding: 15px; border-radius: 5px; margin: 20px 0; }}
                .detail-row {{ display: flex; justify-content: space-between; padding: 8px 0; border-bottom: 1px solid #eee; }}
                .detail-row:last-child {{ border-bottom: none; }}
                .detail-label {{ font-weight: bold; color: #666; }}
                .detail-value {{ color: #333; }}
                .footer {{ text-align: center; font-size: 12px; color: #666; padding-top: 20px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Transaction Confirmation</h1>
                </div>
                <div class="content">
                    <p>Hello {user_name},</p>
                    <p>Your {transaction_type.lower()} has been processed successfully.</p>
                    <div class="transaction-details">
                        <div class="detail-row">
                            <span class="detail-label">Transaction Type:</span>
                            <span class="detail-value">{transaction_type}</span>
                        </div>
                        <div class="detail-row">
                            <span class="detail-label">Amount:</span>
                            <span class="detail-value">{amount}</span>
                        </div>
                        {f'<div class="detail-row"><span class="detail-label">Recipient:</span><span class="detail-value">{recipient}</span></div>' if recipient else ''}
                        {f'<div class="detail-row"><span class="detail-label">Reference ID:</span><span class="detail-value">{reference_id}</span></div>' if reference_id else ''}
                    </div>
                    <p>For your security, we recommend reviewing this transaction in your account dashboard.</p>
                    <p>Best regards,<br>The Finanza Bank Team</p>
                </div>
                <div class="footer">
                    <p>&copy; 2025 Finanza Bank. All rights reserved.</p>
                </div>
            </div>
        </body>
    </html>
    """
    
    text_body = f"""
Transaction Confirmation

Hello {user_name},

Your {transaction_type.lower()} has been processed successfully.

Transaction Details:
- Type: {transaction_type}
- Amount: {amount}
{f'- Recipient: {recipient}' if recipient else ''}
{f'- Reference ID: {reference_id}' if reference_id else ''}

For your security, we recommend reviewing this transaction in your account dashboard.

Best regards,
The Finanza Bank Team
    """
    
    return {
        'html': html_body,
        'text': text_body
    }


def get_account_alert_template(user_name: str, alert_type: str, alert_message: str) -> Dict[str, str]:
    """Account alert email template"""
    html_body = f"""
    <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: #ff6b6b; color: white; padding: 20px; text-align: center; border-radius: 5px; }}
                .content {{ padding: 20px; background: #f9f9f9; }}
                .alert-box {{ background: #fff3cd; border-left: 4px solid #ffc107; padding: 15px; margin: 20px 0; border-radius: 5px; }}
                .footer {{ text-align: center; font-size: 12px; color: #666; padding-top: 20px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Account Alert</h1>
                </div>
                <div class="content">
                    <p>Hello {user_name},</p>
                    <div class="alert-box">
                        <strong>{alert_type}</strong><br>
                        {alert_message}
                    </div>
                    <p>If you did not authorize this activity, please contact our support team immediately.</p>
                    <p>Best regards,<br>The Finanza Bank Security Team</p>
                </div>
                <div class="footer">
                    <p>&copy; 2025 Finanza Bank. All rights reserved.</p>
                </div>
            </div>
        </body>
    </html>
    """
    
    text_body = f"""
Account Alert

Hello {user_name},

{alert_type}:
{alert_message}

If you did not authorize this activity, please contact our support team immediately.

Best regards,
The Finanza Bank Security Team
    """
    
    return {
        'html': html_body,
        'text': text_body
    }


def get_loan_approval_template(user_name: str, loan_id: str, loan_amount: str, rate: str, term_months: int) -> Dict[str, str]:
    """Loan approval email template"""
    html_body = f"""
    <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: #28a745; color: white; padding: 20px; text-align: center; border-radius: 5px; }}
                .content {{ padding: 20px; background: #f9f9f9; }}
                .loan-details {{ background: white; border: 1px solid #ddd; padding: 15px; border-radius: 5px; margin: 20px 0; }}
                .detail-row {{ display: flex; justify-content: space-between; padding: 8px 0; border-bottom: 1px solid #eee; }}
                .detail-row:last-child {{ border-bottom: none; }}
                .detail-label {{ font-weight: bold; color: #666; }}
                .detail-value {{ color: #333; }}
                .button {{ display: inline-block; padding: 12px 24px; background: #28a745; color: white; text-decoration: none; border-radius: 5px; margin: 20px 0; }}
                .footer {{ text-align: center; font-size: 12px; color: #666; padding-top: 20px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Loan Approved!</h1>
                </div>
                <div class="content">
                    <p>Hello {user_name},</p>
                    <p>Great news! Your loan application has been approved.</p>
                    <div class="loan-details">
                        <div class="detail-row">
                            <span class="detail-label">Loan ID:</span>
                            <span class="detail-value">{loan_id}</span>
                        </div>
                        <div class="detail-row">
                            <span class="detail-label">Loan Amount:</span>
                            <span class="detail-value">{loan_amount}</span>
                        </div>
                        <div class="detail-row">
                            <span class="detail-label">Interest Rate:</span>
                            <span class="detail-value">{rate}</span>
                        </div>
                        <div class="detail-row">
                            <span class="detail-label">Term:</span>
                            <span class="detail-value">{term_months} months</span>
                        </div>
                    </div>
                    <p>You can now access your loan details and manage your payments in your account dashboard.</p>
                    <a href="#" class="button">View Loan Details</a>
                    <p>Best regards,<br>The Finanza Bank Team</p>
                </div>
                <div class="footer">
                    <p>&copy; 2025 Finanza Bank. All rights reserved.</p>
                </div>
            </div>
        </body>
    </html>
    """
    
    text_body = f"""
Loan Approved!

Hello {user_name},

Great news! Your loan application has been approved.

Loan Details:
- Loan ID: {loan_id}
- Loan Amount: {loan_amount}
- Interest Rate: {rate}
- Term: {term_months} months

You can now access your loan details and manage your payments in your account dashboard.

Best regards,
The Finanza Bank Team
    """
    
    return {
        'html': html_body,
        'text': text_body
    }
