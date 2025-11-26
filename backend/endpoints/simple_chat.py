#!/usr/bin/env python3
"""
Simple Chat Module for The Gold Box
Handles all AI providers via unified AI service
"""

import os
import asyncio
from typing import Dict, Any, Optional, List
from server.provider_manager import ProviderManager
from server.ai_service import AIService
from server.universal_settings import extract_universal_settings, get_provider_config

async def process_simple_chat(request_data: Dict[str, Any] = None, provider_id: str = None, model: str = None, prompt: str = None, message_context: list = None, base_url: str = None, api_version: str = None, timeout: int = 30, max_retries: int = 3, custom_headers: str = None, **kwargs) -> Dict[str, Any]:
    """
    Main entry point for simple chat processing with message context support
    
    Args:
        request_data: Request data from middleware (contains validated settings) - PRIMARY METHOD
        provider_id: Provider identifier (legacy, for backward compatibility)
        model: Model name to use (legacy, for backward compatibility)
        prompt: The prompt to process (legacy mode)
        message_context: List of message objects from frontend
        base_url: Base URL for custom provider endpoints (legacy, for backward compatibility)
        api_version: API version for provider (legacy, for backward compatibility)
        timeout: Request timeout in seconds (legacy, for backward compatibility)
        max_retries: Maximum retry attempts (legacy, for backward compatibility)
        custom_headers: Custom headers in JSON format (legacy, for backward compatibility)
        **kwargs: Additional parameters
        
    Returns:
        Response dictionary with success/error info
    """
    try:
        # Initialize AI service
        provider_manager = ProviderManager()
        ai_service = AIService(provider_manager)
        
        # Extract universal settings if request_data is provided (NEW PRIMARY METHOD)
        if request_data:
            settings = extract_universal_settings(request_data, "simple_chat")
            print(f"DEBUG simple_chat: Using universal settings: {settings}")
            
            # Extract provider config from universal settings
            provider_config = get_provider_config(settings, use_tactical=False)
            print(f"DEBUG simple_chat: Extracted provider config: {provider_config}")
        else:
            # Fallback to stored settings when no request_data provided
            print("DEBUG simple_chat: No request_data provided, retrieving stored settings")
            try:
                from server import settings_manager
                stored_settings = settings_manager.get_settings()
                print(f"DEBUG simple_chat: Retrieved stored settings: {stored_settings}")
                
                if stored_settings:
                    request_data_for_settings = {
                        'settings': stored_settings
                    }
                    settings = extract_universal_settings(request_data_for_settings, "simple_chat")
                    print(f"DEBUG simple_chat: Using retrieved stored settings: {settings}")
                else:
                    print("DEBUG simple_chat: No stored settings found, using defaults")
                    settings = extract_universal_settings({}, "simple_chat")
                    
                # Extract provider config from settings
                provider_config = get_provider_config(settings, use_tactical=False)
                print(f"DEBUG simple_chat: Extracted provider config: {provider_config}")
                
            except ImportError as e:
                print(f"DEBUG simple_chat: Failed to import settings_manager: {e}")
                # Final fallback to defaults
                settings = extract_universal_settings({}, "simple_chat")
                provider_config = get_provider_config(settings, use_tactical=False)
                print(f"DEBUG simple_chat: Using default settings: {settings}")
            
            # Legacy mode fallback (should not happen with updated endpoint)
            if not settings or ('general llm provider' not in str(settings) and 'general llm model' not in str(settings)):
                print("DEBUG simple_chat: Settings still None after fallback, building legacy settings")
                settings = {
                    'general llm provider': provider_id,
                    'general llm model': model,
                    'general llm base url': base_url,
                    'general llm timeout': timeout,
                    'general llm max retries': max_retries,
                    'general llm custom headers': custom_headers
                }
                print(f"DEBUG simple_chat: Built settings object (legacy): {settings}")
                
                # Extract provider config from manually built settings
                provider_config = get_provider_config(settings, use_tactical=False)
                print(f"DEBUG simple_chat: Extracted provider config (legacy): {provider_config}")
        
        # Handle message context mode
        if message_context:
            # DEBUG: Log what we're receiving
            print(f"DEBUG simple_chat: message_context keys: {list(message_context[0].keys()) if message_context else 'None'}")
            
            # Process message context with universal provider config
            return await ai_service.process_message_context(message_context, settings)
        
        # Legacy single prompt mode
        elif prompt:
            # DEBUG: Log what we're receiving
            print(f"DEBUG simple_chat: Processing legacy prompt mode")
            
            # For legacy prompt mode, create a simple message context
            message_context = [{'sender': 'User', 'content': prompt}]
            
            # Process as message context with universal settings
            return await ai_service.process_message_context(message_context, settings)
        
        else:
            return {
                'success': False,
                'error': 'No prompt or message context provided'
            }
            
    except Exception as e:
        return {
            'success': False,
            'error': f'Error in simple chat processing: {str(e)}'
        }

# Legacy compatibility functions
def process_message_context(messages):
    """
    Process chat messages into chronological context for AI
    messages are in chronological order (oldest first), so we join as-is
    """
    import re
    
    context_parts = []
    
    # messages is already chronological from frontend collectChatMessages
    for msg in messages:
        content = msg['content']
        sender = msg['sender']
        
        # HTML cleanup while preserving game structure
        # Remove delete buttons and control elements but keep dice rolls and formatting
        content = re.sub(r'<a[^>]*class="[^"]*delete[^"]*"[^>]*>.*?</a>', '', content)
        content = re.sub(r'<a[^>]*class="[^"]*chat-control[^"]*"[^>]*>.*?</a>', '', content)
        content = re.sub(r'<[^>]*data-[^>]*>', '', content)
        content = re.sub(r'<[^>]*data-action="[^"]*"[^>]*>', '', content)
        
        # Preserve: dice rolls, formatting, sender names, etc.
        context_parts.append(f"{sender}: {content}")
    
    context_string = '\n'.join(context_parts)  # Oldest first, newest last
    
    return context_string

# Test function (can be called from z_ai_test.py style testing)
async def test_simple_chat():
    """Test simple chat functionality"""
    print("=" * 60)
    print("Simple Chat Service Test")
    print("=" * 60)
    
    # Test with message context
    message_context = [
        {'sender': 'Player 1', 'content': 'I search the room for traps.'},
        {'sender': 'GM', 'content': 'You find a hidden door!'}
    ]
    
    result = await process_simple_chat(
        provider_id='openrouter',
        model='openai/gpt-3.5-turbo',
        message_context=message_context
    )
    
    if result['success']:
        print(f"SUCCESS: {result['response'][:200]}{'...' if len(result['response']) > 200 else ''}")
        print(f"Tokens used: {result.get('tokens_used', 0)}")
    else:
        print(f"FAILED: {result['error']}")
    
    print("=" * 60)
    return result['success']

if __name__ == "__main__":
    # Run test if executed directly
    asyncio.run(test_simple_chat())
