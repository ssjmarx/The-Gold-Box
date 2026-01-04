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

class ProviderManagerException(Exception):
    """Exception raised when provider manager operations fail"""
    pass

# Get absolute path to backend directory (where server.py is located)
BACKEND_DIR = Path(__file__).parent.parent.parent.absolute()

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
        print("Loading providers from JSON...")
        
        try:
            # Load provider list from file as single source of truth
            with open(get_absolute_path('shared/server_files/litellm_providers.json'), 'r') as f:
                provider_data = json.load(f)
                providers_list = provider_data['providers']
                provider_details = provider_data['provider_details']
                
                # Create provider definitions from JSON data only
                self.default_providers = {}
                
                # Process all providers from JSON file
                for provider_slug in providers_list:
                    provider_info = provider_details.get(provider_slug, {})
                    model_count = provider_info.get('model_count', 0)
                    sample_models = provider_info.get('sample_models', [])
                    
                    self.default_providers[provider_slug] = {
                        'slug': provider_slug,
                        'name': provider_info.get('name', provider_slug.replace('_', ' ').title()),
                        'description': provider_info.get('description', f'{model_count} models available'),
                        'models': sample_models,
                        'auth_type': provider_info.get('auth_type', 'Bearer Token'),
                        'requires_auth': provider_info.get('requires_auth', True),  # Default: true
                        'provider_type': provider_info.get('provider_type', 'remote'),  # Default: remote
                        'base_url': provider_info.get('base_url', ''),
                        'default_base_url': provider_info.get('default_base_url', ''),  # For local providers
                        'completion_endpoint': provider_info.get('completion_endpoint', '/v1/chat/completions'),
                        'is_custom': False
                    }
                    
        except FileNotFoundError:
            # If no provider list file, proper error - no silent fallbacks
            raise FileNotFoundError(
                f"Provider configuration file not found: {get_absolute_path('shared/server_files/litellm_providers.json')}. "
                f"Please ensure the litellm_providers.json file exists in the shared/server_files directory."
            )
        except Exception as e:
            # Proper error handling - no silent failures
            raise RuntimeError(f"Error loading provider configuration: {e}")
                
        print(f"Loaded {len(self.default_providers)} providers from JSON")
    
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
                
        except (json.JSONDecodeError, FileNotFoundError, PermissionError) as e:
            print(f"Error loading custom providers: {e}")
            self.custom_providers = {}
            raise ProviderManagerException(f"Failed to load custom providers: {e}")
        except Exception as e:
            print(f"Unexpected error loading custom providers: {e}")
            self.custom_providers = {}
            raise ProviderManagerException(f"Unexpected error loading custom providers: {e}")
    
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
            
        except (ValueError, KeyError) as e:
            print(f"Error adding custom provider: {e}")
            raise ProviderManagerException(f"Invalid custom provider data: {e}")
        except Exception as e:
            print(f"Error adding custom provider: {e}")
            raise ProviderManagerException(f"Failed to add custom provider: {e}")
    
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
                
        except (KeyError, PermissionError) as e:
            print(f"Error removing custom provider: {e}")
            raise ProviderManagerException(f"Failed to remove custom provider '{slug}': {e}")
        except Exception as e:
            print(f"Error removing custom provider: {e}")
            raise ProviderManagerException(f"Unexpected error removing custom provider '{slug}': {e}")
    
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
            
        except (PermissionError, OSError) as e:
            print(f"Error saving custom providers: {e}")
            raise ProviderManagerException(f"Permission error saving custom providers: {e}")
        except Exception as e:
            print(f"Error saving custom providers: {e}")
            raise ProviderManagerException(f"Failed to save custom providers: {e}")
    
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
            # Import litellm locally to avoid global import
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
            raise ProviderManagerException("LiteLLM library is required but not available")
        except Exception as e:
            print(f"ERROR: Failed to configure provider '{provider_id}': {e}")
            raise ProviderManagerException(f"Failed to configure provider '{provider_id}': {e}")
    
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
