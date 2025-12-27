# Patch 0.3.9: The Foundation - Implementation Plan

## Overview

This patch establishes the AI's core ability to communicate, perceive basic game state, and interact with fundamental mechanics (dice, combat status). The AI becomes a basic, aware participant.

---

## Phase 1: AI Function Updates

### 1.1 Rename Existing Functions

#### Rename `get_messages` → `get_message_history`

**Files to modify:**
- `backend/services/ai_tools/ai_tool_definitions.py`
- `backend/services/ai_tools/ai_tool_executor.py`

**Changes in `ai_tool_definitions.py`:**
```python
{
    "type": "function",
    "function": {
        "name": "get_message_history",
        "description": "Retrieves the most recent chat messages.",
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
}
```

**Changes in `ai_tool_executor.py`:**
- Rename method: `execute_get_messages` → `execute_get_message_history`
- Update routing in `execute_tool`:
  ```python
  if tool_name == 'get_message_history':
      return await self.execute_get_message_history(tool_args, client_id)
  ```

#### Rename `post_messages` → `post_message`

**Files to modify:**
- `backend/services/ai_tools/ai_tool_definitions.py`
- `backend/services/ai_tools/ai_tool_executor.py`

**Changes in `ai_tool_definitions.py`:**
```python
{
    "type": "function",
    "function": {
        "name": "post_message",
        "description": "Posts a new message to the chat.",
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
}
```

**Changes in `ai_tool_executor.py`:**
- Rename method: `execute_post_messages` → `execute_post_message`
- Update to handle single message instead of array
- Add dice-roll detection and translation (see Phase 1.3)

### 1.2 Create New Functions

#### `roll_dice` Function

**Add to `ai_tool_definitions.py`:**
```python
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
}
```

**Add to `ai_tool_executor.py`:**

Create new method `execute_roll_dice`:
```python
async def execute_roll_dice(
    self,
    args: Dict[str, Any],
    client_id: str
) -> Dict[str, Any]:
    """
    Execute roll_dice tool - requests dice rolls from frontend
    
    Args:
        args: Tool arguments (must contain 'rolls' array)
        client_id: Client ID for WebSocket communication
    
    Returns:
        Dict with pending roll status (results come back via frontend)
    """
    try:
        # Validate arguments
        rolls = args.get('rolls', [])
        if not isinstance(rolls, list) or not rolls:
            raise ValueError("rolls must be a non-empty array")
        
        for roll in rolls:
            if not isinstance(roll, dict) or 'formula' not in roll:
                raise ValueError("Each roll must be a dict with 'formula' field")
        
        # Get WebSocket manager
        from ..system_services.service_factory import get_websocket_manager
        websocket_manager = get_websocket_manager()
        
        # Send dice roll requests to frontend
        results = []
        for roll in rolls:
            formula = roll.get('formula', '')
            flavor = roll.get('flavor', '')
            
            ws_message = {
                "type": "dice_roll_request",
                "data": {
                    "formula": formula,
                    "flavor": flavor,
                    "timestamp": datetime.now().isoformat()
                }
            }
            
            success = await websocket_manager.send_to_client(client_id, ws_message)
            results.append({
                "formula": formula,
                "success": success
            })
        
        logger.info(f"roll_dice executed: {len(results)} dice roll requests sent to frontend for client {client_id}")
        
        return {
            "success": True,
            "message": f"Dice roll requests sent. Results will be available in next chat context.",
            "requests": results
        }
        
    except Exception as e:
        logger.error(f"roll_dice execution failed: {e}")
        return {
            "success": False,
            "error": str(e)
        }
```

**Full Data Flow for `roll_dice`:**

1. **AI calls `roll_dice`** → Backend receives tool call
2. **Backend sends to frontend** → WebSocket message type `dice_roll_request`
3. **Frontend executes rolls** → Uses Foundry's `game.dice.roll()` API
4. **Frontend sends results** → WebSocket message type `dice_roll_result` (or via webhook)
5. **Backend collects results** → Message collector captures dice-roll messages
6. **Results available to AI** → Next `get_message_history` call includes roll results

#### `get_encounter` Function

**Add to `ai_tool_definitions.py`:**
```python
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
```

**Add to `ai_tool_executor.py`:**

