/**
 * Combat Monitor for The Gold Box
 * Monitors Foundry combat encounters and provides combat state to backend
 * Uses on-demand pattern: frontend asks "are we in combat?" when AI turn is requested
 */

class CombatMonitor {
    constructor() {
        this.combatState = {
            in_combat: false,
            combat_id: null,
            round: 0,
            turn: 0,
            combatants: []
        };
        
        this.cachedCombatData = null;
        this.lastCombatCheck = 0;
        this.lastRequestId = null;  // Track the last request_id
        
        // Initialize combat event listeners
        this.initCombatListeners();
        
        console.log("Combat Monitor initialized");
    }
    
    /**
     * Register WebSocket message handlers for encounter management
     * Called when WebSocket client is available
     */
    registerWebSocketHandlers() {
        // Get WebSocket client reference
        const wsClient = window.goldBox?.webSocketClient;
        
        if (!wsClient) {
            console.warn('Combat Monitor: WebSocket client not available, will retry...');
            return false;
        }
        
        console.log('Combat Monitor: Registering encounter management handlers');
        
        // Handler for create_encounter messages
        wsClient.onMessageType('create_encounter', async (message) => {
            console.log('Combat Monitor: Received create_encounter request', message);
            
            try {
                const actorIds = message.data?.actor_ids;
                const rollInitiative = message.data?.roll_initiative !== false; // Default to true
                const requestId = message.request_id;  // Capture request_id
                
                if (!actorIds || !Array.isArray(actorIds) || actorIds.length ===0) {
                    console.error('Combat Monitor: Invalid actor_ids in create_encounter request');
                    return;
                }
                
                // Store request_id so transmitCombatState can include it
                this.lastRequestId = requestId;
                
                // REMOVED: Blocking check for active combat - Foundry supports multiple encounters via game.combats
                // Combat is automatically added to game.combats collection upon creation
                
                // Create combat with specified actors
                const combatData = {
                    combatants: actorIds.map(actorId => ({
                        actorId: actorId
                    }))
                };
                
                const combat = await Combat.create(combatData);
                const newCombatId = combat._id;  // ← CAPTURE NEW COMBAT ID
                console.log('Combat Monitor: Combat created with ID:', newCombatId);
                
                // Roll initiative if requested with smart timeout fallback
                if (rollInitiative) {
                    console.log('Combat Monitor: Attempting automatic initiative rolling with timeout fallback');
                    
                    try {
                        // Try to roll initiative with 3-second timeout
                        // If system supports automatic initiative, it will complete quickly
                        // If system blocks with dialog, timeout will trigger and we proceed without initiative
                        const initiativePromise = combat.rollAll();
                        const timeoutPromise = new Promise((_, reject) => 
                            setTimeout(() => reject(new Error('Initiative roll timed out after 3 seconds - likely blocked by dialog')), 3000)
                        );
                        
                        await Promise.race([initiativePromise, timeoutPromise]);
                        
                        // Initiative rolled successfully within timeout - advance to first turn
                        await combat.nextRound();
                        console.log('Combat Monitor: Initiative rolled successfully, advanced to turn 1');
                        
                    } catch (error) {
                        // Initiative roll was blocked by dialog or timed out
                        // Proceed with blank initiatives - users can roll manually if needed
                        console.log('Combat Monitor: Initiative roll blocked/timed out, proceeding with blank initiatives:', error.message);
                        
                        // Combat is still created and active, just without initiative values
                        // System will update when users enter initiative manually
                    }
                }
                
                // FIXED: Send immediate response with NEW combat_id (not all encounters)
                // This ensures backend gets the specific combat that was just created
                const responseMessage = {
                    type: 'combat_state',
                    request_id: requestId,
                    data: {
                        combat_state: {
                            in_combat: true,
                            combat_id: newCombatId,  // ← Return NEW combat's ID
                            round: combat.round || 0,
                            turn: combat.turn || 0,
                            combatants: combat.setupTurns().map(c => ({
                                name: c.name || 'Unknown',
                                token_id: c.tokenId,
                                actor_uuid: c.actorUuid,
                                initiative: c.initiative || 0,
                                is_player: c.hasPlayerOwner || false,
                                is_current_turn: false  // Combat just created, no current turn yet
                            })),
                            last_updated: Date.now()
                        }
                    }
                };
                
                await wsClient.send(responseMessage);
                console.log('Combat Monitor: Sent immediate response for new combat:', newCombatId);
                
            } catch (error) {
                console.error('Combat Monitor: Error handling create_encounter:', error);
            }
        });
        
        // Handler for delete_encounter messages
        wsClient.onMessageType('delete_encounter', async (message) => {
            console.log('Combat Monitor: Received delete_encounter request', message);
            
            try {
                const requestId = message.request_id;
                const encounterId = message.data?.encounter_id;
                const combat = encounterId ? game.combats?.get(encounterId) : null;
                
                if (!combat) {
                    console.warn('Combat Monitor: Encounter not found for deletion:', encounterId);
                    // Send immediate response even if combat not found
                    const responseMessage = {
                        type: 'combat_state',
                        request_id: requestId,
                        data: {
                            combat_state: {
                                in_combat: false,
                                combat_id: encounterId,  // Include the attempted encounter_id
                                round: 0,
                                turn: 0,
                                combatants: [],
                                last_updated: Date.now()
                            }
                        }
                    };
                    await wsClient.send(responseMessage);
                    console.log('Combat Monitor: Sent immediate response for non-existent combat deletion');
                    return;
                }
                
                // FIXED: Delete combat FIRST, then send response
                // This ensures the combat is actually gone when we send the response
                await combat.delete();
                console.log('Combat Monitor: Combat deleted:', encounterId);
                
                // Wait longer for Foundry to fully update after deletion
                await new Promise(resolve => setTimeout(resolve, 500));
                
                // Get updated combat state after deletion
                const allCombats = game.combats ? Array.from(game.combats.values()) : [];
                const activeCombatId = game.combat ? game.combat._id : null;
                
                // FIXED: Send response with single combat_state for most recent encounter
                // This ensures backend receives the expected message format to resolve futures
                const encounterStates = allCombats.filter(c => c.started).map(combat => {
                    const combatantsArray = combat.setupTurns() || [];
                    
                    // Determine current turn
                    let currentTurnId = null;
                    let effectiveTurn = 0;
                    
                    if (combat.round === 0 && (combat.turn === null || combat.turn === undefined)) {
                        if (combatantsArray.length > 0) {
                            currentTurnId = combatantsArray[0]._id;
                            effectiveTurn = 0;
                        }
                    } else if (combatantsArray.length > 0) {
                        effectiveTurn = combat.turn || 0;
                        if (effectiveTurn < combatantsArray.length) {
                            currentTurnId = combatantsArray[effectiveTurn]._id;
                        }
                    }
                    
                    const combatants = combatantsArray.map(c => ({
                        name: c.name || 'Unknown',
                        token_id: c.tokenId,
                        actor_uuid: c.actorUuid,
                        initiative: c.initiative || 0,
                        is_player: c.hasPlayerOwner || false,
                        is_current_turn: currentTurnId === c._id
                    }));
                    
                    return {
                        in_combat: true,
                        combat_id: combat._id,
                        is_active: combat._id === activeCombatId,
                        round: combat.round || 0,
                        turn: effectiveTurn + 1,
                        combatants: combatants,
                        last_updated: Date.now()
                    };
                });
                
                // Use most recently updated encounter (or first if no active)
                const mostRecentEncounter = encounterStates.length > 0 
                    ? encounterStates.reduce((a, b) => (a.last_updated > b.last_updated ? a : b))
                    : null;
                
                const responseMessage = {
                    type: 'combat_state',
                    request_id: requestId,
                    data: {
                        combat_state: mostRecentEncounter || {
                            in_combat: false,
                            combat_id: null,
                            round: 0,
                            turn: 0,
                            combatants: [],
                            last_updated: Date.now()
                        }
                    }
                };
                
                await wsClient.send(responseMessage);
                console.log('Combat Monitor: Sent response after deletion with updated combat state');
                
            } catch (error) {
                console.error('Combat Monitor: Error handling delete_encounter:', error);
            }
        });
        
        // Handler for advance_turn messages
        wsClient.onMessageType('advance_turn', async (message) => {
            console.log('Combat Monitor: Received advance_turn request', message);
            
            try {
                const requestId = message.request_id;
                const encounterId = message.data?.encounter_id;
                const combat = encounterId ? game.combats?.get(encounterId) : null;
                
                if (!combat) {
                    console.warn('Combat Monitor: Encounter not found for turn advancement:', encounterId);
                    // Send immediate response even if combat not found
                    const responseMessage = {
                        type: 'combat_state',
                        request_id: requestId,
                        data: {
                            combat_state: {
                                in_combat: false,
                                combat_id: null,
                                round: 0,
                                turn: 0,
                                combatants: [],
                                last_updated: Date.now()
                            }
                        }
                    };
                    await wsClient.send(responseMessage);
                    console.log('Combat Monitor: Sent immediate response for non-existent combat turn advancement');
                    return;
                }
                
                // Advance to next turn using Foundry's native API
                await combat.nextTurn();
                console.log('Combat Monitor: Advanced to next turn for encounter:', encounterId);
                
                // Wait a moment for Foundry to update combat state and fire hooks
                // This ensures we capture updated turn information
                await new Promise(resolve => setTimeout(resolve, 100));
                
                // FIXED: Send immediate response with updated combat state
                const combatantsArray = combat.setupTurns() || [];
                let currentTurnId = null;
                let effectiveTurn = 0;
                
                if (combat.round === 0 && (combat.turn === null || combat.turn === undefined)) {
                    if (combatantsArray.length > 0) {
                        currentTurnId = combatantsArray[0]._id;
                        effectiveTurn = 0;
                    }
                } else if (combatantsArray.length > 0) {
                    effectiveTurn = combat.turn || 0;
                    if (effectiveTurn < combatantsArray.length) {
                        currentTurnId = combatantsArray[effectiveTurn]._id;
                    }
                }
                
                const combatants = combatantsArray.map(c => ({
                    name: c.name || 'Unknown',
                    token_id: c.tokenId,
                    actor_uuid: c.actorUuid,
                    initiative: c.initiative || 0,
                    is_player: c.hasPlayerOwner || false,
                    is_current_turn: currentTurnId === c._id
                }));
                
                const responseMessage = {
                    type: 'combat_state',
                    request_id: requestId,
                    data: {
                        combat_state: {
                            in_combat: true,
                            combat_id: combat._id,
                            round: combat.round || 0,
                            turn: effectiveTurn + 1,
                            combatants: combatants,
                            last_updated: Date.now()
                        }
                    }
                };
                
                await wsClient.send(responseMessage);
                console.log('Combat Monitor: Sent immediate response for turn advancement');
                
            } catch (error) {
                console.error('Combat Monitor: Error handling advance_turn:', error);
            }
        });
        
        // Handler for activate_combat messages
        wsClient.onMessageType('activate_combat', async (message) => {
            console.log('Combat Monitor: Received activate_combat request', message);
            
            try {
                // Store request_id so transmitCombatState can include it
                const requestId = message.request_id;
                if (requestId) {
                    this.lastRequestId = requestId;
                    console.log('Combat Monitor: Stored request_id for activate_combat:', requestId);
                }
                
                // Look up combat by ID from game.combats collection
                const encounterId = message.data?.encounter_id;
                const combat = encounterId ? game.combats?.get(encounterId) : null;
                
                if (!combat) {
                    console.warn('Combat Monitor: Encounter not found for activation:', encounterId);
                    // Transmit current combat state
                    await this.transmitCombatState();
                    return;
                }
                
                // Activate the combat encounter
                await combat.activate();
                console.log('Combat Monitor: Combat activated:', encounterId);
                
                // Wait a moment for Foundry to update
                await new Promise(resolve => setTimeout(resolve, 100));
                
                // Transmit updated combat state
                await this.transmitCombatState();
                
            } catch (error) {
                console.error('Combat Monitor: Error handling activate_combat:', error);
            }
        });
        
        console.log('Combat Monitor: WebSocket encounter management handlers initialized');
    }
    
