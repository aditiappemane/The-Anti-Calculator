"""
Gemini 2.5 Flash client with function calling + streaming support.
Compatible with google-generativeai 0.8.5.
"""

import os
import json
import logging
from typing import List, Dict, Any, Optional, AsyncGenerator

import google.generativeai as genai

logger = logging.getLogger(__name__)


class GeminiClient:
    """Gemini 2.5 Flash LLM wrapper with function calling + chat/stream."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("Missing GEMINI_API_KEY environment variable.")

        genai.configure(api_key=self.api_key)

        # Use Gemini 2.5 Flash
        self.model_name = "models/gemini-2.5-flash"

        # Tools
        self.tools = [
            {
                "function_declarations": [
                    {
                        "name": "calculate_emi",
                        "description": "Calculate EMI using loan amount, interest rate, and tenure.",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "principal": {"type": "number"},
                                "annual_interest_rate": {"type": "number"},
                                "tenure_years": {"type": "integer"},
                            },
                            "required": ["principal", "annual_interest_rate", "tenure_years"]
                        }
                    },
                    {
                        "name": "calculate_ltv",
                        "description": "Calculate max loan (80%) and required down payment.",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "property_price": {"type": "number"},
                            },
                            "required": ["property_price"]
                        }
                    },
                    {
                        "name": "calculate_upfront_costs",
                        "description": "Calculate 7% upfront costs.",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "property_price": {"type": "number"},
                            },
                            "required": ["property_price"]
                        }
                    },
                    {
                        "name": "rent_vs_buy",
                        "description": "Compare renting vs buying.",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "monthly_rent": {"type": "number"},
                                "monthly_mortgage": {"type": "number"},
                                "maintenance_fee": {"type": "number"},
                            },
                            "required": ["monthly_rent", "monthly_mortgage"]
                        }
                    },
                ]
            }
        ]

    # ---------------------------------------------------------
    # Format messages for Gemini v0.8.5
    # ---------------------------------------------------------
    def format_messages(self, messages: List[Dict[str, str]]):
        system_instruction = None
        formatted = []

        for msg in messages:
            role = msg["role"]
            content = msg["content"]

            if role == "system":
                system_instruction = content

            elif role == "user":
                formatted.append({"role": "user", "parts": [content]})

            elif role == "assistant":
                # FIX: Gemini requires the role "model", NOT "assistant"
                formatted.append({"role": "model", "parts": [content]})

        return system_instruction, formatted

    # ---------------------------------------------------------
    # Non-streaming chat with tool calling
    # ---------------------------------------------------------
    async def chat(self, messages: List[Dict[str, str]]) -> Dict[str, Any]:
        try:
            system_instruction, formatted_messages = self.format_messages(messages)

            model = genai.GenerativeModel(
                model_name=self.model_name,
                tools=self.tools,
                system_instruction=system_instruction,
            )

            chat = model.start_chat(
                history=formatted_messages[:-1] if len(formatted_messages) > 1 else [],
            )

            last_user_message = formatted_messages[-1]["parts"][0]

            response = chat.send_message(last_user_message)

            response_text = ""
            function_calls = []

            if response.candidates:
                for part in response.candidates[0].content.parts:

                    if hasattr(part, "function_call") and part.function_call:
                        fn = part.function_call
                        args = fn.args

                        if isinstance(args, str):
                            args = json.loads(args)

                        function_calls.append({
                            "name": fn.name,
                            "arguments": args
                        })

                    elif hasattr(part, "text"):
                        response_text += part.text

            return {
                "text": response_text,
                "function_calls": function_calls or None
            }

        except Exception as e:
            logger.error(f"Error in Gemini chat: {e}", exc_info=True)
            return {"text": "Error occurred", "function_calls": None}

    # ---------------------------------------------------------
    # Streaming chat
    # ---------------------------------------------------------
    async def chat_stream(self, messages: List[Dict[str, str]]) -> AsyncGenerator[str, None]:
        try:
            system_instruction, formatted_messages = self.format_messages(messages)

            model = genai.GenerativeModel(
                model_name=self.model_name,
                tools=self.tools,
                system_instruction=system_instruction,
            )

            chat = model.start_chat(
                history=formatted_messages[:-1] if len(formatted_messages) > 1 else []
            )

            last_user_message = formatted_messages[-1]["parts"][0] if formatted_messages else ""
            if not isinstance(last_user_message, str):
                # Handle cases where last_user_message might be a Part object if function_calling
                # This is a defensive check, typically it should be a string here
                logger.warning(f"last_user_message is not a string, type: {type(last_user_message)}")
                last_user_message = str(last_user_message) # Convert to string defensively

            stream = chat.send_message(last_user_message, stream=True)

            function_calls = []
            
            async for chunk in stream:
                if chunk.candidates:
                    for part in chunk.candidates[0].content.parts:
                        if hasattr(part, "text") and part.text:
                            yield part.text
                        if hasattr(part, "function_call") and part.function_call:
                            function_calls.append(part.function_call)
            
            # If function calls were made, yield a special marker
            if function_calls:
                formatted_function_calls = []
                for fc in function_calls:
                    args = fc.args
                    if isinstance(args, str):
                        try:
                            args = json.loads(args)
                        except json.JSONDecodeError:
                            logger.warning(f"Could not decode function_call args: {args}")
                            pass
                    formatted_function_calls.append({'name': fc.name, 'arguments': args})
                yield f"\n\n[FUNCTION_CALLS:{json.dumps(formatted_function_calls)}]\n\n"

        except Exception as e:
            logger.error(f"Streaming error in Gemini client: {e}", exc_info=True)
            yield f"Streaming failed due to an internal error: {e}"
