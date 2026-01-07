/**
 * The Gold Box - Frontend Delta Service
 * Tracks game state changes (messages, rolls, combat) since last AI turn
 * 
 * Purpose:
 * - Track new messages added to Foundry chat since last AI turn
 * - Track deleted messages removed from Foundry chat since last AI turn
 * - Track new dice rolls executed since last AI turn
 * - Track combat encounters started/ended since last AI turn
 * - Track combat turn advances since last AI turn
 * - Track combatant attribute changes (damage/healing/other) since last AI turn
 * - Provide complete delta object to backend when AI turn button is clicked
 * - Automatically reset all deltas when AI turn completes
 * 
 * Architecture:
 * - Frontend handles ALL delta tracking via Foundry hooks
 * - Smart filtering removes empty/null fields
 * - Frontend sends deltas to backend, backend passes through to AI
 */

export class FrontendDeltaService {
  constructor() {
    // Message tracking
    this.newMessages = 0;
    this.deletedMessages = 0;
    
    // Dice roll tracking
    this.newDiceRolls = [];
    
    // Combat event tracking
    this.encounterStarted = null;
    this.encounterEnded = null;
    
    // NEW: Turn advancement tracking
    this.turnAdvanced = false;
    this.lastTurnNumber = 0;
    this.lastRoundNumber = 0;
    
    // NEW: Combatant attribute change tracking
    this.combatantChanged = null;
    
    // NEW: Scene change tracking (0.3.11)
    this.sceneChanged = null;
    
    // NEW: Token movement tracking (0.3.11)
    this.tokenMoved = null;
    
    // NEW: Scene note update tracking (0.3.11)
    this.sceneNoteUpdated = null;
    
    console.log('The Gold Box: FrontendDeltaService initialized');
  }

  /**
   * Get current delta counts (legacy method for backward compatibility)
   * @deprecated Use getFilteredDelta() instead
   * @returns {Object} Delta counts object with PascalCase field names
   */
  getDeltaCounts() {
    return {
      NewMessages: this.newMessages,
      DeletedMessages: this.deletedMessages
    };
  }

  /**
   * Get complete filtered delta object for backend
   * Smart filtering: only includes fields with actual changes
   * 
   * @returns {Object} Filtered delta object with all tracked changes
   */
  getFilteredDelta() {
    const delta = {
      hasChanges: false
    };
    
    // Add message counts if non-zero
    if (this.newMessages > 0) {
      delta.NewMessages = this.newMessages;
      delta.hasChanges = true;
    }
    if (this.deletedMessages > 0) {
      delta.DeletedMessages = this.deletedMessages;
      delta.hasChanges = true;
    }
    
    // Add dice rolls if any exist
    if (this.newDiceRolls.length > 0) {
      delta.NewDiceRolls = [...this.newDiceRolls];
      delta.hasChanges = true;
    }
    
    // Add combat events if they occurred
    if (this.encounterStarted !== null) {
      delta.EncounterStarted = {...this.encounterStarted};
      delta.hasChanges = true;
    }
    if (this.encounterEnded !== null) {
      delta.EncounterEnded = this.encounterEnded;
      delta.hasChanges = true;
    }
    
    // NEW: Add turn advanced if it occurred
    if (this.turnAdvanced) {
      delta.TurnAdvanced = true;
      delta.LastTurnNumber = this.lastTurnNumber;
      delta.LastRoundNumber = this.lastRoundNumber;
      delta.hasChanges = true;
    }
    
    // NEW: Add combatant changed if it occurred
    if (this.combatantChanged !== null) {
      delta.CombatantChanged = this.combatantChanged;
      delta.hasChanges = true;
    }
    
    // NEW: Add scene changed if it occurred (0.3.11)
    if (this.sceneChanged !== null) {
      delta.SceneChanged = this.sceneChanged;
      delta.hasChanges = true;
    }
    
    // NEW: Add token moved if it occurred (0.3.11)
    if (this.tokenMoved !== null) {
      delta.TokenMoved = this.tokenMoved;
      delta.hasChanges = true;
    }
    
    // NEW: Add scene note updated if it occurred (0.3.11)
    if (this.sceneNoteUpdated !== null) {
      delta.SceneNoteUpdated = this.sceneNoteUpdated;
      delta.hasChanges = true;
    }
    
    // If no changes, add message for clarity
    if (!delta.hasChanges) {
      delta.message = "No changes to game state since last AI turn";
    }
    
    console.log('The Gold Box: Filtered delta object generated:', delta);
    return delta;
  }

