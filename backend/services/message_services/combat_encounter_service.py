#!/usr/bin/env python3
"""
Combat Encounter Service for The Gold Box
Tracks combat state, turn order, and current turn for tactical AI context
Supports multiple concurrent encounters with unique IDs

License: CC-BY-NC-SA 4.0
"""

import logging
import time
from typing import Dict, Any, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class CombatEncounterService:
    """
    Service for tracking combat encounter state and turn order
    Provides combat context for AI prompts and tactical LLM selection
    Supports multiple concurrent encounters with unique IDs
    """
    
    def __init__(self):
        """Initialize combat encounter service"""
        self.encounters: Dict[str, Dict[str, Any]] = {}  # Dictionary of encounters keyed by combat_id
        self.combat_state: Dict[str, Any] = {
            "in_combat": False,
            "combat_id": None,
            "round": 0,
            "turn": 0,
            "combatants": [],
            "last_updated": None
        }
        
        logger.info("CombatEncounterService initialized")
    
    def update_combat_state(self, combat_data: Dict[str, Any], encounter_id: Optional[str] = None) -> bool:
        """
        Update combat state with new data from frontend
        
        Args:
            combat_data: Combat state data from Foundry
            encounter_id: Optional encounter ID to update (if not provided, uses combat_id from data)
            
        Returns:
            True if updated successfully
        """
        try:
            # Determine which encounter to update
            target_encounter_id = encounter_id if encounter_id else combat_data.get("combat_id")
            
            # Validate combat data structure
            if not self._validate_combat_data(combat_data):
                logger.warning(f"Invalid combat data received: {combat_data}")
                return False
            
            # Get or create encounter in the encounters dictionary
            if target_encounter_id:
                # Check if encounter exists
                if target_encounter_id not in self.encounters:
                    # NEW ENCOUNTER: Create it automatically instead of rejecting
                    logger.info(f"Creating new encounter via update_combat_state: {target_encounter_id}")
                    self.encounters[target_encounter_id] = combat_data.copy()
                    logger.info(f"New encounter created: {target_encounter_id}")
                else:
                    # EXISTING ENCOUNTER: Update it
                    encounter = self.encounters[target_encounter_id]
                    encounter.update(combat_data)
                    self.encounters[target_encounter_id] = encounter
                    logger.debug(f"Updated existing encounter: {target_encounter_id}")
            else:
                # Create new encounter from combat data directly
                new_encounter_id = combat_data.get("combat_id")
                if not new_encounter_id:
                    logger.warning(f"Cannot create encounter without combat_id in data")
                    return False
                
                self.encounters[new_encounter_id] = combat_data.copy()
                logger.info(f"Created new encounter: {new_encounter_id}")
            
            # Update legacy combat_state for backward compatibility
            self.combat_state = self.encounters.get(target_encounter_id, {
                "in_combat": False,
                "combat_id": None,
                "round": 0,
                "turn": 0,
                "combatants": [],
                "last_updated": None
            })
            
            logger.info(f"Combat state updated: in_combat={self.combat_state['in_combat']}, "
                        f"combat_id={target_encounter_id}, "
                        f"combatants={len(self.combat_state.get('combatants', []))}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating combat state: {e}")
            return False
    
    def get_combat_context(self, encounter_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get formatted combat context for AI prompts
        
        Args:
            encounter_id: Optional encounter ID to get context for (if None, returns all encounters)
            
        Returns:
            Dictionary with combat context information
        """
        try:
            if encounter_id:
                # Get specific encounter context
                if encounter_id not in self.encounters:
                    return {
                        "in_combat": False,
                        "combat_context": f"Encounter {encounter_id} not found",
                        "encounters": []
                    }
                
                encounter = self.encounters[encounter_id]
                if not encounter.get("in_combat", False):
                    return {
                        "in_combat": False,
                        "combat_context": "Not in combat",
                        "encounters": []
                    }
                
                combat_context = self._format_combat_for_ai(encounter)
                return {
                    "in_combat": True,
                    "combat_context": combat_context,
                    "raw_state": encounter.copy(),
                    "encounters": [encounter.copy()]
                }
            else:
                # Get all encounters context
                active_encounters = [enc for enc in self.encounters.values() if enc.get("in_combat", False)]
                
                if not active_encounters:
                    return {
                        "in_combat": False,
                        "combat_context": "Not in combat",
                        "encounters": []
                    }
                
                # Format all encounters for AI
                encounter_contexts = []
                for encounter in active_encounters:
                    context = self._format_combat_for_ai(encounter)
                    encounter_contexts.append({
                        "combat_id": encounter.get("combat_id"),
                        "context": context,
                        "raw_state": encounter.copy()
                    })
                
                # Update legacy combat_state with first encounter for backward compatibility
                if active_encounters:
                    self.combat_state = active_encounters[0].copy()
                
                # Build combined context string
                combined_context = f"Active Combat Encounters ({len(active_encounters)}):\n\n"
                for i, ec in enumerate(encounter_contexts, 1):
                    combined_context += f"--- Encounter {i} (ID: {ec['combat_id']}) ---\n"
                    combined_context += ec["context"] + "\n\n"
                
                return {
                    "in_combat": True,
                    "combat_context": combined_context,
                    "encounters": [ec["raw_state"] for ec in encounter_contexts],
                    "active_count": len(active_encounters)
                }
            
        except Exception as e:
            logger.error(f"Error getting combat context: {e}")
            return {
                "in_combat": False,
                "combat_context": "Error retrieving combat state",
                "encounters": []
            }
    
    def is_in_combat(self) -> bool:
        """
        Check if currently in combat
        
        Returns:
            True if in combat, False otherwise
        """
        return self.combat_state.get("in_combat", False)
    
    def get_current_turn(self) -> Optional[Dict[str, Any]]:
        """
        Get current combatant information
        
        Returns:
            Current combatant data or None if not in combat
        """
        try:
            if not self.is_in_combat():
                return None
            
            for combatant in self.combat_state.get("combatants", []):
                if combatant.get("is_current_turn", False):
                    return combatant
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting current turn: {e}")
            return None
    
    def get_turn_order(self) -> List[Dict[str, Any]]:
        """
        Get turn order with initiative values
        
        Returns:
            List of combatants sorted by initiative (highest first)
        """
        try:
            if not self.is_in_combat():
                return []
            
            combatants = self.combat_state.get("combatants", [])
            
            # Sort by initiative (highest first), then by name for ties
            sorted_combatants = sorted(
                combatants,
                key=lambda x: (-x.get("initiative", 0), x.get("name", ""))
            )
            
            return sorted_combatants
            
        except Exception as e:
            logger.error(f"Error getting turn order: {e}")
            return []
    
    def get_encounter_state(self, encounter_id: str) -> Optional[Dict[str, Any]]:
        """
        Get state for specific encounter by ID
        
        Args:
            encounter_id: ID of encounter to retrieve
            
        Returns:
            Encounter state dictionary or None if not found
        """
        return self.encounters.get(encounter_id)
    
    def get_combat_state_for_frontend(self) -> Dict[str, Any]:
        """
        Get combat state formatted for frontend consumption
        
        Returns:
            Combat state dictionary
        """
        return self.combat_state.copy()
    
    def clear_combat_state(self, encounter_id: Optional[str] = None) -> bool:
        """
        Clear combat state (when combat ends)
        
        Args:
            encounter_id: Optional encounter ID to clear (if None, clears all encounters)
            
        Returns:
            True if cleared successfully
        """
        try:
            if encounter_id:
                # Clear specific encounter
                if encounter_id in self.encounters:
                    del self.encounters[encounter_id]
                    logger.info(f"Encounter {encounter_id} cleared")
                    
                    # Update legacy combat_state if this was the active encounter
                    if self.combat_state.get("combat_id") == encounter_id:
                        # Set to first remaining encounter or empty state
                        remaining_encounters = list(self.encounters.values())
                        if remaining_encounters:
                            self.combat_state = remaining_encounters[0].copy()
                        else:
                            self.combat_state = {
                                "in_combat": False,
                                "combat_id": None,
                                "round": 0,
                                "turn": 0,
                                "combatants": [],
                                "last_updated": int(time.time() * 1000)
                            }
                else:
                    logger.warning(f"Cannot clear non-existent encounter: {encounter_id}")
                    return False
            else:
                # Clear all encounters
                self.encounters.clear()
                self.combat_state = {
                    "in_combat": False,
                    "combat_id": None,
                    "round": 0,
                    "turn": 0,
                    "combatants": [],
                    "last_updated": int(time.time() * 1000)
                }
                logger.info("All combat states cleared")
            
            return True
            
        except Exception as e:
            logger.error(f"Error clearing combat state: {e}")
            return False
    
    def delete_encounter(self, encounter_id: str) -> bool:
        """
        Delete specific encounter by ID
        
        Args:
            encounter_id: ID of encounter to delete
            
        Returns:
            True if deleted successfully, False if encounter not found
        """
        try:
            if encounter_id not in self.encounters:
                logger.warning(f"Cannot delete non-existent encounter: {encounter_id}")
                return False
            
            del self.encounters[encounter_id]
            logger.info(f"Encounter {encounter_id} deleted")
            
            # Update legacy combat_state if this was the active encounter
            if self.combat_state.get("combat_id") == encounter_id:
                # Set to first remaining encounter or empty state
                remaining_encounters = list(self.encounters.values())
                if remaining_encounters:
                    self.combat_state = remaining_encounters[0].copy()
                else:
                    self.combat_state = {
                        "in_combat": False,
                        "combat_id": None,
                        "round": 0,
                        "turn": 0,
                        "combatants": [],
                        "last_updated": int(time.time() * 1000)
                    }
            
            return True
            
        except Exception as e:
            logger.error(f"Error deleting encounter: {e}")
            return False
    
    def _validate_combat_data(self, combat_data: Dict[str, Any]) -> bool:
        """
        Validate combat data structure
        
        Args:
            combat_data: Combat data to validate
            
        Returns:
            True if valid, False otherwise
        """
        try:
            if not isinstance(combat_data, dict):
                return False
            
            # Check required fields
            if "in_combat" not in combat_data:
                return False
            
            # If in combat, validate combatants
            if combat_data.get("in_combat", False):
                combatants = combat_data.get("combatants", [])
                if not isinstance(combatants, list):
                    return False
                
                # Validate each combatant
                for combatant in combatants:
                    if not isinstance(combatant, dict):
                        return False
                    if "name" not in combatant:
                        return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error validating combat data: {e}")
            return False
    
    def _format_combat_for_ai(self, encounter_state: Optional[Dict[str, Any]] = None) -> str:
        """
        Format combat information for AI consumption
        
        Args:
            encounter_state: Optional encounter state to format (if None, uses self.combat_state)
            
        Returns:
            Formatted combat context string
        """
        try:
            state = encounter_state if encounter_state else self.combat_state
            
            context_parts = [
                f"Combat Status: Active",
                f"Current Round: {state.get('round', 0)}",
                f"Current Turn: {self._get_current_turn_name_for_state(state)}"
            ]
            
            # Add turn order
            turn_order = self._get_turn_order_for_state(state)
            if turn_order:
                context_parts.append("Turn Order:")
                for i, combatant in enumerate(turn_order, 1):
                    current_marker = " (CURRENT)" if combatant.get("is_current_turn", False) else ""
                    context_parts.append(f"  {i}. {combatant.get('name', 'Unknown')} - Initiative: {combatant.get('initiative', 0)}{current_marker}")
            
            return "\n".join(context_parts)
            
        except Exception as e:
            logger.error(f"Error formatting combat for AI: {e}")
            return "Error formatting combat context"
    
    def _get_current_turn_name_for_state(self, state: Dict[str, Any]) -> str:
        """
        Get name of current combatant from specific state
        
        Args:
            state: Combat state dictionary
            
        Returns:
            Name of current combatant or "Unknown"
        """
        for combatant in state.get("combatants", []):
            if combatant.get("is_current_turn", False):
                return combatant.get("name", "Unknown")
        return "Unknown"
    
    def _get_turn_order_for_state(self, state: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Get turn order from specific state
        
        Args:
            state: Combat state dictionary
            
        Returns:
            List of combatants sorted by initiative
        """
        try:
            combatants = state.get("combatants", [])
            
            # Sort by initiative (highest first), then by name for ties
            sorted_combatants = sorted(
                combatants,
                key=lambda x: (-x.get("initiative", 0), x.get("name", ""))
            )
            
            return sorted_combatants
            
        except Exception as e:
            logger.error(f"Error getting turn order for state: {e}")
            return []
    
    def _get_current_turn_name(self) -> str:
        """
        Get name of current combatant
        
        Returns:
            Name of current combatant or "Unknown"
        """
        current_turn = self.get_current_turn()
        if current_turn:
            return current_turn.get("name", "Unknown")
        return "Unknown"
    
    def is_current_turn_player(self) -> bool:
        """
        Determine if current turn belongs to a player character
        
        Returns:
            True if current turn is a player, False otherwise
        """
        current_turn = self.get_current_turn()
        if current_turn:
            return current_turn.get("is_player", False)
        return False
    
    def get_next_player_combatant(self) -> Optional[Dict[str, Any]]:
        """
        Find the next player character in turn order
        
        Returns:
            Next player combatant data or None
        """
        try:
            turn_order = self.get_turn_order()
            if not turn_order:
                return None
            
            # Find current turn index
            current_turn_index = -1
            for i, combatant in enumerate(turn_order):
                if combatant.get("is_current_turn", False):
                    current_turn_index = i
                    break
            
            if current_turn_index == -1:
                return None
            
            # Look for next player in turn order
            for i in range(current_turn_index + 1, len(turn_order)):
                combatant = turn_order[i]
                if combatant.get("is_player", False):
                    return combatant
            
            # Loop around to beginning
            for i in range(0, current_turn_index + 1):
                combatant = turn_order[i]
                if combatant.get("is_player", False):
                    return combatant
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting next player combatant: {e}")
            return None
    
    def get_npc_turn_sequence(self) -> List[str]:
        """
        Get sequence of NPCs who will take turns before next player
        
        Returns:
            List of NPC names in turn order
        """
        try:
            turn_order = self.get_turn_order()
            if not turn_order:
                return []
            
            # Find current turn position
            current_turn_index = -1
            for i, combatant in enumerate(turn_order):
                if combatant.get("is_current_turn", False):
                    current_turn_index = i
                    break
            
            if current_turn_index == -1:
                return []
            
            # Get all subsequent combatants until next player
            npc_sequence = []
            for i in range(current_turn_index + 1, len(turn_order)):
                combatant = turn_order[i]
                if not combatant.get("is_player", False):
                    npc_sequence.append(combatant.get("name", "Unknown"))
                else:
                    # Found next player, stop collecting NPCs
                    break
            
            # If we looped around, check from beginning
            if not npc_sequence:
                for i in range(0, len(turn_order)):
                    combatant = turn_order[i]
                    if combatant.get("is_current_turn", False):
                        # Back to current turn, no more NPCs
                        break
                    if not combatant.get("is_player", False):
                        npc_sequence.append(combatant.get("name", "Unknown"))
                    else:
                        # Found next player, stop collecting NPCs
                        break
            
            return npc_sequence
            
        except Exception as e:
            logger.error(f"Error getting NPC turn sequence: {e}")
            return []
    
    def get_service_stats(self) -> Dict[str, Any]:
        """
        Get service statistics
        
        Returns:
            Service statistics dictionary
        """
        return {
            "service": "CombatEncounterService",
            "in_combat": self.is_in_combat(),
            "combatant_count": len(self.combat_state.get("combatants", [])),
            "last_updated": self.combat_state.get("last_updated"),
            "timestamp": datetime.now().isoformat()
        }

# Global instance
combat_encounter_service = CombatEncounterService()

def get_combat_encounter_service() -> CombatEncounterService:
    """Get the combat encounter service instance"""
    return combat_encounter_service

def update_combat_state(combat_data: Dict[str, Any]) -> bool:
    """
    Update combat state from external caller
    
    Args:
        combat_data: Combat state data
        
    Returns:
        True if updated successfully
    """
    return combat_encounter_service.update_combat_state(combat_data)

def get_combat_context() -> Dict[str, Any]:
    """
    Get combat context for AI prompts
    
    Returns:
        Combat context dictionary
    """
    return combat_encounter_service.get_combat_context()

def is_in_combat() -> bool:
    """
    Check if currently in combat
    
    Returns:
        True if in combat, False otherwise
    """
    return combat_encounter_service.is_in_combat()

def get_current_turn() -> Optional[Dict[str, Any]]:
    """
    Get current combatant information
    
    Returns:
        Current combatant data or None
    """
    return combat_encounter_service.get_current_turn()

def get_turn_order() -> List[Dict[str, Any]]:
    """
    Get turn order with initiative values
    
    Returns:
        List of combatants sorted by initiative
    """
    return combat_encounter_service.get_turn_order()

def clear_combat_state() -> bool:
    """
    Clear combat state
    
    Returns:
        True if cleared successfully
    """
    return combat_encounter_service.clear_combat_state()
