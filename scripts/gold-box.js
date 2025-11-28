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
   * Sync settings to backend via admin API
   */
  async syncSettings(settings, adminPassword) {
    try {
      const headers = this.connectionManager.getSecurityHeaders();
      // CRITICAL FIX: Add adminPassword to headers
      if (adminPassword) {
        headers["X-Admin-Password"] = adminPassword;
        console.log("FINAL HTTP FIX: AdminPassword added to headers:", adminPassword ? "SUCCESS" : "FAILED");
      }
      
      const response = await fetch(`${this.connectionManager.baseUrl}/api/admin`, {
        method: 'POST',
        headers: headers,
        body: JSON.stringify({
          command: 'update_settings',
          settings: settings
        })
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || `HTTP ${response.status}: ${response.statusText}`);
      }

      const data = await response.json();
      return {
        success: true,
        data: data
      };
    } catch (error) {
      console.error('Gold Box API Connection Error:', error);
      return {
        success: false,
        error: error.message
      };
    }
  }

  /**
   * Test backend connection
   */
  async testConnection() {
    return await this.connectionManager.testConnection();
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
   * Send message context to backend with visual indicators and timeout handling
   */
  async sendMessageContextWithVisuals(messages, moduleInstance) {
    const button = document.getElementById('gold-box-launcher');
    const timeout = game.settings.get('gold-box', 'aiResponseTimeout') || 60;
    
    try {
      // Step 1: Disable button and show waiting state
      this.setButtonProcessingState(button, true);
      this.showProcessingIndicator();
      
      // Step 2: Send request with timeout and retry logic
      const response = await Promise.race([
        this.sendMessageContextWithRetry(messages),
        new Promise((_, reject) => setTimeout(() => reject(new Error('AI response timeout')), timeout * 1000))
      ]);
      
      // Step 3: Re-enable button and hide indicators
      this.setButtonProcessingState(button, false);
      this.hideProcessingIndicator();
      
      if (response.success) {
        // Display success response
        moduleInstance.displayAIResponse(response.data.response, response.data);
      } else {
        // Display error response
        moduleInstance.displayErrorResponse(response.error || 'Unknown error occurred');
      }
      
    } catch (error) {
      // Step 4: Ensure button is re-enabled on error
      this.setButtonProcessingState(button, false);
      this.hideProcessingIndicator();
      
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
    // CRITICAL FIX: Ensure API bridge reference is available
    if (!this.apiBridge && typeof game !== 'undefined' && game.goldBox && game.goldBox.apiBridge) {
      this.apiBridge = game.goldBox.apiBridge;
      console.log('API BRIDGE DEBUG: Set API bridge reference from module');
    // CRITICAL FIX: Ensure API bridge reference is available with retry
    if (!this.apiBridge && typeof game !== 'undefined' && game.goldBox && game.goldBox.apiBridge) {
      this.apiBridge = game.goldBox.apiBridge;
      console.log('API BRIDGE DEBUG: Set API bridge reference from module');
    } else if (!this.apiBridge) {
      console.warn('API BRIDGE DEBUG: API bridge not available, retrying in 1 second');
      setTimeout(() => {
        if (!this.apiBridge && typeof game !== 'undefined' && game.goldBox && game.goldBox.apiBridge) {
          this.apiBridge = game.goldBox.apiBridge;
          console.log('API BRIDGE DEBUG: Set API bridge reference from module (retry)');
        } else {
          console.warn('API BRIDGE DEBUG: API bridge still not available after retry');
        }
      }, 1000);
    }
    }
    try {
      const processingMode = game.settings.get('gold-box', 'chatProcessingMode') || 'simple';
      
      let endpoint;
      let requestData;
      
      // STEP 1: Sync settings to admin endpoint FIRST (Phase 2 fix)
      console.log('The Gold Box: Syncing settings to admin endpoint before chat request...');
      const settings = this.getUnifiedFrontendSettings();
      const adminPassword = settings['backend password'];
      
      if (adminPassword && adminPassword.trim()) {
        const syncResult = await this.syncSettings(settings, adminPassword);
        if (syncResult.success) {
          console.log('The Gold Box: ✅ Settings synced successfully to admin endpoint');
        } else {
          console.warn('The Gold Box: ⚠️ Settings sync failed:', syncResult.error);
        }
      } else {
        console.warn('The Gold Box: ⚠️ No backend password configured, skipping settings sync');
      }
      
      // STEP 2: Make chat request WITHOUT settings (use stored settings from backend)
      if (processingMode === 'api') {
        endpoint = '/api/api_chat';
        // Include client ID in request data if available
        const clientId = this.apiBridge ? this.apiBridge.getClientId() : null;
        console.log("API BRIDGE DEBUG: API bridge available:", !!this.apiBridge);
        console.log("API BRIDGE DEBUG: Client ID:", clientId);
        console.log("RELAY DEBUG: Final requestData being sent:", JSON.stringify(requestData, null, 2));
        console.log("API BRIDGE DEBUG: Full API bridge object:", this.apiBridge);
        console.log("API BRIDGE DEBUG: API bridge connection info:", this.apiBridge ? this.apiBridge.getConnectionInfo() : "No bridge");
        requestData = {
          // NO settings here - backend will use stored settings
          context_count: game.settings.get('gold-box', 'maxMessageContext') || 15,
          settings: clientId ? { 'relay client id': clientId } : null // Include client ID, allow null if not connected
        };
        console.log('The Gold Box: Using API mode with client ID:', clientId || 'not connected', '- settings from backend storage');
      } else {
        // Existing logic for other modes
        endpoint = processingMode === 'processed' ? '/api/process_chat' : '/api/simple_chat';
        requestData = {
          // NO settings here - backend will use stored settings
          messages: messages
        };
        console.log('The Gold Box: Using', processingMode, 'mode with endpoint:', endpoint, '- settings from backend storage');
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
   * Get unified frontend settings (delegate to module instance)
   */
  /**
   * Get unified frontend settings (direct implementation to avoid delegation issues)
   */
  getUnifiedFrontendSettings() {
    // Direct implementation to avoid delegation timing issues
    if (typeof game !== 'undefined' && game.settings) {
      console.log("SETTINGS DEBUG: Game and game.settings available");
      const settings = {
        'maximum message context': game.settings.get('gold-box', 'maxMessageContext') || 15,
        'chat processing mode': game.settings.get('gold-box', 'chatProcessingMode') || 'simple',
        'ai role': game.settings.get('gold-box', 'aiRole') || 'dm',
        'general llm provider': game.settings.get('gold-box', 'generalLlmProvider') || '',
        'general llm base url': game.settings.get('gold-box', 'generalLlmBaseUrl') || '',
        'general llm model': game.settings.get('gold-box', 'generalLlmModel') || '',
        'general llm version': game.settings.get('gold-box', 'generalLlmVersion') || 'v1',
        'general llm timeout': game.settings.get('gold-box', 'aiResponseTimeout') || 60,
        'general llm max retries': game.settings.get('gold-box', 'generalLlmMaxRetries') || 3,
        'general llm custom headers': game.settings.get('gold-box', 'generalLlmCustomHeaders') || '',
        'tactical llm provider': game.settings.get('gold-box', 'tacticalLlmProvider') || '',
        'tactical llm base url': game.settings.get('gold-box', 'tacticalLlmBaseUrl') || '',
        'tactical llm model': game.settings.get('gold-box', 'tacticalLlmModel') || '',
        'tactical llm version': game.settings.get('gold-box', 'tacticalLlmVersion') || 'v1',
        'tactical llm timeout': game.settings.get('gold-box', 'tacticalLlmTimeout') || 30,
        'tactical llm max retries': game.settings.get('gold-box', 'tacticalLlmMaxRetries') || 3,
        'tactical llm custom headers': game.settings.get('gold-box', 'tacticalLlmCustomHeaders') || '',
        'backend password': game.settings.get('gold-box', 'backendPassword') || ''
      };
      console.log("SETTINGS DEBUG: Retrieved settings count:", Object.keys(settings).length);
      console.log("SETTINGS DEBUG: Settings keys:", Object.keys(settings));
      return settings;
    } else {
      console.warn("SETTINGS DEBUG: Game or game.settings not available");
      return {};
    }
  }

  /**
   * Set button processing state with visual feedback
   */
  setButtonProcessingState(button, isProcessing) {
    if (!button) return;
    
    if (isProcessing) {
      button.disabled = true;
      button.innerHTML = '🤔 AI Thinking...';
      button.style.opacity = '0.6';
      button.style.cursor = 'not-allowed';
    } else {
      button.disabled = false;
      button.innerHTML = 'Take AI Turn';
      button.style.opacity = '1';
      button.style.cursor = 'pointer';
    }
  }

  /**
   * Show processing indicator
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
    indicator.innerHTML = '🧠 AI Processing...';
    
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
}

class GoldBoxModule {
  constructor() {
    this.hooks = [];
    this.api = new GoldBoxAPI();
    // APIBridge will be initialized later after it's loaded
    this.apiBridge = null;
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
    
    // Check backend connection automatically (delayed until world is ready)
    Hooks.once('ready', () => {
      // Initialize API bridge after game is ready
      this.initializeAPIBridge();
      this.checkBackendAndShowInstructions();
    });
    
    console.log('The Gold Box is ready for AI adventures!');
  }

  /**
   * Initialize API bridge connection
   */
  async initializeAPIBridge() {
    console.log('The Gold Box: Initializing API bridge...');
    
    // Check if APIBridge is available (loaded from api-bridge.js)
    if (typeof APIBridge !== 'undefined') {
      this.apiBridge = new APIBridge();
      const success = await this.apiBridge.initialize();
      // CRITICAL FIX: Share API bridge with global game object
      if (typeof game !== 'undefined') {
        game.goldBox = this;
        game.goldBox.apiBridge = this.apiBridge;
        console.log('API BRIDGE DEBUG: Shared API bridge with game.goldBox');
      }
      if (!success) {
        console.warn('The Gold Box: API bridge initialization failed (this is expected if user is not GM)');
      }
    } else {
      console.warn('The Gold Box: APIBridge class not available - Foundry REST API module may not be loaded');
      this.apiBridge = null;
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
    
    // Register backend status setting (display-only)
    game.settings.register('gold-box', 'backendStatus', {
      name: "Backend Status",
      hint: "Current status of backend server (automatically detected)",
      scope: "world",
      config: false, // Not editable by user
      type: String,
      default: "checking..."
    });

    // Register Backend Password setting (moved to top)
    try {
      game.settings.register('gold-box', 'backendPassword', {
        name: "Backend Password",
        hint: "Password for admin operations on backend server (used to sync settings)",
        scope: "world",
        config: true,
        type: String,
        default: ""
      });
      console.log('The Gold Box: Successfully registered backendPassword setting');
    } catch (error) {
      console.error('The Gold Box: Failed to register backendPassword setting:', error);
    }

    // Register Chat Processing Mode setting
    game.settings.register('gold-box', 'chatProcessingMode', {
      name: "Chat Processing Mode",
      hint: "Choose how AI processes chat messages",
      scope: "world",
      config: true,
      type: String,
      choices: {
        "simple": "Simple (existing /api/simple_chat)",
        "processed": "Processed (new /api/process_chat)",
        "api": "API (Foundry REST API - experimental)"
      },
      default: "simple"
    });

    // Register maximum message context setting
    game.settings.register('gold-box', 'maxMessageContext', {
      name: "Maximum Message Context",
      hint: "Number of recent chat messages to send to AI for context (default: 15)",
      scope: "world",
      config: true,
      type: Number,
      default: 15
    });

    // Register AI Response Timeout setting
    game.settings.register('gold-box', 'aiResponseTimeout', {
      name: "AI Response Timeout (seconds)",
      hint: "Maximum time to wait for AI response before re-enabling button (default: 60)",
      scope: "world",
      config: true,
      type: Number,
      default: 60
    });

    // Register AI role setting with dropdown
    game.settings.register('gold-box', 'aiRole', {
      name: "AI Role",
      hint: "What role AI should play in your game",
      scope: "world",
      config: true,
      type: String,
      choices: {
        "dm": "Dungeon Master",
        "dm_assistant": "DM Assistant",
        "player": "Player"
      },
      default: "dm"
    });

    // Register General LLM Provider setting
    game.settings.register('gold-box', 'generalLlmProvider', {
      name: "General LLM - Provider",
      hint: "Provider name for General LLM (e.g., openai, anthropic, opencode, custom-provider)",
      scope: "world",
      config: true,
      type: String,
      default: ""
    });

    // Register General LLM Base URL setting
    game.settings.register('gold-box', 'generalLlmBaseUrl', {
      name: "General LLM - Base URL",
      hint: "Base URL for General LLM provider (e.g., https://api.openai.com/v1, https://api.z.ai/api/coding/paas/v4)",
      scope: "world",
      config: true,
      type: String,
      default: ""
    });

    // Register General LLM Model setting
    game.settings.register('gold-box', 'generalLlmModel', {
      name: "General LLM - Model",
      hint: "Model name for General LLM (e.g., gpt-3.5-turbo, claude-3-5-sonnet-20241022, openai/glm-4.6)",
      scope: "world",
      config: true,
      type: String,
      default: ""
    });

    // Register General LLM Version setting
    game.settings.register('gold-box', 'generalLlmVersion', {
      name: "General LLM - API Version",
      hint: "API version for General LLM (e.g., v1, v2, custom)",
      scope: "world",
      config: true,
      type: String,
      default: "v1"
    });

    // Register General LLM Timeout setting
    game.settings.register('gold-box', 'generalLlmTimeout', {
      name: "General LLM - Timeout (seconds)",
      hint: "Request timeout for General LLM in seconds (default: 30)",
      scope: "world",
      config: true,
      type: Number,
      default: 30
    });

    // Register General LLM Max Retries setting
    game.settings.register('gold-box', 'generalLlmMaxRetries', {
      name: "General LLM - Max Retries",
      hint: "Maximum retry attempts for General LLM (default: 3)",
      scope: "world",
      config: true,
      type: Number,
      default: 3
    });

    // Register General LLM Custom Headers setting
    game.settings.register('gold-box', 'generalLlmCustomHeaders', {
      name: "General LLM - Custom Headers (JSON)",
      hint: "Custom headers for General LLM in JSON format (advanced)",
      scope: "world",
      config: true,
      type: String,
      default: ""
    });

    // Register Tactical LLM Provider setting
    game.settings.register('gold-box', 'tacticalLlmProvider', {
      name: "Tactical LLM - Provider",
      hint: "Provider name for Tactical LLM (placeholder for future implementation)",
      scope: "world",
      config: true,
      type: String,
      default: ""
    });

    // Register Tactical LLM Base URL setting
    game.settings.register('gold-box', 'tacticalLlmBaseUrl', {
      name: "Tactical LLM - Base URL",
      hint: "Base URL for Tactical LLM provider (placeholder for future implementation)",
      scope: "world",
      config: true,
      type: String,
      default: ""
    });

    // Register Tactical LLM Model setting
    game.settings.register('gold-box', 'tacticalLlmModel', {
      name: "Tactical LLM - Model",
      hint: "Model name for Tactical LLM (placeholder for future implementation)",
      scope: "world",
      config: true,
      type: String,
      default: ""
    });

    // Register Tactical LLM Version setting
    game.settings.register('gold-box', 'tacticalLlmVersion', {
      name: "Tactical LLM - API Version",
      hint: "API version for Tactical LLM (e.g., v1, v2, custom)",
      scope: "world",
      config: true,
      type: String,
      default: "v1"
    });

    // Register Tactical LLM Timeout setting
    game.settings.register('gold-box', 'tacticalLlmTimeout', {
      name: "Tactical LLM - Timeout (seconds)",
      hint: "Request timeout for Tactical LLM in seconds (default: 30)",
      scope: "world",
      config: true,
      type: Number,
      default: 30
    });

    // Register Tactical LLM Max Retries setting
    game.settings.register('gold-box', 'tacticalLlmMaxRetries', {
      name: "Tactical LLM - Max Retries",
      hint: "Maximum retry attempts for Tactical LLM (default: 3)",
      scope: "world",
      config: true,
      type: Number,
      default: 3
    });

    // Register Tactical LLM Custom Headers setting
    game.settings.register('gold-box', 'tacticalLlmCustomHeaders', {
      name: "Tactical LLM - Custom Headers (JSON)",
      hint: "Custom headers for Tactical LLM in JSON format (advanced)",
      scope: "world",
      config: true,
      type: String,
      default: ""
    });

    // Hook to add custom button to settings menu
    Hooks.on('renderSettingsConfig', (app, html, data) => {
      // Handle both jQuery and plain DOM objects
      const $html = $(html);
      
      // Find Gold Box settings section
      const goldBoxSettings = $html.find('.tab[data-tab="gold-box"]');
      if (goldBoxSettings.length > 0) {
        // Add discovery button after existing settings with unified gold styling and enhanced accessibility
        const buttonHtml = `
          <div class="form-group">
            <label></label>
            <div class="form-fields">
              <button type="button" id="gold-box-discover-port" class="gold-box-discover-btn" style="background: linear-gradient(135deg, #FFD700 0%, #FFA500 50%, #FF8C00 100%); color: #1a1a1a; border: none; padding: 8px 16px; border-radius: 4px; cursor: pointer; font-weight: 600; transition: all 0.2s ease; box-shadow: 0 1px 3px rgba(0,0,0,0.3), 0 2px 6px rgba(0,0,0,0.2);">
                Discover Backend
              </button>
              <p class="notes">Test backend connection and discover server if port changed</p>
            </div>
          </div>
        `;
        
        goldBoxSettings.append(buttonHtml);
        
        // Add click handler for discovery button
        $html.find('#gold-box-discover-port').on('click', () => {
          this.manualPortDiscovery();
        });
      }
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
  }

  /**
   * Add chat button to the chat sidebar using ChatConsole pattern
   */
  addChatButton(html) {
    console.log('The Gold Box: addChatButton called');
    
    try {
      const id = 'gold-box-launcher';
      
      // Check if button already exists to avoid duplicates
      if (document.getElementById(id)) {
        console.log('The Gold Box: Button already exists, skipping creation');
        return;
      }
      
      // Use hardcoded name since we removed moduleElementsName setting
      const name = 'The Gold Box';
      
      // Build button HTML with new name
      const inner = `Take AI Turn`;
      
      // Use ChatConsole's proven approach for v13+
      if (game.release.generation >= 13) {
        // Create button using DOM manipulation for v13
        const button = document.createElement('button');
        button.id = id;
        button.type = 'button';
        button.innerHTML = inner;
        button.setAttribute('data-tooltip', 'The Gold Box');
        button.style.cssText = 'margin: 4px 0; background: linear-gradient(135deg, #FFD700 0%, #FFA500 50%, #FF8C00 100%); color: #1a1a1a; border: none; padding: 8px 16px; border-radius: 4px; cursor: pointer; font-weight: 600; transition: all 0.2s ease; box-shadow: 0 1px 3px rgba(0,0,0,0.3), 0 2px 6px rgba(0,0,0,0.2);';
        
        button.addEventListener('click', () => {
          this.onTakeAITurn();
        });
        
        // Find chat form and prepend button - use more specific selector
        const chatForms = document.getElementsByClassName('chat-form');
        const chatForm = chatForms && chatForms.length > 0 ? chatForms[0] : null;
        
        if (chatForm) {
          chatForm.prepend(button);
          console.log('The Gold Box: Added chat button using v13 pattern');
        } else {
          console.error('The Gold Box: Could not find chat form');
          console.log('The Gold Box: Available chat-form elements:', chatForms);
        }
      } else {
        // Fallback for older versions using jQuery
        const $html = $(html);
        const $button = $(`<button id="${id}" data-tooltip="The Gold Box">${inner}</button>`);
        $button.click(() => {
          this.onTakeAITurn();
        });
        
        const chatControls = $html.find('#chat-controls');
        if (chatControls.length) {
          chatControls.after($button);
          console.log('The Gold Box: Added chat button using v12 pattern');
        } else {
          console.error('The Gold Box: Could not find chat controls');
        }
      }
    } catch (error) {
      console.error('The Gold Box: Error adding chat button:', error);
    }
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
   * Handle "Take AI Turn" button click with message context workflow
   */
  async onTakeAITurn() {
    console.log('The Gold Box: AI turn requested');
    
    // Use enhanced method with visual indicators
    await this.api.sendMessageContextWithVisuals(this.collectChatMessages(
      game.settings.get('gold-box', 'maxMessageContext') || 15
    ), this);
  }

  /**
   * Collect ALL frontend settings into unified object
   */
  /**
   * Get unified frontend settings (direct implementation to avoid delegation issues)
   */
  getUnifiedFrontendSettings() {
    // Direct implementation to avoid delegation timing issues
    if (typeof game !== 'undefined' && game.settings) {
      console.log("SETTINGS DEBUG: Game and game.settings available");
      const settings = {
        'maximum message context': game.settings.get('gold-box', 'maxMessageContext') || 15,
        'chat processing mode': game.settings.get('gold-box', 'chatProcessingMode') || 'simple',
        'ai role': game.settings.get('gold-box', 'aiRole') || 'dm',
        'general llm provider': game.settings.get('gold-box', 'generalLlmProvider') || '',
        'general llm base url': game.settings.get('gold-box', 'generalLlmBaseUrl') || '',
        'general llm model': game.settings.get('gold-box', 'generalLlmModel') || '',
        'general llm version': game.settings.get('gold-box', 'generalLlmVersion') || 'v1',
        'general llm timeout': game.settings.get('gold-box', 'aiResponseTimeout') || 60,
        'general llm max retries': game.settings.get('gold-box', 'generalLlmMaxRetries') || 3,
        'general llm custom headers': game.settings.get('gold-box', 'generalLlmCustomHeaders') || '',
        'tactical llm provider': game.settings.get('gold-box', 'tacticalLlmProvider') || '',
        'tactical llm base url': game.settings.get('gold-box', 'tacticalLlmBaseUrl') || '',
        'tactical llm model': game.settings.get('gold-box', 'tacticalLlmModel') || '',
        'tactical llm version': game.settings.get('gold-box', 'tacticalLlmVersion') || 'v1',
        'tactical llm timeout': game.settings.get('gold-box', 'tacticalLlmTimeout') || 30,
        'tactical llm max retries': game.settings.get('gold-box', 'tacticalLlmMaxRetries') || 3,
        'tactical llm custom headers': game.settings.get('gold-box', 'tacticalLlmCustomHeaders') || '',
        'backend password': game.settings.get('gold-box', 'backendPassword') || ''
      };
      console.log("SETTINGS DEBUG: Retrieved settings count:", Object.keys(settings).length);
      console.log("SETTINGS DEBUG: Settings keys:", Object.keys(settings));
      return settings;
    } else {
      console.warn("SETTINGS DEBUG: Game or game.settings not available");
      return {};
    }
  }

  /**
   * Display AI response in chat
   */
  displayAIResponse(response, metadata) {
    // Use hardcoded name since we removed moduleElementsName setting
    const customName = 'The Gold Box';
    const role = game.settings.get('gold-box', 'aiRole') || 'dm';
    
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
    
    if (metadata && metadata.relay_error) {
      // Error case when relay server transmission failed - show actual AI response
      messageContent = `
        <div class="gold-box-error">
          <div class="gold-box-header">
            <strong>⚠️ ${customName} - Relay Transmission Error</strong>
            <div class="gold-box-timestamp">${new Date().toLocaleTimeString()}</div>
          </div>
          <div class="gold-box-content">
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
            <strong>${customName} - ${roleDisplay[role] || 'AI Response'}</strong>
            <div class="gold-box-timestamp">${new Date().toLocaleTimeString()}</div>
          </div>
          <div class="gold-box-content">
            <div class="ai-response-content">${response}</div>
            ${metadata && metadata.provider_used ? `
              <div class="ai-metadata">
                <p><em>Processed using ${metadata.provider_used} - ${metadata.model_used} (${metadata.tokens_used} tokens)</em></p>
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
        ui.notifications.error('❌ No backend server found. Please start the backend server.');
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
        await game.settings.set('gold-box', 'backendStatus', 'connected');
        console.log('The Gold Box: Backend connected via ConnectionManager:', connectionInfo);
        return;
      } else {
        // Show instructions if connection failed
        await game.settings.set('gold-box', 'backendStatus', 'disconnected');
        console.log('The Gold Box: Connection failed, ConnectionManager state:', connectionInfo.state);
        this.displayStartupInstructions();
      }
    } catch (error) {
      await game.settings.set('gold-box', 'backendStatus', 'error');
      console.error('The Gold Box: Error checking backend:', error);
      this.displayStartupInstructions();
    }
  }

  /**
   * Enhanced manual port discovery using ConnectionManager
   */
  async manualPortDiscovery() {
    // Also reinitialize API bridge connection
    await this.initializeAPIBridge();
    
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
        ui.notifications.info('✅ Backend connection verified!');
      }
      return true;
    } else {
      // No backend found
      if (typeof ui !== 'undefined' && ui.notifications) {
        ui.notifications.error('❌ No backend server found. Please start the backend server.');
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
              <p><strong>✅ Found ${configuredProviders.length} configured LLM provider(s):</strong></p>
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
  if (module === 'gold-box') {
    goldBox.tearDown();
  }
});
