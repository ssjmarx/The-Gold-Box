/**
 * Unified WebSocket Communicator for Gold Box
 * Single authority for all backend communication
 * WebSocket-only with fail-fast error handling
 * HTTP used only for initial health check
 */

// Import DiceRollExecutor (relative path from api/ to services/)
import '../services/dice-roll-executor.js';

// Import WorldStateCollector
import { getWorldStateCollector } from '../services/world-state-collector.js';

/**
 * Connection States
 */
const CommunicatorState = {
  DISCONNECTED: 'disconnected',
  CONNECTING: 'connecting',
  CONNECTED: 'connected',
  ERROR: 'error'
};

/**
 * Unified WebSocket Communicator Class
 * Consolidates BackendCommunicator and ConnectionManager functionality
 */
class WebSocketCommunicator {
  constructor(config = {}) {
    // Singleton pattern
    if (WebSocketCommunicator.instance) {
      return WebSocketCommunicator.instance;
    }
    
    WebSocketCommunicator.instance = this;
    
    // Connection state
    this.state = CommunicatorState.DISCONNECTED;
    this.baseUrl = config.baseUrl || 'http://localhost:5000';
    this.port = config.port || 5000;
    
    // WebSocket client reference
    this.webSocketClient = null;
    
    // Session manager reference
    this.sessionManager = null;
    
    // Settings manager reference
    this.settingsManager = null;
    
    // Dice roll executor reference
    this.diceRollExecutor = null;
    
    // World state collector reference
    this.worldStateCollector = null;
    
    // Initialization control
    this.initPromise = null;
    this.isInitializing = false;
    
    // Configuration
    this.defaultPort = config.defaultPort || 5000;
    this.standardPorts = [5000, 5001, 5002];
    
    console.log('WebSocketCommunicator: Initialized singleton instance');
  }

  /**
   * Set SessionManager reference
   * @param {SessionManager} sessionManager - Session manager instance
   */
  setSessionManager(sessionManager) {
    this.sessionManager = sessionManager;
    this.setupSessionManagerCallbacks();
    console.log('WebSocketCommunicator: Session manager set');
  }

  /**
   * Set SettingsManager reference
   * @param {SettingsManager} settingsManager - Settings manager instance
   */
  setSettingsManager(settingsManager) {
    this.settingsManager = settingsManager;
    console.log('WebSocketCommunicator: Settings manager set');
  }

  /**
   * Set WebSocket client reference
   * @param {GoldBoxWebSocketClient} webSocketClient - WebSocket client instance
   */
  async setWebSocketClient(webSocketClient) {
    this.webSocketClient = webSocketClient;
    console.log('WebSocketCommunicator: WebSocket client set');
    
    // Initialize DiceRollExecutor and register handlers
    await this.initializeDiceRollExecutor();
  }

  /**
   * Initialize Dice Roll Executor
   * @private
   */
  async initializeDiceRollExecutor() {
    try {
      if (typeof DiceRollExecutor !== 'undefined') {
        this.diceRollExecutor = new DiceRollExecutor();
        
        // Register message handlers with WebSocket client
        const handlers = this.diceRollExecutor.getMessageHandlers();
        for (const [messageType, handler] of Object.entries(handlers)) {
          this.webSocketClient.onMessageType(messageType, handler);
          console.log(`WebSocketCommunicator: Registered handler for ${messageType}`);
        }
        
        // Store executor globally for access from other scripts
        window.diceRollExecutor = this.diceRollExecutor;
        console.log('WebSocketCommunicator: DiceRollExecutor initialized');
      } else {
        console.warn('WebSocketCommunicator: DiceRollExecutor not available');
      }
    } catch (error) {
      console.error('WebSocketCommunicator: Error initializing DiceRollExecutor:', error);
    }
    
    // Initialize combat state refresh handler
    this.initializeCombatStateRefreshHandler();
    
    // Initialize combat monitor handlers
    this.initializeCombatMonitorHandlers();
    
    // Initialize world state collector
    await this.initializeWorldStateCollector();
    
    // Initialize actor details handler
    this.initializeActorDetailsHandler();
    
    // Initialize scene spatial data handler
    this.initializeSceneSpatialDataHandler();
    
    // Initialize journal context handler
    this.initializeJournalContextHandler();
    
    // Initialize compendium search handler
    this.initializeCompendiumSearchHandler();
    
    // Initialize party members handler
    this.initializePartyMembersHandler();
  }

