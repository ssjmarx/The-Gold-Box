#!/usr/bin/env python3
"""
CLI interface management
Handles terminal UI, menus, and user interactions
"""
import os
import getpass
import re

class CLIManager:
    """Manages CLI interface and user interactions"""
    
    @staticmethod
    def clear_terminal():
        """Clear terminal for clean UI"""
        os.system('cls' if os.name == 'nt' else 'clear')
    
    @staticmethod
    def display_header(title="The Gold Box"):
        """Display professional header"""
        CLIManager.clear_terminal()
        print("=" * 60)
        print(f"{title}")
        print("=" * 60)
    
    @staticmethod
    def get_password_input(prompt, allow_empty=False):
        """Get password input with validation"""
        while True:
            try:
                password = getpass.getpass(prompt)
                if not allow_empty and password == "":
                    print("Password cannot be empty")
                    continue
                return password
            except KeyboardInterrupt:
                print("\nOperation cancelled.")
                return None
    
    @staticmethod
    def get_confirm_password(prompt, original_password):
        """Get password confirmation"""
        confirm = getpass.getpass(prompt)
        return confirm == original_password
    
    @staticmethod
    def get_menu_choice(options, prompt="Enter your choice", allow_empty=False):
        """Get menu choice from user"""
        while True:
            try:
                choice = input(f"\n{prompt}: ").strip()
                if not allow_empty and not choice:
                    print("Choice required")
                    continue
                
                # Validate numeric choice if options are numbered
                if isinstance(options, list) and all(isinstance(x, int) for x in options):
                    try:
                        choice_num = int(choice)
                        if choice_num in options:
                            return choice_num
                        else:
                            print(f"Invalid choice. Please enter: {', '.join(map(str, options))}")
                    except ValueError:
                        print("Please enter a valid number.")
                else:
                    return choice
                    
            except KeyboardInterrupt:
                print("\nOperation cancelled.")
                return None
    
    @staticmethod
    def get_text_input(prompt, required=True, max_length=None, validation_pattern=None):
        """Get text input with validation"""
        while True:
            try:
                text = input(prompt).strip()
                
                if required and not text:
                    print("This field is required.")
                    continue
                
                if max_length and len(text) > max_length:
                    print(f"Input must be {max_length} characters or less.")
                    continue
                
                if validation_pattern and not re.match(validation_pattern, text):
                    print("Invalid format. Please check requirements.")
                    continue
                
                return text
                
            except KeyboardInterrupt:
                print("\nOperation cancelled.")
                return None
    
    @staticmethod
    def get_yes_no(prompt, default='N'):
        """Get yes/no response from user"""
        while True:
            try:
                response = input(f"{prompt} (y/N): ").strip().lower()
                if not response:
                    return default.upper() == 'Y'
                
                if response in ['y', 'yes']:
                    return True
                elif response in ['n', 'no']:
                    return False
                else:
                    print("Please enter 'y' or 'n'.")
                    
            except KeyboardInterrupt:
                print("\nOperation cancelled.")
                return None
    
    @staticmethod
    def display_list_with_numbers(items, title="Available Options"):
        """Display numbered list of items"""
        print(f"\n{title}:")
        print("=" * 50)
        for i, item in enumerate(items, 1):
            print(f"  {i}. {item}")
        print("=" * 50)
    
    @staticmethod
    def display_provider_list(providers, items_per_line=5):
        """Display provider list in compact format"""
        print("\nAvailable Providers:")
        print("=" * 50)
        
        for i in range(0, len(providers), items_per_line):
            # Get up to items_per_line providers for this line
            line_providers = providers[i:i+items_per_line]
            
            # Format each provider with proper spacing
            line_text = ""
            for j, provider in enumerate(line_providers):
                if j < items_per_line - 1:  # All but last item
                    line_text += f"{provider:<20}"
                else:  # Last item
                    line_text += f"{provider:<15}"
            
            print(line_text)
        
        print("=" * 50)
    
    @staticmethod
    def display_key_status(status_dict):
        """Display current API key status"""
        print("\nCurrent API Keys:")
        for i, (provider_id, info) in enumerate(status_dict.items(), 1):
            marker = "[CUSTOM]" if info.get('is_custom', False) else "[STANDARD]"
            print(f"  {i}. {marker} {info.get('name', provider_id)} ({provider_id})")
    
    @staticmethod
    def wait_for_enter(message="Press Enter to continue..."):
        """Wait for user to press Enter"""
        input(f"\n{message}")
    
    @staticmethod
    def display_error(message):
        """Display error message"""
        print(f"ERROR: {message}")
    
    @staticmethod
    def display_warning(message):
        """Display warning message"""
        print(f"WARNING: {message}")
    
    @staticmethod
    def display_success(message):
        """Display success message"""
        print(f"SUCCESS: {message}")
