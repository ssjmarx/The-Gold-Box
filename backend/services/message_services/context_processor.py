"""
Context Processor - Core logic for transforming complete board data into compact, AI-readable JSON
Game-Agnostic: Handle different game systems dynamically
Dynamic Attribute Mapping: Mechanical field detection and standardization
Compression: Optimize data for token efficiency
Combat-Aware: Include combat context for tactical AI decisions
"""

import json
import logging
from typing import Dict, Any, List, Optional, Tuple
from shared.exceptions import MessageCollectionException


class ContextProcessor:
    """
    Transform complete board data into compact, AI-readable JSON
    Game-Agnostic: Handle different game systems dynamically
    Dynamic Attribute Mapping: Mechanical field detection and standardization
    Compression: Optimize data for token efficiency
    """
    
    def __init__(self, foundry_client):
        self.foundry_client = foundry_client
        self.logger = logging.getLogger(__name__)
        
        # Initialize components using ServiceFactory pattern
        from ..system_services.service_factory import get_attribute_mapper, get_json_optimizer, get_combat_encounter_service
        
        self.attribute_mapper = get_attribute_mapper()
        self.json_optimizer = get_json_optimizer()
        self.combat_encounter_service = get_combat_encounter_service()
        
        # Board collector still needs direct client injection
        from shared.core.board_collector import BoardStateCollector
        self.board_collector = BoardStateCollector(foundry_client)
        
        # Cache for attribute mappings across calls
        self.attribute_mapping_cache = {}
        self.reverse_mapping_cache = {}
    
    async def process_context_request(self, client_id: str, scene_id: str, 
                                  include_chat_history: bool = True,
                                  message_count: int = 50) -> Dict[str, Any]:
        """
        Process a complete context request
        
        Args:
            client_id: Foundry client ID
            scene_id: Scene ID to process
            include_chat_history: Whether to include chat messages
            message_count: Number of recent messages to include
            
        Returns:
            Complete processed context ready for AI
        """
        
        try:
            self.logger.info(f"Processing context request for client {client_id}, scene {scene_id}")
            
            # Step 1: Collect complete board state
            board_state = await self.board_collector.collect_complete_board_state(scene_id)
            
            # Step 2: Extract all unique attributes from all tokens
            all_attributes = self._extract_all_token_attributes(board_state)
            
            # Step 3: Generate mechanical attribute codes
            code_mapping, reverse_mapping = self.attribute_mapper.map_attributes(all_attributes)
            
            # Step 4: Optimize board state with attribute codes
            optimized_board_state = self.json_optimizer.optimize_board_state(board_state, code_mapping)
            
            # Step 5: Collect chat history if requested
            chat_history = []
            if include_chat_history:
                chat_history = await self._collect_chat_history(client_id, message_count)
            
            # Step 6: Generate system prompt with attribute mappings
            system_prompt = self._generate_system_prompt(reverse_mapping, optimized_board_state)
            
            # Step 6: Get combat context
            combat_context = self.combat_encounter_service.get_combat_context()
            
            # Step 7: Create final context
            processed_context = {
                'system_prompt': system_prompt,
                'board_state': optimized_board_state,
                'chat_history': chat_history,
                'combat_context': combat_context,
                'metadata': {
                    'client_id': client_id,
                    'scene_id': scene_id,
                    'attribute_count': len(all_attributes),
                    'optimization_stats': self.json_optimizer.get_optimization_stats(),
                    'processed_at': self._get_timestamp(),
                    'in_combat': combat_context.get('in_combat', False)
                }
            }
            
            self.logger.info(f"Context processing complete: {len(all_attributes)} attributes mapped, "
                           f"{self.json_optimizer.get_optimization_stats()['compression_ratio']:.1%} compression")
            
            return processed_context
            
        except Exception as e:
            self.logger.error(f"Error processing context request: {e}")
            raise MessageCollectionException(f"Error processing context request: {e}")
    
    def _extract_all_token_attributes(self, board_state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract all unique attributes from all tokens in board state
        
        Args:
            board_state: Complete board state data
            
        Returns:
            Dictionary of all unique attribute names found
        """
        
        all_attributes = {}
        
        if 'tokens' not in board_state:
            return all_attributes
        
        for token in board_state['tokens']:
            if hasattr(token, 'attributes') and token.attributes:
                # Merge token attributes into global collection
                for attr_name, attr_value in token.attributes.items():
                    if attr_name not in all_attributes:
                        all_attributes[attr_name] = attr_value
        
        # self.logger.info(f"Extracted {len(all_attributes)} unique attributes from tokens")
        return all_attributes
    
    async def _collect_chat_history(self, client_id: str, count: int) -> List[Dict[str, Any]]:
        """
        Collect recent chat messages and dice rolls using unified utilities
        
        Args:
            client_id: Foundry client identifier
            count: Number of recent messages to collect
            
        Returns:
            List of combined chat and dice messages
        """
        
        try:
            # Import message collector to get unified chat and dice context
            from .message_collector import get_combined_client_messages
            
            # Get combined messages using unified collector
            all_messages = get_combined_client_messages(client_id, count)
            
            # Extract only chat messages (exclude rolls for this context)
            chat_messages = [msg for msg in all_messages if msg.get('_source') != 'roll']
            
            self.logger.info(f"Collected {len(chat_messages)} chat messages for client {client_id}")
            return chat_messages
            
        except Exception as e:
            self.logger.warning(f"Could not collect chat history: {e}")
            return []
    
    def _generate_system_prompt(self, reverse_mapping: Dict[str, str], 
                              optimized_board_state: Dict[str, Any]) -> str:
        """
        Generate system prompt with mechanical attribute code dictionary
        Enhanced for Phase 5: Pure System-Agnostic operation
        
        Args:
            reverse_mapping: Mapping from codes to full attribute names
            optimized_board_state: The optimized board state data
            
        Returns:
            Complete system prompt for AI
        """
        
        # PHASE 5: Create enhanced mechanical attribute code dictionary
        attribute_dict_lines = ["Attribute Code Mapping (mechanically generated, system-agnostic):"]
        
        for code, full_name in reverse_mapping.items():
            attribute_dict_lines.append(f"{code}={full_name}")
        
        attribute_dict_lines.append("Note: Codes are mechanically generated from attribute names - no semantic assumptions")
        attribute_dict_lines.append("These codes work for ANY game system (D&D, Pathfinder, Call of Cthulhu, Savage Worlds, etc.)")
        attribute_dict_text = "\n".join(attribute_dict_lines)
        
        # PHASE 5: Enhanced board format instructions for universal game systems
        board_instructions = """Universal Board Format Instructions:
Complete Board State: {scene dimensions, walls, lighting, notes, token positions, ALL attributes, templates}
Use spatial and attribute data for contextual responses
This data format works with ANY TTRPG system or custom implementation

Combat Context Instructions:
When in combat, use combat context for tactical decision making
Current turn, turn order, and combatant information provided
Use this information to make tactical suggestions and track combat flow"""
        
        # PHASE 5: Enhanced context usage guidelines for system-agnostic operation
        usage_guidelines = """Universal Context Usage Guidelines (System-Agnostic):
Use token positions and facing for movement awareness
Consider walls and doors for spatial context and pathfinding
Factor in lighting for visibility considerations
Use detected attributes (with provided mechanical code mappings) for character context
Consider templates and areas for spatial effects and AoE
Reference map notes for location information
Attribute codes are MECHANICALLY generated - use provided dictionary
This system works with D&D 5e, Pathfinder 1e/2e, Call of Cthulhu, Savage Worlds, Starfinder, Cyberpunk, and ANY custom/homebrew system"""
        
        # PHASE 5: Enhanced data structure explanation
        structure_explanation = self._generate_structure_explanation(optimized_board_state)
        
        # PHASE 5: Add game system adaptability section
        adaptability_section = self._generate_adaptability_section()
        
        # PHASE 5: Add universal examples for different game systems
        examples_section = self._generate_examples_section()
        
        # Combine all enhanced prompt components
        system_prompt = f"""{attribute_dict_text}

{board_instructions}

{usage_guidelines}

{structure_explanation}

{adaptability_section}

{examples_section}"""
        
        return system_prompt
    
    def _generate_structure_explanation(self, board_state: Dict[str, Any]) -> str:
        """
        Generate explanation of optimized data structure
        
        Args:
            board_state: Optimized board state
            
        Returns:
            Explanation of data structure
        """
        
        explanation_parts = ["Data Structure Explanation:"]
        
        structure_map = {
            'scn': 'Scene information (dimensions, grid)',
            'wal': 'Walls and doors (coordinates, blocking types)',
            'lig': 'Lighting sources (positions, colors, ranges)',
            'not': 'Map notes (text, positions, visibility)',
            'tkn': 'Tokens (positions, attributes, vision)',
            'tpl': 'Templates (areas, shapes, effects)'
        }
        
        for key, description in structure_map.items():
            if key in board_state:
                explanation_parts.append(f"  {key}: {description}")
        
        return "\n".join(explanation_parts)
    
    def _get_timestamp(self) -> str:
        """Get current timestamp for metadata"""
        from datetime import datetime
        return datetime.utcnow().isoformat() + 'Z'
    
    def _generate_adaptability_section(self) -> str:
        """
        Generate adaptability section for Phase 5
        
        Returns:
            Adaptability explanation text
        """
        
        return """System Adaptability:
This context processor is 100% system-agnostic and adapts to:
- D&D 5e (attributes: hp, ac, speed, strength, etc.)
- Pathfinder 1e & 2e (attributes: hp, ac, speed, str, etc.)
- Call of Cthulhu (attributes: sanity, luck, etc.)
- Savage Worlds (attributes: agility, smarts, spirit, etc.)
- Starfinder (attributes: stamina, resolve, etc.)
- Cyberpunk systems (arbitrary attribute names)
- Custom/homebrew systems (completely arbitrary attributes)

The mechanical code generation works with ANY attribute naming convention."""
    
    def _generate_examples_section(self) -> str:
        """
        Generate universal examples for Phase 5
        
        Returns:
            Examples section text
        """
        
        return """Universal Examples for Different Game Systems:

D&D 5e Example:
- Token attributes: {"hp": 45, "ac": 16, "speed": 30}
- Mapped codes: {"hp": 45, "ac": 16, "spd": 30}
- AI should understand: fighter with 45 HP, 16 AC, 30 speed

Pathfinder Example:
- Token attributes: {"health": 60, "armor_class": 18, "initiative": 5}
- Mapped codes: {"hea": 60, "arm": 18, "ini": 5}
- AI should understand: character with 60 health, 18 AC, +5 initiative

Call of Cthulhu Example:
- Token attributes: {"sanity": 80, "luck": 50, "spot_hidden": 25}
- Mapped codes: {"san": 80, "luc": 50, "spo": 25}
- AI should understand: investigator with 80 sanity, 50 luck, 25 spot hidden

Savage Worlds Example:
- Token attributes: {"agility": 8, "smarts": 6, "spirit": 4}
- Mapped codes: {"agi": 8, "sma": 6, "spi": 4}
- AI should understand: wild card with d8 agility, d6 smarts, d4 spirit

Custom/Cyberpunk Example:
- Token attributes: {"quantum_flux_capacitor": 75, "neural_interface_rating": 8}
- Mapped codes: {"qua": 75, "neu": 8}
- AI should understand: character with quantum flux capacitor, neural interface

Any Game System Works:
The system detects and maps ANY attribute name mechanically."""
    
    def get_processing_stats(self) -> Dict[str, Any]:
        """
        Get statistics about context processing
        
        Returns:
            Dictionary of processing statistics
        """
        
        return {
            'attribute_mappings': self.attribute_mapper.get_code_mapping(),
            'reverse_mappings': self.attribute_mapper.get_reverse_mapping(),
            'optimization_stats': self.json_optimizer.get_optimization_stats()
        }
    
    def reset_caches(self):
        """Reset all caches and statistics"""
        self.attribute_mapping_cache.clear()
        self.reverse_mapping_cache.clear()
        self.json_optimizer.reset_stats()
        self.logger.info("Context processor caches and stats reset")


# Mock Foundry client for testing
class MockFoundryClientWithChat:
    """Mock client that includes chat functionality"""
    
    async def get_chat_messages(self, client_id: str, count: int) -> List[Dict[str, Any]]:
        # Mock chat messages
        return [
            {
                'id': 'msg1',
                'user': 'Player1',
                'content': 'I move forward to investigate the door.',
                'timestamp': 1634567890,
                'type': 'chat'
            },
            {
                'id': 'msg2',
                'user': 'GM',
                'content': 'You see a wooden door with strange markings.',
                'timestamp': 1634567950,
                'type': 'chat'
            },
            {
                'id': 'msg3',
                'user': 'Player2',
                'content': 'I check the door for traps.',
                'timestamp': 1634568000,
                'type': 'chat'
            }
        ]


# Test implementation
if __name__ == "__main__":
    import asyncio
    from shared.core.board_collector import MockFoundryClient
    
    async def test_context_processor():
        # Create a combined mock client
        class TestMockClient(MockFoundryClient, MockFoundryClientWithChat):
            pass
        
        processor = ContextProcessor(TestMockClient())
        
        # Test context processing
        context = await processor.process_context_request(
            client_id="test_client",
            scene_id="test_scene",
            include_chat_history=True,
            message_count=10
        )
        
        print("=== PROCESSED CONTEXT ===")
        print("\nSystem Prompt:")
        print(context['system_prompt'])
        
        print("\nBoard State (optimized):")
        print(json.dumps(context['board_state'], indent=2))
        
        print("\nChat History:")
        for msg in context['chat_history']:
            print(f"{msg['user']}: {msg['content']}")
        
        print("\nMetadata:")
        print(json.dumps(context['metadata'], indent=2))
        
        print("\nProcessing Stats:")
        stats = processor.get_processing_stats()
        print(json.dumps(stats, indent=2))
    
    asyncio.run(test_context_processor())
