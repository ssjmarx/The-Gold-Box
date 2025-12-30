/**
 * The Gold Box - Settings Manager
 * Handles all game settings registration and management for Gold Box module
 */

/**
 * Settings Manager Class
 */
class SettingsManager {
  constructor() {
    this.moduleName = 'the-gold-box';
    this.settingsRegistered = false;
    console.log('SettingsManager: Initialized');
  }

  /**
   * Register all Gold Box settings with Foundry
   */
  registerAllSettings() {
    if (this.settingsRegistered) {
      console.warn('SettingsManager: Settings already registered');
      return;
    }

    console.log('SettingsManager: Starting settings registration...');
    
    // Check if settings are available
    if (!game.settings) {
      console.error('SettingsManager: game.settings not available during hook registration');
      return;
    }
    
    // Register all settings
    this.registerBackendStatus();
    this.registerBackendPassword();
    this.registerMaxHistoryTokens();
    this.registerAIResponseTimeout();
    this.registerAIRole();
    this.registerDisableFunctionCalling();
    this.registerGeneralLLMSettings();
    this.registerTacticalLLMSettings();
    this.registerSettingsConfigHooks();
    
    this.settingsRegistered = true;
    console.log('SettingsManager: All settings registered successfully');
  }

  /**
   * Register backend status setting (display-only)
   */
  registerBackendStatus() {
    game.settings.register(this.moduleName, 'backendStatus', {
      name: "Backend Status",
      hint: "Current status of backend server (automatically detected)",
      scope: "world",
      config: false, // Not editable by user
      type: String,
      default: "checking...",
      group: "general"
    });
  }

  /**
   * Register Backend Password setting
   */
  registerBackendPassword() {
    try {
      game.settings.register(this.moduleName, 'backendPassword', {
        name: "Backend Password",
        hint: "Password for admin operations on backend server (used to sync settings)",
        scope: "world",
        config: true,
        type: String,
        default: "",
        group: "general"
      });
      console.log('SettingsManager: Successfully registered backendPassword setting');
    } catch (error) {
      console.error('SettingsManager: Failed to register backendPassword setting:', error);
    }
  }

  /**
   * Register max history tokens setting
   */
  registerMaxHistoryTokens() {
    game.settings.register(this.moduleName, 'maxHistoryTokens', {
      name: "Max History Tokens",
      hint: "Maximum tokens to keep in conversation history before cleaning up oldest messages (default: 5000)",
      scope: "world",
      config: true,
      type: Number,
      default: 5000,
      group: "general"
    });
  }


  /**
   * Register AI Response Timeout setting
   */
  registerAIResponseTimeout() {
    game.settings.register(this.moduleName, 'aiResponseTimeout', {
      name: "AI Response Timeout (seconds)",
      hint: "Maximum time to wait for AI response before re-enabling button (default: 60)",
      scope: "world",
      config: true,
      type: Number,
      default: 60,
      group: "general"
    });
  }

  /**
   * Register AI role setting with dropdown
   */
  registerAIRole() {
    game.settings.register(this.moduleName, 'aiRole', {
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
      default: "dm",
      group: "general"
    });
  }

  /**
   * Register Disable Function Calling setting
   */
  registerDisableFunctionCalling() {
    game.settings.register(this.moduleName, 'disableFunctionCalling', {
      name: "Disable AI Function Calling",
      hint: "Disable AI tool usage (get_messages, post_messages). Only check this if your AI provider doesn't support function calling. Default: unchecked (function calling enabled).",
      scope: "world",
      config: true,
      type: Boolean,
      default: false,
      group: "general"
    });
  }

