/**
 * The Gold Box - World State Collector
 * Collects full world state from Foundry and sends to backend via WebSocket
 * 
 * This module provides comprehensive world state collection for initial context
 * - Session info (game system, GM name, players)
 * - Party compendium (player-controlled characters)
 * - Active scene (scene data, tokens, notes, light sources)
 * - Compendium index (available compendium packs)
 * 
 * License: CC-BY-NC-SA 4.0
 */

class WorldStateCollector {
    constructor() {
        this.initialized = false;
        this.listeners = [];
        this.initialStateSent = false;
        this.lastRequestId = null; // Track the last request_id for responses
        console.log('WorldStateCollector constructed');
    }

    /**
     * Initialize the world state collector
     */
    async initialize() {
        if (this.initialized) {
            console.warn('WorldStateCollector already initialized');
            return;
        }

        console.log('Initializing WorldStateCollector...');
        
        // Set up hooks for automatic updates
        this._setupHooks();
        
        this.initialized = true;
        console.log('WorldStateCollector initialized');
        
        // If WebSocket is already connected, send initial world state now
        await this._checkAndSendInitialState();
    }
    
    /**
     * Check if WebSocket is connected and send initial world state
     * @private
     */
    async _checkAndSendInitialState() {
        console.log('WorldStateCollector: _checkAndSendInitialState called');
        console.log('WorldStateCollector: Checking WebSocket connection for initial world state...');
        
        try {
            // Check if WebSocket client is connected
            const wsCommunicator = window.WebSocketCommunicator?.instance;
            console.log('WorldStateCollector: wsCommunicator exists:', !!wsCommunicator);
            
            const wsClient = wsCommunicator?.webSocketClient;
            console.log('WorldStateCollector: wsClient exists:', !!wsClient);
            console.log('WorldStateCollector: wsClient isConnected:', wsClient?.isConnected);
            
            if (wsClient && wsClient.isConnected) {
                console.log('WorldStateCollector: WebSocket already connected, sending initial world state');
                this.sendWorldState();
            } else {
                console.log('WorldStateCollector: WebSocket not yet connected, setting up hook to send on connect');
                // Set up a one-time hook to send world state when WebSocket connects
                if (wsClient && !wsClient.isConnected) {
                    // Use setTimeout to poll for connection
                    const checkInterval = setInterval(() => {
                        const refreshedWsClient = window.WebSocketCommunicator?.instance?.webSocketClient;
                        if (refreshedWsClient && refreshedWsClient.isConnected && !this.initialStateSent) {
                            console.log('WorldStateCollector: WebSocket now connected, sending initial world state');
                            this.sendWorldState();
                            clearInterval(checkInterval);
                        }
                    }, 500);
                    
                    // Clear interval after 30 seconds
                    setTimeout(() => {
                        clearInterval(checkInterval);
                    }, 30000);
                }
            }
        } catch (error) {
            console.warn('WorldStateCollector: Error checking WebSocket connection:', error);
        }
    }

    /**
     * Get session info
     * @returns {Object} Session information
     */
    getSessionInfo() {
        try {
            const gameSystem = game?.system?.id || 'unknown';
            const gmName = game?.users?.find(u => u.isGM)?.name || 'Game Master';
            const players = game?.users?.filter(u => !u.isGM && u.active).map(u => u.name) || [];
            
            return {
                game_system: gameSystem,
                gm_name: gmName,
                players: players
            };
        } catch (error) {
            console.error('Error getting session info:', error);
            return {
                game_system: 'unknown',
                gm_name: 'Unknown',
                players: []
            };
        }
    }

    /**
     * Get party compendium (player-controlled characters)
     * @returns {Array} Array of party members
     */
    getPartyCompendium() {
        try {
            const partyMembers = [];
            
            if (!game?.actors) {
                console.warn('No actors available in Foundry');
                return partyMembers;
            }
            
            // Get player-controlled actors
            for (const actor of game.actors) {
                if (actor.hasPlayerOwner) {
                    // Get ownership object
                    const ownership = actor.ownership || {};
                    
                    // Iterate through ownership keys to find first non-GM owner
                    // In Foundry V12, ownership is {userId: level} where keys are user IDs
                    for (const userId in ownership) {
                        const user = game.users.get(userId);
                        
                        // Skip GM users and invalid users
                        if (user && !user.isGM) {
                            partyMembers.push({
                                id: actor.id,
                                name: actor.name,
                                player: user.name,
                                actor_id: actor.id
                            });
                            break; // Only add once per actor
                        }
                    }
                }
            }
            
            console.log(`Collected ${partyMembers.length} party members`);
            return partyMembers;
        } catch (error) {
            console.error('Error getting party compendium:', error);
            return [];
        }
    }

