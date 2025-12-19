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
from ..system_services.service_factory import get_provider_manager
from ..system_services.universal_settings import get_provider_config
from ..message_services.whisper_service import get_whisper_service
from shared.exceptions import APIKeyException, ProviderException, TimeoutException, ValidationException

logger = logging.getLogger(__name__)

class AIService:
    """
    Unified AI service for all API calls
    Handles LiteLLM interactions, formatting, and provider management
    """
    
    def __init__(self, provider_manager):
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
            
        Raises:
            ProviderException: When provider configuration fails
            APIKeyException: When API key is missing or invalid
            TimeoutException: When API call times out
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
            
            # Get provider configuration
            provider = self.provider_manager.get_provider(provider_id)
            if not provider:
                raise ProviderException(f'Provider "{provider_id}" not found')
            
            # Get API key from key_manager using service factory - keys should be loaded at startup
            from ..system_services.service_factory import get_key_manager
            
            key_manager = get_key_manager()
            
            if not hasattr(key_manager, 'keys_data') or not key_manager.keys_data:
                raise APIKeyException("Key manager keys_data not available - keys not loaded at startup")
            
            api_key = key_manager.keys_data.get(provider_id)
            if not api_key:
                raise APIKeyException(f"API key not configured for provider '{provider_id}' in key manager")
            
            # Configure provider in LiteLLM if it's custom
            if provider.get('is_custom', False):
                custom_config = {
                    'base_url': config.get('base_url'),
                    'headers': config.get('headers'),
                    'models': provider.get('models', [])
                }
                success = self.provider_manager.configure_litellm_provider(provider_id, api_key, custom_config)
                if not success:
                    raise ProviderException(f'Failed to configure custom provider "{provider_id}"')
            
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
                # Provider API responded!
                choice = response.choices[0]
                
                # Extracts content
                content = ""
                
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
                
                # Extract thinking content
                whisper_service = get_whisper_service()
                thinking = whisper_service.extract_ai_thinking({}, response)
                
                # Extract metadata
                metadata = {
                    'provider': provider_id,
                    'provider_name': provider.get('name', provider_id),
                    'model': model,
                    'finish_reason': getattr(choice, 'finish_reason', 'unknown'),
                    'usage': getattr(response, 'usage', None),
                    'has_thinking': bool(thinking)
                }
                
                return {
                    'success': True,
                    'response': content,
                    'thinking': thinking,
                    'metadata': metadata,
                    'tokens_used': getattr(response.usage, 'total_tokens', 0) if response.usage else 0,
                    'response_object': response
                }
            else:
                raise ProviderException('No response choices received from API')
                
        except asyncio.TimeoutError:
            raise TimeoutException(f'AI call timed out after {timeout} seconds')
        except (ProviderException, APIKeyException, TimeoutException):
            # Re-raise our custom exceptions directly
            raise
        except Exception as e:
            # Wrap unexpected exceptions
            raise ProviderException(f"Provider API failed: {str(e)}")
    
    async def process_message_context(self, message_context: List[Dict], settings: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process message context for simple chat endpoint
        
        Args:
            message_context: List of message objects from frontend
            settings: Frontend settings including provider info
            
        Returns:
            Response dictionary with success/error info
            
        Raises:
            ProviderException: When AI provider fails
            ValidationException: When message context is invalid
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
            
            # Validate message context
            if not message_context or not isinstance(message_context, list):
                raise ValidationException("Message context must be a non-empty list")
            
            # Process message context into chronological string
            import re
            context_parts = []
            
            for msg in message_context:
                if not isinstance(msg, dict) or 'content' not in msg or 'sender' not in msg:
                    raise ValidationException("Each message must be a dict with 'content' and 'sender' fields")
                
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
                    raise ValidationException(f"Invalid custom headers JSON: {e}")
            
            # Make AI call
            return await self.call_ai_provider(ai_messages, provider_config)
            
        except (ProviderException, APIKeyException, TimeoutException, ValidationException):
            # Re-raise our custom exceptions directly
            raise
        except Exception as e:
            # Wrap unexpected exceptions
            raise ProviderException(f"Error processing message context: {str(e)}")
    
    async def process_compact_context(self, processed_messages: List[Dict], system_prompt: str, settings: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process compact JSON context for process chat endpoint
        
        Args:
            processed_messages: List of compact JSON messages from processor
            system_prompt: System prompt for AI
            settings: Frontend settings including provider info
            
        Returns:
            Response dictionary with success/error info
            
        Raises:
            ProviderException: When AI provider fails
            ValidationException: When compact context is invalid
        """
        try:
            # Check if in combat to determine tactical vs general LLM
            use_tactical = self._should_use_tactical_llm(processed_messages)
            
            # Use universal settings to get provider config
            provider_config = get_provider_config(settings, use_tactical=use_tactical)
            
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
            
            # Validate inputs
            if not processed_messages or not isinstance(processed_messages, list):
                raise ValidationException("Processed messages must be a non-empty list")
            
            if not system_prompt or not isinstance(system_prompt, str):
                raise ValidationException("System prompt must be a non-empty string")
            
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
                    raise ValidationException(f"Invalid custom headers JSON: {e}")
            
            # Make AI call
            return await self.call_ai_provider(ai_messages, provider_config)
            
        except (ProviderException, APIKeyException, TimeoutException, ValidationException):
            # Re-raise our custom exceptions directly
            raise
        except Exception as e:
            # Wrap unexpected exceptions
            raise ProviderException(f"Error processing compact context: {str(e)}")
    
    def _should_use_tactical_llm(self, processed_messages: List[Dict]) -> bool:
        """
        Determine if tactical LLM should be used based on combat context
        
        Args:
            processed_messages: List of processed messages from context processor
            
        Returns:
            True if tactical LLM should be used, False otherwise
        """
        try:
            # Check if combat context exists and indicates active combat
            for msg in processed_messages:
                if msg.get('type') == 'combat_context':
                    combat_data = msg.get('combat_context', {})
                    
                    # Check both direct combat_data and nested structure
                    if isinstance(combat_data, dict):
                        # Direct combat data from frontend
                        if combat_data.get('in_combat', False):
                            logger.debug("Tactical LLM selected: in_combat=True from direct combat data")
                            return True
                        
                        # Check nested combat_context structure
                        nested_combat = combat_data.get('combat_context', {})
                        if nested_combat.get('in_combat', False):
                            logger.debug("Tactical LLM selected: in_combat=True from nested combat context")
                            return True
            
            logger.debug("General LLM selected: no active combat detected")
            return False
            
        except Exception as e:
            logger.warning(f"Error determining tactical LLM usage: {e}")
            return False

def get_ai_service() -> 'AIService':
    """Get AI service instance from ServiceRegistry"""
    from ..system_services.service_factory import get_ai_service as factory_get_ai_service
    return factory_get_ai_service()

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
        
    Raises:
        APIKeyException: When API key is missing
        ValidationException: When request data is invalid
        ProviderException: When AI provider fails
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
        
        # Prepare provider configuration - require API key in config, no environment fallbacks
        if not api_key:
            raise APIKeyException('API key must be provided in request_data for external calls')
        
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
            raise ValidationException('Either prompt or message_context must be provided')
        
        # Make AI call
        return await ai_service.call_ai_provider(messages, provider_config)
        
    except (ProviderException, APIKeyException, TimeoutException, ValidationException):
        # Re-raise our custom exceptions directly
        raise
    except Exception as e:
        # Wrap unexpected exceptions
        raise ProviderException(f"Error in process_ai_request: {str(e)}")
