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
                "description": "Retrieves the most recent chat messages from Foundry chat for context. Use once at the start of a turn to get new messages.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "limit": {
                            "type": "integer",
                            "description": "Number of recent messages to retrieve",
                            "minimum": 1,
                            "maximum": 50,
                            "default": 15
                        }
                    },
                    "required": ["limit"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "post_message",
                "description": "Posts a new message to the chat. Messages can be chat text, or structured chat cards with Foundry-specific formatting. This function accepts markdown styling.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "content": {
                            "type": "string",
                            "description": "Message content"
                        },
                        "speaker_name": {
                            "type": "string",
                            "description": "Speaker name (optional)"
                        },
                        "flavor": {
                            "type": "string",
                            "description": "Flavor text (optional)"
                        },
                        "type": {
                            "type": "string",
                            "description": "Message type: ic, ooc, or emote",
                            "enum": ["ic", "ooc", "emote"]
                        }
                    },
                    "required": ["content"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "roll_dice",
                "description": "Roll one or more Foundry-formatted dice formulas",
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
                                        "description": "Foundry dice formula (e.g., '1d20+5', '2d6+2')"
                                    },
                                    "flavor": {
                                        "type": "string",
                                        "description": "Flavor text for the roll (optional)"
                                    }
                                },
                                "required": ["formula"]
                            }
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
                "description": "Gets the current combat state. Returns a standard 'no active encounter' response if out of combat.",
                "parameters": {
                    "type": "object",
                    "properties": {}
                }
            }
        }
    ]
