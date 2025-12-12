"""
Mortgage service that handles business logic and coordinates between LLM and math utilities.
"""

import logging
from typing import Dict, Any, List, Optional
from backend.utils.math_utils import (
    calculate_emi,
    calculate_ltv,
    calculate_upfront_costs,
    rent_vs_buy
)
from backend.config import INTEREST_RATE, MAX_TENURE_YEARS

logger = logging.getLogger(__name__)


class MortgageService:
    """Service layer for mortgage calculations and advice."""
    
    def __init__(self):
        self.interest_rate = INTEREST_RATE
        self.max_tenure = MAX_TENURE_YEARS
    
    def execute_function_call(self, function_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a function call from the LLM.
        
        Args:
            function_name: Name of the function to call
            arguments: Arguments for the function
        
        Returns:
            Result dictionary with the calculation results
        """
        try:
            if function_name == "calculate_emi":
                principal = float(arguments.get("principal", 0))
                annual_interest_rate = float(arguments.get("annual_interest_rate", self.interest_rate))
                tenure_years = int(arguments.get("tenure_years", self.max_tenure))
                
                # Validate tenure
                if tenure_years > self.max_tenure:
                    tenure_years = self.max_tenure
                
                emi = calculate_emi(principal, annual_interest_rate, tenure_years)
                return {
                    "success": True,
                    "result": {
                        "emi": emi,
                        "principal": principal,
                        "interest_rate": annual_interest_rate,
                        "tenure_years": tenure_years,
                        "total_amount": emi * tenure_years * 12,
                        "total_interest": (emi * tenure_years * 12) - principal
                    }
                }
            
            elif function_name == "calculate_ltv":
                property_price = float(arguments.get("property_price", 0))
                ltv_result = calculate_ltv(property_price)
                ltv_result["property_price"] = property_price
                return {
                    "success": True,
                    "result": ltv_result
                }
            
            elif function_name == "calculate_upfront_costs":
                property_price = float(arguments.get("property_price", 0))
                upfront_result = calculate_upfront_costs(property_price)
                upfront_result["property_price"] = property_price
                return {
                    "success": True,
                    "result": upfront_result
                }
            
            elif function_name == "rent_vs_buy":
                monthly_rent = float(arguments.get("monthly_rent", 0))
                monthly_mortgage = float(arguments.get("monthly_mortgage", 0))
                maintenance_fee = float(arguments.get("maintenance_fee", 0))
                
                comparison_result = rent_vs_buy(monthly_rent, monthly_mortgage, maintenance_fee)
                return {
                    "success": True,
                    "result": comparison_result
                }
            
            else:
                return {
                    "success": False,
                    "error": f"Unknown function: {function_name}"
                }
        
        except ValueError as e:
            logger.error(f"Validation error in {function_name}: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
        except Exception as e:
            logger.error(f"Error executing {function_name}: {str(e)}", exc_info=True)
            return {
                "success": False,
                "error": f"An error occurred: {str(e)}"
            }
    
    def format_function_result(self, function_name: str, result: Dict[str, Any]) -> str:
        """
        Format function result into a human-readable string for the LLM.
        
        Args:
            function_name: Name of the function that was called
            result: Result dictionary from execute_function_call
        
        Returns:
            Formatted string describing the results
        """
        if not result.get("success"):
            return f"Error: {result.get('error', 'Unknown error')}"
        
        data = result["result"]
        
        if function_name == "calculate_emi":
            return (
                f"EMI Calculation Results:\n"
                f"- Monthly EMI: AED {data['emi']:,.2f}\n"
                f"- Loan Amount: AED {data['principal']:,.2f}\n"
                f"- Interest Rate: {data['interest_rate']}% per year\n"
                f"- Tenure: {data['tenure_years']} years\n"
                f"- Total Amount Payable: AED {data['total_amount']:,.2f}\n"
                f"- Total Interest: AED {data['total_interest']:,.2f}"
            )
        
        elif function_name == "calculate_ltv":
            property_price = data.get("property_price", 0)
            return (
                f"Loan-to-Value (LTV) Analysis:\n"
                f"- Property Price: AED {property_price:,.2f}\n"
                f"- Maximum Loan (80% LTV): AED {data['max_loan']:,.2f}\n"
                f"- Required Down Payment (20%): AED {data['required_down_payment']:,.2f}"
            )
        
        elif function_name == "calculate_upfront_costs":
            property_price = data.get("property_price", 0)
            return (
                f"Upfront Costs Breakdown:\n"
                f"- Property Price: AED {property_price:,.2f}\n"
                f"- Transfer Fee (4%): AED {data['transfer_fee']:,.2f}\n"
                f"- Agency Fee (2%): AED {data['agency_fee']:,.2f}\n"
                f"- Miscellaneous (1%): AED {data['misc_fee']:,.2f}\n"
                f"- Total Upfront Costs (7%): AED {data['total_upfront_costs']:,.2f}"
            )
        
        elif function_name == "rent_vs_buy":
            recommendation = data['recommendation'].upper()
            return (
                f"Rent vs Buy Comparison:\n"
                f"- Monthly Rent: AED {data['monthly_rent']:,.2f}\n"
                f"- Monthly Mortgage: AED {data['monthly_mortgage']:,.2f}\n"
                f"- Maintenance Fee: AED {data['maintenance_fee']:,.2f}\n"
                f"- Total Monthly Cost (Buying): AED {data['total_monthly_buying']:,.2f}\n"
                f"- Monthly Difference: AED {data['monthly_difference']:,.2f}\n"
                f"- Annual Rent Cost: AED {data['annual_rent']:,.2f}\n"
                f"- Annual Buying Cost: AED {data['annual_buying']:,.2f}\n"
                f"\nRecommendation: Based on monthly costs, {recommendation}ING appears more cost-effective.\n"
                f"You would save approximately AED {data['savings_per_month']:,.2f} per month by choosing to {recommendation}."
            )
        
        return str(data)

