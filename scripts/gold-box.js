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
    Hooks.on('renderSettings', (app, html) => {
      // Add a button to the settings menu
      const button = $(`
        <button>
          <i class="fas fa-robot"></i> The Gold Box
        </button>
      `);
      
      button.click(() => {
        this.showModuleInfo();
      });
      
      html.find('#settings-game').append(button);
    });

    // Hook when the sidebar is rendered
    Hooks.on('renderSidebarTab', (app, html) => {
      if (app.options.id === 'chat') {
        // Add AI controls to chat sidebar
        this.addChatControls(html);
      }
    });
  }

  /**
   * Add AI controls to the chat sidebar
   */
  addChatControls(html) {
    const aiButton = $(`
      <div class="gold-box-controls">
        <button class="gold-box-ai-turn">
          <i class="fas fa-play"></i> Take AI Turn
        </button>
      </div>
    `);
    
    aiButton.find('.gold-box-ai-turn').click(() => {
      this.onTakeAITurn();
    });
    
    html.find('.chat-controls').after(aiButton);
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
        <h2>The Gold Box v0.1.0</h2>
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
