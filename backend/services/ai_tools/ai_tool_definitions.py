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
        },
        {
            "type": "function",
            "function": {
                "name": "create_encounter",
                "description": "Start a new combat encounter with specified actors. Use roll_initiative parameter to control automatic initiative rolling (false for systems that handle initiative manually, e.g., card-based or dice-pool games). Creates combat and advances to turn 1 if successful.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "actor_ids": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Array of actor IDs to add to the encounter"
                        },
                        "roll_initiative": {
                            "type": "boolean",
                            "description": "Whether to roll initiative for all combatants (default: true)",
                            "default": True
                        }
                    },
                    "required": ["actor_ids"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "delete_encounter",
                "description": "End the current combat encounter",
                "parameters": {
                    "type": "object",
                    "properties": {}
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "advance_combat_turn",
                "description": "Advance the combat tracker to the next turn. Use this to move through turn order for multiple combatants efficiently. Multiple calls can be made in a single response (e.g., advance turn, move and attack, advance turn, move and attack, for NPCs with adjacent turns).",
                "parameters": {
                    "type": "object",
                    "properties": {}
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "get_actor_details",
                "description": "Retrieve a detailed stat block for a token-specific actor instance. Returns complete actor data structure including all field names (e.g., 'attributes.hp.value', 'attributes.ac.value') which can be used with modify_token_attribute. Optional search_phrase performs grep-like search (case-insensitive, exact substring match) returning matching field paths, values, and context (parent/child/sibling fields). Similar to grep: searches all fields, returns matches with surrounding context. Leave empty to return full actor sheet.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "token_id": {
                            "type": "string",
                            "description": "The token-specific actor UUID (e.g., 'Scene.XXX.Token.YYY.Actor.ZZZ')"
                        },
                        "search_phrase": {
                            "type": "string",
                            "description": "Optional search phrase (case-insensitive, exact substring match). Returns matching field paths, values, and context. Similar to grep: searches all fields, returns matches with surrounding context (parent/child/sibling fields). Leave empty to return full actor sheet."
                        }
                    },
                    "required": ["token_id"]
                }
            }
        }
    ]