  /**
   * Register General LLM Provider settings
   */
  registerGeneralLLMSettings() {
    // General LLM Provider
    game.settings.register(this.moduleName, 'generalLlmProvider', {
      name: "General LLM - Provider",
      hint: "Provider name for General LLM (e.g., openai, anthropic, opencode, custom-provider)",
      scope: "world",
      config: true,
      type: String,
      default: "",
      group: "general_llm"
    });

    // General LLM Base URL
    game.settings.register(this.moduleName, 'generalLlmBaseUrl', {
      name: "General LLM - Base URL",
      hint: "Base URL for General LLM provider (e.g., https://api.openai.com/v1, https://api.z.ai/api/coding/paas/v4)",
      scope: "world",
      config: true,
      type: String,
      default: "",
      group: "general_llm"
    });

    // General LLM Model
    game.settings.register(this.moduleName, 'generalLlmModel', {
      name: "General LLM - Model",
      hint: "Model name for General LLM (e.g., gpt-3.5-turbo, claude-3-5-sonnet-20241022, openai/glm-4.6)",
      scope: "world",
      config: true,
      type: String,
      default: "",
      group: "general_llm"
    });

    // General LLM Version
    game.settings.register(this.moduleName, 'generalLlmVersion', {
      name: "General LLM - API Version",
      hint: "API version for General LLM (e.g., v1, v2, custom)",
      scope: "world",
      config: true,
      type: String,
      default: "v1",
      group: "general_llm"
    });


    // General LLM Max Retries
    game.settings.register(this.moduleName, 'generalLlmMaxRetries', {
      name: "General LLM - Max Retries",
      hint: "Maximum retry attempts for General LLM (default: 3)",
      scope: "world",
      config: true,
      type: Number,
      default: 3,
      group: "general_llm"
    });

    // General LLM Custom Headers
    game.settings.register(this.moduleName, 'generalLlmCustomHeaders', {
      name: "General LLM - Custom Headers (JSON)",
      hint: "Custom headers for General LLM in JSON format (advanced)",
      scope: "world",
      config: true,
      type: String,
      default: "",
      group: "general_llm"
    });
  }

  /**
   * Register Tactical LLM settings (placeholders for future implementation)
   */
  registerTacticalLLMSettings() {
    // Tactical LLM Provider
    game.settings.register(this.moduleName, 'tacticalLlmProvider', {
      name: "Tactical LLM - Provider",
      hint: "Provider name for Tactical LLM (placeholder for future implementation)",
      scope: "world",
      config: true,
      type: String,
      default: "",
      group: "tactical_llm"
    });

    // Tactical LLM Base URL
    game.settings.register(this.moduleName, 'tacticalLlmBaseUrl', {
      name: "Tactical LLM - Base URL",
      hint: "Base URL for Tactical LLM provider (placeholder for future implementation)",
      scope: "world",
      config: true,
      type: String,
      default: "",
      group: "tactical_llm"
    });

    // Tactical LLM Model
    game.settings.register(this.moduleName, 'tacticalLlmModel', {
      name: "Tactical LLM - Model",
      hint: "Model name for Tactical LLM (placeholder for future implementation)",
      scope: "world",
      config: true,
      type: String,
      default: "",
      group: "tactical_llm"
    });

    // Tactical LLM Version
    game.settings.register(this.moduleName, 'tacticalLlmVersion', {
      name: "Tactical LLM - API Version",
      hint: "API version for Tactical LLM (e.g., v1, v2, custom)",
      scope: "world",
      config: true,
      type: String,
      default: "v1",
      group: "tactical_llm"
    });


    // Tactical LLM Max Retries
    game.settings.register(this.moduleName, 'tacticalLlmMaxRetries', {
      name: "Tactical LLM - Max Retries",
      hint: "Maximum retry attempts for Tactical LLM (default: 3)",
      scope: "world",
      config: true,
      type: Number,
      default: 3,
      group: "tactical_llm"
    });

    // Tactical LLM Custom Headers
    game.settings.register(this.moduleName, 'tacticalLlmCustomHeaders', {
      name: "Tactical LLM - Custom Headers (JSON)",
      hint: "Custom headers for Tactical LLM in JSON format (advanced)",
      scope: "world",
      config: true,
      type: String,
      default: "",
      group: "tactical_llm"
    });
  }