    /**
     * Initialize Foundry combat event listeners
     */
    initCombatListeners() {
        // WebSocket handlers will be registered separately when WebSocket client is available
        // Don't register here to avoid race condition where WebSocket client isn't ready yet
        
        // Listen for combat create events
        Hooks.on('createCombat', (combat) => {
            console.log('Combat created:', combat);
            this.updateCombatState(combat);
            // Track combat start in delta service
            if (window.FrontendDeltaService && combat && combat._id) {
                window.FrontendDeltaService.setEncounterStarted({
                    id: combat._id,
                    name: combat.name || 'Combat Encounter'
                });
            }
        });
        
        // Listen for combat delete events
        Hooks.on('deleteCombat', (combat) => {
            console.log('Combat deleted:', combat);
            this.clearCombatState();
            // Track combat end in delta service
            if (window.FrontendDeltaService) {
                window.FrontendDeltaService.setEncounterEnded(true);
            }
        });
        
        // Listen for combat round events
        // Note: When a new round starts, combatTurn hook does NOT fire with turn 0
        // It starts firing from turn 1, so we MUST use combatRound to capture turn 0
        Hooks.on('combatRound', (combat, round) => {
            console.log('Combat round:', combat, round);
            // When new round starts, first combatant is index 0
            // Pass turn 0 explicitly since combatTurn won't fire with it
            // Force a small delay to ensure Foundry has updated combat.turn
            setTimeout(() => {
                this.updateCombatState(combat, 0);
            }, 50);
        });
        
        // Listen for combat turn events
        // Note: Second parameter is a context object {round, turn, direction, worldTime}
        // This fires for turns 1, 2, 3, etc. (does NOT fire for turn 0)
        // combatRound hook handles turn 0 (first combatant of new round)
        Hooks.on('combatTurn', (combat, context, combatant) => {
            console.log('Combat turn:', combat, context, combatant);
            // Always use context.turn (0-based index) - this is always accurate
            this.updateCombatState(combat, context?.turn);
        });
        
        // Listen for combatant updates
        // Note: Hook passes combatant as first param, not combat object - use game.combat
        Hooks.on('updateCombatant', (document, data, options, userId) => {
            console.log('Combatant updated:', document, data);
            // Always use game.combat to get the full combat state with all combatants
            this.updateCombatState(game.combat);
        });
        
        // Listen for combatant creation events
        Hooks.on('createCombatant', (document, data, options, userId) => {
            console.log('Combatant created:', document);
            // Always use game.combat to get the full combat state with all combatants
            this.updateCombatState(game.combat);
        });
        
        // Listen for combatant deletion events
        Hooks.on('deleteCombatant', (document, options, userId) => {
            console.log('Combatant deleted:', document);
            // Always use game.combat to get the full combat state with all combatants
            this.updateCombatState(game.combat);
        });
    }
    
