/**
 * The Gold Box - AI-powered Foundry VTT Module
 * Main module entry point
 */

/**
 * API Communication Class for Backend Integration
 * Refactored: Now delegates all operations to BackendCommunicator
 */
class GoldBoxAPI {
  constructor() {
    // Delegate all backend communication to BackendCommunicator
    this.communicator = new BackendCommunicator();
    // Keep ConnectionManager for compatibility
    this.connectionManager = new ConnectionManager();
    // SettingsManager will be set from module
    this.settingsManager = null;
    // WebSocket client reference for compatibility
    this.webSocketClient = null;
  }

  /**
   * Set SettingsManager reference
   */
  setSettingsManager(settingsManager) {
    this.settingsManager = settingsManager;
    this.communicator.setSettingsManager(settingsManager);
  }

  /**
   * Initialize API (called after game is ready)
   */
  init() {
    if (typeof game !== 'undefined' && game.settings) {
      // Set up communicator with ConnectionManager
      this.communicator.setConnectionManager(this.connectionManager);
      this.connectionManager.setWebSocketClient = (client) => {
        this.webSocketClient = client;
        this.communicator.setWebSocketClient(client);
      };
      console.log('The Gold Box: API initialized with BackendCommunicator');
    } else {
      console.warn('The Gold Box: Game settings not available during API init');
    }
  }

  /**
   * Send message context to backend with timeout handling (delegated to communicator)
   */
  async sendMessageContext(messages, moduleInstance) {
    const timeout = this.settingsManager.getSetting('aiResponseTimeout', 60);
    
    try {
      // Delegate to BackendCommunicator with timeout and retry logic
      const response = await this.communicator.sendMessageContext(messages, timeout, 1);
      
      if (response.success) {
        // Display success response
        moduleInstance.uiManager.displayAIResponse(response.data.response, response.data);
      } else {
        // Display error response
        moduleInstance.uiManager.displayErrorResponse(response.error || 'Unknown error occurred');
      }
      
    } catch (error) {
      console.error('The Gold Box: Error processing AI turn:', error);
      moduleInstance.uiManager.displayErrorResponse(error.message);
    }
  }

  /**
   * Sync settings to backend admin endpoint (delegated to communicator)
   */
  async syncSettings(settings, adminPassword) {
    return this.communicator.syncSettings(settings, adminPassword);
  }

  /**
   * Get unified frontend settings using SettingsManager (delegated to communicator)
   */
  getUnifiedFrontendSettings() {
    return this.communicator.getUnifiedFrontendSettings();
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
    // Initialize UI Manager
    this.uiManager = new GoldBoxUIManager(this.settingsManager, this);
  }

