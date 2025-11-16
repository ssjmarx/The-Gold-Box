/**
 * The Gold Box - AI-powered Foundry VTT Module
 * Main module entry point
 */

class GoldBoxModule {
  constructor() {
    this.hooks = [];
  }

  /**
   * Initialize the module
   */
  async init() {
    console.log('The Gold Box module initialized');
    
    // Register hooks
    this.registerHooks();
    
    // Log that the module is ready
    console.log('The Gold Box is ready for AI adventures!');
  }

  /**
   * Register Foundry VTT hooks
   */
  registerHooks() {
    // Hook when the game is ready
    Hooks.once('ready', () => {
      console.log('The Gold Box: Game is ready');
      
      // Add buttons after DOM is fully loaded
      this.addSettingsButton();
      this.addChatButton();
    });
  }

  /**
   * Add settings button to the settings menu
   */
  addSettingsButton() {
    try {
      // Wait a bit for DOM to be ready
      setTimeout(() => {
        // Look for the settings tab button and add our button next to it
        const settingsTab = $('a[data-tab="settings"]');
        if (settingsTab.length > 0) {
          const button = $('<button><i class="fas fa-robot"></i> The Gold Box</button>');
          button.css({
            'margin': '0 0.25rem',
            'padding': '0.5rem 1rem',
            'background': '#4a5568',
            'color': 'white',
            'border': 'none',
            'border-radius': '0.25rem',
            'cursor': 'pointer',
            'font-size': '0.9rem'
          });
          button.click(() => {
            this.showModuleInfo();
          });
          
          // Insert after the settings tab
          settingsTab.after(button);
          console.log('The Gold Box: Added settings button using ready hook');
        } else {
          console.error('The Gold Box: Could not find settings tab');
        }
      }, 1000);
    } catch (error) {
      console.error('The Gold Box: Error adding settings button:', error);
    }
  }

  /**
   * Add chat button to the chat sidebar
   */
  addChatButton() {
    try {
      // Wait a bit for DOM to be ready
      setTimeout(() => {
        // Look for the chat tab and add our button
        const chatTab = $('a[data-tab="chat"]');
        if (chatTab.length > 0) {
          const controlsDiv = $('<div class="gold-box-controls"></div>');
          controlsDiv.css({
            'margin': '0.5rem',
            'padding': '0.5rem',
            'border-top': '1px solid #ccc'
          });
          
          const aiButton = $('<button><i class="fas fa-play"></i> Take AI Turn</button>');
          aiButton.css({
            'background': 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
            'color': 'white',
            'border': 'none',
            'padding': '0.5rem 1rem',
            'border-radius': '0.25rem',
            'cursor': 'pointer',
            'width': '100%',
            'font-size': '0.9rem'
          });
          aiButton.click(() => {
            this.onTakeAITurn();
          });
          
          controlsDiv.append(aiButton);
          
          // Find the chat form and add our button before it
          const chatForm = chatTab.closest('.sidebar-tab').find('form');
          if (chatForm.length > 0) {
            chatForm.before(controlsDiv);
            console.log('The Gold Box: Added chat button using ready hook');
          } else {
            console.error('The Gold Box: Could not find chat form');
          }
        } else {
          console.error('The Gold Box: Could not find chat tab');
        }
      }, 1500);
    } catch (error) {
      console.error('The Gold Box: Error adding chat button:', error);
    }
  }

  /**
   * Add AI controls to the chat sidebar
   */
  addChatControls(html) {
    console.log('The Gold Box: addChatControls called');
    
    // Wrap html with jQuery to use jQuery methods
    const $html = $(html);
    
    // Create a controls container using jQuery
    const controlsDiv = $('<div class="gold-box-controls"></div>');
    controlsDiv.css({
      'margin-top': '10px',
      'padding': '10px',
      'border-top': '1px solid #ccc'
    });
    
    // Create an AI turn button using jQuery
    const aiButton = $('<button><i class="fas fa-play"></i> Take AI Turn</button>');
    aiButton.css({
      'background': 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
      'color': 'white',
      'border': 'none',
      'padding': '8px 16px',
      'border-radius': '4px',
      'cursor': 'pointer',
      'width': '100%'
    });
    aiButton.click(() => {
      this.onTakeAITurn();
    });
    
    controlsDiv.append(aiButton);
    
    // Find the chat controls container and add our button after it
    const chatControls = $html.find('.chat-sidebar') || $html.find('#chat') || $html.find('.chat');
    if (chatControls.length) {
      chatControls.after(controlsDiv);
      console.log('The Gold Box: Found chat controls, adding button');
    } else {
      console.error('The Gold Box: Could not find chat controls');
      console.log('The Gold Box: Available elements:', $html[0].outerHTML.substring(0, 300));
      
      // As a fallback, try to add to the main html element
      $html.append(controlsDiv);
      console.log('The Gold Box: Added button as fallback');
    }
  }

  /**
   * Handle "Take AI Turn" button click
   */
  async onTakeAITurn() {
    console.log('The Gold Box: AI turn requested');
    ui.notifications.info('The Gold Box: AI functionality coming soon!');
  }

  /**
   * Show module information dialog
   */
  showModuleInfo() {
    const dialog = new Dialog({
      title: 'The Gold Box',
      content: `
        <h2>The Gold Box v0.1.6</h2>
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

  /**
   * Clean up when the module is disabled
   */
  tearDown() {
    console.log('The Gold Box module disabled');
  }
}

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
