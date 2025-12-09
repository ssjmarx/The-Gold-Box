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
  WEBSOCKET: 'websocket',
  HTTP: 'http'
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
    
    // Configuration
    this.defaultPort = 5000;
    this.maxPortAttempts = 20;
    this.portTimeout = 2000;
    
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
   * Discover backend port by testing multiple ports
   * @param {number} startPort - Starting port (default: 5000)
   * @param {number} maxAttempts - Maximum ports to check (default: 20)
   * @returns {Promise<number|null>} - Found port or null
   */
  async discoverBackendPort(startPort = this.defaultPort, maxAttempts = this.maxPortAttempts) {
    console.log(`ConnectionManager: Scanning ports from ${startPort}...`);
    
    for (let i = 0; i < maxAttempts; i++) {
      const port = startPort + i;
      const testUrl = `http://localhost:${port}`;
      
      try {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), this.portTimeout);
        
        const response = await fetch(`${testUrl}/api/health`, {
          method: 'GET',
          headers: {
            'Content-Type': 'application/json'
          },
          signal: controller.signal
        });
        
        clearTimeout(timeoutId);
        
        if (response.ok) {
          const data = await response.json();
          // Check for our backend service identifier
          if (data.service === 'The Gold Box Backend' || data.version === '0.2.3') {
            console.log(`ConnectionManager: Found backend on port ${port}`, data);
            return port;
          }
        }
      } catch (error) {
        // Expected for ports that aren't running our backend
        continue;
      }
    }
    return null;
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
   * Make an API request to backend (WebSocket-first with HTTP fallback)
   * @param {string} endpoint - API endpoint
   * @param {Object} data - Request data
   * @param {string} method - HTTP method (default: POST)
   * @returns {Promise<Object>} - Response data
   */
  async makeRequest(endpoint, data, method = 'POST') {
    // Phase 4: Try WebSocket first if available and connected
    if (this.connectionType === ConnectionType.WEBSOCKET && 
        this.webSocketClient && 
        this.webSocketClient.isConnected) {
      
      try {
        console.log(`ConnectionManager: Using WebSocket for ${endpoint}`);
        return await this.makeWebSocketRequest(endpoint, data);
      } catch (error) {
        console.warn('ConnectionManager: WebSocket request failed, falling back to HTTP:', error);
        // Fall back to HTTP on WebSocket failure
      }
    }
    
    // Ensure we're connected before making HTTP request
    if (this.state !== ConnectionState.CONNECTED || !this.isSessionValid()) {
      console.log('ConnectionManager: Not connected, initializing...');
      await this.initialize();
    }
    
    // Get security headers
    const headers = this.getSecurityHeaders();
    
    try {
      console.log(`ConnectionManager: Making HTTP ${method} request to ${endpoint}`);
      
      const response = await fetch(`${this.baseUrl}${endpoint}`, {
        method: method,
        headers: headers,
        body: data ? JSON.stringify(data) : undefined
      });

      if (!response.ok) {
        // Handle security-related errors specifically
        if (response.status === 429) {
          throw new Error(`Rate limit exceeded. Please wait before trying again.`);
        } else if (response.status === 401) {
          throw new Error(`Session required or expired. Please refresh the page.`);
        } else {
          throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
      }

      const responseData = await response.json();
      return {
        success: true,
        data: responseData
      };
      
    } catch (error) {
      console.error('ConnectionManager: HTTP request failed:', error);
      throw error;
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
   * Send data via real-time synchronization (Phase 4)
   * @param {string} syncType - Type of sync data
   * @param {Object} syncData - Data to synchronize
   * @returns {Promise<boolean>} - Success status
   */
  async syncDataRealTime(syncType, syncData) {
    if (this.connectionType === ConnectionType.WEBSOCKET && 
        this.webSocketClient && 
        this.webSocketClient.isConnected) {
      
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
        return false;
      }
    }
    
    // Fallback: store for batch sync when WebSocket becomes available
    this.storeBatchSyncData(syncType, syncData);
    return false;
  }

  /**
   * Store batch sync data for later transmission
   * @param {string} syncType - Type of sync data
   * @param {Object} syncData - Data to synchronize
   */
  storeBatchSyncData(syncType, syncData) {
    if (!this.batchSyncQueue) {
      this.batchSyncQueue = [];
    }
    
    this.batchSyncQueue.push({
      sync_type: syncType,
      sync_data: syncData,
      timestamp: Date.now()
    });
    
    // Limit queue size to prevent memory issues
    if (this.batchSyncQueue.length > 100) {
      this.batchSyncQueue = this.batchSyncQueue.slice(-50); // Keep last 50 items
    }
    
    console.log(`ConnectionManager: Stored batch sync data for ${syncType} (${this.batchSyncQueue.length} items queued)`);
  }

  /**
   * Flush batch sync data when WebSocket becomes available
   */
  async flushBatchSyncData() {
    if (!this.batchSyncQueue || this.batchSyncQueue.length === 0) {
      return;
    }
    
    if (this.connectionType !== ConnectionType.WEBSOCKET || 
        !this.webSocketClient || 
        !this.webSocketClient.isConnected) {
      return;
    }
    
    try {
      const batchMessage = {
        type: 'batch_sync',
        data: {
          sync_items: this.batchSyncQueue,
          flush_timestamp: Date.now()
        }
      };
      
      await this.webSocketClient.send(batchMessage);
      console.log(`ConnectionManager: Flushed ${this.batchSyncQueue.length} batch sync items`);
      
      // Clear queue after successful flush
      this.batchSyncQueue = [];
      
    } catch (error) {
      console.error('ConnectionManager: Failed to flush batch sync data:', error);
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
