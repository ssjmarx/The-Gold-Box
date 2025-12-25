/**
 * The Gold Box - Native WebSocket Client
 * Replaces Relay Server dependency with direct WebSocket communication
 */

/**
 * Gold Box WebSocket Client Class
 */
class GoldBoxWebSocketClient {
  constructor(baseUrl, onMessage, onError) {
    this.baseUrl = baseUrl;
    this.onMessage = onMessage;
    this.onError = onError;
    this.ws = null;
    this.clientId = this.generateClientId();
    this.isConnected = false;
    this.reconnectAttempts = 0;
    this.maxReconnectAttempts =5;
    this.reconnectDelay = 1000;
    this.reconnectTimer = null;
    this.pingInterval = null;
    this.messageHandlers = new Map();
    this.pendingRequests = new Map(); // request_id -> Promise resolver
  }

  /**
   * Generate unique client ID
   */
  generateClientId() {
    const userId = game.user?.id;
    const randomSuffix = crypto.randomUUID().split('-')[0]; // Use first UUID segment
    return userId ? `gb-${userId}-${randomSuffix}` : `gb-${randomSuffix}`;
  }

  /**
   * Generate unique request ID
   */
  generateRequestId() {
    const timestamp = Date.now().toString(36); // Base36 timestamp
    const randomPart = Math.random().toString(36).substring(2, 6);
    return `gold_${timestamp}_${randomPart}`;
  }