    /**
     * Get active scene data including notes and light sources
     * @returns {Object} Active scene data
     */
    getActiveScene() {
        try {
            const scene = game?.scenes?.active;
            
            if (!scene) {
                return {
                    id: 'unknown',
                    name: 'Unknown Scene',
                    dimensions: { width: 0, height: 0, grid: 50 },
                    tokens: [],
                    notes: [],
                    light_sources: []
                };
            }
            
            // Collect tokens
            const tokens = scene.tokens.map(token => {
                return {
                    id: token.id,
                    name: token.name,
                    actor_id: token.actor?.id || null,
                    x: token.x,
                    y: token.y,
                    is_player: token.actor?.hasPlayerOwner || false
                };
            });
            
            // Collect notes (journal notes pinned to scene)
            const notes = scene.notes.map(note => {
                const journalEntry = game?.journal?.get(note.entryId);
                return {
                    id: note.id,
                    entry_name: journalEntry?.name || 'Unknown Note',
                    x: note.x,
                    y: note.y,
                    is_journal_entry: !!journalEntry
                };
            });
            
            // Collect light sources
            const lightSources = [];
            scene.tokens.forEach(token => {
                if (token.emitsLight || token.emitsDarkness) {
                    lightSources.push({
                        id: token.id,
                        x: token.x,
                        y: token.y,
                        radius: token.dimRadius || token.brightRadius || 0,
                        color: token.lightColor || '#ffffff'
                    });
                }
            });
            
            // Also add ambient light if available (use environment.darknessLevel for Foundry V12)
            const darknessLevel = scene.environment?.darknessLevel ?? scene.darkness;
            if (darknessLevel !== undefined) {
                lightSources.push({
                    id: 'ambient_light',
                    x: scene.width / 2,
                    y: scene.height / 2,
                    radius: Math.max(scene.width, scene.height),
                    color: `rgba(0,0,0,${darknessLevel})`
                });
            }
            
            return {
                id: scene.id,
                name: scene.name,
                dimensions: {
                    width: scene.width,
                    height: scene.height,
                    grid: scene.grid?.size || 50
                },
                tokens: tokens,
                notes: notes,
                light_sources: lightSources
            };
        } catch (error) {
            console.error('Error getting active scene:', error);
            return {
                id: 'unknown',
                name: 'Unknown Scene',
                dimensions: { width: 0, height: 0, grid: 50 },
                tokens: [],
                notes: [],
                light_sources: []
            };
        }
    }

    /**
     * Get compendium index (available compendium packs)
     * @returns {Array} Array of compendium packs
     */
    getCompendiumIndex() {
        try {
            const packs = [];
            
            if (!game?.packs) {
                console.warn('No compendium packs available in Foundry');
                return packs;
            }
            
            for (const pack of game.packs) {
                if (pack.visible && !pack.private) {
                    let type = 'unknown';
                    
                    // Determine pack type
                    if (pack.metadata.entity === 'Actor') {
                        type = 'Actor';
                    } else if (pack.metadata.entity === 'Item') {
                        type = 'Item';
                    } else if (pack.metadata.entity === 'JournalEntry') {
                        type = 'JournalEntry';
                    } else if (pack.metadata.entity === 'RollTable') {
                        type = 'RollableTable';
                    } else if (pack.metadata.type === 'Adventure') {
                        type = 'Adventure';
                    } else {
                        type = pack.metadata.entity || pack.metadata.type || 'unknown';
                    }
                    
                    packs.push({
                        pack_name: pack.collection,
                        type: type,
                        label: pack.metadata.label || pack.collection,
                        package: pack.metadata.package || 'world'
                    });
                }
            }
            
            console.log(`Collected ${packs.length} compendium packs`);
            return packs;
        } catch (error) {
            console.error('Error getting compendium index:', error);
            return [];
        }
    }