  /**
   * Initialize module
   */
  async init() {
    console.log('The Gold Box module initialized');
    
    // Initialize UI Manager
    this.uiManager.init();
    
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
        // Use the communicator's baseUrl which is properly initialized
        const wsUrl = this.api.communicator.baseUrl || this.api.baseUrl;
        console.log('The Gold Box: Using WebSocket URL:', wsUrl);
        
        this.webSocketClient = new GoldBoxWebSocketClient(
          wsUrl,
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
    
    // Delegate to BackendCommunicator for real-time sync setup
    this.api.communicator.setupRealTimeSync(
      (message) => this.handleRealTimeSync(message),
      (message) => this.handleBatchSync(message)
    );
    
    console.log('The Gold Box: Real-time synchronization set up via BackendCommunicator');
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

    // Add click handler for discovery button (after SettingsManager has registered button)
    Hooks.on('renderSettingsConfig', (app, html, data) => {
      const $html = $(html);
      $html.find('#gold-box-discover-port').on('click', () => {
        this.manualPortDiscovery();
      });
    });

    // Hook to add chat button when sidebar tab is rendered
    Hooks.on('renderSidebarTab', (app, html, data) => {
      console.log('The Gold Box: renderSidebarTab hook fired for', app.options.id);
      if (app.options.id === 'chat') {
        this.uiManager.addChatButton(html);
      }
    });

    // Also try hooking to chat log render as backup
    Hooks.on('renderChatLog', (app, html, data) => {
      console.log('The Gold Box: renderChatLog hook fired');
      this.uiManager.addChatButton(html);
    });

    // Hook to update button when settings change
    Hooks.on('updateSettings', (settings) => {
      console.log('The Gold Box: Settings updated, updating chat button');
      this.uiManager.updateChatButtonText();
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
      this.uiManager.displayErrorResponse(error.message);
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
                this.uiManager.displayChatMessage(msgData);
                break;
                
              case 'dice-roll':
                // Display dice roll in Foundry chat
                this.uiManager.displayDiceRoll(msgData);
                break;
                
              case 'chat-card':
                // Display chat card in Foundry chat
                this.uiManager.displayChatCard(msgData);
                break;
                
              default:
                console.log('The Gold Box: Unknown message type in chat_response:', msgData.type);
                // Fallback: try to display as simple response
                if (typeof msgData.content === 'string') {
                  this.uiManager.displayAIResponse(msgData.content, message.data);
                }
            }
          } else if (message.data && message.data.response) {
            // Fallback for legacy format (simple string response)
            this.uiManager.displayAIResponse(message.data.response, message.data);
          }
          break;
          
        case 'error':
          // Handle error from WebSocket
          if (message.data && message.data.error) {
            this.uiManager.displayErrorResponse(message.data.error);
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
   * Handle WebSocket error
   */
  handleWebSocketError(error) {
    console.error('The Gold Box: WebSocket error:', error);
    
    // Show error notification to user
    this.uiManager.showErrorNotification('WebSocket connection error: ' + (error.message || error));
  }

  /**
   * Check backend connection and show instructions if needed (using BackendCommunicator)
   */
  async checkBackendAndShowInstructions() {
    try {
      // Initialize connection through BackendCommunicator
      await this.api.communicator.initialize();
      
      // Get connection info for status
      const connectionInfo = this.api.communicator.getConnectionInfo();
      
      if (connectionInfo.isConnected) {
        await game.settings.set('the-gold-box', 'backendStatus', 'connected');
        console.log('The Gold Box: Backend connected via BackendCommunicator:', connectionInfo);
        return;
      } else {
        // Show instructions if connection failed
        await game.settings.set('the-gold-box', 'backendStatus', 'disconnected');
        console.log('The Gold Box: Connection failed, Communicator state:', connectionInfo.state);
        this.uiManager.displayStartupInstructions();
      }
    } catch (error) {
      await game.settings.set('the-gold-box', 'backendStatus', 'error');
      console.error('The Gold Box: Error checking backend:', error);
      this.uiManager.displayStartupInstructions();
    }
  }

  /**
   * Enhanced manual port discovery using BackendCommunicator
   */
  async manualPortDiscovery() {
    // Use BackendCommunicator to initialize connection
    await this.api.communicator.initialize();
    
    // Get connection info for status
    const connectionInfo = this.api.communicator.getConnectionInfo();
    
    if (connectionInfo.isConnected) {
      // Test connection to get provider info
      const healthResult = await this.api.communicator.testConnection();
      
      if (healthResult.success && healthResult.data && healthResult.data.configured_providers) {
        this.uiManager.displayAvailableProviders(healthResult.data.configured_providers);
      }
      
      this.uiManager.showSuccessNotification('Backend connection verified!');
      return true;
    } else {
      // No backend found
      this.uiManager.showErrorNotification('No backend server found. Please start backend server.');
      return false;
    }
  }

  /**
   * Clean up when module is disabled
   */
  tearDown() {
    // Clean up UI Manager
    this.uiManager.tearDown();
    
    // Clean up WebSocket connection
    if (this.webSocketClient) {
      this.webSocketClient.disconnect();
      this.webSocketClient = null;
    }
    
    // Clean up message collector
    if (this.messageCollector) {
      this.messageCollector.stop();
      this.messageCollector = null;
    }
    
    console.log('The Gold Box module disabled');
  }
}

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