    /**
     * Update combat state from Foundry combat object
     * @param {Combat} combat - Foundry combat object (optional, will use game.combat if not provided)
     * @param {number} turnIndex - Optional turn index from combatTurn hook (0-based, indicates which turn is starting)
     */
    updateCombatState(combat = null, turnIndex = null) {
        try {
            // Use game.combat if no combat object provided (hook may pass incomplete object)
            const combatObj = combat || game.combat;
            
            // Safety check: ensure combat object is valid (combatants may be initializing)
            if (!combatObj || combatObj._id === undefined) {
                if (!combatObj) {
                    this.clearCombatState();  // Also clears cachedCombatData
                }
                return;
            }
            
            // Use Foundry's pre-sorted turn order (setupTurns() returns combatants sorted by initiative)
            // This works for all game systems (D&D 5e, Pathfinder, etc.)
            const combatantsArray = combatObj.setupTurns() || [];
            
            // Cache combat data before sending to avoid race conditions
            // This ensures backend always receives complete combat state with valid combat_id
            this.cachedCombatData = {
                combat_id: combatObj._id,
                round: combatObj.round,
                turn: combatObj.turn,
                combatants: combatantsArray,
                last_updated: Date.now()
            };
            
            // Debug: Log combat object structure to find correct current turn property
            console.log('Combat object structure:', {
                combat_id: combatObj._id,
                current: combatObj.current,
                turn: combatObj.turn,
                combatant_count: combatantsArray.length,
                combatant_ids: combatantsArray.map(c => ({ name: c.name, id: c._id }))
            });
            
            // Get current turn combatant ID
            // PRIORITY 1: Use turnIndex from hook (ALWAYS reliable, even for round start at turn 0)
            // PRIORITY 2: Fall back to combatObj.current (only for initial load)
            // PRIORITY 3: Special case - combat just started, no turn has begun yet (round 0, turn null)
            let currentTurnId = null;
            let effectiveTurn = 0;
            
            // Special case: Combat just started, no turn has begun yet (round 0, turn null)
            // Default to first combatant in Foundry's turn order
            if (combatObj.round === 0 && (combatObj.turn === null || combatObj.turn === undefined)) {
                if (combatantsArray.length > 0) {
                    currentTurnId = combatantsArray[0]._id;
                    effectiveTurn = 0;
                    console.log('Combat just started, defaulting to first combatant:', combatantsArray[0].name);
                }
            }
            // Use hook turn index whenever available (includes round start at turn 0)
            else if (turnIndex !== null && turnIndex !== undefined && typeof turnIndex === 'number' && combatantsArray.length > 0) {
                effectiveTurn = turnIndex;
                const currentCombatant = combatantsArray[effectiveTurn];
                if (currentCombatant) {
                    currentTurnId = currentCombatant._id;
                    console.log('Using hook turn index', turnIndex, ':', currentCombatant.name, 'ID:', currentTurnId);
                }
            }
            // Only fall back to combatObj.current for initial load (when no turnIndex provided)
            else {
                // For initial load or non-turn events, use combatObj.current
                if (combatObj.current && combatObj.current.combatantId) {
                    currentTurnId = combatObj.current.combatantId;
                    // Calculate turn number by finding current combatant's position in turns array
                    const currentIndex = combatantsArray.findIndex(c => c._id === currentTurnId);
                    if (currentIndex !== -1) {
                        effectiveTurn = currentIndex;
                    }
                    console.log('Using combat.current.combatantId:', currentTurnId, 'at index:', effectiveTurn);
                } else if (combatObj.current && typeof combatObj.current === 'string') {
                    currentTurnId = combatObj.current;
                    const currentIndex = combatantsArray.findIndex(c => c._id === currentTurnId);
                    if (currentIndex !== -1) {
                        effectiveTurn = currentIndex;
                    }
                    console.log('Using combat.current as combatant ID:', currentTurnId, 'at index:', effectiveTurn);
                }
            }
            
            // Get current combat data from Foundry in the order Foundry is using
            // Include token_id and actor_uuid for token attribute management
            const combatants = combatantsArray.map(c => ({
                name: c.name || 'Unknown',
                token_id: c.tokenId,  // Token UUID for attribute modification
                actor_uuid: c.actorUuid,  // Token-specific actor UUID for queries
                initiative: c.initiative || 0,
                is_player: c.hasPlayerOwner || false,
                is_current_turn: currentTurnId === c._id
            }));
            
            // NO SORTING - Keep Foundry's order for AI context
            // Debug: Log current turn detection
            const currentCombatant = combatants.find(c => c.is_current_turn);
            console.log('Current turn combatant:', currentCombatant ? currentCombatant.name : 'None');
            console.log('All combatants with turn flags:', combatants.map(c => `${c.name}: ${c.is_current_turn}`));
            
            this.combatState = {
                in_combat: true,
                combat_id: combatObj._id,
                round: combatObj.round || 0,
                // Convert 0-based index to 1-based turn number for reporting
                turn: effectiveTurn + 1,
                combatants: combatants
            };
            
            this.cachedCombatData = { ...this.combatState };
            this.lastCombatCheck = Date.now();
            
            console.log('Combat state updated:', this.combatState);
            
            // Removed automatic transmission - state only transmitted on explicit combat_state_refresh request
            
        } catch (error) {
            console.error('Error updating combat state:', error);
            this.clearCombatState();
        }
    }
    
