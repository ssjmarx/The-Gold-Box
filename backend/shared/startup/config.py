"""
The Gold Box - Startup Configuration Module

Handles all configuration loading and setup during server startup.

License: CC-BY-NC-SA 4.0 (compatible with dependencies)
"""

import os
import logging
from typing import Dict, Any, List
from pathlib import Path
from dotenv import load_dotenv

def get_absolute_path(relative_path: str) -> Path:
    """
    Convert a relative path to an absolute path based on backend directory.
    This ensures consistent file operations regardless of where script is called from.
    """
    BACKEND_DIR = Path(__file__).parent.parent.absolute()
    return (BACKEND_DIR / relative_path).resolve()

def load_environment_variables() -> Dict[str, Any]:
    """
    Load and return all environment variables needed for server configuration.
    
    Returns:
        Dict containing all configuration values
    """
    # Load environment variables from .env file
    load_dotenv()
    
    # Configuration from environment variables
    config = {
        'OPENAI_API_KEY': os.environ.get('GOLD_BOX_OPENAI_COMPATIBLE_API_KEY', ''),
        'NOVELAI_API_KEY': os.environ.get('GOLD_BOX_NOVELAI_API_API_KEY', ''),
        'GOLD_BOX_PORT': int(os.environ.get('GOLD_BOX_PORT', 5000)),
        'FLASK_DEBUG': os.environ.get('FLASK_DEBUG', 'False').lower() == 'true',
        'FLASK_ENV': os.environ.get('FLASK_ENV', 'production'),
        'LOG_LEVEL': os.environ.get('LOG_LEVEL', 'INFO'),
        'LOG_FILE': str(get_absolute_path('server_files/goldbox.log')),
        'RATE_LIMIT_MAX_REQUESTS': int(os.environ.get('RATE_LIMIT_MAX_REQUESTS', 5)),
        'RATE_LIMIT_WINDOW_SECONDS': int(os.environ.get('RATE_LIMIT_WINDOW_SECONDS', 60)),
        'SESSION_TIMEOUT_MINUTES': int(os.environ.get('SESSION_TIMEOUT_MINUTES', 60)),
        'SESSION_WARNING_MINUTES': int(os.environ.get('SESSION_WARNING_MINUTES', 10)),
        'GOLD_BOX_KEYCHANGE': os.environ.get('GOLD_BOX_KEYCHANGE', '').lower() in ['true', '1', 'yes']
    }
    
    return config

def setup_cors_origins(flask_env: str) -> List[str]:
    """
    Get CORS origins based on environment with security-first approach.
    In production, this should be explicitly configured via environment variable.
    
    Args:
        flask_env: Current Flask environment ('development' or 'production')
        
    Returns:
        List of allowed CORS origins
    """
    cors_origins_env = os.environ.get('CORS_ORIGINS', '').strip()
    
    if cors_origins_env:
        # Split and clean environment variable origins
        origins = [origin.strip() for origin in cors_origins_env.split(',') if origin.strip()]
        return origins
    
    # Development defaults - only localhost Foundry VTT ports
    if flask_env == 'development':
        default_origins = [
            'http://localhost:30000', 'http://127.0.0.1:30000',  # Default Foundry VTT
            'http://localhost:30001', 'http://127.0.0.1:30001',  # Common alternative
            'http://localhost:30002', 'http://127.0.0.1:30002',  # Another alternative
        ]
        return default_origins
    
    # Production - provide localhost defaults for direct server testing
    default_origins = [
        'http://localhost:30000', 'http://127.0.0.1:30000',  # Default Foundry VTT
        'http://localhost:30001', 'http://127.0.0.1:30001',  # Common alternative
        'http://localhost:30002', 'http://127.0.0.1:30002',  # Another alternative
    ]
    return default_origins

def configure_logging(log_level: str, log_file: str) -> bool:
    """
    Configure logging for the application.
    
    Args:
        log_level: Logging level (INFO, DEBUG, etc.)
        log_file: Path to log file
        
    Returns:
        True if successful, False otherwise
    """
    try:
        log_level_obj = getattr(logging, log_level.upper(), logging.WARNING)
        logging.basicConfig(
            level=log_level_obj,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler()
            ]
        )
        return True
    except Exception as e:
        print(f"Failed to configure logging: {e}")
        return False

def get_server_config() -> Dict[str, Any]:
    """
    Get complete server configuration by combining all configuration sources.
    
    Returns:
        Complete server configuration dictionary
    """
    # Load environment variables
    env_config = load_environment_variables()
    
    # Setup CORS origins
    env_config['CORS_ORIGINS'] = setup_cors_origins(env_config['FLASK_ENV'])
    
    # Configure logging
    if not configure_logging(env_config['LOG_LEVEL'], env_config['LOG_FILE']):
        print("Warning: Failed to configure logging")
    
    # Add derived configuration
    env_config['is_development'] = env_config['FLASK_ENV'] == 'development'
    env_config['debug_mode'] = env_config['FLASK_DEBUG']
    
    return env_config
