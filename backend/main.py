"""
FastAPI main application with chat endpoints and conversation management.
"""

import os
import json
import logging
import uuid
import re # Import re for regex operations
from typing import Dict, List, Optional, Any
from fastapi import FastAPI, HTTPException, UploadFile, File, Depends # Added UploadFile, File, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from dotenv import load_dotenv
import tempfile # Added tempfile
from backend.services.vision_service import VisionService # Added VisionService import

# Helper to extract state from messages
def extract_state_from_messages(msgs: List[Dict[str, str]]) -> Dict[str, Any]:
    state = {}
    for msg in msgs:
        if msg["role"] == "assistant" and msg["content"].startswith("__STATE__{"):
            try:
                state_str = msg["content"].replace("__STATE__", "")
                state.update(json.loads(state_str))
            except json.JSONDecodeError:
                logger.warning(f"Could not decode state message: {msg['content']}")
    return state

env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
load_dotenv(env_path)

# Import SQLAlchemy Base and engine
from backend.database import Base, engine
from backend import models # Import models to ensure they are registered with Base

# Create database tables
models.Base.metadata.create_all(bind=engine)

from backend.llm.gemini_client import GeminiClient
from backend.services.mortgage_service import MortgageService
from backend.database import get_db # Import get_db
from backend import schemas, models, crud # Import schemas, models, crud
from backend.auth import router as auth_router # Import auth router
from backend.profile import router as profile_router # Import profile router


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="AI Mortgage Advisor API",
    description="Backend API for the AI Mortgage Advisor with Gemini LLM and function calling.",
    version="1.0.0",
)

# Register auth router
app.include_router(auth_router, prefix="/api", tags=["Authentication"])
app.include_router(profile_router, prefix="/api", tags=["User Profile"])

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],  # React dev servers
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

# Initialize services
gemini_client = GeminiClient()
mortgage_service = MortgageService()
vision_service = VisionService() # Initialize VisionService

# In-memory storage for conversations (for demonstration purposes)
conversations: Dict[str, List[Dict[str, str]]] = {}


class ChatMessage(BaseModel):
    message: str
    conversation_id: Optional[str] = None


class LeadCapture(BaseModel):
    conversation_id: str
    name: str
    email: str
    phone: Optional[str] = None


@app.get("/")
async def root():
    """Health check endpoint."""
    return {"status": "ok", "message": "AI Mortgage Advisor API"}


from backend.auth import get_current_user # Import get_current_user
from backend.database import get_db # Import get_db
from sqlalchemy.orm import Session # Import Session

@app.post("/api/upload-salary-slip", response_model=schemas.Document) # Changed response_model
async def upload_salary_slip(
    file: UploadFile = File(...),
    current_user: schemas.User = Depends(get_current_user),
    db: Session = Depends(get_db) # Added DB Session dependency
):
    """
    Uploads a salary slip (image or PDF) for financial data extraction using Gemini Vision.
    The file is processed ephemerally and not stored persistently.
    """
    # Security: Define allowed file types and maximum size to prevent abuse
    ALLOWED_CONTENT_TYPES = ["image/jpeg", "image/png", "application/pdf"]
    MAX_FILE_SIZE_MB = 5
    MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024

    if file.content_type not in ALLOWED_CONTENT_TYPES:
        logger.warning(f"Invalid file type uploaded: {file.content_type}")
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type. Only JPEG, PNG images, and PDF documents are allowed (received {file.content_type})."
        )

    # Security: Read file in chunks to prevent large file attacks and memory exhaustion
    # and to check size before full load
    file_contents = b""
    while chunk := await file.read(8192): # Read in 8KB chunks
        file_contents += chunk
        if len(file_contents) > MAX_FILE_SIZE_BYTES:
            logger.warning(f"File size exceeded limit: {file.filename}")
            raise HTTPException(
                status_code=413,
                detail=f"File too large. Maximum size is {MAX_FILE_SIZE_MB}MB."
            )

    # Security: Use temporary file for ephemeral storage, deleted after processing
    # This prevents persistent storage of sensitive user documents.
    with tempfile.NamedTemporaryFile(delete=False, suffix=f".{file.filename.split('.')[-1]}") as temp_file:
        temp_file.write(file_contents)
        temp_file_path = temp_file.name
    
    logger.info(f"Temporary file created for processing: {temp_file_path}")

    try:
        # Pass the temporary file path and content type to the vision service
        extracted_data = await vision_service.extract_financial_data(temp_file_path, file.content_type)
        
        # Create a new document entry in the database with extracted data
        document_create = schemas.DocumentCreate(
            file_name=file.filename,
            file_type=file.content_type,
            extracted_salary_data=extracted_data # Store the extracted data
        )
        db_document = crud.create_user_document(db, document=document_create, owner_id=current_user.id, file_path=file.filename)
        
        return db_document
    finally:
        # Security: Ensure the temporary file is deleted even if processing fails
        os.remove(temp_file_path)
        logger.info(f"Temporary file deleted: {temp_file_path}")