  /**
   * Reset all delta counts to zero
   * Called when AI turn completes to prepare for next turn
   */
  resetDeltaCounts() {
    const countsBeforeReset = {
      NewMessages: this.newMessages,
      DeletedMessages: this.deletedMessages,
      NewDiceRolls: this.newDiceRolls.length,
      EncounterStarted: this.encounterStarted,
      EncounterEnded: this.encounterEnded,
      TurnAdvanced: this.turnAdvanced,
      LastTurnNumber: this.lastTurnNumber,
      LastRoundNumber: this.lastRoundNumber,
      CombatantChanged: this.combatantChanged,
      SceneChanged: this.sceneChanged,
      TokenMoved: this.tokenMoved,
      SceneNoteUpdated: this.sceneNoteUpdated
    };
    
    this.newMessages = 0;
    this.deletedMessages = 0;
    this.newDiceRolls = [];
    this.encounterStarted = null;
    this.encounterEnded = null;
    
    // NEW: Reset turn advancement tracking
    this.turnAdvanced = false;
    this.lastTurnNumber = 0;
    this.lastRoundNumber = 0;
    
    // NEW: Reset combatant change tracking
    this.combatantChanged = null;
    
    // NEW: Reset scene change tracking (0.3.11)
    this.sceneChanged = null;
    
    // NEW: Reset token movement tracking (0.3.11)
    this.tokenMoved = null;
    
    // NEW: Reset scene note update tracking (0.3.11)
    this.sceneNoteUpdated = null;
    
    console.log(`The Gold Box: Delta counts reset. Before reset:`, countsBeforeReset);
  }

  /**
   * Increment new messages counter
   * Called when a message is created in Foundry
   */
  incrementNewMessages() {
    this.newMessages++;
    console.log(`The Gold Box: New message detected. Total new messages: ${this.newMessages}`);
  }

  /**
   * Increment deleted messages counter
   * Called when a message is deleted from Foundry
   */
  incrementDeletedMessages() {
    this.deletedMessages++;
    console.log(`The Gold Box: Deleted message detected. Total deleted messages: ${this.deletedMessages}`);
  }

  /**
   * Add a dice roll to delta tracking
   * Called when a dice roll is executed in Foundry
   * 
   * @param {Object} rollData - Roll data object
   * @param {string} rollData.formula - Dice formula (e.g., "1d20+5")
   * @param {number} rollData.result - Total result of the roll
   * @param {string} rollData.flavor - Flavor text for the roll
   */
  addDiceRoll(rollData) {
    this.newDiceRolls.push({
      formula: rollData.formula,
      result: rollData.result,
      flavor: rollData.flavor || '',
      timestamp: Date.now()
    });
    console.log(`The Gold Box: Dice roll detected: ${rollData.formula} = ${rollData.result}`);
  }

  /**
   * Record that an encounter has started
   * Called by CombatMonitor when combat begins
   * 
   * @param {Object} combatData - Combat encounter data
   * @param {string} combatData.id - Combat encounter ID
   * @param {string} combatData.name - Combat encounter name
   */
  setEncounterStarted(combatData) {
    this.encounterStarted = {
      id: combatData.id,
      name: combatData.name
    };
    this.encounterEnded = null; // Reset ended flag
    console.log(`The Gold Box: Encounter started: ${combatData.name} (${combatData.id})`);
  }

  /**
   * Record that an encounter has ended
   * Called by CombatMonitor when combat ends
   * 
   * @param {boolean} ended - Always true when called
   */
  setEncounterEnded(ended = true) {
    if (ended) {
      this.encounterEnded = true;
      this.encounterStarted = null; // Reset started flag
      console.log('The Gold Box: Encounter ended');
    }
  }

  /**
   * Record that combat turn has advanced
   * Called by CombatMonitor when turn advances
   * 
   * @param {number} round - Current round number
   * @param {number} turn - Current turn number (1-based)
   */
  setTurnAdvanced(round, turn) {
    // Only set turnAdvanced if turn actually changed
    if (round !== this.lastRoundNumber || turn !== this.lastTurnNumber) {
      this.turnAdvanced = true;
      this.lastRoundNumber = round;
      this.lastTurnNumber = turn;
      console.log(`The Gold Box: Turn advanced to round ${round}, turn ${turn}`);
    }
  }

  /**
   * Record that a combatant's attributes have changed
   * Called by CombatMonitor when combatant attributes change
   * 
   * @param {Object} combatantData - Combatant change data
   * @param {string} combatantData.tokenId - Token ID
   * @param {string} combatantData.attributePath - Attribute path that changed
   * @param {any} combatantData.oldValue - Previous value
   * @param {any} combatantData.newValue - New value
   * @param {string} combatantData.changeType - Type of change (damage/healing/other)
   */
  setCombatantChanged(combatantData) {
    this.combatantChanged = {
      token_id: combatantData.tokenId,
      attribute_path: combatantData.attributePath,
      old_value: combatantData.oldValue,
      new_value: combatantData.newValue,
      change_type: combatantData.changeType
    };
    console.log(`The Gold Box: Combatant changed: token ${combatantData.tokenId}, path ${combatantData.attributePath}, ${combatantData.changeType}`);
  }