  /**
   * Initialize Combat Monitor Handlers
   * @private
   */
  initializeCombatMonitorHandlers() {
    try {
      if (!this.webSocketClient) {
        console.warn('WebSocketCommunicator: WebSocket client not available for combat monitor handlers');
        return;
      }
      
      // Check if CombatMonitor is available and has registerWebSocketHandlers method
      if (window.CombatMonitor && typeof window.CombatMonitor.registerWebSocketHandlers === 'function') {
        console.log('WebSocketCommunicator: Registering CombatMonitor handlers');
        window.CombatMonitor.registerWebSocketHandlers();
        console.log('WebSocketCommunicator: CombatMonitor handlers initialized');
      } else {
        console.warn('WebSocketCommunicator: CombatMonitor not available or registerWebSocketHandlers not found');
      }
    } catch (error) {
      console.error('WebSocketCommunicator: Error initializing combat monitor handlers:', error);
    }
  }

  /**
   * Initialize Combat State Refresh Handler
   * @private
   */
  initializeCombatStateRefreshHandler() {
    try {
      if (!this.webSocketClient) {
        console.warn('WebSocketCommunicator: WebSocket client not available for combat state refresh handler');
        return;
      }
      
      // Register handler for combat_state_refresh messages
      this.webSocketClient.onMessageType('combat_state_refresh', async (message) => {
        console.log('WebSocketCommunicator: Received combat_state_refresh request');
        
        try {
          // Store request_id for response correlation
          if (message.request_id) {
            if (window.CombatMonitor) {
              window.CombatMonitor.lastRequestId = message.request_id;
              console.log('WebSocketCommunicator: Stored request_id for combat_state_refresh:', message.request_id);
            }
          }
          
          // Check if CombatMonitor is available
          if (window.CombatMonitor && typeof window.CombatMonitor.transmitCombatState === 'function') {
            // Transmit current combat state
            await window.CombatMonitor.transmitCombatState();
            console.log('WebSocketCommunicator: Combat state transmitted in response to refresh request');
          } else {
            console.warn('WebSocketCommunicator: CombatMonitor not available or transmitCombatState not found');
          }
        } catch (error) {
          console.error('WebSocketCommunicator: Error handling combat_state_refresh:', error);
        }
      });
      
      // Register handler for world_state_refresh messages
      this.webSocketClient.onMessageType('world_state_refresh', async (message) => {
        console.log('WebSocketCommunicator: Received world_state_refresh request');
        
        try {
          // Check if WorldStateCollector is available
          if (this.worldStateCollector && typeof this.worldStateCollector.sendWorldState === 'function') {
            // Send current world state
            await this.worldStateCollector.sendWorldState();
            console.log('WebSocketCommunicator: World state transmitted in response to refresh request');
          } else {
            console.warn('WebSocketCommunicator: WorldStateCollector not available or sendWorldState not found');
          }
        } catch (error) {
          console.error('WebSocketCommunicator: Error handling world_state_refresh:', error);
        }
      });
      
      console.log('WebSocketCommunicator: Combat state refresh handler initialized');
      console.log('WebSocketCommunicator: Combat state refresh handler initialized');
      
    } catch (error) {
      console.error('WebSocketCommunicator: Error initializing combat state refresh handler:', error);
    }
  }

  /**
   * Initialize World State Collector
   * @private
   */
  async initializeWorldStateCollector() {
    try {
      if (typeof getWorldStateCollector !== 'undefined') {
        this.worldStateCollector = getWorldStateCollector();
        
        // Initialize the collector (now async)
        await this.worldStateCollector.initialize();
        
        // Store globally for access from other scripts
        window.goldBoxWorldStateCollector = this.worldStateCollector;
        
        console.log('WebSocketCommunicator: WorldStateCollector initialized');
      } else {
        console.warn('WebSocketCommunicator: WorldStateCollector not available');
      }
    } catch (error) {
      console.error('WebSocketCommunicator: Error initializing World State Collector:', error);
    }
  }

