/**
 * API Bridge for Gold Box - Bridge between Gold Box and Foundry REST API module
 * Handles WebSocket client ID relay for API chat mode
 */

/**
 * API Bridge Class
 */
class APIBridge {
  constructor() {
    this.foundryModule = null;
    this.webSocketManager = null;
    this.clientId = null;
    this.isConnected = false;
    this.connectionPromise = null;
  }

  /**
   * Initialize connection to Foundry REST API module (always try to connect)
   * @returns {Promise<boolean>} - True if successful
   */
  async initialize() {
    try {
      console.log('APIBridge: Starting initialization...');
      
      // Check if game and user are available
      if (!game || !game.user) {
        console.warn('APIBridge: Game or user not available, delaying initialization');
        return false;
      }
      
      console.log('APIBridge: Game and user available, proceeding...');
      console.log('APIBridge: User info:', {
        id: game.user?.id,
        name: game.user?.name,
        isGM: game.user?.isGM,
        role: game.user?.role,
        active: game.user?.active
      });
      
      // Wait for Foundry modules to be ready
      await this.waitForFoundryModule();
      
      // Get the Foundry REST API module
      this.foundryModule = game.modules.get('foundry-rest-api');
      
      if (!this.foundryModule) {
        console.warn('APIBridge: Foundry REST API module not found');
        return false;
      }
      
      console.log('APIBridge: Foundry REST API module found:', this.foundryModule);
      console.log('APIBridge: Module active:', this.foundryModule.active);
      console.log('APIBridge: Module API available:', !!this.foundryModule.api);
      console.log('APIBridge: Available module properties:', Object.keys(this.foundryModule));
      
      // Check if user is GM before proceeding
      if (!game.user.isGM) {
        console.warn('APIBridge: User is not GM, WebSocket manager will not be available');
        return false;
      }
      
      console.log('APIBridge: User is GM, checking WebSocket manager availability...');
      
      // Wait for WebSocket manager to be initialized with retry logic
      this.webSocketManager = await this.waitForWebSocketManager();
      
      if (!this.webSocketManager) {
        console.warn('APIBridge: WebSocket manager not available after waiting');
        console.warn('APIBridge: Module API object:', this.foundryModule.api);
        if (this.foundryModule.api) {
          console.warn('APIBridge: Available API methods:', Object.keys(this.foundryModule.api));
        }
        console.warn('APIBridge: User is GM:', game.user.isGM);
        console.warn('APIBridge: Module active:', this.foundryModule.active);
        
        // Try to check if module needs to be activated
        if (!this.foundryModule.active) {
          console.warn('APIBridge: Foundry REST API module is not active - please enable it in module settings');
        }
        return false;
      }
      
      console.log('APIBridge: WebSocket manager found:', this.webSocketManager);
      console.log('APIBridge: WebSocket manager type:', typeof this.webSocketManager);
      console.log('APIBridge: WebSocket manager methods:', Object.getOwnPropertyNames(this.webSocketManager));
      
      // Wait a moment for connection to establish
      await new Promise(resolve => setTimeout(resolve, 2000));
      
      // Get connection status and client ID with retry logic
      this.isConnected = this.webSocketManager.isConnected();
      this.clientId = await this.waitForClientId();
      
      console.log(`APIBridge: Initialization complete - Connected: ${this.isConnected}, Client ID: ${this.clientId}`);
      
      if (!this.clientId) {
        console.warn('APIBridge: No client ID available, WebSocket may not be connected');
        console.warn('APIBridge: WebSocket connection status:', this.isConnected);
        console.warn('APIBridge: WebSocket manager isConnected() result:', this.webSocketManager.isConnected());
        
        // Try to get more debug info
        try {
          const connectionInfo = this.webSocketManager.getConnectionInfo ? this.webSocketManager.getConnectionInfo() : 'No getConnectionInfo method';
          console.warn('APIBridge: Connection info:', connectionInfo);
        } catch (e) {
          console.warn('APIBridge: Could not get connection info:', e);
        }
      }
      
      return true;
      
    } catch (error) {
      console.error('APIBridge: Initialization failed:', error);
      console.error('APIBridge: Error stack:', error.stack);
      return false;
    }
  }

  /**
   * Reinitialize connection (for rediscover functionality)
   * @returns {Promise<boolean>} - True if successful
   */
  async reinitialize() {
    console.log('APIBridge: Reinitializing connection...');
    
    // Clear existing state
    this.foundryModule = null;
    this.webSocketManager = null;
    this.clientId = null;
    this.isConnected = false;
    this.connectionPromise = null;
    
    // Reinitialize
    return await this.initialize();
  }

  /**
   * Get current client ID
   * @returns {string|null} - Client ID if available
   */
  getClientId() {
    return this.clientId;
  }

