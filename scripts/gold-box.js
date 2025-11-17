/**
 * The Gold Box - AI-powered Foundry VTT Module
 * Main module entry point
 */

/**
 * API Communication Class for Backend Integration
 */
class GoldBoxAPI {
  constructor() {
    this.baseUrl = game.settings.get('gold-box', 'backendUrl') || 'http://localhost:5001';
  }

  /**
   * Test connection to the backend
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
      const response = await fetch(`${this.baseUrl}/api/process`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
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
    
    // Auto-start backend if enabled
    await this.autoStartBackend();
    
    // Log that the module is ready
    console.log('The Gold Box is ready for AI adventures!');
  }

  /**
   * Auto-start backend if enabled
   */
  async autoStartBackend() {
    const autoStart = game.settings.get('gold-box', 'autoStartBackend');
    if (autoStart) {
      console.log('The Gold Box: Auto-starting backend...');
      await this.startBackend();
    }
  }

  /**
   * Start the backend server
   */
  async startBackend() {
    try {
      // Check if backend is already running
      const testResult = await this.api.testConnection();
      if (testResult.success) {
        await game.settings.set('gold-box', 'backendStatus', 'running');
        console.log('The Gold Box: Backend already running');
        return;
      }

      // Start backend using Node.js child process
      const { spawn } = require('child_process');
      
      // For Foundry VTT environment, we need to handle this differently
      // Since we can't use Node.js require directly in browser, 
      // we'll show a message instead
      ui.notifications.warn('Please start the backend manually: cd backend && source venv/bin/activate && python server.py');
      await game.settings.set('gold-box', 'backendStatus', 'manual');
      
    } catch (error) {
      console.error('The Gold Box: Error starting backend:', error);
      ui.notifications.error(`Failed to start backend: ${error.message}`);
    }
  }

  /**
   * Stop the backend server
   */
  async stopBackend() {
    try {
      await game.settings.set('gold-box', 'backendStatus', 'stopped');
      ui.notifications.info('Backend stopped. Please stop the Python process manually.');
      console.log('The Gold Box: Backend stop requested');
      
    } catch (error) {
      console.error('The Gold Box: Error stopping backend:', error);
      ui.notifications.error(`Failed to stop backend: ${error.message}`);
    }
  }

