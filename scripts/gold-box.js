/**
 * The Gold Box - AI-powered Foundry VTT Module
 * Main module entry point
 */

/**
 * API Communication Class for Backend Integration
 */
class GoldBoxAPI {
  constructor() {
    // Use ConnectionManager for all backend communication
    this.connectionManager = new ConnectionManager();
    // SettingsManager will be set from module
    this.settingsManager = null;
  }

  /**
   * Set SettingsManager reference
   */
  setSettingsManager(settingsManager) {
    this.settingsManager = settingsManager;
  }

  /**
   * Initialize API (called after game is ready)
   */
  init() {
    if (typeof game !== 'undefined' && game.settings) {
      // Start with default URL, will be updated by auto-discovery later
      this.baseUrl = 'http://localhost:5000';
      console.log('The Gold Box: API initialized with default URL:', this.baseUrl);
    } else {
      console.warn('The Gold Box: Game settings not available during API init');
    }
  }

  /**
   * Discover available backend port by testing multiple ports
   * @param {number} startPort - Port to start checking from (default: 5000)
   * @param {number} maxAttempts - Maximum number of ports to check (default: 20)
   * @returns {Promise<number|null>} - Found port number or null if none found
   */
  async discoverBackendPort(startPort = 5000, maxAttempts = 20) {
    console.log(`The Gold Box: Starting port discovery from ${startPort}...`);
    
    for (let i = 0; i < maxAttempts; i++) {
      const port = startPort + i;
      const testUrl = `http://localhost:${port}`;
      
      try {
        // Test connection with timeout
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 2000); // 2 second timeout
        
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
            console.log(`The Gold Box: Found backend running on port ${port}`, data);
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
   * Get auto-start instructions from backend
   */
  async getAutoStartInstructions() {
    try {
      const response = await fetch(`${this.baseUrl}/api/start`, {
        method: 'POST',
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
   * Display individual dice roll from WebSocket response
   */
  displayDiceRoll(msgData) {
    try {
      console.log('The Gold Box: Displaying dice roll:', msgData);
      
      const rollData = msgData.roll || {};
      const formula = rollData.formula || '';
      const result = rollData.result || [];
      const total = rollData.total || 0;
      
      // Create roll object for Foundry
      const roll = new Roll(formula);
      
      // Create flavor text for roll
      let flavor = 'The Gold Box Roll';
      if (msgData.author?.name) {
        flavor = `${msgData.author.name} Roll`;
      }
      
      // Create chat message with roll (using current API - define rolls directly)
      ChatMessage.create({
        user: game.user.id,
        speaker: {
          alias: msgData.author?.name || 'The Gold Box'
        },
        content: roll.formula,
        rolls: [roll], // Current API: define rolls directly instead of using type
        sound: CONFIG.sounds.dice,
        style: CONST.CHAT_MESSAGE_STYLES.ROLL // Current API: use style instead of type
      }).then(message => {
        // Update roll with actual results (Foundry creates the roll, we need to set the results)
        if (message && rollData.total !== undefined) {
          roll._total = rollData.total;
          message.update({
            content: roll.formula,
            rolls: [roll]
          });
        }
      });
      
    } catch (error) {
      console.error('The Gold Box: Error displaying dice roll:', error);
    }
  }

  /**
   * Auto-discover and update port
   */
  async autoDiscoverAndUpdatePort() {
    const discoveredPort = await this.discoverBackendPort();
    if (discoveredPort) {
      this.baseUrl = `http://localhost:${discoveredPort}`;
      return true;
    }
    return false;
  }

  /**
   * Send message context to backend with timeout handling
   */
  async sendMessageContext(messages, moduleInstance) {
    const timeout = this.settingsManager.getSetting('aiResponseTimeout', 60);
    
    try {
      // Send request with timeout and retry logic
      const response = await Promise.race([
        this.sendMessageContextWithRetry(messages),
        new Promise((_, reject) => setTimeout(() => reject(new Error('AI response timeout')), timeout * 1000))
      ]);
      
      if (response.success) {
        // Display success response
        moduleInstance.displayAIResponse(response.data.response, response.data);
      } else {
        // Display error response
        moduleInstance.displayErrorResponse(response.error || 'Unknown error occurred');
      }
      
    } catch (error) {
      console.error('The Gold Box: Error processing AI turn:', error);
      moduleInstance.displayErrorResponse(error.message);
    }
  }

  /**
   * Send message context to backend with retry logic
   */
  async sendMessageContextWithRetry(messages, maxRetries = 1) {
    for (let attempt = 0; attempt <= maxRetries; attempt++) {
      try {
        const response = await this.sendMessageContext(messages);
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
   * Send message context to backend with processing mode support and client ID relay
   */
  async sendMessageContext(messages) {
    // Note: API Bridge functionality removed - using native WebSocket client instead
    
    try {
      const processingMode = this.settingsManager.getProcessingMode();
      
      let endpoint;
      let requestData;
      
      // STEP 1: Sync settings to admin endpoint FIRST (Phase 2 fix)
      console.log('The Gold Box: Syncing settings to admin endpoint before chat request...');
      const settings = this.getUnifiedFrontendSettings();
      const adminPassword = settings['backend password'];
      
      if (adminPassword && adminPassword.trim()) {
        const syncResult = await this.syncSettings(settings, adminPassword);
        if (syncResult.success) {
          console.log('The Gold Box: Settings synced successfully to admin endpoint');
        } else {
          console.warn('The Gold Box: Settings sync failed:', syncResult.error);
        }
      } else {
        console.warn('The Gold Box: No backend password configured, skipping settings sync');
      }
      
      // STEP 2: Check if WebSocket is available and use it
      if (processingMode === 'api' && this.webSocketClient) {
        // Check if WebSocket is connected (more robust check)
        const wsConnected = this.webSocketClient.isConnected || this.webSocketClient.connectionState === 'connected';
        if (wsConnected) {
          console.log('The Gold Box: Using WebSocket for API mode');
          return await this.sendViaWebSocket(messages);
        } else {
          console.log('The Gold Box: WebSocket client exists but not connected, falling back to HTTP API');
          console.log('The Gold Box: WebSocket client exists:', !!this.webSocketClient);
          console.log('The Gold Box: WebSocket connection state:', this.webSocketClient.connectionState || 'unknown');
          console.log('The Gold Box: WebSocket isConnected property:', this.webSocketClient.isConnected);
        }
      } else if (processingMode === 'api') {
        console.log('The Gold Box: WebSocket not available, falling back to HTTP API');
        console.log('The Gold Box: WebSocket client exists:', !!this.webSocketClient);
        console.log('The Gold Box: WebSocket connected:', this.webSocketClient ? this.webSocketClient.isConnected : 'N/A');
      }
      
      // STEP 3: Fallback to HTTP API
      if (processingMode === 'context') {
        // NEW: Context mode with full board state integration
        endpoint = '/api/context_chat';
        
        // Get scene ID from current scene
        const sceneId = canvas?.scene?.id || game.scenes?.active?.id;
        const clientId = this.webSocketClient ? this.webSocketClient.clientId : null;
        
        requestData = {
          client_id: clientId || 'default-client',
          scene_id: sceneId || 'default-scene',
          message: messages.length > 0 ? messages[messages.length - 1].content : 'No message provided',
          context_options: {
            include_chat_history: true,
            message_count: this.settingsManager.getSetting('maxMessageContext', 15),
            include_scene_data: true,
            include_tokens: true,
            include_walls: true,
            include_lighting: true,
            include_map_notes: true,
            include_templates: true
          },
          ai_options: {
            model: this.settingsManager.getSetting('generalLlmModel') || 'gpt-4',
            temperature: 0.7,
            max_tokens: 2000
          }
        };
        console.log('The Gold Box: Using CONTEXT mode with endpoint:', endpoint, '- full board state integration');
        console.log('The Gold Box: Scene ID:', sceneId, 'Client ID:', clientId);
      } else if (processingMode === 'api') {
        endpoint = '/api/api_chat';
        // Include client ID in request data if available
        const clientId = this.webSocketClient ? this.webSocketClient.clientId : null;
        console.log("The Gold Box: WebSocket client available:", !!this.webSocketClient);
        console.log("The Gold Box: WebSocket connected:", this.webSocketClient ? this.webSocketClient.isConnected : "N/A");
        requestData = {
          // NO settings here - backend will use stored settings
          context_count: this.settingsManager.getSetting('maxMessageContext', 15),
          settings: clientId ? { 'relay client id': clientId } : null // Include client ID, allow null if not connected
        };
        console.log('The Gold Box: Using API mode with client ID:', clientId || 'not connected', '- settings from backend storage');
      } else {
        // Should never reach here with only 'api' and 'context' modes
        throw new Error(`Unsupported processing mode: ${processingMode}. Supported modes: 'api', 'context'`);
      }
      
      // Use ConnectionManager for request
      const response = await this.connectionManager.makeRequest(endpoint, requestData);
      
      return response;
      
    } catch (error) {
      console.error('Gold Box API Error:', error);
      throw error;
    }
  }

  /**
   * Send chat request via WebSocket
   */
  async sendViaWebSocket(messages) {
    if (!this.webSocketClient || !this.webSocketClient.isConnected) {
      throw new Error('WebSocket not connected');
    }

    try {
      const response = await this.webSocketClient.sendChatRequest(messages, {
        contextCount: this.settingsManager.getSetting('maxMessageContext', 15),
        sceneId: canvas?.scene?.id || game.scenes?.active?.id
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
      console.error('The Gold Box: WebSocket chat request error:', error);
      throw error;
    }
  }

  /**
   * Display AI response in chat with context mode support
   */
  showProcessingIndicator() {
    // Remove existing indicator
    const existing = document.querySelector('.gold-box-processing');
    if (existing) {
      existing.remove();
    }
    
    // Create and show new indicator
    const indicator = document.createElement('div');
    indicator.className = 'gold-box-processing';
    indicator.style.cssText = `
      position: fixed;
      top: 50%;
      left: 50%;
      transform: translate(-50%, -50%);
      background: rgba(0, 0, 0, 0.8);
      color: white;
      padding: 20px;
      border-radius: 8px;
      z-index: 1000;
      font-weight: bold;
      box-shadow: 0 4px 8px rgba(0, 0, 0, 0.3);
    `;
    indicator.innerHTML = 'AI Processing...';
    
    document.body.appendChild(indicator);
  }

  /**
   * Hide processing indicator
   */
  hideProcessingIndicator() {
    const indicator = document.querySelector('.gold-box-processing');
    if (indicator) {
      indicator.remove();
    }
  }

  /**
   * Sync settings to backend admin endpoint
   */
  async syncSettings(settings, adminPassword) {
    try {
      const response = await fetch(`${this.baseUrl}/api/admin`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Admin-Password': adminPassword
        },
        body: JSON.stringify({
          command: 'update_settings',
          settings: settings
        })
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
   * Get unified frontend settings using SettingsManager
   */
  getUnifiedFrontendSettings() {
    return this.settingsManager.getAllSettings();
  }

  /**
   * Set button processing state with visual feedback
   */
  setButtonProcessingState(button, isProcessing) {
    if (!button) return;
    
    if (isProcessing) {
      button.disabled = true;
      const processingMode = this.settingsManager.getProcessingMode();
      button.innerHTML = processingMode === 'context' ? 'Context Processing...' : 'AI Thinking...';
      button.style.opacity = '0.6';
      button.style.cursor = 'not-allowed';
    } else {
      button.disabled = false;
      const processingMode = this.settingsManager.getProcessingMode();
      button.innerHTML = this.settingsManager.getButtonText();
      button.style.opacity = '1';
      button.style.cursor = 'pointer';
    }
  }
}

class GoldBoxModule {
  constructor() {
    this.hooks = [];
    this.api = new GoldBoxAPI();
    // Initialize Settings Manager
    this.settingsManager = new SettingsManager();
  }

  /**
   * Initialize module
   */
  async init() {
    console.log('The Gold Box module initialized');
    
    // Register hooks
    this.registerHooks();
    
    // Initialize API with game settings
    this.api.init();
    
    // Set SettingsManager reference in API
    this.api.setSettingsManager(this.settingsManager);
    
    // Check backend connection automatically (delayed until world is ready)
    Hooks.once('ready', async () => {
      // Phase 4: Initialize with enhanced Connection Manager
      await this.initializeWithConnectionManager();
      
      this.checkBackendAndShowInstructions();
    });
    
    console.log('The Gold Box is ready for AI adventures!');
  }

  /**
   * Initialize WebSocket connection (replaces API bridge)
   */
  async initializeWebSocketConnection() {
    console.log('The Gold Box: Initializing native WebSocket connection...');
    
    // Check if WebSocket client is available
    if (typeof GoldBoxWebSocketClient !== 'undefined') {
      try {
        this.webSocketClient = new GoldBoxWebSocketClient(
          this.api.baseUrl,
          (message) => this.handleWebSocketMessage(message),
          (error) => this.handleWebSocketError(error)
        );

        // Initialize message collector
        if (typeof MessageCollector !== 'undefined') {
          this.messageCollector = new MessageCollector();
          this.messageCollector.start();
          console.log('The Gold Box: Message collector started');
        }

        // Connect to WebSocket server
        const connected = await this.webSocketClient.connect();
        
        if (connected) {
          console.log('The Gold Box: WebSocket connection established successfully');
          
          // Wait for connection to be fully established
          await this.webSocketClient.waitForConnection(5000);
          
          // Store WebSocket client reference in API for message collection
          this.api.webSocketClient = this.webSocketClient;
          
          console.log('The Gold Box: WebSocket connection ready');
          console.log('The Gold Box: WebSocket client details:', this.webSocketClient.getConnectionStatus());
          return true;
        } else {
          console.warn('The Gold Box: WebSocket connection failed');
          this.webSocketClient = null;
          if (this.messageCollector) {
            this.messageCollector.stop();
          }
          return false;
        }
        
      } catch (error) {
        console.error('The Gold Box: WebSocket connection error:', error);
        this.webSocketClient = null;
        if (this.messageCollector) {
          this.messageCollector.stop();
        }
        return false;
      }
    } else {
      console.warn('The Gold Box: GoldBoxWebSocketClient class not available - WebSocket client module may not be loaded');
      this.webSocketClient = null;
      return false;
    }
  }

  /**
   * Initialize with enhanced Connection Manager (Phase 4)
   */
  async initializeWithConnectionManager() {
    console.log('The Gold Box: Phase 4 initialization with enhanced Connection Manager...');
    
    try {
      // Step 1: Initialize Connection Manager
      await this.api.connectionManager.initialize();
      console.log('The Gold Box: Connection Manager initialized');
      
      // Step 2: Try WebSocket connection first
      const wsConnected = await this.initializeWebSocketConnection();
      
      if (wsConnected) {
        console.log('The Gold Box: WebSocket connection established');
        
        // Step 3: Set WebSocket client in Connection Manager
        this.api.connectionManager.setWebSocketClient(this.webSocketClient);
        
        // Step 4: Flush any batch sync data
        await this.api.connectionManager.flushBatchSyncData();
        
        // Step 5: Set up real-time data synchronization
        this.setupRealTimeSync();
        
        console.log('The Gold Box: Phase 4 initialization complete - WebSocket first');
        return true;
      } else {
        console.log('The Gold Box: WebSocket failed, falling back to HTTP-only mode');
        console.log('The Gold Box: Phase 4 initialization complete - HTTP fallback');
        return false;
      }
      
    } catch (error) {
      console.error('The Gold Box: Phase 4 initialization failed:', error);
      console.log('The Gold Box: Phase 4 initialization complete - HTTP fallback');
      return false;
    }
  }

  /**
   * Set up real-time data synchronization (Phase 4)
   */
  setupRealTimeSync() {
    if (!this.webSocketClient || !this.api.connectionManager) {
      console.warn('The Gold Box: Cannot set up real-time sync - missing components');
      return;
    }
    
    // Set up message handlers for real-time sync
    this.webSocketClient.onMessageType('data_sync', (message) => {
      this.handleRealTimeSync(message);
    });
    
    this.webSocketClient.onMessageType('batch_sync', (message) => {
      this.handleBatchSync(message);
    });
    
    console.log('The Gold Box: Real-time synchronization set up');
  }

  /**
   * Handle real-time sync messages (Phase 4)
   */
  handleRealTimeSync(message) {
    try {
      const syncData = message.data;
      console.log('The Gold Box: Received real-time sync:', syncData.sync_type);
      
      switch (syncData.sync_type) {
        case 'settings_update':
          // Handle settings synchronization
          this.handleSettingsSync(syncData.sync_data);
          break;
          
        case 'scene_change':
          // Handle scene change notifications
          this.handleSceneChangeSync(syncData.sync_data);
          break;
          
        case 'user_activity':
          // Handle user activity tracking
          this.handleUserActivitySync(syncData.sync_data);
          break;
          
        default:
          console.log('The Gold Box: Unknown sync type:', syncData.sync_type);
      }
      
    } catch (error) {
      console.error('The Gold Box: Error handling real-time sync:', error);
    }
  }

  /**
   * Handle batch sync messages (Phase 4)
   */
  handleBatchSync(message) {
    try {
      const batchData = message.data;
      console.log('The Gold Box: Received batch sync with', batchData.sync_items.length, 'items');
      
      // Process each sync item
      batchData.sync_items.forEach(item => {
        this.handleRealTimeSync({ data: item });
      });
      
    } catch (error) {
      console.error('The Gold Box: Error handling batch sync:', error);
    }
  }

  /**
   * Handle settings synchronization (Phase 4)
   */
  handleSettingsSync(settingsData) {
    try {
      console.log('The Gold Box: Processing settings sync');
      
      // Update local settings if needed
      if (typeof game !== 'undefined' && game.settings) {
        Object.keys(settingsData).forEach(key => {
          if (settingsData[key] && settingsData[key] !== game.settings.get('the-gold-box', key)) {
            console.log('The Gold Box: Syncing setting', key, '=', settingsData[key]);
            // Note: This would require GM permissions
          }
        });
      }
      
    } catch (error) {
      console.error('The Gold Box: Error handling settings sync:', error);
    }
  }

  /**
   * Handle scene change synchronization (Phase 4)
   */
  handleSceneChangeSync(sceneData) {
    try {
      console.log('The Gold Box: Processing scene change sync');
      
      // Update UI or trigger scene-specific actions
      if (sceneData.scene_id && canvas?.scene?.id !== sceneData.scene_id) {
        console.log('The Gold Box: Scene changed to', sceneData.scene_id);
        // Could trigger scene-specific AI behaviors here
      }
      
    } catch (error) {
      console.error('The Gold Box: Error handling scene change sync:', error);
    }
  }

  /**
   * Handle user activity synchronization (Phase 4)
   */
  handleUserActivitySync(activityData) {
    try {
      console.log('The Gold Box: Processing user activity sync');
      
      // Could be used for collaborative features or activity tracking
      if (activityData.user_id && activityData.activity) {
        console.log('The Gold Box: User activity:', activityData.user_id, activityData.activity);
      }
      
    } catch (error) {
      console.error('The Gold Box: Error handling user activity sync:', error);
    }
  }

  /**
   * Register Foundry VTT hooks
   */
  registerHooks() {
    console.log('The Gold Box: Starting settings registration...');
    
    // Check if settings are available
    if (!game.settings) {
      console.error('The Gold Box: game.settings not available during hook registration');
      return;
    }
    
    // Use SettingsManager to register all settings
    this.settingsManager.registerAllSettings();

    // Add click handler for discovery button (after SettingsManager has registered the button)
    Hooks.on('renderSettingsConfig', (app, html, data) => {
      const $html = $(html);
      $html.find('#gold-box-discover-port').on('click', () => {
        this.manualPortDiscovery();
      });
    });

    // Note: Game ready hook is now consolidated above with API bridge initialization

    // Hook to add chat button when sidebar tab is rendered
    Hooks.on('renderSidebarTab', (app, html, data) => {
      console.log('The Gold Box: renderSidebarTab hook fired for', app.options.id);
      if (app.options.id === 'chat') {
        this.addChatButton(html);
      }
    });

    // Also try hooking to chat log render as backup
    Hooks.on('renderChatLog', (app, html, data) => {
      console.log('The Gold Box: renderChatLog hook fired');
      this.addChatButton(html);
    });

    // Hook to update button when settings change
    Hooks.on('updateSettings', (settings) => {
      console.log('The Gold Box: Settings updated, updating chat button');
      this.updateChatButtonText();
    });
  }

  /**
   * Collect recent chat messages from DOM in chronological order
   * Enhanced for patch 0.2.6 with complete HTML preservation
   * @param {number} maxMessages - Maximum number of messages to collect
   * @returns {Array} - Array of message objects in chronological order
   */
  collectChatMessages(maxMessages = 15) {
    const messages = [];
    const chatElements = document.querySelectorAll('.chat-message');
    
    // Get LAST maxMessages elements (most recent messages - bottom of chat)
    const recentElements = Array.from(chatElements).slice(-maxMessages);
    
    recentElements.forEach(element => {
      // Extract COMPLETE HTML element including all structure for dice rolls, cards, etc.
      // This preserves Foundry's rich HTML structure for backend processing
      const fullHtml = element.outerHTML.trim();
      
      // Enhanced metadata extraction for patch 0.2.6
      const timestampElement = element.querySelector('.message-timestamp');
      const timestamp = timestampElement ? timestampElement.textContent : new Date().toISOString();
      
      // Extract sender information for better context preservation
      const senderElement = element.querySelector('.message-sender, .sender, h4');
      const sender = senderElement ? senderElement.textContent.trim() : 'Unknown';
      
      // Only add if we have HTML content
      if (fullHtml) {
        messages.push({
          content: fullHtml,  // Send complete HTML, not extracted content
          timestamp: timestamp,
          sender: sender,  // Add sender for better backend processing
          type: this.detectMessageType(element)  // Add type hint for backend
        });
      }
    });
    
    console.log('The Gold Box: Collected messages:', messages.length, 'messages with full HTML content');
    console.log('The Gold Box: Sample message structure:', messages[0] ? 'content length: ' + messages[0].content.length + ', sender: ' + messages[0].sender + ', type: ' + messages[0].type : 'No messages');
    
    // Returns in chronological order (oldest first, newest last)
    return messages;
  }

  /**
   * Detect message type from DOM element for enhanced backend processing
   * Helps backend processor with classification hints
   * @param {Element} element - Chat message DOM element
   * @returns {string} - Detected message type
   */
  detectMessageType(element) {
    const classList = element.className;
    
    // Check for specific message types in order of priority
    if (classList.includes('whisper')) return 'whisper';
    if (classList.includes('gm-message')) return 'gm-message';
    if (classList.includes('dice-roll')) return 'dice-roll';
    if (classList.includes('attack-card')) return 'attack-roll';
    if (classList.includes('save-card')) return 'saving-throw';
    if (classList.includes('spell-card') || classList.includes('activation-card')) return 'chat-card';
    if (classList.includes('condition-card')) return 'condition-card';
    if (classList.includes('roll-table-result')) return 'table-result';
    
    // Default to player chat if no specific type detected
    return 'player-chat';
  }

  /**
   * Add "Take AI Turn" button to chat interface
   */
  addChatButton(html) {
    console.log('The Gold Box: Adding chat button...');
    
    // Handle both jQuery and plain DOM objects
    const $html = $(html);
    
    // Remove existing button to prevent duplicates
    $html.find('#gold-box-ai-turn-btn').remove();
    
    // Try multiple selectors for Foundry's chat form structure
    let chatForm = $html.find('#chat-form');
    let messageInput = $html.find('textarea[name="message"]');
    
    // Fallback selectors if primary ones don't work
    if (chatForm.length === 0) {
      chatForm = $html.find('form.chat-form');
    }
    if (messageInput.length === 0) {
      messageInput = $html.find('textarea');
      if (messageInput.length > 1) {
        messageInput = $html.find('textarea').first(); // Get first textarea
      }
    }
    
    // Last resort: try to find any suitable container
    if (chatForm.length === 0) {
      const container = $html.find('.chat-messages, .chat-log, .chat-container');
      if (container.length > 0) {
        // Create a simple button and append to container
        this.addSimpleButton(container);
        return;
      }
      
      console.warn('The Gold Box: Chat form not found, waiting for DOM to be ready...');
      // Only retry a few times, not infinitely
      if (!this.buttonRetryCount) this.buttonRetryCount = 0;
      if (this.buttonRetryCount < 3) {
        this.buttonRetryCount++;
        setTimeout(() => this.addChatButton(html), 2000);
      } else {
        console.error('The Gold Box: Failed to find chat form after multiple attempts');
      }
      return;
    }
    
    // Get current processing mode for button text
    const processingMode = this.settingsManager.getProcessingMode();
    const buttonText = this.settingsManager.getButtonText();
    
    // Create button with enhanced styling and accessibility
    const button = $(`
      <button id="gold-box-ai-turn-btn" 
              class="gold-box-ai-turn-btn" 
              type="button" 
              title="Trigger AI response based on current processing mode"
              aria-label="Take AI Turn"
              style="
                background: linear-gradient(135deg, #FFD700 0%, #FFA500 50%, #FF8C00 100%);
                color: #1a1a1a;
                border: none;
                padding: 8px 12px;
                margin-left: 5px;
                border-radius: 4px;
                cursor: pointer;
                font-weight: 600;
                font-size: 12px;
                transition: all 0.2s ease;
                box-shadow: 0 1px 3px rgba(0,0,0,0.3), 0 2px 6px rgba(0,0,0,0.2);
                flex-shrink: 0;
              ">
        ${buttonText}
      </button>
    `);
    
    // Add button after message input
    if (messageInput.length > 0) {
      messageInput.after(button);
    } else {
      // Fallback: add to form
      chatForm.append(button);
    }
    
    // Add click handler
    button.on('click', (e) => {
      e.preventDefault();
      this.onTakeAITurn();
    });
    
    console.log('The Gold Box: Chat button added successfully');
  }

  /**
   * Add simple button when chat form structure is not available
   */
  addSimpleButton(container) {
    console.log('The Gold Box: Adding simple button to container...');
    
    // Get current processing mode for button text
    const processingMode = this.settingsManager.getProcessingMode();
    const buttonText = this.settingsManager.getButtonText();
    
    // Create button with enhanced styling
    const button = $(`
      <button id="gold-box-ai-turn-btn" 
              class="gold-box-ai-turn-btn" 
              type="button" 
              title="Trigger AI response based on current processing mode"
              style="
                background: linear-gradient(135deg, #FFD700 0%, #FFA500 50%, #FF8C00 100%);
                color: #1a1a1a;
                border: none;
                padding: 8px 12px;
                margin: 5px;
                border-radius: 4px;
                cursor: pointer;
                font-weight: 600;
                font-size: 12px;
                transition: all 0.2s ease;
                box-shadow: 0 1px 3px rgba(0,0,0,0.3), 0 2px 6px rgba(0,0,0,0.2);
              ">
        ${buttonText}
      </button>
    `);
    
    // Add button to container
    container.append(button);
    
    // Add click handler
    button.on('click', (e) => {
      e.preventDefault();
      this.onTakeAITurn();
    });
    
    console.log('The Gold Box: Simple button added successfully');
  }

  /**
   * Update button text when processing mode changes
   */
  updateChatButtonText() {
    const button = $('#gold-box-ai-turn-btn');
    if (button.length > 0) {
      const processingMode = this.settingsManager.getProcessingMode();
      const buttonText = this.settingsManager.getButtonText();
      button.text(buttonText);
      console.log('The Gold Box: Updated button text to:', buttonText);
    }
  }

  /**
   * Handle "Take AI Turn" button click
   */
  async onTakeAITurn() {
    console.log('The Gold Box: Take AI Turn button clicked');
    
    const button = document.getElementById('gold-box-ai-turn-btn');
    if (!button) {
      console.error('The Gold Box: Button not found');
      return;
    }
    
    // Set processing state
    this.api.setButtonProcessingState(button, true);
    
    try {
      // Collect chat messages for context
      const messages = this.collectChatMessages();
      
      // Send to backend for processing
      await this.api.sendMessageContext(messages, this);
      
    } catch (error) {
      console.error('The Gold Box: Error in AI turn:', error);
      this.displayErrorResponse(error.message);
    } finally {
      // Reset button state
      this.api.setButtonProcessingState(button, false);
    }
  }

  /**
   * Handle WebSocket message from server
   */
  handleWebSocketMessage(message) {
    try {
      console.log('The Gold Box: Received WebSocket message:', message);
      
      switch (message.type) {
        case 'chat_response':
          // Handle AI response from WebSocket - NEW: support structured message data
          if (message.data && message.data.message) {
            const msgData = message.data.message;
            
            // Handle different message types from structured AI response
            switch (msgData.type) {
              case 'chat-message':
                // Display chat message in Foundry chat
                this.displayChatMessage(msgData);
                break;
                
              case 'dice-roll':
                // Display dice roll in Foundry chat
                this.displayDiceRoll(msgData);
                break;
                
              case 'chat-card':
                // Display chat card in Foundry chat
                this.displayChatCard(msgData);
                break;
                
              default:
                console.log('The Gold Box: Unknown message type in chat_response:', msgData.type);
                // Fallback: try to display as simple response
                if (typeof msgData.content === 'string') {
                  this.displayAIResponse(msgData.content, message.data);
                }
            }
          } else if (message.data && message.data.response) {
            // Fallback for legacy format (simple string response)
            this.displayAIResponse(message.data.response, message.data);
          }
          break;
          
        case 'error':
          // Handle error from WebSocket
          if (message.data && message.data.error) {
            this.displayErrorResponse(message.data.error);
          }
          break;
          
        case 'connected':
          console.log('The Gold Box: WebSocket connection confirmed');
          break;
          
        default:
          console.log('The Gold Box: Unknown WebSocket message type:', message.type);
      }
    } catch (error) {
      console.error('The Gold Box: Error handling WebSocket message:', error);
    }
  }

  /**
   * Display individual chat message from WebSocket response
   */
  displayChatMessage(msgData) {
    try {
      console.log('The Gold Box: Displaying chat message:', msgData);
      
      // Always use "The Gold Box" as the speaker to clearly label AI-generated content
      const content = msgData.content || '';
      
      // Create chat message in Foundry (using current API)
      ChatMessage.create({
        user: game.user.id,
        content: content,
        speaker: {
          alias: 'The Gold Box' // Always show as The Gold Box to avoid confusion
        },
        style: CONST.CHAT_MESSAGE_STYLES.IC // In-character message (current API)
      });
      
    } catch (error) {
      console.error('The Gold Box: Error displaying chat message:', error);
    }
  }

  /**
   * Display individual dice roll from WebSocket response
   */
  async displayDiceRoll(msgData) {
    try {
      console.log('The Gold Box: Displaying dice roll:', msgData);
      
      const rollData = msgData.roll || {};
      const formula = rollData.formula || '';
      const result = rollData.result || [];
      const total = rollData.total || 0;
      
      // Create roll object for Foundry and evaluate it asynchronously
      const roll = new Roll(formula);
      await roll.evaluate(); // Async evaluation for complex formulas
      
      // Override the total with the AI-provided result
      roll._total = total;
      
      // Create flavor text for the roll
      let flavor = 'The Gold Box Roll';
      if (msgData.author?.name) {
        flavor = `${msgData.author.name} Roll`;
      }
      
      // Create chat message with roll (using current API - no deprecated style)
      await ChatMessage.create({
        user: game.user.id,
        speaker: {
          alias: 'The Gold Box' // Always show as The Gold Box to avoid confusion
        },
        content: roll.formula,
        rolls: [roll], // Current API: define rolls directly (roll is already evaluated)
        sound: CONFIG.sounds.dice
        // Removed deprecated style: CONST.CHAT_MESSAGE_STYLES.ROLL
      });
      
    } catch (error) {
      console.error('The Gold Box: Error displaying dice roll:', error);
    }
  }

  /**
   * Display individual chat card from WebSocket response
   */
  displayChatCard(msgData) {
    try {
      console.log('The Gold Box: Displaying chat card:', msgData);
      
      const title = msgData.title || 'The Gold Box';
      const description = msgData.description || '';
      const actions = msgData.actions || [];
      
      // Create HTML for the card
      let cardContent = `
        <div class="gold-box-chat-card">
          <div class="card-header">
            <h3>${title}</h3>
          </div>
          <div class="card-content">
            ${description ? `<p>${description}</p>` : ''}
          </div>
          ${actions.length > 0 ? `
            <div class="card-actions">
              ${actions.map(action => {
                if (typeof action === 'string') {
                  return `<button class="gold-box-card-action" data-action="${action}">${action}</button>`;
                } else if (action.name && action.action) {
                  return `<button class="gold-box-card-action" data-action="${action.action}" data-name="${action.name}">${action.name}</button>`;
                }
                return `<button class="gold-box-card-action">${action.toString()}</button>`;
              }).join('')}
            </div>
          ` : ''}
        </div>
      `;
      
      // Create chat message with card (using current API)
      ChatMessage.create({
        user: game.user.id,
        speaker: {
          alias: 'The Gold Box'
        },
        content: cardContent,
        style: CONST.CHAT_MESSAGE_STYLES.OTHER // Current API: use style instead of type
      });
      
    } catch (error) {
      console.error('The Gold Box: Error displaying chat card:', error);
    }
  }

  /**
   * Handle WebSocket error
   */
  handleWebSocketError(error) {
    console.error('The Gold Box: WebSocket error:', error);
    
    // Show error notification to user
    if (typeof ui !== 'undefined' && ui.notifications) {
      ui.notifications.error('WebSocket connection error: ' + (error.message || error));
    }
  }

  /**
   * Display AI response in chat with context mode support
   */
  displayAIResponse(response, metadata) {
    // Use hardcoded name since we removed moduleElementsName setting
    const customName = 'The Gold Box';
    const role = this.settingsManager.getSetting('aiRole', 'dm');
    const processingMode = this.settingsManager.getProcessingMode();
    
    const roleDisplay = {
      'dm': 'Dungeon Master',
      'dm_assistant': 'DM Assistant',
      'player': 'Player'
    };
    
    // Check if messages were sent via relay server successfully
    const isRelaySuccess = metadata && metadata.metadata && metadata.metadata.messages_sent > 0 && !metadata.metadata.relay_error;
    
    // When relay transmission works, don't show a separate message - the AI response was already sent to chat
    if (isRelaySuccess) {
      console.log('The Gold Box: Relay transmission successful, skipping duplicate message creation');
      return; // Skip creating duplicate message since relay already sent the AI response
    }
    
    let messageContent;
    let contextInfo = '';
    
    // Add context mode indicators
    if (processingMode === 'context') {
      contextInfo = `
        <div class="gold-box-context-info">
          <p><strong>Context Mode Active</strong> - AI considered complete board state</p>
          ${metadata && metadata.metadata ? `
            <p><em>Context Elements:</em> ${metadata.metadata.board_elements ? Object.keys(metadata.metadata.board_elements).filter(k => metadata.metadata.board_elements[k]).join(', ') : 'scene data'}</p>
            <p><em>Attributes Mapped:</em> ${metadata.metadata.attributes_mapped || 0} attributes</p>
            <p><em>Compression:</em> ${metadata.metadata.compression_ratio ? (metadata.metadata.compression_ratio * 100).toFixed(1) + '%' : 'N/A'}</p>
          ` : ''}
        </div>
      `;
    }
    
    if (metadata && metadata.relay_error) {
      // Error case when relay server transmission failed - show actual AI response
      messageContent = `
        <div class="gold-box-error">
          <div class="gold-box-header">
            <strong>${customName} - Relay Transmission Error</strong>
            <div class="gold-box-timestamp">${new Date().toLocaleTimeString()}</div>
          </div>
          <div class="gold-box-content">
            ${contextInfo}
            <p><strong>AI Response:</strong></p>
            <div class="ai-response-content">${response}</div>
            <p><strong>Relay Error:</strong> ${metadata.relay_error}</p>
            <p><em>Messages were processed but could not be sent to Foundry chat via relay server.</em></p>
            <p><em>Please check relay server connection and client ID configuration.</em></p>
          </div>
        </div>
      `;
    } else {
      // Display actual AI response content - not debug information
      // This handles the case where relay is not used or messages_sent is 0
      messageContent = `
        <div class="gold-box-response">
          <div class="gold-box-header">
            <strong>${customName} - ${roleDisplay[role] || 'AI Response'}${processingMode === 'context' ? ' (Context-Aware)' : ''}</strong>
            <div class="gold-box-timestamp">${new Date().toLocaleTimeString()}</div>
          </div>
          <div class="gold-box-content">
            ${contextInfo}
            <div class="ai-response-content">${response}</div>
            ${metadata && metadata.provider_used ? `
              <div class="ai-metadata">
                <p><em>Processed using ${metadata.provider_used} - ${metadata.model_used} (${metadata.tokens_used} tokens)</em></p>
                ${processingMode === 'context' && metadata.metadata ? `
                  <p><em>Context: ${metadata.metadata.attribute_count || 0} attributes, ${metadata.metadata.scene_id ? 'scene ' + metadata.metadata.scene_id : 'default scene'}</em></p>
                ` : ''}
              </div>
            ` : ''}
          </div>
        </div>
      `;
    }
    
    // Send message to chat
    ChatMessage.create({
      user: game.user.id,
      content: messageContent,
      speaker: {
        alias: customName
      }
    });
  }

  /**
   * Display error response in chat
   */
  displayErrorResponse(error) {
    // Use hardcoded name since we removed moduleElementsName setting
    const customName = 'The Gold Box';
    
    const messageContent = `
      <div class="gold-box-error">
        <div class="gold-box-header">
          <strong>${customName} - Error</strong>
        </div>
        <div class="gold-box-content">
          <p><strong>Error:</strong> ${error}</p>
          <p>Please check your backend connection and settings.</p>
        </div>
      </div>
    `;
    
    // Send error message to chat
    ChatMessage.create({
      user: game.user.id,
      content: messageContent,
      speaker: {
        alias: customName
      }
    });
  }

  /**
   * Display startup instructions prominently in chat
   */
  displayStartupInstructions() {
    // Use hardcoded name since we removed moduleElementsName setting
    const customName = 'The Gold Box';
    
    // Startup instructions without rocket emoji
    const messageContent = `
      <div class="gold-box-startup">
        <div class="gold-box-header">
          <strong>${customName} - Backend Startup Required</strong>
          <div class="gold-box-timestamp">${new Date().toLocaleTimeString()}</div>
        </div>
        <div class="gold-box-content">
          <p><strong>Backend Server Not Running or Not Reachable</strong></p>
          <p><strong>Option 1: Run</strong> automation script</p>
          <p>Run <code>./start-backend.py</code> from The Gold Box module directory to automatically set up and start the backend server.</p>
          <p>See README.md file for manual setup instructions.</p>
          <p>Go to The Gold Box settings and click "Discover Backend" to automatically find and connect to a running backend server.</p>
          <p><em>Configure your desired provider in The Gold Box settings.</em></p>
          <p><strong>Option 2: Manual setup</strong></p>
          <p>See the README.md file for manual setup instructions.</p>
          <p><strong>Option 3: Auto-discover port</strong></p>
          <p>Go to Gold Box settings and click "Discover Backend" to automatically find and connect to a running backend server.</p>
          <p><em><strong>Note:</strong> The frontend automatically discovers the backend port. Use the "Discover Backend" button if needed.</em></p>
        </div>
      </div>
    `;
    
    // Send startup instructions to chat
    ChatMessage.create({
      user: game.user.id,
      content: messageContent,
      speaker: {
        alias: customName
      },
      whisper: {
        users: [game.user.id]
      }
    });
  }

  /**
   * Check backend connection and show instructions if needed (using ConnectionManager)
   */
  async checkBackendAndShowInstructions() {
    try {
      // Initialize connection through ConnectionManager
      await this.api.connectionManager.initialize();
      
      // Get connection info for status
      const connectionInfo = this.api.connectionManager.getConnectionInfo();
      
      if (connectionInfo.state === ConnectionState.CONNECTED) {
        await game.settings.set('the-gold-box', 'backendStatus', 'connected');
        console.log('The Gold Box: Backend connected via ConnectionManager:', connectionInfo);
        return;
      } else {
        // Show instructions if connection failed
        await game.settings.set('the-gold-box', 'backendStatus', 'disconnected');
        console.log('The Gold Box: Connection failed, ConnectionManager state:', connectionInfo.state);
        this.displayStartupInstructions();
      }
    } catch (error) {
      await game.settings.set('the-gold-box', 'backendStatus', 'error');
      console.error('The Gold Box: Error checking backend:', error);
      this.displayStartupInstructions();
    }
  }

  /**
   * Enhanced manual port discovery using ConnectionManager
   */
  async manualPortDiscovery() {
    // Use ConnectionManager to initialize connection
    await this.api.connectionManager.initialize();
    
    // Get connection info for status
    const connectionInfo = this.api.connectionManager.getConnectionInfo();
    
    if (connectionInfo.state === ConnectionState.CONNECTED) {
      // Test connection to get provider info
      const healthResult = await this.api.connectionManager.testConnection();
      
      if (healthResult.success && healthResult.data && healthResult.data.configured_providers) {
        this.displayAvailableProviders(healthResult.data.configured_providers);
      }
      
      if (typeof ui !== 'undefined' && ui.notifications) {
        ui.notifications.info('Backend connection verified!');
      }
      return true;
    } else {
      // No backend found
      if (typeof ui !== 'undefined' && ui.notifications) {
        ui.notifications.error('No backend server found. Please start the backend server.');
      }
      return false;
    }
  }

  /**
   * Display available providers as chat message after discovery
   */
  displayAvailableProviders(configuredProviders) {
    try {
      console.log('The Gold Box: Displaying available providers:', configuredProviders);
      
      if (configuredProviders.length === 0) {
        // No providers configured
        const messageContent = `
          <div class="gold-box-info">
            <div class="gold-box-header">
              <strong>The Gold Box - Provider Status</strong>
              <div class="gold-box-timestamp">${new Date().toLocaleTimeString()}</div>
            </div>
            <div class="gold-box-content">
              <p><strong>No LLM providers configured</strong></p>
              <p>Please configure API keys in the backend to use AI features.</p>
              <p>Use the key manager to add providers like OpenAI, Anthropic, or others.</p>
            </div>
          </div>
        `;
        
        ChatMessage.create({
          user: game.user.id,
          content: messageContent,
          speaker: {
            alias: 'The Gold Box'
          }
        });
      } else {
        // Display configured providers
        const providerList = configuredProviders.map(provider => 
          `<li><strong>${provider.provider_name}</strong> (${provider.provider_id})</li>`
        ).join('');
        
        const messageContent = `
          <div class="gold-box-info">
            <div class="gold-box-header">
              <strong>The Gold Box - Available Providers</strong>
              <div class="gold-box-timestamp">${new Date().toLocaleTimeString()}</div>
            </div>
            <div class="gold-box-content">
              <p><strong>Found ${configuredProviders.length} configured LLM provider(s):</strong></p>
              <ul>${providerList}</ul>
              <p><em>Configure your desired provider in Gold Box settings.</em></p>
            </div>
          </div>
        `;
        
        ChatMessage.create({
          user: game.user.id,
          content: messageContent,
          speaker: {
            alias: 'The Gold Box'
          }
        });
      }
      
    } catch (error) {
      console.error('The Gold Box: Error displaying providers:', error);
    }
  }
}

// GoldBoxModule class extension for tearDown method
GoldBoxModule.prototype.tearDown = function() {
  console.log('The Gold Box module disabled');
};

// Create and register the module
const goldBox = new GoldBoxModule();

// Make module instance globally available for API class
if (typeof game !== 'undefined') {
  game.goldBox = goldBox;
}

// Initialize module when Foundry is ready
Hooks.once('init', () => {
  console.log('The Gold Box: Initializing module...');
  console.log('The Gold Box: game object available:', typeof game !== 'undefined');
  console.log('The Gold Box: game.settings available:', typeof game.settings !== 'undefined');
  
  if (typeof game !== 'undefined' && game.settings) {
    goldBox.init();
    console.log('The Gold Box: Module initialization complete');
  } else {
    console.error('The Gold Box: game or game.settings not available during init');
  }
});

// Clean up when module is disabled
Hooks.on('disableModule', (module) => {
  if (module === 'the-gold-box') {
    goldBox.tearDown();
  }
});
