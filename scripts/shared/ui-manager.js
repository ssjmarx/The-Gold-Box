/**
 * The Gold Box - UI Management Module
 * Handles all UI-related functionality including chat buttons, message display, and user interactions
 */

/**
 * AI Turn Button Handler with State Machine
 */
class AITurnButtonHandler {
  constructor(uiManager, moduleInstance) {
    this.uiManager = uiManager;
    this.moduleInstance = moduleInstance;
    this.state = 'DISCONNECTED'; // States: DISCONNECTED, CONNECTED, THINKING, PAUSED
    this.button = null;
    this.ellipsisIndex = 0;
    this.ellipsisInterval = null;
    this.pausedTimeout = null; // 30-second timeout for resume
    this.pausedAt = null; // Track when pause started
  }
  
  // State transitions
  setState(newState) {
    const oldState = this.state;
    this.state = newState;
    console.log(`AI Turn Button: ${oldState} -> ${newState}`);
    this.updateButton();
  }
  
  // Update button appearance based on state
  updateButton() {
    if (!this.button) {
      this.button = $('#gold-box-ai-turn-btn');
    }
    
    if (!this.button.length) return;
    
    switch (this.state) {
      case 'DISCONNECTED':
        this.setDisconnectedState();
        break;
      case 'CONNECTED':
        this.setConnectedState();
        break;
      case 'THINKING':
        this.setThinkingState();
        break;
      case 'PAUSED':
        this.setPausedState();
        break;
    }
  }
  
  setDisconnectedState() {
    this.button.css({
      'background': '#808080',
      'color': '#ffffff',
      'opacity': '0.5',
      'cursor': 'not-allowed'
    });
    this.button.text('Not Connected');
    this.button.prop('disabled', true);
    this.stopEllipsisAnimation();
    this.clearPausedTimeout();
  }
  
  setConnectedState() {
    this.button.css({
      'background': 'linear-gradient(135deg, #FFD700 0%, #FFA500 50%, #FF8C00 100%)',
      'color': '#1a1a1a',
      'opacity': '1',
      'cursor': 'pointer'
    });
    this.button.text('Take AI Turn');
    this.button.prop('disabled', false);
    this.stopEllipsisAnimation();
    this.clearPausedTimeout();
  }
  
  setThinkingState() {
    this.button.css({
      'background': 'linear-gradient(135deg, #FFD700 0%, #FFA500 50%, #FF8C00 100%)',
      'color': '#1a1a1a',
      'opacity': '0.5',
      'cursor': 'not-allowed'
    });
    this.button.prop('disabled', true);
    this.startEllipsisAnimation();
    this.clearPausedTimeout();
  }
  
  setPausedState() {
    this.button.css({
      'background': 'linear-gradient(135deg, #FFA500 0%, #FF8C00 50%, #FF6347 100%)',
      'color': '#ffffff',
      'opacity': '1',
      'cursor': 'pointer'
    });
    this.button.text('Resume AI Turn');
    this.button.prop('disabled', false);
    this.stopEllipsisAnimation();
    
    // Start 30-second timeout
    this.clearPausedTimeout();
    this.pausedAt = Date.now();
    this.pausedTimeout = setTimeout(() => {
      this.onPausedTimeout();
    }, 30000); // 30 seconds
  }
  
  startEllipsisAnimation() {
    this.stopEllipsisAnimation();
    this.ellipsisIndex = 0;
    this.updateEllipsis();
    this.ellipsisInterval = setInterval(() => {
      this.updateEllipsis();
    }, 500);
  }
  
  updateEllipsis() {
    const ellipsis = '.'.repeat((this.ellipsisIndex % 3) + 1);
    this.button.text('Thinking' + ellipsis);
    this.ellipsisIndex++;
  }
  
  stopEllipsisAnimation() {
    if (this.ellipsisInterval) {
      clearInterval(this.ellipsisInterval);
      this.ellipsisInterval = null;
    }
  }
  
  clearPausedTimeout() {
    if (this.pausedTimeout) {
      clearTimeout(this.pausedTimeout);
      this.pausedTimeout = null;
    }
    this.pausedAt = null;
  }
  
  // Event handlers
  onWebSocketConnected() {
    this.setState('CONNECTED');
  }
  
  onWebSocketDisconnected() {
    this.setState('DISCONNECTED');
  }
  
  onAITurnStarted() {
    this.setState('THINKING');
  }
  
  onAITurnEnded() {
    this.setState('CONNECTED');
  }
  
  onAITurnPaused() {
    this.setState('PAUSED');
  }
  
  onResumeAITurn() {
    this.setState('THINKING');
  }
  
  onPausedTimeout() {
    console.log('AI Turn: Paused state expired after 30 seconds');
    this.clearPausedTimeout();
    this.setState('CONNECTED');
  }
  
  onAITurnError(error) {
    console.error('AI Turn error:', error);
    this.clearPausedTimeout();
    this.setState('CONNECTED');
  }
  
  destroy() {
    this.stopEllipsisAnimation();
    this.clearPausedTimeout();
    this.button = null;
  }
}