    /**
     * Get full world state
     * @returns {Object} Complete world state
     */
    getFullWorldState() {
        try {
            const worldState = {
                session_info: this.getSessionInfo(),
                party_compendium: this.getPartyCompendium(),
                active_scene: this.getActiveScene(),
                compendium_index: this.getCompendiumIndex(),
                timestamp: Date.now()
            };
            
            console.log('Full world state collected:', {
                scene: worldState.active_scene.name,
                players: worldState.session_info.players.length,
                party: worldState.party_compendium.length,
                packs: worldState.compendium_index.length
            });
            
            return worldState;
        } catch (error) {
            console.error('Error collecting full world state:', error);
            return null;
        }
    }

    /**
     * Get token actor details with optional search
     * @param {string} tokenId - Token ID (e.g., 'Scene.XXX.Token.YYY')
     * @param {string} searchPhrase - Optional search phrase for grep-like search
     * @returns {Object} Token actor details or search results
     */
    async getTokenActorDetails(tokenId, searchPhrase = '') {
        try {
            console.log(`WorldStateCollector: Getting actor details for token ${tokenId}${searchPhrase ? ` with search phrase "${searchPhrase}"` : ''}`);
            
            // Get token from canvas
            const token = canvas?.tokens?.get(tokenId);
            
            if (!token) {
                console.error(`WorldStateCollector: Token not found: ${tokenId}`);
                return {
                    success: false,
                    error: `Token not found: ${tokenId}`
                };
            }
            
            // Get token-specific actor
            const actor = token.actor;
            
            if (!actor) {
                console.error(`WorldStateCollector: No actor found for token: ${tokenId}`);
                return {
                    success: false,
                    error: `No actor found for token: ${tokenId}`
                };
            }
            
            // If no search phrase, return complete actor data
            if (!searchPhrase || searchPhrase.trim() === '') {
                console.log(`WorldStateCollector: Returning complete actor data for ${actor.name}`);
                return {
                    success: true,
                    name: actor.name,
                    system: actor.system
                };
            }
            
            // Perform grep-like search
            console.log(`WorldStateCollector: Performing search for "${searchPhrase}" on ${actor.name}`);
            
            // Flatten actor.system to path-value pairs
            const flattened = this._flattenObject(actor.system);
            console.log(`WorldStateCollector: Flattened ${flattened.length} fields`);
            
            // Filter for matches (case-insensitive, exact substring)
            const searchLower = searchPhrase.toLowerCase();
            const matches = flattened.filter(f => {
                const pathLower = f.path.toLowerCase();
                const valueStr = String(f.value).toLowerCase();
                return pathLower.includes(searchLower) || valueStr.includes(searchLower);
            });
            
            console.log(`WorldStateCollector: Found ${matches.length} matches`);
            
            // Add context (parent + sibling fields) for each match
            matches.forEach(match => {
                const parentPath = match.path.split('.').slice(0, -1).join('.');
                match.context = {
                    parent: parentPath,
                    siblings: this._getSiblingFields(flattened, parentPath)
                };
            });
            
            // Return search results
            return {
                success: true,
                name: actor.name,
                matches: matches,
                summary: {
                    total_matches: matches.length,
                    fields_searched: flattened.length
                }
            };
            
        } catch (error) {
            console.error('WorldStateCollector: Error getting token actor details:', error);
            return {
                success: false,
                error: error.message
            };
        }
    }
    
