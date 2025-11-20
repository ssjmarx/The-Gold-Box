/**
 * The Gold Box - AI-powered Foundry VTT Module
 * Main module entry point
 */

/**
 * API Communication Class for Backend Integration
 */
class GoldBoxAPI {
  constructor() {
    // Initialize with default URL - settings will be applied later
    this.baseUrl = 'http://localhost:5000';
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
    
    console.warn(`The Gold Box: No backend found on ports ${startPort}-${startPort + maxAttempts - 1}`);
    return null;
  }

  /**
   * Auto-discover and update backend port
   * @returns {Promise<boolean>} - True if successful, false otherwise
   */
  async autoDiscoverAndUpdatePort() {
    try {
      const discoveredPort = await this.discoverBackendPort();
      
      if (discoveredPort) {
        const newUrl = `http://localhost:${discoveredPort}`;
        
        // Update the API URL
        this.baseUrl = newUrl;
        
        // Update status only (backendUrl setting was removed)
        if (typeof game !== 'undefined' && game.settings) {
          console.log(`The Gold Box: Updated backend URL to: ${newUrl}`);
          
          // Update status
          await game.settings.set('gold-box', 'backendStatus', 'connected');
          
        }
        
        return true;
      } else {
        // Update status to disconnected
        if (typeof game !== 'undefined' && game.settings) {
          await game.settings.set('gold-box', 'backendStatus', 'disconnected');
        }
        return false;
      }
    } catch (error) {
      console.error('The Gold Box: Error during port discovery:', error);
      if (typeof game !== 'undefined' && game.settings) {
        await game.settings.set('gold-box', 'backendStatus', 'error');
      }
      return false;
    }
  }

