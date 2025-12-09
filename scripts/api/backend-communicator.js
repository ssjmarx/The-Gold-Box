/**
 * Backend Communicator for Gold Box
 * Handles all backend communication concerns extracted from gold-box.js
 * Following same successful pattern as SessionManager extraction
 */

/**
 * Connection States for Communicator
 */
const CommunicatorState = {
  DISCONNECTED: 'disconnected',
  CONNECTING: 'connecting',
  CONNECTED: 'connected',
  ERROR: 'error'
};

/**
 * Communication Types
 */
const CommunicationType = {
  WEBSOCKET: 'websocket',
  HTTP: 'http'
};

/**
 * Backend Communicator Class
 * Handles all backend communication, connection management, and routing
 */
class BackendCommunicator {
  constructor(config = {}) {
    // Singleton pattern
    if (BackendCommunicator.instance) {
      return BackendCommunicator.instance;
    }
    
    BackendCommunicator.instance = this;
    
    // Connection state
    this.state = CommunicatorState.DISCONNECTED;
    this.communicationType = CommunicationType.HTTP;
    this.baseUrl = config.baseUrl || 'http://localhost:5000';
    this.port = config.port || 5000;
    
    // WebSocket client reference
    this.webSocketClient = null;
    
    // Connection management
    this.connectionManager = config.connectionManager || null;
    this.settingsManager = config.settingsManager || null;
    
    // Configuration
    this.defaultPort = config.defaultPort || 5000;
    this.maxPortAttempts = config.maxPortAttempts || 20;
    this.portTimeout = config.portTimeout || 2000;
    
    // Request handling
    this.requestQueue = [];
    this.activeRequests = new Map();
    
    console.log('BackendCommunicator: Initialized singleton instance');
  }

  /**
   * Set ConnectionManager reference
   * @param {ConnectionManager} connectionManager - Connection manager instance
   */
  setConnectionManager(connectionManager) {
    this.connectionManager = connectionManager;
    console.log('BackendCommunicator: Connection manager set');
  }

  /**
   * Set SettingsManager reference
   * @param {SettingsManager} settingsManager - Settings manager instance
   */
  setSettingsManager(settingsManager) {
    this.settingsManager = settingsManager;
    console.log('BackendCommunicator: Settings manager set');
  }

  /**
   * Set WebSocket client reference
   * @param {GoldBoxWebSocketClient} webSocketClient - WebSocket client instance
   */
  setWebSocketClient(webSocketClient) {
    this.webSocketClient = webSocketClient;
    this.communicationType = CommunicationType.WEBSOCKET;
    console.log('BackendCommunicator: WebSocket client set, communication type:', this.communicationType);
  }

  /**
   * Initialize backend communication
   * @returns {Promise<boolean>} - True if initialization successful
   */
  async initialize() {
    try {
      this.setState(CommunicatorState.CONNECTING);
      console.log('BackendCommunicator: Starting backend communication initialization...');
      
      // Step 1: Initialize ConnectionManager if provided
      if (this.connectionManager) {
        const connectionInitialized = await this.connectionManager.initialize();
        if (!connectionInitialized) {
          throw new Error('Failed to initialize connection manager');
        }
        this.baseUrl = this.connectionManager.baseUrl;
        this.port = this.connectionManager.port;
      } else {
        // Fallback: Discover backend port ourselves
        const port = await this.discoverBackendPort();
        if (!port) {
          throw new Error('No backend server found on any port');
        }
        this.port = port;
        this.baseUrl = `http://localhost:${port}`;
      }
      
      this.setState(CommunicatorState.CONNECTED);
      console.log('BackendCommunicator: Backend communication initialized successfully');
      console.log('BackendCommunicator: Backend on port', this.port, 'at', this.baseUrl);
      
      return true;
      
    } catch (error) {
      this.setState(CommunicatorState.ERROR);
      console.error('BackendCommunicator: Initialization failed:', error);
      return false;
    }
  }

