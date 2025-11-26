"""
Server module exports for The Gold Box
"""

from .key_manager import MultiKeyManager
from .processor import ChatContextProcessor
from .ai_service import AIService
from .api_chat_processor import APIChatProcessor
from .ai_chat_processor import AIChatProcessor
from .provider_manager import ProviderManager
from .universal_settings import UniversalSettings, extract_universal_settings, get_provider_config

# Import settings_manager from server.py (it's defined there)
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# This will be set by server.py when it starts
settings_manager = None

def get_settings_manager():
    """Get the global settings manager instance"""
    global settings_manager
    return settings_manager

__all__ = [
    'MultiKeyManager',
    'ChatContextProcessor', 
    'AIService',
    'APIChatProcessor',
    'AIChatProcessor',
    'ProviderManager',
    'UniversalSettings',
    'extract_universal_settings',
    'get_provider_config',
    'get_settings_manager'
]