  /**
   * Get authentication token
   */
  async getAuthToken() {
    try {
      // Try to get backend password from settings first
      const backendPassword = game.settings.get('the-gold-box', 'backendPassword');
      if (backendPassword && backendPassword.trim()) {
        console.log('Using backend password for authentication');
        return backendPassword.trim();
      }
      
      // Fallback to session-based token
      console.log('Getting session-based authentication token...');
      const response = await fetch(`${this.baseUrl}/api/session/init`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          extend_existing: true
        })
      });
      
      if (response.ok) {
        const data = await response.json();
        console.log('Got session token:', data.session_id);
        return data.session_id;
      } else {
        console.error('Failed to get session token:', response.status, response.statusText);
      }
      
      return null;
    } catch (error) {
      console.error('Error getting auth token:', error);
      return null;
    }
  }

  /**
   * Get world information
   */
  getWorldInfo() {
    return {
      id: game.world?.id,
      title: game.world?.title,
      foundry_version: game.version,
      system_id: game.system?.id,
      system_title: game.system?.title || game.system?.id,
      system_version: game.system?.version || 'unknown'
    };
  }

  /**
   * Get user information
   */
  getUserInfo() {
    return {
      id: game.user?.id,
      name: game.user?.name,
      role: game.user?.role
    };
  }

  /**
   * Connect to WebSocket server
   */
  async connect() {
    try {
      if (this.isConnected) {
        console.warn('WebSocket already connected');
        return true;
      }

      // WebSocket connection available to all users
      console.log('Initializing WebSocket connection...');

      // Get auth token
      const token = await this.getAuthToken();
      if (!token) {
        throw new Error('No authentication token available');
      }

      // Build WebSocket URL - use FastAPI WebSocket endpoint
      const url = new URL(this.baseUrl);
      const wsUrl = `ws://${url.hostname}:5000/ws`;
      console.log(`Connecting to WebSocket at ${wsUrl}`);

      // Create WebSocket connection
      this.ws = new WebSocket(wsUrl);

      // Set up event handlers
      this.ws.onopen = () => this.handleOpen();
      this.ws.onmessage = (event) => this.handleMessage(event);
      this.ws.onclose = (event) => this.handleClose(event);
      this.ws.onerror = (error) => this.handleError(error);

      return new Promise((resolve, reject) => {
        const timeout = setTimeout(() => {
          reject(new Error('Connection timeout'));
        },10000); // 10 second timeout

        // Override: onopen handler for this promise
        const originalOnopen = this.ws.onopen;
        this.ws.onopen = () => {
          clearTimeout(timeout);
          console.log('WebSocket connection established, sending connection message...');
          this.handleOpen();
          resolve(true);
        };

        this.ws.onerror = (error) => {
          clearTimeout(timeout);
          console.error('WebSocket connection error:', error);
          reject(error);
        };
      });

    } catch (error) {
      console.error('Error creating WebSocket connection:', error);
      this.onError?.(error);
      return false;
    }
  }

  /**
   * Handle WebSocket open event
   */
  async handleOpen() {
    try {
      console.log('WebSocket connection opened');
      this.isConnected = true;
      this.reconnectAttempts = 0;

      // Send connection message
      const connectMessage = {
        type: 'connect',
        client_id: this.clientId,
        token: await this.getAuthToken(),
        world_info: this.getWorldInfo(),
        user_info: this.getUserInfo(),
        timestamp: Date.now()
      };

      this.ws.send(JSON.stringify(connectMessage));
      console.log('Sent connection message');

      // Start ping interval
      this.startPingInterval();

    } catch (error) {
      console.error('Error in WebSocket open handler:', error);
      this.onError?.(error);
    }
  }

  /**
   * Handle WebSocket message event
   */
  handleMessage(event) {
    try {
      const message = JSON.parse(event.data);
      console.log('Received WebSocket message:', message);

      // Handle different message types
      switch (message.type) {
        case 'connected':
          console.log('WebSocket connection confirmed:', message.data);
          break;

        case 'chat_response':
          this.handleChatResponse(message);
          break;

        case 'error':
          console.error('WebSocket error from server:', message.data);
          this.onError?.(message.data);
          break;

        case 'pong':
          // Ping response received
          console.log('WebSocket ping response received');
          break;

        default:
          // Handle custom message types
          if (this.messageHandlers.has(message.type)) {
            this.messageHandlers.get(message.type)(message);
          } else {
            console.warn('Unknown message type:', message.type);
          }
      }

    } catch (error) {
      console.error('Error parsing WebSocket message:', error);
    }
  }

  /**
   * Handle chat response message
   */
  handleChatResponse(message) {
    try {
      const requestId = message.request_id;
      
      if (requestId && this.pendingRequests.has(requestId)) {
        // Resolve pending request
        const resolver = this.pendingRequests.get(requestId);
        resolver({
          success: true,
          data: message.data
        });
        this.pendingRequests.delete(requestId);
      } else {
        // Handle as unsolicited message
        this.onMessage?.(message);
      }
    } catch (error) {
      console.error('Error handling chat response:', error);
    }
  }

  /**
   * Handle WebSocket close event
   */
  handleClose(event) {
    console.log('WebSocket connection closed:', event.code, event.reason);
    this.isConnected = false;
    this.stopPingInterval();

    // Clear pending requests
    for (const [requestId, resolver] of this.pendingRequests) {
      resolver({
        success: false,
        error: 'Connection closed'
      });
    }
    this.pendingRequests.clear();

    // Attempt reconnection if not a normal closure
    if (event.code !== 1000 && this.reconnectAttempts < this.maxReconnectAttempts) {
      this.scheduleReconnect();
    }
  }

  /**
   * Handle WebSocket error event
   */
  handleError(error) {
    console.error('WebSocket error:', error);
    this.isConnected = false;
    this.stopPingInterval();
    this.onError?.(error);
  }

  /**
   * Schedule reconnection attempt
   */
  scheduleReconnect() {
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
    }

    this.reconnectAttempts++;
    const delay = Math.min(30000, this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1));

    console.log(`Scheduling WebSocket reconnect in ${delay}ms (attempt ${this.reconnectAttempts}/${this.maxReconnectAttempts})`);

    this.reconnectTimer = setTimeout(() => {
      this.reconnectTimer = null;
      console.log('Attempting WebSocket reconnect...');
      this.connect();
    }, delay);
  }

  /**
   * Start ping interval
   */
  startPingInterval() {
    this.stopPingInterval();
    
    // Send ping every 30 seconds
    this.pingInterval = setInterval(() => {
      if (this.isConnected && this.ws?.readyState === WebSocket.OPEN) {
        this.ws.send(JSON.stringify({
          type: 'ping',
          timestamp: Date.now()
        }));
      }
    },30000);
  }

  /**
   * Stop ping interval
   */
  stopPingInterval() {
    if (this.pingInterval) {
      clearInterval(this.pingInterval);
      this.pingInterval = null;
    }
  }

  /**
   * Send message to WebSocket server
   */
  send(message) {
    return new Promise((resolve, reject) => {
      if (!this.isConnected || !this.ws || this.ws.readyState !== WebSocket.OPEN) {
        reject(new Error('WebSocket not connected'));
        return;
      }

      try {
        const requestId = message.request_id || this.generateRequestId();
        message.request_id = requestId;
        message.timestamp = Date.now();

        // Set up promise resolver for response
        if (message.type === 'chat_request') {
          this.pendingRequests.set(requestId, resolve);
        }

        this.ws.send(JSON.stringify(message));
        
        // For non-chat messages, resolve immediately
        if (message.type !== 'chat_request') {
          resolve(true);
        }

      } catch (error) {
        reject(error);
      }
    });
  }

  /**
   * Send chat request
   */
  async sendChatRequest(messages, options = {}) {
    try {
      // Get delta counts before sending request
      const deltaCounts = window.FrontendDeltaService?.getDeltaCounts() || {
        newMessages: 0,
        deletedMessages: 0
      };

      console.log('Gold Box WebSocket: Sending chat_request with delta:', JSON.stringify(deltaCounts));
      console.log('Gold Box WebSocket: Full message data being sent:', JSON.stringify({
        type: 'chat_request',
        data: {
          messages_count: messages.length,
          context_count: options.contextCount || 15,
          scene_id: options.sceneId || null,
          force_full_context: options.forceFullContext || false,
          message_delta: deltaCounts
        }
      }));

      const message = {
        type: 'chat_request',
        data: {
          messages: messages,
          context_count: options.contextCount || 15,  // Use proper default of 15
          scene_id: options.sceneId || null,
          // Let backend handle session management entirely
          // No ai_session_id - backend will manage sessions based on client_id
          force_full_context: options.forceFullContext || false,
          message_delta: deltaCounts,  // Add delta counts for function calling mode
          ...options
        }
      };

      const response = await this.send(message);
      return response;

    } catch (error) {
      console.error('Error sending chat request:', error);
      return {
        success: false,
        error: error.message
      };
    }
  }

  /**
   * Send message (alias for compatibility with MessageCollector)
   */
  async sendMessage(message) {
    return this.send(message);
  }

  /**
   * Disconnect from WebSocket server
   */
  disconnect() {
    this.stopPingInterval();

    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }

    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.close(1000, 'Client disconnecting');
    }

    this.isConnected = false;
    
    // Clear pending requests
    for (const [requestId, resolver] of this.pendingRequests) {
      resolver({
        success: false,
        error: 'Client disconnected'
      });
    }
    this.pendingRequests.clear();

    console.log('WebSocket disconnected');
  }

  /**
   * Register message handler
   */
  onMessageType(type, handler) {
    this.messageHandlers.set(type, handler);
  }

  /**
   * Unregister message handler
   */
  offMessageType(type) {
    this.messageHandlers.delete(type);
  }

  /**
   * Get connection status
   */
  getConnectionStatus() {
    return {
      connected: this.isConnected,
      client_id: this.clientId,
      reconnect_attempts: this.reconnectAttempts,
      pending_requests: this.pendingRequests.size
    };
  }

  /**
   * Wait for connection to be established
   */
  waitForConnection(timeout =10000) {
    return new Promise((resolve) => {
      if (this.isConnected) {
        resolve(true);
        return;
      }

      const checkInterval = setInterval(() => {
        if (this.isConnected) {
          clearInterval(checkInterval);
          resolve(true);
        }
      }, 100);

      setTimeout(() => {
        clearInterval(checkInterval);
        resolve(false);
      }, timeout);
    });
  }
}

// Export for use in other modules
window.GoldBoxWebSocketClient = GoldBoxWebSocketClient;

console.log('Gold Box WebSocket Client module loaded');
