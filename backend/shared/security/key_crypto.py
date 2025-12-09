#!/usr/bin/env python3
"""
Key encryption and security operations
Handles password derivation, encryption, and validation
"""
import hashlib
import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.backends import default_backend

class KeyCrypto:
    """Handles encryption and security operations for API keys"""
    
    @staticmethod
    def derive_key(password):
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
    
    @staticmethod
    def hash_password(password):
        """Hash password for verification storage"""
        if password is None:
            return None
        return hashlib.sha256(password.encode('utf-8')).hexdigest()
    
    @staticmethod
    def verify_password(provided_password, stored_hash):
        """Verify password against stored hash"""
        if provided_password is None:
            return stored_hash is None
        return KeyCrypto.hash_password(provided_password) == stored_hash
    
    @staticmethod
    def encrypt_data(data, password):
        """Encrypt data with password"""
        if password is None:
            return None
        
        key = KeyCrypto.derive_key(password)
        if key is None:
            return None
        
        fernet = Fernet(key)
        return fernet.encrypt(data.encode())
    
    @staticmethod
    def decrypt_data(encrypted_data, password):
        """Decrypt data with password"""
        if password is None:
            return None
        
        key = KeyCrypto.derive_key(password)
        if key is None:
            return None
        
        try:
            fernet = Fernet(key)
            return fernet.decrypt(encrypted_data).decode()
        except Exception:
            return None
    
    @staticmethod
    def validate_password_strength(password):
        """Validate password strength"""
        if password is None:
            return False, "Password cannot be None"
        
        if len(password) < 1:
            return False, "Password cannot be empty"
        
        # Could add more validation rules here
        return True, ""
