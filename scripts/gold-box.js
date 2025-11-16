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
      
      // Add a button to the settings menu - use app's HTML element
      const button = document.createElement('button');
      button.innerHTML = '<i class="fas fa-robot"></i> The Gold Box';
      button.style.margin = '0.25rem';
      button.style.padding = '0.5rem 1rem';
      button.style.background = '#4a5568';
      button.style.color = 'white';
      button.style.border = 'none';
      button.style.borderRadius = '0.25rem';
      button.style.cursor = 'pointer';
      button.addEventListener('click', () => {
        this.showModuleInfo();
      });
      
      // Try to add to the settings app's element
      if (app.element && app.element.length) {
        app.element[0].appendChild(button);
        console.log('The Gold Box: Adding button to settings app element');
      } else {
        console.error('The Gold Box: Could not find app element');
        console.log('The Gold Box: App object:', app);
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
    console.log('The Gold Box: HTML element:', html.tagName || html.constructor.name);
    
    // Create the controls container
    const controlsDiv = document.createElement('div');
    controlsDiv.className = 'gold-box-controls';
    controlsDiv.style.marginTop = '10px';
    controlsDiv.style.padding = '10px';
    controlsDiv.style.borderTop = '1px solid #ccc';
    
    // Create the AI turn button
    const aiButton = document.createElement('button');
    aiButton.className = 'gold-box-ai-turn';
    aiButton.innerHTML = '<i class="fas fa-play"></i> Take AI Turn';
    aiButton.style.background = 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)';
    aiButton.style.color = 'white';
    aiButton.style.border = 'none';
    aiButton.style.padding = '8px 16px';
    aiButton.style.borderRadius = '4px';
    aiButton.style.cursor = 'pointer';
    aiButton.style.width = '100%';
    aiButton.addEventListener('click', () => {
      this.onTakeAITurn();
    });
    
    controlsDiv.appendChild(aiButton);
    
    // Try multiple selectors for chat container
    let chatContainer = html.querySelector('.chat-controls') ||
                      html.querySelector('.chat') ||
                      html.querySelector('#chat') ||
                      html.querySelector('.sidebar-tab');
    
    if (chatContainer) {
      console.log('The Gold Box: Found chat container, adding button');
      chatContainer.parentNode.insertBefore(controlsDiv, chatContainer.nextSibling);
    } else {
      console.error('The Gold Box: Could not find chat container');
      console.log('The Gold Box: Available elements:', html.innerHTML.substring(0, 300));
      
      // As a fallback, try to add to the main html element
      html.appendChild(controlsDiv);
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
        <h2>The Gold Box v0.1.2</h2>
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
