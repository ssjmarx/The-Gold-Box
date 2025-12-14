"""
The Gold Box - Startup Module

This module contains all startup-related functionality for the server,
separated from the main server.py file for better maintainability.

License: CC-BY-NC-SA 4.0 (compatible with dependencies)
"""

from .startup import ServerStartup, run_server_startup

__all__ = ['ServerStartup', 'run_server_startup']
