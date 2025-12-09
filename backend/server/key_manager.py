#!/usr/bin/env python3
"""
Enhanced multi-service API key storage with encryption and dynamic provider support
Refactored to use separated modules for better maintainability
"""
import os
import re
from pathlib import Path
from .provider_manager import ProviderManager
from security.key_crypto import KeyCrypto
from ui.cli_manager import CLIManager
from core.key_storage import KeyStorage
from providers.custom_provider_wizard import CustomProviderWizard

# Get absolute path to backend directory (where server.py is located)
BACKEND_DIR = Path(__file__).parent.parent.absolute()

def get_absolute_path(relative_path: str) -> Path:
    """
    Convert a relative path to an absolute path based on backend directory.
    This ensures consistent file operations regardless of where script is called from.
    """
    return (BACKEND_DIR / relative_path).resolve()

class MultiKeyManager:
    def __init__(self, key_file='server_files/keys.enc'):
        # Initialize separated modules
        self.key_storage = KeyStorage(key_file)
        self.provider_manager = ProviderManager()
        self.custom_wizard = CustomProviderWizard(self.provider_manager)
        
        # For backward compatibility
        self.key_file = self.key_storage.key_file
        self.master_password = self.key_storage.master_password
        self.keys_data = self.key_storage.keys_data
    
    def clear_terminal(self):
        """Clear terminal for clean UI"""
        CLIManager.clear_terminal()
    
    def display_header(self):
        """Display professional header"""
        CLIManager.display_header("The Gold Box API Key Manager")
    
    def _derive_key(self, password):
        """Derive encryption key from password (backward compatibility)"""
        return KeyCrypto.derive_key(password)
    
    def _hash_password(self, password):
        """Hash password for verification storage (backward compatibility)"""
        return KeyCrypto.hash_password(password)
    
    def _verify_password(self, provided_password, stored_hash):
        """Verify password against stored hash (backward compatibility)"""
        return KeyCrypto.verify_password(provided_password, stored_hash)
    
    def load_keys(self):
        """Load and decrypt keys from file"""
        result = self.key_storage.load_keys()
        if result is not None:
            # Update compatibility properties
            self.master_password = self.key_storage.master_password
            self.keys_data = self.key_storage.keys_data
        return result
    
    def load_keys_with_password(self, password):
        """Load and decrypt keys from file with provided password"""
        result = self.key_storage.load_keys_with_password(password)
        if result:
            # Update compatibility properties
            self.master_password = self.key_storage.master_password
            self.keys_data = self.key_storage.keys_data
        return result
    
    def get_password_status(self):
        """Get password status"""
        return self.key_storage.get_password_status()
    
    def set_password(self, password=None):
        """Set master password"""
        result = self.key_storage.set_password(password)
        if result:
            # Update compatibility property
            self.master_password = self.key_storage.master_password
        return result
    
    def verify_password(self, provided_password):
        """Verify master password"""
        return self.key_storage.verify_password(provided_password)
    
    def save_keys(self, keys_data=None, password=None):
        """Encrypt and save keys to file"""
        if password is not None:
            self.master_password = password
        
        result = self.key_storage.save_keys(keys_data)
        if result:
            # Update compatibility properties
            self.keys_data = self.key_storage.keys_data
        return result
    
    def get_key_status(self):
        """Get current status of all keys"""
        return self.key_storage.get_key_status(self.provider_manager)
    
    def add_key_flow(self):
        """Enhanced key addition with validation"""
        self.display_header()
        print("Add an API Key")
        print("-" * 60)
        
        # Display all available providers in compact format (5 per line)
        provider_list = self.provider_manager.get_provider_list()
        provider_names = [p['name'] for p in provider_list]
        CLIManager.display_provider_list(provider_names)
        
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
                current_status = self.get_key_status()
                if provider_slug in current_status and current_status[provider_slug]['set']:
                    overwrite = input(f"Key for {provider_name} already exists. Overwrite? (y/N): ").strip().lower()
                    if overwrite not in ['y', 'yes']:
                        print("Operation cancelled.")
                        return False
                
                # Get API key
                print(f"\nEnter or paste (ctrl+shift+v) your {provider_name} API key:")
                api_key = CLIManager.get_password_input(f"{provider_name} API Key: ")
                
                if not api_key:
                    print("ERROR: No key provided - operation cancelled.")
                    print("Please enter a valid API key to continue.")
                    continue
                
                if len(api_key) < 8:
                    print("ERROR: Key too short - API keys must be at least 8 characters long")
                    print("Please enter a valid API key or try again.")
                    continue
                
                # Save key using storage module
                self.key_storage.add_key(provider_slug, api_key)
                self.keys_data = self.key_storage.keys_data  # Update compatibility
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
            CLIManager.wait_for_enter()
            return True
        
        CLIManager.display_key_status(existing_keys)
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
                            if self.key_storage.remove_key(provider_to_delete):
                                self.keys_data = self.key_storage.keys_data  # Update compatibility
                                print(f"\nKey for {provider_info['name']} deleted successfully")
                                break
                            else:
                                print("Failed to delete key")
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
            change = CLIManager.get_yes_no("Change password?")
            if not change:
                print("Operation cancelled.")
                return True
        else:
            print("No password currently set.")
        
        # Set new password
        return self.set_password()
    
    def interactive_setup(self):
        """Enhanced interactive setup with professional menu"""
        try:
            while True:
                self.display_header()
                print("\n1. Add a Key")
                print("2. Delete a Key")
                print("3. Create a Custom Provider")
                print("4. Change Password")
                print("5. Finish and Start Server")
                
                choice = CLIManager.get_menu_choice([1, 2, 3, 4, 5])
                if choice is None:
                    return False
                    
                if choice == 1:
                    self.add_key_flow()
                elif choice == 2:
                    self.delete_key_flow()
                elif choice == 3:
                    self.create_custom_provider_flow()
                elif choice == 4:
                    self.change_password_flow()
                elif choice == 5:
                    # Check for password before starting server
                    if not self.get_password_status():
                        print("WARNING: No password set!")
                        print("It's highly recommended to set a password for security.")
                        confirm = CLIManager.get_yes_no("Continue without password?")
                        if not confirm:
                            continue
                    
                    # Save keys and exit
                    print("\nSaving configuration...")
                    if self.save_keys():
                        CLIManager.display_success("Configuration saved successfully")
                        print("\nStarting server...")
                        return True
                    else:
                        CLIManager.display_error("Failed to save configuration")
                        CLIManager.wait_for_enter()
                else:
                    print("Invalid choice. Please try again.")
        except KeyboardInterrupt:
            print("\n\nExiting setup...")
            # Clear terminal when key manager closes
            self.clear_terminal()
            return False
    
    def create_custom_provider_flow(self):
        """Create custom provider using wizard"""
        return self.custom_wizard.create_custom_provider_flow()
    
    def set_environment_variables(self):
        """Set API keys as environment variables for all providers"""
        return self.key_storage.set_environment_variables()
    
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
    
    def save_and_exit(self):
        """Save keys and start server"""
        print("\nSaving configuration...")
        if self.save_keys():
            CLIManager.display_success("Configuration saved successfully")
            print("\nStarting server...")
            # Clear terminal when key manager closes
            self.clear_terminal()
            return True
        else:
            CLIManager.display_error("Failed to save configuration")
            CLIManager.wait_for_enter()
            return False
