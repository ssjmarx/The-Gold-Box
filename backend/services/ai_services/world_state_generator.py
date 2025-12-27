#!/usr/bin/env python3
"""
World State Generator for The Gold Box
Generates World State Overview for initial AI prompts
"""

import logging
import json
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class WorldStateGenerator:
    """
    Generates World State Overview for new AI sessions
    
    Provides foundational understanding:
    - Session info (game system, GM, players)
    - Active scene (name, dimensions, tokens)
    - Party compendium (list of party members)
    - Active encounter (current combat state)
    """
    
    def __init__(self):
        """Initialize world state generator"""
        logger.info("WorldStateGenerator initialized")
    
    def generate_world_state_overview(
        self,
        client_id: str,
        universal_settings: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Generate World State Overview for initial AI prompt
        
        Args:
            client_id: The Foundry client ID
            universal_settings: Settings from frontend
            
        Returns:
            Dictionary with World State Overview structure
        """
        try:
            world_state = {}
            
            # 1. Session Info
            world_state['session_info'] = self._get_session_info(universal_settings)
            
            # 2. Active Scene
            world_state['active_scene'] = self._get_active_scene(client_id, universal_settings)
            
            # 3. Party Compendium
            world_state['party_compendium'] = self._get_party_compendium(client_id, universal_settings)
            
            # 4. Active Encounter
            world_state['active_encounter'] = self._get_active_encounter()
            
            # 5. Compendium Index (basic list)
            world_state['compendium_index'] = self._get_compendium_index()
            
            logger.info(f"World State Overview generated for client {client_id}")
            return world_state
            
        except Exception as e:
            logger.error(f"Error generating World State Overview: {e}")
            # Return minimal structure even on error
            return {
                'session_info': {'game_system': 'unknown'},
                'active_scene': None,
                'party_compendium': [],
                'active_encounter': None,
                'compendium_index': []
            }
    
    def _get_session_info(self, universal_settings: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get session information from universal settings
        
        Returns:
            Dictionary with game_system, gm_name, players
        """
        try:
            return {
                'game_system': universal_settings.get('game_system', 'dnd5e'),
                'gm_name': universal_settings.get('gm_name', 'Game Master'),
                'players': universal_settings.get('players', [])
            }
        except Exception as e:
            logger.warning(f"Error getting session info: {e}")
            return {'game_system': 'unknown', 'gm_name': 'Unknown', 'players': []}
    
    def _get_active_scene(
        self,
        client_id: str,
        universal_settings: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Get active scene from WebSocket collector
        
        Frontend must send scene data via WebSocket messages
        
        Returns:
            Dictionary with scene info or None
        """
        try:
            # Try to get scene data from message collector
            from ..system_services.service_factory import get_message_collector
            message_collector = get_message_collector()
            
            # Look for recent scene info messages
            messages = message_collector.get_combined_messages(client_id, limit=50)
            
            for msg in reversed(messages):
                if msg.get('type') == 'scene_info':
                    return msg.get('scene_info')
            
            # Fallback: check universal settings
            if 'scene_info' in universal_settings:
                return universal_settings['scene_info']
            
            return None
            
        except Exception as e:
            logger.warning(f"Error getting active scene: {e}")
            return None
    
    def _get_party_compendium(
        self,
        client_id: str,
        universal_settings: Dict[str, Any]
    ) -> list:
        """
        Get party members from frontend
        
        Frontend must send party data via WebSocket messages
        
        Returns:
            Array of party member dictionaries
        """
        try:
            # Try to get party data from message collector
            from ..system_services.service_factory import get_message_collector
            message_collector = get_message_collector()
            
            # Look for recent party info messages
            messages = message_collector.get_combined_messages(client_id, limit=50)
            
            for msg in reversed(messages):
                if msg.get('type') == 'party_info':
                    return msg.get('party_info', [])
            
            # Fallback: check universal settings
            if 'party_info' in universal_settings:
                return universal_settings['party_info']
            
            return []
            
        except Exception as e:
            logger.warning(f"Error getting party compendium: {e}")
            return []
    
    def _get_active_encounter(self) -> Optional[Dict[str, Any]]:
        """
        Get active encounter from CombatEncounterService
        
        Returns:
            Dictionary with encounter data or None if no active encounter
        """
        try:
            from ..system_services.service_factory import get_combat_encounter_service
            combat_service = get_combat_encounter_service()
            combat_context = combat_service.get_combat_context()
            
            if combat_context.get('in_combat', False):
                # Return full encounter data for WSO
                return combat_context
            else:
                return None
                
        except Exception as e:
            logger.warning(f"Error getting active encounter: {e}")
            return None
    
    def _get_compendium_index(self) -> list:
        """
        Get basic compendium index
        
        For now, return a basic structure.
        Future: Query Foundry API for available compendium packs.
        
        Returns:
            Array of compendium pack objects
        """
        try:
            # Basic structure for now
            # Frontend can enhance this by sending compendium data
            return [
                {"pack_name": "dnd5e.monsters", "type": "Actor"},
                {"pack_name": "dnd5e.items", "type": "Item"},
                {"pack_name": "dnd5e.spells", "type": "Item"},
                {"pack_name": "world.lore-journals", "type": "JournalEntry"},
                {"pack_name": "world.random-encounters", "type": "RollableTable"}
            ]
        except Exception as e:
            logger.warning(f"Error getting compendium index: {e}")
            return []


# Global instance
_world_state_generator = None

def get_world_state_generator() -> WorldStateGenerator:
    """Get the global world state generator instance"""
    global _world_state_generator
    if _world_state_generator is None:
        _world_state_generator = WorldStateGenerator()
    return _world_state_generator
