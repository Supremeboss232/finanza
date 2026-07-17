"""Foundational loan origination helpers for the missing lending workflow."""

from math import pow
from typing import Dict, List


class LoanOriginationService:
    """Small deterministic utility for loan quoting and amortization."""

    @staticmethod
    def generate_schedule(principal: float, annual_rate: float, term_months: int) -> Dict:
        monthly_rate = annual_rate / 12.0
        if term_months <= 0:
            return {"success": False, "error": "term_months must be positive"}

        if monthly_rate == 0:
            monthly_payment = principal / term_months
        else:
            monthly_payment = principal * (
                monthly_rate * (1 + monthly_rate) ** term_months
            ) / ((1 + monthly_rate) ** term_months - 1)

        remaining_balance = principal
        schedule: List[Dict] = []

        for payment_number in range(1, term_months + 1):
            interest = remaining_balance * monthly_rate
            principal_component = monthly_payment - interest
            remaining_balance -= principal_component
            schedule.append(
                {
                    "payment_number": payment_number,
                    "payment_amount": round(monthly_payment, 2),
                    "interest": round(interest, 2),
                    "principal": round(principal_component, 2),
                    "remaining_balance": round(max(0.0, remaining_balance), 2),
                }
            )

        return {
            "success": True,
            "monthly_payment": round(monthly_payment, 2),
            "total_payments": term_months,
            "total_interest": round(sum(item["interest"] for item in schedule), 2),
            "schedule": schedule,
        }