/**
 * UI Management Class for The Gold Box
 */
class GoldBoxUIManager {
  constructor(settingsManager, moduleInstance) {
    this.settingsManager = settingsManager;
    this.moduleInstance = moduleInstance;
    this.buttonRetryCount = 0;
    // Initialize AI Turn button handler
    this.aiTurnButtonHandler = new AITurnButtonHandler(this, moduleInstance);
  }

  /**
   * Initialize UI manager
   */
  init() {
    console.log('The Gold Box: UI Manager initialized');
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
      this.moduleInstance.onTakeAITurn();
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
      this.moduleInstance.onTakeAITurn();
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
      
      // Reset delta counters when AI turn completes
      window.FrontendDeltaService?.resetDeltaCounts();
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
    
    // When relay transmission works, don't show a separate message - AI response was already sent to chat
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
   * Parse markdown-style content to HTML for Foundry
   * Converts **bold** to <h4> headings and preserves newlines
   */
  parseMarkdownToHTML(content) {
    // Preserve newlines by converting to <br> tags first
    let html = content.replace(/\n/g, '<br>');
    
    // Convert **text** to <h4>text</h4> (headings)
    html = html.replace(/\*\*(.*?)\*\*/g, '<h4>$1</h4>');
    
    // Convert *text* to <strong>text</strong> (bold)
    html = html.replace(/(?<!\*)\*(?!\*)\*(.*?)\*(?!\*)/g, '<strong>$1</strong>');
    
    // Preserve line breaks between sections
    html = html.replace(/(<\/h4>)(<br>)/g, '$1');
    html = html.replace(/(<br>)(<h4>)/g, '$1');
    
    return html;
  }

  /**
   * Display individual chat message from WebSocket response
   */
  displayChatMessage(msgData) {
    try {
      console.log('The Gold Box: Displaying chat message:', msgData);
      
      // Always use "The Gold Box" as the speaker to clearly label AI-generated content
      const content = msgData.content || '';
      
      // Parse markdown-style formatting to HTML
      const htmlContent = this.parseMarkdownToHTML(content);
      
      // Create chat message in Foundry (using current API)
      ChatMessage.create({
        user: game.user.id,
        content: htmlContent,
        speaker: {
          alias: 'The Gold Box' // Always show as The Gold Box to avoid confusion
        },
        style: CONST.CHAT_MESSAGE_STYLES.IC, // In-character message (current API)
        flags: {
          'gold-box': {
            isAIMessage: true  // Flag for hook to identify our messages
          }
        }
      });
      
      // CRITICAL FIX: Also send message via message collector for immediate backend sync
      // This ensures post_message results are available for get_message_history in same session
      if (window.goldBox && window.goldBox.messageCollector) {
        window.goldBox.messageCollector.sendChatMessage({
          type: 'chat',
          content: htmlContent,
          speaker: {
            name: 'The Gold Box',
            alias: 'The Gold Box'
          },
          timestamp: Date.now()
        });
        console.log('The Gold Box: Message data sent via message collector');
      }
      
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
        sound: CONFIG.sounds.dice,
        flags: {
          'gold-box': {
            isAIMessage: true  // Flag for hook to identify our messages
          }
        }
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
        style: CONST.CHAT_MESSAGE_STYLES.OTHER, // Current API: use style instead of type
        flags: {
          'gold-box': {
            isAIMessage: true  // Flag for hook to identify our messages
          }
        }
      });
      
    } catch (error) {
      console.error('The Gold Box: Error displaying chat card:', error);
    }
  }

  /**
   * Display startup instructions prominently in chat
   */
  displayStartupInstructions() {
    // Use hardcoded name since we removed moduleElementsName setting
    const customName = 'The Gold Box';
    
    // Simplified startup instructions
    const messageContent = `
      <div class="gold-box-startup">
        <div class="gold-box-header">
          <strong>${customName} - Backend Startup Required</strong>
          <div class="gold-box-timestamp">${new Date().toLocaleTimeString()}</div>
        </div>
        <div class="gold-box-content">
          <p><strong>Backend Server Not Running or Not Reachable</strong></p>
          <p>Run <code>backend.sh</code> from The Gold Box module directory to automatically set up and start the backend server.</p>
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
   * Show error notification to user
   */
  showErrorNotification(message) {
    if (typeof ui !== 'undefined' && ui.notifications) {
      ui.notifications.error(message);
    }
  }

  /**
   * Show success notification to user
   */
  showSuccessNotification(message) {
    if (typeof ui !== 'undefined' && ui.notifications) {
      ui.notifications.info(message);
    }
  }

  /**
   * Clean up UI elements when module is disabled
   */
  tearDown() {
    // Remove processing indicator
    this.hideProcessingIndicator();
    
    // Remove chat button
    $('#gold-box-ai-turn-btn').remove();
    
    console.log('The Gold Box: UI Manager torn down');
  }
}

// Export class for use in other modules
window.GoldBoxUIManager = GoldBoxUIManager;