  /**
   * Register settings configuration hooks (like discovery button)
   */
  registerSettingsConfigHooks() {
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
      }
    });
  }

  /**
   * Get a specific setting value
   * @param {string} key - Setting key
   * @param {*} defaultValue - Default value if setting doesn't exist
   * @returns {*} - Setting value
   */
  getSetting(key, defaultValue = null) {
    try {
      if (typeof game !== 'undefined' && game.settings) {
        return game.settings.get(this.moduleName, key) ?? defaultValue;
      } else {
        console.warn('SettingsManager: Game settings not available');
        return defaultValue;
      }
    } catch (error) {
      console.error(`SettingsManager: Error getting setting ${key}:`, error);
      return defaultValue;
    }
  }

  /**
   * Set a specific setting value
   * @param {string} key - Setting key
   * @param {*} value - Setting value
   * @returns {Promise<boolean>} - True if successful
   */
  async setSetting(key, value) {
    try {
      if (typeof game !== 'undefined' && game.settings) {
        await game.settings.set(this.moduleName, key, value);
        return true;
      } else {
        console.warn('SettingsManager: Game settings not available');
        return false;
      }
    } catch (error) {
      console.error(`SettingsManager: Error setting setting ${key}:`, error);
      return false;
    }
  }

  /**
   * Get all Gold Box settings as a unified object
   * @returns {Object} - All settings object
   */
  getAllSettings() {
    if (typeof game !== 'undefined' && game.settings) {
      console.log("SETTINGS DEBUG: Game and game.settings available");
      const settings = {
        'max history tokens': this.getSetting('maxHistoryTokens', 5000),
        'chat processing mode': 'api', // Always use API mode now
        'ai role': this.getSetting('aiRole', 'dm'),
        'disable function calling': this.getSetting('disableFunctionCalling', false),
        'general llm provider': this.getSetting('generalLlmProvider', ''),
        'general llm base url': this.getSetting('generalLlmBaseUrl', ''),
        'general llm model': this.getSetting('generalLlmModel', ''),
        'general llm version': this.getSetting('generalLlmVersion', 'v1'),
        'general llm timeout': this.getSetting('aiResponseTimeout', 60),
        'general llm max retries': this.getSetting('generalLlmMaxRetries', 3),
        'general llm custom headers': this.getSetting('generalLlmCustomHeaders', ''),
        'tactical llm provider': this.getSetting('tacticalLlmProvider', ''),
        'tactical llm base url': this.getSetting('tacticalLlmBaseUrl', ''),
        'tactical llm model': this.getSetting('tacticalLlmModel', ''),
        'tactical llm version': this.getSetting('tacticalLlmVersion', 'v1'),
        'tactical llm max retries': this.getSetting('tacticalLlmMaxRetries', 3),
        'tactical llm custom headers': this.getSetting('tacticalLlmCustomHeaders', ''),
        'backend password': this.getSetting('backendPassword', '')
      };
      console.log("SETTINGS DEBUG: Retrieved settings count:", Object.keys(settings).length);
      console.log("SETTINGS DEBUG: Settings keys:", Object.keys(settings));
      console.log("SETTINGS DEBUG: General LLM Provider:", settings['general llm provider']);
      console.log("SETTINGS DEBUG: General LLM Model:", settings['general llm model']);
      return settings;
    } else {
      console.warn("SETTINGS DEBUG: Game or game.settings not available");
      return {};
    }
  }

  /**
   * Get processing mode for button text display
   * @returns {string} - Current processing mode
   */
  getProcessingMode() {
    return 'api'; // Always return 'api' mode now
  }

  /**
   * Get button text based on current processing mode
   * @returns {string} - Button text
   */
  getButtonText() {
    return 'Take AI Turn'; // Always use API mode text now
  }

  /**
   * Get AI role display text
   * @returns {string} - AI role display
   */
  getAIRoleDisplay() {
    const role = this.getSetting('aiRole', 'dm');
    const roleDisplay = {
      'dm': 'Dungeon Master',
      'dm_assistant': 'DM Assistant',
      'player': 'Player'
    };
    return roleDisplay[role] || 'AI Response';
  }

  /**
   * Check if settings have been registered
   * @returns {boolean} - True if registered
   */
  isRegistered() {
    return this.settingsRegistered;
  }
}

// Export for global access
window.SettingsManager = SettingsManager;

console.log('SettingsManager: Module loaded');
