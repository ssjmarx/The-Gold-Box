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
                "description": "Retrieve recent chat messages from Foundry chat for context. Call at the start of your turn to get new messages. Efficient: only call once per turn, not before each tool use.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "count": {
                            "type": "integer",
                            "description": "Number of recent messages to retrieve",
                            "minimum":1,
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
                "description": "Send one or more chat messages or chat cards to Foundry as your response. Multiple messages can be batched in a single call (e.g., post a scene description, and an NPC speaking, in seperate messages at same time). Chat Cards are created using HTML formatting. Use messages array to batch multiple outputs efficiently.",
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
                                        "description": "Flavor text for message"
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
                "description": "Roll one or more Foundry-formatted dice formulas. Multiple rolls can be batched in a single call (e.g., roll attack and damage together, or roll multiple saving throws simultaneously). Each roll can include optional flavor text. The rolls are executed in Foundry and results are returned.",
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
                                        "description": "Flavor text for roll (optional)"
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
                "description": "Gets combat state. If encounter_id is provided, gets that specific encounter. If not provided, returns all encounters with is_active flags indicating which is active combat. Returns standard 'no active encounter' response if out of combat.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "encounter_id": {
                            "type": "string",
                            "description": "ID of specific encounter to retrieve (optional - if not provided, returns all encounters)"
                        }
                    }
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "create_encounter",
                "description": "Start a new combat encounter with specified actors. Creates combat but does not automatically activate it. Use activate_combat tool after creating to make it active combat. Use roll_initiative parameter to control automatic initiative rolling (false for systems that handle initiative manually, e.g., card-based or dice-pool games).",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "actor_ids": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Array of actor IDs to add to encounter"
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
                "name": "activate_combat",
                "description": "Activate a specific combat encounter to make it active combat. Use this after creating a new encounter to ensure it becomes the active combat that responds to turn advancement and other operations. Only one encounter can be active at a time.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "encounter_id": {
                            "type": "string",
                            "description": "ID of encounter to activate"
                        }
                    },
                    "required": ["encounter_id"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "delete_encounter",
                "description": "End specified combat encounter",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "encounter_id": {
                            "type": "string",
                            "description": "ID of encounter to delete"
                        }
                    },
                    "required": ["encounter_id"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "advance_combat_turn",
                "description": "Advance combat tracker to next turn for specified encounter. Use this to move through turn order for multiple combatants efficiently. Multiple calls can be made in a single response (e.g., advance turn, move and attack, advance turn, move and attack, for NPCs with adjacent turns).",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "encounter_id": {
                            "type": "string",
                            "description": "ID of encounter to advance"
                        }
                    },
                    "required": ["encounter_id"]
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
        },
        {
            "type": "function",
            "function": {
                "name": "modify_token_attribute",
                "description": "Modify a token's attribute using Foundry's native API. Use field names from get_actor_details (e.g., 'attributes.hp.value', 'attributes.ac.value'). Multiple tokens can be updated in a single response (e.g., apply multi-target spell damage to multiple NPCs together). Set is_delta=true for relative changes (damage/healing), is_delta=false for absolute values. Set is_bar=true to update token bar display.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "token_id": {
                            "type": "string",
                            "description": "The token ID to update"
                        },
                        "attribute_path": {
                            "type": "string",
                            "description": "Attribute path to modify (e.g., 'attributes.hp.value')"
                        },
                        "value": {
                            "type": "number",
                            "description": "Value to set (if is_delta=false) or add/subtract (if is_delta=true)"
                        },
                        "is_delta": {
                            "type": "boolean",
                            "description": "Whether value is a relative change (true) or absolute (false). Default: true for damage/healing"
                        },
                        "is_bar": {
                            "type": "boolean",
                            "description": "Whether to update token bar display. Default: true"
                        }
                    },
                    "required": ["token_id", "attribute_path", "value"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "get_nearby_objects",
                "description": "Get scene objects within a radius of a location or token. Returns hierarchical object structure including tokens, structures (walls/doors), locations of interest (journal notes), lighting, and distance matrix for nearest tokens. Supports line-of-sight filtering to respect vision-blocking walls. Distances formatted in user's preferred units (feet, meters, squares).",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "origin": {
                            "oneOf": [
                                {"type": "object"},
                                {"type": "string"}
                            ],
                            "description": "Search origin: either token_id string or coordinates object {x, y}"
                        },
                        "radius": {
                            "type": "number",
                            "description": "Search radius in grid squares (converted from user's distance unit setting)"
                        },
                        "search_mode": {
                            "type": "string",
                            "enum": ["absolute", "line_of_sight"],
                            "description": "Search mode: 'absolute' (all objects within radius) or 'line_of_sight' (only visible objects, default)"
                        }
                    },
                    "required": ["origin", "radius"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "get_journal_context",
                "description": "Searches for a phrase within a journal entry and returns the surrounding context. Returns matching text with specified number of lines before and after for context. Similar to grep -C (context) but for journal content. Use after seeing a map note to get detailed information about that location.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "entry_name": {
                            "type": "string",
                            "description": "Name of journal entry to search"
                        },
                        "search_phrase": {
                            "type": "string",
                            "description": "Phrase to search for within the journal entry"
                        },
                        "context_lines": {
                            "type": "integer",
                            "description": "Number of lines of context before and after match (default: 3)",
                            "default": 3,
                            "minimum": 0,
                            "maximum": 20
                        }
                    },
                    "required": ["entry_name", "search_phrase"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "search_compendium",
                "description": "Searches within a specific compendium pack for entries matching a query. Returns matching entries with their names, IDs, and key information. Use to find items, spells, monsters, or other game content in compendiums.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "pack_name": {
                            "type": "string",
                            "description": "Name of compendium pack to search (e.g., 'dnd5e.items', 'dnd5e.spells', 'world.lore-journals')"
                        },
                        "query": {
                            "type": "string",
                            "description": "Search query text (case-insensitive, partial matches allowed)"
                        }
                    },
                    "required": ["pack_name", "query"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "get_party_members",
                "description": "Returns a list of all player-controlled characters (PCs) in the session. Includes character names, player names, and basic information for party composition awareness.",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            }
        }
    ]
