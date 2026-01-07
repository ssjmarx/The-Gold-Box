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
     * Collect scene spatial data for spatial filtering
     * @returns {Object} Complete scene data for spatial filtering
     */
    collectSceneSpatialData() {
        try {
            const scene = game?.scenes?.active;
            
            if (!scene) {
                console.error('WorldStateCollector: No active scene for spatial data collection');
                return {
                    scene_id: null,
                    scene_name: 'No Active Scene',
                    grid_size:100,
                    distance_unit: '5 feet',
                    walls: [],
                    doors: [],
                    tokens: [],
                    notes: [],
                    lights: []
                };
            }
            
            console.log('WorldStateCollector: Collecting scene spatial data for scene:', scene.name);
            console.log('WorldStateCollector: scene object keys:', Object.keys(scene));
            console.log('WorldStateCollector: scene.tokens exists:', !!scene.tokens);
            console.log('WorldStateCollector: scene.tokens type:', typeof scene.tokens);
            console.log('WorldStateCollector: scene.tokens length:', scene.tokens?.length);
            console.log('WorldStateCollector: scene.tokens is embedded collection:', scene.tokens instanceof Array);
            console.log('WorldStateCollector: canvas ready:', !!canvas?.ready);
            console.log('WorldStateCollector: canvas.tokens exists:', !!canvas?.tokens);
            console.log('WorldStateCollector: canvas.tokens placeables length:', canvas?.tokens?.placeables?.length || 0);
            
            // Collect grid information
            const grid_size = scene.grid?.size || 100;
            const distance_unit = scene.grid?.distance || 5; // Foundry stores this as units per square (e.g., 5 for 5ft squares)
            const distance_unit_setting = `${distance_unit} feet`;
            
            // Collect walls with coordinate arrays and vision blocking info
            const walls = scene.walls.map(wall => {
                return {
                    id: wall.id,
                    c: wall.c, // [x1, y1, x2, y2] coordinate array
                    door: wall.door,
                    blocks_vision: wall.sense // Vision blocking flag
                };
            });
            
            // Collect doors (subset of walls that are doors)
            const doors = scene.walls.filter(wall => {
                return wall.door && wall.door !== CONST.WALL_DOOR_TYPES.NONE;
            }).map(door => {
                return {
                    id: door.id,
                    c: door.c, // [x1, y1, x2, y2] coordinate array
                    door: door.door,
                    state: door.doorState || 0, // 0=closed, 1=open, 2=locked
                    locked: door.locked,
                    blocks_vision: door.sense,
                    coordinates: {
                        start: { x: door.c[0], y: door.c[1] },
                        end: { x: door.c[2], y: door.c[3] },
                        center: {
                            x: (door.c[0] + door.c[2]) / 2,
                            y: (door.c[1] + door.c[3]) / 2
                        }
                    }
                };
            });
            
            // Collect notes with journal entry details
            const notes = scene.notes.map(note => {
                const journalEntry = game?.journal?.get(note.entryId);
                return {
                    id: note.id,
                    x: note.x,
                    y: note.y,
                    entry_name: note.entryName,
                    journal_entry_title: journalEntry?.name || 'Unknown',
                    note_type: note.icon || 'location'
                };
            });
            
            // Collect light sources from tokens
            // Use scene.tokens instead of canvas.tokens.placeables for consistency
            // In Foundry V12, scene.tokens returns TokenDocuments, so access properties directly
            if (!scene.tokens || scene.tokens.length === 0) {
                console.warn('WorldStateCollector: scene.tokens is empty or unavailable, using fallback');
                return {
                    scene_id: scene.id,
                    scene_name: scene.name,
                    grid_size: grid_size,
                    distance_unit: distance_unit_setting,
                    walls: [],
                    doors: [],
                    tokens: [],
                    notes: [],
                    lights: []
                };
            }
            
            const tokenList = Array.from(scene.tokens);
            const lights = tokenList
                .filter(token => token.light && token.light.radius > 0)
                .map(token => {
                    return {
                        id: token.id,
                        source_token: token.name,
                        x: token.x,
                        y: token.y,
                        radius: token.light.radius,
                        color: token.light.color || '#ffffff',
                        brightness: token.light.dim > 0 ? 'dim' : 'bright'
                    };
                });
            
            // Collect tokens with player ownership and coordinates
            // scene.tokens is an EmbeddedCollection, so convert to array first
            // (Already converted above, reusing the same list for consistency)
            console.log(`WorldStateCollector: tokenList length: ${tokenList.length}`);
            const tokens = tokenList.map(token => {
                // Calculate center coordinates manually since token.center doesn't exist on TokenDocuments
                const tokenWidth = token.width || (scene.grid?.size || 100);
                const tokenHeight = token.height || (scene.grid?.size || 100);
                const centerX = token.x + (tokenWidth / 2);
                const centerY = token.y + (tokenHeight / 2);
                
                return {
                    id: token.id,
                    name: token.name,
                    actor_id: token.actor?.id || null,
                    x: token.x,
                    y: token.y,
                    is_player: token.actor?.hasPlayerOwner || false,
                    coordinates: {
                        x: centerX,
                        y: centerY
                    }
                };
            });
            
            console.log(`WorldStateCollector: Mapped ${tokens.length} tokens`);
            console.log(`WorldStateCollector: First token: ${tokens.length > 0 ? JSON.stringify(tokens[0]) : 'none'}`);
            
            const sceneData = {
                scene_id: scene.id,
                scene_name: scene.name,
                grid_size: grid_size,
                distance_unit: distance_unit_setting,
                walls: walls,
                doors: doors,
                tokens: tokens,
                notes: notes,
                lights: lights
            };
            
            console.log(`WorldStateCollector: Collected scene spatial data:`, {
                scene: scene.name,
                walls: walls.length,
                doors: doors.length,
                tokens: tokens.length,
                notes: notes.length,
                lights: lights.length,
                grid_size: grid_size,
                distance_unit: distance_unit_setting
            });
            
            console.log(`WorldStateCollector: Full scene data keys:`, Object.keys(sceneData));
            console.log(`WorldStateCollector: Returning scene data:`, sceneData);
            
            return sceneData;
            
        } catch (error) {
            console.error('WorldStateCollector: Error collecting scene spatial data:', error);
            return {
                scene_id: null,
                scene_name: 'Error',
                grid_size: 100,
                distance_unit: '5 feet',
                walls: [],
                doors: [],
                tokens: [],
                notes: [],
                lights: []
            };
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
                spatial_context: this.getSpatialContext(),
                timestamp: Date.now()
            };
            
            console.log('Full world state collected:', {
                scene: worldState.active_scene.name,
                players: worldState.session_info.players.length,
                party: worldState.party_compendium.length,
                packs: worldState.compendium_index.length,
                spatial_enabled: worldState.spatial_context.enabled
            });
            
            return worldState;
        } catch (error) {
            console.error('Error collecting full world state:', error);
            return null;
        }
    }

  /**
   * Get spatial context for AI
   * @returns {Object} Spatial context with search origin
   */
  getSpatialContext() {
    try {
      // Check if auto-search is enabled
      const autoSearchEnabled = game?.settings?.get('the-gold-box', 'autoSearchEnabled') ?? true;
      
      if (!autoSearchEnabled) {
        return {
          enabled: false,
          reason: 'Auto-search disabled in settings'
        };
      }
      
      // Get active scene
      const scene = game?.scenes?.active;
      if (!scene) {
        return {
          enabled: false,
          reason: 'No active scene'
        };
      }
      
      // Get search origin using fallback chain
      const activeScene = this.getActiveScene();
      const searchOrigin = this.getSpatialSearchOrigin(activeScene);
      
      if (!searchOrigin) {
        return {
          enabled: false,
          reason: 'No tokens available in scene'
        };
      }
      
      // Get spatial settings
      const radius = game?.settings?.get('the-gold-box', 'autoSearchRadius') ?? 6;
      const mode = game?.settings?.get('the-gold-box', 'autoSearchMode') ?? 'line_of_sight';
      
      return {
        enabled: true,
        search_origin: searchOrigin,
        radius: radius,
        mode: mode
      };
    } catch (error) {
      console.error('Error getting spatial context:', error);
      return {
        enabled: false,
        reason: `Error: ${error.message}`
      };
    }
  }

    /**
     * Get spatial search origin using fallback chain
     * Priority:
     * 1. User's configured PC token (game.user.character)
     * 2. First player-owned token in scene
     * 3. First non-player token in scene
     * 4. null (no tokens available)
     * 
     * @param {Object} activeScene - Active scene data from getActiveScene()
     * @returns {Object|null} Search origin with token_id, token_name, actor_id, coordinates
     */
    getSpatialSearchOrigin(activeScene) {
        try {
            // Step 1: Try current user's configured player character
            const currentUser = game?.user;
            if (currentUser && currentUser.character) {
                const pcActor = game.actors.get(currentUser.character.id);
                if (pcActor) {
                    // Find all tokens for this actor in scene
                    const actorTokens = activeScene.tokens.filter(t => t.actor_id === pcActor.id);
                    if (actorTokens.length > 0) {
                        const firstToken = actorTokens[0];
                        console.log(`Spatial search: Using user's PC token ${firstToken.name}`);
                        return {
                            token_id: firstToken.id,
                            token_name: firstToken.name,
                            actor_id: pcActor.id,
                            coordinates: { x: firstToken.x, y: firstToken.y }
                        };
                    }
                }
            }
            
            // Step 2: Try first player-owned token in scene
            const playerToken = activeScene.tokens.find(t => t.is_player);
            if (playerToken) {
                console.log(`Spatial search: Using first player-owned token ${playerToken.name}`);
                return {
                    token_id: playerToken.id,
                    token_name: playerToken.name,
                    actor_id: playerToken.actor_id,
                    coordinates: { x: playerToken.x, y: playerToken.y }
                };
            }
            
            // Step 3: Try first non-player token in scene
            const anyToken = activeScene.tokens.find(t => !t.is_player);
            if (anyToken) {
                console.log(`Spatial search: Using first non-player token ${anyToken.name}`);
                return {
                    token_id: anyToken.id,
                    token_name: anyToken.name,
                    actor_id: anyToken.actor_id,
                    coordinates: { x: anyToken.x, y: anyToken.y }
                };
            }
            
            // Step 4: No tokens found
            console.log('Spatial search: No tokens in scene, skipping');
            return null;
        } catch (error) {
            console.error('Error getting spatial search origin:', error);
            return null;
        }
    }

    /**
     * Get party members (player-controlled characters)
     * @returns {Object} Party members with total count and member details
     */
    getPartyMembers() {
        try {
            const partyMembers = [];
            
            if (!game?.actors) {
                console.warn('WorldStateCollector: No actors available in Foundry');
                return {
                    total_party_members: 0,
                    members: []
                };
            }
            
            // Get all player-controlled actors
            for (const actor of game.actors) {
                if (actor.hasPlayerOwner) {
                    // Get ownership object
                    const ownership = actor.ownership || {};
                    
                    // Collect owner information
                    const owners = [];
                    for (const userId in ownership) {
                        const user = game.users.get(userId);
                        
                        // Skip GM users and invalid users
                        if (user && !user.isGM) {
                            owners.push({
                                id: user.id,
                                name: user.name,
                                is_active: user.active
                            });
                        }
                    }
                    
                    // Get basic system data
                    const systemData = actor.system || {};
                    
                    partyMembers.push({
                        id: actor.id,
                        name: actor.name,
                        type: actor.type,
                        img: actor.img,
                        owners: owners,
                        system: {
                            hp: systemData.attributes?.hp || {},
                            ac: systemData.attributes?.ac || {},
                            // Add more system fields as needed
                            details: systemData.details || {}
                        }
                    });
                }
            }
            
            console.log(`WorldStateCollector: Collected ${partyMembers.length} party members`);
            
            return {
                total_party_members: partyMembers.length,
                members: partyMembers
            };
        } catch (error) {
            console.error('WorldStateCollector: Error getting party members:', error);
            return {
                total_party_members: 0,
                members: [],
                error: error.message
            };
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
     * Get journal context - search for phrase within journal entry with context lines
     * @param {string} entryName - Name of journal entry to search
     * @param {string} searchPhrase - Phrase to search for
     * @param {number} contextLines - Number of lines of context before and after match (default: 3)
     * @returns {Object} Journal context with matches
     */
    async getJournalContext(entryName, searchPhrase, contextLines = 3) {
        try {
            console.log(`WorldStateCollector: Getting journal context for entry "${entryName}", phrase "${searchPhrase}", context: ${contextLines} lines`);
            
            // Find journal entry by name
            const journalEntry = game?.journal?.find(entry => {
                const entryNameMatch = entry.name === entryName || entry.id === entryName;
                if (entryNameMatch) {
                    console.log(`Found journal entry: ${entry.name} (ID: ${entry.id})`);
                }
                return entryNameMatch;
            });
            
            if (!journalEntry) {
                console.error(`WorldStateCollector: Journal entry not found: ${entryName}`);
                return {
                    success: false,
                    error: `Journal entry not found: ${entryName}`
                };
            }
            
            // Get text content from first page
            const page = journalEntry.pages?.contents?.[0];
            
            if (!page) {
                console.error(`WorldStateCollector: Journal entry has no pages: ${entryName}`);
                return {
                    success: false,
                    error: `Journal entry has no pages: ${entryName}`
                };
            }
            
            const text = page.text?.content || '';
            
            if (!text) {
                console.error(`WorldStateCollector: Journal entry has no text content: ${entryName}`);
                return {
                    success: false,
                    error: `Journal entry has no text content: ${entryName}`
                };
            }
            
            // Split text into lines
            const lines = text.split('\n');
            console.log(`WorldStateCollector: Journal entry has ${lines.length} lines`);
            
            // Search for phrase (case-insensitive)
            const searchLower = searchPhrase.toLowerCase();
            const matches = [];
            
            lines.forEach((line, index) => {
                if (line.toLowerCase().includes(searchLower)) {
                    const start = Math.max(0, index - contextLines);
                    const end = Math.min(lines.length, index + contextLines + 1);
                    
                    matches.push({
                        match: line,
                        context: lines.slice(start, end),
                        line_number: index + 1,
                        position: { start, end }
                    });
                }
            });
            
            console.log(`WorldStateCollector: Found ${matches.length} matches for phrase "${searchPhrase}"`);
            
            // Return results with entry metadata
            return {
                success: true,
                entry_name: journalEntry.name,
                entry_id: journalEntry.id,
                search_phrase: searchPhrase,
                context_lines: contextLines,
                matches: matches,
                total_matches: matches.length,
                timestamp: Date.now()
            };
            
        } catch (error) {
            console.error('WorldStateCollector: Error getting journal context:', error);
            return {
                success: false,
                error: error.message
            };
        }
    }

    /**
     * Search Compendium - search for entries in a compendium pack
     * @param {string} packName - Name of compendium pack to search
     * @param {string} query - Search query text
     * @returns {Object} Compendium search results
     */
    async searchCompendium(packName, query) {
        try {
            console.log(`WorldStateCollector: Searching compendium pack "${packName}" for "${query}"`);
            
            // Find compendium pack by name/collection
            const pack = game?.packs?.find(p => {
                return p.collection === packName || p.metadata.label === packName || p.collection.includes(packName);
            });
            
            if (!pack) {
                console.error(`WorldStateCollector: Compendium pack not found: ${packName}`);
                return {
                    success: false,
                    error: `Compendium pack not found: ${packName}`
                };
            }
            
            // Get compendium index
            const index = await pack.getIndex();
            
            if (!index) {
                console.error(`WorldStateCollector: Failed to get index for pack: ${packName}`);
                return {
                    success: false,
                    error: `Failed to get index for compendium pack: ${packName}`
                };
            }
            
            // Search for entries matching query (case-insensitive, partial matches)
            const queryLower = query.toLowerCase();
            const matches = [];
            
            for (const entry of index) {
                const nameLower = (entry.name || '').toLowerCase();
                const match = nameLower.includes(queryLower);
                
                if (match) {
                    matches.push({
                        id: entry._id,
                        name: entry.name,
                        type: entry.type,
                        pack: pack.collection
                    });
                }
            }
            
            console.log(`WorldStateCollector: Found ${matches.length} matches for query "${query}" in pack "${packName}"`);
            
            return {
                success: true,
                pack_name: packName,
                pack_label: pack.metadata.label || packName,
                query: query,
                matches: matches,
                total_matches: matches.length,
                timestamp: Date.now()
            };
            
        } catch (error) {
            console.error('WorldStateCollector: Error searching compendium:', error);
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
