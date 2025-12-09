"""
The Gold Box - Universal Service Registry

Central registry for all shared services to eliminate module import fragility
and provider manager duplication across the backend.

License: CC-BY-NC-SA 4.0 (compatible with dependencies)
"""

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

class ServiceRegistry:
    """
    Central registry for all shared services
    
    Eliminates module import dependencies and provides single source of truth
    for all service instances across the backend.
    """
    
    _services: Dict[str, Any] = {}
    _initialized: bool = False
    _startup_order: List[str] = []
    
    @classmethod
    def register(cls, name: str, service: Any, overwrite: bool = False) -> bool:
        """
        Register a service instance
        
        Args:
            name: Service name for registration
            service: Service instance to register
            overwrite: Whether to overwrite existing service
            
        Returns:
            True if registered successfully, False otherwise
        """
        try:
            if name in cls._services and not overwrite:
                existing_service = cls._services[name]
                logger.error(f"❌ Service '{name}' already registered: {type(existing_service).__name__}")
                return False
            
            cls._services[name] = service
            cls._startup_order.append(name)
            
            service_type = type(service).__name__
            logger.info(f"✅ Registered service: {name} ({service_type})")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to register service '{name}': {e}")
            return False
    
    @classmethod
    def get(cls, name: str, default: Any = None) -> Any:
        """
        Get a registered service
        
        Args:
            name: Service name to retrieve
            default: Default value if service not found
            
        Returns:
            Service instance or default value
            
        Raises:
            ValueError: If service not found and no default provided
        """
        try:
            if name not in cls._services:
                if default is not None:
                    logger.warning(f"⚠️ Service '{name}' not found, returning default")
                    return default
                
                available_services = list(cls._services.keys())
                raise ValueError(
                    f"❌ Service '{name}' not registered. "
                    f"Available services: {available_services}"
                )
            
            service = cls._services[name]
            logger.debug(f"🔧 Retrieved service: {name} ({type(service).__name__})")
            return service
            
        except Exception as e:
            logger.error(f"❌ Failed to get service '{name}': {e}")
            if default is not None:
                return default
            raise
    
    @classmethod
    def is_registered(cls, name: str) -> bool:
        """
        Check if service is registered
        
        Args:
            name: Service name to check
            
        Returns:
            True if service is registered, False otherwise
        """
        is_registered = name in cls._services
        logger.debug(f"🔍 Service '{name}' registered: {is_registered}")
        return is_registered
    
    @classmethod
    def list_services(cls) -> List[str]:
        """
        List all registered services
        
        Returns:
            List of registered service names
        """
        service_list = list(cls._services.keys())
        logger.debug(f"📋 Registered services: {service_list}")
        return service_list
    
    @classmethod
    def get_service_info(cls) -> Dict[str, Dict[str, Any]]:
        """
        Get detailed information about all registered services
        
        Returns:
            Dictionary with service information
        """
        service_info = {}
        for name, service in cls._services.items():
            service_type = type(service).__name__
            service_module = type(service).__module__
            service_info[name] = {
                'name': name,
                'type': service_type,
                'module': service_module,
                'registered_order': cls._startup_order.index(name) if name in cls._startup_order else -1
            }
        
        return service_info
    
    @classmethod
    def initialize_complete(cls) -> bool:
        """
        Mark registry as fully initialized
        
        Returns:
            True if marked successfully
        """
        try:
            cls._initialized = True
            service_count = len(cls._services)
            
            logger.info(f"🎉 Service Registry initialized with {service_count} services")
            logger.info(f"📋 Services in startup order: {cls._startup_order}")
            
            # Log all registered services
            for name in cls._startup_order:
                service = cls._services[name]
                service_type = type(service).__name__
                logger.info(f"  ✓ {name}: {service_type}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to mark registry as initialized: {e}")
            return False
    
    @classmethod
    def is_ready(cls) -> bool:
        """
        Check if registry is ready for use
        
        Returns:
            True if registry is initialized, False otherwise
        """
        is_ready = cls._initialized
        logger.debug(f"🟢 Registry ready: {is_ready}")
        return is_ready
    
    @classmethod
    def validate_required_services(cls, required_services: List[str]) -> bool:
        """
        Validate that all required services are registered
        
        Args:
            required_services: List of required service names
            
        Returns:
            True if all required services are registered, False otherwise
        """
        missing_services = []
        for service_name in required_services:
            if not cls.is_registered(service_name):
                missing_services.append(service_name)
        
        if missing_services:
            logger.error(f"❌ Missing required services: {missing_services}")
            logger.error(f"❌ Available services: {cls.list_services()}")
            return False
        
        logger.info(f"✅ All required services registered: {required_services}")
        return True
    
    @classmethod
    def get_startup_order(cls) -> List[str]:
        """
        Get the order in which services were registered
        
        Returns:
            List of service names in registration order
        """
        return cls._startup_order.copy()
    
    @classmethod
    def reset(cls) -> bool:
        """
        Reset the registry (for testing purposes)
        
        Returns:
            True if reset successfully
        """
        try:
            cls._services.clear()
            cls._initialized = False
            cls._startup_order.clear()
            logger.warning("🔄 Service Registry reset")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to reset registry: {e}")
            return False

# Convenience functions for common operations
def register_service(name: str, service: Any, overwrite: bool = False) -> bool:
    """Convenience function to register a service"""
    return ServiceRegistry.register(name, service, overwrite)

def get_service(name: str, default: Any = None) -> Any:
    """Convenience function to get a service"""
    return ServiceRegistry.get(name, default)

def is_service_registered(name: str) -> bool:
    """Convenience function to check if service is registered"""
    return ServiceRegistry.is_registered(name)

def list_registered_services() -> List[str]:
    """Convenience function to list all services"""
    return ServiceRegistry.list_services()

def is_registry_ready() -> bool:
    """Convenience function to check if registry is ready"""
    return ServiceRegistry.is_ready()

def initialize_registry_complete() -> bool:
    """Convenience function to mark registry as ready"""
    return ServiceRegistry.initialize_complete()
