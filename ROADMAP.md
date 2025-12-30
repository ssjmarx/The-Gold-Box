### **Comprehensive AI Tool Suite Plan**

This plan outlines every function, delta, and initial context element required to give the AI a robust ability to perceive, understand, and manipulate the Foundry VTT world.

---

### **1. The Complete Function Suite**

These are the tools the AI can explicitly call. They are organized by category for clarity.

#### **A. Core & Meta-Functions**
*   **`post_message`**
    *   **Description:** Posts a new message to the chat.
    *   **Parameters:** `content` (string), `speaker_name` (string, optional), `flavor` (string, optional), `type` (enum: "ic", "ooc", "emote").
    *   **Criticality:** **High**
*   **`get_message_history`**
    *   **Description:** Retrieves the most recent chat messages.
    *   **Parameters:** `limit` (integer, optional).
    *   **Criticality:** **High**
*   **`roll_dice`**
    *   **Description:** Rolls one or more Foundry-formatted dice formulas.
    *   **Parameters:** `rolls` (array of objects, each with `formula` and `flavor`).
    *   **Criticality:** **High**

#### **B. Encounter Functions**
*   **`get_encounter`**
    *   **Description:** Gets the current combat state. Returns a standard "no active encounter" response if out of combat.
    *   **Parameters:** None.
    *   **Criticality:** **High**
*   **`create_encounter`**
    *   **Description:** Starts a new combat encounter with a specified list of actors, rolls initiative, and advances to turn 1.
    *   **Parameters:** `actor_ids` (array of strings), `roll_initiative` (boolean, default true).
    *   **Criticality:** **High**
*   **`delete_encounter`**
    *   **Description:** Ends the current combat encounter.
    *   **Parameters:** None.
    *   **Criticality:** **High**
*   **`advance_combat_turn`**
    *   **Description:** Advances the combat tracker to the next turn.
    *   **Parameters:** None.
    *   **Criticality:** **High**
*   **`update_actor_in_encounter`**
    *   **Description:** A versatile function to make changes to a specific combatant's state.
    *   **Parameters:** `actor_id` (string), `hp_change` (integer, optional), `add_status_effect` (string, optional), `remove_status_effect` (string, optional).
    *   **Criticality:** **Medium**

#### **C. Actor & Item Functions**
*   **`get_actor_details`**
    *   **Description:** Retrieves a detailed stat block for a specific actor. Can search for specific text on the sheet.
    *   **Parameters:** `actor_id` (string), `source` (enum: "world", "compendium"), `search_phrase` (string, optional).
    *   **Criticality:** **High**
*   **`get_party_members`**
    *   **Description:** Returns a list of all player-controlled characters (PCs) in the session.
    *   **Parameters:** None.
    *   **Criticality:** **Medium**
*   **`update_actor_hp`**
    *   **Description:** Applies damage or healing to a specific actor.
    *   **Parameters:** `actor_id` (string), `hp_change` (integer), `damage_type` (string, optional).
    *   **Criticality:** **High**
*   **`give_actor_item`**
    *   **Description:** Adds an item to a specific actor's inventory.
    *   **Parameters:** `actor_id` (string), `item_id` (string), `quantity` (integer, default 1).
    *   **Criticality:** **Medium**
*   **`create_actor_on_scene`**
    *   **Description:** Creates a new token for an actor and places it on the current scene.
    *   **Parameters:** `actor_id` (string), `x` (number), `y` (number).
    *   **Criticality:** **Medium**

#### **D. Scene & Environment Functions**
*   **`get_current_scene`**
    *   **Description:** Retrieves data about the currently active scene, including dimensions and a list of tokens with their positions.
    *   **Parameters:** None.
    *   **Criticality:** **High**
*   **`set_active_scene`**
    *   **Description:** Changes the view for all players to a different scene.
    *   **Parameters:** `scene_id` (string).
    *   **Criticality:** **Medium**
*   **`move_token`**
    *   **Description:** Moves a specific token to new coordinates on the current scene grid.
    *   **Parameters:** `token_id` (string), `x` (number), `y` (number).
    *   **Criticality:** **Medium**
