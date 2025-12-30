/**
 * The Gold Box - Native WebSocket Client
 * Replaces Relay Server dependency with direct WebSocket communication
 */

  /**
   * Gold Box WebSocket Client Class
   */
class GoldBoxWebSocketClient {
  constructor(baseUrl, onMessage, onError, onConnected, onDisconnected) {
    this.baseUrl = baseUrl;
    this.onMessage = onMessage;
    this.onError = onError;
    this.onConnected = onConnected;
    this.onDisconnected = onDisconnected;
    this.ws = null;
    this.clientId = this.generateClientId();
    this.isConnected = false;
    this.reconnectAttempts = 0;
    this.maxReconnectAttempts = 3; // Changed from 5 to 3
    this.reconnectDelay = 1000;
    this.reconnectTimer = null;
    this.isReconnecting = false;
    this.manualDisconnect = false; // NEW: Flag to prevent auto-reconnect during manual resets
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
      if (this.isConnected && !this.isReconnecting) {
        console.warn('WebSocket already connected');
        return true;
      }

      // Reset reconnect attempts for manual connections
      if (!this.isReconnecting) {
        this.reconnectAttempts = 0;
      }

      // WebSocket connection available to all users
      console.log('Initializing WebSocket connection...');

      // Get auth token
      const token = await this.getAuthToken();
      if (!token) {
        throw new Error('No authentication token available');
      }

      // Build WebSocket URL - use FastAPI WebSocket endpoint
      // Use the discovered port from baseUrl instead of hardcoded 5000
      const wsUrl = this.baseUrl.replace('http://', 'ws://').replace('https://', 'wss://') + '/ws';
      console.log(`Connecting to WebSocket at ${wsUrl}`);

      // Create WebSocket connection
      this.ws = new WebSocket(wsUrl);

      // Set up event handlers (will be overridden in promise for connection attempt)
      this.ws.onopen = () => this.handleOpen();
      this.ws.onmessage = (event) => this.handleMessage(event);
      this.ws.onclose = (event) => this.handleClose(event);
      this.ws.onerror = (error) => this.handleError(error);

      return new Promise((resolve, reject) => {
        const timeout = setTimeout(() => {
          console.error('WebSocket connection timeout');
          reject(new Error('Connection timeout'));
        }, 10000); // 10 second timeout

        // Override onopen handler for this promise to resolve when connected
        const originalHandleOpen = this.handleOpen.bind(this);
        this.ws.onopen = (event) => {
          clearTimeout(timeout);
          originalHandleOpen();
          resolve(true);
        };

        // Override onerror handler for this promise to reject with error
        const originalHandleError = this.handleError.bind(this);
        this.ws.onerror = (event) => {
          clearTimeout(timeout);
          console.error('WebSocket connection error during connect attempt');
          originalHandleError(event);
          reject(event);
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
      this.isReconnecting = false;

      // Wait for WebSocket to be fully OPEN before sending
      if (this.ws.readyState !== WebSocket.OPEN) {
        await new Promise(resolve => {
          const checkInterval = setInterval(() => {
            if (this.ws.readyState === WebSocket.OPEN) {
              clearInterval(checkInterval);
              resolve();
            }
          }, 10);
        });
      }
      
      // Notify connection established
      if (this.onConnected) {
        this.onConnected();
      }

      // Send initial world state
      if (window.goldBoxWorldStateCollector && typeof window.goldBoxWorldStateCollector.sendWorldState === 'function') {
        try {
          await window.goldBoxWorldStateCollector.sendWorldState();
          console.log('Gold Box WebSocket: Initial world state sent after connection');
        } catch (error) {
          console.warn('Gold Box WebSocket: Failed to send initial world state:', error);
        }
      }

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

        case 'ai_turn_complete':
          // AI turn completed - forward to main message handler
          console.log('WebSocket: Received ai_turn_complete message, forwarding to main handler');
          this.onMessage?.(message);
          break;

        case 'test_session_start':
          this.handleTestSessionStart(message);
          break;

        case 'test_session_end':
          this.handleTestSessionEnd(message);
          break;

        case 'test_chat_response':
          this.handleTestChatResponse(message);
          break;

        case 'error':
          console.error('WebSocket error from server:', message.data);
          this.onError?.(message.data);
          break;

        case 'pong':
          // Ping response received
          console.log('WebSocket ping response received');
          break;

        case 'settings_sync_response':
          console.log('WebSocket settings sync response received:', message.data);
          // Settings sync completed, no action needed
          break;

        case 'game_delta':
          console.log('WebSocket game_delta confirmation received:', message.data);
          // Game delta processed by backend, no action needed
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
   * Handle test session start message
   */
  handleTestSessionStart(message) {
    try {
      console.log('Test session started:', message.data);
      
      const testData = message.data;
      
      // Notify that we're in testing mode
      ui.notifications?.info(`Testing session ${testData.test_session_id} started`);
      
      // Trigger normal AI turn flow to collect messages
      // This ensures messages are collected from Foundry chat properly
      // Check multiple locations for the goldBox instance and wait for initialization
      let goldBoxInstance = window.goldBox || (typeof game !== 'undefined' && game.goldBox);
      
      // If module instance not found, wait a bit and try again (initialization may be in progress)
      if (!goldBoxInstance) {
        console.warn('Gold Box: Module instance not immediately available, waiting for initialization...');
        
        // Try up to 5 times with 100ms delay between attempts
        let attempts = 0;
        const maxAttempts = 5;
        
        const checkInterval = setInterval(() => {
          attempts++;
          goldBoxInstance = window.goldBox || (typeof game !== 'undefined' && game.goldBox);
          
          if (goldBoxInstance) {
            clearInterval(checkInterval);
            this.activateTestMode(goldBoxInstance, testData);
          } else if (attempts >= maxAttempts) {
            clearInterval(checkInterval);
            console.error('Gold Box: Module instance still not available after waiting');
            ui.notifications?.error('Failed to start test session - module not loaded');
          }
        }, 100);
      } else {
        // Module instance found, activate test mode immediately
        this.activateTestMode(goldBoxInstance, testData);
      }
      
    } catch (error) {
      console.error('Error handling test session start:', error);
    }
  }

  /**
   * Activate test mode on the module instance
   */
  activateTestMode(goldBoxInstance, testData) {
    try {
      // Store test mode info globally so backend knows we're in test mode
      goldBoxInstance.testMode = {
        active: true,
        testSessionId: testData.test_session_id,
        aiRole: testData.ai_role
      };
      
      console.log('Gold Box: Test mode activated - triggering AI turn flow');
      console.log('Gold Box: Test session ID:', testData.test_session_id);
      console.log('Gold Box: AI Role:', testData.ai_role);
      
      // Trigger the normal AI turn button flow which will collect messages
      goldBoxInstance.onTakeAITurn();
    } catch (error) {
      console.error('Gold Box: Error activating test mode:', error);
      ui.notifications?.error('Failed to activate test mode: ' + error.message);
    }
  }

  /**
   * Handle test chat response message
   */
  handleTestChatResponse(message) {
    try {
      console.log('Test chat response received:', message.data);
      
      const testData = message.data;
      
      // Display test session info to user
      const initialPrompt = testData.initial_prompt || 'No initial prompt';
      ui.notifications?.info(`Test mode active: ${testData.message || 'Ready for testing commands'}`);
      
      // Optionally log the initial prompt to chat
      if (game.messages) {
        const whisperContent = `
          <div class="gold-box-test-mode">
            <strong>Test Session Started</strong><br>
            Session ID: ${testData.test_session_id}<br>
            <em>${testData.message}</em>
          </div>
        `;
        
        ChatMessage.create({
          speaker: { alias: 'The Gold Box Testing' },
          content: whisperContent,
          whisper: game.users.filter(u => u.isGM).map(u => u.id),
          type: CONST.CHAT_MESSAGE_TYPES.WHISPER
        });
      }
      
    } catch (error) {
      console.error('Error handling test chat response:', error);
    }
  }

  /**
   * Handle test session end message
   */
  handleTestSessionEnd(message) {
    try {
      console.log('Test session ended:', message.data);
      
      const testData = message.data;
      
      // Get goldBox instance
      let goldBoxInstance = window.goldBox || (typeof game !== 'undefined' && game.goldBox);
      
      if (goldBoxInstance && goldBoxInstance.testMode) {
        // Clean up test mode state
        goldBoxInstance.testMode = {
          active: false,
          testSessionId: null,
          aiRole: null
        };
        
        console.log('Gold Box: Test mode deactivated');
        
        // Use unified cleanup handler for turn completion
        // This ensures both button state and delta counters are reset
        if (goldBoxInstance.api && goldBoxInstance.api.handleTurnCompletion) {
          goldBoxInstance.api.handleTurnCompletion();
        }
      }
      
      // Handle WebSocket reset (default behavior)
      if (testData.reset_connection !== false) {
        console.log('Gold Box: WebSocket reset requested');
        
        // Notify user about reconnect
        ui.notifications?.info('Testing session ended - reconnecting...');
        
        // Disconnect and reconnect with new client ID
        console.log('Gold Box: Disconnecting WebSocket...');
        this.manualDisconnect = true; // Prevent auto-reconnect during reset
        this.disconnect();
        
        // Wait 1 second, then reconnect with new client ID
        setTimeout(() => {
          console.log('Gold Box: Generating new client ID...');
          this.clientId = this.generateClientId();
          console.log('Gold Box: New client ID:', this.clientId);
          console.log('Gold Box: Reconnecting...');
          this.connect();
        }, 1000);
      } else {
        // No reset, just notify
        ui.notifications?.info(`Testing session ${testData.test_session_id} ended`);
      }
      
      // Optionally log to chat
      if (game.messages) {
        const whisperContent = `
          <div class="gold-box-test-mode">
            <strong>Test Session Ended</strong><br>
            Session ID: ${testData.test_session_id}<br>
            ${testData.reset_connection !== false ? '<em>WebSocket connection reset</em>' : ''}
          </div>
        `;
        
        ChatMessage.create({
          speaker: { alias: 'The Gold Box Testing' },
          content: whisperContent,
          whisper: game.users.filter(u => u.isGM).map(u => u.id),
          type: CONST.CHAT_MESSAGE_TYPES.WHISPER
        });
      }
      
    } catch (error) {
      console.error('Error handling test session end:', error);
    }
  }

  /**
   * Handle WebSocket close event
   */
  handleClose(event) {
    console.log('WebSocket connection closed:', event.code, event.reason);
    this.isConnected = false;
    this.stopPingInterval();

    // Notify disconnection
    if (this.onDisconnected) {
      this.onDisconnected();
    }

    // Clear pending requests
    for (const [requestId, resolver] of this.pendingRequests) {
      resolver({
        success: false,
        error: 'Connection closed'
      });
    }
    this.pendingRequests.clear();

    // Don't auto-reconnect if this was a manual disconnect
    if (this.manualDisconnect) {
      this.manualDisconnect = false;
      console.log('Manual disconnect detected - skipping auto-reconnect');
      return;
    }
  
    // Only auto-reconnect for network errors
    if (this.reconnectAttempts < this.maxReconnectAttempts) {
      this.scheduleReconnect();
    } else {
      console.error('WebSocket reconnection failed after 3 attempts');
      ui.notifications?.error('WebSocket connection lost after 3 reconnection attempts. Please refresh the page.', {permanent: true});
    }
  }

  /**
   * Handle WebSocket error event
   */
  handleError(error) {
    console.error('WebSocket error:', error);
    this.isConnected = false;
    this.stopPingInterval();
    
    // Notify disconnection on error (for failed initial connections)
    if (this.onDisconnected) {
      this.onDisconnected();
    }
    
    // Check if it's an authentication error
    if (error.data?.code === 'AUTH_REQUIRED') {
      this.onError?.(error.data.message);
    } else {
      this.onError?.(error);
    }
  }

  /**
   * Schedule reconnection attempt
   */
  scheduleReconnect() {
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
    }

    this.reconnectAttempts++;
    this.isReconnecting = true;

    // Exponential backoff: 1s, 2s, 4s
    const delay = Math.min(4000, this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1));

    console.log(`Scheduling WebSocket reconnect in ${delay}ms (attempt ${this.reconnectAttempts}/${this.maxReconnectAttempts})`);
    ui.notifications?.info(`WebSocket reconnecting in ${delay/1000}s... (attempt ${this.reconnectAttempts}/3)`);

    this.reconnectTimer = setTimeout(async () => {
      this.reconnectTimer = null;
      try {
        console.log('Attempting WebSocket reconnect...');
        await this.connect();
        this.reconnectAttempts = 0; // Reset on success
        this.isReconnecting = false;
        console.log('WebSocket reconnected successfully');
        ui.notifications?.success('WebSocket reconnected successfully');
      } catch (error) {
        console.error('WebSocket reconnection failed:', error);
        if (this.reconnectAttempts < this.maxReconnectAttempts) {
          this.scheduleReconnect();
        }
      }
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
      // Get filtered game delta before sending request
      const gameDelta = window.FrontendDeltaService?.getFilteredDelta() || {
        hasChanges: false,
        message: "No changes to game state since last AI turn"
      };

      console.log('Gold Box WebSocket: Sending game_delta:', JSON.stringify(gameDelta));
      
      // Include message_delta directly in chat_request message data (use camelCase as specified in ROADMAP)
      console.log('Gold Box WebSocket: Sending chat_request with message_delta included');
      console.log('Gold Box WebSocket: Full message data being sent:', JSON.stringify({
        type: 'chat_request',
        data: {
          messages_count: messages.length,
          context_count: options.contextCount || 15,
          scene_id: options.sceneId || null,
          force_full_context: options.forceFullContext || false,
          message_delta: gameDelta
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
          // Include message_delta in chat_request for backend access (use camelCase as specified in ROADMAP)
          message_delta: gameDelta,
          // Include client_id so backend can identify this client
          client_id: this.clientId
        }
      };

      const response = await this.send(message);
      
      // Note: Don't reset deltas here - AI Orchestrator will clear after retrieving and injecting
      
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
