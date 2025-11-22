#!/usr/bin/env python3
"""
AI Service for The Gold Box
Dedicated module for formatting AI API calls and LiteLLM interactions

Provides unified interface for both simple_chat and process_chat endpoints
"""

import os
import asyncio
import litellm
from typing import Dict, Any, Optional, List
from provider_manager import ProviderManager

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
            config: Provider configuration including api_key, provider, model, etc.
            
        Returns:
            Dictionary with response data and metadata
        """
        try:
            provider_id = config.get('provider')
            model = config.get('model')
            api_key = config.get('api_key')
            
            # Get provider configuration
            provider = self.provider_manager.get_provider(provider_id)
            if not provider:
                return {
                    'success': False,
                    'error': f'Provider "{provider_id}" not found'
                }
            
            # Get API key from environment if not provided
            if not api_key:
                api_key = os.environ.get(f'{provider_id.upper()}_API_KEY', '')
            
            if not api_key:
                return {
                    'success': False,
                    'error': f'API key not configured for provider "{provider_id}"'
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
            
            # Prepare LiteLLM completion parameters
            completion_params = {
                "model": model,
                "messages": messages,
                "api_key": api_key,
                "temperature": float(config.get('temperature', 0.1)),
                "max_tokens": int(config.get('max_tokens', 0)) if config.get('max_tokens') is not None else None,  # No limit by default
                "stream": False  # Stream internally but wait for complete response
            }
            
            # Apply custom configuration if provided
            if config.get('base_url'):
                completion_params['api_base'] = config['base_url']
            
            if config.get('headers'):
                completion_params['custom_llm_provider'] = "openai"  # Use OpenAI format for custom headers
                completion_params['headers'] = config['headers']
            
            # Apply timeout
            timeout = config.get('timeout', 30)
            
            # Use LiteLLM to call any provider API
            response = await asyncio.wait_for(
                litellm.acompletion(**completion_params),
                timeout=timeout
            )
            
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
            # Extract provider settings
            provider_id = settings.get('general llm provider')
            model = settings.get('general llm model', 'default')
            base_url = settings.get('general llm base url')
            custom_headers = settings.get('general llm custom headers')
            timeout = settings.get('general llm timeout', 30)
            max_retries = settings.get('general llm max retries', 3)
            
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
            # Extract provider settings
            provider_id = settings.get('general llm provider')
            model = settings.get('general llm model', 'default')
            base_url = settings.get('general llm base url')
            custom_headers = settings.get('general llm custom headers')
            timeout = settings.get('general llm timeout', 30)
            max_retries = settings.get('general llm max retries', 3)
            
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
