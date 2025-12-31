/**
 * The Gold Box - AI-powered Foundry VTT Module
 * Main module entry point
 */

/**
 * API Communication Class for Backend Integration
 * Refactored: Now uses unified WebSocketCommunicator
 */
class GoldBoxAPI {
  constructor(uiManager) {
    // UI Manager reference for button state management
    this.uiManager = uiManager;
    // Use unified WebSocket communicator
    this.communicator = new WebSocketCommunicator();
    // SettingsManager will be set from module
    this.settingsManager = null;
    // WebSocket client reference for compatibility
    this.webSocketClient = null;
    // Session manager reference
    this.sessionManager = null;
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
      // Set up session manager if available
      if (typeof SessionManager !== 'undefined') {
        this.sessionManager = new SessionManager();
        this.communicator.setSessionManager(this.sessionManager);
      }
      
      console.log('The Gold Box: API initialized with WebSocketCommunicator');
    } else {
      console.warn('The Gold Box: Game settings not available during API init');
    }
  }

  /**
   * Send message context to backend with timeout handling (WebSocket-only)
   */
  async sendMessageContext(messages, moduleInstance, buttonElement, testMode = null) {
    const timeout = this.settingsManager.getSetting('aiResponseTimeout', 60);
    let response = null; // Define response outside try block so it's accessible in finally
    
    try {
      // Use WebSocket-only communication with proper context count
      const maxMessages = 15;  // Use default of 15
      
      // Build options
      const options = {
        timeout: timeout,
        contextCount: maxMessages
      };
      
      // Add test mode if active
      if (testMode && testMode.active) {
        options.test = true;
        options.testSessionId = testMode.testSessionId;
        options.aiRole = testMode.aiRole;
        console.log('The Gold Box: Sending chat request with test mode:', options);
      }
      
      response = await this.communicator.sendChatRequest(messages, options);
      
      if (response.success) {
        // WebSocket mode - response comes via WebSocket message handler
        console.log('The Gold Box: WebSocket request sent, waiting for async response via WebSocket handler');
        return; // Don't reset button yet - wait for WebSocket response
      } else {
        // Display error response
        moduleInstance.uiManager.displayErrorResponse(response.error || 'Unknown error occurred');
        // Reset button on error
        if (buttonElement) {
          this.setButtonProcessingState(buttonElement, false);
        }
      }
      
    } catch (error) {
      console.error('The Gold Box: Error processing AI turn:', error);
      moduleInstance.uiManager.displayErrorResponse(error.message);
      // Reset button on error
      if (buttonElement) {
        this.setButtonProcessingState(buttonElement, false);
      }
    }
  }

  /**
   * Get unified frontend settings using SettingsManager
   */
  getUnifiedFrontendSettings() {
    return this.settingsManager ? this.settingsManager.getAllSettings() : {};
  }

  /**
   * Set button processing state with visual feedback
   */
  setButtonProcessingState(button, isProcessing) {
    if (!button) return;
    
    if (isProcessing) {
      button.disabled = true;
      button.innerHTML = 'AI Thinking...';
      button.style.opacity = '0.6';
      button.style.cursor = 'not-allowed';
    } else {
      button.disabled = false;
      button.innerHTML = this.settingsManager ? this.settingsManager.getButtonText() : 'Take AI Turn';
      button.style.opacity = '1';
      button.style.cursor = 'pointer';
      
      // Reset delta counters when AI turn completes
      window.FrontendDeltaService?.resetDeltaCounts();
    }
  }

  /**
   * Unified cleanup handler for turn completion
   * Handles both button state reset and delta counter reset
   * Called when AI turn completes or test session ends
   */
  handleTurnCompletion() {
    console.log('The Gold Box: ===== TURN COMPLETION DIAGNOSTICS =====');
    console.log('The Gold Box: handleTurnCompletion called');
    console.log('The Gold Box: uiManager exists:', !!this.uiManager);
    console.log('The Gold Box: aiTurnButtonHandler exists:', !!(this.uiManager && this.uiManager.aiTurnButtonHandler));
    console.log('The Gold Box: FrontendDeltaService exists:', !!window.FrontendDeltaService);
    
    // Reset button state via state machine
    if (this.uiManager && this.uiManager.aiTurnButtonHandler) {
      console.log('The Gold Box: Calling onAITurnEnded on button handler');
      this.uiManager.aiTurnButtonHandler.onAITurnEnded();
    } else {
      console.error('The Gold Box: Cannot reset button - handler not available');
    }
    
    // Reset delta counters
    if (window.FrontendDeltaService) {
      console.log('The Gold Box: Resetting delta counters');
      window.FrontendDeltaService.resetDeltaCounts();
    } else {
      console.warn('The Gold Box: FrontendDeltaService not available');
    }
    
    console.log('The Gold Box: Turn completion handled successfully');
    console.log('The Gold Box: ===== END TURN COMPLETION DIAGNOSTICS =====');
  }
}