  /**
   * Test connection to backend
   */
  async testConnection() {
    try {
      const response = await fetch(`${this.baseUrl}/api/health`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json'
        }
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
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
   * Send prompt to backend for processing
   */
  async sendPrompt(prompt) {
    try {
      const headers = {
        'Content-Type': 'application/json'
      };
      
      const response = await fetch(`${this.baseUrl}/api/process`, {
        method: 'POST',
        headers: headers,
        body: JSON.stringify({ prompt: prompt })
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const data = await response.json();
      return {
        success: true,
        data: data
      };
    } catch (error) {
      console.error('Gold Box API Error:', error);
      throw error;
    }
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
   * @param {Object} settings - Settings object to sync
   * @param {string} adminPassword - Admin password for authentication
   * @returns {Promise<Object>} - Result of the sync operation
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
      console.error('Gold Box API Settings Sync Error:', error);
      return {
        success: false,
        error: error.message
      };
    }
  }
}

class GoldBoxModule {
  constructor() {
    this.hooks = [];
    this.api = new GoldBoxAPI();
  }

  /**
   * Initialize the module
   */
  async init() {
    console.log('The Gold Box module initialized');
    
    // Register hooks
    this.registerHooks();
    
    // Initialize API with game settings
    this.api.init();
    
    // Check backend connection automatically (delayed until world is ready)
    Hooks.once('ready', () => {
      this.checkBackendAndShowInstructions();
    });
    
    // Log that the module is ready
    console.log('The Gold Box is ready for AI adventures!');
  }

  /**
   * Check backend connection and show instructions if needed (health check only)
   */
  async checkBackendAndShowInstructions() {
    try {
      // Test connection to auto-discovered URL
      const testResult = await this.api.testConnection();
      if (testResult.success) {
        await game.settings.set('gold-box', 'backendStatus', 'connected');
        console.log('The Gold Box: Backend is running on auto-discovered URL:', this.api.baseUrl);
        return;
      }
      
      // If auto-discovery failed, try manual discovery
      console.log('The Gold Box: Auto-discovery failed, trying manual discovery...');
      const manualResult = await this.api.autoDiscoverAndUpdatePort();
      
      if (manualResult) {
        console.log('The Gold Box: Backend found at:', this.api.baseUrl);
      } else {
        // Show instructions if no backend found
        await game.settings.set('gold-box', 'backendStatus', 'disconnected');
        console.log('The Gold Box: No backend server found');
        this.displayStartupInstructions();
      }
    } catch (error) {
      await game.settings.set('gold-box', 'backendStatus', 'error');
      console.error('The Gold Box: Error checking backend:', error);
      this.displayStartupInstructions();
    }
  }

  /**
   * Register Foundry VTT hooks
   */
  registerHooks() {
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
    game.settings.register('gold-box', 'backendPassword', {
      name: "Backend Password",
      hint: "Password for admin operations on backend server (used to sync settings)",
      scope: "world",
      config: true,
      type: String,
      default: ""
    });

    // Register server debug prompt setting
    game.settings.register('gold-box', 'aiPrompt', {
      name: "Server Debug Prompt",
      hint: "The prompt that will be sent to the AI backend when you click the AI chat button",
      scope: "world",
      config: true,
      type: String,
      default: "Hello! This is a test prompt. Please respond with a friendly greeting and introduce yourself as an AI assistant for tabletop RPGs."
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

    // Register General LLM setting with dropdown
    game.settings.register('gold-box', 'generalLlm', {
      name: "General LLM",
      hint: "Select primary LLM service to use for AI processing",
      scope: "world",
      config: true,
      type: String,
      choices: {
        "openai_compatible": "OpenAI Compatible",
        "novelai_api": "NovelAI API", 
        "local": "Local"
      },
      default: "openai_compatible"
    });

    // Register OpenAI Compatible Base URL setting
    game.settings.register('gold-box', 'openaiBaseUrl', {
      name: "OpenAI Compatible - Base URL",
      hint: "Base URL for OpenAI-compatible API (e.g., https://api.openai.com/v1)",
      scope: "world",
      config: true,
      type: String,
      default: "https://api.openai.com/v1"
    });

    // Register OpenAI Compatible Model Name setting
    game.settings.register('gold-box', 'openaiModelName', {
      name: "OpenAI Compatible - Model Name", 
      hint: "Model name to use (e.g., gpt-3.5-turbo, gpt-4, etc.)",
      scope: "world",
      config: true,
      type: String,
      default: "gpt-3.5-turbo"
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

    // Hook when game is ready
    Hooks.once('ready', () => {
      console.log('The Gold Box: Game is ready');
    });

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
   * Handle "Take AI Turn" button click with sync-then-process workflow
   */
  async onTakeAITurn() {
    console.log('The Gold Box: AI turn requested');
    
    // Get current prompt from settings
    const prompt = game.settings.get('gold-box', 'aiPrompt');
    
    if (!prompt || prompt.trim() === '') {
      if (typeof ui !== 'undefined' && ui.notifications) {
        ui.notifications.warn('Please configure a server debug prompt in Gold Box settings first!');
      }
      return;
    }
    
    try {
      // Step 1: Sync current settings to backend first
      const backendPassword = game.settings.get('gold-box', 'backendPassword');
      
      if (!backendPassword || backendPassword.trim() === '') {
        if (typeof ui !== 'undefined' && ui.notifications) {
          ui.notifications.error('❌ Please configure a backend password in Gold Box settings first!');
        }
        return;
      }

      // Collect all current frontend settings
      const settingsToSync = {
        'server debug prompt': game.settings.get('gold-box', 'aiPrompt') || '',
        'ai role': game.settings.get('gold-box', 'aiRole') || 'dm',
        'general llm': game.settings.get('gold-box', 'generalLlm') || 'openai_compatible',
        'backend password': backendPassword
      };

      console.log('The Gold Box: Syncing settings before AI turn:', settingsToSync);
      const syncResult = await this.api.syncSettings(settingsToSync, backendPassword);
      
      if (!syncResult.success) {
        // Handle sync failure with smart error messages
        if (syncResult.error) {
          if (syncResult.error.includes('401') || syncResult.error.includes('authentication')) {
            ui.notifications.error('❌ Admin password incorrect. Please check your backend password in Gold Box settings.');
          } else if (syncResult.error.includes('404') || syncResult.error.includes('not found')) {
            ui.notifications.error('🚫 Backend server not responding. Please ensure backend server is running.');
          } else if (syncResult.error.includes('403')) {
            ui.notifications.error('🔒 Admin access denied. Check backend password configuration.');
          } else {
            ui.notifications.error('⚠️ Backend connection failed. Check server status and admin password.');
          }
        }
        return; // Stop here if sync failed
      }
      
      // Step 2: If sync succeeded, send prompt to AI
      console.log('The Gold Box: Settings synced, sending prompt:', prompt);
      const result = await this.api.sendPrompt(prompt);
      
      if (result.success) {
        // Display the response in chat
        this.displayAIResponse(result.data.response, result.data);
      } else {
        throw new Error(result.error || 'Unknown error occurred');
      }
      
    } catch (error) {
      console.error('The Gold Box: Error processing AI turn:', error);
      this.displayErrorResponse(error.message);
    }
  }

  /**
   * Display AI response in the chat
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
    
    // Chat message without robot emoji
    const messageContent = `
      <div class="gold-box-response">
        <div class="gold-box-header">
          <strong>${customName} - ${roleDisplay[role]}</strong>
          <div class="gold-box-timestamp">${new Date(metadata.timestamp).toLocaleTimeString()}</div>
        </div>
        <div class="gold-box-content">
          <p>${response}</p>
          ${metadata.message ? `<div class="gold-box-status">${metadata.message}</div>` : ''}
        </div>
      </div>
    `;
    
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
   * Display error response in the chat
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
   * Display startup instructions prominently in the chat
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
          <p><strong>Option 1: Run the automation script</strong></p>
          <p>Run <code>./start-backend.py</code> from the Gold Box module directory to automatically set up and start the backend server.</p>
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
   * Enhanced manual port discovery with health check and port scanning
   */
  async manualPortDiscovery() {
    try {
      // First: Try current saved URL
      console.log('The Gold Box: Testing current backend connection...');
      const healthResult = await this.api.testConnection();
      
      if (healthResult.success) {
        if (typeof ui !== 'undefined' && ui.notifications) {
          ui.notifications.info('✅ Backend connection verified!');
        }
        return true;
      }
      
      // Second: If current URL fails, scan for new port
      console.log('The Gold Box: Current connection failed, scanning for backend...');
      const discoveredPort = await this.api.discoverBackendPort();
      
      if (discoveredPort) {
        this.api.baseUrl = `http://localhost:${discoveredPort}`;
        if (typeof ui !== 'undefined' && ui.notifications) {
          ui.notifications.success(`🔍 Found backend on port ${discoveredPort}!`);
        }
        
        // Refresh settings to show updated URL
        if (game.settings && game.settings.menu) {
          game.settings.menu.render(true);
        }
        return true;
      }
      
      // Third: No backend found at all
      if (typeof ui !== 'undefined' && ui.notifications) {
        ui.notifications.error('❌ No backend server found. Please start the backend server.');
      }
      return false;
      
    } catch (error) {
      console.error('The Gold Box: Backend discovery failed:', error);
      if (typeof ui !== 'undefined' && ui.notifications) {
        ui.notifications.error(`🚫 Backend discovery failed - ${error.message}`);
      }
      return false;
    }
  }


  /**
   * Show module information dialog
   */
  showModuleInfo() {
    const dialog = new Dialog({
      title: 'The Gold Box',
      content: `
        <h2>The Gold Box v0.1.12</h2>
        <p>An AI-powered Foundry VTT module for intelligent TTRPG assistance.</p>
        <p><strong>Status:</strong> Basic structure loaded - AI features coming soon!</p>
        <p><a href="https://github.com/ssjmarx/gold-Box" target="_blank">GitHub Repository</a></p>
      `,
      buttons: {
        close: {
          label: 'Close',
          callback: () => {}
        }
      },
      default: 'close'
    });
    
    dialog.render(true);
  }
}

// GoldBoxModule class extension for tearDown method
GoldBoxModule.prototype.tearDown = function() {
  console.log('The Gold Box module disabled');
};

// Create and register the module
const goldBox = new GoldBoxModule();

// Initialize the module when Foundry is ready
Hooks.once('init', () => {
  game.goldBox = goldBox;
  goldBox.init();
});

// Clean up when the module is disabled
Hooks.on('disableModule', (module) => {
  if (module === 'gold-box') {
    goldBox.tearDown();
  }
});