*   **`get_scene_layout`**
    *   **Description:** Retrieves the geometric data of the current scene, including walls and doors.
    *   **Parameters:** None.
    *   **Criticality:** **Medium**
*   **`get_scene_lighting`**
    *   **Description:** Retrieves information about all light sources on the current scene.
    *   **Parameters:** None.
    *   **Criticality:** **Medium**
*   **`measure_distance`**
    *   **Description:** Measures the distance between two points, accounting for walls and terrain.
    *   **Parameters:** `from_x`, `from_y` (numbers), `to_x`, `to_y` (numbers).
    *   **Returns:** `{ "distance": ..., "path_blocked": boolean, "intervening_tokens": [...] }`
    *   **Criticality:** **High**
*   **`interact_with_door`**
    *   **Description:** Opens or closes a specific door on the map.
    *   **Parameters:** `door_id` (string), `action` (enum: "open", "close").
    *   **Criticality:** **Medium**
*   **`interact_with_light_source`**
    *   **Description:** Toggles or adjusts a light source.
    *   **Parameters:** `light_source_id` (string), `action` (enum: "toggle_on", "toggle_off", "extinguish").
    *   **Criticality:** **Medium**

#### **E. Knowledge & Lore Functions**
*   **`get_journal_context`**
    *   **Description:** Searches for a phrase within a journal entry and returns the surrounding context.
    *   **Parameters:** `entry_name` (string), `search_phrase` (string), `context_lines` (integer, optional).
    *   **Criticality:** **High**
*   **`get_scene_notes`**
    *   **Description:** Retrieves all journal notes pinned to the current scene, including their text and position.
    *   **Parameters:** None.
    *   **Criticality:** **High**
*   **`create_journal_note`**
    *   **Description:** Pins a new journal entry note to the map at a specific location.
    *   **Parameters:** `entry_name` (string), `x` (number), `y` (number).
    *   **Criticality:** **Low**
*   **`roll_on_table`**
    *   **Description:** Performs a roll on a specific Rollable Table and returns the result(s).
    *   **Parameters:** `table_name` (string), `roll_formula` (string, optional).
    *   **Criticality:** **Medium**

#### **F. Search & Utility Functions**
*   **`search_compendium`**
    *   **Description:** Searches within a specific compendium pack for entries matching a query.
    *   **Parameters:** `pack_name` (string), `query` (string).
    *   **Criticality:** **High**
*   **`execute_macro`**
    *   **Description:** Executes a specific, GM-approved macro.
    *   **Parameters:** `macro_name` (string).
    *   **Criticality:** **Low**

---

### **2. The Complete Delta Service**

This JSON object is included in every AI prompt to inform it of changes since its last turn.

```json
Recent changes to the game:
{
  "NewMessages": 2,
  "DeletedMessages": 0,
  "NewDiceRolls": [
    {"formula": "1d20+5", "result": 22, "flavor": "Attack Roll"},
    {"formula": "2d6+2", "result": 9, "flavor": "Greatsword Damage"}
  ],
  "EncounterStarted": { "id": "combat123", "name": "Goblin Ambush" },
  "EncounterEnded": true,
  "TurnAdvanced": true,
  "CombatantChanged": {
    "actor_id": "abc123",
    "hp_change": -9,
    "new_status_effects": ["Prone"]
  },
  "SceneChanged": {
    "new_scene_id": "scene456",
    "new_scene_name": "The Dragon's Lair"
  },
  "TokenMoved": {
    "token_id": "def456",
    "x": 1200,
    "y": 800
  },
  "TokenCreated": {
    "token_id": "tokenXYZ",
    "actor_id": "actorGoblin",
    "x": 1100, "y": 1300
  },
  "SceneNoteUpdated": {
    "note_id": "noteA",
    "entry_name": "4. Tower Shell",
    "position": {"x": 1500, "y": 800}
  },
  "SceneLightingChanged": {
    "light_source_id": "lightB",
    "new_status": "extinguished"
  },
  "DoorStateChanged": {
    "door_id": "door789",
    "new_state": "open"
  },
  "ItemAcquired": {
    "actor_id": "actorA",
    "item_name": "Potion of Healing"
  }
}
```

---

### **3. The Complete Initial Context (`World State Overview`)**

