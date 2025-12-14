/**
 * Connection Manager for Gold Box Backend
 * WebSocket-first implementation with HTTP fallback
 * Phase 4: Removed Relay Server dependency
 * Refactored: Session management extracted to SessionManager
 */

/**
 * Connection States
 */
const ConnectionState = {
  DISCONNECTED: 'disconnected',
  CONNECTING: 'connecting',
  CONNECTED: 'connected',
  ERROR: 'error'
};

/**
 * Connection Types
 */
const ConnectionType = {
  WEBSOCKET: 'websocket'
};

/**
 * Connection Manager Class
 */
class ConnectionManager {
  constructor() {
    // Singleton pattern
    if (ConnectionManager.instance) {
      return ConnectionManager.instance;
    }
    
    ConnectionManager.instance = this;
    
    // Connection state
    this.state = ConnectionState.DISCONNECTED;
    this.connectionType = ConnectionType.WEBSOCKET; // WebSocket-first approach
    this.baseUrl = 'http://localhost:5000';
    this.port = 5000;
    
    // WebSocket client reference
    this.webSocketClient = null;
    
    // Session Manager (extracted concern)
    this.sessionManager = new window.SessionManager();
    
    // Initialization control
    this.initPromise = null;
    this.initQueue = [];
    
    // Configuration (simplified)
    this.defaultPort = 5000;
    
    console.log('ConnectionManager: Initialized singleton instance');
  }
  
  /**
   * Set WebSocket client reference
   * @param {GoldBoxWebSocketClient} webSocketClient - WebSocket client instance
   */
  setWebSocketClient(webSocketClient) {
    this.webSocketClient = webSocketClient;
    this.connectionType = ConnectionType.WEBSOCKET;
    console.log('ConnectionManager: WebSocket client set, connection type:', this.connectionType);
  }

