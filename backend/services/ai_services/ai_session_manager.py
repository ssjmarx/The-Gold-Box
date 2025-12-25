#!/usr/bin/env python3
"""
AI Session Manager for The Gold Box
Manages AI session state for conversations with full context history

Enhanced session tracking that stores:
- Session ID to client mapping  
- Last message timestamp sent to AI (for delta filtering)
- Session activity tracking for cleanup
- Full conversation history (OpenAI format for AI compatibility)
"""

import logging
import time
import secrets
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# Simple token estimation (approximate, can be refined later)
def estimate_tokens(text: str) -> int:
    """Rough token estimation - ~4 characters per token"""
    return len(text) // 4 if text else 0

class AISessionManager:
    """
    Enhanced AI session manager with conversation history support
    
    Tracks comprehensive session information:
    - Session ID to client mapping
    - Last message timestamp for delta filtering
    - Session activity for cleanup
    - Full conversation history in OpenAI format
    """
    
    def __init__(self, session_timeout_minutes: int = 20160, cleanup_interval_minutes: int = 10):  # 2 weeks = 20160 minutes
        self.sessions: Dict[str, Dict[str, Any]] = {}
        self.session_timeout_minutes = session_timeout_minutes
        self.cleanup_interval_minutes = cleanup_interval_minutes
        self._last_cleanup_time = time.time()
        
        # Default memory limits (configurable via settings)
        self.default_max_history_messages = 50
        self.default_max_history_hours = 24  # 1 day
        self.default_cleanup_hours = 168  # 1 week
        
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
            'conversation_history': []  # Store full conversation history
        }
        
        # logger.info(f"Created new AI session {new_session_id} for client {client_id} with {provider}/{model}")
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
    
    def add_conversation_message(self, session_id: str, message: Dict[str, Any]) -> bool:
        """
        Add a message to conversation history
        
        Args:
            session_id: Session identifier
            message: Message dictionary with role, content, etc.
            
        Returns:
            True if successful, False if session not found
        """
        if session_id not in self.sessions:
            logger.warning(f"Attempted to add message to non-existent session {session_id}")
            return False
        
        current_time = time.time()
        session_data = self.sessions[session_id]
        
        # Validate session is not expired
        if current_time - session_data.get('last_activity', 0) >= self.session_timeout_minutes * 60:
            logger.warning(f"Attempted to add message to expired session {session_id}")
            return False
        
        # Add message to conversation history
        if 'conversation_history' not in session_data:
            session_data['conversation_history'] = []
        
        session_data['conversation_history'].append(message)
        session_data['last_activity'] = current_time
        
        # Print debug output for this message (once when added)
        role = message.get('role', 'unknown')
        content = message.get('content', '')
        tool_calls = message.get('tool_calls', [])
        tool_call_id = message.get('tool_call_id', '')
        
        logger.info(f"===== ADDING MESSAGE TO CONVERSATION =====")
        logger.info(f"Session: {session_id}")
        logger.info(f"Role: {role}")
        
        if tool_calls:
            # Log tool calls summary
            tool_names = [tc.get('function', {}).get('name', 'unknown') for tc in tool_calls]
            logger.info(f"Tool calls: {len(tool_calls)} - {tool_names}")
            for tc in tool_calls:
                # Format tool call details with decoded arguments
                func = tc.get('function', {})
                tool_id = tc.get('id', 'unknown')
                func_name = func.get('name', 'unknown')
                func_args = func.get('arguments', '{}')
                
                # Parse and decode arguments JSON with recursive decoding
                try:
                    import json
                    decoded_args = self._decode_content_for_display(func_args)
                    args_dict = json.loads(decoded_args)
                    # Recursively decode all nested strings
                    decoded_dict = self._decode_json_recursively(args_dict)
                    formatted_args = json.dumps(decoded_dict, indent=4, ensure_ascii=False)
                except:
                    formatted_args = self._decode_content_for_display(func_args)
                
                logger.info(f"  Tool call details:")
                logger.info(f"    id: {tool_id}")
                logger.info(f"    type: function")
                logger.info(f"    function:")
                logger.info(f"      name: {func_name}")
                logger.info(f"      arguments: {formatted_args}")
        elif role == 'tool':
            # Log tool results (full content with newlines rendered)
            logger.info(f"Tool call ID: {tool_call_id}")
            logger.info(f"Content length: {len(content)}")
            # Parse and format JSON content for better readability
            try:
                import json
                # Parse to JSON to get proper structure
                parsed = json.loads(content)
                # Recursively decode all nested strings
                decoded_obj = self._decode_json_recursively(parsed)
                # Re-dump with proper formatting
                formatted_json = json.dumps(decoded_obj, indent=6, ensure_ascii=False)
                logger.info(f"Tool result content:\n{formatted_json}")
            except:
                # If JSON parsing fails, use decode method
                decoded_content = self._decode_content_for_display(content)
                logger.info(f"Tool result content:\n{decoded_content}")
        else:
            # Log full content for system/user/assistant messages with newlines rendered
            # Decode escape sequences and render newlines properly in log
            decoded_content = self._decode_content_for_display(content)
            logger.info(f"  {decoded_content}")
        
        logger.info(f"===== END ADDING MESSAGE =====")
        
        return True
    
    def get_conversation_history(self, session_id: str, max_messages: Optional[int] = None, max_hours: Optional[int] = None, max_tokens: Optional[int] = None) -> list:
        """
        Get conversation history for a session with configurable limits
        Returns OpenAI format messages for AI processing (no conversion to compact JSON)
        
        Args:
            session_id: Session identifier
            max_messages: Maximum number of messages to return (None for default)
            max_hours: Maximum age in hours for messages to return (None for default)
            max_tokens: Maximum tokens allowed (prunes oldest if exceeded)
            
        Returns:
            List of conversation messages in OpenAI format
        """
        if session_id not in self.sessions:
            return []
        
        session_data = self.sessions[session_id]
        current_time = time.time()
        
        # Check if session is expired
        if current_time - session_data.get('last_activity', 0) >= self.session_timeout_minutes * 60:
            logger.info(f"Session {session_id} expired during history retrieval")
            del self.sessions[session_id]
            return []
        
        conversation_history = session_data.get('conversation_history', [])
        
        # Apply token-based pruning if specified
        if max_tokens is not None:
            conversation_history = self.prune_by_tokens(conversation_history, max_tokens)
        
        # Apply message count limit if provided
        if max_messages is not None:
            conversation_history = conversation_history[-max_messages:]
        
        # Apply time limit if provided
        if max_hours is not None:
            cutoff_time = current_time - (max_hours * 3600)
            conversation_history = [
                msg for msg in conversation_history
                if msg.get('timestamp', current_time) >= cutoff_time
            ]
        
        return conversation_history
    
    def prune_by_tokens(self, conversation_history: List[Dict[str, Any]], max_tokens: int) -> List[Dict[str, Any]]:
        """
        Prune conversation history to stay within token limit
        Removes oldest messages first, keeping system message if present
        
        Args:
            conversation_history: List of conversation messages in OpenAI format
            max_tokens: Maximum tokens allowed
            
        Returns:
            Pruned conversation history
        """
        if not conversation_history or max_tokens <= 0:
            return conversation_history
        
        # Calculate total tokens
        total_tokens = sum(
            estimate_tokens(msg.get('content', '')) for msg in conversation_history
        )
        
        if total_tokens <= max_tokens:
            logger.debug(f"Conversation history within token limit: {total_tokens}/{max_tokens}")
            return conversation_history
        
        logger.info(f"Pruning conversation history: {total_tokens} tokens > {max_tokens} limit")
        
        # Find system message (keep if present)
        system_message = None
        filtered_history = []
        for msg in conversation_history:
            if msg.get('role') == 'system':
                system_message = msg
            else:
                filtered_history.append(msg)
        
        # Remove oldest messages until under token limit
        while filtered_history:
            total_tokens = sum(
                estimate_tokens(msg.get('content', '')) for msg in filtered_history
            )
            
            if total_tokens <= max_tokens:
                break
            
            # Remove oldest non-system message
            removed = filtered_history.pop(0)
            removed_tokens = estimate_tokens(removed.get('content', ''))
            total_tokens -= removed_tokens
            
            logger.debug(f"Removed oldest message ({removed_tokens} tokens) to stay under limit")
        
        # Add back system message if it existed
        if system_message:
            filtered_history.insert(0, system_message)
            logger.debug(f"Preserved system message in pruned conversation history")
        
        final_tokens = sum(
            estimate_tokens(msg.get('content', '')) for msg in filtered_history
        )
        logger.info(f"Pruned conversation history to {final_tokens}/{max_tokens} tokens ({len(filtered_history)} messages)")
        
        return filtered_history
    
    def clear_conversation_history(self, session_id: str) -> bool:
        """
        Clear conversation history for a session
        
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
            logger.warning(f"Attempted to clear conversation history for expired session {session_id}")
            return False
        
        # Clear conversation history and update activity
        session_data['conversation_history'] = []
        session_data['last_activity'] = current_time
        
        logger.info(f"Cleared conversation history for session {session_id}")
        return True
    
    def auto_cleanup(self) -> None:
        """
        Automatically cleanup expired sessions if cleanup interval has passed
        Called periodically during session operations
        """
        current_time = time.time()
        
        if current_time - self._last_cleanup_time >= self.cleanup_interval_minutes * 60:
            self._last_cleanup_time = current_time
            self._cleanup_conversation_history()
            self.cleanup_expired_sessions()
    
    def _cleanup_conversation_history(self) -> None:
        """
        Clean up conversation history based on age and size limits
        
        Called automatically during cleanup operations
        """
        current_time = time.time()
        
        for session_id, session_data in list(self.sessions.items()):
            if 'conversation_history' not in session_data:
                continue
            
            # Apply default limits
            max_messages = session_data.get('max_history_messages', self.default_max_history_messages)
            max_hours = session_data.get('max_history_hours', self.default_max_history_hours)
            cleanup_hours = session_data.get('cleanup_hours', self.default_cleanup_hours)
            
            conversation_history = session_data['conversation_history']
            
            # Remove messages older than max_hours
            if max_hours is not None:
                cutoff_time = current_time - (max_hours * 3600)
                original_count = len(conversation_history)
                conversation_history = [
                    msg for msg in conversation_history
                    if msg.get('timestamp', current_time) >= cutoff_time
                ]
                removed_count = original_count - len(conversation_history)
                if removed_count > 0:
                    logger.debug(f"Cleaned up {removed_count} old messages from session {session_id}")
            
            # Limit history size to max_messages
            if max_messages is not None and len(conversation_history) > max_messages:
                original_count = len(conversation_history)
                session_data['conversation_history'] = conversation_history[-max_messages:]
                removed_count = original_count - len(session_data['conversation_history'])
                if removed_count > 0:
                    logger.debug(f"Limited conversation history for session {session_id}: removed {removed_count} old messages")
            
            # Update session data
            session_data['conversation_history'] = conversation_history
    
    def _decode_json_recursively(self, obj):
        """
        Recursively decode JSON strings within a JSON structure
        
        Args:
            obj: JSON object (dict, list, or primitive type)
            
        Returns:
            Decoded JSON object with all string values properly formatted
        """
        import json
        
        if isinstance(obj, dict):
            return {k: self._decode_json_recursively(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._decode_json_recursively(item) for item in obj]
        elif isinstance(obj, str):
            # Try to parse string as JSON
            try:
                parsed = json.loads(obj)
                # If successfully parsed, recursively process it
                if isinstance(parsed, (dict, list)):
                    return self._decode_json_recursively(parsed)
            except (json.JSONDecodeError, ValueError):
                # Not valid JSON, just decode escape sequences
                pass
            
            # Decode escape sequences
            decoded = obj.replace('\\n', '\n')
            decoded = decoded.replace('\\r', '\r')
            decoded = decoded.replace('\\t', '\t')
            decoded = decoded.replace('\\"', '"')
            decoded = decoded.replace('\\\\', '\\')
            return decoded
        else:
            # Return primitive types as-is
            return obj
    
    def _decode_content_for_display(self, content: str) -> str:
        """
        Decode content for display, handling JSON strings with escape sequences
        
        Args:
            content: Content string that may contain JSON escape sequences
            
        Returns:
            Decoded content with proper newlines and other special characters
        """
        try:
            import json
            
            # Try to parse as JSON if it looks like a JSON string
            if content.startswith('{') or content.startswith('['):
                try:
                    # Parse and recursively decode all nested strings
                    parsed = json.loads(content)
                    if isinstance(parsed, (dict, list)):
                        decoded_obj = self._decode_json_recursively(parsed)
                        return json.dumps(decoded_obj, indent=2, ensure_ascii=False)
                except json.JSONDecodeError:
                    # Not valid JSON, continue with string decoding
                    pass
            
            # Decode escape sequences in the string
            # Replace common escape sequences with their actual characters
            decoded = content
            
            # Handle escaped newlines and other characters
            decoded = decoded.replace('\\n', '\n')
            decoded = decoded.replace('\\r', '\r')
            decoded = decoded.replace('\\t', '\t')
            decoded = decoded.replace('\\"', '"')
            decoded = decoded.replace('\\\\', '\\')
            
            return decoded
            
        except Exception as e:
            # If decoding fails, return original content
            logger.debug(f"Content decoding failed: {e}, returning original")
            return content


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
