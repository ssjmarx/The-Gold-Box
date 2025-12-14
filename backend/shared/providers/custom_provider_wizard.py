#!/usr/bin/env python3
"""
Custom provider creation wizard
Handles configuration, validation, and testing of custom AI providers
"""
import re
import ssl
import requests
from datetime import datetime

class CustomProviderWizard:
    """Wizard for creating and managing custom AI providers"""
    
    def __init__(self, provider_manager):
        self.provider_manager = provider_manager
    
    def create_custom_provider_flow(self):
        """Enhanced custom provider creation wizard with comprehensive validation"""
        from ui.cli_manager import CLIManager
        
        CLIManager.display_header("Create a Custom Provider")
        print("This wizard helps you add custom AI providers to The Gold Box")
        print("Supports OpenAI-compatible APIs and custom authentication methods")
        print("-" * 60)
        
        config = {}
        
        try:
            # === BASIC SETUP ===
            config.update(self._configure_basic_setup())
            
            # === API CONNECTION ===
            config.update(self._configure_api_connection())
            
            # === ADVANCED OPTIONS ===
            advanced = CLIManager.get_yes_no("Configure advanced options")
            if advanced:
                config.update(self._configure_advanced_options())
            
            # === REVIEW & CONFIRM ===
            return self._review_and_confirm(config)
            
        except KeyboardInterrupt:
            print("\n\nOperation cancelled by user.")
            return False
        except Exception as e:
            print(f"\nERROR: Unexpected error during provider creation: {e}")
            print("Please try again or contact support if issue persists.")
            CLIManager.wait_for_enter()
            return False
    
    def _configure_basic_setup(self):
        """Configure basic provider information"""
        from ui.cli_manager import CLIManager
        
        print("\n=== BASIC SETUP ===")
        print("Configure basic information for your custom provider")
        
        config = {}
        
        # Provider Slug with validation
        while True:
            slug = CLIManager.get_text_input(
                "Provider Slug (unique identifier, e.g., my-company-llm): ",
                required=True,
                max_length=50,
                validation_pattern=r'^[a-z0-9_-]+$'
            )
            if slug is None:
                return None
            
            # Check if slug already exists
            existing_provider = self.provider_manager.get_provider(slug)
            if existing_provider:
                provider_name = existing_provider.get('name', slug)
                CLIManager.display_warning(f"Provider '{slug}' already exists ({provider_name}).")
                overwrite = CLIManager.get_yes_no("Overwrite existing provider?")
                if not overwrite:
                    CLIManager.display_warning("Please choose a different slug.")
                    continue
                print(f"Will overwrite existing provider '{provider_name}'")
            break
        
        config['slug'] = slug
        
        # Display Name with validation
        name = CLIManager.get_text_input(
            "Display Name (e.g., My Company LLM): ",
            required=False,
            max_length=100
        )
        if not name:
            name = slug.replace('-', ' ').title()
            print(f"Using generated name: {name}")
        config['name'] = name
        
        # Description (optional but recommended)
        description = CLIManager.get_text_input(
            "Description (optional, e.g., Fast inference for custom models): ",
            required=False,
            max_length=500
        )
        if description:
            config['description'] = description
        else:
            config['description'] = f"Custom provider: {name}"
        
        # Model Names (support multiple models)
        models = self._configure_models()
        config['models'] = models
        
        return config
    
    def _configure_models(self):
        """Configure model names for the provider"""
        from ui.cli_manager import CLIManager
        
        print("\nModel Configuration:")
        print("Enter model names supported by this provider (comma-separated)")
        print("Examples: gpt-4, claude-3, my-custom-model")
        
        while True:
            models_input = CLIManager.get_text_input(
                "Models (comma-separated): ",
                required=False
            )
            if models_input is None:
                return None
            
            if not models_input:
                # Generate default model name from slug
                # This will be handled by caller
                return []
            
            # Parse and validate models
            models = [model.strip() for model in models_input.split(',')]
            models = [model for model in models if model]  # Remove empty strings
            
            if not models:
                CLIManager.display_error("At least one model is required.")
                continue
            
            # Validate each model name
            invalid_models = []
            for model in models:
                if not re.match(r'^[a-zA-Z0-9._-]+$', model):
                    invalid_models.append(model)
            
            if invalid_models:
                CLIManager.display_error(f"Invalid model names: {', '.join(invalid_models)}")
                print("Model names can only contain letters, numbers, dots, hyphens, and underscores.")
                continue
            
            return models[:10]  # Limit to 10 models
    
    def _configure_api_connection(self):
        """Configure API connection settings"""
        from ui.cli_manager import CLIManager
        
        print("\n=== API CONNECTION ===")
        print("Configure how to connect to your provider's API")
        
        config = {}
        
        # Base URL with enhanced validation
        while True:
            base_url = CLIManager.get_text_input(
                "Base URL (e.g., https://api.mycompany.com/ai/v1): ",
                required=True
            )
            if base_url is None:
                return None
            
            # Enhanced URL validation
            url_pattern = re.compile(
                r'^https?:\/\/'  # Protocol
                r'(?:\S+(?::\S*)?@)?'  # Optional authentication
                r'(?:[a-z0-9\u00a1-\uffff-]+\.)*[a-z0-9\u00a1-\uffff-]+'  # Domain
                r'(?:\.[a-z0-9\u00a1-\uffff-]+)*'  # Subdomains
                r'\.[a-z\u00a1-\uffff]{2,}'  # TLD
                r'(?::\d{2,5})?'  # Optional port
                r'(?:[/?#]\S*)?$',  # Optional path/query
                re.IGNORECASE
            )
            
            if not url_pattern.match(base_url):
                CLIManager.display_error("Invalid URL format. Please enter a complete URL.")
                print("Example: https://api.mycompany.com/ai/v1")
                continue
            
            # Ensure no trailing slash for consistency
            base_url = base_url.rstrip('/')
            break
        
        config['base_url'] = base_url
        
        # Enhanced Auth Type with more options
        print("\nAuthentication Type:")
        print("1. Bearer Token (Standard JWT/API token in Authorization header)")
        print("2. API Key in Header (Custom header name)")
        print("3. API Key in Query Parameter")
        print("4. Basic Authentication (Username:Password)")
        print("5. Custom Header (Specify header name and value)")
        
        auth_config = self._configure_authentication()
        config.update(auth_config)
        
        # Completion Endpoint with validation
        while True:
            endpoint = CLIManager.get_text_input(
                "Completion Endpoint (e.g., /chat/completions): ",
                required=True,
                validation_pattern=r'^/[a-zA-Z0-9/_{}.-]*$'
            )
            if endpoint is None:
                return None
            
            if not endpoint.startswith('/'):
                CLIManager.display_error("Completion endpoint must start with /")
                continue
            
            break
        
        config['completion_endpoint'] = endpoint
        return config
    
    def _configure_authentication(self):
        """Configure authentication method"""
        from ui.cli_manager import CLIManager
        
        while True:
            auth_choice = CLIManager.get_menu_choice([1, 2, 3, 4, 5], "Choose auth type")
            if auth_choice is None:
                return None
            
            if auth_choice == 1:
                return {
                    'auth_type': 'Bearer Token',
                    'auth_header': 'Authorization',
                    'auth_prefix': 'Bearer '
                }
            elif auth_choice == 2:
                header_name = CLIManager.get_text_input(
                    "Enter header name (e.g., X-API-Key): ",
                    required=True
                )
                if header_name is None:
                    continue
                return {
                    'auth_type': 'API Key Header',
                    'auth_header': header_name,
                    'auth_prefix': ''
                }
            elif auth_choice == 3:
                param_name = CLIManager.get_text_input(
                    "Enter query parameter name (e.g., api_key): ",
                    required=True
                )
                if param_name is None:
                    continue
                return {
                    'auth_type': 'API Key Query',
                    'auth_query_param': param_name
                }
            elif auth_choice == 4:
                print("Basic Authentication:")
                username = CLIManager.get_text_input("Username: ", required=True)
                if username is None:
                    continue
                password = CLIManager.get_password_input("Password: ")
                if password is None:
                    continue
                return {
                    'auth_type': 'Basic Auth',
                    'auth_username': username,
                    'auth_password': password
                }
            elif auth_choice == 5:
                header_name = CLIManager.get_text_input("Enter header name: ", required=True)
                if header_name is None:
                    continue
                header_value = CLIManager.get_text_input("Enter header value: ", required=True)
                if header_value is None:
                    continue
                return {
                    'auth_type': 'Custom Header',
                    'auth_header': header_name,
                    'auth_value': header_value
                }
    
    def _configure_advanced_options(self):
        """Configure advanced request/response mapping"""
        from ui.cli_manager import CLIManager
        
        print("\n=== REQUEST MAPPING ===")
        
        config = {}
        
        # Messages Key
        messages_key = CLIManager.get_text_input(
            "Messages Key (default: messages): ",
            required=False
        )
        if messages_key:
            config.setdefault('request_mapping', {})['messages_key'] = messages_key
        
        # Max Tokens Alias
        max_tokens_alias = CLIManager.get_text_input(
            "max_tokens Alias (leave blank if same): ",
            required=False
        )
        if max_tokens_alias:
            config.setdefault('request_mapping', {})['max_tokens_alias'] = max_tokens_alias
        
        # Temperature Alias
        temp_alias = CLIManager.get_text_input(
            "temperature Alias (leave blank if same): ",
            required=False
        )
        if temp_alias:
            config.setdefault('request_mapping', {})['temperature_alias'] = temp_alias
        
        print("\n=== RESPONSE MAPPING ===")
        
        # Content Path
        content_path = CLIManager.get_text_input(
            "Content Path (default: choices[0].message.content): ",
            required=False
        )
        if content_path:
            config.setdefault('response_mapping', {})['content_path'] = content_path
        
        # Usage Object Path
        usage_path = CLIManager.get_text_input(
            "Usage Object Path (default: usage): ",
            required=False
        )
        if usage_path:
            config.setdefault('response_mapping', {})['usage_path'] = usage_path
        
        # Error Message Path
        error_path = CLIManager.get_text_input(
            "Error Message Path (default: error.message): ",
            required=False
        )
        if error_path:
            config.setdefault('response_mapping', {})['error_path'] = error_path
        
        CLIManager.display_success("Advanced options configured")
        return config
    
    def _review_and_confirm(self, config):
        """Review configuration and confirm with user"""
        from ui.cli_manager import CLIManager
        
        CLIManager.display_header("Review Custom Provider Configuration")
        print("=" * 60)
        
        # Generate default model if none provided
        if not config.get('models'):
            default_model = config['slug'].replace('-', '').replace('_', '')
            config['models'] = [default_model]
            print(f"Using default model: {default_model}")
        
        # Basic info
        print(f"Slug: {config['slug']}")
        print(f"Name: {config['name']}")
        print(f"Description: {config['description']}")
        print(f"Models: {', '.join(config['models'])}")
        
        # API info
        print(f"\nAPI Configuration:")
        print(f"Base URL: {config['base_url']}")
        print(f"Auth Type: {config['auth_type']}")
        print(f"Completion Endpoint: {config['completion_endpoint']}")
        
        # Advanced options
        if 'request_mapping' in config:
            print(f"\nRequest Mapping: {config['request_mapping']}")
        if 'response_mapping' in config:
            print(f"Response Mapping: {config['response_mapping']}")
        
        # Test URL construction
        test_url = f"{config['base_url']}{config['completion_endpoint']}"
        print(f"\nFull Endpoint URL: {test_url}")
        
        print("\n" + "=" * 60)
        print("OPTIONS:")
        print("1. Confirm and Save")
        print("2. Test Connection (requires API key)")
        print("3. Edit Configuration")
        print("4. Cancel")
        
        while True:
            action = CLIManager.get_menu_choice([1, 2, 3, 4], "Choose action")
            if action is None:
                return False
            
            if action == 1:
                return self._confirm_and_save(config)
            elif action == 2:
                return self._test_connection(config)
            elif action == 3:
                CLIManager.display_warning("\nRestarting configuration...")
                return self.create_custom_provider_flow()  # Restart flow
            elif action == 4:
                CLIManager.display_warning("\nOperation cancelled.")
                return True
    
    def _confirm_and_save(self, config):
        """Validate and save the provider configuration"""
        from ui.cli_manager import CLIManager
        
        # Validate configuration before saving
        is_valid, error_msg = self._validate_provider_config(config)
        if not is_valid:
            CLIManager.display_error(f"Configuration validation failed:")
            print(f"  {error_msg}")
            print("\nPlease fix issues and try again.")
            CLIManager.wait_for_enter()
            return self.create_custom_provider_flow()  # Restart flow
        
        # Save custom provider
        CLIManager.display_warning(f"\nSaving custom provider '{config['name']}'...")
        
        if self.provider_manager.add_custom_provider(config['slug'], config):
            CLIManager.display_success(f"Custom provider '{config['name']}' saved successfully")
            print(f"  - Slug: {config['slug']}")
            print(f"  - Models: {', '.join(config['models'])}")
            print(f"  - Endpoint: {config['base_url']}{config['completion_endpoint']}")
            print("\nTip: You can now add an API key for this provider in key manager.")
            return True
        else:
            CLIManager.display_error(f"Failed to save custom provider '{config['name']}'")
            print("Please check configuration and try again.")
            CLIManager.wait_for_enter()
            return False
    
    def _test_connection(self, config):
        """Test basic connection to provider endpoint"""
        from ui.cli_manager import CLIManager
        
        CLIManager.display_warning(f"\nTesting connection to {config['base_url']}...")
        if self._test_provider_connection(config):
            CLIManager.display_success("Connection test passed")
            CLIManager.wait_for_enter()
        else:
            CLIManager.display_warning("Connection test failed")
            print("The provider may not be accessible or may require different configuration.")
            CLIManager.wait_for_enter()
        return True  # Return to menu after test
    
    def _validate_provider_config(self, config):
        """Validate custom provider configuration"""
        try:
            # Required fields
            required_fields = ['slug', 'name', 'base_url', 'auth_type', 'completion_endpoint']
            for field in required_fields:
                if field not in config or not config[field]:
                    return False, f"Missing required field: {field}"
            
            # Validate models
            if 'models' not in config or not config['models']:
                return False, "At least one model is required"
            
            # Validate URL format
            url_pattern = re.compile(
                r'^https?:\/\/'  # Protocol
                r'(?:\S+(?::\S*)?@)?'  # Optional authentication
                r'(?:[a-z0-9\u00a1-\uffff-]+\.)*[a-z0-9\u00a1-\uffff-]+'  # Domain
                r'(?:\.[a-z0-9\u00a1-\uffff-]+)*'  # Subdomains
                r'\.[a-z\u00a1-\uffff]{2,}'  # TLD
                r'(?::\d{2,5})?'  # Optional port
                r'(?:[/?#]\S*)?$',  # Optional path/query
                re.IGNORECASE
            )
            
            if not url_pattern.match(config['base_url']):
                return False, "Invalid base URL format"
            
            # Validate auth type
            valid_auth_types = ['Bearer Token', 'API Key Header', 'API Key Query', 'Basic Auth', 'Custom Header']
            if config['auth_type'] not in valid_auth_types:
                return False, f"Invalid auth type: {config['auth_type']}"
            
            # Validate endpoint
            if not config['completion_endpoint'].startswith('/'):
                return False, "Completion endpoint must start with /"
            
            return True, ""
            
        except Exception as e:
            return False, f"Validation error: {str(e)}"
    
    def _test_provider_connection(self, config):
        """Test basic connection to provider endpoint"""
        try:
            # Test URL construction
            test_url = f"{config['base_url']}{config['completion_endpoint']}"
            
            print(f"Attempting to connect to: {test_url}")
            
            # Basic connection test (no authentication required for basic test)
            response = requests.get(
                test_url,
                timeout=10,
                verify=ssl.create_default_context()
            )
            
            # Check if server responds (even with error)
            if response.status_code < 500:
                print(f"Server responded with status: {response.status_code}")
                return True
            else:
                print(f"Server error status: {response.status_code}")
                return False
                
        except requests.exceptions.Timeout:
            print("Connection timeout - server may be slow or unavailable")
            return False
        except requests.exceptions.ConnectionError:
            print("Connection failed - check URL or network connectivity")
            return False
        except requests.exceptions.SSLError:
            print("SSL/TLS error - certificate issues or invalid HTTPS")
            return False
        except Exception as e:
            print(f"Connection test failed: {str(e)}")
            return False