@app.post("/api/chat")
async def chat_endpoint(chat_message: ChatMessage):
    conversation_id = chat_message.conversation_id or str(uuid.uuid4())

    # Initialize conversation
    if conversation_id not in conversations:
        conversations[conversation_id] = [
            {
                "role": "system",
                "content": (
                    "You are an AI Mortgage Advisor for the UAE.\n\n"
                    "You MUST use the provided functions to perform ALL calculations. Never perform math yourself.\n\n"
                    "You have access to shared structured state stored in messages like:\n"
                    "__STATE___{\"key\": value}\n\n"
                    "Whenever the user asks for:\n"
                    "- EMI -> ALWAYS call calculate_emi.\n"
                    "- LTV -> ALWAYS call calculate_ltv.\n"
                    "- Upfront costs -> ALWAYS call calculate_upfront_costs.\n"
                    "- Rent vs buy -> ALWAYS call rent_vs_buy.\n\n"
                    "Default values:\n"
                    "- annual_interest_rate = 4.5 unless user explicitly changes it\n"
                    "- tenure_years = 25 unless user explicitly changes it\n\n"
                    "Use these values automatically:\n"
                    "- principal = latest __STATE__.max_loan\n"
                    "- monthly_rent = latest __STATE__.monthly_rent\n"
                    "- maintenance_fee = latest __STATE__.maintenance_fee\n"
                    "- monthly_mortgage = latest __STATE__.monthly_mortgage\n\n"
                    "NEVER ask the user for interest rate, tenure, or loan amount if they already exist in state.\n\n"
                    "Your job:\n"
                    "1. Understand user request\n"
                    "2. Check if required values are available in state\n"
                    "3. If something is missing, ask ONLY for that value\n"
                    "4. Otherwise, trigger the correct function call\n"
                    "5. After function output, store updated state in a __STATE__ message\n"
                    "6. Reply conversationally without doing math. When constructing your response, always strive for conciseness, professionalism, and easy readability.\n\n"
                    "When providing a property purchase summary, strictly use this structured markdown format:\n"
                    "\n"
                    "Great choice! [One personalized sentence based on property price, e.g., 'Buying a 2,000,000 AED apartment is a significant milestone.'].\n"
                    "\n"
                    "📊 **Purchase Summary**\n"
                    "- **Property Price**: AED [formatted_property_price]\n"
                    "- **Maximum Loan (80% LTV)**: AED [formatted_max_loan]\n"
                    "- **Required Down Payment (20%)**: AED [formatted_required_down_payment]\n"
                    "- **Upfront Costs (approx. 7%)**: AED [formatted_total_upfront_costs]\n"
                    "- **Estimated Monthly EMI**: AED [formatted_monthly_mortgage]\n"
                    "  _(Calculated at [annual_interest_rate]% annual interest over [tenure_years] years)_\n"
                    "\n"
                    "💡 **Total upfront amount needed**: AED [formatted_total_upfront_amount]\n"
                    "  _(down payment + upfront costs)_\n"
                    "\n"
                    "After the summary, end with ONLY ONE concise next-step question. Choose from these examples:\n"
                    "- \"Would you like to compare this with renting?\"\n"
                    "- \"Do you want to adjust the loan tenure or interest rate?\"\n"
                    "- \"Should we explore refinancing options?\"\n"
                    "\n"
                    "REFINANCING RULES:\n"
                    "- When the user asks about refinancing, lowering EMI, reducing interest, switching banks, or restructuring their mortgage:\n"
                    "    - ALWAYS call calculate_emi.\n"
                    "    - Treat refinancing exactly like EMI calculation using user-provided values.\n"
                    "    - Required fields:\n"
                    "        * principal (remaining loan amount)\n"
                    "        * annual_interest_rate (new rate)\n"
                    "        * tenure_years (new tenure)\n"
                    "    - If any required value is missing, ask ONLY for that value.\n"
                    "    - If multiple values are missing, ask for them in a single question.\n"
                    "    - Never refuse refinancing questions.\n"
                    "    - Never say you cannot help with refinancing.\n"
                    "    - Never answer refinancing questions with plain text.\n"
                    "    - Once all required fields are available, immediately trigger calculate_emi.\n\n"
                    "IMPORTANT: NEVER include '__STATE__ { ... }' in your natural language responses. This is for internal use only. NEVER show raw tool output. NEVER repeat the same section twice."
                )
            }
        ]

    # Add user message
    conversations[conversation_id].append({
        "role": "user",
        "content": chat_message.message
    })

    async def generate_response():
        try:
            current_messages = list(conversations[conversation_id]) # Create a mutable copy
            current_state = extract_state_from_messages(current_messages)

            # Inject current state into messages for LLM context (transient)
            if current_state:
                state_injection_message = {
                    "role": "user", # Use 'user' role for transient state injection
                    "content": f"__STATE__{json.dumps(current_state)}"
                }
                current_messages.insert(1, state_injection_message) # Insert after system message

            response = await gemini_client.chat(messages=current_messages)

            # DEBUG LOGGING: Detect tool calls
            print("\n======================")
            print("🔍 RAW LLM RESPONSE:")
            print("text:", response.get("text"))
            print("function_calls:", response.get("function_calls"))
            print("======================\n")

            initial_text = response.get("text", "")
            # IMMEDIATELY filter out any __STATE__{...} from the LLM's raw text response
            initial_text = re.sub(r'__STATE__\{.*?\}', '', initial_text).strip()
            
            # Introduce a loop to handle chained tool calls
            final_assistant_response_text_buffer = []
            while True:
                # Accumulate any filtered natural language text from the LLM (if not empty)
                if initial_text:
                    final_assistant_response_text_buffer.append(initial_text)
                    # Add to conversation history for context, but avoid duplicates if LLM repeats itself
                    if not any(msg.get("content") == initial_text for msg in conversations[conversation_id]):
                        conversations[conversation_id].append({"role": "assistant", "content": initial_text})

                # Reset initial_text for the next iteration
                initial_text = "" 

                if response.get("function_calls"):
                    print("🔥 TOOL CALL DETECTED!")

                    for func_call in response["function_calls"]:
                        func_name = func_call["name"]
                        # Convert func_args from MapComposite to dict
                        func_args = dict(func_call["arguments"])

                        # Apply defaults and state to missing arguments
                        if func_name == "calculate_emi":
                            func_args.setdefault("annual_interest_rate", 4.5)
                            func_args.setdefault("tenure_years", 25)
                            if "principal" not in func_args and "max_loan" in current_state:
                                func_args["principal"] = current_state["max_loan"]
                        elif func_name == "calculate_ltv":
                            pass  # Relies on direct property_price
                        elif func_name == "calculate_upfront_costs":
                            if "property_price" not in func_args and "property_price" in current_state:
                                func_args["property_price"] = current_state["property_price"]
                            elif "property_price" not in func_args and func_name == "calculate_upfront_costs":
                                # Attempt to extract property_price from current user message if not in args or state
                                last_user_content = conversations[conversation_id][-1]["content"].lower()
                                match = re.search(r'(\d+(?:\.\d+)?)\s*m(?:illion)?', last_user_content)
                                if match:
                                    price_million = float(match.group(1))
                                    func_args["property_price"] = price_million * 1_000_000
                                    logger.info(f"Extracted property_price from message: {func_args['property_price']}")

                        elif func_name == "rent_vs_buy":
                            if "monthly_rent" not in func_args and "monthly_rent" in current_state:
                                func_args["monthly_rent"] = current_state["monthly_rent"]
                            if "monthly_mortgage" not in func_args and "monthly_mortgage" in current_state:
                                func_args["monthly_mortgage"] = current_state["monthly_mortgage"]
                            if "maintenance_fee" not in func_args and "maintenance_fee" in current_state:
                                func_args["maintenance_fee"] = current_state["maintenance_fee"]

                        print(f"🔧 Calling function: {func_name} with args {func_args}")

                        result = mortgage_service.execute_function_call(func_name, func_args)

                        if result.get("success") and result["result"]:
                            if func_name == "calculate_emi":
                                current_state["monthly_mortgage"] = result["result"]["emi"]
                                current_state["principal"] = result["result"]["principal"]
                                current_state["annual_interest_rate"] = result["result"]["interest_rate"]
                                current_state["tenure_years"] = result["result"]["tenure_years"]
                            elif func_name == "calculate_ltv":
                                current_state["max_loan"] = result["result"]["max_loan"]
                                current_state["required_down_payment"] = result["result"]["required_down_payment"]
                                current_state["property_price"] = func_args.get("property_price") # Store the input property price

                                # Immediately queue calculate_upfront_costs if LTV was just calculated
                                if current_state.get("property_price") and not current_state.get("total_upfront_costs"):
                                    logger.info("LTV calculated, programmatically adding calculate_upfront_costs to function_calls.")
                                    response["function_calls"].append({
                                        "name": "calculate_upfront_costs",
                                        "arguments": {"property_price": current_state["property_price"]}
                                    })

                            elif func_name == "calculate_upfront_costs":
                                current_state["total_upfront_costs"] = result["result"]["total_upfront_costs"]
                            elif func_name == "rent_vs_buy":
                                current_state["monthly_rent"] = result["result"]["monthly_rent"]
                                current_state["monthly_mortgage"] = result["result"]["monthly_mortgage"]
                                current_state["maintenance_fee"] = result["result"]["maintenance_fee"]

                        # Format result
                        formatted_result = mortgage_service.format_function_result(func_name, result)

                        conversations[conversation_id].append({"role": "assistant", "content": formatted_result})
                        conversations[conversation_id].append({"role": "assistant", "content": f"__STATE__{json.dumps(current_state)}"})

                    # After executing tools, call LLM again with tool outputs and updated state
                    response = await gemini_client.chat(messages=conversations[conversation_id])
                    initial_text = response.get("text", "") # Update initial_text for next iteration
                    print("\n======================")
                    print("🔍 RAW LLM RESPONSE AFTER TOOL CALLS:")
                    print("text:", response.get("text"))
                    print("function_calls:", response.get("function_calls"))
                    print("======================\n")

                else:
                    # No function calls, break the loop
                    print("⚠️ NO TOOL CALL — Gemini responded without calling a function. Breaking loop.")
                    break
            
            # Stream the final consolidated natural language response to the frontend
            final_response_text = " ".join(final_assistant_response_text_buffer).strip()
            if final_response_text:
                for char in final_response_text:
                    yield char
                # The final response should already be in conversations due to initial_text handling

            yield f"\n\n[CONVERSATION_ID:{conversation_id}]"

        except Exception as e:
            logger.error(f"Error in chat endpoint: {e}", exc_info=True)
            yield "I encountered an error. Please try again."

    return StreamingResponse(
        generate_response(),
        media_type="text/plain",
        headers={"X-Conversation-ID": conversation_id}
    )

