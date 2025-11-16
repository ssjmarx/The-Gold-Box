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
    });

    // Hook when settings are rendered
    Hooks.on('renderSettings', (app, html, data) => {
      console.log('The Gold Box: renderSettings hook called');
      
      // Wrap html with jQuery to use jQuery methods
      const $html = $(html);
      
      // Add a button to the settings menu - use jQuery to append to html
      const button = $('<button><i class="fas fa-robot"></i> The Gold Box</button>');
      button.css({
        'margin': '0.25rem',
        'padding': '0.5rem 1rem',
        'background': '#4a5568',
        'color': 'white',
        'border': 'none',
        'border-radius': '0.25rem',
        'cursor': 'pointer'
      });
      button.click(() => {
        this.showModuleInfo();
      });
      
      // Find the settings menu container and add the button
      const settingsMenu = $html.find('.settings-sidebar') || $html.find('#settings') || $html.find('.settings-list');
      if (settingsMenu.length) {
        settingsMenu.append(button);
        console.log('The Gold Box: Adding button to settings menu');
      } else {
        console.error('The Gold Box: Could not find settings menu');
        console.log('The Gold Box: Available elements:', $html[0].outerHTML.substring(0, 200));
      }
    });

    // Hook when the sidebar is rendered
    Hooks.on('renderSidebarTab', (app, html, data) => {
      console.log('The Gold Box: renderSidebarTab hook called for', app.options.id);
      
      if (app.options.id === 'chat') {
        // Add AI controls to chat sidebar
        this.addChatControls(app.element);
      }
    });

    // Also try to add chat controls when chat log is rendered
    Hooks.on('renderChatLog', (app, html, data) => {
      console.log('The Gold Box: renderChatLog hook called');
      this.addChatControls(app.element);
    });
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