  /**
   * Initialize Actor Details Handler
   * @private
   */
  initializeActorDetailsHandler() {
    try {
      if (!this.webSocketClient) {
        console.warn('WebSocketCommunicator: WebSocket client not available for actor details handler');
        return;
      }
      
      // Register handler for get_actor_details messages
      this.webSocketClient.onMessageType('get_actor_details', async (message) => {
        console.log('WebSocketCommunicator: Received get_actor_details request');
        
        try {
          const tokenId = message.data?.token_id;
          const searchPhrase = message.data?.search_phrase || '';
          
          if (!tokenId) {
            console.error('WebSocketCommunicator: get_actor_details missing token_id');
            return;
          }
          
          // Get actor details from WorldStateCollector
          const result = await this.worldStateCollector?.getTokenActorDetails(tokenId, searchPhrase);
          
          if (result && result.success !== false) {
            // Send actor details response back to backend
            const responseMessage = {
              type: 'token_actor_details',
              request_id: message.request_id,
              data: result,
              timestamp: Date.now()
            };
            
            await this.webSocketClient.send(responseMessage);
            console.log('WebSocketCommunicator: Actor details transmitted for token', tokenId);
          } else {
            console.error('WebSocketCommunicator: Failed to get actor details:', result?.error);
          }
        } catch (error) {
          console.error('WebSocketCommunicator: Error handling get_actor_details:', error);
        }
      });
      
      // Register handler for modify_token_attribute messages
      this.webSocketClient.onMessageType('modify_token_attribute', async (message) => {
        console.log('WebSocketCommunicator: Received modify_token_attribute request');
        
        try {
          const tokenId = message.data?.token_id;
          const attributePath = message.data?.attribute_path;
          const value = message.data?.value;
          const isDelta = message.data?.is_delta !== false; // Default to true
          const isBar = message.data?.is_bar !== false; // Default to true
          
          if (!tokenId || !attributePath || value === undefined || value === null) {
            console.error('WebSocketCommunicator: modify_token_attribute missing required parameters');
            return;
          }
          
      // Validate token_id before attempting modification
      if (!tokenId || typeof tokenId !== 'string' || tokenId.trim() === '') {
        console.error(`WebSocketCommunicator: modify_token_attribute invalid tokenId: "${tokenId}"`);
        
        // Send error response back to backend immediately
        const errorMessage = `Invalid token ID: "${tokenId || '(empty)'}"`;
        await this.webSocketClient.send({
          type: 'combat_state',
          request_id: message.request_id,
          data: {
            combat_state: {
                  in_combat: false,
                  combat_id: null,
                  round: 0,
                  turn: 0,
                  combatants: [],
                  last_updated: Date.now(),
                  error: errorMessage
                }
          },
          timestamp: Date.now()
        });
        console.log(`WebSocketCommunicator: Sent error response: ${errorMessage}`);
        return;
      }
      
      // Validate attribute_path
      if (!attributePath || typeof attributePath !== 'string' || attributePath.trim() === '') {
        console.error(`WebSocketCommunicator: modify_token_attribute invalid attributePath: "${attributePath}"`);
        
        // Send error response back to backend immediately
        const errorMessage = `Invalid attribute path: "${attributePath || '(empty)'}"`;
        await this.webSocketClient.send({
          type: 'combat_state',
          request_id: message.request_id,
          data: {
            combat_state: {
                  in_combat: false,
                  combat_id: null,
                  round: 0,
                  turn: 0,
                  combatants: [],
                  last_updated: Date.now(),
                  error: errorMessage
                }
          },
          timestamp: Date.now()
        });
        console.log(`WebSocketCommunicator: Sent error response: ${errorMessage}`);
        return;
      }
      
      // Validate value
      if (value === undefined || value === null) {
        console.error(`WebSocketCommunicator: modify_token_attribute invalid value: ${value}`);
        
        // Send error response back to backend immediately
        const errorMessage = 'Value is undefined or null';
        await this.webSocketClient.send({
          type: 'combat_state',
          request_id: message.request_id,
          data: {
            combat_state: {
                  in_combat: false,
                  combat_id: null,
                  round: 0,
                  turn: 0,
                  combatants: [],
                  last_updated: Date.now(),
                  error: errorMessage
                }
          },
          timestamp: Date.now()
        });
        console.log(`WebSocketCommunicator: Sent error response: ${errorMessage}`);
        return;
      }
      
      console.log(`WebSocketCommunicator: Attempting to modify token ${tokenId}, path: ${attributePath}, value: ${value}, isDelta: ${isDelta}, isBar: ${isBar}, request_id: ${message.request_id}`);
      
      // Modify token attribute from WorldStateCollector
      const result = await this.worldStateCollector?.modifyTokenAttribute(tokenId, attributePath, value, isDelta, isBar);
      
      if (result && result.success) {
        // Send combat state response back to backend (token modification triggers combat state update)
        const responseMessage = {
          type: 'combat_state',
          request_id: message.request_id,
          data: {
            combat_state: result.combat_state || {
                  in_combat: false,
                  combat_id: null,
                  round: 0,
                  turn: 0,
                  combatants: [],
                  last_updated: Date.now()
                }
          },
          timestamp: Date.now()
        };
      
        await this.webSocketClient.send(responseMessage);
        console.log('WebSocketCommunicator: Token attribute modified, combat state transmitted');
      } else if (result) {
        // Send error response back to backend
        const errorMessage = result.error || 'Unknown error';
        await this.webSocketClient.send({
          type: 'combat_state',
          request_id: message.request_id,
          data: {
            combat_state: {
                  in_combat: false,
                  combat_id: null,
                  round: 0,
                  turn: 0,
                  combatants: [],
                  last_updated: Date.now(),
                  error: errorMessage
                }
          },
          timestamp: Date.now()
        });
        console.error('WebSocketCommunicator: Failed to modify token attribute:', errorMessage);
      } else {
        // Send error response for no result
        const errorMessage = 'No result returned from modifyTokenAttribute';
        await this.webSocketClient.send({
          type: 'combat_state',
          request_id: message.request_id,
          data: {
            combat_state: {
                  in_combat: false,
                  combat_id: null,
                  round: 0,
                  turn: 0,
                  combatants: [],
                  last_updated: Date.now(),
                  error: errorMessage
                }
          },
          timestamp: Date.now()
        });
        console.error('WebSocketCommunicator: No result returned from modifyTokenAttribute');
      }
    } catch (error) {
      console.error('WebSocketCommunicator: Error handling modify_token_attribute:', error);
      
      // Send error response back to backend on exception
      const errorMessage = error.message || 'Unknown error';
      await this.webSocketClient.send({
        type: 'combat_state',
        request_id: message.request_id,
        data: {
          combat_state: {
                in_combat: false,
                combat_id: null,
                round: 0,
                turn: 0,
                combatants: [],
                last_updated: Date.now(),
                error: errorMessage
              }
        },
        timestamp: Date.now()
      });
      console.error(`WebSocketCommunicator: Sent error response on exception: ${errorMessage}`);
    }
      });
      
      console.log('WebSocketCommunicator: Actor details handler initialized');
    } catch (error) {
      console.error('WebSocketCommunicator: Error initializing DiceRollExecutor:', error);
    }
    
    // Initialize Scene Spatial Data Handler
    this.initializeSceneSpatialDataHandler();
    
    // Initialize Journal Context Handler
    this.initializeJournalContextHandler();
  }

