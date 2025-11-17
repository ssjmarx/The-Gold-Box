#!/usr/bin/env python3
"""
Simple multi-service API key storage with encryption
"""
import json
import os
import getpass
from pathlib import Path
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.backends import default_backend
import base64
from datetime import datetime

class MultiKeyManager:
    def __init__(self, key_file='keys.enc'):
        self.key_file = Path(key_file)
        self.supported_services = {
            '1': {'id': 'openai_compatible', 'name': 'OpenAI Compatible'},
            '2': {'id': 'novelai_api', 'name': 'NovelAI API'}
        }
        self.keys_data = {}
    
    def _get_encryption_password(self):
        """Get encryption password from user"""
        while True:
            try:
                password = getpass.getpass("Set encryption password for your keys: ")
                if password == "":
                    print("Blank password - keys will be stored unencrypted (NOT RECOMMENDED)")
                    confirm = getpass.getpass("Confirm blank password (press Enter): ")
                    if confirm != "":
                        print("Confirmation doesn't match")
                        continue
                    return None
                else:
                    confirm = getpass.getpass("Confirm encryption password: ")
                    if password != confirm:
                        print("Passwords don't match")
                        continue
                    return password
            except KeyboardInterrupt:
                print("\nSetup cancelled")
                return None
    
    def _derive_key(self, password):
        """Derive encryption key from password"""
        if password is None:
            return None
        
        salt = b'goldbox_salt_2025'
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
            backend=default_backend()
        )
        return base64.urlsafe_b64encode(kdf.derive(password.encode()))
    
    def load_keys(self):
        """Load and decrypt keys from file"""
        if not self.key_file.exists():
            return None
        
        try:
            with open(self.key_file, 'rb') as f:
                data = json.load(f)
            
            if data.get('encrypted', True):
                password = getpass.getpass("Enter encryption password to unlock keys: ")
                if password == "" and data.get('encrypted', True):
                    print("Keys are encrypted - password required")
                    return None
                
                key = self._derive_key(password)
                if key is None:
                    # Unencrypted keys
                    self.keys_data = data['keys']
                else:
                    # Decrypt keys
                    fernet = Fernet(key)
                    decrypted_data = fernet.decrypt(data['encrypted_keys'].encode()).decode()
                    self.keys_data = json.loads(decrypted_data)
            else:
                # Unencrypted keys
                self.keys_data = data['keys']
            
            return True
            
        except Exception as e:
            print(f"Failed to load keys: {e}")
            return False
    
    def save_keys(self, keys_data, password=None):
        """Encrypt and save keys to file"""
        self.keys_data = keys_data
        
        # Ensure directory exists
        self.key_file.parent.mkdir(parents=True, exist_ok=True)
        
        if password is None:
            data = {
                'encrypted': False,
                'keys': keys_data,
                'created_at': datetime.now().isoformat(),
                'version': '1.0'
            }
            with open(self.key_file, 'w') as f:
                json.dump(data, f, indent=2)
        else:
            key = self._derive_key(password)
            fernet = Fernet(key)
            encrypted_keys = fernet.encrypt(json.dumps(keys_data).encode())
            
            data = {
                'encrypted': True,
                'encrypted_keys': encrypted_keys.decode(),
                'created_at': datetime.now().isoformat(),
                'version': '1.0'
            }
            with open(self.key_file, 'w') as f:
                json.dump(data, f, indent=2)
        
        os.chmod(self.key_file, 0o600)
        print(f"Keys saved to {self.key_file}")
    
    def get_key_status(self):
        """Get current status of all keys"""
        if self.keys_data is None:
            self.keys_data = {}  # Initialize as empty dict if None
        
        status = {}
        for key_id, key_info in self.supported_services.items():
            service_id = key_info['id']
            status[key_id] = {
                'name': key_info['name'],
                'set': service_id in self.keys_data and self.keys_data[service_id] != '',
                'id': service_id
            }
        return status
    
    def add_key(self, service_choice):
        """Add or update a key for specific service"""
        if service_choice not in self.supported_services:
            print("Invalid service choice")
            return False
        
        service_info = self.supported_services[service_choice]
        print(f"\nEnter or paste (ctrl+shift+v) your {service_info['name']} key and press Enter:")
        
        try:
            api_key = getpass.getpass(f"{service_info['name']} API Key: ")
            if not api_key:
                print("No key provided")
                return False
            
            if len(api_key) < 10:
                print("Key too short - invalid format")
                return False
            
            if self.keys_data is None:
                self.keys_data = {}
            
            self.keys_data[service_info['id']] = api_key
            print(f"{service_info['name']} API key registered and ready for encryption")
            return True
            
        except KeyboardInterrupt:
            print("\nKey entry cancelled")
            return False
    
    def erase_all_keys(self):
        """Erase all stored keys"""
        try:
            if self.key_file.exists():
                os.remove(self.key_file)
            self.keys_data = {}
            print("All keys erased")
            return True
        except Exception as e:
            print(f"Failed to erase keys: {e}")
            return False
    
    def set_environment_variables(self):
        """Set API keys as environment variables"""
        if self.keys_data is None:
            print("No keys loaded")
            return False
        
        for service_id, api_key in self.keys_data.items():
            if api_key:
                os.environ[f'GOLD_BOX_{service_id.upper()}_API_KEY'] = api_key
                print(f"{service_id} API key loaded into environment")
        
        return True
    
    def interactive_setup(self):
        """Interactive key setup wizard"""
        while True:
            print("\n" + "=" * 50)
            print("Gold Box - API Key Management")
            print("=" * 50)
            print("Choose which API key to enter:")
            
            status = self.get_key_status()
            for key_id, info in status.items():
                set_status = "set!" if info['set'] else "not set."
                print(f"{key_id}. {info['name']} ({set_status})")
            
            print("3. Erase all keys.")
            print("4. Done! Start the server.")
            
            try:
                choice = input("\nEnter your choice (1-4): ").strip()
                
                if choice in ['1', '2']:
                    self.add_key(choice)
                elif choice == '3':
                    confirm = input("This will erase ALL stored keys. Type 'ERASE' to confirm: ")
                    if confirm == 'ERASE':
                        self.erase_all_keys()
                    else:
                        print("Erase cancelled")
                elif choice == '4':
                    if not self.keys_data or all(v == '' for v in self.keys_data.values()):
                        print("No keys configured - please set at least one API key")
                        continue
                    return True
                else:
                    print("Invalid choice")
                    
            except KeyboardInterrupt:
                print("\nSetup cancelled")
                return False
