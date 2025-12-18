"""
Deterministic math utilities for mortgage calculations.
All calculations are performed here - LLM never does math.
"""

from typing import Dict, Tuple
import math


def calculate_emi(principal: float, annual_interest_rate: float, tenure_years: int) -> float:
    """
    Calculate EMI using the standard formula:
    M = P * r * (1+r)^n / ((1+r)^n - 1)
    
    Args:
        principal: Loan amount (principal)
        annual_interest_rate: Annual interest rate as percentage (e.g., 4.5 for 4.5%)
        tenure_years: Loan tenure in years
    
    Returns:
        Monthly EMI amount
    """
    if principal <= 0:
        raise ValueError("Principal must be greater than 0")
    if annual_interest_rate < 0:
        raise ValueError("Interest rate cannot be negative")
    if tenure_years <= 0:
        raise ValueError("Tenure must be greater than 0")
    
    # Convert annual rate to monthly rate (as decimal)
    monthly_rate = (annual_interest_rate / 100) / 12
    
    # Number of monthly payments
    num_payments = tenure_years * 12
    
    if monthly_rate == 0:
        # If interest rate is 0, EMI is simply principal divided by number of payments
        return principal / num_payments
    
    # EMI formula
    emi = principal * monthly_rate * ((1 + monthly_rate) ** num_payments) / (((1 + monthly_rate) ** num_payments) - 1)
    
    return round(emi, 2)


def calculate_ltv(property_price: float) -> Dict[str, float]:
    """
    Calculate Loan-to-Value ratio details.
    
    Args:
        property_price: Total property price
    
    Returns:
        Dictionary with max_loan and required_down_payment
    """
    if property_price <= 0:
        raise ValueError("Property price must be greater than 0")
    
    max_loan = property_price * 0.8  # 80% LTV
    required_down_payment = property_price * 0.2  # 20% down payment
    
    return {
        "max_loan": round(max_loan, 2),
        "required_down_payment": round(required_down_payment, 2),
        "ltv_percentage": 80.0
    }


def calculate_upfront_costs(property_price: float) -> Dict[str, float]:
    """
    Calculate upfront costs for property purchase.
    Breakdown: 4% transfer + 2% agency + 1% misc = 7% total
    
    Args:
        property_price: Total property price
    
    Returns:
        Dictionary with breakdown and total upfront costs
    """
    if property_price <= 0:
        raise ValueError("Property price must be greater than 0")
    
    transfer_fee = property_price * 0.04  # 4%
    agency_fee = property_price * 0.02   # 2%
    misc_fee = property_price * 0.01      # 1%
    total_upfront = property_price * 0.07  # 7% total
    
    return {
        "transfer_fee": round(transfer_fee, 2),
        "agency_fee": round(agency_fee, 2),
        "misc_fee": round(misc_fee, 2),
        "total_upfront_costs": round(total_upfront, 2)
    }


def rent_vs_buy(monthly_rent: float, monthly_mortgage: float, maintenance_fee: float = 0) -> Dict[str, any]:
    """
    Compare renting vs buying costs.
    
    Args:
        monthly_rent: Monthly rental cost
        monthly_mortgage: Monthly mortgage payment (EMI)
        maintenance_fee: Monthly maintenance fee (optional)
    
    Returns:
        Dictionary with comparison results and recommendation
    """
    if monthly_rent < 0 or monthly_mortgage < 0 or maintenance_fee < 0:
        raise ValueError("All costs must be non-negative")
    
    total_monthly_buying = monthly_mortgage + maintenance_fee
    monthly_difference = total_monthly_buying - monthly_rent
    
    # Calculate annual costs
    annual_rent = monthly_rent * 12
    annual_buying = total_monthly_buying * 12
    
    # Determine recommendation
    if monthly_rent < total_monthly_buying:
        recommendation = "rent"
        savings_per_month = monthly_rent - total_monthly_buying
    else:
        recommendation = "buy"
        savings_per_month = total_monthly_buying - monthly_rent
    
    return {
        "monthly_rent": round(monthly_rent, 2),
        "monthly_mortgage": round(monthly_mortgage, 2),
        "maintenance_fee": round(maintenance_fee, 2),
        "total_monthly_buying": round(total_monthly_buying, 2),
        "monthly_difference": round(monthly_difference, 2),
        "annual_rent": round(annual_rent, 2),
        "annual_buying": round(annual_buying, 2),
        "recommendation": recommendation,
        "savings_per_month": round(abs(savings_per_month), 2)
    }

