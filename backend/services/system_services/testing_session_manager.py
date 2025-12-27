#!/usr/bin/env python3
"""
Testing Session Manager for The Gold Box
Manages testing sessions for AI function testing without calling real AI services
"""

import logging
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)

class TestingSessionManager:
    """
    Manages testing sessions for AI function testing
    
    Responsibilities:
    - Create and manage active test sessions
    - Map client_id to test_session_state
    - Track session metadata (start time, current prompt, conversation history)
    - Manage test session lifecycle (start, continue, end)
    - Store pending responses waiting for user input
    - Clean up expired sessions
    """
    
    def __init__(self):
        """Initialize testing session manager"""
        self._sessions: Dict[str, Dict[str, Any]] = {}
        self._client_to_session: Dict[str, str] = {}  # client_id -> test_session_id
        self._session_timeout_minutes = 60  # Sessions expire after 1 hour
        logger.info("TestingSessionManager initialized")
    
    def create_session(self, client_id: str, universal_settings: Optional[Dict[str, Any]] = None) -> str:
        """
        Create a new test session for a client
        
        Args:
            client_id: The Foundry client ID
            universal_settings: Optional settings from frontend
            
        Returns:
            test_session_id: Unique ID for the test session
        """
        # Check if client already has an active test session
        if client_id in self._client_to_session:
            old_session_id = self._client_to_session[client_id]
            logger.warning(f"Client {client_id} already has active test session {old_session_id}, ending it")
            self.end_session(old_session_id)
        
        # Generate unique session ID
        test_session_id = str(uuid.uuid4())
        
        # Create session state
        session_state = {
            'test_session_id': test_session_id,
            'client_id': client_id,
            'start_time': datetime.now(),
            'last_activity': datetime.now(),
            'state': 'awaiting_input',  # awaiting_input, processing, completed, ended
            'conversation_history': [],
            'commands_executed': 0,
            'tools_used': [],
            'universal_settings': universal_settings or {},
            'initial_prompt': None,
            'session_summary': {}
        }
        
        # Store session
        self._sessions[test_session_id] = session_state
        self._client_to_session[client_id] = test_session_id
        
        logger.info(f"Created test session {test_session_id} for client {client_id}")
        return test_session_id
    
    def get_session(self, test_session_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve session state
        
        Args:
            test_session_id: The test session ID
            
        Returns:
            Session state dictionary or None if not found
        """
        # Check if session exists
        if test_session_id not in self._sessions:
            logger.warning(f"Test session {test_session_id} not found")
            return None
        
        # Check if session has expired
        session = self._sessions[test_session_id]
        if self._is_session_expired(session):
            logger.info(f"Test session {test_session_id} has expired, cleaning up")
            self._cleanup_session(test_session_id)
            return None
        
        return session
    
    def update_session(self, test_session_id: str, updates: Dict[str, Any]) -> bool:
        """
        Update session state
        
        Args:
            test_session_id: The test session ID
            updates: Dictionary of fields to update
            
        Returns:
            True if successful, False if session not found
        """
        session = self.get_session(test_session_id)
        if not session:
            return False
        
        # Update session fields
        for key, value in updates.items():
            session[key] = value
        
        # Update last activity timestamp
        session['last_activity'] = datetime.now()
        
        logger.debug(f"Updated test session {test_session_id}: {list(updates.keys())}")
        return True
    
    def end_session(self, test_session_id: str) -> Optional[Dict[str, Any]]:
        """
        End a test session and return summary
        
        Args:
            test_session_id: The test session ID
            
        Returns:
            Session summary dictionary or None if session not found
        """
        session = self.get_session(test_session_id)
        if not session:
            return None
        
        # Generate session summary
        end_time = datetime.now()
        duration_seconds = (end_time - session['start_time']).total_seconds()
        
        session_summary = {
            'test_session_id': test_session_id,
            'client_id': session['client_id'],
            'duration_seconds': duration_seconds,
            'commands_executed': session['commands_executed'],
            'tools_used': session['tools_used'],
            'conversation_length': len(session['conversation_history']),
            'state': 'ended'
        }
        
        # Update session state
        session['state'] = 'ended'
        session['session_summary'] = session_summary
        
        logger.info(f"Ended test session {test_session_id}: {duration_seconds:.1f}s, {session['commands_executed']} commands")
        
        # Clean up session (remove from active sessions but keep summary temporarily)
        return session_summary
    
    def cleanup_session(self, test_session_id: str) -> bool:
        """
        Completely remove a test session (after ending)
        
        Args:
            test_session_id: The test session ID
            
        Returns:
            True if successful, False if session not found
        """
        session = self._sessions.get(test_session_id)
        if not session:
            return False
        
        client_id = session['client_id']
        
        # Remove from mappings
        if test_session_id in self._sessions:
            del self._sessions[test_session_id]
        
        if client_id in self._client_to_session:
            del self._client_to_session[client_id]
        
        logger.info(f"Cleaned up test session {test_session_id}")
        return True
    
    def list_sessions(self) -> List[Dict[str, Any]]:
        """
        List all active test sessions
        
        Returns:
            List of session information dictionaries
        """
        # Clean up expired sessions first
        self._cleanup_expired_sessions()
        
        sessions_list = []
        for test_session_id, session in self._sessions.items():
            if session['state'] not in ['ended']:
                duration_seconds = (datetime.now() - session['start_time']).total_seconds()
                session_info = {
                    'test_session_id': test_session_id,
                    'client_id': session['client_id'],
                    'start_time': session['start_time'].isoformat(),
                    'duration_seconds': int(duration_seconds),
                    'commands_executed': session['commands_executed'],
                    'state': session['state']
                }
                sessions_list.append(session_info)
        
        return sessions_list
    
    def is_test_active(self, client_id: str) -> bool:
        """
        Check if client has an active test session
        
        Args:
            client_id: The Foundry client ID
            
        Returns:
            True if active test session exists, False otherwise
        """
        if client_id not in self._client_to_session:
            return False
        
        test_session_id = self._client_to_session[client_id]
        session = self.get_session(test_session_id)
        
        if not session or session['state'] in ['ended']:
            return False
        
        return True
    
    def get_session_by_client(self, client_id: str) -> Optional[Dict[str, Any]]:
        """
        Get test session by client ID
        
        Args:
            client_id: The Foundry client ID
            
        Returns:
            Session state dictionary or None if not found
        """
        if client_id not in self._client_to_session:
            return None
        
        test_session_id = self._client_to_session[client_id]
        return self.get_session(test_session_id)
    
    def add_conversation_message(self, test_session_id: str, message: Dict[str, Any]) -> bool:
        """
        Add a message to the conversation history
        
        Args:
            test_session_id: The test session ID
            message: Message dictionary to add
            
        Returns:
            True if successful, False if session not found
        """
        session = self.get_session(test_session_id)
        if not session:
            return False
        
        session['conversation_history'].append(message)
        return True
    
    def increment_commands_executed(self, test_session_id: str) -> bool:
        """
        Increment the command counter for a session
        
        Args:
            test_session_id: The test session ID
            
        Returns:
            True if successful, False if session not found
        """
        session = self.get_session(test_session_id)
        if not session:
            return False
        
        session['commands_executed'] += 1
        return True
    
    def record_tool_used(self, test_session_id: str, tool_name: str) -> bool:
        """
        Record that a tool was used during testing
        
        Args:
            test_session_id: The test session ID
            tool_name: Name of the tool used
            
        Returns:
            True if successful, False if session not found
        """
        session = self.get_session(test_session_id)
        if not session:
            return False
        
        if tool_name not in session['tools_used']:
            session['tools_used'].append(tool_name)
        
        return True
    
    def set_initial_prompt(self, test_session_id: str, initial_prompt: str) -> bool:
        """
        Set the initial prompt for a test session
        
        Args:
            test_session_id: The test session ID
            initial_prompt: The initial prompt text
            
        Returns:
            True if successful, False if session not found
        """
        return self.update_session(test_session_id, {'initial_prompt': initial_prompt})
    
    def _is_session_expired(self, session: Dict[str, Any]) -> bool:
        """
        Check if a session has expired based on inactivity
        
        Args:
            session: Session state dictionary
            
        Returns:
            True if expired, False otherwise
        """
        if session['state'] == 'ended':
            return True
        
        last_activity = session['last_activity']
        timeout = timedelta(minutes=self._session_timeout_minutes)
        
        return (datetime.now() - last_activity) > timeout
    
    def _cleanup_session(self, test_session_id: str) -> None:
        """
        Remove a session without ending it (for expired sessions)
        
        Args:
            test_session_id: The test session ID
        """
        session = self._sessions.get(test_session_id)
        if not session:
            return
        
        client_id = session['client_id']
        
        if test_session_id in self._sessions:
            del self._sessions[test_session_id]
        
        if client_id in self._client_to_session:
            del self._client_to_session[client_id]
    
    def _cleanup_expired_sessions(self) -> None:
        """Clean up all expired sessions"""
        expired_sessions = []
        
        for test_session_id, session in self._sessions.items():
            if self._is_session_expired(session):
                expired_sessions.append(test_session_id)
        
        for test_session_id in expired_sessions:
            logger.info(f"Cleaning up expired test session {test_session_id}")
            self._cleanup_session(test_session_id)
        
        if expired_sessions:
            logger.info(f"Cleaned up {len(expired_sessions)} expired test sessions")

def get_testing_session_manager() -> TestingSessionManager:
    """
    Get or create the testing session manager instance
    
    Returns:
        TestingSessionManager instance
    """
    # This will be integrated with ServiceFactory later
    return TestingSessionManager()