Create new method `execute_get_encounter`:
```python
async def execute_get_encounter(
    self,
    args: Dict[str, Any],
    client_id: str
) -> Dict[str, Any]:
    """
    Execute get_encounter tool - retrieves current combat state
    
    Args:
        args: Tool arguments (none required)
        client_id: Client ID for context (not used but kept for consistency)
    
    Returns:
        Dict with combat state or 'no active encounter' message
    """
    try:
        # Get combat encounter service
        from ..system_services.service_factory import get_combat_encounter_service
        combat_service = get_combat_encounter_service()
        
        # Get current combat context
        combat_context = combat_service.get_combat_context()
        
        # Check if combat is active
        if combat_context.get('in_combat', False):
            # Combat is active - return full encounter data
            encounter_data = {
                "success": True,
                "in_combat": True,
                "encounter_id": combat_context.get('combat_id'),
                "round": combat_context.get('round', 0),
                "turn": combat_context.get('turn', 0),
                "combatants": combat_context.get('combatants', []),
                "current_turn_actor": combat_context.get('current_turn_actor')
            }
            
            logger.info(f"get_encounter: Active encounter {encounter_data['encounter_id']}, Round {encounter_data['round']}, Turn {encounter_data['turn']}")
            
            return encounter_data
        else:
            # No active encounter
            logger.info("get_encounter: No active encounter")
            
            return {
                "success": True,
                "in_combat": False,
                "message": "No active encounter"
            }
        
    except Exception as e:
        logger.error(f"get_encounter execution failed: {e}")
        return {
            "success": False,
            "error": str(e)
        }
```

**Note:** Combat encounter data structure includes:
- `combat_id`: Unique identifier for the encounter
- `round`: Current round number
- `turn`: Current turn index
- `combatants`: Array of combatant objects (actors, their initiative, HP, status effects)
- `current_turn_actor`: Name/ID of actor whose turn it currently is (if active)

### 1.3 Dice Roll Detection in `post_message`

**Modify `execute_post_message` in `ai_tool_executor.py`:**

Add logic to detect and translate dice-roll message types:

```python
async def execute_post_message(
    self,
    args: Dict[str, Any],
    client_id: str
) -> Dict[str, Any]:
    """
    Execute post_message tool - with dice-roll detection
    
    Args:
        args: Tool arguments (must contain 'content')
        client_id: Client ID for WebSocket communication
    
    Returns:
        Dict with success status
    """
    try:
        # Validate arguments
        content = args.get('content', '')
        if not content:
            raise ValueError("content is required")
        
        # Check if content is a dice roll (AI trying to create roll via post_message)
        # Pattern detection: dice formulas, roll keywords, etc.
        import re
        dice_pattern = r'\d+d\d+[\+\-]\d+|\d+d\d+'
        
        is_dice_roll = re.search(dice_pattern, content) is not None
        is_roll_keyword = any(keyword in content.lower() for keyword in ['roll ', 'rolls', 'attack roll', 'damage'])
        
        if is_dice_roll or is_roll_keyword:
            # AI is trying to create a dice roll - translate to roll_dice call
            logger.warning(f"AI attempting dice roll via post_message, translating to roll_dice")
            
            # Extract formula from content
            formula_match = re.search(r'(\d+d\d+[\+\-]\d+|\d+d\d+)', content)
            if formula_match:
                formula = formula_match.group(1)
                flavor = content.replace(formula, '').strip()
                
                # Call roll_dice instead
                from ..system_services.service_factory import get_ai_tool_executor
                tool_executor = get_ai_tool_executor()
                return await tool_executor.execute_roll_dice(
                    {'rolls': [{'formula': formula, 'flavor': flavor}]},
                    client_id
                )
        
        # Normal post_message logic continues...
        # (Send chat message to frontend via WebSocket)
        
    except Exception as e:
        logger.error(f"post_message execution failed: {e}")
        return {
            "success": False,
            "error": str(e)
        }
```

---

## Phase 2: Delta Tracking Updates

### 2.1 Update Delta Format to PascalCase

**Modify `backend/api/api_chat.py`:**

In `process_with_function_calling_or_standard` function:

```python
# OLD:
new_count = message_delta.get('new_messages', 0)
deleted_count = message_delta.get('deleted_messages', 0)

# NEW:
new_count = message_delta.get('NewMessages', 0)
deleted_count = message_delta.get('DeletedMessages', 0)
```

### 2.2 Add New Delta Fields

**Frontend Changes (to be implemented in frontend):**

Frontend must track and send these new delta fields:
- `NewDiceRolls`: Array of dice roll objects since last AI turn
  ```javascript
  {
    "formula": "1d20+5",
    "result": 22,
    "flavor": "Attack Roll"
  }
  ```
- `EncounterStarted`: Object with encounter info when combat begins
  ```javascript
  {
    "id": "combat123",
    "name": "Goblin Ambush"
  }
  ```
- `EncounterEnded`: Boolean when combat ends
  ```javascript
  true  // or omitted if false
  ```
- `CurrentTurnActor`: String name of actor whose turn it currently is (if encounter active)

**Modify `backend/api/api_chat.py`:**

Update delta display in `process_with_function_calling_or_standard`:

