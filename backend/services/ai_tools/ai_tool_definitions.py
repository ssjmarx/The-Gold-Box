#!/usr/bin/env python3
"""
AI Tool Definitions for The Gold Box
Define tool schemas using OpenAI function calling format
"""

def get_tool_definitions() -> list:
    """
    Get tool definitions in OpenAI function calling format
    
    Returns:
        List of tool definition dictionaries
    """
    return [
        {
            "type": "function",
            "function": {
                "name": "get_message_history",
                "description": "Retrieve recent chat messages from Foundry chat for context. Use once at the start of a turn to get new messages.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "count": {
                            "type": "integer",
                            "description": "Number of recent messages to retrieve",
                            "minimum": 1,
                            "maximum": 50,
                            "default": 15
                        }
                    },
                    "required": ["count"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "post_message",
                "description": "Send one or more chat messages or chat cards to Foundry as your response. Messages can be chat text, or structured chat cards with Foundry-specific formatting. This function accepts markdown styling.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "messages": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "content": {
                                        "type": "string",
                                        "description": "Message content (required)"
                                    },
                                    "type": {
                                        "type": "string",
                                        "description": "Message type (chat-message, dice-roll, chat-card, etc.)",
                                        "default": "chat-message"
                                    },
                                    "flavor": {
                                        "type": "string",
                                        "description": "Flavor text for the message"
                                    },
                                    "speaker": {
                                        "type": "object",
                                        "properties": {
                                            "name": {"type": "string"},
                                            "alias": {"type": "string"},
                                            "scene": {"type": "string"},
                                            "actor": {"type": "string"},
                                            "token": {"type": "string"}
                                        }
                                    },
                                    "flags": {
                                        "type": "object",
                                        "description": "Foundry flags object"
                                    },
                                    "whisper": {
                                        "type": "array",
                                        "items": {"type": "string"},
                                        "description": "Array of recipient IDs for whispers"
                                    },
                                    "compact_format": {
                                        "type": "object",
                                        "description": "Alternative: compact JSON format message"
                                    }
                                },
                                "required": ["content"]
                            }
                        }
                    },
                    "required": ["messages"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "roll_dice",
                "description": "Roll one or more Foundry-formatted dice formulas. Each roll can include optional flavor text. The rolls are executed in Foundry and the results are returned.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "rolls": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "formula": {
                                        "type": "string",
                                        "description": "Foundry dice formula (e.g., '1d20+5', '2d6', '4d6kh3')"
                                    },
                                    "flavor": {
                                        "type": "string",
                                        "description": "Flavor text for the roll (optional)"
                                    }
                                },
                                "required": ["formula"]
                            },
                            "description": "Array of dice roll requests"
                        }
                    },
                    "required": ["rolls"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "get_encounter",
                "description": "Gets the current combat state. Returns standard 'no active encounter' response if out of combat.",
                "parameters": {
                    "type": "object",
                    "properties": {}
                }
            }
        }
    ]
