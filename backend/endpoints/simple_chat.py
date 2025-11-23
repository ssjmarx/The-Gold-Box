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

async def process_simple_chat(provider_id: str = None, model: str = None, prompt: str = None, message_context: list = None, base_url: str = None, api_version: str = None, timeout: int = 30, max_retries: int = 3, custom_headers: str = None, **kwargs) -> Dict[str, Any]:
    """
    Main entry point for simple chat processing with message context support
    
    Args:
        provider_id: Provider identifier (e.g., 'openai', 'anthropic', 'custom_provider')
        model: Model name to use (optional, uses provider default if None)
        prompt: The prompt to process (legacy mode)
        message_context: List of message objects from frontend
        base_url: Base URL for custom provider endpoints
        api_version: API version for provider
        timeout: Request timeout in seconds
        max_retries: Maximum retry attempts
        custom_headers: Custom headers in JSON format
        **kwargs: Additional parameters
        
    Returns:
        Response dictionary with success/error info
    """
    try:
        # Initialize AI service
        provider_manager = ProviderManager()
        ai_service = AIService(provider_manager)
        
        # Handle message context mode
        if message_context:
            # Build settings object for AI service
            settings = {
                'general llm provider': provider_id,
                'general llm model': model,
                'general llm base url': base_url,
                'general llm timeout': timeout,
                'general llm max retries': max_retries,
                'general llm custom headers': custom_headers
            }
            
            # Process message context
            return await ai_service.process_message_context(message_context, settings)
        
        # Legacy single prompt mode
        elif prompt:
            # For legacy prompt mode, create a simple message context
            message_context = [{'sender': 'User', 'content': prompt}]
            
            # Build settings object for AI service
            settings = {
                'general llm provider': provider_id,
                'general llm model': model,
                'general llm base url': base_url,
                'general llm timeout': timeout,
                'general llm max retries': max_retries,
                'general llm custom headers': custom_headers
            }
            
            # Process as message context
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
    """Test the simple chat functionality"""
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
