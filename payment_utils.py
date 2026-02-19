# payment_utils.py
# Functions to process payments, handle transactions, and integrate payment gateways.

from decimal import Decimal
from typing import Optional

class PaymentGateway:
    def __init__(self, api_key: str, secret_key: str):
        self.api_key = api_key
        self.secret_key = secret_key
        # Initialize connection to payment gateway

    async def process_payment(self, amount: Decimal, currency: str, card_details: dict, description: str) -> dict:
        """
        Simulates processing a payment through a payment gateway.
        In a real-world scenario, this would involve API calls to the payment provider.
        """
        print(f"Processing payment of {amount} {currency} for {description}...")
        # Placeholder for actual payment gateway integration logic
        # This would typically involve sending card_details to the gateway
        # and handling their API response.
        if amount > 0 and card_details.get("number") and card_details.get("expiry"):
            # Simulate a successful transaction
            transaction_id = "txn_" + str(abs(hash(description))) # Generate a unique transaction ID
            return {
                "status": "success",
                "transaction_id": transaction_id,
                "amount": str(amount),
                "currency": currency,
                "message": "Payment processed successfully."
            }
        else:
            return {
                "status": "failed",
                "transaction_id": None,
                "amount": str(amount),
                "currency": currency,
                "message": "Payment processing failed. Invalid details."
            }

    async def refund_payment(self, transaction_id: str, amount: Optional[Decimal] = None) -> dict:
        """
        Simulates refunding a payment.
        """
        print(f"Refunding transaction {transaction_id} for amount {amount or 'full'}...")
        # Placeholder for actual refund logic via payment gateway API
        return {
            "status": "success",
            "refund_id": "ref_" + str(abs(hash(transaction_id))),
            "message": "Refund processed successfully."
        }

# Example usage (would be called from a service or route)
async def handle_deposit(user_id: int, account_id: int, amount: Decimal, currency: str, card_details: dict) -> dict:
    # Initialize payment gateway (API keys would come from config)
    # For demonstration, using dummy keys
    gateway = PaymentGateway("dummy_api_key", "dummy_secret_key")
    description = f"Deposit for user {user_id} into account {account_id}"

    payment_result = await gateway.process_payment(amount, currency, card_details, description)

    if payment_result["status"] == "success":
        # Update user's account balance, log transaction in DB (via crud operations)
        print(f"Deposit successful: {payment_result}")
        return {"message": "Deposit successful", "transaction": payment_result}
    else:
        print(f"Deposit failed: {payment_result}")
        return {"message": "Deposit failed", "error": payment_result["message"]}