```python
# Extract new delta fields
new_dice_rolls = message_delta.get('NewDiceRolls', [])
encounter_started = message_delta.get('EncounterStarted')
encounter_ended = message_delta.get('EncounterEnded')
current_turn_actor = message_delta.get('CurrentTurnActor')

# Build delta display - only include non-zero/non-None values
delta_parts = []
delta_parts.append(f'"NewMessages": {new_count}')
delta_parts.append(f'"DeletedMessages": {deleted_count}')

if new_dice_rolls:
    delta_parts.append(f'"NewDiceRolls": {json.dumps(new_dice_rolls)}')

if encounter_started:
    delta_parts.append(f'"EncounterStarted": {json.dumps(encounter_started)}')

if encounter_ended:
    delta_parts.append(f'"EncounterEnded": {encounter_ended}')

if current_turn_actor:
    delta_parts.append(f'"CurrentTurnActor": "{current_turn_actor}"')

delta_display = f"""

Recent changes to the game:
{{{', '.join(delta_parts)}}}
"""
```

Add to system prompt:
```python
system_prompt_with_delta = system_prompt + delta_display
```

---

## Phase 3: World State Overview Implementation

### 3.1 Create World State Overview Generator

**New File: `backend/services/ai_services/world_state_generator.py`**

```python
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
```

### 3.2 Integrate World State Overview into System Prompt

**Modify `backend/shared/core/unified_message_processor.py`:**

Update `generate_enhanced_system_prompt` method signature:
```python
def generate_enhanced_system_prompt(
    self,
    ai_role: str,
    compact_messages: List[Dict[str, Any]],
    world_state_overview: Optional[Dict[str, Any]] = None
) -> str:
```

Add WSO insertion at beginning of prompt:
```python
def generate_enhanced_system_prompt(
    self,
    ai_role: str,
    compact_messages: List[Dict[str, Any]],
    world_state_overview: Optional[Dict[str, Any]] = None
) -> str:
    """
    Generate enhanced system prompt with optional World State Overview
    """
    # Build system prompt with WSO (if provided for new sessions)
    system_prompt_parts = []
    
    # Add World State Overview for new sessions
    if world_state_overview:
        wso_str = f"""

World State Overview:
{json.dumps(world_state_overview, indent=2)}

"""
        system_prompt_parts.append(wso_str)
    
    # ... rest of existing system prompt generation code ...
    # (role prompts, combat context, etc.)
    
    return ''.join(system_prompt_parts)
```

### 3.3 Determine New Session vs. Existing Session

**Modify `backend/api/api_chat.py`:**

In `process_with_function_calling_or_standard` function:

```python
# Get AI session manager
from services.system_services.service_factory import get_ai_session_manager
ai_session_manager = get_ai_session_manager()

# Check if this is a new session (no conversation history yet)
conversation_history = ai_session_manager.get_conversation_history(session_id)
is_new_session = len(conversation_history) == 0

# Generate World State Overview for new sessions only
world_state_overview = None
if is_new_session:
    from services.ai_services.world_state_generator import get_world_state_generator
    wso_generator = get_world_state_generator()
    world_state_overview = wso_generator.generate_world_state_overview(
        client_id,
        universal_settings
    )
    logger.info(f"New session detected - generated World State Overview for session {session_id}")
else:
    logger.info(f"Existing session - skipping World State Overview for session {session_id}")

# Pass WSO to system prompt generator
system_prompt = unified_processor.generate_enhanced_system_prompt(
    ai_role,
    compact_messages,
    world_state_overview=world_state_overview
)
```

---

## Phase 4: Frontend Data Collection Requirements

The frontend must implement webhook handlers to collect and send the following data:

### 4.1 Scene Data

Frontend should send scene info via WebSocket when scene changes or on initial connection:

```javascript
// Send to backend
{
  "type": "scene_info",
  "scene_info": {
    "id": "scene123",
    "name": "The Sunless Citadel",
    "dimensions": {
      "width": 4000,
      "height": 3000,
      "grid": 50
    },
    "tokens": [
      {
        "id": "tokenA",
        "name": "Valerius",
        "actor_id": "actorA",
        "x": 1000,
        "y": 1500,
        "is_player": true
      }
    ]
  }
}
```

### 4.2 Party Data

Frontend should send party info via WebSocket:

```javascript
{
  "type": "party_info",
  "party_info": [
    {
      "id": "actorA",
      "name": "Valerius",
      "player": "Alice"
    },
    {
      "id": "actorC",
      "name": "Kaelen",
      "player": "Bob"
    }
  ]
}
```

### 4.3 Delta Data for Dice Rolls

Frontend should track dice rolls since last AI turn:

```javascript
// In delta object sent to backend
{
  "NewDiceRolls": [
    {
      "formula": "1d20+5",
      "result": 22,
      "flavor": "Attack Roll"
    },
    {
      "formula": "2d6+2",
      "result": 9,
      "flavor": "Greatsword Damage"
    }
  ]
}
```

