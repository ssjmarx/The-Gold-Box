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
    // Register the setting that we use in chat button and config
    game.settings.register('gold-box', 'moduleElementsName', {
      name: "Module Elements Name",
      scope: "world",
      config: false,
      type: String,
      default: "The Gold Box"
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
    ui.notifications.info('The Gold Box: AI functionality coming soon!');
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

// Simple configuration handler for settings menu
class GoldBoxConfig extends foundry.applications.api.HandlebarsApplicationMixin(foundry.applications.api.ApplicationV2) {
  static get defaultOptions() {
    return foundry.utils.mergeObject(super.defaultOptions, {
      title: 'The Gold Box Configuration',
      id: 'gold-box-config',
      template: 'templates/gold-box-config.html',
      width: 400,
      height: 300
    });
  }

  getData() {
    return {
      moduleElementsName: game.settings.get('gold-box', 'moduleElementsName') || 'The Gold Box'
    };
  }

  async _updateObject(event, formData) {
    await game.settings.set('gold-box', 'moduleElementsName', formData.moduleElementsName);
    ui.notifications.info('The Gold Box settings updated!');
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