  /**
   * Record that the active scene has changed (0.3.11)
   * Called when the GM switches to a different scene
   * 
   * @param {Object} sceneData - Scene change data
   * @param {string} sceneData.scene_id - New scene ID
   * @param {string} sceneData.scene_name - New scene name
   */
  setSceneChanged(sceneData) {
    this.sceneChanged = {
      new_scene_id: sceneData.scene_id,
      new_scene_name: sceneData.scene_name
    };
    console.log(`The Gold Box: Scene changed to: ${sceneData.scene_name} (${sceneData.scene_id})`);
  }

  /**
   * Record that a token has moved (0.3.11)
   * Called when a token's position changes on the scene
   * 
   * @param {Object} tokenData - Token movement data
   * @param {string} tokenData.token_id - Token ID that moved
   * @param {Object} tokenData.old_position - Previous position {x, y}
   * @param {Object} tokenData.new_position - New position {x, y}
   */
  setTokenMoved(tokenData) {
    this.tokenMoved = {
      token_id: tokenData.token_id,
      old_position: tokenData.old_position,
      new_position: tokenData.new_position
    };
    console.log(`The Gold Box: Token moved: ${tokenData.token_id} from (${tokenData.old_position.x}, ${tokenData.old_position.y}) to (${tokenData.new_position.x}, ${tokenData.new_position.y})`);
  }

  /**
   * Record that a scene note has been updated (0.3.11)
   * Called when a journal note pinned to the scene is updated
   * 
   * @param {Object} noteData - Note update data
   * @param {string} noteData.note_id - Note ID that was updated
   * @param {string} noteData.entry_name - Name of the journal entry
   * @param {Object} noteData.position - Note position {x, y}
   */
  setSceneNoteUpdated(noteData) {
    this.sceneNoteUpdated = {
      note_id: noteData.note_id,
      entry_name: noteData.entry_name,
      position: noteData.position
    };
    console.log(`The Gold Box: Scene note updated: ${noteData.entry_name} (${noteData.note_id}) at (${noteData.position.x}, ${noteData.position.y})`);
  }
}

// Create global instance and attach to window
if (!window.FrontendDeltaService) {
  window.FrontendDeltaService = new FrontendDeltaService();
  console.log('The Gold Box: FrontendDeltaService attached to window');
}

// Register Foundry hooks for message tracking
Hooks.on('createChatMessage', (chatMessage) => {
  // Only increment counter for user-created messages, not AI-generated messages
  // AI-generated messages have flags['gold-box']?.isAIMessage flag
  const isAIMessage = chatMessage.flags?.['gold-box']?.isAIMessage;
  if (!isAIMessage) {
    window.FrontendDeltaService?.incrementNewMessages();
    
    // Check if this is a dice roll message
    if (chatMessage.isRoll && chatMessage.rolls) {
      // Extract roll data from message
      const roll = chatMessage.rolls[0];
      if (roll) {
        const rollData = {
          formula: roll.formula || chatMessage.getRollData().formula || 'Unknown',
          result: roll.total || roll.total,
          flavor: chatMessage.flavor || ''
        };
        window.FrontendDeltaService?.addDiceRoll(rollData);
      }
    }
  }
});

Hooks.on('deleteChatMessage', (document, options) => {
  // Only increment counter for user-created messages, not AI-generated messages
  const isAIMessage = document.flags?.['gold-box']?.isAIMessage;
  if (!isAIMessage) {
    window.FrontendDeltaService?.incrementDeletedMessages();
  }
});

// NEW: Track scene changes (0.3.11)
Hooks.on('updateScene', (scene, data, options, userId) => {
  // Only track when scene actually changes (active scene switch)
  if (scene.active && (data.initial !== undefined || data.active !== undefined)) {
    window.FrontendDeltaService?.setSceneChanged({
      scene_id: scene.id,
      scene_name: scene.name
    });
  }
});

// NEW: Track token movements (0.3.11)
Hooks.on('updateToken', (token, data, options, userId) => {
  // Only track when token position changes (x or y coordinates)
  if (data.x !== undefined || data.y !== undefined) {
    window.FrontendDeltaService?.setTokenMoved({
      token_id: token.id,
      old_position: {
        x: data._source?.x ?? token.document._source?.x ?? token.x,
        y: data._source?.y ?? token.document._source?.y ?? token.y
      },
      new_position: {
        x: token.x,
        y: token.y
      }
    });
  }
});

// NEW: Track scene note updates (0.3.11)
Hooks.on('updateNote', (note, data, options, userId) => {
  // Get journal entry name for the note
  const journalEntry = game?.journal?.get(note.entryId);
  window.FrontendDeltaService?.setSceneNoteUpdated({
    note_id: note.id,
    entry_name: journalEntry?.name || 'Unknown Note',
    position: {
      x: note.x,
      y: note.y
    }
  });
});

console.log('The Gold Box: Frontend delta service loaded and Foundry hooks registered');