    /**
     * Modify token attribute using Foundry's native API
     * @param {string} tokenId - Token ID to modify
     * @param {string} attributePath - Attribute path to modify (e.g., 'attributes.hp.value')
     * @param {number} value - Value to set or add/subtract
     * @param {boolean} isDelta - Whether value is relative (true) or absolute (false)
     * @param {boolean} isBar - Whether to update token bar display
     * @returns {Object} Modification result
     */
    async modifyTokenAttribute(tokenId, attributePath, value, isDelta = true, isBar = true) {
        try {
            console.log(`WorldStateCollector: Modifying token ${tokenId}, path: ${attributePath}, value: ${value}, isDelta: ${isDelta}, isBar: ${isBar}`);
            
            // Get token from canvas
            const token = canvas?.tokens?.get(tokenId);
            
            if (!token) {
                console.error(`WorldStateCollector: Token not found: ${tokenId}`);
                
                // CRITICAL: Send error response back to backend even on failure
                if (window.WebSocketCommunicator?.instance?.webSocketClient) {
                    const wsClient = window.WebSocketCommunicator.instance.webSocketClient;
                    const errorMsg = `Token not found: ${tokenId}`;
                    
                    // Send combat_state response with error
                    await wsClient.send({
                        type: 'combat_state',
                        request_id: this.lastRequestId || null,
                        data: {
                            combat_state: {
                                in_combat: false,
                                combat_id: null,
                                round: 0,
                                turn: 0,
                                combatants: [],
                                last_updated: Date.now(),
                                error: errorMsg
                            }
                        },
                        timestamp: Date.now()
                    });
                    console.log(`WorldStateCollector: Sent error response to backend: ${errorMsg}`);
                }
                
                return {
                    success: false,
                    error: `Token not found: ${tokenId}`
                };
            }
            
            // For system attributes (like HP), use actor.update() instead of updateSource()
            // Parse the attribute path (e.g., 'attributes.hp.value')
            const pathParts = attributePath.split('.');
            
            // The path structure is: [top_level].[sub_attribute].[property]
            // e.g., 'attributes.hp.value' -> attributeName='attributes', subAttribute='hp', property='value'
            const attributeName = pathParts[0]; // 'attributes'
            const subAttributeName = pathParts[1]; // 'hp'
            const propertyName = pathParts[2] || 'value'; // 'value' (or default to 'value')
            
            // Validate that top-level attribute exists in actor's system data
            if (!token.actor.system[attributeName]) {
                const errorMsg = `Attribute '${attributeName}' not found in actor ${token.actor.name}. Valid attributes: ${Object.keys(token.actor.system).join(', ')}`;
                console.error(`WorldStateCollector: ${errorMsg}`);
                
                // Send error response back to backend
                if (window.WebSocketCommunicator?.instance?.webSocketClient) {
                    const wsClient = window.WebSocketCommunicator.instance.webSocketClient;
                    
                    await wsClient.send({
                        type: 'combat_state',
                        request_id: this.lastRequestId || null,
                        data: {
                            combat_state: {
                                in_combat: false,
                                combat_id: null,
                                round: 0,
                                turn: 0,
                                combatants: [],
                                last_updated: Date.now(),
                                error: errorMsg
                            }
                        },
                        timestamp: Date.now()
                    });
                    console.log(`WorldStateCollector: Sent error response to backend: ${errorMsg}`);
                }
                
                return {
                    success: false,
                    error: errorMsg
                };
            }
            
            // Validate that sub-attribute exists (if specified)
            if (subAttributeName && !token.actor.system[attributeName][subAttributeName]) {
                const errorMsg = `Sub-attribute '${subAttributeName}' not found in ${attributeName}. Valid sub-attributes: ${Object.keys(token.actor.system[attributeName]).join(', ')}`;
                console.error(`WorldStateCollector: ${errorMsg}`);
                
                // Send error response back to backend
                if (window.WebSocketCommunicator?.instance?.webSocketClient) {
                    const wsClient = window.WebSocketCommunicator.instance.webSocketClient;
                    
                    await wsClient.send({
                        type: 'combat_state',
                        request_id: this.lastRequestId || null,
                        data: {
                            combat_state: {
                                in_combat: false,
                                combat_id: null,
                                round: 0,
                                turn: 0,
                                combatants: [],
                                last_updated: Date.now(),
                                error: errorMsg
                            }
                        },
                        timestamp: Date.now()
                    });
                    console.log(`WorldStateCollector: Sent error response to backend: ${errorMsg}`);
                }
                
                return {
                    success: false,
                    error: errorMsg
                };
            }
            
            // Build update object with proper nested structure
            let updateData = {};
            
            if (isDelta) {
                // Get current value and apply delta
                const currentValue = token.actor.system[attributeName][subAttributeName]?.[propertyName] || 0;
                updateData = {
                    system: {
                        [attributeName]: {
                            [subAttributeName]: {
                                [propertyName]: currentValue + value
                            }
                        }
                    }
                };
                console.log(`WorldStateCollector: Applying delta ${value} to current value ${currentValue} at ${attributePath}, result: ${currentValue + value}`);
            } else {
                // Set absolute value
                updateData = {
                    system: {
                        [attributeName]: {
                            [subAttributeName]: {
                                [propertyName]: value
                            }
                        }
                    }
                };
                console.log(`WorldStateCollector: Setting absolute value ${value} at ${attributePath}`);
            }
            
            await token.actor.update(updateData);
            
            // Wait for Foundry to process and propagate the update before verifying
            await new Promise(resolve => setTimeout(resolve, 100));
            
            // Validate the change was actually applied
            const updatedValue = token.actor.system[attributeName]?.[subAttributeName]?.[propertyName];
            
            // Check if attribute exists
            if (updatedValue === null || updatedValue === undefined) {
                throw new Error(`Attribute ${attributePath} not found in actor system data`);
            }
            
            // Verify the value matches expected result
            const expectedValue = isDelta ? 
                (parseFloat(token.actor.system[attributeName][subAttributeName]?.[propertyName] || 0) - parseFloat(value)) + parseFloat(value) : 
                parseFloat(value);
            
            if (Math.abs(parseFloat(updatedValue) - expectedValue) > 0.001) {
                console.warn(`WorldStateCollector: Value mismatch - expected ${expectedValue}, got ${updatedValue}`);
                // Don't throw error, just log warning - Foundry may have modified the value
            }
            
            console.log(`WorldStateCollector: Successfully modified token ${tokenId} attribute ${attributePath} to value ${updatedValue}`);
            
            // If token is in combat, update combat state
            let combatUpdated = false;
            if (window.CombatMonitor && game.combat && game.combat.started) {
                const combatants = game.combat.combatants;
                const isInCombat = combatants.some(c => c.tokenId === tokenId);
                
                if (isInCombat) {
                    console.log(`WorldStateCollector: Token is in combat, updating combat state`);
                    try {
                        await window.CombatMonitor.transmitCombatState();
                        combatUpdated = true;
                    } catch (combatError) {
                        console.error('WorldStateCollector: Error updating combat state:', combatError);
                        // Continue to send response even if combat update fails
                    }
                }
            }
            
            // CRITICAL: Always send success response back to backend
            if (window.WebSocketCommunicator?.instance?.webSocketClient) {
                const wsClient = window.WebSocketCommunicator.instance.webSocketClient;
                
                // Send combat_state response back to backend (token modification triggers combat state update)
                const responseMessage = {
                    type: 'combat_state',
                    request_id: this.lastRequestId || null,
                    data: {
                        combat_state: {
                            in_combat: combatUpdated ? game.combat?.started || false : false,
                            combat_id: game.combat?._id || null,
                            round: game.combat?.round || 0,
                            turn: game.combat?.turn || 0,
                            combatants: combatUpdated ? (game.combat?.combatants?.map(c => ({
                                name: c.name,
                                initiative: c.initiative || 0,
                                is_player: c.hasPlayerOwner,
                                is_current_turn: game.combat?.current === c._id
                            })) || []) : [],
                            last_updated: Date.now()
                        }
                    },
                    timestamp: Date.now()
                };
                
                await wsClient.send(responseMessage);
                console.log(`WorldStateCollector: Token attribute modified, combat state transmitted to backend`);
            }
            
            return {
                success: true,
                message: 'Attribute modified successfully',
                token_id: tokenId,
                attribute_path: attributePath,
                value: value,
                is_delta: isDelta,
                is_bar: isBar
            };
            
        } catch (error) {
            console.error('WorldStateCollector: Error modifying token attribute:', error);
            
            // CRITICAL: Send error response back to backend even on failure
            if (window.WebSocketCommunicator?.instance?.webSocketClient) {
                const wsClient = window.WebSocketCommunicator.instance.webSocketClient;
                const errorMsg = error.message || 'Unknown error';
                
                await wsClient.send({
                    type: 'combat_state',
                    request_id: this.lastRequestId || null,
                    data: {
                        combat_state: {
                            in_combat: false,
                            combat_id: null,
                            round: 0,
                            turn: 0,
                            combatants: [],
                            last_updated: Date.now(),
                            error: errorMsg
                        }
                    },
                    timestamp: Date.now()
                });
                console.log(`WorldStateCollector: Sent error response to backend: ${errorMsg}`);
            }
            
            return {
                success: false,
                error: error.message || 'Unknown error',
                token_id: tokenId,
                attribute_path: attributePath,
                value: value,
                is_delta: isDelta,
                is_bar: isBar
            };
        }
    }
    