  /**
   * Initialize connection to backend (WebSocket-first approach)
   * @returns {Promise<boolean>} - True if connection successful
   */
  async initialize() {
    // If already connecting, wait for existing initialization
    if (this.initPromise) {
      console.log('ConnectionManager: Initialization already in progress, waiting...');
      return this.initPromise;
    }
    
    // If already connected, return success
    if (this.state === ConnectionState.CONNECTED && this.sessionManager.isSessionValid()) {
      console.log('ConnectionManager: Already connected with valid session');
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
    try {
      this.setState(ConnectionState.CONNECTING);
      console.log('ConnectionManager: Starting backend connection...');
      
      // Step 1: Discover backend port
      const port = await this.discoverBackendPort();
      if (!port) {
        console.log('ConnectionManager: No backend server found on any port');
        this.setState(ConnectionState.DISCONNECTED);
        return false;
      }
      
      this.port = port;
      this.baseUrl = `http://localhost:${port}`;
      console.log(`ConnectionManager: Found backend on port ${port}`);
      
      // Step 2: Initialize session using SessionManager
      const sessionInitialized = await this.sessionManager.initializeSession(this.baseUrl);
      if (!sessionInitialized) {
        console.log('ConnectionManager: Failed to initialize session');
        this.setState(ConnectionState.ERROR);
        return false;
      }
      
      // Setup session manager callbacks
      this.setupSessionManagerCallbacks();
      
      // Start session monitoring
      this.sessionManager.startHealthMonitoring(this.baseUrl);
      this.sessionManager.setupVisibilityChangeHandler();
      
      this.setState(ConnectionState.CONNECTED);
      console.log('ConnectionManager: Successfully connected to backend');
      
      return true;
      
    } catch (error) {
      this.setState(ConnectionState.ERROR);
      console.error('ConnectionManager: Initialization failed:', error);
      return false;
    }
  }


  /**
   * Discover backend port using browser-compatible methods (WebSocket-first, HTTP fallback)
   * @returns {Promise<number|null>} - Port number or null
   */
  async discoverBackendPort() {
    console.log('ConnectionManager: Starting browser-compatible port discovery...');
    
    // Try environment override first
    const envPort = this.getEnvironmentPortOverride();
    if (envPort) {
      console.log(`ConnectionManager: Using environment override port: ${envPort}`);
      return envPort;
    }
    
    // Try WebSocket discovery first (primary method)
    const wsPort = await this.tryWebSocketPortDiscovery();
    if (wsPort) {
      console.log(`ConnectionManager: Using WebSocket-discovered port: ${wsPort}`);
      return wsPort;
    }
    
    // Fallback to HTTP health check
    const httpPort = await this.tryHttpPortDiscovery();
    if (httpPort) {
      console.log(`ConnectionManager: Using HTTP-discovered port: ${httpPort}`);
      return httpPort;
    }
    
    throw new Error('No backend server found on any standard port. Please start the backend server first.');
  }

  /**
   * Get port from environment variable override
   * @returns {number|null} - Port number or null
   */
  getEnvironmentPortOverride() {
    try {
      // Check for browser-compatible environment detection
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
      console.warn('ConnectionManager: Environment override check failed:', error);
      return null;
    }
  }

  /**
   * Try to discover port via WebSocket connections
   * @returns {Promise<number|null>} - Port number or null
   */
  async tryWebSocketPortDiscovery() {
    const standardPorts = [5000, 5001, 5002];
    
    for (const port of standardPorts) {
      try {
        console.log(`ConnectionManager: Testing WebSocket port ${port}...`);
        
        const wsUrl = `ws://localhost:${port}/ws`;
        const testWs = new WebSocket(wsUrl);
        
        // Create a promise that resolves when connection succeeds or fails
        const connectionResult = await Promise.race([
          new Promise((resolve) => {
            testWs.onopen = () => {
              testWs.close();
              resolve(port);
            };
            testWs.onerror = () => resolve(null);
          }),
          new Promise(resolve => setTimeout(() => {
            testWs.close();
            resolve(null);
          }, 1000)) // 1 second timeout
        ]);
        
        if (connectionResult === port) {
          console.log(`ConnectionManager: WebSocket connection successful on port ${port}`);
          return port;
        }
        
      } catch (error) {
        console.log(`ConnectionManager: WebSocket test failed for port ${port}:`, error.message);
      }
    }
    
    return null;
  }

  /**
   * Try to discover port via HTTP health checks
   * @returns {Promise<number|null>} - Port number or null
   */
  async tryHttpPortDiscovery() {
    const standardPorts = [5000, 5001, 5002];
    
    for (const port of standardPorts) {
      try {
        console.log(`ConnectionManager: Testing HTTP port ${port}...`);
        
        const response = await fetch(`http://localhost:${port}/api/health`, {
          method: 'GET',
          signal: AbortSignal.timeout(2000) // 2 second timeout
        });
        
        if (response.ok) {
          console.log(`ConnectionManager: HTTP health check successful on port ${port}`);
          return port;
        }
        
      } catch (error) {
        console.log(`ConnectionManager: HTTP test failed for port ${port}:`, error.message);
      }
    }
    
    return null;
  }

  /**
   * Validate port number
   * @param {number} port - Port to validate
   * @param {string} source - Source of port for error messages
   * @returns {number} - Validated port
   */
  validatePort(port, source) {
    if (isNaN(port) || port < 1024 || port > 65535) {
      throw new Error(`Invalid port ${port} from ${source}. Must be 1024-65535.`);
    }
    return port;
  }

  /**
   * Setup callbacks for SessionManager events
   * @private
   */
  setupSessionManagerCallbacks() {
    this.sessionManager.setCallbacks({
      onSessionExpired: () => {
        console.log('ConnectionManager: Session expired, attempting refresh');
        this.sessionManager.refreshSession(this.baseUrl);
      },
      onCriticalState: (sessionInfo) => {
        console.log('ConnectionManager: Session in critical state');
        // ConnectionManager can add additional handling here if needed
      },
      onSessionCreated: (sessionData) => {
        console.log('ConnectionManager: New session created');
      },
      onSessionExtended: (sessionData) => {
        console.log('ConnectionManager: Session extended');
      },
      onSessionRefreshed: (sessionData) => {
        console.log('ConnectionManager: Session refreshed');
      }
    });
  }
  

  
  /**
   * Check if session is valid (delegated to SessionManager)
   * @returns {boolean} - True if session is valid
   */
  isSessionValid() {
    return this.sessionManager.isSessionValid();
  }
  
  /**
   * Make an API request to backend (WebSocket-only)
   * @param {string} endpoint - API endpoint
   * @param {Object} data - Request data
   * @returns {Promise<Object>} - Response data
   */
  async makeRequest(endpoint, data) {
    // Ensure we're connected before making request
    if (this.state !== ConnectionState.CONNECTED || !this.isSessionValid()) {
      console.log('ConnectionManager: Not connected, initializing...');
      await this.initialize();
    }
    
    // Use WebSocket only - no HTTP fallback
    if (!this.webSocketClient || !this.webSocketClient.isConnected) {
      throw new Error('WebSocket connection required. Please ensure backend server is running.');
    }
    
    try {
      console.log(`ConnectionManager: Using WebSocket for ${endpoint}`);
      return await this.makeWebSocketRequest(endpoint, data);
    } catch (error) {
      console.error('ConnectionManager: WebSocket request failed:', error);
      throw new Error(`WebSocket connection failed: ${error.message}. Please restart the backend server.`);
    }
  }

  /**
   * Make request via WebSocket (Phase 4 enhancement)
   * @param {string} endpoint - API endpoint
   * @param {Object} data - Request data
   * @returns {Promise<Object>} - Response data
   */
  async makeWebSocketRequest(endpoint, data) {
    if (!this.webSocketClient || !this.webSocketClient.isConnected) {
      throw new Error('WebSocket not available or not connected');
    }

    // Convert HTTP endpoint to WebSocket message type
    const messageType = this.endpointToMessageType(endpoint);
    
    try {
      let response;
      
      switch (messageType) {
        case 'chat_request':
          response = await this.webSocketClient.sendChatRequest(data.messages || [], data);
          break;
          
        case 'simple_chat':
          // For simple_chat, send as chat_request with compatibility mode
          response = await this.webSocketClient.sendChatRequest(data.messages || [], data);
          break;
          
        case 'context_chat':
          // For context_chat, send scene data along with messages
          response = await this.webSocketClient.sendChatRequest(data.messages || [], {
            ...data,
            scene_id: data.scene_id,
            context_options: data.context_options
          });
          break;
          
        default:
          // For unknown endpoints, fall back to HTTP
          throw new Error(`WebSocket mapping not available for endpoint: ${endpoint}`);
      }
      
      return {
        success: true,
        data: response.data || response
      };
      
    } catch (error) {
      console.error('ConnectionManager: WebSocket request failed:', error);
      throw error;
    }
  }

  /**
   * Convert HTTP endpoint to WebSocket message type
   * @param {string} endpoint - HTTP endpoint
   * @returns {string} - WebSocket message type
   */
  endpointToMessageType(endpoint) {
    const endpointMap = {
      '/api/simple_chat': 'simple_chat',
      '/api/api_chat': 'chat_request',
      '/api/context_chat': 'context_chat',
      '/api/process_chat': 'process_chat'
    };
    
    return endpointMap[endpoint] || 'unknown';
  }

  /**
   * Send data via real-time synchronization (WebSocket-only)
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
      console.log(`ConnectionManager: Real-time sync sent for ${syncType}`);
      return true;
      
    } catch (error) {
      console.error('ConnectionManager: Real-time sync failed:', error);
      throw new Error(`Real-time sync failed: ${error.message}. Please restart the backend server.`);
    }
  }
  
  /**
   * Get security headers for requests
   * @returns {Object} - Headers object
   */
  getSecurityHeaders() {
    const headers = {
      'Content-Type': 'application/json'
    };
    
    // Get session ID from SessionManager
    const sessionId = this.sessionManager.getSessionId();
    if (sessionId) {
      headers['X-Session-ID'] = sessionId;
    }
    
    return headers;
  }
  
  /**
   * Test backend connection
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
    const sessionInfo = this.sessionManager.getSessionInfo();
    return {
      state: this.state,
      baseUrl: this.baseUrl,
      port: this.port,
      hasValidSession: this.isSessionValid(),
      sessionId: sessionInfo.sessionId,
      sessionExpiry: sessionInfo.sessionExpiry,
      sessionState: sessionInfo.sessionState,
      timeToExpiry: sessionInfo.timeToExpiry
    };
  }
  
  /**
   * Set connection state
   * @private
   */
  setState(newState) {
    const oldState = this.state;
    this.state = newState;
    
    if (oldState !== newState) {
      console.log(`ConnectionManager: State changed from ${oldState} to ${newState}`);
    }
  }
  
  /**
   * Disconnect and cleanup
   */
  disconnect() {
    console.log('ConnectionManager: Disconnecting...');
    
    // Clear session using SessionManager
    this.sessionManager.clearSession();
    
    // Reset state
    this.setState(ConnectionState.DISCONNECTED);
    
    // Clear initialization promise
    this.initPromise = null;
    
    // Clear WebSocket client
    this.webSocketClient = null;
    
    console.log('ConnectionManager: Cleanup complete');
  }
}

// Export for global access
window.ConnectionManager = ConnectionManager;
window.ConnectionState = ConnectionState;