class GoldBoxModule {
  constructor() {
    this.hooks = [];
    // Initialize Settings Manager
    this.settingsManager = new SettingsManager();
    // Initialize UI Manager
    this.uiManager = new GoldBoxUIManager(this.settingsManager, this);
    // Initialize API with UI Manager reference
    this.api = new GoldBoxAPI(this.uiManager);
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
    
    // Set button to disconnected state initially
    this.uiManager.aiTurnButtonHandler.onWebSocketDisconnected();
    
    // Check if WebSocket client is available
    if (typeof GoldBoxWebSocketClient !== 'undefined') {
      try {
        // Use communicator's baseUrl which is properly initialized
        const baseUrl = this.api.communicator.baseUrl || this.api.baseUrl;
        const wsUrl = baseUrl.replace('http://', 'ws://').replace('https://', 'wss://');
        console.log('The Gold Box: Using WebSocket URL:', wsUrl);
        
        this.webSocketClient = new GoldBoxWebSocketClient(
          wsUrl,
          (message) => this.handleWebSocketMessage(message),
          (error) => this.handleWebSocketError(error),
          () => this.uiManager.aiTurnButtonHandler.onWebSocketConnected(),  // onConnected callback
          () => this.uiManager.aiTurnButtonHandler.onWebSocketDisconnected() // onDisconnected callback
        );

        // Initialize message collector
        if (typeof MessageCollector !== 'undefined') {
          this.messageCollector = new MessageCollector();
          // Set SettingsManager reference in message collector
          this.messageCollector.setSettingsManager(this.settingsManager);
          // Set WebSocket client reference in message collector
          if (this.webSocketClient) {
            this.messageCollector.webSocketClient = this.webSocketClient;
          }
        
          // Enable message collector for WebSocket communication
          this.messageCollector.isEnabled = true;
          console.log('The Gold Box: Message collector initialized and enabled');
        }

        // Connect to WebSocket server
        const connected = await this.webSocketClient.connect();
        
        if (connected) {
          console.log('The Gold Box: WebSocket connection established successfully');
          
          // Wait for connection to be fully established
          await this.webSocketClient.waitForConnection(5000);
          
          // Store WebSocket client reference in API for message collection
          this.api.webSocketClient = this.webSocketClient;
          
          // Register WebSocket handlers for Combat Monitor
          if (window.CombatMonitor && typeof window.CombatMonitor.registerWebSocketHandlers === 'function') {
            const handlersRegistered = window.CombatMonitor.registerWebSocketHandlers();
            if (handlersRegistered) {
              console.log('The Gold Box: Combat Monitor handlers registered successfully');
            } else {
              console.warn('The Gold Box: Combat Monitor handler registration returned false');
            }
          } else {
            console.warn('The Gold Box: Combat Monitor or registerWebSocketHandlers not available');
          }
          
          // Set button to connected state
          this.uiManager.aiTurnButtonHandler.onWebSocketConnected();
          
          console.log('The Gold Box: WebSocket connection ready');
          console.log('The Gold Box: WebSocket client details:', this.webSocketClient.getConnectionStatus());
          return true;
        } else {
          console.warn('The Gold Box: WebSocket connection failed');
          this.webSocketClient = null;
          if (this.messageCollector) {
            this.messageCollector.stop();
          }
          // Explicitly keep button in DISCONNECTED state on failed connection
          setTimeout(() => {
            this.uiManager.aiTurnButtonHandler.onWebSocketDisconnected();
          }, 100);
          return false;
        }
        
      } catch (error) {
        console.error('The Gold Box: WebSocket connection error:', error);
        this.webSocketClient = null;
        if (this.messageCollector) {
          this.messageCollector.stop();
        }
        // Explicitly keep button in DISCONNECTED state on connection error
        setTimeout(() => {
          this.uiManager.aiTurnButtonHandler.onWebSocketDisconnected();
        }, 100);
        return false;
      }
    } else {
      console.warn('The Gold Box: GoldBoxWebSocketClient class not available - WebSocket client module may not be loaded');
      this.webSocketClient = null;
      // Explicitly keep button in DISCONNECTED state when class not available
      setTimeout(() => {
        this.uiManager.aiTurnButtonHandler.onWebSocketDisconnected();
      }, 100);
      return false;
    }
  }

