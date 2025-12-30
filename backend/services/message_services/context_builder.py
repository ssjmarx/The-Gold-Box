#!/usr/bin/env python3
"""
Context Builder for The Gold Box
Builds initial world context for AI on first turn

Gathers foundational information about the game world:
- Session info (game system, GM, players)
- Party compendium (player-controlled characters)
- Active scene (basic scene data and tokens)
- Active encounter (combat state if active)

This is distinct from context_processor.py which handles detailed board state.
Context builder provides the "World State Overview" for initial AI context.

License: CC-BY-NC-SA 4.0
"""

import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class ContextBuilder:
    """
    Builds initial world context for AI
    
    Provides comprehensive world overview on first AI turn:
    - Session information (game system, participants)
    - Party compendium (player characters)
    - Active scene (scene data, token positions)
    - Active encounter (combat state or null)
    
    This context is only provided on the first AI turn per client.
    Subsequent turns use delta tracking instead.
    """
    
    def __init__(self):
        """Initialize context builder"""
        logger.info("ContextBuilder initialized")
    
    def build_initial_context(self, client_id: str) -> Dict[str, Any]:
        """
        Build initial world context for a client
        
        Args:
            client_id: WebSocket client identifier
            
        Returns:
            Complete initial context object per ROADMAP.md specification
            
            Structure:
            {
                "session_info": {
                    "game_system": "dnd5e",
                    "gm_name": "The Dungeon Master",
                    "players": ["Alice", "Bob", "Charlie"]
                },
                "party_compendium": [
                    {"id": "actorA", "name": "Valerius", "player": "Alice"}
                ],
                "active_scene": {
                    "id": "scene123",
                    "name": "The Sunless Citadel",
                    "dimensions": {"width": 4000, "height": 3000, "grid": 50},
                    "tokens": [...],
                    "notes": [...],
                    "light_sources": [...]
                },
                "compendium_index": [
                    {"pack_name": "dnd5e.monsters", "type": "Actor"},
                    {"pack_name": "dnd5e.items", "type": "Item"}
                ],
                "active_encounter": null | {...}
            }
        """
        try:
            logger.info(f"Building initial context for client {client_id}")
            
            # Get message collector to access frontend data
            from .websocket_message_collector import get_websocket_message_collector
            collector = get_websocket_message_collector()
            
            # Try to get world state from frontend
            world_state = collector.get_world_state(client_id)
            
            if world_state:
                logger.info(f"Using world state from frontend for client {client_id}")
                # Build context components from world state
                session_info = world_state.get("session_info", {})
                party_compendium = world_state.get("party_compendium", [])
                active_scene = self._build_active_scene_from_world_state(world_state)
                compendium_index = world_state.get("compendium_index", [])
                active_encounter = self._build_active_encounter(client_id, collector)
            else:
                logger.warning(f"No world state available for client {client_id}, using placeholders")
                # Fallback to placeholders
                session_info = self._build_session_info(client_id, collector)
                party_compendium = self._build_party_compendium(client_id, collector)
                active_scene = self._build_active_scene(client_id, collector)
                compendium_index = []
                active_encounter = self._build_active_encounter(client_id, collector)
            
            # Assemble complete context
            context = {
                "session_info": session_info,
                "party_compendium": party_compendium,
                "active_scene": active_scene,
                "compendium_index": compendium_index,
                "active_encounter": active_encounter
            }
            
            logger.info(f"Initial context built for client {client_id}: "
                       f"{len(party_compendium)} party members, "
                       f"scene '{active_scene.get('name', 'unknown')}', "
                       f"{len(compendium_index)} compendium packs, "
                       f"combat active: {active_encounter is not None}")
            
            return context
            
        except Exception as e:
            logger.error(f"Error building initial context for client {client_id}: {e}")
            # Return minimal context on error
            return {
                "session_info": {"game_system": "unknown", "gm_name": "Unknown", "players": []},
                "party_compendium": [],
                "active_scene": {"id": "unknown", "name": "Unknown Scene", "dimensions": {}, "tokens": [], "notes": [], "light_sources": []},
                "compendium_index": [],
                "active_encounter": None,
                "error": str(e)
            }
    
    def _build_session_info(self, client_id: str, collector) -> Dict[str, Any]:
        """
        Build session info component
        
        Args:
            client_id: Client identifier
            collector: WebSocket message collector
            
        Returns:
            Session info dictionary
        """
        try:
            # Get client stats from collector
            stats = collector.get_client_stats(client_id)
            
            # For now, use placeholder data
            # TODO: Enhance frontend to send actual game system info
            return {
                "game_system": "unknown",  # Will be filled by frontend in future
                "gm_name": "Game Master",  # Will be filled by frontend in future
                "players": []  # Will be filled by frontend in future
            }
            
        except Exception as e:
            logger.warning(f"Error building session info: {e}")
            return {
                "game_system": "unknown",
                "gm_name": "Unknown",
                "players": []
            }
    
    def _build_party_compendium(self, client_id: str, collector) -> list:
        """
        Build party compendium (player-controlled characters)
        
        Args:
            client_id: Client identifier
            collector: WebSocket message collector
            
        Returns:
            List of party member dictionaries
        """
        try:
            # Get client messages to extract party info
            messages = collector.client_messages.get(client_id, [])
            
            # For now, return empty list
            # TODO: Extract party members from frontend scene data
            # Frontend should send token list with is_player flag
            party_members = []
            
            return party_members
            
        except Exception as e:
            logger.warning(f"Error building party compendium: {e}")
            return []
    
    def _build_active_scene_from_world_state(self, world_state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Build active scene data from world state
        
        Args:
            world_state: Full world state from frontend
            
        Returns:
            Scene data dictionary with notes and light_sources
        """
        try:
            active_scene = world_state.get("active_scene", {})
            
            return {
                "id": active_scene.get('id', 'unknown'),
                "name": active_scene.get('name', 'Unknown Scene'),
                "dimensions": active_scene.get('dimensions', {"width": 0, "height": 0, "grid": 50}),
                "tokens": active_scene.get('tokens', []),
                "notes": active_scene.get('notes', []),
                "light_sources": active_scene.get('light_sources', [])
            }
            
        except Exception as e:
            logger.warning(f"Error building active scene from world state: {e}")
            return {
                "id": "unknown",
                "name": "Unknown Scene",
                "dimensions": {"width": 0, "height": 0, "grid": 50},
                "tokens": [],
                "notes": [],
                "light_sources": []
            }
    
    def _build_active_scene(self, client_id: str, collector) -> Dict[str, Any]:
        """
        Build active scene data (fallback when no world state available)
        
        Args:
            client_id: Client identifier
            collector: WebSocket message collector
            
        Returns:
            Scene data dictionary
        """
        try:
            # Get cached combat state which contains scene info
            combat_state = collector.get_cached_combat_state(client_id)
            
            if combat_state and 'scene' in combat_state:
                scene = combat_state['scene']
                return {
                    "id": scene.get('id', 'unknown'),
                    "name": scene.get('name', 'Unknown Scene'),
                    "dimensions": {
                        "width": scene.get('width', 0),
                        "height": scene.get('height', 0),
                        "grid": scene.get('grid', 50)
                    },
                    "tokens": scene.get('tokens', []),
                    "notes": [],  # Not available from combat state
                    "light_sources": []  # Not available from combat state
                }
            
            # Return minimal scene data if no combat state
            return {
                "id": "unknown",
                "name": "Unknown Scene",
                "dimensions": {"width": 0, "height": 0, "grid": 50},
                "tokens": [],
                "notes": [],
                "light_sources": []
            }
            
        except Exception as e:
            logger.warning(f"Error building active scene: {e}")
            return {
                "id": "unknown",
                "name": "Unknown Scene",
                "dimensions": {"width": 0, "height": 0, "grid": 50},
                "tokens": [],
                "notes": [],
                "light_sources": []
            }
    
    def _build_active_encounter(self, client_id: str, collector) -> Optional[Dict[str, Any]]:
        """
        Build active encounter data
        
        Args:
            client_id: Client identifier
            collector: WebSocket message collector
            
        Returns:
            Encounter data dictionary or null if no active encounter
        """
        try:
            # Get cached combat state
            combat_state = collector.get_cached_combat_state(client_id)
            
            if combat_state and combat_state.get('in_combat', False):
                # Return full combat state if active
                return combat_state
            else:
                # No active encounter
                return None
            
        except Exception as e:
            logger.warning(f"Error building active encounter: {e}")
            return None


# Global instance
_context_builder = None


def get_context_builder() -> ContextBuilder:
    """
    Get the context builder instance
    
    Returns:
        ContextBuilder instance
    """
    global _context_builder
    if _context_builder is None:
        _context_builder = ContextBuilder()
    return _context_builder


def reset_context_builder() -> ContextBuilder:
    """
    Reset the context builder (for testing)
    
    Returns:
        New ContextBuilder instance
    """
    global _context_builder
    _context_builder = ContextBuilder()
    return _context_builder
