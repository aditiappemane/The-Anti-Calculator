# AI Mortgage Advisor - UAE

A production-grade conversational AI agent that helps users decide whether to buy or rent a property in the UAE, or whether to refinance their mortgage.

## 🎯 Features

- **Conversational AI Interface**: ChatGPT-like UI with streaming responses
- **Deterministic Calculations**: All math is performed by backend functions (LLM never does math)
- **Function Calling**: Gemini LLM uses function calling to invoke backend calculations
- **Buy vs Rent Analysis**: Compare monthly costs and get recommendations
- **Mortgage Calculations**: EMI, LTV, and upfront costs calculations
- **Lead Capture**: Collect user information for follow-up assistance
- **Mobile Responsive**: Works seamlessly on desktop and mobile devices

## 📋 Domain Constants (UAE Mortgage Rules)

- **Maximum LTV**: 80%
- **Required Down Payment**: 20%
- **Upfront Costs**: 7% of property price (4% transfer + 2% agency + 1% misc)
- **Interest Rate**: 4.5% per year
- **Maximum Tenure**: 25 years

## 🏗️ Project Structure

```
.
├── backend/
│   ├── __init__.py
│   ├── main.py                 # FastAPI application
│   ├── config.py               # Domain constants
│   ├── utils/
│   │   ├── __init__.py
│   │   └── math_utils.py      # Deterministic math functions
│   ├── llm/
│   │   ├── __init__.py
│   │   └── gemini_client.py   # Gemini LLM client with function calling
│   └── services/
│       ├── __init__.py
│       └── mortgage_service.py # Business logic layer
├── frontend/
│   ├── src/
│   │   ├── components/        # React components
│   │   ├── services/          # API service layer
│   │   ├── types/             # TypeScript interfaces
│   │   ├── App.tsx            # Main app component
│   │   └── main.tsx           # Entry point
│   ├── package.json
│   └── vite.config.ts
├── requirements.txt           # Python dependencies
└── README.md

```

## 🚀 Setup Instructions

### Prerequisites

- Python 3.9+
- Node.js 18+
- Gemini API Key ([Get one here](https://makersuite.google.com/app/apikey))

### Backend Setup

1. **Navigate to the project root**:
   ```bash
   cd challenge
   ```

2. **Create a virtual environment** (recommended):
   ```bash
   python -m venv venv
   ```

3. **Activate virtual environment**:
   - Windows:
     ```bash
     venv\Scripts\activate
     ```
   - macOS/Linux:
     ```bash
     source venv/bin/activate
     ```

4. **Install Python dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

5. **Set up environment variables**:
   Create a `.env` file in the project root:
   ```env
   GEMINI_API_KEY=your_gemini_api_key_here
   PORT=8000
   HOST=0.0.0.0
   ```

6. **Run the backend server**:
   ```bash
   python -m uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
   ```

   The API will be available at `http://localhost:8000`

### Frontend Setup

1. **Navigate to frontend directory**:
   ```bash
   cd frontend
   ```

2. **Install dependencies**:
   ```bash
   npm install
   ```

3. **Create `.env` file** (optional, defaults to localhost:8000):
   ```env
   VITE_API_URL=http://localhost:8000
   ```

4. **Start the development server**:
   ```bash
   npm run dev
   ```

   The frontend will be available at `http://localhost:3000`

## 📡 API Endpoints

### POST `/api/chat`
Send a chat message and receive a streaming response.

**Request Body**:
```json
{
  "message": "I want to buy a 2M AED apartment",
  "conversation_id": "optional-conversation-id"
}
```

**Response**: Streaming text response with conversation ID in headers.

### POST `/api/lead-capture`
Capture lead information after conversation.

**Request Body**:
```json
{
  "conversation_id": "conversation-id",
  "name": "John Doe",
  "email": "john@example.com",
  "phone": "+971 XX XXX XXXX"
}
```

### GET `/api/conversation/{conversation_id}`
Get conversation history.

## 🔧 Backend Functions

All calculations are performed deterministically by backend functions:

### `calculate_emi(principal, annual_interest_rate, tenure_years)`
Calculates Equated Monthly Installment using the standard EMI formula.

### `calculate_ltv(property_price)`
Returns maximum loan amount (80% LTV) and required down payment (20%).

### `calculate_upfront_costs(property_price)`
Calculates upfront costs breakdown: transfer fee (4%), agency fee (2%), misc (1%).

### `rent_vs_buy(monthly_rent, monthly_mortgage, maintenance_fee)`
Compares renting vs buying costs and provides recommendation.

## 🎨 Frontend Features

- **Streaming Chat Interface**: Real-time message streaming
- **Message History**: Persistent conversation state
- **Loading Indicators**: Visual feedback during API calls
- **Lead Capture Form**: Modal form for collecting user information
- **Responsive Design**: Mobile-first approach with Tailwind CSS
- **Dark Mode Support**: Automatic dark mode detection

## 🧪 Testing

### Test Backend Functions

You can test the backend functions directly:

```python
from backend.utils.math_utils import calculate_emi, calculate_ltv

# Test EMI calculation
emi = calculate_emi(principal=1600000, annual_interest_rate=4.5, tenure_years=25)
print(f"Monthly EMI: AED {emi}")

# Test LTV calculation
ltv = calculate_ltv(property_price=2000000)
print(f"Max Loan: AED {ltv['max_loan']}, Down Payment: AED {ltv['required_down_payment']}")
```

## 📝 Notes

- **Never let LLM do math**: All calculations are performed by backend functions
- **Domain constants**: Never change the constants in `backend/config.py`
- **Error handling**: Comprehensive error handling for invalid inputs
- **Logging**: All errors are logged for debugging

## 🔒 Security Considerations

- Store API keys in environment variables (never commit to git)
- Use HTTPS in production
- Implement rate limiting for production
- Add authentication/authorization for production use
- Use a proper database instead of in-memory storage for conversations

## 🚧 Production Deployment

For production deployment:

1. Use a production WSGI server (e.g., Gunicorn)
2. Set up a reverse proxy (e.g., Nginx)
3. Use a proper database (PostgreSQL, MongoDB, etc.)
4. Implement Redis for conversation state management
5. Add monitoring and logging (e.g., Sentry)
6. Set up CI/CD pipeline
7. Use environment-specific configuration files

## 📄 License

This project is provided as-is for the challenge.

## 🤝 Support

For issues or questions, please refer to the project documentation or contact the development team.