This JSON object is provided to the AI at the beginning of its session to give it a foundational understanding of the world.

```json
World State Overview:
{
  "session_info": {
    "game_system": "dnd5e",
    "gm_name": "The Dungeon Master",
    "players": ["Alice", "Bob", "Charlie"]
  },
  "active_scene": {
    "id": "scene123",
    "name": "The Sunless Citadel",
    "dimensions": {"width": 4000, "height": 3000, "grid": 50},
    "tokens": [
      {"id": "tokenA", "name": "Valerius", "actor_id": "actorA", "x": 1000, "y": 1500, "is_player": true},
      {"id": "tokenB", "name": "Goblin Guard", "actor_id": "actorB", "x": 1200, "y": 1400, "is_player": false}
    ],
    "notes": [
      {"id": "noteA", "entry_name": "4. Tower Shell", "x": 1500, "y": 800, "is_journal_entry": true}
    ],
    "light_sources": [
      {"id": "lightA", "x": 1200, "y": 1200, "radius": 60, "color": "#ffaa00"}
    ]
  },
  "party_compendium": [
    {"id": "actorA", "name": "Valerius", "player": "Alice"},
    {"id": "actorC", "name": "Kaelen", "player": "Bob"}
  ],
  "compendium_index": [
    {"pack_name": "dnd5e.monsters", "type": "Actor"},
    {"pack_name": "dnd5e.items", "type": "Item"},
    {"pack_name": "dnd5e.spells", "type": "Item"},
    {"pack_name": "world.lore-journals", "type": "JournalEntry"},
    {"pack_name": "world.random-encounters", "type": "RollableTable"}
  ],
  "active_encounter": null // Or the full encounter object if one is active
}
```

This comprehensive plan provides the full blueprint for developing a highly capable and context-aware AI for Foundry VTT.

### **Patch 0.3.9: The Foundation**

**Status:** ✅ **COMPLETE**
**Completed:** 2025-12-30

**Goal:** To establish the AI's core ability to communicate, perceive the basic game state, and interact with the most fundamental mechanics (dice, combat status). This patch turns the AI into a basic, aware participant.

#### **New Functions (0.3.9)**
*   `post_message`
*   `get_message_history`
*   `roll_dice`
*   `get_encounter`

#### **New Deltas Tracked (0.3.9)**
*   `NewMessages`
*   `DeletedMessages`
*   `NewDiceRolls`
*   `EncounterStarted`
*   `EncounterEnded`

#### **Initial Context Added (0.3.9)**
The `World State Overview` now includes:
*   `session_info`
*   `party_compendium`
*   A basic `active_scene` object (with name, dimensions, and tokens).
*   `active_encounter` (null or the basic encounter object).

---

### **Patch 0.3.10: The Combatant**

**Goal:** To give the AI the tools needed to actively manage and participate in combat encounters, moving it from a passive observer to an active combatant.

#### **New Functions (0.3.10)**
*   `create_encounter`
*   `delete_encounter`
*   `advance_combat_turn`
*   `get_actor_details`
*   `update_actor_hp`

#### **New Deltas Tracked (0.3.10)**
*   `TurnAdvanced`
*   `CombatantChanged`

#### **Initial Context Added (0.3.10)**
No major changes to the `World State Overview`, as the AI can now query for this information dynamically.

---

### **Patch 0.3.11: The Observer**

**Goal:** To provide the AI with deep contextual awareness of the physical environment and the game's lore. This patch is about giving the AI "eyes" and "ears," allowing it to understand the *where* and the *why*.

#### **New Functions (0.3.11)**
*   `get_scene_layout`
*   `get_scene_lighting`
*   `get_scene_notes`
*   `get_journal_context`
*   `search_compendium`
*   `get_party_members`

#### **New Deltas Tracked (0.3.11)**
*   `SceneChanged`
*   `TokenMoved`
*   `SceneNoteUpdated`

#### **Initial Context Added (0.3.11)**
The `World State Overview` is now expanded:
*   The `active_scene` object now includes the `notes` and `light_sources` arrays.
*   The `compendium_index` is added to give the AI a map of available knowledge.

---

### **Patch 0.4.0: The Agent**