  /**
   * Initialize Scene Spatial Data Handler
   * @private
   */
  initializeSceneSpatialDataHandler() {
    try {
      if (!this.webSocketClient) {
        console.warn('WebSocketCommunicator: WebSocket client not available for scene spatial data handler');
        return;
      }
      
      // Register handler for get_scene_spatial_data messages
      this.webSocketClient.onMessageType('get_scene_spatial_data', async (message) => {
        console.log('WebSocketCommunicator: Received get_scene_spatial_data request');
        
        try {
          // Check if WorldStateCollector is available
          if (this.worldStateCollector && typeof this.worldStateCollector.collectSceneSpatialData === 'function') {
            // Collect scene spatial data
            const sceneData = this.worldStateCollector.collectSceneSpatialData();
            
            if (sceneData) {
              // Send scene data response back to backend
              const responseMessage = {
                type: 'scene_spatial_data',
                request_id: message.request_id,
                data: sceneData,
                timestamp: Date.now()
              };
              
              await this.webSocketClient.send(responseMessage);
              console.log('WebSocketCommunicator: Scene spatial data transmitted');
            } else {
              console.warn('WebSocketCommunicator: Failed to collect scene data');
              
              // Send error response
              const errorMessage = 'Failed to collect scene data';
              await this.webSocketClient.send({
                type: 'scene_spatial_data',
                request_id: message.request_id,
                data: {
                  error: errorMessage,
                  scene_id: null,
                  scene_name: 'Unknown'
                },
                timestamp: Date.now()
              });
            }
          } else {
            console.warn('WebSocketCommunicator: WorldStateCollector not available or collectSceneSpatialData not found');
          }
        } catch (error) {
          console.error('WebSocketCommunicator: Error handling get_scene_spatial_data:', error);
        }
      });
      
      console.log('WebSocketCommunicator: Scene spatial data handler initialized');
    } catch (error) {
      console.error('WebSocketCommunicator: Error initializing scene spatial data handler:', error);
    }
  }

