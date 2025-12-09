#!/usr/bin/env python3
"""
Key storage operations
Handles file I/O, key data management, and environment variables
"""
import json
import os
from pathlib import Path
from datetime import datetime
from security.key_crypto import KeyCrypto

# Get absolute path to backend directory
BACKEND_DIR = Path(__file__).parent.parent.absolute()

def get_absolute_path(relative_path: str) -> Path:
    """Convert a relative path to an absolute path based on backend directory"""
    return (BACKEND_DIR / relative_path).resolve()

class KeyStorage:
    """Handles storage and retrieval of API keys"""
    
    def __init__(self, key_file='server_files/keys.enc'):
        self.key_file = get_absolute_path(key_file)
        self.keys_data = {}
        self.master_password = None
    
    def load_keys(self):
        """Load and decrypt keys from file"""
        if not self.key_file.exists():
            return None
        
        try:
            with open(self.key_file, 'rb') as f:
                data = json.load(f)
            
            if data.get('encrypted', True):
                import getpass
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
                
                decrypted_data = KeyCrypto.decrypt_data(
                    data['encrypted_keys'], 
                    password
                )
                if decrypted_data is None:
                    print("Invalid password")
                    return False
                
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
            from ui.cli_manager import CLIManager
            
            while True:
                try:
                    password = CLIManager.get_password_input("Set master password: ")
                    if password == "":
                        print("Blank password - will set to empty after warning")
                        confirm = CLIManager.get_password_input("Confirm blank password (press Enter): ")
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
                        confirm = CLIManager.get_password_input("Confirm master password: ")
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
    
    def save_keys(self, keys_data=None):
        """Encrypt and save keys to file"""
        if keys_data is not None:
            self.keys_data = keys_data
        
        # Don't save if there's no data to save (no keys, no password)
        if not self.keys_data and not self.master_password:
            print("No data to save - skipping file creation")
            return True
        
        # Ensure directory exists
        self.key_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Prepare data to save
        save_data = {
            'api_keys': self.keys_data,
            'password_hash': KeyCrypto.hash_password(self.master_password) if self.master_password else None
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
            encrypted_data = KeyCrypto.encrypt_data(
                json.dumps(save_data), 
                self.master_password
            )
            if encrypted_data is None:
                print("Failed to encrypt data")
                return False
            
            data = {
                'encrypted': True,
                'encrypted_keys': encrypted_data.decode(),
                'password_hash': KeyCrypto.hash_password(self.master_password),
                'created_at': datetime.now().isoformat(),
                'version': '2.0'
            }
            with open(self.key_file, 'w') as f:
                json.dump(data, f, indent=2)
        
        os.chmod(self.key_file, 0o600)
        print(f"Keys saved to {self.key_file}")
        return True
    
    def get_key_status(self, provider_manager):
        """Get current status of all keys"""
        if self.keys_data is None:
            self.keys_data = {}
        
        status = {}
        all_providers = provider_manager.get_all_providers()
        
        for provider_id in all_providers:
            provider = all_providers[provider_id]
            status[provider_id] = {
                'name': provider.get('name', provider_id),
                'set': provider_id in self.keys_data and self.keys_data[provider_id] != '',
                'is_custom': provider.get('is_custom', False),
                'id': provider_id
            }
        
        return status
    
    def add_key(self, provider_slug, api_key):
        """Add an API key for a provider"""
        if self.keys_data is None:
            self.keys_data = {}
        
        self.keys_data[provider_slug] = api_key
    
    def remove_key(self, provider_slug):
        """Remove an API key for a provider"""
        if provider_slug in self.keys_data:
            del self.keys_data[provider_slug]
            return True
        return False
    
    def get_key(self, provider_slug):
        """Get API key for a provider"""
        return self.keys_data.get(provider_slug)
    
    def get_all_keys(self):
        """Get all stored keys"""
        return self.keys_data.copy() if self.keys_data else {}
    
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
    
    def get_keys_data(self):
        """Get the keys data dictionary"""
        return self.keys_data.copy() if self.keys_data else {}