**Goal:** To grant the AI full agency to manipulate the world it now understands. This patch completes the tool suite, allowing the AI to move tokens, interact with objects, create content, and perform complex, measured actions.

#### **New Functions (0.4.0)**
*   `move_token`
*   `measure_distance`
*   `interact_with_door`
*   `interact_with_light_source`
*   `create_actor_on_scene`
*   `give_actor_item`
*   `create_journal_note`
*   `roll_on_table`
*   `set_active_scene`
*   `update_actor_in_encounter`
*   `execute_macro`

#### **New Deltas Tracked (0.4.0)**
*   `TokenCreated`
*   `SceneLightingChanged`
*   `DoorStateChanged`
*   `ItemAcquired`

#### **Initial Context Added (0.4.0)**
No changes to the `World State Overview` are needed, as the AI now has a complete suite of tools to query and manipulate the world as needed.

This phased approach ensures that each patch delivers a cohesive set of features, building a robust and powerful AI assistant layer by layer.

## Phase 2: Professionalization & Beta Prep 

With the feature suite complete, this phase focuses on developer experience, code quality, automation, and stability. These updates are not user-facing features, but they ensure the project is robust enough for collaboration and public use. 

### Patch 0.4.1: The Automation Update 

Goal: Eliminate manual release processes and ensure code integrity through automated testing and pipelines. 

     CI/CD Pipeline:
         Implement GitHub Actions workflows (ci.yml) to run automated tests on every Pull Request.
         Integrate existing test scripts (test_rest_api.py, test_harness.py) into the pipeline.
         
     Release Automation:
         Enhance the Release workflow (release.yml) to communicate with the Foundry VTT Developer API automatically when a version tag (e.g., v0.4.1) is pushed.
         Secure API keys using GitHub Secrets.
         
     Branch Protection:
         Enforce "Require status checks to pass before merging" on the main branch.
         Enable "Require pull request reviews before merging" to facilitate better code quality control.
         
     

### Patch 0.4.2: The Hygiene Update 

Goal: Reduce technical debt and standardize code quality across the project. 

     Linting & Formatting:
         Introduce ESLint and Prettier for the frontend.
         Introduce Pylint or Flake8 and Black for the Python backend.
         Configure CI to fail builds if linting standards are not met.
         
     Dead Code Removal:
         Integrate vulture (Python) to identify unused code/modules.
         Conduct a manual cleanup pass to remove unused frontend functions identified by static analysis.
         
     Documentation Cleanup:
         Review and update inline comments.
         Ensure all core functions have clear docstrings describing parameters and return types.
         
     

### Patch 0.4.3: The Modernization Update 

Goal: Increase type safety and developer velocity by introducing TypeScript to the frontend. 

     Build Chain Setup:
         Configure the TypeScript compiler and a bundler (e.g., Vite) for the Foundry module.
         Enable allowJs: true to allow JavaScript and TypeScript to coexist during the transition.
         
     Type Definitions:
         Integrate foundry-vtt-types for autocomplete and API safety.
         
     Gradual Migration:
         Migrate high-complexity frontend modules (e.g., the Main HUD, Combat Tracker integration) to TypeScript.
         Apply JSDoc type hints to remaining JavaScript modules to bridge the gap.
         
     Refactoring Safety:
         Verify that the TypeScript compilation step is included in the CI pipeline to catch type errors before merge.
         
     

### Patch 0.5.0: Beta Release (The Open House) 

Goal: Polish the user experience and formalize the project for public consumption and contributors. 

     Documentation Overhaul:
         Create a comprehensive README.md with installation instructions, configuration guides, and a quick-start tutorial.
         Write a CONTRIBUTING.md document explaining the git workflow, how to set up the dev environment, and coding standards (TS/Python linting).
         Add CHANGELOG.md to track user-facing changes per version.
         
     Security Audit:
         Review API key storage and encryption mechanisms.
         Ensure no sensitive credentials are hardcoded.
         
     Bug Bash & Stability:
         Focus effort on fixing issues reported during the automated testing phases.
         Polish error messages in the UI to be user-friendly rather than technical.
         
     Release Candidates:
         Deploy v0.5.0-rc1 to a limited audience for final testing.
         Proceed to full v0.5.0 Beta release.
