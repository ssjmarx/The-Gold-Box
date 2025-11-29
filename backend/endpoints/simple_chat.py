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
            
            # Step 4.1: Validate data quality before sending to AI
            from server.ai_prompt_validator import validate_ai_prompt_context
            
            # Separate chat messages and rolls from message context
            chat_messages = []
            rolls = []
            
            for msg in message_context:
                if msg.get('t') == 'cm':
                    chat_messages.append(msg)
                elif msg.get('t') == 'dr':
                    rolls.append(msg)
            
            validation_result = validate_ai_prompt_context(
                messages=chat_messages,
                rolls=rolls,
                scene_data=None,  # Simple chat doesn't use scene data
                strict_mode=False  # Use lenient mode for now
            )
            
            # Check if data quality is acceptable (more lenient threshold)
            if not validation_result.get('should_block_prompt', False):  # Fixed logic - should_block_prompt=True means block
                # Data quality is acceptable, proceed with AI request
                print(f"=== AI PROMPT VALIDATION PASSED ===")
                print(f"Quality Score: {validation_result.get('data_quality_score', 0):.1f}%")
                print(f"Context: {validation_result.get('context_completeness', 0):.1f}% complete")
                print(f"Freshness: {validation_result.get('data_freshness', 0):.1f}% fresh")
                
                # Process message context with universal provider config
                return await ai_service.process_message_context(message_context, settings)
            else:
                # Data quality is unacceptable, block and return error
                print(f"=== AI PROMPT VALIDATION BLOCKED ===")
                print(f"Quality Score: {validation_result.get('data_quality_score', 0):.1f}% (below threshold)")
                print(f"Context: {validation_result.get('context_completeness', 0):.1f}% complete")
                print(f"Freshness: {validation_result.get('data_freshness', 0):.1f}% fresh")
                print(f"Errors: {len(validation_result.get('errors', []))}")
                print(f"Warnings: {len(validation_result.get('warnings', []))}")
                
                # Return structured error response
                block_message = ""
                validator_instance = None
                try:
                    from server.ai_prompt_validator import AIPromptValidator
                    validator_instance = AIPromptValidator(strict_mode=False)
                    validator_instance.validation_results = validation_result
                    block_message = validator_instance.get_block_message()
                except ImportError:
                    block_message = f"🚫 **AI Prompt Blocked - Data Quality Issues**\n\n**Quality Score:** {validation_result.get('data_quality_score', 0):.1f}% (below acceptable threshold)\n\n**Context Completeness:** {validation_result.get('context_completeness', 0):.1f}%\n\n**Data Freshness:** {validation_result.get('data_freshness', 0):.1f}%\n\n**Errors:**\n"
                    for error in validation_result.get('errors', [])[:3]:
                        block_message += f"• {error}\n"
                    block_message += f"**Warnings:**\n"
                    for warning in validation_result.get('warnings', [])[:2]:
                        block_message += f"• {warning}\n"
                
                return {
                    'success': False,
                    'error': 'AI prompt blocked due to data quality issues',
                    'details': {
                        'quality_score': validation_result.get('data_quality_score', 0),
                        'context_completeness': validation_result.get('context_completeness', 0),
                        'data_freshness': validation_result.get('data_freshness', 0),
                        'errors': validation_result.get('errors', []),
                        'warnings': validation_result.get('warnings', []),
                        'block_message': block_message,
                        'recommendations': validation_result.get('recommendations', [])
                    },
                    'metadata': {
                        'validation_timestamp': validation_result.get('validation_timestamp'),
                        'data_source': 'simple_chat_validation'
                    }
                }
        
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
