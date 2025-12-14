"""
The Gold Box - Client Manager
Manages WebSocket client connections and sessions
"""

import logging
import time
from typing import Dict, Any, Optional, Set
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class ClientManager:
    """
    Manages WebSocket client connections and sessions
    Handles authentication, registration, and message routing
    """
    
    def __init__(self):
        self.clients: Dict[str, Dict[str, Any]] = {}
        self.sessions: Dict[str, Set[str]] = {}  # token -> set of client_ids
        self.last_cleanup = time.time()
        self.client_timeout = 300  # 5 minutes
        self.session_timeout = 3600  # 1 hour
        
    def register_client(self, client_id: str, token: str, client_info: Dict[str, Any]) -> bool:
        """
        Register a new client connection
        """
        try:
            # Check if client already exists
            if client_id in self.clients:
                logger.warning(f"Client {client_id} already registered")
                return False
            
            # Validate client info
            if not self.validate_client_info(client_info):
                logger.error(f"Invalid client info for {client_id}")
                return False
            
            # Register client
            self.clients[client_id] = {
                **client_info,
                "registered_at": datetime.now().isoformat(),
                "last_activity": time.time(),
                "token": token,
                "is_active": True
            }
            
            # Add to session
            if token not in self.sessions:
                self.sessions[token] = set()
            self.sessions[token].add(client_id)
            
            logger.info(f"Client {client_id} registered successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error registering client {client_id}: {e}")
            return False
    
    def unregister_client(self, client_id: str) -> bool:
        """
        Unregister a client connection
        """
        try:
            if client_id not in self.clients:
                logger.warning(f"Client {client_id} not found for unregistration")
                return False
            
            # Get token before removing client
            token = self.clients[client_id].get("token")
            
            # Remove from clients
            del self.clients[client_id]
            
            # Remove from session
            if token and token in self.sessions:
                self.sessions[token].discard(client_id)
                if not self.sessions[token]:
                    del self.sessions[token]
            
            logger.info(f"Client {client_id} unregistered successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error unregistering client {client_id}: {e}")
            return False
    
    def get_client(self, client_id: str) -> Optional[Dict[str, Any]]:
        """
        Get client information by ID
        """
        return self.clients.get(client_id)
    
    def update_client_activity(self, client_id: str) -> bool:
        """
        Update client's last activity timestamp
        """
        try:
            if client_id in self.clients:
                self.clients[client_id]["last_activity"] = time.time()
                self.clients[client_id]["is_active"] = True
                return True
            return False
            
        except Exception as e:
            logger.error(f"Error updating activity for client {client_id}: {e}")
            return False
    
    def get_session_clients(self, token: str) -> Set[str]:
        """
        Get all client IDs in a session
        """
        return self.sessions.get(token, set()).copy()
    
    def is_client_active(self, client_id: str) -> bool:
        """
        Check if client is active and within timeout
        """
        try:
            client = self.clients.get(client_id)
            if not client:
                return False
            
            # Check if client was recently active
            last_activity = client.get("last_activity", 0)
            return (time.time() - last_activity) < self.client_timeout
            
        except Exception as e:
            logger.error(f"Error checking activity for client {client_id}: {e}")
            return False
    
    def cleanup_inactive_clients(self) -> int:
        """
        Remove inactive clients and sessions
        Returns count of cleaned up clients
        """
        try:
            current_time = time.time()
            cleanup_count = 0
            
            # Check if cleanup is needed (run every 5 minutes)
            if current_time - self.last_cleanup < 300:
                return 0
            
            self.last_cleanup = current_time
            
            # Find inactive clients
            inactive_clients = []
            for client_id, client_info in self.clients.items():
                last_activity = client_info.get("last_activity", 0)
                if current_time - last_activity > self.client_timeout:
                    inactive_clients.append(client_id)
            
            # Remove inactive clients
            for client_id in inactive_clients:
                if self.unregister_client(client_id):
                    cleanup_count += 1
            
            # Clean up empty sessions
            empty_sessions = []
            for token, client_ids in self.sessions.items():
                if not client_ids:
                    empty_sessions.append(token)
            
            for token in empty_sessions:
                del self.sessions[token]
                logger.info(f"Cleaned up empty session {token[:8]}...")
            
            if cleanup_count > 0 or empty_sessions:
                logger.info(f"Cleanup completed: {cleanup_count} clients, {len(empty_sessions)} sessions removed")
            
            return cleanup_count
            
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
            return 0
    
    def get_client_stats(self) -> Dict[str, Any]:
        """
        Get statistics about connected clients
        """
        try:
            active_clients = sum(1 for client in self.clients.values() 
                             if self.is_client_active(list(client.keys())[0] if client else ""))
            
            total_clients = len(self.clients)
            active_sessions = len(self.sessions)
            
            # Get primary GM info
            primary_gm_clients = []
            for client_id, client_info in self.clients.items():
                user_info = client_info.get("user_info", {})
                if user_info.get("is_primary_gm", False):
                    primary_gm_clients.append(client_id)
            
            return {
                "total_clients": total_clients,
                "active_clients": active_clients,
                "inactive_clients": total_clients - active_clients,
                "active_sessions": active_sessions,
                "primary_gm_clients": len(primary_gm_clients),
                "cleanup_interval": self.client_timeout,
                "last_cleanup": datetime.fromtimestamp(self.last_cleanup).isoformat() if self.last_cleanup else None
            }
            
        except Exception as e:
            logger.error(f"Error getting client stats: {e}")
            return {
                "error": str(e),
                "total_clients": 0,
                "active_clients": 0,
                "active_sessions": 0
            }
    
    def validate_client_info(self, client_info: Dict[str, Any]) -> bool:
        """
        Validate client connection information
        """
        try:
            # Check required fields
            required_fields = ["world_info", "user_info"]
            for field in required_fields:
                if field not in client_info:
                    logger.error(f"Missing required field in client info: {field}")
                    return False
            
            # Validate world info
            world_info = client_info.get("world_info", {})
            if not isinstance(world_info, dict):
                logger.error("world_info must be a dictionary")
                return False
            
            # Validate user info
            user_info = client_info.get("user_info", {})
            if not isinstance(user_info, dict):
                logger.error("user_info must be a dictionary")
                return False
            
            # Check required user info fields
            if "id" not in user_info or "name" not in user_info:
                logger.error("user_info must contain 'id' and 'name' fields")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error validating client info: {e}")
            return False
    
    def get_world_info(self, client_id: str) -> Optional[Dict[str, Any]]:
        """
        Get world information for a client
        """
        client = self.clients.get(client_id)
        return client.get("world_info") if client else None
    
    def get_user_info(self, client_id: str) -> Optional[Dict[str, Any]]:
        """
        Get user information for a client
        """
        client = self.clients.get(client_id)
        return client.get("user_info") if client else None
    
    def is_primary_gm(self, client_id: str) -> bool:
        """
        Check if client is primary GM
        """
        client = self.clients.get(client_id)
        if not client:
            return False
        
        user_info = client.get("user_info", {})
        return user_info.get("is_primary_gm", False)
    
    def get_primary_gm_client(self, token: str) -> Optional[str]:
        """
        Get primary GM client ID for a session
        """
        try:
            client_ids = self.sessions.get(token, set())
            
            for client_id in client_ids:
                if self.is_primary_gm(client_id):
                    return client_id
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting primary GM client for token {token[:8]}: {e}")
            return None

# Convenience functions that use ServiceRegistry via service factory
def cleanup_inactive_clients():
    """Trigger cleanup of inactive clients using ServiceRegistry"""
    # Avoid circular import - these functions should be called from within the class
    # or via ServiceFactory from external modules
    raise NotImplementedError("Use ClientManager instance via ServiceFactory instead")

def get_client_stats() -> Dict[str, Any]:
    """Get client statistics using ServiceRegistry"""
    # Avoid circular import - these functions should be called from within the class
    # or via ServiceFactory from external modules
    raise NotImplementedError("Use ClientManager instance via ServiceFactory instead")