  /**
   * Initialize Journal Context Handler
   * @private
   */
  initializeJournalContextHandler() {
    try {
      if (!this.webSocketClient) {
        console.warn('WebSocketCommunicator: WebSocket client not available for journal context handler');
        return;
      }
      
      // Register handler for get_journal_context messages
      this.webSocketClient.onMessageType('get_journal_context', async (message) => {
        console.log('WebSocketCommunicator: Received get_journal_context request');
        
        try {
          const entryName = message.data?.entry_name;
          const searchPhrase = message.data?.search_phrase;
          const contextLines = message.data?.context_lines || 3;
          
          if (!entryName || !searchPhrase) {
            console.error('WebSocketCommunicator: get_journal_context missing required parameters');
            return;
          }
          
          // Store request_id for response correlation
          if (this.worldStateCollector) {
            this.worldStateCollector.lastRequestId = message.request_id;
          }
          
          // Get journal context from WorldStateCollector
          const result = await this.worldStateCollector?.getJournalContext(entryName, searchPhrase, contextLines);
          
          if (result && result.success !== false) {
            // Send journal context response back to backend
            const responseMessage = {
              type: 'journal_context',
              request_id: message.request_id,
              data: result,
              timestamp: Date.now()
            };
            
            await this.webSocketClient.send(responseMessage);
            console.log('WebSocketCommunicator: Journal context transmitted for entry', entryName);
          } else {
            console.error('WebSocketCommunicator: Failed to get journal context:', result?.error);
          }
        } catch (error) {
          console.error('WebSocketCommunicator: Error handling get_journal_context:', error);
        }
      });
      
      console.log('WebSocketCommunicator: Journal context handler initialized');
    } catch (error) {
      console.error('WebSocketCommunicator: Error initializing journal context handler:', error);
    }
  }

  /**
   * Initialize Compendium Search Handler
   * @private
   */
  initializeCompendiumSearchHandler() {
    try {
      if (!this.webSocketClient) {
        console.warn('WebSocketCommunicator: WebSocket client not available for compendium search handler');
        return;
      }
      
      // Register handler for search_compendium messages
      this.webSocketClient.onMessageType('search_compendium', async (message) => {
        console.log('WebSocketCommunicator: Received search_compendium request');
        
        try {
          const packName = message.data?.pack_name;
          const query = message.data?.query;
          
          if (!packName || !query) {
            console.error('WebSocketCommunicator: search_compendium missing required parameters');
            return;
          }
          
          // Get compendium search results from WorldStateCollector
          const result = await this.worldStateCollector?.searchCompendium(packName, query);
          
          if (result && result.success !== false) {
            // Send compendium results response back to backend
            const responseMessage = {
              type: 'compendium_results',
              request_id: message.request_id,
              data: result,
              timestamp: Date.now()
            };
            
            await this.webSocketClient.send(responseMessage);
            console.log('WebSocketCommunicator: Compendium search results transmitted for pack', packName);
          } else {
            console.error('WebSocketCommunicator: Failed to search compendium:', result?.error);
          }
        } catch (error) {
          console.error('WebSocketCommunicator: Error handling search_compendium:', error);
        }
      });
      
      console.log('WebSocketCommunicator: Compendium search handler initialized');
    } catch (error) {
      console.error('WebSocketCommunicator: Error initializing compendium search handler:', error);
    }
  }

  /**
   * Initialize Party Members Handler
   * @private
   */
  initializePartyMembersHandler() {
    try {
      if (!this.webSocketClient) {
        console.warn('WebSocketCommunicator: WebSocket client not available for party members handler');
        return;
      }
      
      // Register handler for get_party_members messages
      this.webSocketClient.onMessageType('get_party_members', async (message) => {
        console.log('WebSocketCommunicator: Received get_party_members request');
        
        try {
          // Get party members from WorldStateCollector
          const result = this.worldStateCollector?.getPartyMembers();
          
          if (result) {
            // Send party members response back to backend
            const responseMessage = {
              type: 'party_members',
              request_id: message.request_id,
              data: result,
              timestamp: Date.now()
            };
            
            await this.webSocketClient.send(responseMessage);
            console.log('WebSocketCommunicator: Party members transmitted');
          } else {
            console.error('WebSocketCommunicator: Failed to get party members');
          }
        } catch (error) {
          console.error('WebSocketCommunicator: Error handling get_party_members:', error);
        }
      });
      
      console.log('WebSocketCommunicator: Party members handler initialized');
    } catch (error) {
      console.error('WebSocketCommunicator: Error initializing party members handler:', error);
    }
  }

