/**
 * Connection Manager for Gold Box Backend
 * WebSocket-first implementation with HTTP fallback
 * Phase 4: Removed Relay Server dependency
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
    
    // Session management
    this.sessionId = null;
    this.sessionExpiry = null;
    this.sessionRefreshInterval = null;
    this.sessionHealthInterval = null;
    
    // Retry and refresh state
    this.refreshState = {
      isRefreshing: false,
      consecutiveFailures: 0,
      lastRefreshAttempt: null,
      circuitBreakerOpen: false,
      circuitBreakerResetTime: null
    };
    
    // Initialization control
    this.initPromise = null;
    this.initQueue = [];
    
    // Configuration
    this.defaultPort = 5000;
    this.maxPortAttempts = 20;
    this.portTimeout = 2000;
    
    // Enhanced refresh configuration
    this.refreshConfig = {
      maxRetries: 3,
      baseDelay: 1000,        // 1 second base delay
      maxDelay: 30000,        // 30 second max delay
      criticalThreshold: 60000, // 1 minute critical threshold
      warningThreshold: 300000, // 5 minute warning threshold
      minRefreshBuffer: 300000,  // 5 minute minimum buffer
      healthCheckInterval: 30000, // 30 second health check
      circuitBreakerResetDelay: 300000 // 5 minute circuit breaker reset
    };
    
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
    if (this.state === ConnectionState.CONNECTED && this.isSessionValid()) {
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
   * Perform the actual initialization
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
      
      // Step 2: Initialize session
      const sessionInitialized = await this.initializeSession();
      if (!sessionInitialized) {
        console.log('ConnectionManager: Failed to initialize session');
        this.setState(ConnectionState.ERROR);
        return false;
      }
      
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
   * Initialize session with backend
   * @returns {Promise<boolean>} - True if successful
   */
  async initializeSession() {
    try {
      console.log('ConnectionManager: Initializing session...');
      
      const response = await fetch(`${this.baseUrl}/api/session/init`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        }
      });

      if (response.ok) {
        const data = await response.json();
        this.sessionId = data.session_id;
        this.sessionExpiry = new Date(data.expires_at);
        
        console.log('ConnectionManager: Session initialized successfully');
        console.log('ConnectionManager: Session ID:', this.sessionId);
        console.log('ConnectionManager: Session expires:', this.sessionExpiry);
        
        // Reset refresh state on successful initialization
        this.refreshState = {
          isRefreshing: false,
          consecutiveFailures: 0,
          lastRefreshAttempt: null,
          circuitBreakerOpen: false,
          circuitBreakerResetTime: null
        };
        
        // Start enhanced refresh system
        this.scheduleNextRefresh();
        this.startHealthMonitoring();
        this.setupVisibilityChangeHandler();
        
        return true;
      } else {
        console.error('ConnectionManager: Failed to initialize session:', response.status, response.statusText);
        return false;
      }
    } catch (error) {
      console.error('ConnectionManager: Error initializing session:', error);
      return false;
    }
  }

  /**
   * Setup visibility change handler to handle tab background/foreground
   */
  setupVisibilityChangeHandler() {
    // Remove existing listener if any
    if (this.visibilityChangeHandler) {
      document.removeEventListener('visibilitychange', this.visibilityChangeHandler);
    }

    this.visibilityChangeHandler = () => {
      if (document.hidden) {
        console.log('ConnectionManager: Tab became hidden, adjusting refresh behavior');
        // When tab is hidden, be more conservative with refreshes
        this.adjustRefreshForBackground();
      } else {
        console.log('ConnectionManager: Tab became visible, checking session health');
        // When tab becomes visible, immediately check session health
        this.performImmediateHealthCheck();
      }
    };

    document.addEventListener('visibilitychange', this.visibilityChangeHandler);
    console.log('ConnectionManager: Visibility change handler setup complete');
  }

  /**
   * Perform immediate health check when tab becomes visible
   */
  async performImmediateHealthCheck() {
    if (!this.sessionId || !this.sessionExpiry) return;

    const now = Date.now();
    const timeToExpiry = this.sessionExpiry.getTime() - now;

    // If session is expired, refresh immediately
    if (timeToExpiry <= 0) {
      console.log('ConnectionManager: Tab visible with expired session, refreshing immediately');
      await this.refreshSession();
      return;
    }

    // If session is in warning zone, test connection
    if (timeToExpiry < this.refreshConfig.warningThreshold) {
      try {
        const testResult = await this.testConnection();
        if (!testResult.success) {
          console.warn('ConnectionManager: Connection test failed on tab visibility, refreshing session');
          await this.refreshSession();
        } else {
          console.log('ConnectionManager: Connection test passed on tab visibility');
        }
      } catch (error) {
        console.error('ConnectionManager: Error testing connection on tab visibility:', error);
        await this.refreshSession();
      }
    }
  }
  
  /**
   * Refresh session token with retry logic and exponential backoff
   * @returns {Promise<boolean>} - True if successful
   */
  async refreshSession() {
    // Check if already refreshing to prevent concurrent refreshes
    if (this.refreshState.isRefreshing) {
      console.log('ConnectionManager: Refresh already in progress, skipping...');
      return false;
    }

    // Check circuit breaker
    if (this.refreshState.circuitBreakerOpen) {
      const now = Date.now();
      if (now < this.refreshState.circuitBreakerResetTime) {
        console.log('ConnectionManager: Circuit breaker is open, skipping refresh');
        return false;
      } else {
        console.log('ConnectionManager: Circuit breaker reset, allowing refresh');
        this.refreshState.circuitBreakerOpen = false;
        this.refreshState.consecutiveFailures = 0;
      }
    }

    this.refreshState.isRefreshing = true;
    this.refreshState.lastRefreshAttempt = Date.now();

    try {
      // Try to extend existing session first
      const wasExtended = await this.extendExistingSession();
      
      if (wasExtended) {
        console.log('ConnectionManager: Session extended successfully');
        this.refreshState.consecutiveFailures = 0;
        this.scheduleNextRefresh();
        return true;
      }

      // If extension failed, try refresh with retry logic
      const refreshed = await this.refreshSessionWithRetry();
      
      if (refreshed) {
        this.refreshState.consecutiveFailures = 0;
        this.scheduleNextRefresh();
        return true;
      }

      // All refresh attempts failed
      this.refreshState.consecutiveFailures++;
      console.error(`ConnectionManager: Session refresh failed after ${this.refreshState.consecutiveFailures} consecutive failures`);

      // Check for critical situation
      if (this.isSessionInCriticalState()) {
        this.handleCriticalSessionState();
      }

      // Open circuit breaker if too many failures
      if (this.refreshState.consecutiveFailures >= this.refreshConfig.maxRetries) {
        this.refreshState.circuitBreakerOpen = true;
        this.refreshState.circuitBreakerResetTime = Date.now() + this.refreshConfig.circuitBreakerResetDelay;
        console.warn('ConnectionManager: Circuit breaker opened due to repeated failures');
      }

      return false;

    } finally {
      this.refreshState.isRefreshing = false;
    }
  }

  /**
   * Try to extend existing session instead of creating new one
   * @returns {Promise<boolean>} - True if successful
   */
  async extendExistingSession() {
    if (!this.sessionId || !this.isSessionValid()) {
      return false;
    }

    try {
      console.log('ConnectionManager: Attempting to extend existing session...');
      
      const response = await fetch(`${this.baseUrl}/api/session/init`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          extend_existing: true,
          session_id: this.sessionId
        })
      });

      if (response.ok) {
        const data = await response.json();
        
        if (data.was_extended) {
          this.sessionExpiry = new Date(data.expires_at);
          console.log('ConnectionManager: Session extended successfully');
          console.log('ConnectionManager: New expiry:', this.sessionExpiry);
          return true;
        } else {
          console.log('ConnectionManager: Server created new session instead of extending');
          this.sessionId = data.session_id;
          this.sessionExpiry = new Date(data.expires_at);
          return true;
        }
      } else {
        console.log('ConnectionManager: Session extension failed, will try refresh');
        return false;
      }
    } catch (error) {
      console.error('ConnectionManager: Error extending session:', error);
      return false;
    }
  }

  /**
   * Refresh session with exponential backoff retry logic
   * @returns {Promise<boolean>} - True if successful
   */
  async refreshSessionWithRetry() {
    for (let attempt = 0; attempt < this.refreshConfig.maxRetries; attempt++) {
      try {
        console.log(`ConnectionManager: Refresh attempt ${attempt + 1}/${this.refreshConfig.maxRetries}`);
        
        const response = await fetch(`${this.baseUrl}/api/session/init`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          }
        });

        if (response.ok) {
          const data = await response.json();
          this.sessionId = data.session_id;
          this.sessionExpiry = new Date(data.expires_at);
          
          console.log('ConnectionManager: Session refreshed successfully');
          console.log('ConnectionManager: New Session ID:', this.sessionId);
          console.log('ConnectionManager: New expiry:', this.sessionExpiry);
          
          return true;
        } else {
          console.error(`ConnectionManager: Refresh attempt ${attempt + 1} failed:`, response.status, response.statusText);
        }
      } catch (error) {
        console.error(`ConnectionManager: Refresh attempt ${attempt + 1} error:`, error);
      }

      // If not the last attempt, wait with exponential backoff
      if (attempt < this.refreshConfig.maxRetries - 1) {
        const delay = this.calculateBackoffDelay(attempt);
        console.log(`ConnectionManager: Waiting ${delay}ms before retry...`);
        await this.sleep(delay);
      }
    }

    return false;
  }

  /**
   * Calculate exponential backoff delay with jitter
   * @param {number} attempt - Current attempt number (0-based)
   * @returns {number} - Delay in milliseconds
   */
  calculateBackoffDelay(attempt) {
    const exponentialDelay = this.refreshConfig.baseDelay * Math.pow(2, attempt);
    const jitter = Math.random() * 0.1 * exponentialDelay; // Add 10% jitter
    const totalDelay = exponentialDelay + jitter;
    return Math.min(totalDelay, this.refreshConfig.maxDelay);
  }

  /**
   * Sleep helper function
   * @param {number} ms - Milliseconds to sleep
   * @returns {Promise} - Promise that resolves after ms milliseconds
   */
  sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
  }

  /**
   * Check if session is in critical state (expiring soon)
   * @returns {boolean} - True if session expires in less than critical threshold
   */
  isSessionInCriticalState() {
    if (!this.sessionExpiry) return false;
    
    const timeToExpiry = this.sessionExpiry.getTime() - Date.now();
    return timeToExpiry < this.refreshConfig.criticalThreshold;
  }

  /**
   * Handle critical session state with user notification
   */
  handleCriticalSessionState() {
    console.error('ConnectionManager: Session in critical state - showing user warning');
    
    // Try to show user notification
    if (typeof ui !== 'undefined' && ui.notifications) {
      ui.notifications.error('⚠️ Session expiring soon! Server connection may be unstable. Please refresh the page.', {
        permanent: true
      });
    }

    // Also show in chat if available
    if (typeof ChatMessage !== 'undefined') {
      const messageContent = `
        <div class="gold-box-critical-warning">
          <div class="gold-box-header">
            <strong>The Gold Box - Critical Session Warning</strong>
          </div>
          <div class="gold-box-content">
            <p><strong>⚠️ Session expiring soon!</strong></p>
            <p>The backend connection is unstable and may fail soon. Please refresh the page to restore connection.</p>
            <p><em>If this persists, the backend server may be down or experiencing issues.</em></p>
          </div>
        </div>
      `;
      
      ChatMessage.create({
        user: game?.user?.id || 'system',
        content: messageContent,
        speaker: {
          alias: 'The Gold Box System'
        }
      });
    }
  }

  /**
   * Schedule next refresh using smart timing
   */
  scheduleNextRefresh() {
    // Clear any existing timer
    if (this.sessionRefreshInterval) {
      clearTimeout(this.sessionRefreshInterval);
      this.sessionRefreshInterval = null;
    }

    if (!this.sessionExpiry) {
      console.log('ConnectionManager: No session expiry, cannot schedule refresh');
      return;
    }

    const now = Date.now();
    const timeToExpiry = this.sessionExpiry.getTime() - now;

    // If already expired, refresh immediately
    if (timeToExpiry <= 0) {
      console.log('ConnectionManager: Session expired, refreshing immediately');
      this.refreshSession();
      return;
    }

    let refreshDelay;

    // If less than minimum buffer, refresh immediately
    if (timeToExpiry < this.refreshConfig.minRefreshBuffer) {
      refreshDelay = 1000; // 1 second
      console.log('ConnectionManager: Session expires soon, refreshing immediately');
    }
    // If less than warning threshold, refresh more frequently
    else if (timeToExpiry < this.refreshConfig.warningThreshold) {
      refreshDelay = Math.max(30000, timeToExpiry - this.refreshConfig.criticalThreshold); // Every 30 seconds or critical threshold
      console.log('ConnectionManager: Session in warning zone, scheduling frequent refresh');
    }
    // Normal case: refresh 5 minutes before expiry
    else {
      refreshDelay = timeToExpiry - this.refreshConfig.minRefreshBuffer;
      console.log(`ConnectionManager: Scheduling normal refresh in ${refreshDelay / 1000} seconds`);
    }

    this.sessionRefreshInterval = setTimeout(() => {
      this.refreshSession();
    }, refreshDelay);
  }

  /**
   * Start health monitoring for session
   */
  startHealthMonitoring() {
    // Clear existing health check
    if (this.sessionHealthInterval) {
      clearInterval(this.sessionHealthInterval);
      this.sessionHealthInterval = null;
    }

    // Start periodic health checks
    this.sessionHealthInterval = setInterval(() => {
      this.performHealthCheck();
    }, this.refreshConfig.healthCheckInterval);

    console.log('ConnectionManager: Started session health monitoring');
  }

  /**
   * Perform health check on session
   */
  async performHealthCheck() {
    if (!this.sessionId || !this.sessionExpiry) {
      return;
    }

    const now = Date.now();
    const timeToExpiry = this.sessionExpiry.getTime() - now;

    // If session is expired, try to refresh
    if (timeToExpiry <= 0) {
      console.log('ConnectionManager: Health check detected expired session, refreshing...');
      await this.refreshSession();
      return;
    }

    // If session is in warning zone, be more aggressive
    if (timeToExpiry < this.refreshConfig.warningThreshold) {
      console.log('ConnectionManager: Health check detected session in warning zone');
      
      // Test connection to backend
      try {
        const testResult = await this.testConnection();
        if (!testResult.success) {
          console.warn('ConnectionManager: Health check failed, attempting refresh');
          await this.refreshSession();
        }
      } catch (error) {
        console.error('ConnectionManager: Health check error:', error);
      }
    }
  }
  
  /**
   * Check if session is valid
   * @returns {boolean} - True if session is valid
   */
  isSessionValid() {
    return this.sessionId && this.sessionExpiry && Date.now() < this.sessionExpiry.getTime();
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
    
    // Only add session ID if we have one
    if (this.sessionId) {
      headers['X-Session-ID'] = this.sessionId;
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
    return {
      state: this.state,
      baseUrl: this.baseUrl,
      port: this.port,
      hasValidSession: this.isSessionValid(),
      sessionId: this.sessionId,
      sessionExpiry: this.sessionExpiry
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
    
    // Clear refresh timer
    if (this.sessionRefreshInterval) {
      clearTimeout(this.sessionRefreshInterval);
      this.sessionRefreshInterval = null;
    }
    
    // Clear health monitoring
    if (this.sessionHealthInterval) {
      clearInterval(this.sessionHealthInterval);
      this.sessionHealthInterval = null;
    }
    
    // Remove visibility change handler
    if (this.visibilityChangeHandler) {
      document.removeEventListener('visibilitychange', this.visibilityChangeHandler);
      this.visibilityChangeHandler = null;
    }
    
    // Clear session data
    this.sessionId = null;
    this.sessionExpiry = null;
    
    // Reset refresh state
    this.refreshState = {
      isRefreshing: false,
      consecutiveFailures: 0,
      lastRefreshAttempt: null,
      circuitBreakerOpen: false,
      circuitBreakerResetTime: null
    };
    
    // Reset state
    this.setState(ConnectionState.DISCONNECTED);
    
    // Clear initialization promise
    this.initPromise = null;
    
    console.log('ConnectionManager: Cleanup complete');
  }
}

// Export for global access
window.ConnectionManager = ConnectionManager;
window.ConnectionState = ConnectionState;
