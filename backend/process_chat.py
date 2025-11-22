#!/usr/bin/env python3
"""
The Gold Box v0.2.5 - Process Chat Endpoint
Single-call API endpoint with system prompt integration

Converts Foundry HTML → Compact JSON → AI → Compact JSON → Foundry HTML

License: CC-BY-NC-SA 4.0
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks, Request
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional, Union
import logging
import json
import asyncio
from datetime import datetime

from processor import ChatContextProcessor
from provider_manager import ProviderManager
from ai_service import AIService

# Configure logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api", tags=["chat"])

# Request models
class FrontendMessage(BaseModel):
    """Model for individual frontend message"""
    sender: str = Field(..., description="Message sender")
    content: str = Field(..., description="HTML content of message")
    timestamp: Optional[str] = Field("", description="Message timestamp")

class MessageRequest(BaseModel):
    """Request model for process chat endpoint"""
    messages: List[Union[str, FrontendMessage]] = Field(..., description="List of HTML chat messages (strings) or frontend message objects")
    user_message: Optional[str] = Field(None, description="Optional user message to include")
    settings: Optional[Dict[str, Any]] = Field(None, description="Settings from frontend including provider info")

# Request model for validate endpoint specifically
class ValidateRequest(BaseModel):
    """Request model for validate endpoint"""
    messages: List[Union[str, FrontendMessage]] = Field(..., description="List of HTML messages (strings) or frontend message objects to validate")

class MessageResponse(BaseModel):
    """Response model for process chat endpoint"""
    response: str = Field(..., description="AI response as Foundry HTML")
    processed_context: List[Dict[str, Any]] = Field(..., description="Processed messages as compact JSON")
    tokens_used: Optional[int] = Field(None, description="Tokens used for API call")
    processing_time: Optional[float] = Field(None, description="Processing time in seconds")

class ProcessingStatus(BaseModel):
    """Status model for processing updates"""
    status: str = Field(..., description="Processing status")
    message: str = Field(..., description="Status message")
    timestamp: str = Field(..., description="Timestamp of status update")

# Global processor instance
processor = ChatContextProcessor()
provider_manager = ProviderManager()
ai_service = AIService(provider_manager)

# Processing status tracking
processing_status = {}

@router.post("/process_chat", response_model=MessageResponse)
async def process_chat(
    request: MessageRequest,
    background_tasks: BackgroundTasks,
    http_request: Request  # Add Request parameter for middleware access
):
    """
    Process chat messages using compact JSON translation
    
    Security is now handled by UniversalSecurityMiddleware:
    - CSRF protection validated
    - Rate limiting applied
    - Input validation performed
    - Session management enforced
    - Audit logging active
    
    This endpoint:
    1. Gets validated data from universal security middleware
    2. Converts HTML messages to compact JSON
    3. Sends context + system prompt to AI
    4. Converts AI response back to Foundry HTML
    5. Returns structured response
    
    Token efficiency: 90-93% reduction vs HTML
    """
    start_time = datetime.now()
    request_id = f"req_{start_time.strftime('%Y%m%d_%H%M%S_%f')}"
    
    try:
        # Get validated data from universal security middleware if available
        if hasattr(http_request.state, 'validated_body') and http_request.state.validated_body:
            # Use middleware-validated data for enhanced security
            validated_request = http_request.state.validated_body
            messages = validated_request.get('messages', request.messages)
            user_message = validated_request.get('user_message', request.user_message)
            settings = validated_request.get('settings', request.settings)
            logger.info(f"Processing chat request {request_id} with middleware-validated data")
        else:
            # Fallback to original request data (should not happen with proper middleware)
            messages = request.messages
            user_message = request.user_message
            settings = request.settings
            logger.info(f"Processing chat request {request_id} with original request data")
        
        logger.info(f"Processing chat request {request_id} with {len(messages)} messages")
        
        # Step 1: Convert HTML messages to compact JSON
        logger.info(f"DEBUG: Raw frontend messages received: {messages}")
        processed_messages = processor.process_message_list(messages)
        logger.info(f"DEBUG: Processed messages to compact JSON: {processed_messages}")
        
        # Step 2: Prepare system prompt and context
        system_prompt = processor.generate_system_prompt()
        
        # Step 3: Call AI API
        try:
            # Convert processed messages to JSON string for AI context
            import json
            compact_json_context = json.dumps(processed_messages, indent=2)
            
            # Add user message if provided to the context
            if user_message:
                user_message_obj = {
                    "t": "pl",
                    "s": "User",
                    "c": user_message
                }
                # Add to the context
                if isinstance(processed_messages, list):
                    processed_messages.append(user_message_obj)
                    compact_json_context = json.dumps(processed_messages, indent=2)
            
            # Prepare messages for LLM with compact JSON context
            ai_messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Chat Context (Compact JSON Format):\n{compact_json_context}\n\nPlease respond to this conversation as an AI assistant for tabletop RPGs. If you need to generate game mechanics, use the compact JSON format specified in the system prompt."}
            ]
            
            # Use validated settings or fallback to request parameters
            if not settings:
                # Fallback settings for backward compatibility
                settings = {
                    'general llm provider': 'openai',
                    'general llm model': 'gpt-3.5-turbo',
                    'general llm base url': None,
                    'general llm timeout': 30,
                    'general llm max retries': 3,
                    'general llm custom headers': None
                }
            
            # DEBUG: Log the full prompt being sent
            logger.info(f"DEBUG: System prompt being sent:\n{system_prompt}")
            logger.info(f"DEBUG: Conversation context being sent:\n{compact_json_context}")
            
            ai_response_data = await ai_service.process_compact_context(
                processed_messages=processed_messages,
                system_prompt=system_prompt,
                settings=settings
            )
            
            ai_response = ai_response_data.get("response", "")
            tokens_used = ai_response_data.get("tokens_used", 0)
            
            # DEBUG: Log the full response received
            logger.info(f"DEBUG: Raw AI response received:\n{ai_response}")
            
        except Exception as e:
            logger.error(f"AI API call failed: {e}")
            # Fallback response
            ai_response = "I apologize, but I'm having trouble processing your request right now. Please try again."
            tokens_used = 0
        
        # Step 4: Process AI response (convert any compact JSON to HTML)
        try:
            # Try to extract compact JSON from AI response
            # Look for JSON blocks in the response
            import re
            json_pattern = r'\{[^{}]*"t"\s*:\s*"[^"]*"[^{}]*\}'
            json_matches = re.findall(json_pattern, ai_response, re.DOTALL)
            
            if json_matches:
                # Process each JSON block to HTML
                html_parts = []
                remaining_text = ai_response
                
                for json_str in json_matches:
                    # Convert JSON to HTML
                    try:
                        json_data = json.loads(json_str)
                        html_part = processor.compact_json_to_html(json_data)
                        html_parts.append(html_part)
                        
                        # Remove this JSON from remaining text
                        remaining_text = remaining_text.replace(json_str, "", 1)
                    except json.JSONDecodeError:
                        # Invalid JSON, keep as text
                        continue
                
                # Combine HTML parts with remaining text
                final_response = remaining_text + "\n".join(html_parts)
            else:
                # No JSON found, return as plain text in player chat format
                final_response = f'<div class="chat-message player-chat"><div class="message-content"><p>{ai_response.replace(chr(10), "<br>")}</p></div></div>'
                
        except Exception as e:
            logger.error(f"Error processing AI response: {e}")
            # Fallback: wrap response in basic chat message
            final_response = f'<div class="chat-message player-chat"><div class="message-content"><p>{ai_response.replace(chr(10), "<br>")}</p></div></div>'
        
        # Calculate processing time
        processing_time = (datetime.now() - start_time).total_seconds()
        
        logger.info(f"Request {request_id} completed in {processing_time:.2f}s, {tokens_used} tokens used")
        
        return MessageResponse(
            response=final_response,
            processed_context=processed_messages,
            tokens_used=tokens_used,
            processing_time=processing_time
        )
        
    except Exception as e:
        logger.error(f"Error processing chat request {request_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error during chat processing: {str(e)}"
        )

@router.get("/process_chat/status/{request_id}", response_model=ProcessingStatus)
async def get_processing_status(request_id: str):
    """
    Get processing status for a request
    
    This endpoint provides real-time status updates for long-running
    chat processing requests, enabling frontend visual indicators.
    """
    if request_id not in processing_status:
        return ProcessingStatus(
            status="not_found",
            message="Request not found or expired",
            timestamp=datetime.now().isoformat()
        )
    
    return processing_status[request_id]

@router.post("/process_chat/validate")
async def validate_messages(messages: List[Union[str, FrontendMessage]]):
    """
    Validate HTML messages for processing
    
    This endpoint checks if messages can be properly processed
    by the chat context processor, helping frontend validate input.
    
    Accepts both HTML strings and frontend message objects for flexibility.
    """
    results = []
    
    for i, message in enumerate(messages):
        try:
            # Extract HTML content based on message type
            if isinstance(message, str):
                # Plain HTML string
                html_content = message
                sender = "Unknown"
                timestamp = ""
            elif isinstance(message, FrontendMessage):
                # Frontend message object
                html_content = message.content
                sender = message.sender
                timestamp = message.timestamp or ""
            else:
                # Unexpected type
                results.append({
                    "index": i,
                    "valid": False,
                    "type": "error",
                    "message": f"Invalid message type: {type(message)}"
                })
                continue
            
            # Try to process the HTML content
            compact = processor.html_to_compact_json(html_content)
            
            # Check if we can convert it back
            html = processor.compact_json_to_html(compact)
            
            # Enhance validation with metadata
            validation_result = {
                "index": i,
                "valid": True,
                "type": compact.get('t', 'unknown'),
                "sender": sender,
                "timestamp": timestamp,
                "compact_format": compact,
                "message": "Valid message"
            }
            
            results.append(validation_result)
            
        except Exception as e:
            results.append({
                "index": i,
                "valid": False,
                "type": "error",
                "sender": getattr(message, 'sender', 'Unknown') if hasattr(message, 'sender') else "Unknown",
                "message": f"Invalid message: {str(e)}"
            })
    
    return {"validation_results": results}

@router.get("/process_chat/schemas")
async def get_schemas():
    """
    Get compact JSON schemas for frontend reference
    
    This endpoint provides the current schemas and type codes
    that the processor uses, enabling frontend integration.
    """
    return {
        "type_codes": processor.TYPE_CODES,
        "reverse_type_codes": processor.REVERSE_TYPE_CODES,
        "schemas": {
            "dice_roll": {"t": "dr", "f": "formula", "r": [1, 2, 3], "tt": 6},
            "player_chat": {"t": "pl", "s": "speaker", "c": "content"},
            "attack_roll": {"t": "ar", "af": "attack_formula", "at": 15, "df": "damage_formula", "dt": 8, "s": "speaker"},
            "saving_throw": {"t": "sv", "st": "Dexterity", "f": "1d20+3", "tt": 16, "dc": 14, "succ": True, "s": "speaker"},
            "whisper": {"t": "wp", "s": "speaker", "c": "content", "tg": ["target1", "target2"]},
            "gm_message": {"t": "gm", "c": "content"},
            "chat_card": {"t": "cc", "ct": "spell", "n": "Fireball", "d": "description", "a": ["cast", "damage"]},
            "condition_card": {"t": "cd", "cn": "Prone", "d": "description"},
            "table_result": {"t": "tr", "r": 42, "res": "result", "tn": "table_name"}
        },
        "system_prompt": processor.generate_system_prompt()
    }

# Helper functions for status management
def set_processing_status(request_id: str, status: str, message: str):
    """Set processing status for a request"""
    processing_status[request_id] = ProcessingStatus(
        status=status,
        message=message,
        timestamp=datetime.now().isoformat()
    )

def cleanup_old_status():
    """Clean up old processing status entries"""
    current_time = datetime.now()
    expired_ids = []
    
    for request_id, status in processing_status.items():
        status_time = datetime.fromisoformat(status.timestamp)
        # Remove entries older than 5 minutes
        if (current_time - status_time).total_seconds() > 300:
            expired_ids.append(request_id)
    
    for request_id in expired_ids:
        del processing_status[request_id]

# Test endpoint
@router.get("/process_chat/test")
async def test_endpoint():
    """Test endpoint to verify functionality"""
    return {
        "status": "operational",
        "processor_loaded": True,
        "provider_manager_loaded": True,
        "message": "Process chat endpoint is ready"
    }