  /**
   * Initialize with WebSocket Communicator
   */
  async initializeWithConnectionManager() {
    console.log('The Gold Box: Initializing with WebSocket Communicator...');
    
    // Set button to DISCONNECTED state BEFORE any connection attempt
    // This ensures button is correct state regardless of success/failure
    this.uiManager.aiTurnButtonHandler.onWebSocketDisconnected();
    
    try {
      // Step 1: Initialize WebSocket Communicator
      await this.api.communicator.initialize();
      console.log('The Gold Box: WebSocket Communicator initialized');
      
      // Step 2: Try WebSocket connection first
      const wsConnected = await this.initializeWebSocketConnection();
      
      if (wsConnected) {
        console.log('The Gold Box: WebSocket connection established');
        
        // Step 3: Set WebSocket client in communicator
        await this.api.communicator.setWebSocketClient(this.webSocketClient);
        
        // Step 4: Set up real-time data synchronization
        this.setupRealTimeSync();
        
        console.log('The Gold Box: Initialization complete - WebSocket connected');
        return true;
      } else {
        console.log('The Gold Box: WebSocket connection failed');
        console.log('The Gold Box: Initialization complete - no WebSocket connection');
        return false;
      }
      
    } catch (error) {
      console.error('The Gold Box: Initialization failed:', error);
      console.log('The Gold Box: Initialization complete - error state');
      // Button already set to DISCONNECTED at start of method
      return false;
    }
  }

