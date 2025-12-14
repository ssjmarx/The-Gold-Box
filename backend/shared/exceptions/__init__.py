"""
Custom Exceptions for The Gold Box
Provides specific exception types to replace generic Exception handling
"""

class GoldBoxException(Exception):
    """Base exception for The Gold Box project"""
    pass

class ServiceException(GoldBoxException):
    """Exceptions related to service management and access"""
    pass

class ServiceNotInitializedException(ServiceException):
    """Raised when attempting to access a service that hasn't been initialized"""
    pass

class ServiceNotFoundException(ServiceException):
    """Raised when attempting to access a service that doesn't exist"""
    pass

class APIException(GoldBoxException):
    """Exceptions related to API calls and external services"""
    pass

class APIKeyException(APIException):
    """Raised when API key validation fails"""
    pass

class ProviderException(APIException):
    """Raised when AI provider operations fail"""
    pass

class TimeoutException(APIException):
    """Raised when API calls timeout"""
    pass

class MessageException(GoldBoxException):
    """Exceptions related to message processing and collection"""
    pass

class MessageCollectionException(MessageException):
    """Raised when message collection fails"""
    pass

class MessageValidationException(MessageException):
    """Raised when message validation fails"""
    pass

class ConfigurationException(GoldBoxException):
    """Exceptions related to configuration issues"""
    pass

class ValidationException(ConfigurationException):
    """Raised when configuration validation fails"""
    pass

class ProcessingException(GoldBoxException):
    """Exceptions related to data processing"""
    pass

class RollProcessingException(ProcessingException):
    """Raised when roll data processing fails"""
    pass

class ContentProcessingException(ProcessingException):
    """Raised when content processing fails"""
    pass
