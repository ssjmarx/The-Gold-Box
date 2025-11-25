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
      
      // Wait for Foundry modules to be ready
      await this.waitForFoundryModule();
      
      // Get the Foundry REST API module
      this.foundryModule = game.modules.get('foundry-rest-api');
      
      if (!this.foundryModule) {
        console.warn('APIBridge: Foundry REST API module not found');
        return false;
      }
      
      // Get WebSocket manager instance
      this.webSocketManager = this.foundryModule.api?.getWebSocketManager();
      
      if (!this.webSocketManager) {
        console.warn('APIBridge: WebSocket manager not available (user may not be GM)');
        return false;
      }
      
      // Wait a moment for connection to establish
      await new Promise(resolve => setTimeout(resolve, 2000));
      
      // Get connection status and client ID
      this.isConnected = this.webSocketManager.isConnected();
      this.clientId = this.webSocketManager.getClientId();
      
      console.log(`APIBridge: Initialization complete - Connected: ${this.isConnected}, Client ID: ${this.clientId}`);
      
      if (!this.clientId) {
        console.warn('APIBridge: No client ID available, WebSocket may not be connected');
      }
      
      return true;
      
    } catch (error) {
      console.error('APIBridge: Initialization failed:', error);
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
