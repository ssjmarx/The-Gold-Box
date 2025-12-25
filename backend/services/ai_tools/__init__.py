#!/usr/bin/env python3
"""
AI Tools for The Gold Box
Provides tool definitions and execution for AI function calling
"""

from .ai_tool_definitions import get_tool_definitions
from .ai_tool_executor import get_ai_tool_executor

__all__ = [
    'get_tool_definitions',
    'get_ai_tool_executor'
]