  /**
   * Register Foundry VTT hooks
   */
  registerHooks() {
    // Register the setting that we use in chat button and config
    game.settings.register('gold-box', 'moduleElementsName', {
      name: "Module Elements Name",
      scope: "world",
      config: false,
      type: String,
      default: "The Gold Box"
    });

    // Register backend URL setting
    game.settings.register('gold-box', 'backendUrl', {
      name: "Backend URL",
      scope: "world",
      config: false,
      type: String,
      default: "http://localhost:5001"
    });

    // Register backend auto-start setting
    game.settings.register('gold-box', 'autoStartBackend', {
      name: "Auto-start Backend",
      scope: "world",
      config: false,
      type: Boolean,
      default: true
    });

    // Register backend status setting
    game.settings.register('gold-box', 'backendStatus', {
      name: "Backend Status",
      scope: "world",
      config: false,
      type: String,
      default: "stopped"
    });

    // Register AI prompt setting
    game.settings.register('gold-box', 'aiPrompt', {
      name: "AI Prompt",
      scope: "world",
      config: false,
      type: String,
      default: ""
    });

    // Register AI role setting
    game.settings.register('gold-box', 'aiRole', {
      name: "AI Role",
      scope: "world",
      config: false,
      type: String,
      default: "dm"
    });

    // Register settings menu using ChatConsole pattern
    game.settings.registerMenu('gold-box', 'configMenu', {
      name: "The Gold Box Configuration",
      label: "Open Gold Box Config",
      hint: "Configure The Gold Box module settings",
      scope: "world",
      config: true,
      restricted: true,
      requiresReload: false,
      icon: "fas fa-robot",
      type: GoldBoxConfig
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
      
      const customName = game.settings.get('gold-box', 'moduleElementsName');
      let name = customName ? customName : 'The Gold Box';
      
      // Build button HTML
      const inner = `<i class="fas fa-robot"></i> ${name}`;
      
      // Use ChatConsole's proven approach for v13+
      if (game.release.generation >= 13) {
        // Create button using DOM manipulation for v13
        const button = document.createElement('button');
        button.id = id;
        button.type = 'button';
        button.innerHTML = inner;
        button.setAttribute('data-tooltip', 'The Gold Box');
        button.style.cssText = 'margin: 4px 0; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; border: none; padding: 8px 16px; border-radius: 4px; cursor: pointer;';
        
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
   * Handle "Take AI Turn" button click
   */
  async onTakeAITurn() {
    console.log('The Gold Box: AI turn requested');
    
    // Get the current prompt from settings
    const prompt = game.settings.get('gold-box', 'aiPrompt');
    
    if (!prompt || prompt.trim() === '') {
      ui.notifications.warn('Please configure an AI prompt in the Gold Box settings first!');
      return;
    }
    
    // Show loading notification
    const loadingId = ui.notifications.info('The Gold Box: Sending request to AI...');
    
    try {
      // Send prompt to backend
      console.log('The Gold Box: Sending prompt:', prompt);
      const result = await this.api.sendPrompt(prompt);
      
      if (result.success) {
        // Display the response in chat
        this.displayAIResponse(result.data.response, result.data);
        ui.notifications.info('The Gold Box: AI response received!');
      } else {
        throw new Error(result.error || 'Unknown error occurred');
      }
      
    } catch (error) {
      console.error('The Gold Box: Error processing AI turn:', error);
      ui.notifications.error(`The Gold Box Error: ${error.message}`);
      this.displayErrorResponse(error.message);
    } finally {
      // Clear loading notification
      if (loadingId) {
        ui.notifications.remove(loadingId);
      }
    }
  }

  /**
   * Display AI response in the chat
   */
  displayAIResponse(response, metadata) {
    const customName = game.settings.get('gold-box', 'moduleElementsName') || 'The Gold Box';
    const role = game.settings.get('gold-box', 'aiRole') || 'dm';
    
    const roleDisplay = {
      'dm': 'Dungeon Master',
      'dm_assistant': 'DM Assistant', 
      'player': 'Player'
    };
    
    const messageContent = `
      <div class="gold-box-response">
        <div class="gold-box-header">
          <strong><i class="fas fa-robot"></i> ${customName} - ${roleDisplay[role]}</strong>
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
    const customName = game.settings.get('gold-box', 'moduleElementsName') || 'The Gold Box';
    
    const messageContent = `
      <div class="gold-box-error">
        <div class="gold-box-header">
          <strong><i class="fas fa-exclamation-triangle"></i> ${customName} - Error</strong>
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
   * Show module information dialog
   */
  showModuleInfo() {
    const dialog = new Dialog({
      title: 'The Gold Box',
      content: `
        <h2>The Gold Box v0.1.12</h2>
        <p>An AI-powered Foundry VTT module for intelligent TTRPG assistance.</p>
        <p><strong>Status:</strong> Basic structure loaded - AI features coming soon!</p>
        <p><a href="https://github.com/ssjmarx/Gold-Box" target="_blank">GitHub Repository</a></p>
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

// Enhanced configuration handler for settings menu
class GoldBoxConfig extends foundry.applications.api.HandlebarsApplicationMixin(foundry.applications.api.ApplicationV2) {
  static get defaultOptions() {
    return foundry.utils.mergeObject(super.defaultOptions, {
      title: 'The Gold Box Configuration',
      id: 'gold-box-config',
      template: 'templates/gold-box-config.html',
      width: 500,
      height: 600
    });
  }

  getData() {
    return {
      moduleElementsName: game.settings.get('gold-box', 'moduleElementsName') || 'The Gold Box',
      backendUrl: game.settings.get('gold-box', 'backendUrl') || 'http://localhost:5001',
      aiPrompt: game.settings.get('gold-box', 'aiPrompt') || '',
      aiRole: game.settings.get('gold-box', 'aiRole') || 'dm',
      autoStartBackend: game.settings.get('gold-box', 'autoStartBackend') || true,
      backendStatus: game.settings.get('gold-box', 'backendStatus') || 'stopped'
    };
  }

  async _updateObject(event, formData) {
    // Update all settings
    await game.settings.set('gold-box', 'moduleElementsName', formData.moduleElementsName);
    await game.settings.set('gold-box', 'backendUrl', formData.backendUrl);
    await game.settings.set('gold-box', 'aiPrompt', formData.aiPrompt);
    await game.settings.set('gold-box', 'aiRole', formData.aiRole);
    
    // Update the API instance with new backend URL
    if (game.goldBox && game.goldBox.api) {
      game.goldBox.api = new GoldBoxAPI();
    }
    
    ui.notifications.info('The Gold Box settings updated!');
  }

  activateListeners(html) {
    super.activateListeners(html);
    
    // Add connection test button functionality
    const testButton = html.find('#test-connection')[0];
    if (testButton) {
      testButton.addEventListener('click', () => this.testConnection());
    }
    
    // Add backend start button functionality
    const startButton = html.find('#start-backend')[0];
    if (startButton) {
      startButton.addEventListener('click', () => this.startBackend());
    }
    
    // Add backend stop button functionality
    const stopButton = html.find('#stop-backend')[0];
    if (stopButton) {
      stopButton.addEventListener('click', () => this.stopBackend());
    }
    
    // Update backend status display on load
    this.updateBackendStatus();
  }

  async startBackend() {
    const statusDiv = document.getElementById('backend-status');
    const startButton = document.getElementById('start-backend');
    const stopButton = document.getElementById('stop-backend');
    
    if (!statusDiv || !startButton || !stopButton) return;
    
    // Show starting status
    statusDiv.className = 'gold-box-connection-status testing';
    statusDiv.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Starting backend...';
    startButton.disabled = true;
    stopButton.disabled = true;
    
    try {
      // Check if backend is already running
      const backendUrl = document.querySelector('input[name="backendUrl"]').value || 'http://localhost:5001';
      const testAPI = new GoldBoxAPI();
      testAPI.baseUrl = backendUrl;
      
      const testResult = await testAPI.testConnection();
      if (testResult.success) {
        await game.settings.set('gold-box', 'backendStatus', 'running');
        statusDiv.className = 'gold-box-connection-status success';
        statusDiv.innerHTML = `<i class="fas fa-check-circle"></i> Backend already running: ${testResult.data.service}`;
      } else {
        // Show manual start instructions
        await game.settings.set('gold-box', 'backendStatus', 'manual');
        statusDiv.className = 'gold-box-connection-status testing';
        statusDiv.innerHTML = '<i class="fas fa-info-circle"></i> Manual start required. See terminal for command.';
        
        // Show instruction dialog
        ui.notifications.warn('Please start the backend manually using the terminal commands shown in the notification.');
      }
      
    } catch (error) {
      statusDiv.className = 'gold-box-connection-status error';
      statusDiv.innerHTML = `<i class="fas fa-exclamation-circle"></i> Error: ${error.message}`;
    } finally {
      startButton.disabled = false;
      stopButton.disabled = false;
    }
  }

  async stopBackend() {
    const statusDiv = document.getElementById('backend-status');
    const startButton = document.getElementById('start-backend');
    const stopButton = document.getElementById('stop-backend');
    
    if (!statusDiv || !startButton || !stopButton) return;
    
    // Show stopping status
    statusDiv.className = 'gold-box-connection-status testing';
    statusDiv.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Stopping backend...';
    startButton.disabled = true;
    stopButton.disabled = true;
    
    try {
      await game.settings.set('gold-box', 'backendStatus', 'stopped');
      statusDiv.className = 'gold-box-connection-status testing';
      statusDiv.innerHTML = '<i class="fas fa-info-circle"></i> Please stop the Python process manually.';
      ui.notifications.info('Backend stop requested. Please stop the Python process manually.');
      
    } catch (error) {
      statusDiv.className = 'gold-box-connection-status error';
      statusDiv.innerHTML = `<i class="fas fa-exclamation-circle"></i> Error: ${error.message}`;
    } finally {
      startButton.disabled = false;
      stopButton.disabled = false;
    }
  }

  async updateBackendStatus() {
    const statusDiv = document.getElementById('backend-status');
    if (!statusDiv) return;
    
    const backendStatus = game.settings.get('gold-box', 'backendStatus') || 'stopped';
    
    switch (backendStatus) {
      case 'running':
        statusDiv.className = 'gold-box-connection-status success';
        statusDiv.innerHTML = '<i class="fas fa-check-circle"></i> Backend is running';
        break;
      case 'stopped':
        statusDiv.className = 'gold-box-connection-status error';
        statusDiv.innerHTML = '<i class="fas fa-stop-circle"></i> Backend is stopped';
        break;
      case 'manual':
        statusDiv.className = 'gold-box-connection-status testing';
        statusDiv.innerHTML = '<i class="fas fa-exclamation-triangle"></i> Manual start required';
        break;
      default:
        statusDiv.className = 'gold-box-connection-status testing';
        statusDiv.innerHTML = '<i class="fas fa-question-circle"></i> Backend status: Unknown';
    }
  }

  async testConnection() {
    const statusDiv = document.getElementById('connection-status');
    const testButton = document.getElementById('test-connection');
    
    if (!statusDiv || !testButton) return;
    
    // Show testing status
    statusDiv.className = 'gold-box-connection-status testing';
    statusDiv.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Testing connection...';
    testButton.disabled = true;
    
    try {
      // Get current backend URL from form
      const backendUrl = document.querySelector('input[name="backendUrl"]').value || 'http://localhost:5000';
      
      // Create a temporary API instance for testing
      const testAPI = new GoldBoxAPI();
      testAPI.baseUrl = backendUrl;
      
      const result = await testAPI.testConnection();
      
      if (result.success) {
        statusDiv.className = 'gold-box-connection-status success';
        statusDiv.innerHTML = `<i class="fas fa-check-circle"></i> Connected to ${result.data.service} v${result.data.version}`;
      } else {
        statusDiv.className = 'gold-box-connection-status error';
        statusDiv.innerHTML = `<i class="fas fa-exclamation-circle"></i> Connection failed: ${result.error}`;
      }
      
    } catch (error) {
      statusDiv.className = 'gold-box-connection-status error';
      statusDiv.innerHTML = `<i class="fas fa-exclamation-circle"></i> Connection failed: ${error.message}`;
    } finally {
      testButton.disabled = false;
    }
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
