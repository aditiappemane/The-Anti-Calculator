# Quick Start Guide

## Prerequisites

- Python 3.9+ installed
- Node.js 18+ installed
- Gemini API Key ([Get one here](https://makersuite.google.com/app/apikey))

## Step-by-Step Setup

### 1. Clone/Navigate to Project

```bash
cd challenge
```

### 2. Backend Setup

```bash
# Create virtual environment (recommended)
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Create .env file
# Copy env.example to .env and add your Gemini API key
# Windows:
copy env.example .env
# macOS/Linux:
cp env.example .env

# Edit .env and add your GEMINI_API_KEY
```

### 3. Start Backend Server

```bash
# Make sure you're in the project root
python -m uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

Backend will be running at `http://localhost:8000`

### 4. Frontend Setup (New Terminal)

```bash
# Navigate to frontend directory
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

Frontend will be running at `http://localhost:3000`

### 5. Test the Application

1. Open `http://localhost:3000` in your browser
2. Try asking:
   - "I want to buy a 2M AED apartment"
   - "Should I rent or buy if rent is 8,000 AED/month?"
   - "Help me calculate EMI for 1.6M loan at 4.5% for 25 years"

## Troubleshooting

### Backend Issues

- **Import errors**: Make sure virtual environment is activated
- **API key error**: Check that `.env` file exists and has `GEMINI_API_KEY` set
- **Port already in use**: Change port in uvicorn command or kill process using port 8000

### Frontend Issues

- **Cannot connect to backend**: Check that backend is running on port 8000
- **Build errors**: Delete `node_modules` and run `npm install` again
- **CORS errors**: Check that backend CORS settings include frontend URL

## Testing Math Functions

You can test the backend functions directly:

```python
# In Python shell (with venv activated)
from backend.utils.math_utils import calculate_emi, calculate_ltv

# Test EMI
emi = calculate_emi(principal=1600000, annual_interest_rate=4.5, tenure_years=25)
print(f"Monthly EMI: AED {emi:,.2f}")

# Test LTV
ltv = calculate_ltv(property_price=2000000)
print(f"Max Loan: AED {ltv['max_loan']:,.2f}")
print(f"Down Payment: AED {ltv['required_down_payment']:,.2f}")
```

## Production Deployment

For production, see the main README.md for deployment considerations.