  /**
   * Set up real-time data synchronization
   */
  setupRealTimeSync() {
    if (!this.webSocketClient || !this.api.communicator) {
      console.warn('The Gold Box: Cannot set up real-time sync - missing components');
      return;
    }
    
    // Set up real-time sync handlers
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
    
    // Register hook for subtitle override (Phase 4.3)
    Hooks.on('renderChatMessageHTML', (chatMessage, html, data) => {
      // Only modify messages from The Gold Box AI
      if (chatMessage.flags?.['gold-box']?.isAIMessage) {
        // Find subtitle element in name-stacked structure
        const nameStacked = html.querySelector('.name-stacked');
        if (nameStacked) {
          const subtitle = nameStacked.querySelector('.subtitle');
          if (subtitle) {
            subtitle.textContent = 'The Gold Box AI';
          }
        }
      }
    });

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
   * Handle "Take AI Turn" button click
   */
  async onTakeAITurn() {
    console.log('The Gold Box: Take AI Turn button clicked');
    
    const button = document.getElementById('gold-box-ai-turn-btn');
    if (!button) {
      console.error('The Gold Box: Button not found');
      return;
    }
    
    // Set processing state using state machine
    this.uiManager.aiTurnButtonHandler.onAITurnStarted();
    
    try {
      // WebSocket-only: collect messages from Foundry chat and send via WebSocket
      const messages = this.collectFoundryChatMessages();
      console.log('The Gold Box: Collected messages from Foundry chat:', messages.length);
      
      // ADD COMBAT CONTEXT: Check if CombatMonitor is available and get FRESH combat state
      let combatContext = null;
      if (window.CombatMonitor) {
        // Force refresh combat state to get current turn information
        combatContext = window.CombatMonitor.getCombatStateForBackend(true);  // true = force refresh
        console.log('The Gold Box: Combat context retrieved:', combatContext);
        
        // Add combat context as a special message type if combat is active
        if (combatContext && combatContext.in_combat) {
          messages.push({
            type: 'combat_context',
            combat_context: combatContext
          });
          console.log('The Gold Box: Added combat context to messages (in_combat:', combatContext.in_combat, ', combatants:', combatContext.combatants?.length || 0, ')');
        }
      } else {
        console.warn('The Gold Box: CombatMonitor not available - no combat context will be sent');
      }
      
      // ADD TEST MODE: Check if we're in test mode
      let testMode = null;
      if (this.testMode && this.testMode.active) {
        testMode = {
          active: true,
          testSessionId: this.testMode.testSessionId,
          aiRole: this.testMode.aiRole
        };
        console.log('The Gold Box: Test mode active:', testMode);
      }
      
      // Send to backend for processing (pass button element for proper state management)
      await this.api.sendMessageContext(messages, this, button, testMode);
      
    } catch (error) {
      console.error('The Gold Box: Error in AI turn:', error);
      this.uiManager.displayErrorResponse(error.message);
      // Reset button on error
      if (button) {
        this.api.setButtonProcessingState(button, false);
      }
    }
  }

  /**
   * Collect recent chat messages from Foundry chat DOM (fallback method)
   * This is now only used for testing/demo purposes
   * Real message collection happens via WebSocket
   */
  collectFoundryChatMessages(maxMessages = null) {
    // Use default if no explicit maxMessages provided
    if (maxMessages === null) {
      maxMessages = 15; // Default value
      console.log('The Gold Box: Using default maxMessages:', maxMessages);
    } else {
      console.log('The Gold Box: Using provided maxMessages:', maxMessages);
    }
    
    console.log('The Gold Box: Final maxMessages value:', maxMessages);
    const messages = [];
    const chatElements = document.querySelectorAll('.chat-message');
    
    // Get LAST maxMessages elements (most recent messages - bottom of chat)
    const recentElements = Array.from(chatElements).slice(-maxMessages);
    
    recentElements.forEach(element => {
      // Extract COMPLETE HTML element including all structure for dice rolls, cards, etc.
      // This preserves Foundry's rich HTML structure for backend processing
      const fullHtml = element.outerHTML.trim();
      
      // Enhanced metadata extraction - get actual message ID first
      const messageId = element.dataset.messageId || element.getAttribute('data-message-id');
      let timestamp;
      
      // Try to get actual Foundry message object for proper timestamp
      if (messageId && game.messages) {
        const foundryMessage = game.messages.get(messageId);
        if (foundryMessage && foundryMessage.timestamp) {
          timestamp = foundryMessage.timestamp;
        } else {
          // Fallback to timestamp element if message object not found
          const timestampElement = element.querySelector('.message-timestamp');
          timestamp = timestampElement ? this._parseFoundryTimestamp(timestampElement.textContent) : Date.now();
        }
      } else {
        // Fallback to timestamp element
        const timestampElement = element.querySelector('.message-timestamp');
        timestamp = timestampElement ? this._parseFoundryTimestamp(timestampElement.textContent) : Date.now();
      }
      
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
   * Handle WebSocket message from server
   */
  handleWebSocketMessage(message) {
    try {
      console.log('The Gold Box: Received WebSocket message:', message);
      
      switch (message.type) {
        case 'chat_response':
          // Handle AI response from WebSocket - NEW: support structured message data
          // NOTE: Do NOT reset button here - wait for ai_turn_complete message
          console.log('The Gold Box: Received chat_response (not resetting button yet)');
          
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
          
        case 'ai_turn_complete':
          console.log('The Gold Box: ===== AI_TURN_COMPLETE MESSAGE RECEIVED =====');
          console.log('The Gold Box: Received ai_turn_complete message from server');
          console.log('The Gold Box: Message data:', JSON.stringify(message.data));
          
          // Use unified cleanup handler for turn completion
          // This is the ONLY place where we reset the button state
          this.api.handleTurnCompletion();
          console.log('The Gold Box: Turn completion handled via WebSocket ai_turn_complete message');
          
          if (message.data && message.data.test_mode) {
            console.log('The Gold Box: Test mode turn completed');
          }
          
          console.log('The Gold Box: ===== END AI_TURN_COMPLETE MESSAGE =====');
          break;
          
        case 'error':
          // Reset button state on error as well
          this.uiManager.aiTurnButtonHandler.onAITurnError(message.data);
          console.log('The Gold Box: Reset button state after WebSocket error received');
          
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
      // Reset button state on error in message handling as well
      this.uiManager.aiTurnButtonHandler.onAITurnError(error);
      console.log('The Gold Box: Reset button state after message handling error');
    }
  }

  /**
   * Handle WebSocket error
   */
  handleWebSocketError(error) {
    console.error('The Gold Box: WebSocket error:', error);
    
    // Check if it's an authentication error with user-friendly message
    if (error && error.includes && error.includes('Please set your backend server password')) {
      // Display as permanent notification since user needs to take action
      this.uiManager.showErrorNotification(error);
    } else {
      // Show generic error notification for other errors
      this.uiManager.showErrorNotification('WebSocket connection error: ' + (error.message || error));
    }
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
   * Parse Foundry's human-readable timestamps to milliseconds
   * Handles formats like "now", "1s ago", "2m ago", "1h ago", "20d 4h ago"
   */
  _parseFoundryTimestamp(timeString) {
    if (!timeString || typeof timeString !== 'string') {
      return Date.now();
    }
    
    const now = Date.now();
    
    // Handle "now"
    if (timeString === 'now') {
      return now;
    }
    
    // Parse relative time formats
    const timePattern = /(?:^(\d+)([smhd])\s+ago)?(?:\s+(\d+)([smhd])\s+ago)?/i;
    const matches = timeString.match(timePattern);
    
    if (!matches) {
      // Fallback: try to parse as ISO date or other format
      const parsed = new Date(timeString);
      return isNaN(parsed.getTime()) ? now : parsed.getTime();
    }
    
    let totalMs = 0;
    
    // Parse first time unit (e.g., "20d" in "20d 4h ago")
    if (matches[1] && matches[2]) {
      const value1 = parseInt(matches[1]);
      const unit1 = matches[2].toLowerCase();
      totalMs += this._timeUnitToMs(value1, unit1);
    }
    
    // Parse second time unit (e.g., "4h" in "20d 4h ago")
    if (matches[3] && matches[4]) {
      const value2 = parseInt(matches[3]);
      const unit2 = matches[4].toLowerCase();
      totalMs += this._timeUnitToMs(value2, unit2);
    }
    
    return now - totalMs;
  }

  /**
   * Convert time unit to milliseconds
   */
  _timeUnitToMs(value, unit) {
    const multipliers = {
      's': 1000,           // seconds
      'm': 60 * 1000,      // minutes
      'h': 60 * 60 * 1000, // hours
      'd': 24 * 60 * 60 * 1000 // days
    };
    
    return value * (multipliers[unit] || 0);
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

// Create and register module
const goldBox = new GoldBoxModule();

// Make module instance globally available for API class
// Set on both window and game for maximum compatibility
window.goldBox = goldBox;
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

// Initialize combat monitoring and whisper display when ready - with delay for module loading
Hooks.once('ready', () => {
  console.log('The Gold Box: Initializing combat monitoring and whisper display...');  
  
  // Add small delay to allow all modules to load
  setTimeout(() => {
    // Combat Monitor will auto-initialize from combat-monitor.js
    // Whisper Display Manager will auto-initialize from whisper-display.js
  
    // Set up integration between components
    if (window.CombatMonitor && window.WhisperDisplayManager) {
      console.log('The Gold Box: Combat Monitor and Whisper Display Manager initialized');
      
      // Set up real-time combat thinking updates
      Hooks.on('combatTurn', (combat, turn, combatant) => {
        console.log('The Gold Box: Combat turn detected, thinking updates may follow');
      });
    } else {
      console.warn('The Gold Box: Combat Monitor or Whisper Display Manager not available');
    }
  }, 500); // 500ms delay to allow modules to load
});

// Clean up when module is disabled
Hooks.on('disableModule', (module) => {
  if (module === 'the-gold-box') {
    goldBox.tearDown();
  }
});