    /**
     * Flatten nested object to array of path-value pairs
     * @param {Object} obj - Object to flatten
     * @param {string} prefix - Current path prefix
     * @param {Set} visited - Set of already visited objects to prevent circular references
     * @returns {Array} Array of {path, value} objects
     * @private
     */
    _flattenObject(obj, prefix = '', visited = new Set()) {
        const result = [];
        
        if (!obj || typeof obj !== 'object') {
            return result;
        }
        
        // Check for circular reference
        if (visited.has(obj)) {
            // Skip circular reference to prevent infinite recursion
            result.push({ path: prefix || '[circular]', value: '[Circular Reference]' });
            return result;
        }
        
        // Add current object to visited set
        visited.add(obj);
        
        for (const key in obj) {
            if (obj.hasOwnProperty(key)) {
                const value = obj[key];
                const path = prefix ? `${prefix}.${key}` : key;
                
                if (value && typeof value === 'object' && !Array.isArray(value)) {
                    // Recursively flatten nested objects, passing on visited set
                    result.push(...this._flattenObject(value, path, visited));
                } else if (Array.isArray(value)) {
                    // Handle arrays specially - add index to path
                    value.forEach((item, index) => {
                        if (item && typeof item === 'object') {
                            // Pass visited set for array items too
                            result.push(...this._flattenObject(item, `${path}.${index}`, visited));
                        } else {
                            result.push({ path: `${path}.${index}`, value: item });
                        }
                    });
                } else {
                    // Primitive value
                    result.push({ path, value });
                }
            }
        }
        
        return result;
    }
    
