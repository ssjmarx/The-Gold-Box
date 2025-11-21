#!/usr/bin/env python3
"""
Provider-Agnostic Chat Module for The Gold Box
Handles all AI providers via LiteLLM integration
"""

import os
import asyncio
import litellm
from typing import Dict, Any, Optional, List
from provider_manager import ProviderManager

class ProviderAgnosticService:
    """
    Provider-agnostic AI service handler
    Supports any provider through LiteLLM integration
    """
    
    def __init__(self, provider_manager: ProviderManager):
        """
        Initialize provider-agnostic service
        
        Args:
            provider_manager: ProviderManager instance for provider access
        """
        self.provider_manager = provider_manager
    
    async def process_prompt(self, provider_id: str, model: str, prompt: str, timeout: int = 30, max_retries: int = 3, custom_config: Dict[str, Any] = None, **kwargs) -> Dict[str, Any]:
        """
        Process a prompt using any configured provider via LiteLLM
        
        Args:
            provider_id: Provider identifier (e.g., 'openai', 'anthropic', 'custom_provider')
            model: Model name to use
            prompt: The prompt to process
            timeout: Request timeout in seconds
            max_retries: Maximum retry attempts
            **kwargs: Additional parameters (temperature, max_tokens, etc.)
            
        Returns:
            Dictionary with response data and metadata
        """
        try:
            # Get provider configuration
            provider = self.provider_manager.get_provider(provider_id)
            if not provider:
                return {
                    'success': False,
                    'error': f'Provider "{provider_id}" not found'
                }
            
            # Get API key from environment
            api_key = os.environ.get(f'{provider_id.upper()}_API_KEY', '')
            if not api_key:
                return {
                    'success': False,
                    'error': f'API key not configured for provider "{provider_id}"'
                }
            
            # Configure provider in LiteLLM if it's custom
            if provider.get('is_custom', False):
                success = self.provider_manager.configure_litellm_provider(provider_id, api_key, provider)
                if not success:
                    return {
                        'success': False,
                        'error': f'Failed to configure custom provider "{provider_id}"'
                    }
            
            print(f"Sending to {provider.get('name', provider_id)} API: {provider_id} with model: {model}")
            # print(f"Prompt: {prompt[:100]}{'...' if len(prompt) > 100 else ''}")
            
            # Prepare LiteLLM completion parameters
            completion_params = {
                "model": model,
                "messages": [
                    {"role": "user", "content": prompt}
                ],
                "api_key": api_key,
                "temperature": kwargs.get('temperature', 0.1),
                "max_tokens": kwargs.get('max_tokens', None),  # No limit by default
                "stream": False  # Stream internally but wait for complete response
            }
            
            # Apply custom configuration if provided
            if custom_config:
                if 'base_url' in custom_config:
                    completion_params['api_base'] = custom_config['base_url']
                    # print(f"Applied custom base URL: {custom_config['base_url']}")
                
                if 'headers' in custom_config:
                    completion_params['custom_llm_provider'] = "openai"  # Use OpenAI format for custom headers
                    completion_params['headers'] = custom_config['headers']
                    # print(f"Applied custom headers: {list(custom_config['headers'].keys())}")
            
            # Use LiteLLM to call any provider API
            response = await litellm.acompletion(**completion_params)
            
            if response and response.choices:
                print("SUCCESS: Provider API responded!")
                
                # Extract the content
                content = ""
                choice = response.choices[0]
                
                # Handle both content and reasoning_content fields
                if hasattr(choice, 'message') and choice.message:
                    content = choice.message.content or ""
                    
                    # If content is empty, check for reasoning_content (but we'll ignore it per requirements)
                    if not content and hasattr(choice.message, 'reasoning_content') and choice.message.reasoning_content:
                        # print("Reasoning content found but ignoring per requirements")
                        pass
                    
                    # Additional content extraction attempts if content is still empty
                    if not content:
                        # Try to get content from other possible fields
                        if hasattr(choice, 'text'):
                            content = choice.text or ""
                        elif hasattr(response, 'content'):
                            content = response.content or ""
                
                # Final fallback - try to extract from raw response if available
                if not content:
                    # print(f"DEBUG: Content still empty, trying fallback extraction methods")
                    try:
                        # Try to access raw response data
                        if hasattr(response, '_hidden_params') and response._hidden_params.get('response'):
                            raw_response = response._hidden_params['response']
                            # print(f"DEBUG: Raw response type: {type(raw_response)}")
                            # print(f"DEBUG: Raw response: {str(raw_response)[:500]}...")
                            pass
                    except Exception as e:
                        # print(f"DEBUG: Could not access raw response: {e}")
                        pass
                
                # Extract metadata
                metadata = {
                    'provider': provider_id,
                    'provider_name': provider.get('name', provider_id),
                    'model': model,
                    'finish_reason': getattr(choice, 'finish_reason', 'unknown'),
                    'usage': getattr(response, 'usage', None)
                }
                
                return {
                    'success': True,
                    'content': content,
                    'metadata': metadata,
                    'response_object': response
                }
            else:
                return {
                    'success': False,
                    'error': 'No response choices received from API'
                }
                
        except Exception as e:
            print(f"ERROR: Provider API failed: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }

# Default endpoints configuration for common OpenCode-compatible services
OPENCODE_ENDPOINTS = {
    'z_ai': {
        'base_url': 'https://api.z.ai/api/coding/paas/v4',
        'model': 'openai/glm-4.6',
        'name': 'Z.AI'
    },
    # Can add more OpenCode-compatible services here
    # 'other_service': {
    #     'base_url': 'https://api.other-service.com/v1',
    #     'model': 'openai/custom-model',
    #     'name': 'Other Service'
    # }
}

def get_opencode_service(service_key: str, api_key: str) -> Optional[ProviderAgnosticService]:
    """
    Get provider-agnostic service instance (legacy function for compatibility)
    
    Args:
        service_key: Key identifying the service (e.g., 'z_ai')
        api_key: API key for the service
        
    Returns:
        ProviderAgnosticService instance or None if service not found
    """
    if service_key in OPENCODE_ENDPOINTS:
        provider_manager = ProviderManager()
        return ProviderAgnosticService(provider_manager)
    return None

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

async def process_simple_chat(provider_id: str = None, model: str = None, prompt: str = None, message_context: list = None, base_url: str = None, api_version: str = None, timeout: int = 30, max_retries: int = 3, custom_headers: str = None, **kwargs) -> Dict[str, Any]:
    """
    Main entry point for provider-agnostic chat processing with message context support
    
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
    # Initialize provider manager
    provider_manager = ProviderManager()
    
    # Get provider configuration
    provider = provider_manager.get_provider(provider_id)
    if not provider:
        return {
            'success': False,
            'error': f'Provider "{provider_id}" not found'
        }
    
    # Use provider's default model if none specified
    if not model:
        models = provider.get('models', [])
        if models:
            model = models[0]  # Use first available model
        else:
            model = 'default'
    
    # Skip model-provider validation - let LiteLLM handle it
    # This allows users to use any model they want through LiteLLM
    # print(f"Skipping model validation - letting LiteLLM handle model '{model}' for provider '{provider_id}'")
    
    # Get API key from environment
    api_key = os.environ.get(f'{provider_id.upper()}_API_KEY', '')
    
    if not api_key:
        return {
            'success': False,
            'error': f'API key not configured for provider "{provider_id}"'
        }
    
    # Configure custom provider settings from frontend
    custom_config = {}
    if base_url or custom_headers:
        # Prepare custom configuration for LiteLLM
        if base_url:
            custom_config['base_url'] = base_url
            # print(f"Using custom base URL: {base_url}")
        if custom_headers:
            try:
                import json
                headers_dict = json.loads(custom_headers)
                custom_config['headers'] = headers_dict
                # print(f"Using custom headers: {list(headers_dict.keys())}")
            except json.JSONDecodeError as e:
                print(f"Invalid custom headers JSON: {e}")
    
    # Initialize provider-agnostic service
    service = ProviderAgnosticService(provider_manager)
    
    # Handle message context mode
    if message_context:
        context_string = process_message_context(message_context)
        full_prompt = f"Chat context:\n{context_string}\n\nNew request: Please respond naturally to the conversation as an AI assistant for tabletop RPGs."
        # print(f"Processing message context with {len(message_context)} messages")
        # print(f"Context length: {len(context_string)} characters")
        return await service.process_prompt(provider_id, model, full_prompt, timeout=timeout, max_retries=max_retries, custom_config=custom_config, **kwargs)
    
    # Legacy single prompt mode
    elif prompt:
        return await service.process_prompt(provider_id, model, prompt, timeout=timeout, max_retries=max_retries, custom_config=custom_config, **kwargs)
    
    else:
        return {
            'success': False,
            'error': 'No prompt or message context provided'
        }

# Test function (can be called from z_ai_test.py style testing)
async def test_opencode_service():
    """Test the OpenCode service functionality"""
    print("=" * 60)
    print("OpenCode Service Test")
    print("=" * 60)
    
    # Test with Z.AI
    result = await process_simple_chat(
        service_key='z_ai',
        prompt="I search for room, rolling a 16 on a die with a +3 modifier for a total of 19."
    )
    
    if result['success']:
        print(f"SUCCESS: {result['content'][:200]}{'...' if len(result['content']) > 200 else ''}")
        print(f"Usage: {result['metadata'].get('usage', 'N/A')}")
    else:
        print(f"FAILED: {result['error']}")
    
    print("=" * 60)
    return result['success']

if __name__ == "__main__":
    # Run test if executed directly
    asyncio.run(test_opencode_service())
