#!/usr/bin/env python3
"""
Combat Prompt Generator for The Gold Box
Generates dynamic AI prompts based on combat state
Provides context-aware instructions for exploration, player turns, and NPC group turns

License: CC-BY-NC-SA 4.0
"""

import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

class CombatPromptGenerator:
    """
    Generates dynamic AI prompts based on combat state
    Provides context-aware instructions for different combat scenarios
    """
    
    def __init__(self):
        """Initialize combat prompt generator"""
        self.logger = logging.getLogger(__name__)
        self.logger.info("CombatPromptGenerator initialized")
    
    def generate_prompt(self, combat_context: Dict[str, Any], combat_state: Dict[str, Any]) -> str:
        """
        Generate appropriate prompt based on combat state
        
        Args:
            combat_context: Combat context from CombatEncounterService
            combat_state: Raw combat state from frontend
            
        Returns:
            Appropriate prompt instruction text
        """
        try:
            # Check if in combat
            if not combat_context.get("in_combat", False):
                return self._get_no_combat_prompt()
            
            # Get current turn combatant
            current_turn = self._get_current_turn_combatant(combat_state)
            
            if not current_turn:
                # No current turn, use no combat prompt
                return self._get_no_combat_prompt()
            
            # Check if current turn is a player
            if current_turn.get("is_player", False):
                return self._get_player_turn_prompt(current_turn.get("name", "Unknown"))
            
            # Current turn is NPC, get NPC group sequence (excluding current NPC)
            npc_sequence = self._get_npc_turn_sequence(combat_state)
            return self._get_npc_group_prompt(npc_sequence)
            
        except Exception as e:
            self.logger.error(f"Error generating combat prompt: {e}")
            # Fallback to generic prompt
            return "Please respond to this conversation as an AI assistant for tabletop RPGs. If you need to generate game mechanics, use compact JSON format specified in system prompt."
    
    def _get_no_combat_prompt(self) -> str:
        """
        Get prompt for non-combat scenarios
        
        Returns:
            Exploration-focused prompt instruction
        """
        return """Your instruction is to respond to this prompt with:
1) Resolve any pending player actions, dice rolls, or mechanical effects from the previous context.
2) Describe reactions from non-player characters to the most recent player actions with personality and intent.
3) Provide vivid descriptions of the current environment, including lighting, sounds, smells, and atmosphere.
4) Create natural chat messages, chat cards, and dice rolls based on your role as Game Master and the current situation.
5) Set up the next scene or encounter based on player movements, discoveries, and choices."""
    
    def _get_player_turn_prompt(self, current_player_name: str) -> str:
        """
        Get prompt for player turn scenarios
        
        Args:
            current_player_name: Name of current player
            
        Returns:
            Player action-focused prompt instruction
        """
        return f"""It is currently {current_player_name}'s turn.  Your instruction is to respond to this prompt with:
1) Describe what {current_player_name} will attempt to do this turn, considering the current tactical situation and environment.
2) Generate appropriate dice rolls for the attempted actions, including modifiers for cover, range, and conditions.
3) Create descriptive chat cards for abilities, spells, or special actions when applicable.
4) Describe the immediate results of the actions, including hit/miss, damage, and environmental effects.
5) Anticipate and describe any reactions from nearby enemies or NPCs."""
    
    def _get_npc_group_prompt(self, npc_sequence: List[str]) -> str:
        """
        Get prompt for NPC group turn scenarios
        
        Args:
            npc_sequence: List of NPC names taking turns before next player
            
        Returns:
            Coordinated NPC action prompt instruction
        """
        if not npc_sequence:
            # No NPCs, use no combat prompt
            return self._get_no_combat_prompt()
        
        # Format NPC list as readable text
        npc_list = ", ".join(npc_sequence)
        
        return f"""{npc_list} are currently taking their turns.  Your instruction is to respond to this prompt with:
1) Describe coordinated actions for the NPC group as a whole, considering tactical positioning and objectives.
2) Generate separate dice rolls for each NPC's attacks, saving throws, and skill checks.
3) Create descriptive chat cards for special abilities, spells, or coordinated tactics.
4) Describe the results of the group's turn, including movement, positioning changes, and combat effects.
5) Focus on intelligent tactical behavior - flanking, cover usage, spell combinations, and team coordination."""
    
    def _get_current_turn_combatant(self, combat_state: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Get current turn combatant from combat state
        
        Args:
            combat_state: Raw combat state from frontend
            
        Returns:
            Current combatant data or None
        """
        try:
            combatants = combat_state.get("combatants", [])
            
            for combatant in combatants:
                if combatant.get("is_current_turn", False):
                    return combatant
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error getting current turn combatant: {e}")
            return None
    
    def _get_npc_turn_sequence(self, combat_state: Dict[str, Any]) -> List[str]:
        """
        Get sequence of NPCs who will take turns before next player
        
        Args:
            combat_state: Raw combat state from frontend
            
        Returns:
            List of NPC names in turn order
        """
        try:
            combatants = combat_state.get("combatants", [])
            
            if not combatants:
                return []
            
            # Sort combatants by initiative (highest first)
            sorted_combatants = sorted(
                combatants,
                key=lambda x: (-x.get("initiative", 0), x.get("name", ""))
            )
            
            # Find current turn position
            current_turn_index = -1
            for i, combatant in enumerate(sorted_combatants):
                if combatant.get("is_current_turn", False):
                    current_turn_index = i
                    break
            
            if current_turn_index == -1:
                # No current turn found
                return []
            
            # Get all subsequent combatants until next player
            npc_sequence = []
            for i in range(current_turn_index + 1, len(sorted_combatants)):
                combatant = sorted_combatants[i]
                if not combatant.get("is_player", False):
                    npc_sequence.append(combatant.get("name", "Unknown"))
                else:
                    # Found next player, stop collecting NPCs
                    break
            
            # If we looped around, check from beginning
            if not npc_sequence:
                for i in range(0, len(sorted_combatants)):
                    combatant = sorted_combatants[i]
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
            self.logger.error(f"Error getting NPC turn sequence: {e}")
            return []

# Global instance
combat_prompt_generator = CombatPromptGenerator()

def get_combat_prompt_generator() -> CombatPromptGenerator:
    """Get combat prompt generator instance"""
    return combat_prompt_generator
