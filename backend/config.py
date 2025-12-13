"""
Configuration constants for the mortgage advisor.
These are domain constants that should NEVER be changed.
"""

import os
from dotenv import load_dotenv

# Load environment variables
env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
load_dotenv(env_path)

# Database Settings
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./sql_app.db")

# JWT Settings
SECRET_KEY = os.getenv("SECRET_KEY", "super-secret-jwt-key")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30  # 30 minutes

# Maximum Loan-to-Value ratio (as percentage)
MAX_LTV = 80.0

# Required Down Payment (as percentage)
REQUIRED_DOWN_PAYMENT = 20.0

# Upfront Costs Breakdown (as percentages)
TRANSFER_FEE_PERCENT = 4.0
AGENCY_FEE_PERCENT = 2.0
MISC_FEE_PERCENT = 1.0
TOTAL_UPFRONT_COSTS_PERCENT = 7.0

# Interest Rate (annual percentage)
INTEREST_RATE = 4.5

# Maximum Loan Tenure (in years)
MAX_TENURE_YEARS = 25