  /**
   * Discover backend port by testing multiple ports
   * @param {number} startPort - Starting port
   * @param {number} maxAttempts - Maximum ports to check
   * @returns {Promise<number|null>} - Found port or null
   */
  async discoverBackendPort(startPort = this.defaultPort, maxAttempts = this.maxPortAttempts) {
    console.log(`BackendCommunicator: Scanning ports from ${startPort}...`);
    
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
            console.log(`BackendCommunicator: Found backend on port ${port}`, data);
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
   * Send request to backend (HTTP/WebSocket routing)
   * @param {string} endpoint - API endpoint
   * @param {Object} data - Request data
   * @param {string} method - HTTP method
   * @param {Object} options - Additional options
   * @returns {Promise<Object>} - Response data
   */
  async sendRequest(endpoint, data, method = 'POST', options = {}) {
    try {
      // Step 1: Ensure communication is initialized
      if (this.state !== CommunicatorState.CONNECTED) {
        console.log('BackendCommunicator: Not connected, initializing...');
        await this.initialize();
      }
      
      // Step 2: Determine communication method
      let response;
      
      if (this.communicationType === CommunicationType.WEBSOCKET && 
          this.webSocketClient && 
          this.webSocketClient.isConnected) {
        
        console.log(`BackendCommunicator: Using WebSocket for ${endpoint}`);
        response = await this.sendWebSocketRequest(endpoint, data, options);
        
      } else {
        console.log(`BackendCommunicator: Using HTTP for ${endpoint}`);
        response = await this.sendHttpRequest(endpoint, data, method, options);
      }
      
      return response;
      
    } catch (error) {
      console.error('BackendCommunicator: Request failed:', error);
      throw error;
    }
  }

  /**
   * Send HTTP request
   * @param {string} endpoint - API endpoint
   * @param {Object} data - Request data
   * @param {string} method - HTTP method
   * @param {Object} options - Additional options
   * @returns {Promise<Object>} - Response data
   */
  async sendHttpRequest(endpoint, data, method = 'POST', options = {}) {
    try {
      console.log(`BackendCommunicator: Making HTTP ${method} request to ${endpoint}`);
      
      // Get security headers from ConnectionManager
      const headers = this.getSecurityHeaders();
      
      const response = await fetch(`${this.baseUrl}${endpoint}`, {
        method: method,
        headers: headers,
        body: data ? JSON.stringify(data) : undefined,
        ...options
      });

      if (!response.ok) {
        // Handle specific HTTP errors
        if (response.status === 429) {
          throw new Error('Rate limit exceeded. Please wait before trying again.');
        } else if (response.status === 401) {
          throw new Error('Session required or expired. Please refresh the page.');
        } else if (response.status === 404) {
          throw new Error(`Endpoint not found: ${endpoint}`);
        } else {
          throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
      }

      const responseData = await response.json();
      return {
        success: true,
        data: responseData,
        status: response.status
      };
      
    } catch (error) {
      console.error('BackendCommunicator: HTTP request failed:', error);
      throw error;
    }
  }

  /**
   * Send WebSocket request
   * @param {string} endpoint - API endpoint
   * @param {Object} data - Request data
   * @param {Object} options - Additional options
   * @returns {Promise<Object>} - Response data
   */
  async sendWebSocketRequest(endpoint, data, options = {}) {
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
          response = await this.webSocketClient.sendChatRequest(data.messages || [], data);
          break;
          
        case 'context_chat':
          response = await this.webSocketClient.sendChatRequest(data.messages || [], {
            ...data,
            scene_id: data.scene_id,
            context_options: data.context_options
          });
          break;
          
        default:
          throw new Error(`WebSocket mapping not available for endpoint: ${endpoint}`);
      }
      
      return {
        success: true,
        data: response.data || response,
        source: 'websocket'
      };
      
    } catch (error) {
      console.error('BackendCommunicator: WebSocket request failed:', error);
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
   * Get security headers for requests
   * @returns {Object} - Headers object
   */
  getSecurityHeaders() {
    const headers = {
      'Content-Type': 'application/json'
    };
    
    // Get session ID from ConnectionManager if available
    if (this.connectionManager && this.connectionManager.sessionManager) {
      const sessionId = this.connectionManager.sessionManager.getSessionId();
      if (sessionId) {
        headers['X-Session-ID'] = sessionId;
      }
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
   * Get auto-start instructions from backend
   * @returns {Promise<Object>} - Auto-start instructions
   */
  async getAutoStartInstructions() {
    try {
      const response = await this.sendHttpRequest('/api/start', {}, 'POST');
      return response;
    } catch (error) {
      return {
        success: false,
        error: error.message
      };
    }
  }

  /**
   * Sync settings to backend admin endpoint
   * @param {Object} settings - Settings to sync
   * @param {string} adminPassword - Admin password
   * @returns {Promise<Object>} - Sync result
   */
  async syncSettings(settings, adminPassword) {
    try {
      const response = await this.sendHttpRequest('/api/admin', {
        command: 'update_settings',
        settings: settings
      }, 'POST', {
        headers: {
          'X-Admin-Password': adminPassword
        }
      });
      
      return response;
    } catch (error) {
      return {
        success: false,
        error: error.message
      };
    }
  }

  /**
   * Get unified frontend settings
   * @returns {Object} - All settings
   */
  getUnifiedFrontendSettings() {
    if (this.settingsManager) {
      return this.settingsManager.getAllSettings();
    }
    return {};
  }

  /**
   * Get current communication state
   * @returns {string} - Current state
   */
  getState() {
    return this.state;
  }

  /**
   * Get current communication info
   * @returns {Object} - Communication info
   */
  getConnectionInfo() {
    const info = {
      state: this.state,
      communicationType: this.communicationType,
      baseUrl: this.baseUrl,
      port: this.port,
      hasConnectionManager: !!this.connectionManager,
      hasWebSocketClient: !!this.webSocketClient,
      isConnected: this.state === CommunicatorState.CONNECTED
    };
    
    // Add connection manager info if available
    if (this.connectionManager) {
      const connectionInfo = this.connectionManager.getConnectionInfo();
      info.hasValidSession = connectionInfo.hasValidSession;
      info.sessionId = connectionInfo.sessionId;
      info.sessionExpiry = connectionInfo.sessionExpiry;
      info.sessionState = connectionInfo.sessionState;
      info.timeToExpiry = connectionInfo.timeToExpiry;
    }
    
    return info;
  }

  /**
   * Set communication state
   * @private
   */
  setState(newState) {
    const oldState = this.state;
    this.state = newState;
    
    if (oldState !== newState) {
      console.log(`BackendCommunicator: State changed from ${oldState} to ${newState}`);
    }
  }

  /**
   * Send message context to backend with timeout and retry logic
   * @param {Array} messages - Chat messages
   * @param {number} timeout - Request timeout in seconds
   * @param {number} maxRetries - Maximum retry attempts
   * @returns {Promise<Object>} - Response data
   */
  async sendMessageContext(messages, timeout = 60, maxRetries = 1) {
    try {
      // Send request with timeout and retry logic
      const response = await Promise.race([
        this.sendMessageContextWithRetry(messages, maxRetries),
        new Promise((_, reject) => setTimeout(() => reject(new Error('AI response timeout')), timeout * 1000))
      ]);
      
      return response;
      
    } catch (error) {
      console.error('BackendCommunicator: Error processing message context:', error);
      throw error;
    }
  }

  /**
   * Send message context with retry logic
   * @param {Array} messages - Chat messages
   * @param {number} maxRetries - Maximum retry attempts
   * @returns {Promise<Object>} - Response data
   */
  async sendMessageContextWithRetry(messages, maxRetries = 1) {
    for (let attempt = 0; attempt <= maxRetries; attempt++) {
      try {
        const response = await this.sendMessageContextInternal(messages);
        return response;
      } catch (error) {
        // For non-CSRF errors, implement basic retry logic
        if (attempt === maxRetries) {
          throw error;
        }
        
        // Wait a moment before retrying
        await new Promise(resolve => setTimeout(resolve, 500));
      }
    }
  }

  /**
   * Internal message context processing
   * @param {Array} messages - Chat messages
   * @returns {Promise<Object>} - Response data
   */
  async sendMessageContextInternal(messages) {
    try {
      const processingMode = this.settingsManager ? this.settingsManager.getProcessingMode() : 'api';
      
      let endpoint;
      let requestData;
      
      // STEP 1: Sync settings to admin endpoint FIRST
      console.log('BackendCommunicator: Syncing settings to admin endpoint before chat request...');
      const settings = this.getUnifiedFrontendSettings();
      const adminPassword = settings['backend password'];
      
      if (adminPassword && adminPassword.trim()) {
        const syncResult = await this.syncSettings(settings, adminPassword);
        if (syncResult.success) {
          console.log('BackendCommunicator: Settings synced successfully to admin endpoint');
        } else {
          console.warn('BackendCommunicator: Settings sync failed:', syncResult.error);
        }
      } else {
        console.warn('BackendCommunicator: No backend password configured, skipping settings sync');
      }
      
      // STEP 2: Check if WebSocket is available and use it
      if (processingMode === 'api' && this.webSocketClient) {
        // Check if WebSocket is connected (more robust check)
        const wsConnected = this.webSocketClient.isConnected || this.webSocketClient.connectionState === 'connected';
        if (wsConnected) {
          console.log('BackendCommunicator: Using WebSocket for API mode - response will be handled asynchronously');
          // For WebSocket, we send the request and return immediately - response comes via WebSocket message handler
          this.sendViaWebSocket(messages).catch(error => {
            console.error('BackendCommunicator: WebSocket send error:', error);
            // Error will be handled by the WebSocket client's error handler
          });
          // Return a special response indicating async processing
          return {
            success: true,
            data: {
              response: 'WebSocket request sent - response will be handled asynchronously',
              metadata: { websocket_mode: true }
            }
          };
        } else {
          console.log('BackendCommunicator: WebSocket client exists but not connected, falling back to HTTP API');
          console.log('BackendCommunicator: WebSocket client exists:', !!this.webSocketClient);
          console.log('BackendCommunicator: WebSocket connection state:', this.webSocketClient.connectionState || 'unknown');
          console.log('BackendCommunicator: WebSocket isConnected property:', this.webSocketClient.isConnected);
        }
      } else if (processingMode === 'api') {
        console.log('BackendCommunicator: WebSocket not available, falling back to HTTP API');
        console.log('BackendCommunicator: WebSocket client exists:', !!this.webSocketClient);
        console.log('BackendCommunicator: WebSocket connected:', this.webSocketClient ? this.webSocketClient.isConnected : 'N/A');
      }
      
      // STEP 3: Fallback to HTTP API
      if (processingMode === 'context') {
        // NEW: Context mode with full board state integration
        endpoint = '/api/context_chat';
        
        // Get scene ID from current scene
        const sceneId = typeof canvas !== 'undefined' && canvas.scene ? canvas.scene.id : 
                       (typeof game !== 'undefined' && game.scenes && game.scenes.active ? game.scenes.active.id : null);
        const clientId = this.webSocketClient ? this.webSocketClient.clientId : null;
        
        requestData = {
          client_id: clientId || 'default-client',
          scene_id: sceneId || 'default-scene',
          message: messages.length > 0 ? messages[messages.length - 1].content : 'No message provided',
          context_options: {
            include_chat_history: true,
            message_count: this.settingsManager ? this.settingsManager.getSetting('maxMessageContext', 15) : 15,
            include_scene_data: true,
            include_tokens: true,
            include_walls: true,
            include_lighting: true,
            include_map_notes: true,
            include_templates: true
          },
          ai_options: {
            model: this.settingsManager ? this.settingsManager.getSetting('generalLlmModel') || 'gpt-4' : 'gpt-4',
            temperature: 0.7,
            max_tokens: 2000
          }
        };
        console.log('BackendCommunicator: Using CONTEXT mode with endpoint:', endpoint, '- full board state integration');
        console.log('BackendCommunicator: Scene ID:', sceneId, 'Client ID:', clientId);
      } else if (processingMode === 'api') {
        endpoint = '/api/api_chat';
        // Include client ID in request data if available
        const clientId = this.webSocketClient ? this.webSocketClient.clientId : null;
        console.log("BackendCommunicator: WebSocket client available:", !!this.webSocketClient);
        console.log("BackendCommunicator: WebSocket connected:", this.webSocketClient ? this.webSocketClient.isConnected : "N/A");
        requestData = {
          // NO settings here - backend will use stored settings
          context_count: this.settingsManager ? this.settingsManager.getSetting('maxMessageContext', 15) : 15,
          settings: clientId ? { 'relay client id': clientId } : null // Include client ID, allow null if not connected
        };
        console.log('BackendCommunicator: Using API mode with client ID:', clientId || 'not connected', '- settings from backend storage');
      } else {
        // Should never reach here with only 'api' and 'context' modes
        throw new Error(`Unsupported processing mode: ${processingMode}. Supported modes: 'api', 'context'`);
      }
      
      // Use this class's sendRequest method
      const response = await this.sendRequest(endpoint, requestData);
      
      return response;
      
    } catch (error) {
      console.error('BackendCommunicator: Message context processing error:', error);
      throw error;
    }
  }

  /**
   * Send chat request via WebSocket
   * @param {Array} messages - Chat messages
   * @returns {Promise<Object>} - Response data
   */
  async sendViaWebSocket(messages) {
    if (!this.webSocketClient || !this.webSocketClient.isConnected) {
      throw new Error('WebSocket not connected');
    }

    try {
      const response = await this.webSocketClient.sendChatRequest(messages, {
        contextCount: this.settingsManager ? this.settingsManager.getSetting('maxMessageContext', 15) : 15,
        sceneId: typeof canvas !== 'undefined' && canvas.scene ? canvas.scene.id : 
                  (typeof game !== 'undefined' && game.scenes && game.scenes.active ? game.scenes.active.id : null)
      });

      if (response.success) {
        return {
          success: true,
          data: {
            response: response.data.response,
            metadata: response.data
          }
        };
      } else {
        throw new Error(response.error || 'WebSocket request failed');
      }
    } catch (error) {
      console.error('BackendCommunicator: WebSocket chat request error:', error);
      throw error;
    }
  }

  /**
   * Set up real-time data synchronization
   * @param {Function} onRealTimeSync - Callback for real-time sync
   * @param {Function} onBatchSync - Callback for batch sync
   */
  setupRealTimeSync(onRealTimeSync, onBatchSync) {
    if (!this.webSocketClient) {
      console.warn('BackendCommunicator: Cannot set up real-time sync - WebSocket client not available');
      return;
    }
    
    // Set up message handlers for real-time sync
    this.webSocketClient.onMessageType('data_sync', (message) => {
      onRealTimeSync(message);
    });
    
    this.webSocketClient.onMessageType('batch_sync', (message) => {
      onBatchSync(message);
    });
    
    console.log('BackendCommunicator: Real-time synchronization set up');
  }

  /**
   * Disconnect and cleanup
   */
  disconnect() {
    console.log('BackendCommunicator: Disconnecting...');
    
    // Clear WebSocket client
    if (this.webSocketClient) {
      this.webSocketClient.disconnect();
      this.webSocketClient = null;
    }
    
    // Clear connection manager
    if (this.connectionManager) {
      this.connectionManager = null;
    }
    
    // Clear settings manager
    this.settingsManager = null;
    
    // Reset state
    this.setState(CommunicatorState.DISCONNECTED);
    
    console.log('BackendCommunicator: Cleanup complete');
  }
}

// Export for global access
window.BackendCommunicator = BackendCommunicator;
window.CommunicatorState = CommunicatorState;
window.CommunicationType = CommunicationType;
