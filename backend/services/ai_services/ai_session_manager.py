#!/usr/bin/env python3
"""
AI Session Manager for The Gold Box
Manages minimal session state for AI conversations with context delta support

Implements simplified session tracking that only stores:
- Session ID to client mapping
- Last message timestamp sent to AI
- Session activity tracking for cleanup

No full context storage - always gather fresh, just filter by timestamps
"""

import logging
import time
import secrets
from typing import Dict, Any, Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class AISessionManager:
    """
    Minimal AI session manager for context delta filtering
    
    Tracks only essential session information:
    - Session ID to client mapping
    - Last message timestamp sent to AI
    - Session activity for cleanup
    """
    
    def __init__(self, session_timeout_minutes: int = 20160, cleanup_interval_minutes: int = 10):  # 2 weeks = 20160 minutes
        self.sessions: Dict[str, Dict[str, Any]] = {}
        self.session_timeout_minutes = session_timeout_minutes
        self.cleanup_interval_minutes = cleanup_interval_minutes
        self._last_cleanup_time = time.time()
        
        logger.info(f"AISessionManager initialized - timeout: {session_timeout_minutes}min, cleanup: {cleanup_interval_minutes}min")
    
    def create_or_get_session(self, client_id: str, session_id: Optional[str] = None, provider: Optional[str] = None, model: Optional[str] = None) -> str:
        """
        Create new session or get existing session
        
        Args:
            client_id: Client identifier
            session_id: Optional existing session ID to continue
            provider: Optional AI provider name for session uniqueness
            model: Optional AI model name for session uniqueness
            
        Returns:
            Session ID for conversation
        """
        current_time = time.time()
        
        # Try to continue existing session if provided
        if session_id and session_id in self.sessions:
            session_data = self.sessions[session_id]
            
            # Verify session belongs to same client and is not expired
            if (session_data.get('client_id') == client_id and 
                current_time - session_data.get('last_activity', 0) < self.session_timeout_minutes * 60):
                
                # Update activity and return existing session
                session_data['last_activity'] = current_time
                logger.debug(f"Continued existing AI session {session_id} for client {client_id}")
                return session_id
            else:
                # Session expired or wrong client - remove it
                if session_id in self.sessions:
                    del self.sessions[session_id]
                logger.info(f"Removed invalid/expired session {session_id}")
        
        # Create session key that includes provider/model for uniqueness
        session_key = f"{client_id}_{provider}_{model}" if provider and model else client_id
        
        # Check if we have an existing session for this client+provider+model combo
        existing_session_id = None
        for sid, sdata in self.sessions.items():
            if (sdata.get('client_id') == client_id and 
                sdata.get('provider') == provider and 
                sdata.get('model') == model and
                current_time - sdata.get('last_activity', 0) < self.session_timeout_minutes * 60):
                existing_session_id = sid
                break
        
        if existing_session_id and not session_id:
            # Use existing session for this provider/model combo
            session_data = self.sessions[existing_session_id]
            session_data['last_activity'] = current_time
            logger.debug(f"Reusing existing AI session {existing_session_id} for client {client_id} with {provider}/{model}")
            return existing_session_id
        
        # Create new session
        new_session_id = session_id or self._generate_session_id()
        
        self.sessions[new_session_id] = {
            'client_id': client_id,
            'provider': provider,
            'model': model,
            'created_at': current_time,
            'last_activity': current_time,
            'last_message_timestamp': None,  # No messages sent to AI yet
        }
        
        logger.info(f"Created new AI session {new_session_id} for client {client_id} with {provider}/{model}")
        return new_session_id
    
    def update_session_timestamp(self, session_id: str, message_timestamp: int) -> bool:
        """
        Update the last message timestamp for a session
        
        Args:
            session_id: Session identifier
            message_timestamp: Timestamp of most recent message sent to AI
            
        Returns:
            True if successful, False if session not found
        """
        if session_id not in self.sessions:
            logger.warning(f"Attempted to update timestamp for non-existent session {session_id}")
            return False
        
        current_time = time.time()
        session_data = self.sessions[session_id]
        
        # Validate session is not expired
        if current_time - session_data.get('last_activity', 0) >= self.session_timeout_minutes * 60:
            logger.warning(f"Attempted to update expired session {session_id}")
            return False
        
        # Update timestamp and activity
        session_data['last_message_timestamp'] = message_timestamp
        session_data['last_activity'] = current_time
        
        logger.debug(f"Updated session {session_id} timestamp to {message_timestamp}")
        return True
    
    def get_session_timestamp(self, session_id: str) -> Optional[int]:
        """
        Get the last message timestamp for a session
        
        Args:
            session_id: Session identifier
            
        Returns:
            Last message timestamp or None if not found/expired
        """
        if session_id not in self.sessions:
            return None
        
        current_time = time.time()
        session_data = self.sessions[session_id]
        
        # Check if session is expired
        if current_time - session_data.get('last_activity', 0) >= self.session_timeout_minutes * 60:
            logger.info(f"Session {session_id} expired during timestamp retrieval")
            del self.sessions[session_id]
            return None
        
        return session_data.get('last_message_timestamp')
    
    def clear_session_timestamp(self, session_id: str) -> bool:
        """
        Clear the timestamp for a session (forces full context on next call)
        
        Args:
            session_id: Session identifier
            
        Returns:
            True if successful, False if session not found
        """
        if session_id not in self.sessions:
            return False
        
        current_time = time.time()
        session_data = self.sessions[session_id]
        
        # Validate session is not expired
        if current_time - session_data.get('last_activity', 0) >= self.session_timeout_minutes * 60:
            logger.warning(f"Attempted to clear expired session {session_id}")
            return False
        
        # Clear timestamp and update activity
        session_data['last_message_timestamp'] = None
        session_data['last_activity'] = current_time
        
        logger.info(f"Cleared timestamp for session {session_id} - will send full context next call")
        return True
    
    def get_session_info(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Get session information for debugging/monitoring
        
        Args:
            session_id: Session identifier
            
        Returns:
            Session information or None if not found
        """
        if session_id not in self.sessions:
            return None
        
        current_time = time.time()
        session_data = self.sessions[session_id].copy()
        
        # Check if session is expired
        is_expired = current_time - session_data.get('last_activity', 0) >= self.session_timeout_minutes * 60
        
        info = {
            'session_id': session_id,
            'client_id': session_data.get('client_id'),
            'created_at': datetime.fromtimestamp(session_data.get('created_at', 0)).isoformat(),
            'last_activity': datetime.fromtimestamp(session_data.get('last_activity', 0)).isoformat(),
            'last_message_timestamp': session_data.get('last_message_timestamp'),
            'is_expired': is_expired,
            'session_age_seconds': current_time - session_data.get('created_at', 0),
            'last_activity_seconds': current_time - session_data.get('last_activity', 0)
        }
        
        return info
    
    def cleanup_expired_sessions(self) -> int:
        """
        Remove expired sessions from memory
        
        Returns:
            Number of sessions cleaned up
        """
        current_time = time.time()
        cutoff_time = current_time - (self.session_timeout_minutes * 60)
        
        expired_sessions = [
            session_id for session_id, session_data in self.sessions.items()
            if session_data.get('last_activity', 0) < cutoff_time
        ]
        
        for session_id in expired_sessions:
            del self.sessions[session_id]
        
        if expired_sessions:
            logger.info(f"Cleaned up {len(expired_sessions)} expired AI sessions: {expired_sessions[:3]}...")
        
        return len(expired_sessions)
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get statistics about current sessions
        
        Returns:
            Session statistics dictionary
        """
        current_time = time.time()
        active_sessions = 0
        sessions_with_timestamps = 0
        
        for session_data in self.sessions.values():
            if current_time - session_data.get('last_activity', 0) < 5 * 60:  # Active in last 5 minutes
                active_sessions += 1
            
            if session_data.get('last_message_timestamp') is not None:
                sessions_with_timestamps += 1
        
        return {
            'total_sessions': len(self.sessions),
            'active_sessions': active_sessions,
            'sessions_with_timestamps': sessions_with_timestamps,
            'session_timeout_minutes': self.session_timeout_minutes,
            'cleanup_interval_minutes': self.cleanup_interval_minutes
        }
    
    def _generate_session_id(self) -> str:
        """
        Generate a secure session ID
        
        Returns:
            New session ID
        """
        return f"ai_session_{secrets.token_urlsafe(16)}"
    
    def auto_cleanup(self) -> None:
        """
        Automatically cleanup expired sessions if cleanup interval has passed
        Called periodically during session operations
        """
        current_time = time.time()
        
        if current_time - self._last_cleanup_time >= self.cleanup_interval_minutes * 60:
            self._last_cleanup_time = current_time
            self.cleanup_expired_sessions()


# Global instance for application-wide use
_ai_session_manager = None

def get_ai_session_manager() -> AISessionManager:
    """
    Get the global AI session manager instance
    
    Returns:
        AISessionManager instance
    """
    global _ai_session_manager
    if _ai_session_manager is None:
        _ai_session_manager = AISessionManager()
    return _ai_session_manager

def reset_ai_session_manager() -> AISessionManager:
    """
    Reset the global AI session manager (for testing)
    
    Returns:
        New AISessionManager instance
    """
    global _ai_session_manager
    _ai_session_manager = AISessionManager()
    return _ai_session_manager
