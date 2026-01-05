#!/usr/bin/env python3
"""
AI Service for The Gold Box
Dedicated module for formatting AI API calls and LiteLLM interactions

Provides unified interface for both simple_chat and process_chat endpoints
"""

import os
import time
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
    
    async def call_ai_provider(self, messages: List[Dict[str, str]], config: Dict[str, Any], tools: Optional[List[Dict]] = None) -> Dict[str, Any]:
        """
        Make AI call using LiteLLM with unified configuration
        
        Args:
            messages: List of messages in chat format [{'role': 'system', 'content': '...'}, ...]
            config: Provider configuration from universal settings (pre-validated)
            tools: Optional list of tool definitions in OpenAI format for function calling
            
        Returns:
            Dictionary with response data and metadata, including tool_calls if present
            
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
            
            # DEBUG: Log model name at entry point
            logger.info(f"=== DEBUG: Model name at ai_service.py entry ===")
            logger.info(f"provider_id: {provider_id}")
            logger.info(f"model: {model}")
            logger.info(f"model type: {type(model)}")
            logger.info(f"==============================================")
            
            # Get provider configuration
            provider = self.provider_manager.get_provider(provider_id)
            if not provider:
                raise ProviderException(f'Provider "{provider_id}" not found')
            
            # Only check for API key if provider requires authentication
            if provider.get('requires_auth', True):
                # Get API key from key_manager using service factory - keys should be loaded at startup
                from ..system_services.service_factory import get_key_manager
                
                key_manager = get_key_manager()
                
                if not hasattr(key_manager, 'keys_data') or not key_manager.keys_data:
                    raise APIKeyException("Key manager keys_data not available - keys not loaded at startup")
                
                api_key = key_manager.keys_data.get(provider_id)
                if not api_key:
                    raise APIKeyException(f"API key not configured for provider '{provider_id}' in key manager")
            else:
                # No authentication needed for local providers
                # However, LiteLLM's OpenAI client always requires an API key, even if unused
                # Pass a dummy key to satisfy the client requirement
                api_key = "dummy-key-not-required"
                logger.debug(f"Using dummy API key for provider '{provider_id}' (no auth required)")
            
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
            
            # Add tools if provided (function calling)
            if tools:
                completion_params["tools"] = tools
            
            # Apply custom configuration if provided
            # IMPORTANT: Don't set api_base for providers that use prefixed model names
            # (ollama, ollama_chat, ollama_openai, etc.) because setting api_base
            # triggers LiteLLM provider auto-detection which strips the prefix from model names
            # LiteLLM will auto-detect provider from model prefix and use default base URL
            base_url_from_config = config.get('base_url')
            if base_url_from_config and provider_id not in ['ollama', 'ollama_chat', 'ollama_openai']:
                completion_params['api_base'] = base_url_from_config
                logger.debug(f"Setting api_base={base_url_from_config} for provider {provider_id}")
            elif base_url_from_config and provider_id in ['ollama', 'ollama_chat', 'ollama_openai']:
                # For local providers with prefixed models, don't set api_base
                # LiteLLM will auto-detect provider from model prefix and use default base URL
                logger.debug(f"Skipping api_base for {provider_id} to preserve model prefix auto-detection")
            
            # For custom providers without provider prefixes, explicitly tell LiteLLM which provider to use
            # Don't set this for providers that use prefixed model names (ollama, ollama_chat, etc.)
            # because LiteLLM will auto-detect the provider from the model prefix
            if provider_id in ['custom', 'custom_openai', 'openai_like']:
                completion_params['custom_llm_provider'] = provider_id
                logger.debug(f"Setting custom_llm_provider={provider_id} for prefixed model support")
            
            if config.get('headers'):
                # Set custom headers without forcing OpenAI client
                # Let LiteLLM auto-detect provider from model name
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
                
                # Log summary of response from AI (detailed logs will be in add_conversation_message)
                logger.info(f"===== RECEIVED FROM AI =====")
                logger.info(f"Finish reason: {getattr(choice, 'finish_reason', 'unknown')}")
                
                # Check for tool_calls and content
                if hasattr(choice, 'message'):
                    msg = choice.message
                    
                    # Check for tool_calls attribute
                    if hasattr(msg, 'tool_calls') and msg.tool_calls:
                        tool_calls = msg.tool_calls
                        tool_count = len(tool_calls)
                        tool_names = [tc.function.name for tc in tool_calls]
                        logger.info(f"  Tool calls: {tool_count} - {tool_names}")
                    else:
                        logger.info(f"  Tool calls: 0")
                    
                    # Log content
                    content = msg.content or ""
                    if content:
                        logger.info(f"  Content length: {len(content)} characters")
                    else:
                        logger.info(f"  Content length: 0 characters (empty)")
                    
                    # Check for thinking/reasoning_content
                    if hasattr(msg, 'reasoning_content') and msg.reasoning_content:
                        thinking = msg.reasoning_content
                        logger.info(f"  Thinking length: {len(str(thinking))} characters")
                    elif hasattr(msg, 'thinking') and msg.thinking:
                        thinking = msg.thinking
                        logger.info(f"  Thinking length: {len(str(thinking))} characters")
                
                logger.info(f"===== END RECEIVED FROM AI =====")
                
                # Extracts content and tool calls
                content = ""
                tool_calls = None
                
                # Handle both content and tool_calls
                if hasattr(choice, 'message') and choice.message:
                    content = choice.message.content or ""
                    
                    # Check for tool_calls (function calling)
                    if hasattr(choice.message, 'tool_calls') and choice.message.tool_calls:
                        tool_calls = choice.message.tool_calls
                    
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
                    'has_thinking': bool(thinking),
                    'has_tool_calls': bool(tool_calls)
                }
                
                return {
                    'success': True,
                    'response': content,
                    'thinking': thinking,
                    'tool_calls': tool_calls,
                    'has_tool_calls': bool(tool_calls),
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
    
    async def process_compact_context(self, processed_messages: List[Dict], system_prompt: str, settings: Dict[str, Any], session_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Process compact JSON context for process chat endpoint with conversation history support
        
        Args:
            processed_messages: List of compact JSON messages from processor (NEW FOUNDRY MESSAGES ONLY)
            system_prompt: System prompt for AI
            settings: Frontend settings including provider info
            session_id: Optional session ID for conversation history
            
        Returns:
            Response dictionary with success/error info
            
        Raises:
            ProviderException: When AI provider fails
            ValidationException: When compact context is invalid
        """
        try:
            # Check if in combat to determine tactical vs general LLM (use processed_messages for this)
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
            if not system_prompt or not isinstance(system_prompt, str):
                raise ValidationException("System prompt must be a non-empty string")
            
            # Build AI message list using conversation history
            ai_messages = []
            
            if session_id:
                from ..ai_services.ai_session_manager import get_ai_session_manager
                from ..message_services.message_delta_service import get_message_delta_service
                from ..ai_services.ai_session_manager import estimate_tokens
                
                ai_session_manager = get_ai_session_manager()
                delta_service = get_message_delta_service()
                
                # Get token limit from settings (default 5000)
                max_history_tokens = settings.get('max history tokens', 5000)
                
                # Get conversation history in OpenAI format with token pruning
                conversation_history = ai_session_manager.get_conversation_history(
                    session_id, max_tokens=max_history_tokens
                )
                
                # Add conversation history to AI messages (excluding any existing system message)
                for msg in conversation_history:
                    if msg.get('role') != 'system':
                        ai_messages.append(msg)
                
                # Store new user messages (compact JSON converted to OpenAI format)
                if processed_messages:
                    # Convert compact JSON context to user message
                    import json
                    compact_json_context = json.dumps(processed_messages, indent=2)
                    
                    # Get timestamp from newest message in processed_messages for proper delta tracking
                    newest_timestamp = None
                    for msg in processed_messages:
                        msg_ts = msg.get('ts') or msg.get('timestamp')
                        if msg_ts and (newest_timestamp is None or msg_ts > newest_timestamp):
                            newest_timestamp = msg_ts
                    
                    # Use newest message timestamp if available, otherwise use current time
                    user_timestamp = newest_timestamp if newest_timestamp else int(time.time() * 1000)
                    
                    user_message = {
                        "role": "user",
                        "content": f"Chat Context (Compact JSON Format):\n{compact_json_context}",
                        "timestamp": user_timestamp
                    }
                    
                    # Add to AI messages
                    ai_messages.append(user_message)
                    
                    # Store in conversation history immediately
                    ai_session_manager.add_conversation_message(session_id, user_message)
                
                # No session_id - fallback to single message with compact context
                import json
                compact_json_context = json.dumps(processed_messages, indent=2)
                
                ai_messages = [
                    {"role": "user", "content": f"Chat Context (Compact JSON Format):\n{compact_json_context}"}
                ]
            
            # Generate dynamic combat-aware prompt from processed_messages
            from .combat_prompt_generator import get_combat_prompt_generator
            
            combat_prompt_generator = get_combat_prompt_generator()
            combat_context = self._extract_combat_context_from_messages(processed_messages)
            combat_state = self._extract_combat_state_from_messages(processed_messages)
            
            dynamic_prompt = combat_prompt_generator.generate_prompt(combat_context, combat_state)
            
            # Add system prompt at the beginning
            ai_messages.insert(0, {"role": "system", "content": system_prompt})
            
            # Add dynamic prompt to last user message
            if ai_messages and ai_messages[-1].get('role') == 'user':
                ai_messages[-1]['content'] += f"\n\n{dynamic_prompt}"
            
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
            response = await self.call_ai_provider(ai_messages, provider_config)
            
            # Store AI response in conversation history if session_id provided
            if session_id and response.get('success'):
                ai_response_content = response.get('response', '')
                if ai_response_content:
                    from ..ai_services.ai_session_manager import get_ai_session_manager
                    ai_session_manager = get_ai_session_manager()
                    
                    ai_message = {
                        "role": "assistant",
                        "content": ai_response_content,
                        "timestamp": int(time.time() * 1000)
                    }
                    
                    ai_session_manager.add_conversation_message(session_id, ai_message)
                    ai_session_manager.update_session_timestamp(session_id, ai_message['timestamp'])
            
            return response
            
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
                            return True
                        
                        # Check nested combat_context structure
                        nested_combat = combat_data.get('combat_context', {})
                        if isinstance(nested_combat, dict) and nested_combat.get('in_combat', False):
                            return True
            return False
            
        except Exception as e:
            logger.warning(f"Error determining tactical LLM usage: {e}")
            return False
    
    def _extract_combat_context_from_messages(self, processed_messages: List[Dict]) -> Dict[str, Any]:
        """
        Extract combat context from processed messages
        
        Args:
            processed_messages: List of processed messages from context processor
            
        Returns:
            Combat context dictionary
        """
        try:
            for msg in processed_messages:
                if msg.get('type') == 'combat_context':
                    return msg.get('combat_context', {})
            return {}
            
        except Exception as e:
            logger.warning(f"Error extracting combat context: {e}")
            return {}
    
    def _decode_json_recursively(self, obj):
        """
        Recursively decode JSON strings within a JSON structure
        
        Args:
            obj: JSON object (dict, list, or primitive type)
            
        Returns:
            Decoded JSON object with all string values properly formatted
        """
        import json
        
        if isinstance(obj, dict):
            return {k: self._decode_json_recursively(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._decode_json_recursively(item) for item in obj]
        elif isinstance(obj, str):
            # Try to parse string as JSON
            try:
                parsed = json.loads(obj)
                # If successfully parsed, recursively process it
                if isinstance(parsed, (dict, list)):
                    return self._decode_json_recursively(parsed)
            except (json.JSONDecodeError, ValueError):
                # Not valid JSON, just decode escape sequences
                pass
            
            # Decode escape sequences
            decoded = obj.replace('\\n', '\n')
            decoded = decoded.replace('\\r', '\r')
            decoded = decoded.replace('\\t', '\t')
            decoded = decoded.replace('\\"', '"')
            decoded = decoded.replace('\\\\', '\\')
            return decoded
        else:
            # Return primitive types as-is
            return obj
    
    def _decode_content_for_display(self, content: str) -> str:
        """
        Decode content for display, handling JSON strings with escape sequences
        
        Args:
            content: Content string that may contain JSON escape sequences
            
        Returns:
            Decoded content with proper newlines and other special characters
        """
        try:
            import json
            
            # Try to parse as JSON if it looks like a JSON string
            if content.startswith('{') or content.startswith('['):
                try:
                    # Parse and recursively decode all nested strings
                    parsed = json.loads(content)
                    if isinstance(parsed, (dict, list)):
                        decoded_obj = self._decode_json_recursively(parsed)
                        return json.dumps(decoded_obj, indent=2, ensure_ascii=False)
                except json.JSONDecodeError:
                    # Not valid JSON, continue with string decoding
                    pass
            
            # Decode escape sequences in the string
            # Replace common escape sequences with their actual characters
            decoded = content
            
            # Handle escaped newlines and other characters
            decoded = decoded.replace('\\n', '\n')
            decoded = decoded.replace('\\r', '\r')
            decoded = decoded.replace('\\t', '\t')
            decoded = decoded.replace('\\"', '"')
            decoded = decoded.replace('\\\\', '\\')
            
            return decoded
            
        except Exception as e:
            # If decoding fails, return original content
            logger.debug(f"Content decoding failed: {e}, returning original")
            return content
    
    def _extract_combat_state_from_messages(self, processed_messages: List[Dict]) -> Dict[str, Any]:
        """
        Extract raw combat state from processed messages
        
        Args:
            processed_messages: List of processed messages from context processor
            
        Returns:
            Raw combat state dictionary
        """
        try:
            for msg in processed_messages:
                if msg.get('type') == 'combat_context':
                    combat_context = msg.get('combat_context', {})
                    if isinstance(combat_context, dict):
                        raw_state = combat_context.get('raw_state', {})
                        if isinstance(raw_state, dict):
                            return raw_state
            return {}
            
        except Exception as e:
            logger.warning(f"Error extracting combat state: {e}")
            return {}

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