  /**
   * Initialize WebSocket communication
   * @returns {Promise<boolean>} - True if initialization successful
   */
  async initialize() {
    // If already connecting, wait for existing initialization
    if (this.initPromise) {
      console.log('WebSocketCommunicator: Initialization already in progress, waiting...');
      return this.initPromise;
    }
    
    // If already connected, return success
    if (this.state === CommunicatorState.CONNECTED && this.isSessionValid()) {
      console.log('WebSocketCommunicator: Already connected with valid session');
      return true;
    }
    
    // Create initialization promise
    this.initPromise = this._performInitialization();
    
    try {
      const result = await this.initPromise;
      return result;
    } finally {
      this.initPromise = null;
    }
  }

  /**
   * Perform actual initialization
   * @private
   */
  async _performInitialization() {
    // Prevent race conditions - if already initializing, wait for current init
    if (this.isInitializing) {
      console.log('WebSocketCommunicator: Initialization already in progress, waiting...');
      return this.initPromise;
    }
    
    try {
      this.isInitializing = true;
      this.setState(CommunicatorState.CONNECTING);
      console.log('WebSocketCommunicator: Starting WebSocket initialization...');
      
      // Step 1: Discover backend port (HTTP health check only)
      const port = await this.discoverBackendPort();
      if (!port) {
        throw new Error('No backend server found on any port. Please start the backend server first.');
      }
      
      this.port = port;
      this.baseUrl = `http://localhost:${port}`;
      console.log(`WebSocketCommunicator: Found backend on port ${port}`);
      
      // Step 2: Initialize session if session manager is available
      if (this.sessionManager) {
        const sessionInitialized = await this.sessionManager.initializeSession(this.baseUrl);
        if (!sessionInitialized) {
          throw new Error('Failed to initialize session');
        }
        
        // Start session monitoring
        this.sessionManager.startHealthMonitoring(this.baseUrl);
        this.sessionManager.setupVisibilityChangeHandler();
      }
      
      this.setState(CommunicatorState.CONNECTED);
      console.log('WebSocketCommunicator: Successfully connected to backend');
      
      return true;
      
    } catch (error) {
      this.setState(CommunicatorState.ERROR);
      console.error('WebSocketCommunicator: Initialization failed:', error);
      throw error;
    } finally {
      this.isInitializing = false;
    }
  }

  /**
   * Discover backend port using HTTP health check only
   * @returns {Promise<number|null>} - Port number or null
   */
  async discoverBackendPort() {
    console.log('WebSocketCommunicator: Discovering backend port via HTTP health check...');
    
    // Try environment override first
    const envPort = this.getEnvironmentPortOverride();
    if (envPort) {
      console.log(`WebSocketCommunicator: Using environment override port: ${envPort}`);
      return envPort;
    }
    
    // Try HTTP health check on standard ports
    for (const port of this.standardPorts) {
      try {
        console.log(`WebSocketCommunicator: Testing HTTP health check on port ${port}...`);
        
        const response = await fetch(`http://localhost:${port}/api/health`, {
          method: 'GET',
          signal: AbortSignal.timeout(5000) // 5 second timeout (increased from 2s to handle slow systems)
        });
        
        if (response.ok) {
          const data = await response.json();
          // Verify it's our backend
          if (data.service === 'The Gold Box Backend' || data.version) {
            console.log(`WebSocketCommunicator: Backend confirmed on port ${port}`);
            return port;
          }
        }
        
      } catch (error) {
        console.log(`WebSocketCommunicator: Health check failed for port ${port}:`, error.message);
      }
    }
    
    return null;
  }

