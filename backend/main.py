"""
FastAPI main application with chat endpoints and conversation management.
"""

import os
import json
import logging
import uuid
from typing import Dict, List, Optional
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

    # Initialize conversation
    if conversation_id not in conversations:
        conversations[conversation_id] = [
            {
                "role": "system",
                "content": (
                    "You are a helpful and empathetic AI Mortgage Advisor for the UAE market. "
                    "Your role is to help users decide whether to buy or rent a property, or whether to refinance their mortgage.\n\n"
                    "RULES:\n"
                    "1. ALWAYS use the provided functions for ANY financial calculation.\n"
                    "2. NEVER do math yourself.\n"
                    "3. When the user gives a property price → call calculate_ltv AND calculate_upfront_costs.\n"
                    "4. After that, ask if they want EMI.\n"
                    "5. ANY time rent and mortgage values appear → call rent_vs_buy.\n"
                    "6. Respond only using tool results.\n"
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
            response = await gemini_client.chat(messages=conversations[conversation_id])

            # DEBUG LOGGING: Detect tool calls
            print("\n======================")
            print("🔍 RAW LLM RESPONSE:")
            print("text:", response.get("text"))
            print("function_calls:", response.get("function_calls"))
            print("======================\n")

            initial_text = response.get("text", "")
            if initial_text:
                for char in initial_text:
                    yield char

                conversations[conversation_id].append({
                    "role": "assistant",
                    "content": initial_text
                })

            # -------------------------------
            # TOOL CALL HANDLING
            # -------------------------------
            if response.get("function_calls"):
                print("🔥 TOOL CALL DETECTED!")

                for func_call in response["function_calls"]:
                    func_name = func_call["name"]
                    func_args = func_call["arguments"]

                    print(f"🔧 Calling function: {func_name} with args {func_args}")

                    # Execute function
                    result = mortgage_service.execute_function_call(func_name, func_args)

                    # Format result
                    formatted_result = mortgage_service.format_function_result(func_name, result)

                    # Yield tool result to frontend
                    yield "\n" + formatted_result + "\n"

                    conversations[conversation_id].append({
                        "role": "assistant",
                        "content": formatted_result
                    })

                # Ask Gemini to produce the natural-language response
                final_response = await gemini_client.chat(messages=conversations[conversation_id])
                final_text = final_response.get("text", "")

                if final_text:
                    for char in final_text:
                        yield char

                    conversations[conversation_id].append({
                        "role": "assistant",
                        "content": final_text
                    })

            else:
                # -------------------------------
                # ❌ NO TOOL CALL → LLM responded normally
                # -------------------------------
                print("⚠️ NO TOOL CALL — Gemini responded without calling a function")

                assistant_msg = response.get("text", "")
                if assistant_msg:
                    for char in assistant_msg:
                        yield char

                    conversations[conversation_id].append({
                        "role": "assistant",
                        "content": assistant_msg
                    })

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
    
    if conversation_id not in conversations:
        conversations[conversation_id] = [
            {
                "role": "system",
                "content": (
                    "You are an AI Mortgage Advisor for the UAE market.\n\n"
                "MANDATORY RULES:\n"
                "- YOU MUST ALWAYS use the provided functions for ANY numeric or financial calculation.\n"
                "- YOU MUST NEVER compute numbers yourself, estimate, or guess numeric values.\n"
                "- If the user provides a property_price, IMMEDIATELY call calculate_ltv and calculate_upfront_costs.\n"
                "- If the user asks about monthly payments, EMI, interest or tenure, IMMEDIATELY call calculate_emi.\n"
                "- If the user asks to compare renting vs buying, IMMEDIATELY call rent_vs_buy.\n"
                "- Do not produce a numeric answer until the required functions have been executed and their results added to the conversation.\n"
                "- If multiple tools are required, call them one by one; wait for each tool result to be appended before calling the next.\n\n"
                "Style: Be empathetic, concise, and ask clarifying questions only when strictly necessary."
                )
            }
        ]
    
    conversations[conversation_id].append({
        "role": "user",
        "content": chat_message.message
    })
    
    async def stream_response():
        async for chunk in gemini_client.chat_stream(
            messages=conversations[conversation_id]
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