### 4.4 Encounter Delta Data

Frontend should track encounter state changes:

```javascript
// When combat starts
{
  "EncounterStarted": {
    "id": "combat123",
    "name": "Goblin Ambush"
  }
}

// When combat ends
{
  "EncounterEnded": true
}

// Current turn actor (if encounter active)
{
  "CurrentTurnActor": "Goblin Guard"  // Actor name
}
```

---

## Phase 5: Testing Harness Integration

The testing harness already uses universal tool calling via `execute_tool_call`, so renamed and new functions will automatically be available.

### 5.1 Update Testing Documentation

**Modify `backend/testing/TESTING.md`:**

Add documentation for:
- Renamed functions (`get_message_history`, `post_message`)
- New functions (`roll_dice`, `get_encounter`)
- World State Overview availability for new sessions
- Delta format changes (PascalCase, new fields)
- Dice roll detection in `post_message`

---

## Phase 6: Testing Strategy

### 6.1 Unit Tests (via Testing Harness)

For each function, test:

**`get_message_history`:**
- Retrieve messages with various limits (1, 15, 50)
- Empty result when no messages exist
- Timestamps are included

**`post_message`:**
- Send simple chat message
- Send message with speaker_name and flavor
- Send different message types (ic, ooc, emote)
- Test dice-roll detection and translation

**`roll_dice`:**
- Roll single die formula
- Roll multiple dice formulas
- Roll with flavor text
- Verify WebSocket message sent to frontend

**`get_encounter`:**
- Get combat state when in combat (verify structure)
- Get "no active encounter" message when out of combat
- Verify encounter_id, round, turn, combatants, current_turn_actor

### 6.2 Integration Tests

1. **New Session Flow:**
   - Create new session (no history)
   - Verify World State Overview is generated and included in prompt
   - Verify session_info, active_scene, party_compendium, active_encounter structure

2. **Existing Session Flow:**
   - Continue session with existing history
   - Verify World State Overview is NOT included (delta only)

3. **Delta Format Test:**
   - Verify PascalCase format (NewMessages, DeletedMessages)
   - Verify new fields appear only when non-zero/non-None
   - Test NewDiceRolls, EncounterStarted, EncounterEnded, CurrentTurnActor

4. **Dice Roll Data Flow Test:**
   - AI calls `roll_dice`
   - Verify request sent to frontend
   - Verify frontend executes roll (mocked in test)
   - Verify results sent back to backend
   - Verify results available in next `get_message_history` call

5. **Function Calling Loop Test:**
   - AI calls multiple tools in sequence
   - Verify renamed and new functions work
   - Verify dice-roll detection in `post_message` triggers `roll_dice`

### 6.3 Regression Tests

Ensure existing functionality still works:
- Standard chat mode (without function calling)
- Delta filtering behavior
- Conversation history management
- CombatEncounterService integration

---

## Implementation Order

1. **Phase 1** - AI Function Updates (renames + new functions + dice detection)
2. **Phase 2** - Delta Updates (PascalCase + new fields)
3. **Phase 3** - World State Overview (generator + integration + session detection)
4. **Phase 4** - Frontend Requirements (document requirements for frontend implementation)
5. **Phase 5** - Testing Harness (update documentation)
6. **Phase 6** - Testing (all test types)

---

## Files to Modify

### Backend Files:
1. `backend/services/ai_tools/ai_tool_definitions.py` - Rename + add functions
2. `backend/services/ai_tools/ai_tool_executor.py` - Update execution methods + dice detection
3. `backend/api/api_chat.py` - Delta format + WSO integration + session detection
4. `backend/shared/core/unified_message_processor.py` - System prompt with WSO parameter
5. `backend/services/ai_services/world_state_generator.py` - NEW FILE
6. `backend/testing/TESTING.md` - Update documentation

### Frontend Files (for reference):
- `scripts/services/frontend-delta-service.js` - Add delta field tracking
- `scripts/api/combat-monitor.js` - Add encounter delta tracking
- `scripts/services/message-collector.js` - Add scene/party info collection

---

## Summary

Patch 0.3.9: The Foundation establishes the AI's core capabilities:
- **Communication**: `get_message_history`, `post_message`
- **Dice**: `roll_dice` with full data flow (AI → Backend → Frontend → Execute → Results → Backend → AI)
- **Combat**: `get_encounter` with combatants, turn order, current turn
- **Context**: World State Overview for new sessions (session_info, active_scene, party_compendium, active_encounter, compendium_index)
- **Delta Tracking**: PascalCase format + NewDiceRolls, EncounterStarted, EncounterEnded, CurrentTurnActor
- **Testing**: All functions available via testing harness

This creates a solid foundation for future patches (Combatant, Observer, Agent).
