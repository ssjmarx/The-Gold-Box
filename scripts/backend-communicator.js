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
