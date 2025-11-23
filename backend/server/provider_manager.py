#!/usr/bin/env python3
"""
Provider Manager for The Gold Box
Handles dynamic loading of litellm providers and custom providers
"""

import json
import os
import requests
from pathlib import Path
from typing import Dict, List, Optional, Any
import hashlib

# Get absolute path to backend directory (where server.py is located)
BACKEND_DIR = Path(__file__).parent.parent.absolute()

def get_absolute_path(relative_path: str) -> Path:
    """
    Convert a relative path to an absolute path based on backend directory.
    This ensures consistent file operations regardless of where script is called from.
    """
    return (BACKEND_DIR / relative_path).resolve()

class ProviderManager:
    """Manages both default litellm providers and custom providers"""
    
    def __init__(self, custom_providers_file='custom_providers.json'):
        self.custom_providers_file = get_absolute_path(custom_providers_file)
        self.default_providers = {}
        self.custom_providers = {}
        self.all_providers = {}
        
        # Load all providers on initialization
        self.load_default_providers()
        self.load_custom_providers()
        self.merge_providers()
    
    def load_default_providers(self):
        """Load providers from litellm_providers.json as single source of truth"""
        print("Loading comprehensive provider list from JSON...")
        
        try:
            # Load comprehensive provider list from file as single source of truth
            with open(get_absolute_path('server_files/litellm_providers.json'), 'r') as f:
                provider_data = json.load(f)
                providers_list = provider_data['providers']
                provider_details = provider_data['provider_details']
                
                # Create comprehensive provider definitions
                self.default_providers = {}
                
                # Enhanced provider definitions for major providers
                enhanced_providers = {
                    'openai': {
                        'slug': 'openai',
                        'name': 'OpenAI',
                        'description': 'GPT models including Sora, ChatGPT, and embeddings',
                        'models': ['gpt-4', 'gpt-4-turbo', 'gpt-4o', 'gpt-3.5-turbo'],
                        'auth_type': 'Bearer Token',
                        'base_url': 'https://api.openai.com/v1',
                        'completion_endpoint': '/chat/completions',
                        'is_custom': False
                    },
                    'anthropic': {
                        'slug': 'anthropic',
                        'name': 'Anthropic Claude',
                        'description': 'Claude AI models including Haiku, Sonnet, and Opus',
                        'models': ['claude-3-5-haiku-20241022', 'claude-3-5-sonnet-20241022', 'claude-3-opus-20240229'],
                        'auth_type': 'Bearer Token',
                        'base_url': 'https://api.anthropic.com',
                        'completion_endpoint': '/v1/messages',
                        'is_custom': False
                    },
                    'google': {
                        'slug': 'google',
                        'name': 'Google AI',
                        'description': 'Gemini models by Google',
                        'models': ['gemini-1.5-pro', 'gemini-1.5-flash', 'gemini-pro'],
                        'auth_type': 'Bearer Token',
                        'base_url': 'https://generativelanguage.googleapis.com',
                        'completion_endpoint': '/v1beta/models/{model}:generateContent',
                        'is_custom': False
                    },
                    'azure': {
                        'slug': 'azure',
                        'name': 'Azure OpenAI',
                        'description': 'OpenAI models hosted on Microsoft Azure',
                        'models': ['gpt-4', 'gpt-4-32k', 'gpt-35-turbo'],
                        'auth_type': 'Bearer Token',
                        'base_url': 'https://your-resource.openai.azure.com',
                        'completion_endpoint': '/openai/deployments/{deployment}/chat/completions',
                        'is_custom': False
                    },
                    'cohere': {
                        'slug': 'cohere',
                        'name': 'Cohere',
                        'description': 'Command and embedding models by Cohere',
                        'models': ['command-r-plus', 'command', 'embed-v4.0'],
                        'auth_type': 'Bearer Token',
                        'base_url': 'https://api.cohere.ai',
                        'completion_endpoint': '/v1/chat',
                        'is_custom': False
                    },
                    'groq': {
                        'slug': 'groq',
                        'name': 'Groq',
                        'description': 'Ultra-fast inference for open models',
                        'models': ['llama-3.1-405b-reasoning', 'mixtral-8x7b-32768', 'gemma-7b-it'],
                        'auth_type': 'Bearer Token',
                        'base_url': 'https://api.groq.com',
                        'completion_endpoint': '/openai/v1/chat/completions',
                        'is_custom': False
                    },
                    'together_ai': {
                        'slug': 'together_ai',
                        'name': 'Together AI',
                        'description': 'Open source models with fast inference',
                        'models': ['meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo', 'mistralai/Mixtral-8x7B-Instruct-v0.1'],
                        'auth_type': 'Bearer Token',
                        'base_url': 'https://api.together.xyz',
                        'completion_endpoint': '/v1/chat/completions',
                        'is_custom': False
                    },
                    'replicate': {
                        'slug': 'replicate',
                        'name': 'Replicate',
                        'description': 'Serverless open source model deployment',
                        'models': ['meta/llama-2-70b-chat', 'meta/meta-llama-3-70b-instruct'],
                        'auth_type': 'Bearer Token',
                        'base_url': 'https://api.replicate.com',
                        'completion_endpoint': '/v1/models/{model}/predictions',
                        'is_custom': False
                    },
                    'aws_bedrock': {
                        'slug': 'aws_bedrock',
                        'name': 'AWS Bedrock',
                        'description': 'Amazon Bedrock with Claude, Titan, and other AWS models',
                        'models': ['anthropic.claude-3-sonnet-20240229-v1:0', 'amazon.titan-text-express-v1'],
                        'auth_type': 'AWS SigV4',
                        'base_url': 'https://bedrock-runtime.us-east-1.amazonaws.com',
                        'completion_endpoint': '/model/{model}/invoke',
                        'is_custom': False
                    },
                    'vertex_ai': {
                        'slug': 'vertex_ai',
                        'name': 'Google Vertex AI',
                        'description': 'Google Cloud Vertex AI platform',
                        'models': ['gemini-1.0-pro', 'gemini-1.5-pro'],
                        'auth_type': 'Bearer Token',
                        'base_url': 'https://us-central1-aiplatform.googleapis.com',
                        'completion_endpoint': '/v1/projects/{project}/locations/{location}/publishers/google/models/{model}:generateContent',
                        'is_custom': False
                    },
                    'mistral': {
                        'slug': 'mistral',
                        'name': 'Mistral AI',
                        'description': 'Official Mistral models including Codestral and Pixtral',
                        'models': ['mistral-large-2407', 'codestral-2405'],
                        'auth_type': 'Bearer Token',
                        'base_url': 'https://api.mistral.ai',
                        'completion_endpoint': '/v1/chat/completions',
                        'is_custom': False
                    },
                    'perplexity': {
                        'slug': 'perplexity',
                        'name': 'Perplexity AI',
                        'description': 'Mixtral and Llama models with fast inference',
                        'models': ['mixtral-8x7b-instruct', 'llama-3-8b-instruct'],
                        'auth_type': 'Bearer Token',
                        'base_url': 'https://api.perplexity.ai',
                        'completion_endpoint': '/chat/completions',
                        'is_custom': False
                    },
                    'fireworks_ai': {
                        'slug': 'fireworks_ai',
                        'name': 'Fireworks AI',
                        'description': 'Fast and affordable inference for open models',
                        'models': ['llama-v3-8b-instruct', 'llama-v3-70b-instruct'],
                        'auth_type': 'Bearer Token',
                        'base_url': 'https://api.fireworks.ai',
                        'completion_endpoint': '/v1/chat/completions',
                        'is_custom': False
                    },
                    'xai': {
                        'slug': 'xai',
                        'name': 'xAI (Grok)',
                        'description': 'Elon Musk\'s xAI with Grok models',
                        'models': ['grok-beta', 'grok-vision-beta'],
                        'auth_type': 'Bearer Token',
                        'base_url': 'https://api.x.ai',
                        'completion_endpoint': '/v1/chat/completions',
                        'is_custom': False
                    },
                    'openrouter': {
                        'slug': 'openrouter',
                        'name': 'OpenRouter',
                        'description': 'AI model router with access to many providers',
                        'models': ['openai/gpt-4o', 'anthropic/claude-3.5-sonnet', 'google/gemini-pro-1.5'],
                        'auth_type': 'Bearer Token',
                        'base_url': 'https://openrouter.ai',
                        'completion_endpoint': '/api/v1/chat/completions',
                        'is_custom': False
                    }
                }
                
                # Add all providers from litellm_providers.json as single source of truth
                for provider_slug in providers_list:
                    if provider_slug in enhanced_providers:
                        # Use enhanced definition for major providers
                        self.default_providers[provider_slug] = enhanced_providers[provider_slug]
                    else:
                        # Create basic provider entry for all other providers
                        provider_info = provider_details.get(provider_slug, {})
                        model_count = provider_info.get('model_count', 0)
                        sample_models = provider_info.get('sample_models', [])
                        
                        self.default_providers[provider_slug] = {
                            'slug': provider_slug,
                            'name': provider_slug.replace('_', ' ').title().replace('Ai', 'AI').replace('Ai', 'AI'),
                            'description': f'{model_count} models available via LiteLLM',
                            'models': sample_models[:3] if sample_models else [],
                            'auth_type': 'Bearer Token',
                            'base_url': 'https://api.example.com',  # User should configure this
                            'completion_endpoint': '/v1/chat/completions',
                            'is_custom': False
                        }
                    
        except FileNotFoundError:
            # If no provider list file, use minimal fallback
            self.default_providers = {
                'openai': {
                    'slug': 'openai',
                    'name': 'OpenAI',
                    'description': 'GPT-3.5, GPT-4, and other OpenAI models',
                    'models': ['gpt-3.5-turbo', 'gpt-4', 'gpt-4-turbo', 'gpt-4o'],
                    'auth_type': 'Bearer Token',
                    'base_url': 'https://api.openai.com/v1',
                    'completion_endpoint': '/chat/completions',
                    'is_custom': False
                }
            }
        except Exception as e:
            print(f"Error loading provider list: {e}")
            self.default_providers = {}
                
        print(f"Loaded {len(self.default_providers)} comprehensive providers")
    
    def load_custom_providers(self):
        """Load custom providers from JSON file"""
        try:
            if self.custom_providers_file.exists():
                with open(self.custom_providers_file, 'r') as f:
                    data = json.load(f)
                
                self.custom_providers = data.get('providers', {})
                print(f"Loaded {len(self.custom_providers)} custom providers")
            else:
                self.custom_providers = {}
                print("No custom providers file found, starting fresh")
                
        except Exception as e:
            print(f"Error loading custom providers: {e}")
            self.custom_providers = {}
    
    def merge_providers(self):
        """Combine default and custom providers"""
        self.all_providers = {**self.default_providers, **self.custom_providers}
        print(f"Total available providers: {len(self.all_providers)}")
    
    def get_all_providers(self) -> Dict[str, Any]:
        """Get all available providers"""
        return self.all_providers
    
    def get_provider(self, slug: str) -> Optional[Dict[str, Any]]:
        """Get specific provider by slug"""
        return self.all_providers.get(slug)
    
    def get_provider_list(self) -> List[Dict[str, Any]]:
        """Get list of all providers for display"""
        providers = []
        for slug, provider in self.all_providers.items():
            providers.append({
                'slug': slug,
                'name': provider.get('name', slug),
                'description': provider.get('description', ''),
                'is_custom': provider.get('is_custom', False)
            })
        return providers
    
    def add_custom_provider(self, slug: str, config: Dict[str, Any]) -> bool:
        """Add a new custom provider"""
        try:
            # Validate required fields
            required_fields = ['slug', 'name', 'base_url', 'auth_type', 'completion_endpoint']
            for field in required_fields:
                if field not in config:
                    print(f"Error: Missing required field '{field}'")
                    return False
            
            # Set is_custom flag
            config['is_custom'] = True
            
            # Add to custom providers
            self.custom_providers[slug] = config
            
            # Update merged providers
            self.merge_providers()
            
            # Save to file
            return self.save_custom_providers()
            
        except Exception as e:
            print(f"Error adding custom provider: {e}")
            return False
    
    def remove_custom_provider(self, slug: str) -> bool:
        """Remove a custom provider"""
        try:
            if slug in self.custom_providers:
                del self.custom_providers[slug]
                self.merge_providers()
                return self.save_custom_providers()
            else:
                print(f"Custom provider '{slug}' not found")
                return False
                
        except Exception as e:
            print(f"Error removing custom provider: {e}")
            return False
    
    def save_custom_providers(self) -> bool:
        """Save custom providers to file"""
        try:
            # Ensure directory exists
            self.custom_providers_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Prepare data with metadata
            data = {
                "_metadata": {
                    "version": "1.0",
                    "description": "Custom provider definitions for The Gold Box",
                    "last_updated": None
                },
                "providers": self.custom_providers
            }
            
            # Save to file
            with open(self.custom_providers_file, 'w') as f:
                json.dump(data, f, indent=2)
            
            # Set appropriate permissions
            os.chmod(self.custom_providers_file, 0o644)
            
            print(f"Custom providers saved to {self.custom_providers_file}")
            return True
            
        except Exception as e:
            print(f"Error saving custom providers: {e}")
            return False
    
    def validate_custom_config(self, config: Dict[str, Any]) -> tuple[bool, str]:
        """Validate custom provider configuration"""
        
        # Check URL format
        base_url = config.get('base_url', '')
        if not base_url.startswith(('http://', 'https://')):
            return False, "Base URL must start with http:// or https://"
        
        # Check auth type
        auth_type = config.get('auth_type', '')
        valid_auth_types = ['Bearer Token', 'Custom Header', 'Query Param']
        if auth_type not in valid_auth_types:
            return False, f"Auth type must be one of: {', '.join(valid_auth_types)}"
        
        # Check completion endpoint
        endpoint = config.get('completion_endpoint', '')
        if not endpoint.startswith('/'):
            return False, "Completion endpoint must start with /"
        
        return True, ""
    
    def get_environment_variables(self) -> Dict[str, str]:
        """Get environment variables for all providers"""
        env_vars = {}
        
        for slug, provider in self.all_providers.items():
            env_key = f'{slug.upper()}_API_KEY'
            env_value = os.environ.get(env_key)
            if env_value:
                env_vars[env_key] = env_value
        
        return env_vars
    
    def configure_litellm_provider(self, provider_id: str, api_key: str, custom_config: Dict[str, Any] = None) -> bool:
        """
        Configure any litellm provider dynamically
        
        Args:
            provider_id: Provider slug identifier
            api_key: API key for the provider
            custom_config: Optional custom provider configuration
            
        Returns:
            True if successful, False otherwise
        """
        try:
            import litellm
            
            # Set environment variable for provider
            env_key = f'{provider_id.upper()}_API_KEY'
            os.environ[env_key] = api_key
            
            # Configure custom provider if specified
            if custom_config:
                # Build litellm custom provider config
                litellm_config = {
                    'model_list': custom_config.get('models', []),
                }
                
                # Add base URL if provided
                if 'base_url' in custom_config:
                    litellm_config['api_base'] = custom_config['base_url']
                
                # Add completion endpoint if provided
                if 'completion_endpoint' in custom_config:
                    litellm_config['completion_endpoint'] = custom_config['completion_endpoint']
                
                # Configure authentication based on type
                auth_type = custom_config.get('auth_type', 'Bearer Token')
                if auth_type == 'Bearer Token':
                    # Standard Bearer token - handled by env var
                    pass
                elif auth_type == 'API Key Header':
                    if 'auth_header' in custom_config:
                        litellm_config['api_base'] = custom_config.get('base_url', '')
                        litellm_config['headers'] = {
                            custom_config['auth_header']: '${api_key}'
                        }
                elif auth_type == 'API Key Query':
                    if 'auth_query_param' in custom_config:
                        litellm_config['api_base'] = custom_config.get('base_url', '')
                        litellm_config['query_params'] = {
                            custom_config['auth_query_param']: '${api_key}'
                        }
                elif auth_type == 'Basic Auth':
                    if 'auth_username' in custom_config and 'auth_password' in custom_config:
                        litellm_config['api_base'] = custom_config.get('base_url', '')
                        litellm_config['headers'] = {
                            'Authorization': f'Basic ${base64_credentials}'
                        }
                elif auth_type == 'Custom Header':
                    if 'auth_header' in custom_config and 'auth_value' in custom_config:
                        litellm_config['api_base'] = custom_config.get('base_url', '')
                        litellm_config['headers'] = {
                            custom_config['auth_header']: custom_config['auth_value']
                        }
                
                # Set the custom provider in litellm
                litellm.set_custom_provider(provider_id, litellm_config)
                print(f"Custom provider '{provider_id}' configured in LiteLLM")
                
            else:
                # Standard provider - just set environment variable
                print(f"Standard provider '{provider_id}' configured via environment variable")
            
            return True
            
        except ImportError:
            print(f"ERROR: litellm library not available")
            return False
        except Exception as e:
            print(f"ERROR: Failed to configure provider '{provider_id}': {e}")
            return False
    
    def get_provider_for_model(self, model_name: str) -> Optional[Dict[str, Any]]:
        """
        Find which provider supports a specific model
        
        Args:
            model_name: Model name to search for
            
        Returns:
            Provider configuration if found, None otherwise
        """
        for provider_id, provider in self.all_providers.items():
            models = provider.get('models', [])
            if model_name in models:
                return provider
        return None
    
    def validate_model_provider_pair(self, model_name: str, provider_id: str) -> tuple[bool, str]:
        """
        Validate that a model is supported by a provider
        
        Args:
            model_name: Model name to validate
            provider_id: Provider identifier
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        provider = self.get_provider(provider_id)
        if not provider:
            return False, f"Provider '{provider_id}' not found"
        
        models = provider.get('models', [])
        if model_name not in models:
            return False, f"Model '{model_name}' not supported by provider '{provider_id}'. Available models: {', '.join(models[:5])}{'...' if len(models) > 5 else ''}"
        
        return True, ""
    
    def get_litellm_model_name(self, provider_id: str, model_name: str) -> str:
        """
        Convert provider/model to litellm format
        
        Args:
            provider_id: Provider identifier
            model_name: Model name
            
        Returns:
            Model name in litellm format
        """
        # For most providers, use model name as-is
        # Special handling for providers that need different formats
        if provider_id == 'openrouter':
            # OpenRouter uses provider/model format
            return f"{provider_id}/{model_name}"
        elif provider_id == 'together_ai':
            # Together AI uses repo/model format
            if '/' not in model_name:
                return f"togethercomputer/{model_name}"
        elif provider_id == 'replicate':
            # Replicate uses specific format
            if '/' not in model_name:
                return f"replicate/{model_name}"
        
        # Default: return as-is
        return model_name
    
    def display_providers(self):
        """Display all available providers in a formatted way"""
        print("\nAvailable Providers:")
        print("=" * 50)
        
        default_providers = [p for p in self.get_provider_list() if not p['is_custom']]
        custom_providers = [p for p in self.get_provider_list() if p['is_custom']]
        
        if default_providers:
            print("\nDefault Providers:")
            for i, provider in enumerate(default_providers, 1):
                print(f"  {i}. {provider['name']} ({provider['slug']})")
                print(f"     {provider['description']}")
        
        if custom_providers:
            print("\nCustom Providers:")
            for i, provider in enumerate(custom_providers, len(default_providers) + 1):
                print(f"  {i}. {provider['name']} ({provider['slug']})")
                print(f"     {provider['description']}")
        
        print("=" * 50)
        
        return len(default_providers) + len(custom_providers)
