# notification_templates.py
# Notification templates for various events

from typing import Dict, Any


def get_transaction_notification(transaction_type: str, amount: str, status: str) -> Dict[str, str]:
    """Transaction notification"""
    messages = {
        'email': f"Your {transaction_type} of {amount} has been {status}.",
        'sms': f"FinanzaBank: {transaction_type} {amount} {status}.",
        'push': {
            'title': 'Transaction Update',
            'body': f"{transaction_type} of {amount} {status}."
        }
    }
    return messages


def get_kyc_notification(status: str, message: str = "") -> Dict[str, str]:
    """KYC status notification"""
    status_emoji = "✓" if status.lower() == "approved" else "⏳" if status.lower() == "pending" else "✗"
    
    messages = {
        'email': f"Your KYC verification has been {status}. {message}",
        'sms': f"FinanzaBank: KYC {status}. {message}" if message else f"FinanzaBank: KYC {status}.",
        'push': {
            'title': f'KYC {status_emoji}',
            'body': f'KYC verification: {status}. {message}' if message else f'KYC verification: {status}.'
        }
    }
    return messages


def get_loan_notification(loan_id: str, status: str, amount: str = "") -> Dict[str, str]:
    """Loan application notification"""
    status_emoji = "✓" if status.lower() == "approved" else "⏳" if status.lower() == "pending" else "✗"
    
    messages = {
        'email': f"Your loan application {loan_id} has been {status}. Amount: {amount}" if amount else f"Your loan application {loan_id} has been {status}.",
        'sms': f"FinanzaBank: Loan {status}. ID: {loan_id}",
        'push': {
            'title': f'Loan {status_emoji}',
            'body': f'Loan {loan_id} {status}. {amount}' if amount else f'Loan {loan_id} {status}.'
        }
    }
    return messages


def get_security_alert(alert_type: str, description: str) -> Dict[str, str]:
    """Security alert notification"""
    messages = {
        'email': f"⚠️ Security Alert: {alert_type}\n\n{description}\n\nIf this wasn't you, secure your account immediately.",
        'sms': f"FinanzaBank: ALERT - {alert_type}. Check your account now.",
        'push': {
            'title': '⚠️ Security Alert',
            'body': f'{alert_type}'
        }
    }
    return messages


def get_payment_reminder(payment_id: str, amount: str, due_date: str) -> Dict[str, str]:
    """Payment reminder notification"""
    messages = {
        'email': f"Reminder: Payment {payment_id} of {amount} is due on {due_date}.",
        'sms': f"FinanzaBank: Payment {amount} due {due_date}. Ref: {payment_id}",
        'push': {
            'title': 'Payment Reminder',
            'body': f'Payment {amount} due {due_date}'
        }
    }
    return messages


def get_card_activation(card_type: str, last_four: str) -> Dict[str, str]:
    """Card activation notification"""
    messages = {
        'email': f"Your {card_type} card ending in {last_four} has been activated.",
        'sms': f"FinanzaBank: {card_type} card ending in {last_four} activated.",
        'push': {
            'title': 'Card Activated',
            'body': f'{card_type} card ending in {last_four}'
        }
    }
    return messages


def get_investment_notification(investment_id: str, action: str, amount: str) -> Dict[str, str]:
    """Investment update notification"""
    messages = {
        'email': f"Your investment {investment_id} has been {action}: {amount}",
        'sms': f"FinanzaBank: Investment {investment_id} {action}: {amount}",
        'push': {
            'title': f'Investment Update',
            'body': f'{investment_id} {action}: {amount}'
        }
    }
    return messages


def get_deposit_notification(deposit_id: str, amount: str, status: str) -> Dict[str, str]:
    """Deposit notification"""
    messages = {
        'email': f"Your deposit {deposit_id} of {amount} is {status}.",
        'sms': f"FinanzaBank: Deposit {deposit_id} {amount} {status}.",
        'push': {
            'title': 'Deposit Update',
            'body': f'Deposit {amount} {status}'
        }
    }
    return messages


def get_account_notification(notification_type: str, details: str) -> Dict[str, str]:
    """General account notification"""
    messages = {
        'email': f"Account Alert: {notification_type}\n\n{details}",
        'sms': f"FinanzaBank: {notification_type}",
        'push': {
            'title': 'Account Update',
            'body': notification_type
        }
    }
    return messages


def get_promotional_notification(title: str, message: str, offer: str = "") -> Dict[str, str]:
    """Promotional notification"""
    messages = {
        'email': f"{title}\n\n{message}\n\nOffer: {offer}" if offer else f"{title}\n\n{message}",
        'sms': f"FinanzaBank: {title}. {offer}" if offer else f"FinanzaBank: {title}",
        'push': {
            'title': title,
            'body': message
        }
    }
    return messages