  /**
   * Check if WebSocket is connected
   * @returns {boolean} - True if connected
   */
  isWebSocketConnected() {
    return this.isConnected && this.webSocketManager?.isConnected();
  }

  /**
   * Ensure connection is active (reconnect if needed)
   * @returns {Promise<boolean>} - True if connected or reconnection successful
   */
  async ensureConnection() {
    if (!this.isWebSocketConnected()) {
      console.log('APIBridge: WebSocket not connected, attempting reconnection...');
      return await this.initialize();
    }
    return true;
  }

  /**
   * Wait for WebSocket manager to be initialized with retry logic
   * @private
   * @returns {Promise<Object|null>} - WebSocket manager instance or null
   */
  async waitForWebSocketManager() {
    const maxAttempts = 30; // 15 seconds max with 500ms intervals
    const baseDelay = 500; // Start with 500ms
    const maxDelay = 3000; // Max 3 seconds between attempts
    
    console.log('APIBridge: Waiting for WebSocket manager to be initialized...');
    
    for (let attempt = 1; attempt <= maxAttempts; attempt++) {
      try {
        // Try to get WebSocket manager
        const wsManager = this.foundryModule.api?.getWebSocketManager();
        
        if (wsManager) {
          console.log(`APIBridge: WebSocket manager found on attempt ${attempt}`);
          return wsManager;
        }
        
        // Calculate delay with exponential backoff
        const delay = Math.min(baseDelay * Math.pow(1.2, attempt - 1), maxDelay);
        
        if (attempt < maxAttempts) {
          console.log(`APIBridge: WebSocket manager not ready (attempt ${attempt}/${maxAttempts}), waiting ${delay}ms...`);
          await new Promise(resolve => setTimeout(resolve, delay));
        }
        
      } catch (error) {
        console.warn(`APIBridge: Error checking WebSocket manager on attempt ${attempt}:`, error);
        
        if (attempt < maxAttempts) {
          const delay = Math.min(baseDelay * Math.pow(1.2, attempt - 1), maxDelay);
          await new Promise(resolve => setTimeout(resolve, delay));
        }
      }
    }
    
    console.error('APIBridge: WebSocket manager not available after all attempts');
    return null;
  }

  /**
   * Wait for Foundry REST API module to be available
   * @private
   */
  async waitForFoundryModule() {
    let attempts = 0;
    const maxAttempts = 50; // 5 seconds max
    
    while (attempts < maxAttempts) {
      if (game.modules && game.modules.get('foundry-rest-api')) {
        console.log('APIBridge: Foundry REST API module is available');
        return;
      }
      await new Promise(resolve => setTimeout(resolve, 100));
      attempts++;
    }
    
    throw new Error('Foundry REST API module not available after timeout');
  }

  /**
   * Wait for client ID to be available with retry logic
   * @private
   * @returns {Promise<string|null>} - Client ID if available
   */
  async waitForClientId() {
    const maxAttempts = 20; // 10 seconds max with 500ms intervals
    const baseDelay = 500; // Start with 500ms
    const maxDelay = 2000; // Max 2 seconds between attempts
    
    console.log('APIBridge: Waiting for client ID to be available...');
    
    for (let attempt = 1; attempt <= maxAttempts; attempt++) {
      try {
        // Try to get client ID
        const clientId = this.webSocketManager.getClientId();
        
        if (clientId && clientId.length > 0) {
          console.log(`APIBridge: Client ID found on attempt ${attempt}: ${clientId}`);
          return clientId;
        }
        
        // Calculate delay with exponential backoff
        const delay = Math.min(baseDelay * Math.pow(1.2, attempt - 1), maxDelay);
        
        if (attempt < maxAttempts) {
          console.log(`APIBridge: Client ID not ready (attempt ${attempt}/${maxAttempts}), waiting ${delay}ms...`);
          await new Promise(resolve => setTimeout(resolve, delay));
        }
        
      } catch (error) {
        console.warn(`APIBridge: Error getting client ID on attempt ${attempt}:`, error);
        
        if (attempt < maxAttempts) {
          const delay = Math.min(baseDelay * Math.pow(1.2, attempt - 1), maxDelay);
          await new Promise(resolve => setTimeout(resolve, delay));
        }
      }
    }
    
    console.error('APIBridge: Client ID not available after all attempts');
    return null;
  }

  /**
   * Get connection status information
   * @returns {Object} - Connection status object
   */
  getConnectionInfo() {
    return {
      moduleAvailable: !!this.foundryModule,
      webSocketManagerAvailable: !!this.webSocketManager,
      connected: this.isWebSocketConnected(),
      clientId: this.clientId,
      connectionStatus: this.isConnected ? 'connected' : 'disconnected'
    };
  }
}

// Export for global access
window.APIBridge = APIBridge;

console.log('APIBridge: Module loaded');
