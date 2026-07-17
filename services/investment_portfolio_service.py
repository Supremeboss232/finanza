"""Foundational portfolio analytics for incomplete investment workflows."""

from typing import Dict, List


class InvestmentPortfolioService:
    """Simple portfolio valuation and risk summary for local development."""

    @staticmethod
    def calculate_portfolio_value(positions: List[Dict]) -> Dict:
        total_value = 0.0
        for position in positions:
            shares = float(position.get("shares", 0) or 0)
            price = float(position.get("price", 0) or 0)
            total_value += shares * price

        return {
            "success": True,
            "total_value": round(total_value, 2),
            "positions": len(positions),
            "risk_level": "medium" if total_value >= 100 else "low",
        }
