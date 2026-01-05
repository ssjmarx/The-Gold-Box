"""
The Gold Box - Message Protocol
Handles WebSocket message serialization and routing
"""

import json
import logging
import time
import uuid
from typing import Dict, Any, Optional, Union
from datetime import datetime

logger = logging.getLogger(__name__)

class MessageProtocol:
    """
    Handles WebSocket message serialization, deserialization, and validation
    Provides standardized message format for The Gold Box WebSocket communication
    """
    
    # Message type constants
    TYPE_CONNECT = "connect"
    TYPE_CONNECTED = "connected"
    TYPE_DISCONNECT = "disconnect"
    TYPE_CHAT_REQUEST = "chat_request"
    TYPE_CHAT_RESPONSE = "chat_response"
    TYPE_PING = "ping"
    TYPE_PONG = "pong"
    TYPE_ERROR = "error"
    TYPE_STATUS = "status"
    TYPE_BROADCAST = "broadcast"
    TYPE_EXECUTE_ROLL = "execute_roll"
    TYPE_ROLL_RESULT = "roll_result"
    TYPE_COMBAT_STATE = "combat_state"
    TYPE_COMBAT_STATE_REFRESH = "combat_state_refresh"
    TYPE_CREATE_ENCOUNTER = "create_encounter"
    TYPE_DELETE_ENCOUNTER = "delete_encounter"
    TYPE_ADVANCE_TURN = "advance_turn"
    TYPE_GET_ACTOR_DETAILS = "get_actor_details"
    TYPE_TOKEN_ACTOR_DETAILS = "token_actor_details"
    TYPE_MODIFY_TOKEN_ATTRIBUTE = "modify_token_attribute"
    TYPE_GAME_DELTA = "game_delta"
    TYPE_WORLD_STATE_SYNC = "world_state_sync"
    TYPE_WORLD_STATE_REFRESH = "world_state_refresh"
    
    # Protocol version
    PROTOCOL_VERSION = "1.0"
    
    @staticmethod
    def create_message(message_type: str, data: Any = None, request_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Create a standardized message object
        """
        return {
            "type": message_type,
            "data": data or {},
            "timestamp": time.time(),
            "request_id": request_id or str(uuid.uuid4()),
            "protocol_version": MessageProtocol.PROTOCOL_VERSION
        }
    
    @staticmethod
    def create_connect_message(client_id: str, token: str, world_info: Dict[str, Any], user_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a connection message
        """
        return {
            "type": MessageProtocol.TYPE_CONNECT,
            "client_id": client_id,
            "token": token,
            "world_info": world_info,
            "user_info": user_info,
            "timestamp": time.time(),
            "protocol_version": MessageProtocol.PROTOCOL_VERSION
        }
    
    @staticmethod
    def create_connected_response(client_id: str, message: str = "Connected successfully") -> Dict[str, Any]:
        """
        Create a connection confirmation response
        """
        return MessageProtocol.create_message(
            MessageProtocol.TYPE_CONNECTED,
            {
                "client_id": client_id,
                "message": message,
                "server_time": datetime.now().isoformat()
            }
        )
    
    @staticmethod
    def create_chat_request(messages: list, context_count: int = 15, scene_id: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        """
        Create a chat request message
        """
        data = {
            "messages": messages,
            "context_count": context_count
        }
        
        # Add optional parameters
        if scene_id:
            data["scene_id"] = scene_id
        
        # Add any additional parameters
        data.update(kwargs)
        
        return MessageProtocol.create_message(
            MessageProtocol.TYPE_CHAT_REQUEST,
            data
        )
    
    @staticmethod
    def create_chat_response(response: str, metadata: Dict[str, Any] = None, request_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Create a chat response message
        """
        return MessageProtocol.create_message(
            MessageProtocol.TYPE_CHAT_RESPONSE,
            {
                "response": response,
                "metadata": metadata or {},
                "provider_used": metadata.get("provider_used", "unknown") if metadata else "unknown",
                "model_used": metadata.get("model_used", "unknown") if metadata else "unknown",
                "tokens_used": metadata.get("tokens_used", 0) if metadata else 0
            },
            request_id
        )
    
    @staticmethod
    def create_ping_message() -> Dict[str, Any]:
        """
        Create a ping message
        """
        return MessageProtocol.create_message(MessageProtocol.TYPE_PING)
    
    @staticmethod
    def create_pong_message() -> Dict[str, Any]:
        """
        Create a pong message
        """
        return MessageProtocol.create_message(MessageProtocol.TYPE_PONG)
    
    @staticmethod
    def create_error_message(error: str, code: Optional[str] = None, details: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Create an error message
        """
        data = {
            "error": error
        }
        
        if code:
            data["error_code"] = code
        
        if details:
            data["details"] = details
        
        return MessageProtocol.create_message(
            MessageProtocol.TYPE_ERROR,
            data
        )
    
    @staticmethod
    def create_status_message(status: str, details: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Create a status message
        """
        return MessageProtocol.create_message(
            MessageProtocol.TYPE_STATUS,
            {
                "status": status,
                "details": details or {},
                "server_time": datetime.now().isoformat()
            }
        )
    
    @staticmethod
    def create_broadcast_message(message: str, broadcast_type: str = "info", data: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Create a broadcast message
        """
        return MessageProtocol.create_message(
            MessageProtocol.TYPE_BROADCAST,
            {
                "message": message,
                "broadcast_type": broadcast_type,
                "data": data or {}
            }
        )
    
    @staticmethod
    def serialize_message(message: Dict[str, Any]) -> str:
        """
        Serialize a message to JSON string
        """
        try:
            return json.dumps(message, ensure_ascii=False, separators=(',', ':'))
        except Exception as e:
            logger.error(f"Error serializing message: {e}")
            # Return a simple error message if serialization fails
            error_msg = MessageProtocol.create_error_message(f"Message serialization failed: {e}")
            return json.dumps(error_msg, ensure_ascii=False, separators=(',', ':'))
    
    @staticmethod
    def deserialize_message(raw_message: str) -> Optional[Dict[str, Any]]:
        """
        Deserialize a message from JSON string
        """
        try:
            message = json.loads(raw_message)
            
            # Validate basic message structure
            if not isinstance(message, dict):
                logger.error("Message must be a dictionary")
                return None
            
            # Validate required fields
            if "type" not in message:
                logger.error("Message missing required 'type' field")
                return None
            
            # Add timestamp if missing
            if "timestamp" not in message:
                message["timestamp"] = time.time()
            
            return message
            
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in message: {e}")
            return None
        except Exception as e:
            logger.error(f"Error deserializing message: {e}")
            return None
    
    @staticmethod
    def validate_message(message: Dict[str, Any], expected_type: Optional[str] = None) -> tuple[bool, Optional[str]]:
        """
        Validate a message structure and content
        Returns (is_valid, error_message)
        """
        try:
            # Check message type
            message_type = message.get("type")
            if not message_type:
                return False, "Message type is required"
            
            if expected_type and message_type != expected_type:
                return False, f"Expected message type '{expected_type}', got '{message_type}'"
            
            # Check protocol version if present
            protocol_version = message.get("protocol_version")
            if protocol_version and protocol_version != MessageProtocol.PROTOCOL_VERSION:
                logger.warning(f"Protocol version mismatch: expected {MessageProtocol.PROTOCOL_VERSION}, got {protocol_version}")
            
            # Type-specific validation
            if message_type == MessageProtocol.TYPE_CONNECT:
                return MessageProtocol._validate_connect_message(message)
            elif message_type == MessageProtocol.TYPE_CHAT_REQUEST:
                return MessageProtocol._validate_chat_request_message(message)
            elif message_type == MessageProtocol.TYPE_CHAT_RESPONSE:
                return MessageProtocol._validate_chat_response_message(message)
            elif message_type in [MessageProtocol.TYPE_PING, MessageProtocol.TYPE_PONG]:
                return True, None  # Ping/pong messages are simple
            
            return True, None
            
        except Exception as e:
            return False, f"Validation error: {e}"
    
    @staticmethod
    def _validate_connect_message(message: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """Validate connection message"""
        required_fields = ["client_id", "token", "world_info", "user_info"]
        
        for field in required_fields:
            if field not in message:
                return False, f"Connection message missing required field: {field}"
        
        # Validate world_info
        world_info = message.get("world_info")
        if not isinstance(world_info, dict):
            return False, "world_info must be a dictionary"
        
        # Validate user_info
        user_info = message.get("user_info")
        if not isinstance(user_info, dict):
            return False, "user_info must be a dictionary"
        
        # Check required user_info fields
        required_user_fields = ["id", "name"]
        for field in required_user_fields:
            if field not in user_info:
                return False, f"user_info missing required field: {field}"
        
        return True, None
    
    @staticmethod
    def _validate_chat_request_message(message: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """Validate chat request message"""
        data = message.get("data", {})
        
        if not isinstance(data, dict):
            return False, "Chat request data must be a dictionary"
        
        # Check messages field
        messages = data.get("messages")
        if not isinstance(messages, list):
            return False, "messages field must be a list"
        
        if len(messages) == 0:
            return False, "messages field cannot be empty"
        
        # Validate message content
        for i, msg in enumerate(messages):
            if not isinstance(msg, (str, dict)):
                return False, f"Message {i} must be a string or dictionary"
            
            if isinstance(msg, dict):
                if "content" not in msg:
                    return False, f"Message {i} dictionary missing 'content' field"
        
        return True, None
    
    @staticmethod
    def _validate_chat_response_message(message: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """Validate chat response message"""
        data = message.get("data", {})
        
        if not isinstance(data, dict):
            return False, "Chat response data must be a dictionary"
        
        # Check response field
        response = data.get("response")
        if not isinstance(response, str):
            return False, "response field must be a string"
        
        return True, None
    
    @staticmethod
    def extract_request_id(message: Dict[str, Any]) -> Optional[str]:
        """
        Extract request ID from message
        """
        return message.get("request_id")
    
    @staticmethod
    def extract_message_data(message: Dict[str, Any]) -> Any:
        """
        Extract data payload from message
        """
        return message.get("data")
    
    @staticmethod
    def get_message_type(message: Dict[str, Any]) -> Optional[str]:
        """
        Get message type from message
        """
        return message.get("type")
    
    @staticmethod
    def is_system_message(message: Dict[str, Any]) -> bool:
        """
        Check if message is a system message (not user-generated)
        """
        message_type = MessageProtocol.get_message_type(message)
        system_types = [
            MessageProtocol.TYPE_CONNECT,
            MessageProtocol.TYPE_CONNECTED,
            MessageProtocol.TYPE_DISCONNECT,
            MessageProtocol.TYPE_PING,
            MessageProtocol.TYPE_PONG,
            MessageProtocol.TYPE_ERROR,
            MessageProtocol.TYPE_STATUS
        ]
        return message_type in system_types
    
    @staticmethod
    def is_user_message(message: Dict[str, Any]) -> bool:
        """
        Check if message is user-generated
        """
        message_type = MessageProtocol.get_message_type(message)
        user_types = [
            MessageProtocol.TYPE_CHAT_REQUEST,
            MessageProtocol.TYPE_CHAT_RESPONSE
        ]
        return message_type in user_types
    
    @staticmethod
    def create_response_for_request(request_message: Dict[str, Any], response_data: Any, success: bool = True) -> Dict[str, Any]:
        """
        Create a response message that correlates with a request
        """
        request_id = MessageProtocol.extract_request_id(request_message)
        request_type = MessageProtocol.get_message_type(request_message)
        
        if success:
            if request_type == MessageProtocol.TYPE_CHAT_REQUEST:
                return MessageProtocol.create_chat_response(response_data, request_id=request_id)
            else:
                return MessageProtocol.create_message(
                    f"{request_type}_response",
                    response_data,
                    request_id
                )
        else:
            # Create error response
            error_message = response_data if isinstance(response_data, str) else str(response_data)
            return MessageProtocol.create_error_message(error_message, request_id=request_id)