  /**
   * Get port from environment variable override
   * @returns {number|null} - Port number or null
   */
  getEnvironmentPortOverride() {
    try {
      // Check localStorage first
      if (window.localStorage) {
        const overridePort = localStorage.getItem('GOLD_BOX_PORT_OVERRIDE');
        if (overridePort) {
          const port = parseInt(overridePort);
          if (!isNaN(port) && port >= 1024 && port <= 65535) {
            return port;
          }
        }
      }
      
      // Check global window object for testing
      if (window.GOLD_BOX_PORT_OVERRIDE) {
        const port = parseInt(window.GOLD_BOX_PORT_OVERRIDE);
        if (!isNaN(port) && port >= 1024 && port <= 65535) {
          return port;
        }
      }
      
      return null;
    } catch (error) {
      console.warn('WebSocketCommunicator: Environment override check failed:', error);
      return null;
    }
  }

  /**
   * Setup callbacks for SessionManager events
   * @private
   */
  setupSessionManagerCallbacks() {
    if (!this.sessionManager) return;
    
    this.sessionManager.setCallbacks({
      onSessionExpired: () => {
        console.log('WebSocketCommunicator: Session expired, attempting refresh');
        this.sessionManager.refreshSession(this.baseUrl);
      },
      onCriticalState: (sessionInfo) => {
        console.log('WebSocketCommunicator: Session in critical state');
      },
      onSessionCreated: (sessionData) => {
        console.log('WebSocketCommunicator: New session created');
      },
      onSessionExtended: (sessionData) => {
        console.log('WebSocketCommunicator: Session extended');
      },
      onSessionRefreshed: (sessionData) => {
        console.log('WebSocketCommunicator: Session refreshed');
      }
    });
  }

  /**
   * Check if session is valid (delegated to SessionManager)
   * @returns {boolean} - True if session is valid
   */
  isSessionValid() {
    return this.sessionManager ? this.sessionManager.isSessionValid() : true;
  }

  /**
   * Send chat request via WebSocket (primary communication method)
   * @param {Array} messages - Chat messages
   * @param {Object} options - Additional options
   * @returns {Promise<Object>} - Response data
   */
  async sendChatRequest(messages, options = {}) {
    // Ensure we're connected
    if (this.state !== CommunicatorState.CONNECTED || !this.isSessionValid()) {
      await this.initialize();
    }
    
    // WebSocket required - no fallbacks
    if (!this.webSocketClient || !this.webSocketClient.isConnected) {
      throw new Error('WebSocket connection required. Please ensure backend server is running and WebSocket client is connected.');
    }
    
    try {
      console.log('WebSocketCommunicator: Sending chat request via WebSocket');
      
      // Sync settings to backend first (frontend is source of truth)
      await this.syncSettingsToBackend();
      
      // Add combat state to request if available
      const combatState = this.getCombatStateForRequest();
      if (combatState) {
        options.combat_state = combatState;
        console.log('WebSocketCommunicator: Added combat state to request:', combatState);
      }
      
      const response = await this.webSocketClient.sendChatRequest(messages, options);
      
      return {
        success: true,
        data: response.data || response,
        metadata: { websocket_mode: true }
      };
      
    } catch (error) {
      console.error('WebSocketCommunicator: Chat request failed:', error);
      throw new Error(`WebSocket communication failed: ${error.message}. Please restart the backend server.`);
    }
  }

  /**
   * Sync settings to backend (frontend is source of truth)
   * @returns {Promise<Object>} - Sync result
   */
  async syncSettingsToBackend() {
    if (!this.settingsManager) {
      console.warn('WebSocketCommunicator: No settings manager available, skipping sync');
      return { success: false, error: 'Settings manager not available' };
    }
    
    try {
      const settings = this.settingsManager.getAllSettings();
      const adminPassword = settings['backend password'];
      
      if (!adminPassword || !adminPassword.trim()) {
        console.warn('WebSocketCommunicator: No backend password configured, skipping settings sync');
        return { success: false, error: 'Backend password not configured' };
      }
      
      // Send settings sync via WebSocket
      const syncMessage = {
        type: 'settings_sync',
        data: {
          settings: settings,
          timestamp: Date.now()
        }
      };
      
      await this.webSocketClient.send(syncMessage);
      console.log('WebSocketCommunicator: Settings synced to backend');
      return { success: true };
      
    } catch (error) {
      console.error('WebSocketCommunicator: Settings sync failed:', error);
      return { success: false, error: error.message };
    }
  }

