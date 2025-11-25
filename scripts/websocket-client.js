/**
 * Simple WebSocket Client for Gold Box - Direct connection to relay server
 * Minimal implementation to get client ID for API chat mode
 */

/**
 * Simple WebSocket Client Class
 */
class SimpleWebSocketClient {
  constructor() {
    this.socket = null;
    this.clientId = null;
    this.isConnected = false;
    this.relayUrl = 'ws://localhost:3010'; // Default relay server URL
    this.reconnectAttempts = 0;
    this.maxReconnectAttempts = 5;
    this.reconnectDelay = 2000;
  }

  /**
   * Initialize connection to relay server
   * @returns {Promise<boolean>} - True if successful
   */
  async initialize() {
    try {
      console.log('SimpleWebSocketClient: Starting initialization...');
      
      // Generate client ID
      this.clientId = `gold-box-${game.user.id || Math.random().toString(36).substring(2, 15)}-${Date.now()}`;
      
      // Connect to relay server
      const success = await this.connect();
      
      if (success) {
        console.log(`SimpleWebSocketClient: Initialization complete - Client ID: ${this.clientId}`);
        return true;
      } else {
        console.warn('SimpleWebSocketClient: Failed to connect to relay server');
        return false;
      }
      
    } catch (error) {
      console.error('SimpleWebSocketClient: Initialization failed:', error);
      return false;
    }
  }

  /**
   * Connect to relay server
   * @returns {Promise<boolean>} - True if connection successful
   */
  async connect() {
    return new Promise((resolve) => {
      try {
        const url = `${this.relayUrl}?id=${encodeURIComponent(this.clientId)}&token=${game.world.id || 'default'}`;
        console.log(`SimpleWebSocketClient: Connecting to ${url}`);
        
        this.socket = new WebSocket(url);
        
        const timeout = setTimeout(() => {
          console.error('SimpleWebSocketClient: Connection timeout');
          this.socket = null;
          resolve(false);
        }, 5000);

        this.socket.onopen = () => {
          clearTimeout(timeout);
          console.log('SimpleWebSocketClient: Connected to relay server');
          this.isConnected = true;
          this.reconnectAttempts = 0;
          
          // Send initial ping
          this.send({ type: 'ping' });
          
          resolve(true);
        };

        this.socket.onclose = (event) => {
          clearTimeout(timeout);
          console.log(`SimpleWebSocketClient: Disconnected - Code: ${event.code}, Reason: ${event.reason}`);
          this.isConnected = false;
          this.socket = null;
          
          // Attempt reconnection if not a normal close
          if (event.code !== 1000 && this.reconnectAttempts < this.maxReconnectAttempts) {
            this.scheduleReconnect();
          }
        };

        this.socket.onerror = (error) => {
          clearTimeout(timeout);
          console.error('SimpleWebSocketClient: Connection error:', error);
          this.isConnected = false;
          this.socket = null;
          resolve(false);
        };

        this.socket.onmessage = (event) => {
          try {
            const message = JSON.parse(event.data);
            console.log('SimpleWebSocketClient: Received message:', message);
            
            // Handle pong responses
            if (message.type === 'pong') {
              console.log('SimpleWebSocketClient: Received pong');
            }
          } catch (error) {
            console.error('SimpleWebSocketClient: Error parsing message:', error);
          }
        };

      } catch (error) {
        console.error('SimpleWebSocketClient: Error creating WebSocket:', error);
        resolve(false);
      }
    });
  }

  /**
   * Send message to relay server
   * @param {Object} message - Message to send
   * @returns {boolean} - True if sent successfully
   */
  send(message) {
    if (this.isConnected && this.socket) {
      try {
        this.socket.send(JSON.stringify(message));
        return true;
      } catch (error) {
        console.error('SimpleWebSocketClient: Error sending message:', error);
        return false;
      }
    } else {
      console.warn('SimpleWebSocketClient: Cannot send message - not connected');
      return false;
    }
  }

  /**
   * Schedule reconnection attempt
   */
  scheduleReconnect() {
    this.reconnectAttempts++;
    const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1);
    
    console.log(`SimpleWebSocketClient: Scheduling reconnect in ${delay}ms (attempt ${this.reconnectAttempts}/${this.maxReconnectAttempts})`);
    
    setTimeout(() => {
      if (this.reconnectAttempts <= this.maxReconnectAttempts) {
        this.connect();
      }
    }, delay);
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
    return this.isConnected && this.socket && this.socket.readyState === WebSocket.OPEN;
  }

  /**
   * Disconnect from relay server
   */
  disconnect() {
    if (this.socket) {
      console.log('SimpleWebSocketClient: Disconnecting...');
      this.socket.close(1000, 'Disconnecting');
      this.socket = null;
    }
    this.isConnected = false;
    this.reconnectAttempts = 0;
  }

  /**
   * Get connection status information
   * @returns {Object} - Connection status object
   */
  getConnectionInfo() {
    return {
      connected: this.isWebSocketConnected(),
      clientId: this.clientId,
      relayUrl: this.relayUrl,
      reconnectAttempts: this.reconnectAttempts,
      connectionStatus: this.isConnected ? 'connected' : 'disconnected'
    };
  }
}

// Export for global access
window.SimpleWebSocketClient = SimpleWebSocketClient;

console.log('SimpleWebSocketClient: Module loaded');
