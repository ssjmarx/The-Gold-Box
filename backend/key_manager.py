#!/usr/bin/env python3
"""
Enhanced multi-service API key storage with encryption and dynamic provider support
"""
import json
import os
import getpass
import hashlib
import re
from pathlib import Path
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.backends import default_backend
import base64
from datetime import datetime
from provider_manager import ProviderManager

class MultiKeyManager:
    def __init__(self, key_file='keys.enc'):
        self.key_file = Path(key_file)
        self.keys_data = {}
        self.master_password = None  # Consolidated password for encryption and admin
        self.provider_manager = ProviderManager()
        
    def clear_terminal(self):
        """Clear terminal for clean UI"""
        os.system('cls' if os.name == 'nt' else 'clear')
    
    def display_header(self):
        """Display professional header"""
        self.clear_terminal()
        print("=" * 60)
        print("The Gold Box API Key Manager")
        print("=" * 60)
    
    def _derive_key(self, password):
        """Derive encryption key from password"""
        if password is None:
            return None
        
        # Generate salt from password using a fixed method for consistency
        password_hash = hashlib.sha256(password.encode('utf-8')).digest()
        salt = password_hash[:16]  # Use first 16 bytes as salt
        
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
            backend=default_backend()
        )
        return base64.urlsafe_b64encode(kdf.derive(password.encode()))
    
    def _hash_password(self, password):
        """Hash password for verification storage"""
        if password is None:
            return None
        return hashlib.sha256(password.encode('utf-8')).hexdigest()
    
    def _verify_password(self, provided_password, stored_hash):
        """Verify password against stored hash"""
        if provided_password is None:
            return stored_hash is None
        return self._hash_password(provided_password) == stored_hash
    
    def load_keys(self):
        """Load and decrypt keys from file"""
        if not self.key_file.exists():
            return None
        
        try:
            with open(self.key_file, 'rb') as f:
                data = json.load(f)
            
            if data.get('encrypted', True):
                password = getpass.getpass("Enter password to unlock keys: ")
                return self.load_keys_with_password(password)
            else:
                # Unencrypted keys (legacy)
                self.keys_data = data.get('api_keys', {})
                self.master_password = None  # Legacy had no password
                return True
            
        except Exception as e:
            print(f"Failed to load keys: {e}")
            return False
    
    def load_keys_with_password(self, password):
        """Load and decrypt keys from file with provided password"""
        if not self.key_file.exists():
            return None
        
        try:
            with open(self.key_file, 'rb') as f:
                data = json.load(f)
            
            if data.get('encrypted', True):
                if password == "" and data.get('encrypted', True):
                    print("Keys are encrypted - password required")
                    return False
                
                key = self._derive_key(password)
                if key is None:
                    return False
                
                fernet = Fernet(key)
                decrypted_data = fernet.decrypt(data['encrypted_keys'].encode()).decode()
                parsed_data = json.loads(decrypted_data)
                
                self.keys_data = parsed_data.get('api_keys', {})
                self.master_password = password
            else:
                # Unencrypted keys (legacy)
                self.keys_data = data.get('api_keys', {})
                self.master_password = None
            
            return True
            
        except Exception as e:
            print(f"Failed to load keys: {e}")
            return False
    
    def get_password_status(self):
        """Get password status"""
        return self.master_password is not None and self.master_password != ''
    
    def set_password(self, password=None):
        """Set master password"""
        if password is None:
            while True:
                try:
                    password = getpass.getpass("Set master password: ")
                    if password == "":
                        print("Blank password - will set to empty after warning")
                        confirm = getpass.getpass("Confirm blank password (press Enter): ")
                        if confirm != "":
                            print("Confirmation doesn't match")
                            continue
                        print("WARNING: Master password will be empty - anyone can access admin functions!")
                        confirm_blank = input("Type 'YES' to confirm empty password: ")
                        if confirm_blank == 'YES':
                            self.master_password = ""
                            return True
                        else:
                            continue
                    else:
                        confirm = getpass.getpass("Confirm master password: ")
                        if password != confirm:
                            print("Passwords don't match")
                            continue
                        self.master_password = password
                        return True
                except KeyboardInterrupt:
                    print("\nPassword setup cancelled")
                    return False
        else:
            self.master_password = password
            return True
    
    def verify_password(self, provided_password):
        """Verify master password"""
        if self.master_password is None:
            return False, "No password set"
        
        return provided_password == self.master_password, None
    
    def save_keys(self, keys_data=None, password=None):
        """Encrypt and save keys to file"""
        if keys_data is not None:
            self.keys_data = keys_data
        
        # Ensure directory exists
        self.key_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Prepare data to save
        save_data = {
            'api_keys': self.keys_data,
            'password_hash': self._hash_password(self.master_password) if self.master_password else None
        }
        
        if self.master_password is None:
            # No password - save unencrypted (legacy support)
            data = {
                'encrypted': False,
                'api_keys': self.keys_data,
                'password_hash': None,
                'created_at': datetime.now().isoformat(),
                'version': '2.0'
            }
            with open(self.key_file, 'w') as f:
                json.dump(data, f, indent=2)
        else:
            # Encrypt with password
            key = self._derive_key(self.master_password)
            fernet = Fernet(key)
            encrypted_data = fernet.encrypt(json.dumps(save_data).encode())
            
            data = {
                'encrypted': True,
                'encrypted_keys': encrypted_data.decode(),
                'password_hash': self._hash_password(self.master_password),
                'created_at': datetime.now().isoformat(),
                'version': '2.0'
            }
            with open(self.key_file, 'w') as f:
                json.dump(data, f, indent=2)
        
        os.chmod(self.key_file, 0o600)
        print(f"Keys saved to {self.key_file}")
        return True
    
    def get_key_status(self):
        """Get current status of all keys"""
        if self.keys_data is None:
            self.keys_data = {}
        
        status = {}
        all_providers = self.provider_manager.get_all_providers()
        
        for provider_id in all_providers:
            provider = all_providers[provider_id]
            status[provider_id] = {
                'name': provider.get('name', provider_id),
                'set': provider_id in self.keys_data and self.keys_data[provider_id] != '',
                'is_custom': provider.get('is_custom', False),
                'id': provider_id
            }
        
        return status
    
    def add_key_flow(self):
        """Enhanced key addition with validation"""
        self.display_header()
        print("Add an API Key")
        print("-" * 60)
        
        # Display all available providers in compact format (5 per line)
        provider_list = self.provider_manager.get_provider_list()
        print("\nAvailable Providers:")
        print("=" * 50)
        
        for i in range(0, len(provider_list), 5):
            # Get up to 5 providers for this line
            line_providers = provider_list[i:i+5]
            
            # Format each provider with proper spacing
            line_text = ""
            for j, provider in enumerate(line_providers):
                if j < 4:  # First 4 items
                    line_text += f"{provider['name']:<20}"
                else:  # Last item
                    line_text += f"{provider['name']:<15}"
            
            print(line_text)
        
        print("=" * 50)
        print("Type provider name directly (case-insensitive)")
        
        while True:
            try:
                choice = input(f"\nEnter provider name: ").strip()
                
                if not choice:
                    print("Provider name required. Please try again.")
                    continue
                
                # Search for provider by name (case-insensitive)
                provider_slug = None
                provider_name = None
                
                choice_lower = choice.lower()
                for provider in provider_list:
                    if provider['name'].lower() == choice_lower:
                        provider_slug = provider['slug']
                        provider_name = provider['name']
                        break
                    # Also check slug
                    if provider['slug'].lower() == choice_lower.replace(' ', '_'):
                        provider_slug = provider['slug']
                        provider_name = provider['name']
                        break
                
                if not provider_slug:
                    # Try fuzzy matching
                    matches = []
                    for provider in provider_list:
                        if choice_lower in provider['name'].lower() or choice_lower in provider['slug'].lower():
                            matches.append(provider)
                    
                    if len(matches) == 1:
                        provider_slug = matches[0]['slug']
                        provider_name = matches[0]['name']
                    elif len(matches) > 1:
                        print(f"Multiple matches found: {', '.join([m['name'] for m in matches])}")
                        print("Please be more specific.")
                        continue
                    else:
                        print(f"Provider '{choice}' not found. Please check spelling or create a custom provider.")
                        print("\nAvailable providers include:", ", ".join([p['name'] for p in provider_list[:10]]), "...")
                        continue
                
                # Check if key already exists
                if provider_slug in self.keys_data and self.keys_data[provider_slug]:
                    overwrite = input(f"Key for {provider_name} already exists. Overwrite? (y/N): ").strip().lower()
                    if overwrite not in ['y', 'yes']:
                        print("Operation cancelled.")
                        return False
                
                # Get the API key
                print(f"\nEnter or paste (ctrl+shift+v) your {provider_name} API key:")
                api_key = getpass.getpass(f"{provider_name} API Key: ")
                
                if not api_key:
                    print("ERROR: No key provided - operation cancelled.")
                    print("Please enter a valid API key to continue.")
                    continue
                
                if len(api_key) < 8:
                    print("ERROR: Key too short - API keys must be at least 8 characters long")
                    print("Please enter a valid API key or try again.")
                    continue
                
                # Save the key
                if self.keys_data is None:
                    self.keys_data = {}
                
                self.keys_data[provider_slug] = api_key
                print(f"\n{provider_name} API key added successfully")
                
                # Ask if user wants to add another key
                another = input("\nAdd another key? (y/N): ").strip().lower()
                if another not in ['y', 'yes']:
                    break
                
            except KeyboardInterrupt:
                print("\nOperation cancelled.")
                return False
        
        return True
    
    def delete_key_flow(self):
        """Key deletion with confirmation"""
        self.display_header()
        print("Delete an API Key")
        print("-" * 60)
        
        # Show current keys
        status = self.get_key_status()
        existing_keys = {k: v for k, v in status.items() if v['set']}
        
        if not existing_keys:
            print("No API keys configured.")
            input("\nPress Enter to continue...")
            return True
        
        print("\nCurrent API Keys:")
        for i, (provider_id, info) in enumerate(existing_keys.items(), 1):
            marker = "[CUSTOM]" if info['is_custom'] else "[STANDARD]"
            print(f"  {i}. {marker} {info['name']} ({provider_id})")
        
        print("\n0. Cancel")
        
        while True:
            try:
                choice = input(f"\nEnter key number to delete (0 to cancel): ").strip()
                
                if choice == '0':
                    print("Operation cancelled.")
                    return True
                
                try:
                    choice_num = int(choice)
                    if 1 <= choice_num <= len(existing_keys):
                        provider_to_delete = list(existing_keys.keys())[choice_num - 1]
                        provider_info = existing_keys[provider_to_delete]
                        
                        confirm = input(f"\nDelete key for {provider_info['name']}? This cannot be undone. (y/N): ").strip().lower()
                        if confirm in ['y', 'yes']:
                            del self.keys_data[provider_to_delete]
                            print(f"\nKey for {provider_info['name']} deleted successfully")
                            break
                        else:
                            print("Operation cancelled.")
                            break
                    else:
                        print("Invalid number. Please try again.")
                except ValueError:
                    print("Invalid input. Please enter a number.")
                    
            except KeyboardInterrupt:
                print("\nOperation cancelled.")
                return True
        
        return True
    
    def change_password_flow(self):
        """Single password management"""
        self.display_header()
        print("Change Master Password")
        print("-" * 60)
        
        if self.master_password:
            print("Current password is set.")
            change = input("Change password? (y/N): ").strip().lower()
            if change not in ['y', 'yes']:
                print("Operation cancelled.")
                return True
        else:
            print("No password currently set.")
        
        # Set new password
        return self.set_password()
    
    def interactive_setup(self):
        """Enhanced interactive setup with professional menu"""
        while True:
            self.display_header()
            print("\n1. Add a Key")
            print("2. Delete a Key")
            print("3. Create a Custom Provider")
            print("4. Change Password")
            print("5. Finish and Start Server")
            
            try:
                choice = input("\nEnter your choice (1-5): ").strip()
                
                if choice == '1':
                    self.add_key_flow()
                elif choice == '2':
                    self.delete_key_flow()
                elif choice == '3':
                    self.create_custom_provider_flow()
                elif choice == '4':
                    self.change_password_flow()
                elif choice == '5':
                    # Check for password before starting server
                    if not self.get_password_status():
                        print("WARNING: No password set!")
                        print("It's highly recommended to set a password for security.")
                        confirm = input("Continue without password? (y/N): ").strip().lower()
                        if confirm not in ['y', 'yes']:
                            continue
                    
                    # Save keys and exit
                    print("\nSaving configuration...")
                    if self.save_keys():
                        print("SUCCESS: Configuration saved successfully")
                        print("\nStarting server...")
                        return True
                    else:
                        print("ERROR: Failed to save configuration")
                        input("Press Enter to continue...")
                else:
                    print("Invalid choice. Please try again.")
                    
            except KeyboardInterrupt:
                print("\n\nExiting setup...")
                # Clear terminal when key manager closes
                self.clear_terminal()
                return False
    
    def create_custom_provider_flow(self):
        """Enhanced custom provider creation wizard with comprehensive validation"""
        self.display_header()
        print("Create a Custom Provider")
        print("-" * 60)
        print("This wizard helps you add custom AI providers to The Gold Box")
        print("Supports OpenAI-compatible APIs and custom authentication methods")
        print("-" * 60)
        
        config = {}
        
        try:
            # === BASIC SETUP ===
            print("\n=== BASIC SETUP ===")
            print("Configure the basic information for your custom provider")
            
            # Provider Slug with validation
            while True:
                slug = input("Provider Slug (unique identifier, e.g., my-company-llm): ").strip().lower()
                if not slug:
                    print("ERROR: Slug is required.")
                    continue
                
                # Validate slug format
                if not re.match(r'^[a-z0-9_-]+$', slug):
                    print("ERROR: Slug can only contain lowercase letters, numbers, hyphens, and underscores.")
                    continue
                
                if len(slug) > 50:
                    print("ERROR: Slug must be 50 characters or less.")
                    continue
                
                # Check if slug already exists
                existing_provider = self.provider_manager.get_provider(slug)
                if existing_provider:
                    provider_name = existing_provider.get('name', slug)
                    print(f"WARNING: Provider '{slug}' already exists ({provider_name}).")
                    overwrite = input("Overwrite existing provider? (y/N): ").strip().lower()
                    if overwrite not in ['y', 'yes']:
                        print("Please choose a different slug.")
                        continue
                    print(f"Will overwrite existing provider '{provider_name}'")
                break
            
            config['slug'] = slug
            
            # Display Name with validation
            while True:
                name = input("Display Name (e.g., My Company LLM): ").strip()
                if not name:
                    name = slug.replace('-', ' ').title()
                    print(f"Using generated name: {name}")
                
                if len(name) > 100:
                    print("ERROR: Display name must be 100 characters or less.")
                    continue
                
                break
            
            config['name'] = name
            
            # Description (optional but recommended)
            description = input("Description (optional, e.g., Fast inference for custom models): ").strip()
            if description:
                if len(description) > 500:
                    print("WARNING: Description truncated to 500 characters.")
                    description = description[:500]
                config['description'] = description
            else:
                config['description'] = f"Custom provider: {name}"
            
            # Model Names (support multiple models)
            print("\nModel Configuration:")
            print("Enter model names supported by this provider (comma-separated)")
            print("Examples: gpt-4, claude-3, my-custom-model")
            
            while True:
                models_input = input("Models (comma-separated): ").strip()
                if not models_input:
                    # Generate default model name from slug
                    default_model = slug.replace('-', '').replace('_', '')
                    models = [default_model]
                    print(f"Using default model: {default_model}")
                else:
                    # Parse and validate models
                    models = [model.strip() for model in models_input.split(',')]
                    models = [model for model in models if model]  # Remove empty strings
                    
                    if not models:
                        print("ERROR: At least one model is required.")
                        continue
                    
                    # Validate each model name
                    invalid_models = []
                    for model in models:
                        if not re.match(r'^[a-zA-Z0-9._-]+$', model):
                            invalid_models.append(model)
                    
                    if invalid_models:
                        print(f"ERROR: Invalid model names: {', '.join(invalid_models)}")
                        print("Model names can only contain letters, numbers, dots, hyphens, and underscores.")
                        continue
                
                config['models'] = models[:10]  # Limit to 10 models
                if len(models) > 10:
                    print(f"WARNING: Limited to first 10 models: {', '.join(models[:10])}")
                break
            
            # === API CONNECTION ===
            print("\n=== API CONNECTION ===")
            print("Configure how to connect to your provider's API")
            
            # Base URL with enhanced validation
            while True:
                base_url = input("Base URL (e.g., https://api.mycompany.com/ai/v1): ").strip()
                if not base_url:
                    print("ERROR: Base URL is required.")
                    continue
                
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
                    print("ERROR: Invalid URL format. Please enter a complete URL.")
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
            
            while True:
                auth_choice = input("Choose auth type (1-5): ").strip()
                if auth_choice == '1':
                    config['auth_type'] = 'Bearer Token'
                    config['auth_header'] = 'Authorization'
                    config['auth_prefix'] = 'Bearer '
                    break
                elif auth_choice == '2':
                    header_name = input("Enter header name (e.g., X-API-Key): ").strip()
                    if not header_name:
                        print("ERROR: Header name is required.")
                        continue
                    config['auth_type'] = 'API Key Header'
                    config['auth_header'] = header_name
                    config['auth_prefix'] = ''
                    break
                elif auth_choice == '3':
                    param_name = input("Enter query parameter name (e.g., api_key): ").strip()
                    if not param_name:
                        print("ERROR: Parameter name is required.")
                        continue
                    config['auth_type'] = 'API Key Query'
                    config['auth_query_param'] = param_name
                    break
                elif auth_choice == '4':
                    print("Basic Authentication:")
                    username = input("Username: ").strip()
                    password = getpass.getpass("Password: ")
                    if not username or not password:
                        print("ERROR: Both username and password are required.")
                        continue
                    config['auth_type'] = 'Basic Auth'
                    config['auth_username'] = username
                    config['auth_password'] = password
                    break
                elif auth_choice == '5':
                    header_name = input("Enter header name: ").strip()
                    header_value = input("Enter header value: ").strip()
                    if not header_name or not header_value:
                        print("ERROR: Both header name and value are required.")
                        continue
                    config['auth_type'] = 'Custom Header'
                    config['auth_header'] = header_name
                    config['auth_value'] = header_value
                    break
                else:
                    print("ERROR: Invalid choice. Please enter 1-5.")
            
            # Completion Endpoint with validation
            while True:
                endpoint = input("Completion Endpoint (e.g., /chat/completions): ").strip()
                if not endpoint:
                    print("ERROR: Completion endpoint is required.")
                    continue
                
                if not endpoint.startswith('/'):
                    print("ERROR: Completion endpoint must start with /")
                    continue
                
                # Validate endpoint path
                if not re.match(r'^/[a-zA-Z0-9/_{}.-]*$', endpoint):
                    print("ERROR: Invalid endpoint format. Use letters, numbers, /, _, -, .")
                    continue
                
                break
            
            config['completion_endpoint'] = endpoint
            
            # === ADVANCED OPTIONS ===
            print("\n=== ADVANCED OPTIONS ===")
            print("Configure advanced request/response mapping for non-standard APIs")
            print("Leave blank to use OpenAI-compatible defaults")
            
            advanced = input("Configure advanced options? (y/N): ").strip().lower()
            if advanced in ['y', 'yes']:
                self._configure_advanced_options(config)
            
            # === REVIEW & CONFIRM ===
            self.display_header()
            print("Review Custom Provider Configuration")
            print("=" * 60)
            
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
                action = input("\nChoose action (1-4): ").strip()
                
                if action == '1':
                    # Validate configuration before saving
                    is_valid, error_msg = self._validate_provider_config(config)
                    if not is_valid:
                        print(f"\nERROR: Configuration validation failed:")
                        print(f"  {error_msg}")
                        print("\nPlease fix the issues and try again.")
                        input("Press Enter to continue...")
                        return self.create_custom_provider_flow()  # Restart flow
                    
                    # Save custom provider
                    print(f"\nSaving custom provider '{config['name']}'...")
                    
                    if self.provider_manager.add_custom_provider(config['slug'], config):
                        print(f"SUCCESS: Custom provider '{config['name']}' saved successfully")
                        print(f"  - Slug: {config['slug']}")
                        print(f"  - Models: {', '.join(config['models'])}")
                        print(f"  - Endpoint: {config['base_url']}{config['completion_endpoint']}")
                        print("\nTip: You can now add an API key for this provider in the key manager.")
                        
                        # Ask if user wants to add API key now
                        add_key = input("\nAdd API key for this provider now? (y/N): ").strip().lower()
                        if add_key in ['y', 'yes']:
                            return self._add_key_for_provider(config['slug'], config['name'])
                        
                        return True
                    else:
                        print(f"ERROR: Failed to save custom provider '{config['name']}'")
                        print("Please check the configuration and try again.")
                        input("Press Enter to continue...")
                        return False
                
                elif action == '2':
                    # Test connection (basic validation)
                    print(f"\nTesting connection to {config['base_url']}...")
                    if self._test_provider_connection(config):
                        print("SUCCESS: Connection test passed")
                        input("Press Enter to continue...")
                    else:
                        print("WARNING: Connection test failed")
                        print("The provider may not be accessible or may require different configuration.")
                        input("Press Enter to continue...")
                    # Return to menu after test
                    return True
                
                elif action == '3':
                    print("\nRestarting configuration...")
                    return self.create_custom_provider_flow()  # Restart flow
                
                elif action == '4':
                    print("\nOperation cancelled.")
                    return True
                
                else:
                    print("ERROR: Invalid choice. Please enter 1-4.")
                    
        except KeyboardInterrupt:
            print("\n\nOperation cancelled by user.")
            return True
        except Exception as e:
            print(f"\nERROR: Unexpected error during provider creation: {e}")
            print("Please try again or contact support if the issue persists.")
            input("Press Enter to continue...")
            return False
    
    def _configure_advanced_options(self, config):
        """Configure advanced options for custom provider"""
        print("\n=== REQUEST MAPPING ===")
        
        # Messages Key
        messages_key = input("Messages Key (default: messages): ").strip()
        if messages_key:
            config.setdefault('request_mapping', {})['messages_key'] = messages_key
        
        # Max Tokens Alias
        max_tokens_alias = input("max_tokens Alias (leave blank if same): ").strip()
        if max_tokens_alias:
            config.setdefault('request_mapping', {})['max_tokens_alias'] = max_tokens_alias
        
        # Temperature Alias
        temp_alias = input("temperature Alias (leave blank if same): ").strip()
        if temp_alias:
            config.setdefault('request_mapping', {})['temperature_alias'] = temp_alias
        
        print("\n=== RESPONSE MAPPING ===")
        
        # Content Path
        content_path = input("Content Path (default: choices[0].message.content): ").strip()
        if content_path:
            config.setdefault('response_mapping', {})['content_path'] = content_path
        
        # Usage Object Path
        usage_path = input("Usage Object Path (default: usage): ").strip()
        if usage_path:
            config.setdefault('response_mapping', {})['usage_path'] = usage_path
        
        # Error Message Path
        error_path = input("Error Message Path (default: error.message): ").strip()
        if error_path:
            config.setdefault('response_mapping', {})['error_path'] = error_path
        
        print("\nSUCCESS: Advanced options configured")
    
    def set_environment_variables(self):
        """Set API keys as environment variables for all providers"""
        if self.keys_data is None:
            print("No keys loaded")
            return False
        
        for provider_id, api_key in self.keys_data.items():
            if api_key:
                env_key = f'{provider_id.upper()}_API_KEY'
                os.environ[env_key] = api_key
                print(f"{provider_id} API key loaded into environment")
        
        return True
    
    def get_provider_manager(self):
        """Get provider manager instance"""
        return self.provider_manager
    
    def load_default_providers(self):
        """Load default providers (delegated to provider_manager)"""
        return self.provider_manager.load_default_providers()
    
    def load_custom_providers(self):
        """Load custom providers (delegated to provider_manager)"""
        return self.provider_manager.load_custom_providers()
    
    def get_all_providers(self):
        """Get all providers (delegated to provider_manager)"""
        return self.provider_manager.get_all_providers()
    
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
            import re
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
            import requests
            import ssl
            
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
    
    def _add_key_for_provider(self, provider_slug, provider_name):
        """Add API key for a specific provider"""
        self.display_header()
        print(f"Add API Key for {provider_name}")
        print("-" * 60)
        print(f"Provider Slug: {provider_slug}")
        
        try:
            # Get the API key
            print(f"\nEnter or paste (ctrl+shift+v) your {provider_name} API key:")
            api_key = getpass.getpass(f"{provider_name} API Key: ")
            
            if not api_key:
                print("ERROR: No key provided - operation cancelled.")
                return False
            
            if len(api_key) < 8:
                print("ERROR: Key too short - API keys must be at least 8 characters long")
                return False
            
            # Save the key
            if self.keys_data is None:
                self.keys_data = {}
            
            self.keys_data[provider_slug] = api_key
            print(f"\nSUCCESS: {provider_name} API key added successfully")
            
            return True
            
        except KeyboardInterrupt:
            print("\nOperation cancelled.")
            return False
        except Exception as e:
            print(f"\nERROR: Failed to add API key: {e}")
            return False
    
    def save_and_exit(self):
        """Save keys and start server"""
        print("\nSaving configuration...")
        if self.save_keys():
            print("SUCCESS: Configuration saved successfully")
            print("\nStarting server...")
            # Clear terminal when key manager closes
            self.clear_terminal()
            return True
        else:
            print("ERROR: Failed to save configuration")
            input("Press Enter to continue...")
            return False