    /**
     * Clear combat state when combat ends
     */
    clearCombatState() {
        this.combatState = {
            in_combat: false,
            combat_id: null,
            round: 0,
            turn: 0,
            combatants: []
        };
        
        this.cachedCombatData = null;
        this.lastCombatCheck = Date.now();
        
        console.log('Combat state cleared');
        
        // Removed automatic transmission - state only transmitted on explicit combat_state_refresh request
    }
    
    /**
     * Get current combat state (on-demand pattern)
     * @param {boolean} forceRefresh - Force refresh from Foundry even if cache is recent
     * @returns {Object} Current combat state
     */
    getCurrentCombatState(forceRefresh = false) {
        // Force refresh if requested or if cache is old (more than 5 seconds)
        if (forceRefresh || Date.now() - this.lastCombatCheck > 5000) {
            this.refreshCombatState();
        }
        
        return { ...this.combatState };
    }
    
    /**
     * Refresh combat state from current Foundry combat
     */
    refreshCombatState() {
        try {
            const combat = game.combat;
            if (combat) {
                this.updateCombatState(combat);
            } else {
                this.clearCombatState();
            }
        } catch (error) {
            console.error('Error refreshing combat state:', error);
            this.clearCombatState();
        }
    }
    
    /**
     * Transmit combat state to backend
     * Handles both direct combat state and responses to refresh requests
     * @param {Object} combatState - The combat state to transmit
     * @param {string|null} requestId - Optional request ID if responding to a refresh request
     */
    transmitCombatState(combatState, requestId = null) {
        // Get Gold Box WebSocket client instance
        const wsClient = window.goldBox?.webSocketClient;
        
        if (!wsClient || !wsClient.isConnected) {
            console.log('Combat Monitor: WebSocket client not available or not connected, skipping combat state transmission');
            return;
        }
        
        // Get ALL encounters from game.combats collection
        const allCombats = game.combats ? Array.from(game.combats.values()) : [];
        const activeCombatId = game.combat ? game.combat._id : null;
        
        // Build combat state for all encounters
        const encounterStates = allCombats.filter(c => c.started).map(combat => {
            const combatantsArray = combat.setupTurns() || [];
            
                // Determine current turn
                let currentTurnId = null;
                let effectiveTurn = 0;
                
                if (combat.round === 0 && (combat.turn === null || combat.turn === undefined)) {
                    if (combatantsArray.length > 0) {
                        currentTurnId = combatantsArray[0]._id;
                        effectiveTurn = 0;
                    }
                } else if (combatantsArray.length > 0) {
                    effectiveTurn = combat.turn || 0;
                    if (effectiveTurn < combatantsArray.length) {
                        currentTurnId = combatantsArray[effectiveTurn]._id;
                    }
                }

                const combatants = combatantsArray.map(c => ({
                    name: c.name || 'Unknown',
                    token_id: c.tokenId,
                    actor_uuid: c.actorUuid,
                    initiative: c.initiative || 0,
                    is_player: c.hasPlayerOwner || false,
                    is_current_turn: currentTurnId === c._id
                }));
            
            return {
                in_combat: true,
                combat_id: combat._id,
                is_active: combat._id === activeCombatId,
                round: combat.round || 0,
                turn: effectiveTurn + 1,
                combatants: combatants,
                last_updated: Date.now()
            };
        });
        
        // Build message with all encounters
        const message = {
            type: 'combat_state',
            request_id: requestId || this.lastRequestId,  // Use provided requestId or fall back to lastRequestId
            data: combatState ? {
                combat_state: combatState
            } : {
                encounters: encounterStates,
                active_combat_id: activeCombatId,
                timestamp: Date.now()
            }
        };
        
        wsClient.send(message);
        console.log('Combat Monitor: Transmitted combat state to backend:', 
                    (combatState ? 'single combat state' : `${encounterStates.length} encounters`), 
                    'active:', activeCombatId);
    }
    
