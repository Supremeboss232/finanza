from services.loan_origination_service import LoanOriginationService
from services.investment_portfolio_service import InvestmentPortfolioService
from services.card_processing_service import CardProcessingService


def test_loan_schedule_generation_is_stable():
    schedule = LoanOriginationService.generate_schedule(1000, 0.12, 12)

    assert schedule["success"] is True
    assert schedule["monthly_payment"] > 0
    assert len(schedule["schedule"]) == 12


def test_investment_portfolio_value_is_calculated():
    result = InvestmentPortfolioService.calculate_portfolio_value(
        [
            {"symbol": "AAA", "shares": 2, "price": 50},
            {"symbol": "BBB", "shares": 3, "price": 25},
        ]
    )

    assert result["total_value"] == 175.0
    assert result["positions"] == 2


def test_card_validation_accepts_valid_example():
    assert CardProcessingService.validate_card_number("4111111111111111") is True
    assert CardProcessingService.validate_card_number("4111") is False