@app.post("/api/chat/stream")
async def chat_stream_endpoint(chat_message: ChatMessage):
    """
    Alternative streaming endpoint (for future use with better streaming support).
    """
    conversation_id = chat_message.conversation_id or str(uuid.uuid4())

    # Initialize conversation
    if conversation_id not in conversations:
        conversations[conversation_id] = [
            {
                "role": "system",
                "content": (
                    "You are an AI Mortgage Advisor for the UAE.\n\n"
                    "You MUST use the provided functions to perform ALL calculations. Never perform math yourself.\n\n"
                    "You have access to shared structured state stored in messages like:\n"
                    "__STATE___{\"key\": value}\n\n"
                    "Whenever the user asks for:\n"
                    "- EMI -> ALWAYS call calculate_emi.\n"
                    "- LTV -> ALWAYS call calculate_ltv.\n"
                    "- Upfront costs -> ALWAYS call calculate_upfront_costs.\n"
                    "- Rent vs buy -> ALWAYS call rent_vs_buy.\n\n"
                    "Default values:\n"
                    "- annual_interest_rate = 4.5 unless user explicitly changes it\n"
                    "- tenure_years = 25 unless user explicitly changes it\n\n"
                    "Use these values automatically:\n"
                    "- principal = latest __STATE__.max_loan\n"
                    "- monthly_rent = latest __STATE__.monthly_rent\n"
                    "- maintenance_fee = latest __STATE__.maintenance_fee\n"
                    "- monthly_mortgage = latest __STATE__.monthly_mortgage\n\n"
                    "NEVER ask the user for interest rate, tenure, or loan amount if they already exist in state.\n\n"
                    "Your job:\n"
                    "1. Understand user request\n"
                    "2. Check if required values are available in state\n"
                    "3. If something is missing, ask ONLY for that value\n"
                    "4. Otherwise, trigger the correct function call\n"
                    "5. After function output, store updated state in a __STATE__ message\n"
                    "6. Reply conversationally without doing math"
                )
            }
        ]

    # Add user message
    conversations[conversation_id].append({
        "role": "user",
        "content": chat_message.message
    })

    async def stream_response():
        current_messages = list(conversations[conversation_id]) # Create a mutable copy
        current_state = extract_state_from_messages(current_messages)

        # Inject current state into messages for LLM context (transient)
        if current_state:
            state_injection_message = {
                "role": "user", # Use 'user' role for transient state injection
                "content": f"__STATE__{json.dumps(current_state)}"
            }
            current_messages.insert(1, state_injection_message) # Insert after system message

        async for chunk in gemini_client.chat_stream(
            messages=current_messages
        ):
            yield chunk

    return StreamingResponse(
        stream_response(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Conversation-ID": conversation_id
        }
    )


@app.post("/api/lead-capture")
async def lead_capture_endpoint(lead: LeadCapture):
    """
    Capture lead information after conversation.
    """
    if lead.conversation_id not in conversations:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # In production, save to database
    logger.info(f"Lead captured: {lead.name}, {lead.email}, {lead.phone}")

    return {
        "success": True,
        "message": "Thank you! We'll be in touch soon.",
        "conversation_id": lead.conversation_id
    }


@app.get("/api/conversation/{conversation_id}")
async def get_conversation(conversation_id: str):
    """
    Get conversation history.
    """
    if conversation_id not in conversations:
        raise HTTPException(status_code=404, detail="Conversation not found")

    return {
        "conversation_id": conversation_id,
        "messages": conversations[conversation_id]
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