  /**
   * Send data via real-time synchronization
   * @param {string} syncType - Type of sync data
   * @param {Object} syncData - Data to synchronize
   * @returns {Promise<boolean>} - Success status
   */
  async syncDataRealTime(syncType, syncData) {
    if (!this.webSocketClient || !this.webSocketClient.isConnected) {
      throw new Error('WebSocket connection required for real-time sync. Please ensure backend server is running.');
    }
    
    try {
      const syncMessage = {
        type: 'data_sync',
        data: {
          sync_type: syncType,
          sync_data: syncData,
          timestamp: Date.now()
        }
      };
      
      await this.webSocketClient.send(syncMessage);
      console.log(`WebSocketCommunicator: Real-time sync sent for ${syncType}`);
      return true;
      
    } catch (error) {
      console.error('WebSocketCommunicator: Real-time sync failed:', error);
      throw new Error(`Real-time sync failed: ${error.message}. Please restart the backend server.`);
    }
  }

  /**
   * Test backend connection (HTTP health check only)
   * @returns {Promise<Object>} - Connection test result
   */
  async testConnection() {
    try {
      const response = await fetch(`${this.baseUrl}/api/health`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json'
        }
      });

      if (response.ok) {
        const data = await response.json();
        return {
          success: true,
          data: data
        };
      } else {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }
    } catch (error) {
      return {
        success: false,
        error: error.message
      };
    }
  }

  /**
   * Get current connection state
   * @returns {string} - Current state
   */
  getState() {
    return this.state;
  }

  /**
   * Get current connection info
   * @returns {Object} - Connection info
   */
  getConnectionInfo() {
    const info = {
      state: this.state,
      baseUrl: this.baseUrl,
      port: this.port,
      hasWebSocketClient: !!this.webSocketClient,
      isConnected: this.state === CommunicatorState.CONNECTED
    };
    
    // Add session info if available
    if (this.sessionManager) {
      const sessionInfo = this.sessionManager.getSessionInfo();
      info.hasValidSession = this.isSessionValid();
      info.sessionId = sessionInfo.sessionId;
      info.sessionExpiry = sessionInfo.sessionExpiry;
      info.sessionState = sessionInfo.sessionState;
      info.timeToExpiry = sessionInfo.timeToExpiry;
    }
    
    return info;
  }

  /**
   * Set connection state
   * @private
   */
  setState(newState) {
    const oldState = this.state;
    this.state = newState;
    
    if (oldState !== newState) {
      console.log(`WebSocketCommunicator: State changed from ${oldState} to ${newState}`);
    }
  }

  /**
   * Get combat state for request (integrates with CombatMonitor)
   * @returns {Object|null} - Combat state or null
   */
  getCombatStateForRequest() {
    try {
      // Check if CombatMonitor is available
      if (window.CombatMonitor) {
        const combatMonitor = window.CombatMonitor;
        if (typeof combatMonitor.getCurrentCombatState === 'function') {
          return combatMonitor.getCombatStateForBackend();
        }
      }
      
      // Fallback: try to get basic combat info directly
      if (window.game && window.game.combat) {
        const combat = window.game.combat;
        if (combat && combat.started) {
          const combatants = combat.combatants.map(c => ({
            name: c.name,
            initiative: c.initiative || 0,
            is_player: c.hasPlayerOwner,
            is_current_turn: combat.current === c._id
          }));
          
          return {
            in_combat: true,
            combat_id: combat._id,
            round: combat.round || 0,
            turn: combat.turn || 0,
            combatants: combatants
          };
        }
      }
      
      return null;
      
    } catch (error) {
      console.warn('WebSocketCommunicator: Error getting combat state:', error);
      return null;
    }
  }

  /**
   * Disconnect and cleanup
   */
  disconnect() {
    console.log('WebSocketCommunicator: Disconnecting...');
    
    // Clear session if session manager is available
    if (this.sessionManager) {
      this.sessionManager.clearSession();
    }
    
    // Disconnect WebSocket client
    if (this.webSocketClient) {
      this.webSocketClient.disconnect();
    }
    
    // Clear references
    this.webSocketClient = null;
    this.sessionManager = null;
    this.settingsManager = null;
    
    // Reset state
    this.setState(CommunicatorState.DISCONNECTED);
    
    // Clear initialization promise
    this.initPromise = null;
    
    console.log('WebSocketCommunicator: Cleanup complete');
  }
}

// Export for global access
window.WebSocketCommunicator = WebSocketCommunicator;
window.CommunicatorState = CommunicatorState;
