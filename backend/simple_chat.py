#!/usr/bin/env python3
"""
Simple Chat Module for OpenCode-compatible APIs
Handles Z.AI and other OpenCode-compatible AI services
"""

import os
import asyncio
import litellm
from typing import Dict, Any, Optional

class OpenCodeService:
    """
    OpenCode-compatible AI service handler
    Supports Z.AI and other OpenCode-compatible APIs
    """
    
    def __init__(self, api_key: str, base_url: str = "https://api.z.ai/api/coding/paas/v4", model: str = "openai/glm-4.6"):
        """
        Initialize OpenCode service
        
        Args:
            api_key: API key for the service
            base_url: Base URL for the OpenCode-compatible API
            model: Model name to use
        """
        self.api_key = api_key
        self.base_url = base_url
        self.model = model
    
    async def process_prompt(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """
        Process a prompt using OpenCode-compatible API
        
        Args:
            prompt: The prompt to process
            **kwargs: Additional parameters (temperature, max_tokens, etc.)
            
        Returns:
            Dictionary with response data and metadata
        """
        try:
            print(f"🔄 Sending to OpenCode API: {self.base_url} with model: {self.model}")
            print(f"📤 Prompt: {prompt[:100]}{'...' if len(prompt) > 100 else ''}")
            
            # Use LiteLLM to call OpenCode-compatible API
            response = await litellm.acompletion(
                model=self.model,
                messages=[
                    {"role": "user", "content": prompt}
                ],
                api_base=self.base_url,
                api_key=self.api_key,
                temperature=kwargs.get('temperature', 0.1),
                max_tokens=kwargs.get('max_tokens', None),  # No limit by default
                stream=False  # Stream internally but wait for complete response
            )
            
            if response and response.choices:
                print("✅ SUCCESS: OpenCode API responded!")
                
                # DEBUG: Print actual response content
                # print(f"🔍 DEBUG: Full response: {response}")
                # print(f"🔍 DEBUG: Response dict: {response.model_dump() if hasattr(response, 'model_dump') else str(response)}")
                
                # Extract the content
                content = ""
                choice = response.choices[0]
                
                # print(f"🔍 DEBUG: Choice: {choice}")
                # print(f"🔍 DEBUG: Choice dict: {choice.model_dump() if hasattr(choice, 'model_dump') else str(choice)}")
                
                # Handle both content and reasoning_content fields
                if hasattr(choice, 'message') and choice.message:
                    # print(f"🔍 DEBUG: Message: {choice.message}")
                    # print(f"🔍 DEBUG: Message dict: {choice.message.model_dump() if hasattr(choice.message, 'model_dump') else str(choice.message)}")
                    
                    content = choice.message.content or ""
                    # print(f"📥 Found message content: '{content}'")
                    # print(f"📥 Content length: {len(content) if content else 0}")
                    # print(f"📥 Content is None: {content is None}")
                    # print(f"📥 Content is empty string: {content == ''}")
                    
                    # Debug: Show when content is successfully extracted
                    if content and content.strip():
                        # print(f"🎯 SUCCESS: API connection successful!")
                        # print(f"📝 Content: '{content.strip()}'")
                        pass  # Placeholder for when content is successfully extracted
                    
                    # If content is empty, check for reasoning_content (but we'll ignore it per requirements)
                    if not content and hasattr(choice.message, 'reasoning_content') and choice.message.reasoning_content:
                        print("📥 Reasoning content found but ignoring per requirements")
                        print(f"🔍 DEBUG: Reasoning content: '{choice.message.reasoning_content[:100]}...'")
                        # We ignore reasoning_content as per user requirements
                    
                    # Additional content extraction attempts if content is still empty
                    if not content:
                        # Try to get content from other possible fields
                        if hasattr(choice, 'text'):
                            content = choice.text or ""
                            print(f"📥 Found text content: '{content}'")
                        elif hasattr(response, 'content'):
                            content = response.content or ""
                            print(f"📥 Found response content: '{content}'")
                
                # Final fallback - try to extract from raw response if available
                if not content:
                    print(f"🔍 DEBUG: Content still empty, trying fallback extraction methods")
                    try:
                        # Try to access raw response data
                        if hasattr(response, '_hidden_params') and response._hidden_params.get('response'):
                            raw_response = response._hidden_params['response']
                            print(f"🔍 DEBUG: Raw response type: {type(raw_response)}")
                            print(f"🔍 DEBUG: Raw response: {str(raw_response)[:500]}...")
                    except Exception as e:
                        print(f"🔍 DEBUG: Could not access raw response: {e}")
                
                # Extract metadata
                metadata = {
                    'model': self.model,
                    'api_base': self.base_url,
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
            print(f"❌ ERROR: OpenCode API failed: {str(e)}")
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

def get_opencode_service(service_key: str, api_key: str) -> Optional[OpenCodeService]:
    """
    Get OpenCode service instance for the specified service
    
    Args:
        service_key: Key identifying the service (e.g., 'z_ai')
        api_key: API key for the service
        
    Returns:
        OpenCodeService instance or None if service not found
    """
    if service_key in OPENCODE_ENDPOINTS:
        config = OPENCODE_ENDPOINTS[service_key]
        return OpenCodeService(
            api_key=api_key,
            base_url=config['base_url'],
            model=config['model']
        )
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

async def process_simple_chat(service_key: str, prompt: str = None, message_context: list = None, **kwargs) -> Dict[str, Any]:
    """
    Main entry point for simple chat processing with message context support
    
    Args:
        service_key: Key identifying which OpenCode service to use
        prompt: The prompt to process (legacy mode)
        message_context: List of message objects from frontend
        **kwargs: Additional parameters
        
    Returns:
        Response dictionary with success/error info
    """
    # Get API key from environment
    api_key = os.environ.get('GOLD_BOX_OPENCODE_COMPATIBLE_API_KEY', '')
    
    if not api_key:
        return {
            'success': False,
            'error': 'OpenCode Compatible API key not configured'
        }
    
    # Get service instance
    service = get_opencode_service(service_key, api_key)
    if not service:
        return {
            'success': False,
            'error': f'Unknown OpenCode service: {service_key}'
        }
    
    # Handle message context mode
    if message_context:
        context_string = process_message_context(message_context)
        full_prompt = f"Chat context:\n{context_string}\n\nNew request: Please respond naturally to the conversation as an AI assistant for tabletop RPGs."
        print(f"🔄 Processing message context with {len(message_context)} messages")
        print(f"📝 Context length: {len(context_string)} characters")
        return await service.process_prompt(full_prompt, **kwargs)
    
    # Legacy single prompt mode
    elif prompt:
        return await service.process_prompt(prompt, **kwargs)
    
    else:
        return {
            'success': False,
            'error': 'No prompt or message context provided'
        }

# Test function (can be called from z_ai_test.py style testing)
async def test_opencode_service():
    """Test the OpenCode service functionality"""
    print("=" * 60)
    print("🤖 OpenCode Service Test")
    print("=" * 60)
    
    # Test with Z.AI
    result = await process_simple_chat(
        service_key='z_ai',
        prompt="I search for room, rolling a 16 on a die with a +3 modifier for a total of 19."
    )
    
    if result['success']:
        print(f"✅ SUCCESS: {result['content'][:200]}{'...' if len(result['content']) > 200 else ''}")
        print(f"📊 Usage: {result['metadata'].get('usage', 'N/A')}")
    else:
        print(f"❌ FAILED: {result['error']}")
    
    print("=" * 60)
    return result['success']

if __name__ == "__main__":
    # Run test if executed directly
    asyncio.run(test_opencode_service())
