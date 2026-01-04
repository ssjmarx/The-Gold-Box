"""
The Gold Box - Server Startup Orchestrator

Main startup module that coordinates all initialization phases.

License: CC-BY-NC-SA 4.0 (compatible with dependencies)
"""

import os
import sys
import asyncio
import logging
from typing import Dict, Any, Optional
from fastapi import FastAPI
import uvicorn

from .config import get_server_config
from .security import get_security_components, initialize_security_middleware
from .services import get_global_services, setup_application_routers
from .validation import (
    find_available_port, manage_keys, manage_admin_password, 
    validate_server_requirements, get_configured_providers,
    validate_startup_environment
)

logger = logging.getLogger(__name__)

class ServerStartup:
    """
    Main server startup orchestrator that coordinates all initialization phases.
    """
    
    def __init__(self):
        self.config: Dict[str, Any] = {}
        self.security_components: Dict[str, Any] = {}
        self.global_services: Dict[str, Any] = {}
        self.app: Optional[FastAPI] = None
        self.manager = None
        self.available_port: Optional[int] = None
    
    
    def get_effective_port(self) -> int:
        """
        Get port from environment override or config default.
        
        Returns:
            Port to use for server startup
        """
        # Check environment variable override first
        override_port = os.getenv('GOLD_BOX_PORT_OVERRIDE')
        if override_port:
            try:
                port = int(override_port)
                if 1024 <= port <= 65535:
                    logger.info(f"Using port override from environment: {port}")
                    return port
                else:
                    logger.warning(f"Invalid GOLD_BOX_PORT_OVERRIDE: {port}, must be 1024-65535")
            except ValueError:
                logger.warning(f"Invalid GOLD_BOX_PORT_OVERRIDE: {override_port}, not a number")
        
        # Use config default
        return self.config.get('GOLD_BOX_PORT', 5000)
        
    def load_configuration(self) -> bool:
        """
        Load all server configuration.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            self.config = get_server_config()
            logger.info("Server configuration loaded successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to load configuration: {e}")
            return False
    
    def initialize_security(self) -> bool:
        """
        Initialize all security components.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            # Get security components
            self.security_components = get_security_components(self.config)
            
            if not self.security_components.get('security_valid', False):
                logger.error("Security components validation failed")
                return False
            
            logger.info("Security components initialized successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize security: {e}")
            return False
    
    def setup_application(self) -> bool:
        """
        Setup the FastAPI application.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            # Initialize FastAPI app
            self.app = FastAPI(
                title="The Gold Box Backend",
                description="AI-powered Foundry VTT Module Backend",
                version="0.2.3",
                docs_url="/docs" if self.config['FLASK_ENV'] == 'development' else None,
                redoc_url=None
            )
            
            # Setup application routers
            if not setup_application_routers(self.app):
                logger.error("Failed to setup application routers")
                return False
            
            # Initialize security middleware
            from ..security.security import SECURITY_CONFIG
            if not initialize_security_middleware(
                self.app, 
                self.config['CORS_ORIGINS'], 
                SECURITY_CONFIG
            ):
                logger.error("Failed to initialize security middleware")
                return False
            
            logger.info("FastAPI application setup completed")
            return True
        except Exception as e:
            logger.error(f"Failed to setup application: {e}")
            return False
    
    def initialize_global_services(self) -> bool:
        """
        Initialize all global services.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            self.global_services = get_global_services()
            
            if not self.global_services.get('services_valid', False):
                logger.error("Global services validation failed")
                return False
            
            logger.info("Global services initialized successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize global services: {e}")
            return False
    
    def validate_requirements(self) -> bool:
        """
        Validate all server requirements including keys and passwords.
        
        Returns:
            True if all requirements are met, False otherwise
        """
        try:
            # Direct instantiation to avoid circular dependency during startup
            from services.system_services.key_manager import MultiKeyManager
            from services.system_services.provider_manager import ProviderManager
            
            # Create instances directly first
            provider_manager = ProviderManager()
            self.manager = MultiKeyManager('server_files/keys.enc', provider_manager)  # Pass provider_manager as dependency
            
            # Initialize ServiceRegistry for these core services
            from services.system_services.registry import ServiceRegistry
            
            # Mark registry as initializing
            ServiceRegistry._is_ready = True
            
            # Register key manager and provider manager
            if not ServiceRegistry.register('key_manager', self.manager):
                logger.error("Failed to register key manager with service registry")
                return False
            
            if not ServiceRegistry.register('provider_manager', provider_manager):
                logger.error("Failed to register provider manager with service registry")
                return False
            
            logger.info("OK Key manager and provider manager registered with service registry (direct initialization)")
            
            # Handle key management
            if not manage_keys(self.manager, self.config['GOLD_BOX_KEYCHANGE']):
                return False
            
            # Validate server requirements (only if NOT keychange)
            if not self.config['GOLD_BOX_KEYCHANGE']:
                if not validate_server_requirements(self.manager):
                    return False
            else:
                # For keychange, only validate admin password if needed
                if not self.manager.get_password_status():
                    if not manage_admin_password(self.manager):
                        return False
            
            # Set environment variables
            if not self.manager.set_environment_variables():
                logger.error("Failed to set environment variables")
                return False
            
            logger.info("All requirements validated successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to validate requirements: {e}")
            return False
    
    def validate_startup_environment(self) -> bool:
        """
        Validate the startup environment and find available port.
        
        Returns:
            True if environment is valid, False otherwise
        """
        try:
            # Get effective port (environment override or config)
            start_port = self.get_effective_port()
            
            # Find available port with simple fallback (max 3 attempts)
            self.available_port = find_available_port(start_port)
            if not self.available_port:
                logger.error(f"No available ports found starting from {start_port}")
                return False
            
            # Validate startup environment
            if not validate_startup_environment(self.config):
                return False
            
            logger.info(f"Startup environment validated, using port {self.available_port}")
            return True
        except Exception as e:
            logger.error(f"Failed to validate startup environment: {e}")
            return False
    
    def display_startup_info(self) -> None:
        """
        Display startup information to the console.
        """
        try:
            # Clear terminal for clean startup display
            os.system('clear' if os.name == 'posix' else 'cls')
            
            print("=" * 60)
            print("The Gold Box FastAPI Backend Server")
            print("=" * 60)
            print(f"Environment: {self.config['FLASK_ENV']}")
            
            # List all loaded API keys from provider manager
            loaded_keys = []
            if hasattr(self.manager, 'keys_data') and self.manager.keys_data:
                for provider_id, key_value in self.manager.keys_data.items():
                    if key_value:  # Check if key has a value (any length)
                        # Get provider name from provider manager for better display
                        provider_info = self.manager.provider_manager.get_provider(provider_id)
                        if provider_info:
                            provider_name = provider_info.get('name', provider_id.upper())
                        else:
                            provider_name = provider_id.upper().replace('_API_KEY', '')
                        loaded_keys.append(provider_name)
            
            print(f"Loaded API Keys: {', '.join(loaded_keys) if loaded_keys else 'None'}")
            print(f"Rate Limiting: {self.config['RATE_LIMIT_MAX_REQUESTS']} requests per {self.config['RATE_LIMIT_WINDOW_SECONDS']} seconds")
            
            # CORS Configuration Summary
            print(f"CORS Origins: {len(self.config['CORS_ORIGINS'])} configured")
            if self.config['is_development']:
                print("  Development CORS origins (localhost only):")
                for origin in self.config['CORS_ORIGINS']:
                    print(f"    - {origin}")
            else:
                print("  Production CORS origins (explicitly configured)")
                for origin in self.config['CORS_ORIGINS']:
                    print(f"    - {origin}")
            
            # Server startup information
            print(f"FastAPI Server starting on http://localhost:{self.available_port}")
            print("=" * 60)
            print("Universal Security Middleware is now active and protecting all endpoints")
            print("=" * 60)
            
        except Exception as e:
            logger.error(f"Failed to display startup info: {e}")
    
    def start_server(self) -> None:
        """
        Start the FastAPI server with uvicorn.
        """
        try:
            # Display startup information
            self.display_startup_info()
            
            # Initialize WebSocket chat handler
            print("Initializing WebSocket endpoint...")
            from .services import start_websocket_chat_handler
            websocket_started = asyncio.run(start_websocket_chat_handler())
            if not websocket_started:
                print("WARNING  Warning: Failed to initialize WebSocket endpoint. Native chat functionality may not work.")
            
            # Start FastAPI server with uvicorn
            uvicorn.run(
                self.app,
                host='localhost',
                port=self.available_port,
                log_level="info" if not self.config['debug_mode'] else "debug",
                access_log=True
            )
            
        except Exception as e:
            logger.error(f"Failed to start server: {e}")
            sys.exit(1)
    
    def run_startup_sequence(self) -> bool:
        """
        Run the complete startup sequence.
        
        Returns:
            True if startup successful, False otherwise
        """
        try:
            logger.info("Starting server startup sequence...")
            
            # Phase 1: Load configuration
            if not self.load_configuration():
                return False
            
            # Phase 2: Validate requirements (keys, passwords)
            if not self.validate_requirements():
                return False
            
            # Phase 3: Initialize global services
            if not self.initialize_global_services():
                return False
            
            # Phase 4: Initialize security
            if not self.initialize_security():
                return False
            
            # Phase 5: Setup application (now services are ready)
            if not self.setup_application():
                return False
            
            # Phase 6: Validate startup environment
            if not self.validate_startup_environment():
                return False
            
            logger.info("Server startup sequence completed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Startup sequence failed: {e}")
            return False
    
    def get_startup_components(self) -> Dict[str, Any]:
        """
        Get all startup components for access by other modules.
        
        Returns:
            Dictionary containing all startup components
        """
        return {
            'config': self.config,
            'security_components': self.security_components,
            'global_services': self.global_services,
            'app': self.app,
            'manager': self.manager,
            'available_port': self.available_port
        }

def run_server_startup() -> ServerStartup:
    """
    Main entry point for server startup.
    
    Returns:
        Initialized ServerStartup instance
    """
    startup = ServerStartup()
    
    if not startup.run_startup_sequence():
        logger.error("Server startup failed")
        sys.exit(1)
    
    return startup

if __name__ == '__main__':
    # This allows the startup module to be run directly for testing
    startup = run_server_startup()
    startup.start_server()
