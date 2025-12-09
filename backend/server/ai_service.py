#!/usr/bin/env python3
"""
AI Service for The Gold Box
Dedicated module for formatting AI API calls and LiteLLM interactions

Provides unified interface for both simple_chat and process_chat endpoints
"""

import os
import asyncio
import logging
import litellm
from typing import Dict, Any, Optional, List
from .provider_manager import ProviderManager
from .universal_settings import get_provider_config

logger = logging.getLogger(__name__)

class AIService:
    """
    Unified AI service for all API calls
    Handles LiteLLM interactions, formatting, and provider management
    """
    
    def __init__(self, provider_manager: ProviderManager):
        """
        Initialize AI service
        
        Args:
            provider_manager: ProviderManager instance for provider access
        """
        self.provider_manager = provider_manager
    
    async def call_ai_provider(self, messages: List[Dict[str, str]], config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Make AI call using LiteLLM with unified configuration
        
        Args:
            messages: List of messages in chat format [{'role': 'system', 'content': '...'}, ...]
            config: Provider configuration from universal settings (pre-validated)
            
        Returns:
            Dictionary with response data and metadata
        """
        try:
            # Extract from pre-validated universal settings config
            provider_id = config.get('provider')
            model = config.get('model')
            api_key = config.get('api_key')
            base_url = config.get('base_url')
            timeout = config.get('timeout', 30)
            max_retries = config.get('max_retries', 3)
            headers = config.get('headers', {})
            
            # Enhanced logging for debugging with universal settings info
            # print(f"DEBUG: AI Service called with pre-validated config")
            # print(f"DEBUG: Provider: {provider_id}, Model: {model}, Base URL: {base_url}")
            # print(f"DEBUG: Timeout: {timeout}s, Max Retries: {max_retries}")
            # print(f"DEBUG: Custom Headers: {len(headers)} headers provided")
            # print(f"DEBUG: Available environment variables: {[k for k in os.environ.keys() if 'API_KEY' in k]}")
            
            # Get provider configuration
            provider = self.provider_manager.get_provider(provider_id)
            if not provider:
                error_msg = f'Provider "{provider_id}" not found'
                print(f"ERROR: {error_msg}")
                return {
                    'success': False,
                    'error': error_msg
                }
            
            # Get API key from environment if not provided
            if not api_key:
                env_var_name = f'{provider_id.upper()}_API_KEY'
                api_key = os.environ.get(env_var_name, '')
                # print(f"DEBUG: Looking for API key in environment variable: {env_var_name}")
                # print(f"DEBUG: API key found in environment: {'Yes' if api_key else 'No'}")
                
                # If not in environment, try to load from key manager
                if not api_key:
                    # print(f"DEBUG: API key not in environment, trying key manager...")
                    try:
                        from .key_manager import MultiKeyManager
                        key_manager = MultiKeyManager()
                        # Try to load keys without password for testing
                        if key_manager.load_keys_with_password("") is True:
                            if hasattr(key_manager, 'keys_data') and key_manager.keys_data:
                                api_key = key_manager.keys_data.get(provider_id, '')
                                # print(f"DEBUG: API key found in key manager: {'Yes' if api_key else 'No'}")
                                # Set environment variable for LiteLLM
                                if api_key:
                                    os.environ[env_var_name] = api_key
                                    # print(f"DEBUG: Set {env_var_name} from key manager")
                    except Exception as e:
                        # print(f"DEBUG: Failed to load from key manager: {e}")
                        pass
            
            if not api_key:
                error_msg = f'API key not configured for provider "{provider_id}" (checked {env_var_name})'
                print(f"ERROR: {error_msg}")
                return {
                    'success': False,
                    'error': error_msg
                }
            
            # Configure provider in LiteLLM if it's custom
            if provider.get('is_custom', False):
                custom_config = {
                    'base_url': config.get('base_url'),
                    'headers': config.get('headers'),
                    'models': provider.get('models', [])
                }
                success = self.provider_manager.configure_litellm_provider(provider_id, api_key, custom_config)
                if not success:
                    return {
                        'success': False,
                        'error': f'Failed to configure custom provider "{provider_id}"'
                    }
            
            print(f"Sending to {provider.get('name', provider_id)} API: {provider_id} with model: {model}")
            
            # Prepare LiteLLM completion parameters with proper type conversion
            completion_params = {
                "model": model,
                "messages": messages,
                "api_key": api_key,
                "temperature": float(config.get('temperature', 0.1)) if config.get('temperature') is not None else 0.1,
                "max_tokens": int(config.get('max_tokens', 0)) if config.get('max_tokens') is not None else None,  # No limit by default
                "stream": False  # Stream internally but wait for complete response
            }
            
            # Apply custom configuration if provided
            if config.get('base_url'):
                completion_params['api_base'] = config['base_url']
            
            if config.get('headers'):
                completion_params['custom_llm_provider'] = "openai"  # Use OpenAI format for custom headers
                completion_params['headers'] = config['headers']
            
            # Apply timeout with proper type conversion
            timeout = int(config.get('timeout', 30)) if config.get('timeout') is not None else 30
            
            # Use LiteLLM to call any provider API
            response = await asyncio.wait_for(
                litellm.acompletion(**completion_params),
                timeout=timeout
            )
            
            if response and response.choices:
                print("SUCCESS: Provider API responded!")
                
                # Extracts content
                content = ""
                choice = response.choices[0]
                
                # Handle both content and reasoning_content fields
                if hasattr(choice, 'message') and choice.message:
                    content = choice.message.content or ""
                    
                    # If content is empty, check for reasoning_content (but we'll ignore it per requirements)
                    if not content and hasattr(choice.message, 'reasoning_content') and choice.message.reasoning_content:
                        pass
                    
                    # Additional content extraction attempts if content is still empty
                    if not content:
                        # Try to get content from other possible fields
                        if hasattr(choice, 'text'):
                            content = choice.text or ""
                        elif hasattr(response, 'content'):
                            content = response.content or ""
                
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
                    'response': content,
                    'metadata': metadata,
                    'tokens_used': getattr(response.usage, 'total_tokens', 0) if response.usage else 0,
                    'response_object': response
                }
            else:
                return {
                    'success': False,
                    'error': 'No response choices received from API'
                }
                
        except asyncio.TimeoutError:
            return {
                'success': False,
                'error': f'AI call timed out after {timeout} seconds'
            }
        except Exception as e:
            print(f"ERROR: Provider API failed: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def process_message_context(self, message_context: List[Dict], settings: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process message context for simple chat endpoint
        
        Args:
            message_context: List of message objects from frontend
            settings: Frontend settings including provider info
            
        Returns:
            Response dictionary with success/error info
        """
        try:
            # Use universal settings to get provider config
            provider_config = get_provider_config(settings, use_tactical=False)
            
            # Extract values from pre-validated provider config
            provider_id = provider_config['provider']
            model = provider_config['model']
            base_url = provider_config['base_url']
            custom_headers = provider_config.get('custom_headers')
            timeout = provider_config['timeout']
            max_retries = provider_config['max_retries']
            
            # Use provider's default model if none specified
            if not model:
                provider = self.provider_manager.get_provider(provider_id)
                if provider:
                    models = provider.get('models', [])
                    if models:
                        model = models[0]
                else:
                    model = 'default'
            
            # Process message context into chronological string
            import re
            context_parts = []
            
            for msg in message_context:
                content = msg['content']
                sender = msg['sender']
                
                # HTML cleanup while preserving game structure
                content = re.sub(r'<a[^>]*class="[^"]*delete[^"]*"[^>]*>.*?</a>', '', content)
                content = re.sub(r'<a[^>]*class="[^"]*chat-control[^"]*"[^>]*>.*?</a>', '', content)
                content = re.sub(r'<[^>]*data-[^>]*>', '', content)
                content = re.sub(r'<[^>]*data-action="[^"]*"[^>]*>', '', content)
                
                # Preserve: dice rolls, formatting, sender names, etc.
                context_parts.append(f"{sender}: {content}")
            
            context_string = '\n'.join(context_parts)
            
            # Build prompt for RPG assistant
            prompt = f"Chat context:\n{context_string}\n\nPlease respond naturally to this conversation as an AI assistant for tabletop RPGs."
            
            # Prepare messages for AI
            ai_messages = [
                {"role": "user", "content": prompt}
            ]
            
            # Prepare provider configuration
            provider_config = {
                "provider": provider_id,
                "model": model,
                "base_url": base_url,
                "timeout": timeout,
                "max_retries": max_retries
            }
            
            # Parse custom headers if provided
            if custom_headers:
                try:
                    import json
                    headers_dict = json.loads(custom_headers)
                    provider_config['headers'] = headers_dict
                except json.JSONDecodeError as e:
                    print(f"Invalid custom headers JSON: {e}")
            
            # Make AI call
            return await self.call_ai_provider(ai_messages, provider_config)
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Error processing message context: {str(e)}'
            }
    
    async def process_compact_context(self, processed_messages: List[Dict], system_prompt: str, settings: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process compact JSON context for process chat endpoint
        
        Args:
            processed_messages: List of compact JSON messages from processor
            system_prompt: System prompt for AI
            settings: Frontend settings including provider info
            
        Returns:
            Response dictionary with success/error info
        """
        try:
            # Use universal settings to get provider config
            provider_config = get_provider_config(settings, use_tactical=False)
            
            # Extract values from pre-validated provider config
            provider_id = provider_config['provider']
            model = provider_config['model']
            base_url = provider_config['base_url']
            custom_headers = provider_config.get('custom_headers')
            timeout = provider_config['timeout']
            max_retries = provider_config['max_retries']
            
            # Use provider's default model if none specified
            if not model:
                provider = self.provider_manager.get_provider(provider_id)
                if provider:
                    models = provider.get('models', [])
                    if models:
                        model = models[0]
                else:
                    model = 'default'
            
            # Convert processed messages to JSON string for AI context
            import json
            compact_json_context = json.dumps(processed_messages, indent=2)
            
            # Prepare messages for LLM with compact JSON context
            ai_messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Chat Context (Compact JSON Format):\n{compact_json_context}\n\nPlease respond to this conversation as an AI assistant for tabletop RPGs. If you need to generate game mechanics, use the compact JSON format specified in the system prompt."}
            ]
            
            # Prepare provider configuration
            provider_config = {
                "provider": provider_id,
                "model": model,
                "base_url": base_url,
                "timeout": timeout,
                "max_retries": max_retries
            }
            
            # Parse custom headers if provided
            if custom_headers:
                try:
                    import json
                    headers_dict = json.loads(custom_headers)
                    provider_config['headers'] = headers_dict
                except json.JSONDecodeError as e:
                    print(f"Invalid custom headers JSON: {e}")
            
            # Make AI call
            return await self.call_ai_provider(ai_messages, provider_config)
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Error processing compact context: {str(e)}'
            }

# Global AI service instance
_ai_service = None

def get_ai_service() -> 'AIService':
    """Get or create global AI service instance using ServiceRegistry"""
    global _ai_service
    if _ai_service is None:
        # Use ServiceRegistry to get provider manager
        try:
            from .registry import ServiceRegistry
            
            # Try to get provider manager from registry
            if ServiceRegistry.is_ready() and ServiceRegistry.is_registered('provider_manager'):
                provider_manager = ServiceRegistry.get('provider_manager')
                logger.info("✅ AI Service: Using provider manager from ServiceRegistry")
            else:
                # Fallback - create new instance
                from .provider_manager import ProviderManager
                provider_manager = ProviderManager()
                if ServiceRegistry.is_ready():
                    logger.warning("⚠️ AI Service: Provider manager not in registry, created new instance")
                else:
                    logger.warning("⚠️ AI Service: ServiceRegistry not ready, created new ProviderManager")
                
        except Exception as e:
            # Ultimate fallback - create new instance
            logger.error(f"❌ AI Service: Failed to access ServiceRegistry: {e}")
            from .provider_manager import ProviderManager
            provider_manager = ProviderManager()
            logger.info("🔄 AI Service: Created new ProviderManager (exception fallback)")
            
        _ai_service = AIService(provider_manager)
        
        # Register AI service with registry if available
        try:
            from .registry import ServiceRegistry
            if ServiceRegistry.is_ready():
                ServiceRegistry.register('ai_service', _ai_service)
                logger.info("✅ AI Service: Registered with ServiceRegistry")
        except Exception as e:
            logger.warning(f"⚠️ AI Service: Failed to register with ServiceRegistry: {e}")
    
    return _ai_service

async def process_ai_request(request_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process AI request - main entry point for external callers
    
    Args:
        request_data: Dictionary containing:
            - provider: Provider ID (e.g., 'openrouter')
            - model: Model name (e.g., 'openai/glm-4.6')
            - prompt: Prompt text (optional, will use message_context if not provided)
            - message_context: List of messages (optional)
            - base_url: Custom API base URL (optional)
            - api_key: API key (optional, will use environment if not provided)
            - temperature: Temperature for generation (optional)
            - max_tokens: Maximum tokens (optional)
            - timeout: Request timeout in seconds (optional)
            
    Returns:
        Dictionary with response data and metadata
    """
    try:
        ai_service = get_ai_service()
        
        # Extract configuration with proper type conversion
        provider_id = request_data.get('provider', 'openai')
        model = request_data.get('model', 'gpt-3.5-turbo')
        prompt = request_data.get('prompt')
        message_context = request_data.get('message_context')
        base_url = request_data.get('base_url')
        api_key = request_data.get('api_key')
        temperature = request_data.get('temperature', 0.1)
        max_tokens = request_data.get('max_tokens')
        timeout = request_data.get('timeout', 30)
        
        # Prepare provider configuration with type safety
        provider_config = {
            "provider": provider_id,
            "model": model,
            "base_url": base_url,
            "api_key": api_key,
            "temperature": float(temperature) if temperature is not None else 0.1,
            "max_tokens": int(max_tokens) if max_tokens is not None else None,
            "timeout": int(timeout) if timeout is not None else 30
        }
        
        # Prepare messages
        if prompt:
            # Use simple prompt
            messages = [{"role": "user", "content": prompt}]
        elif message_context:
            # Use message context
            messages = message_context
        else:
            return {
                'success': False,
                'error': 'Either prompt or message_context must be provided'
            }
        
        # Make AI call
        return await ai_service.call_ai_provider(messages, provider_config)
        
    except Exception as e:
        return {
            'success': False,
            'error': f'Error in process_ai_request: {str(e)}'
        }
