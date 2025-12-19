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
        Hooks.on('combatRound', (combat, round) => {
            console.log('Combat round:', combat, round);
            this.updateCombatState(combat);
        });
        
        // Listen for combat turn events
        Hooks.on('combatTurn', (combat, turn, combatant) => {
            console.log('Combat turn:', combat, turn, combatant);
            this.updateCombatState(combat);
        });
        
        // Listen for combatant updates
        Hooks.on('updateCombatant', (combat, combatant) => {
            console.log('Combatant updated:', combat, combatant);
            this.updateCombatState(combat);
        });
    }
    
    /**
     * Update combat state from Foundry combat object
     * @param {Combat} combat - Foundry combat object
     */
    updateCombatState(combat) {
        if (!combat) {
            this.clearCombatState();
            return;
        }
        
        try {
            // Safety check: ensure combat.combatants exists and is accessible
            if (!combat.combatants) {
                console.warn('Combat combatants not yet initialized, skipping update');
                return;
            }
            
            // Debug: Log combat object structure to find correct current turn property
            console.log('Combat object structure:', {
                combat_id: combat._id,
                current: combat.current,
                turn: combat.turn,
                combatant_count: combat.combatants.length,
                combatant_ids: combat.combatants.map(c => ({ name: c.name, id: c._id }))
            });
            
            // Try different ways to get current turn combatant ID
            let currentTurnId = null;
            
            // Method 1: Check combat.current (should contain combatant ID)
            if (combat.current && typeof combat.current === 'string') {
                currentTurnId = combat.current;
                console.log('Using combat.current as combatant ID:', currentTurnId);
            }
            // Method 2: Check if combat.current is an object with combatantId
            else if (combat.current && combat.current.combatantId) {
                currentTurnId = combat.current.combatantId;
                console.log('Using combat.current.combatantId:', currentTurnId);
            }
            // Method 3: Use combat.turn as index (0-based)
            else if (typeof combat.turn === 'number' && combat.turn >= 0) {
                const combatantsArray = Array.from(combat.combatants);
                if (combat.turn < combatantsArray.length) {
                    const currentCombatant = combatantsArray[combat.turn];
                    if (currentCombatant) {
                        currentTurnId = currentCombatant._id;
                        console.log('Using combat.turn as index', combat.turn, ':', currentCombatant.name, 'ID:', currentTurnId);
                    }
                }
            }
            
            // Convert combatants to array if it's a collection
            const combatantsArray = Array.from(combat.combatants);
            
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
                combat_id: combat._id,
                round: combat.round || 0,
                turn: combat.turn || 0,
                combatants: combatants
            };
            
            this.cachedCombatData = { ...this.combatState };
            this.lastCombatCheck = Date.now();
            
            console.log('Combat state updated:', this.combatState);
            
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
    }
    
    /**
     * Get current combat state (on-demand pattern)
     * @returns {Object} Current combat state
     */
    getCurrentCombatState() {
        // Update cache if it's old (more than 5 seconds)
        if (Date.now() - this.lastCombatCheck > 5000) {
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
     * @returns {Object} Combat state formatted for backend
     */
    getCombatStateForBackend() {
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
});