    /**
     * Get sibling fields for a given parent path
     * @param {Array} flattened - Array of flattened fields
     * @param {string} parentPath - Parent path to get siblings for
     * @returns {Object} Object of sibling field names to values
     * @private
     */
    _getSiblingFields(flattened, parentPath) {
        const siblings = {};
        
        // Find all fields under the same parent
        flattened.forEach(f => {
            if (f.path.startsWith(parentPath + '.')) {
                // Get the field name directly under parent
                const remainingPath = f.path.substring(parentPath.length + 1);
                const firstDotIndex = remainingPath.indexOf('.');
                
                if (firstDotIndex === -1) {
                    // Direct child of parent
                    siblings[remainingPath] = f.value;
                }
                // Ignore nested fields beyond first level
            }
        });
        
        return siblings;
    }
    
    /**
     * Send world state to backend via WebSocket
     */
    async sendWorldState() {
        try {
            const worldState = this.getFullWorldState();
            
            if (!worldState) {
                console.error('Failed to collect world state');
                return false;
            }
            
            // Get WebSocket client from communicator
            const wsCommunicator = window.WebSocketCommunicator?.instance;
            
            if (!wsCommunicator || !wsCommunicator.webSocketClient || !wsCommunicator.webSocketClient.isConnected) {
                console.warn('WebSocket not connected, cannot send world state');
                return false;
            }
            
            // Send world state sync message
            const message = {
                type: 'world_state_sync',
                data: worldState,
                timestamp: Date.now()
            };
            
            await wsCommunicator.webSocketClient.send(message);
            console.log('World state sent to backend');
            
            return true;
        } catch (error) {
            console.error('Error sending world state:', error);
            return false;
        }
    }

    /**
     * Set up Foundry hooks for automatic world state updates
     */
    _setupHooks() {
        // Hook for scene changes
        Hooks.on('updateScene', (scene, data) => {
            console.log('Scene updated, refreshing world state');
            this.sendWorldState();
        });

        // Hook for actor updates (party compendium changes)
        Hooks.on('updateActor', (actor, data) => {
            if (actor.hasPlayerOwner) {
                console.log('Party actor updated, refreshing world state');
                this.sendWorldState();
            }
        });

        // Hook for combat state changes
        Hooks.on('createCombat', (combat) => {
            console.log('Combat created, refreshing world state');
            this.sendWorldState();
        });

        Hooks.on('deleteCombat', (combat) => {
            console.log('Combat deleted, refreshing world state');
            this.sendWorldState();
        });

        // Hook for token updates
        Hooks.on('updateToken', (token, data) => {
            console.log('Token updated, refreshing world state');
            this.sendWorldState();
        });

        // Hook for note updates
        Hooks.on('updateNote', (note, data) => {
            console.log('Note updated, refreshing world state');
            this.sendWorldState();
        });

        console.log('World state hooks set up');
    }
}

// Global instance
let worldStateCollector = null;

/**
 * Get the world state collector instance
 * @returns {WorldStateCollector} World state collector instance
 */
export function getWorldStateCollector() {
    if (!worldStateCollector) {
        worldStateCollector = new WorldStateCollector();
    }
    return worldStateCollector;
}

/**
 * Initialize the world state collector
 */
export function initializeWorldStateCollector() {
    const collector = getWorldStateCollector();
    collector.initialize();
    return collector;
}

export default WorldStateCollector;
