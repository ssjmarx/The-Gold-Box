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
        
        // Initialize combat event listeners
        this.initCombatListeners();
        
        console.log("Combat Monitor initialized");
    }
    
    /**
     * Initialize Foundry combat event listeners
     */
    initCombatListeners() {
        // Listen for combat create events
        Hooks.on('createCombat', (combat) => {
            console.log('Combat created:', combat);
            this.updateCombatState(combat);
        });
        
        // Listen for combat delete events
        Hooks.on('deleteCombat', (combat) => {
            console.log('Combat deleted:', combat);
            this.clearCombatState();
        });
        
        // Listen for combat round events
        // Note: When a new round starts, combatTurn hook does NOT fire with turn 0
        // It starts firing from turn 1, so we MUST use combatRound to capture turn 0
        Hooks.on('combatRound', (combat, round) => {
            console.log('Combat round:', combat, round);
            // When new round starts, first combatant is index 0
            // Pass turn 0 explicitly since combatTurn won't fire with it
            this.updateCombatState(combat, 0);
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
            const combatants = combatantsArray.map(c => ({
                name: c.name || 'Unknown',
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
            
            // Transmit updated combat state to backend
            this.transmitCombatState();
            
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
        
        // Transmit cleared combat state to backend
        this.transmitCombatState();
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
