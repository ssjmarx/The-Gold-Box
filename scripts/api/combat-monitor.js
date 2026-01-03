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
        this.lastRequestId = null;  // Track the last create_encounter request_id
        
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
                const requestId = message.request_id;  // Capture the request_id
                
                if (!actorIds || !Array.isArray(actorIds) || actorIds.length === 0) {
                    console.error('Combat Monitor: Invalid actor_ids in create_encounter request');
                    return;
                }
                
                // Store the request_id so transmitCombatState can include it
                this.lastRequestId = requestId;
                
                // Check if combat is already active
                if (game.combat && game.combat.started) {
                    console.warn('Combat Monitor: Combat already active, cannot create new encounter');
                    // Send error response instead of combat state
                    const wsClient = window.goldBox?.webSocketClient;
                    if (wsClient && wsClient.isConnected) {
                        const errorMessage = {
                            type: 'error',
                            request_id: requestId,  // Include request_id for correlation
                            data: {
                                error: 'Combat encounter already active',
                                error_code: 'COMBAT_ALREADY_ACTIVE'
                            },
                            timestamp: Date.now()
                        };
                        await wsClient.send(errorMessage);
                        console.log('Combat Monitor: Sent error response for create_encounter:', errorMessage);
                    }
                    return;
                }
                
                // Create combat with specified actors
                const combatData = {
                    combatants: actorIds.map(actorId => ({
                        actorId: actorId
                    }))
                };
                
                const combat = await Combat.create(combatData);
                console.log('Combat Monitor: Combat created with', actorIds.length, 'combatants');
                
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
                
                // Transmit combat state immediately (with or without initiative values)
                await this.transmitCombatState();
                
            } catch (error) {
                console.error('Combat Monitor: Error handling create_encounter:', error);
            }
        });
        
        // Handler for delete_encounter messages
        wsClient.onMessageType('delete_encounter', async (message) => {
            console.log('Combat Monitor: Received delete_encounter request', message);
            
            try {
                // Store request_id so transmitCombatState can include it
                const requestId = message.request_id;
                if (requestId) {
                    this.lastRequestId = requestId;
                    console.log('Combat Monitor: Stored request_id for delete_encounter:', requestId);
                }
                
                // Check if combat is active
                if (!game.combat || !game.combat.started) {
                    console.warn('Combat Monitor: No active combat to end');
                    // Transmit current combat state (should show in_combat: false)
                    await this.transmitCombatState();
                    return;
                }
                
                // Delete combat directly (bypasses confirmation dialog)
                await game.combat.delete();
                console.log('Combat Monitor: Combat deleted');
                
                // Transmit updated combat state (should show in_combat: false)
                await this.transmitCombatState();
                
            } catch (error) {
                console.error('Combat Monitor: Error handling delete_encounter:', error);
            }
        });
        
        // Handler for advance_turn messages
        wsClient.onMessageType('advance_turn', async (message) => {
            console.log('Combat Monitor: Received advance_turn request', message);
            
            try {
                // Store request_id so transmitCombatState can include it
                const requestId = message.request_id;
                if (requestId) {
                    this.lastRequestId = requestId;
                    console.log('Combat Monitor: Stored request_id for advance_turn:', requestId);
                }
                
                // Check if combat is active
                if (!game.combat || !game.combat.started) {
                    console.warn('Combat Monitor: No active combat to advance');
                    // Transmit current combat state (should show in_combat: false)
                    await this.transmitCombatState();
                    return;
                }
                
                // Advance to next turn using Foundry's native API
                await game.combat.nextTurn();
                console.log('Combat Monitor: Advanced to next turn');
                
                // Wait a moment for Foundry to update combat state and fire hooks
                // This ensures we capture the updated turn information
                await new Promise(resolve => setTimeout(resolve, 100));
                
                // Transmit updated combat state
                await this.transmitCombatState();
                
            } catch (error) {
                console.error('Combat Monitor: Error handling advance_turn:', error);
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
            // Default to the first combatant in Foundry's turn order
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
     * Get current turn information
     * @returns {Object|null} Current turn combatant or null
     */
    getCurrentTurn() {
        if (!this.combatState.in_combat) {
            return null;
        }
        
        return this.combatState.combatants.find(c => c.is_current_turn) || null;
    }
    
    /**
     * Get turn order with initiative values
     * @returns {Array} Sorted combatants by initiative
     */
    getTurnOrder() {
        if (!this.combatState.in_combat) {
            return [];
        }
        
        return [...this.combatState.combatants].sort((a, b) => b.initiative - a.initiative);
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
    
    /**
     * Transmit combat state to backend via WebSocket
     */
    async transmitCombatState() {
        try {
            // Get Gold Box WebSocket client instance
            const wsClient = window.goldBox?.webSocketClient;
            
            if (!wsClient || !wsClient.isConnected) {
                console.log('Combat Monitor: WebSocket client not available or not connected, skipping combat state transmission');
                return;
            }
            
            // Get current combat state
            const combatState = this.getCombatStateForBackend();
            
            // Send combat state via WebSocket
            const message = {
                type: 'combat_state',
                request_id: this.lastRequestId,  // Include the request_id if available
                data: {
                    combat_state: combatState,
                    timestamp: Date.now()
                }
            };
            
            await wsClient.send(message);
            console.log('Combat Monitor: Transmitted combat state to backend:', combatState);
            
        } catch (error) {
            console.error('Combat Monitor: Error transmitting combat state:', error);
        }
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