    /**
     * Check if a specific combatant's turn is active
     * @param {string} combatantName - Name of combatant to check
     * @returns {boolean} True if it's their turn
     */
    isCombatantTurn(combatantName) {
        const currentTurn = this.getCurrentTurn();
        return currentTurn && currentTurn.name === combatantName;
    }
    
    /**
     * Get current turn combatant
     * @returns {Object|null} Current turn combatant or null if not in combat
     */
    getCurrentTurn() {
        if (!this.combatState.in_combat || !this.combatState.combatants) {
            return null;
        }
        return this.combatState.combatants.find(c => c.is_current_turn) || null;
    }
    
    /**
     * Get combat state for backend integration
     * @param {boolean} forceRefresh - Force refresh from Foundry even if cache is recent
     * @returns {Object} Combat state formatted for backend
     */
    getCombatStateForBackend(forceRefresh = false) {
        // Force refresh to ensure we have the latest turn information
        if (forceRefresh) {
            this.refreshCombatState();
        }
        
        return {
            in_combat: this.combatState.in_combat,
            combat_id: this.combatState.combat_id,
            round: this.combatState.round,
            turn: this.combatState.turn,
            combatants: this.combatState.combatants,
            last_updated: Date.now()
        };
    }
}

// Export for global access
window.CombatMonitor = CombatMonitor;

// Auto-initialize when module is ready
Hooks.once('ready', () => {
    window.CombatMonitor = new CombatMonitor();
    
    // NEW: Capture combat state if combat was already active before module loaded
    if (game.combat) {
        console.log('Combat detected during module load - capturing initial state');
        window.CombatMonitor.updateCombatState(game.combat);
    }
});
