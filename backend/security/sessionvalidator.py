#!/usr/bin/env python3
"""
The Gold Box - Session Validator Module
Dedicated CSRF and session management functionality

Consolidates all session and CSRF protection logic from scattered locations
into a single, maintainable module.

License: CC-BY-NC-SA 4.0
"""

import secrets
import json
import time
import hashlib
import logging
from pathlib import Path
from typing import Dict, Optional, Any, Tuple
from datetime import datetime, UTC, timedelta
from fastapi import Request

# Get absolute path to backend directory (where server.py is located)
BACKEND_DIR = Path(__file__).parent.parent.absolute()

def get_absolute_path(relative_path: str) -> Path:
    """
    Convert a relative path to an absolute path based on backend directory.
    This ensures consistent file operations regardless of where script is called from.
    """
    return (BACKEND_DIR / relative_path).resolve()

logger = logging.getLogger(__name__)

class SessionValidator:
    """
    Centralized session and CSRF token management
    Provides cryptographically secure CSRF protection with persistent storage
    """
    
    def __init__(self, storage_file: str = None, timeout_minutes: int = 30, warning_minutes: int = 5):
        self.tokens = {}  # session_id -> token_data
        self.sessions = {}  # session_id -> session_data
        # Use absolute path for sessions file
        if storage_file is None:
            storage_file = "server_files/sessions.json"
        self.storage_file = get_absolute_path(storage_file)
        self.timeout_minutes = timeout_minutes
        self.warning_minutes = warning_minutes
        self.load_data()
        logger.info(f"SessionValidator initialized with storage: {self.storage_file}, timeout: {timeout_minutes}min, warning: {warning_minutes}min")
    
    def load_data(self):
        """Load existing sessions and tokens from file"""
        try:
            if self.storage_file.exists():
                with open(self.storage_file, 'r') as f:
                    data = json.load(f)
                    self.sessions = data.get('sessions', {})
                    self.tokens = data.get('tokens', {})
                    logger.info(f"Loaded {len(self.sessions)} sessions and {len(self.tokens)} CSRF tokens")
            else:
                self.sessions = {}
                self.tokens = {}
                logger.info("No existing session data found, starting fresh")
        except (json.JSONDecodeError, IOError) as e:
            logger.error(f"Error loading session data: {e}")
            self.sessions = {}
            self.tokens = {}
    
    def save_data(self):
        """Save sessions and tokens to file"""
        try:
            # Ensure directory exists
            self.storage_file.parent.mkdir(parents=True, exist_ok=True)
            
            data = {
                'sessions': self.sessions,
                'tokens': self.tokens,
                'last_saved': datetime.now(UTC).isoformat()
            }
            
            with open(self.storage_file, 'w') as f:
                json.dump(data, f, indent=2)
            
            logger.debug("Session data saved successfully")
        except IOError as e:
            logger.error(f"Error saving session data: {e}")
    
    def generate_session_id(self, request: Request) -> str:
        """
        Generate stable session ID from request characteristics
        Uses IP + User-Agent hash for consistency
        """
        # Extract client information
        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get('user-agent', '')[:50]  # Truncate for consistency
        
        # Create stable hash from IP + User-Agent
        identifier = f"{client_ip}:{user_agent}"
        session_id = hashlib.sha256(identifier.encode()).hexdigest()[:16]
        
        return f"session_{session_id}"
    
    def create_session(self, request: Request) -> str:
        """
        Create new session for client
        Returns session ID for the client to use
        """
        session_id = self.generate_session_id(request)
        now = time.time()
        
        # Create or update session data
        if session_id not in self.sessions:
            self.sessions[session_id] = {
                'created': now,
                'last_activity': now,
                'client_ip': request.client.host if request.client else "unknown",
                'user_agent': request.headers.get('user-agent', '')[:100]
            }
            logger.info(f"Created new session: {session_id}")
        else:
            # Update existing session activity
            self.sessions[session_id]['last_activity'] = now
            logger.debug(f"Updated existing session: {session_id}")
        
        # Save session data
        self.save_data()
        
        return session_id
    
    def generate_csrf_token(self, session_id: str) -> str:
        """
        Generate cryptographically secure CSRF token for session
        """
        if not self.is_session_valid(session_id):
            logger.warning(f"Attempted to generate CSRF token for invalid session: {session_id}")
            return None
        
        # Generate secure random token
        token = secrets.token_urlsafe(32)
        now = time.time()
        
        # Store token with expiration
        self.tokens[session_id] = {
            'token': token,
            'created': now,
            'expires': now + 3600,  # 1 hour expiration
            'last_used': now
        }
        
        # Save token data
        self.save_data()
        
        logger.debug(f"Generated CSRF token for session: {session_id}")
        return token
    
    def validate_csrf_token(self, session_id: str, provided_token: str) -> bool:
        """
        Validate CSRF token with timing attack protection
        Returns True if token is valid and not expired
        """
        if not provided_token:
            logger.debug("CSRF validation failed: no token provided")
            return False
        
        if session_id not in self.tokens:
            logger.debug(f"CSRF validation failed: no token for session {session_id}")
            return False
        
        token_data = self.tokens[session_id]
        now = time.time()
        
        # Check expiration
        if now > token_data['expires']:
            logger.debug(f"CSRF validation failed: token expired for session {session_id}")
            # Clean up expired token
            del self.tokens[session_id]
            self.save_data()
            return False
        
        # Constant-time comparison to prevent timing attacks
        stored_token = token_data['token']
        is_valid = secrets.compare_digest(stored_token, provided_token)
        
        if is_valid:
            # Update last used time
            token_data['last_used'] = now
            self.save_data()
            logger.debug(f"CSRF token validated successfully for session {session_id}")
        else:
            logger.warning(f"CSRF validation failed: invalid token for session {session_id}")
        
        return is_valid
    
    def is_session_valid(self, session_id: str) -> bool:
        """
        Check if session exists and is not expired
        """
        if session_id not in self.sessions:
            return False
        
        session_data = self.sessions[session_id]
        now = time.time()
        
        # Check if session has timed out (configurable timeout)
        last_activity = session_data['last_activity']
        timeout_seconds = self.timeout_minutes * 60  # Use configurable timeout
        
        if now - last_activity > timeout_seconds:
            logger.info(f"Session {session_id} expired due to inactivity")
            # Clean up expired session and its tokens
            if session_id in self.tokens:
                del self.tokens[session_id]
            del self.sessions[session_id]
            self.save_data()
            return False
        
        return True
    
    def update_session_activity(self, session_id: str) -> bool:
        """
        Update session's last activity timestamp
        Returns True if session is valid, False if expired
        """
        if not self.is_session_valid(session_id):
            return False
        
        self.sessions[session_id]['last_activity'] = time.time()
        self.save_data()
        return True
    
    def cleanup_expired_data(self) -> Tuple[int, int]:
        """
        Remove expired sessions and tokens
        Returns tuple of (sessions_cleaned, tokens_cleaned)
        """
        now = time.time()
        sessions_cleaned = 0
        tokens_cleaned = 0
        
        # Clean expired sessions (configurable timeout + grace period)
        expired_sessions = []
        for session_id, session_data in self.sessions.items():
            last_activity = session_data['last_activity']
            if now - last_activity > (self.timeout_minutes * 60 + 10 * 60):  # timeout + 10 min grace
                expired_sessions.append(session_id)
        
        for session_id in expired_sessions:
            del self.sessions[session_id]
            sessions_cleaned += 1
        
        # Clean expired tokens (1 hour)
        expired_tokens = []
        for session_id, token_data in self.tokens.items():
            if now > token_data['expires']:
                expired_tokens.append(session_id)
        
        for session_id in expired_tokens:
            del self.tokens[session_id]
            tokens_cleaned += 1
        
        # Save changes if any were made
        if sessions_cleaned > 0 or tokens_cleaned > 0:
            self.save_data()
            logger.info(f"Cleaned up {sessions_cleaned} expired sessions and {tokens_cleaned} expired tokens")
        
        return sessions_cleaned, tokens_cleaned
    
    def get_session_info(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Get session information for debugging/monitoring
        Returns None if session doesn't exist
        """
        if session_id not in self.sessions:
            return None
        
        session_data = self.sessions[session_id].copy()
        token_info = self.tokens.get(session_id)
        
        # Calculate session age and time to expiration
        now = time.time()
        session_age = now - session_data['created']
        last_activity = now - session_data['last_activity']
        
        info = {
            'session_id': session_id,
            'created': datetime.fromtimestamp(session_data['created'], UTC).isoformat(),
            'last_activity': datetime.fromtimestamp(session_data['last_activity'], UTC).isoformat(),
            'session_age_seconds': session_age,
            'last_activity_seconds': last_activity,
            'client_ip': session_data['client_ip'],
            'has_csrf_token': token_info is not None,
            'csrf_token_expires': None
        }
        
        if token_info:
            info['csrf_token_expires'] = datetime.fromtimestamp(token_info['expires'], UTC).isoformat()
        
        return info
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get statistics about current sessions and tokens
        """
        total_sessions = len(self.sessions)
        total_tokens = len(self.tokens)
        active_sessions = sum(1 for s in self.sessions.values() 
                           if time.time() - s['last_activity'] < 5 * 60)  # Active in last 5 minutes
        
        return {
            'total_sessions': total_sessions,
            'active_sessions': active_sessions,
            'total_csrf_tokens': total_tokens,
            'storage_file': str(self.storage_file)
        }

# Global session validator instance with environment-based configuration
import os
SESSION_TIMEOUT_MINUTES = int(os.environ.get('SESSION_TIMEOUT_MINUTES', 60))
SESSION_WARNING_MINUTES = int(os.environ.get('SESSION_WARNING_MINUTES', 10))
session_validator = SessionValidator(timeout_minutes=SESSION_TIMEOUT_MINUTES, warning_minutes=SESSION_WARNING_MINUTES)
