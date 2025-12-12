"""
FastAPI main application with chat endpoints and conversation management.
"""

import os
import json
import logging
import uuid
from typing import Dict, List, Optional, Any
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from dotenv import load_dotenv

env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
load_dotenv(env_path)


from backend.llm.gemini_client import GeminiClient
from backend.services.mortgage_service import MortgageService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(title="AI Mortgage Advisor API", version="1.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],  # React dev servers
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize services
gemini_client = GeminiClient()
mortgage_service = MortgageService()

# In-memory conversation storage (use Redis/DB in production)
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


@app.post("/api/chat")
async def chat_endpoint(chat_message: ChatMessage):
    conversation_id = chat_message.conversation_id or str(uuid.uuid4())

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
            
            # Introduce a loop to handle chained tool calls
            while True:
                if initial_text:
                    for char in initial_text:
                        yield char
                    conversations[conversation_id].append({"role": "assistant", "content": initial_text})
                
                if response.get("function_calls"):
                    print("🔥 TOOL CALL DETECTED!")
                    tool_outputs_for_llm = []

                    for func_call in response["function_calls"]:
                        func_name = func_call["name"]
                        func_args = func_call["arguments"]

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
                                current_state["property_price"] = func_args.get("property_price")
                            elif func_name == "calculate_upfront_costs":
                                current_state["total_upfront_costs"] = result["result"]["total_upfront_costs"]
                            elif func_name == "rent_vs_buy":
                                current_state["monthly_rent"] = result["result"]["monthly_rent"]
                                current_state["monthly_mortgage"] = result["result"]["monthly_mortgage"]
                                current_state["maintenance_fee"] = result["result"]["maintenance_fee"]
                        
                        formatted_result = mortgage_service.format_function_result(func_name, result)
                        tool_outputs_for_llm.append(formatted_result)

                        conversations[conversation_id].append({"role": "assistant", "content": formatted_result})
                        conversations[conversation_id].append({"role": "assistant", "content": f"__STATE__{json.dumps(current_state)}"})
                        
                        yield "\n" + formatted_result + "\n"
                        yield f"__STATE__{json.dumps(current_state)}\n"

                    # After executing tools, call LLM again with tool outputs and updated state
                    # No need to inject state again here, as it's already in conversations
                    response = await gemini_client.chat(messages=conversations[conversation_id])
                    initial_text = response.get("text", "") # Update initial_text for next iteration
                    print("\n======================")
                    print("🔍 RAW LLM RESPONSE AFTER TOOL CALLS:")
                    print("text:", response.get("text"))
                    print("function_calls:", response.get("function_calls"))
                    print("======================\n")

                else:
                    # No function calls, break the loop and stream final text
                    if initial_text:
                        for char in initial_text:
                            yield char
                        conversations[conversation_id].append({"role": "assistant", "content": initial_text})
                    print("⚠️ NO TOOL CALL — Gemini responded without calling a function. Breaking loop.")
                    break

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

