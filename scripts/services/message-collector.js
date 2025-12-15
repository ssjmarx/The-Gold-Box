/**
 * The Gold Box - Message Collection System
 * Hooks into Foundry events to collect chat messages, dice rolls, and game events
 * Formats messages for backend processing
 */

/**
 * Message Collector Class
 */
class MessageCollector {
  constructor() {
    this.messages = [];
    this.rolls = [];
    this.maxMessages = 15; // Default to 15, will be updated by settings
    this.maxRolls = 50; // Keep last 50 rolls
    this.hooks = [];
    this.isEnabled = false;
    this.collectionInterval = null;
    this.lastCollection = 0;
    this.settingsManager = null; // Will be set from gold-box.js
    
    console.log('MessageCollector: Initialized');
  }

  /**
   * Send individual chat message to backend via WebSocket
   * Replaces DOM scraping with real-time collection
   */
  sendChatMessage(messageData) {
    if (this.active && this.webSocketClient && this.webSocketClient.isConnected) {
      // Add metadata to message
      const enrichedMessage = {
        ...messageData,
        type: messageData.type || 'chat',
        timestamp: messageData.timestamp || Date.now(),
        source: 'foundry-chat'
      };
      
      // Send individual message via WebSocket
      this.webSocketClient.sendMessage({
        type: 'chat_message',
        data: enrichedMessage
      });
      
      console.log('MessageCollector: Sent chat message via WebSocket:', enrichedMessage.type);
    } else {
      console.warn('MessageCollector: WebSocket not connected - cannot send message');
    }
  }

  /**
   * Send dice roll to backend via WebSocket
   * Replaces DOM scraping with real-time collection
   */
  sendDiceRoll(rollData) {
    if (this.active && this.webSocketClient && this.webSocketClient.isConnected) {
      // Add metadata to roll
      const enrichedRoll = {
        ...rollData,
        type: 'roll',
        timestamp: rollData.timestamp || Date.now(),
        source: 'foundry-dice'
      };
      
      // Send dice roll via WebSocket
      this.webSocketClient.sendMessage({
        type: 'dice_roll',
        data: enrichedRoll
      });
      
      console.log('MessageCollector: Sent dice roll via WebSocket:', enrichedRoll.formula);
    } else {
      console.warn('MessageCollector: WebSocket not connected - cannot send roll');
    }
  }

  /**
   * Collect chat messages (now WebSocket-ready)
   * DEPRECATED: Use WebSocket collection instead of DOM scraping
   */
  collectChatMessages() {
    if (this.active && this.uiManager && this.webSocketClient) {
      const messages = this.uiManager.collectChatMessages();
      console.log('MessageCollector: Collected messages for WebSocket collection:', messages.length);
      
      // Send to backend via WebSocket if available
      if (this.webSocketClient.isConnected) {
        this.webSocketClient.sendMessage({
          type: 'chat_collection',
          data: {
            messages: messages,
            timestamp: Date.now()
          }
        });
      } else {
        console.warn('MessageCollector: WebSocket not connected - cannot send collected messages');
      }
    }
  }

  /**
   * Stop collecting messages
   */
  stop() {
    if (!this.isEnabled) {
      console.warn('MessageCollector: Already stopped');
      return;
    }

    console.log('MessageCollector: Stopping message collection...');
    this.isEnabled = false;
    
    // Unregister hooks
    this.unregisterHooks();
    
    // Stop periodic collection
    this.stopPeriodicCollection();
    
    console.log('MessageCollector: Stopped successfully');
  }

  /**
   * Register Foundry hooks for message collection
   */
  registerHooks() {
    // Chat message hook
    this.hooks.push(Hooks.on('createChatMessage', (message, options, userId) => {
      this.onChatMessage(message, options, userId);
    }));

    // Dice roll hook
    this.hooks.push(Hooks.on('createChatMessage', (message, options, userId) => {
      this.onDiceRoll(message, options, userId);
    }));

    // Combat hook for combat events
    if (Hooks.on) {
      this.hooks.push(Hooks.on('updateCombat', (combat, changes) => {
        this.onCombatUpdate(combat, changes);
      }));
    }

    console.log(`MessageCollector: Registered ${this.hooks.length} hooks`);
  }

  /**
   * Unregister Foundry hooks
   */
  unregisterHooks() {
    this.hooks.forEach(hook => {
      if (hook && typeof hook === 'function') {
        // Note: Foundry doesn't provide a way to unregister specific hooks
        // This is a limitation of the current Foundry hook system
      }
    });
    this.hooks = [];
  }

  /**
   * Collect existing messages from chat log
   */
  collectExistingMessages() {
    try {
      if (!game.messages || !game.messages.size) {
        console.log('MessageCollector: No existing messages to collect');
        return;
      }

      console.log(`MessageCollector: Collecting ${game.messages.size} existing messages`);
      
      // Get recent messages from Foundry's message collection
      const recentMessages = game.messages.contents
        .filter(msg => msg.content && msg.content.trim())
        .slice(-this.maxMessages);

      recentMessages.forEach(message => {
        this.addMessage(message);
      });

      console.log(`MessageCollector: Collected ${recentMessages.length} existing messages`);
    } catch (error) {
      console.error('MessageCollector: Error collecting existing messages:', error);
    }
  }

  /**
   * Handle new chat message
   */
  onChatMessage(message, options, userId) {
    if (!this.isEnabled || !message) return;

    try {
      // Skip system messages that don't contain meaningful content
      if (message.type === 1 && (!message.content || message.content.trim() === '')) {
        return;
      }

      // Format message for backend
      const formattedMessage = this.formatMessage(message);
      if (formattedMessage) {
        this.addMessage(formattedMessage);
        console.log('MessageCollector: Collected chat message:', formattedMessage.type);
      }
    } catch (error) {
      console.error('MessageCollector: Error handling chat message:', error);
    }
  }

  /**
   * Handle dice roll message
   */
  onDiceRoll(message, options, userId) {
    if (!this.isEnabled || !message) return;

    try {
      // Check if this is a dice roll message
      if (message.rolls && message.rolls.length > 0) {
        const formattedRoll = this.formatRoll(message);
        if (formattedRoll) {
          this.addRoll(formattedRoll);
          console.log('MessageCollector: Collected dice roll:', formattedRoll.formula);
        }
      }
    } catch (error) {
      console.error('MessageCollector: Error handling dice roll:', error);
    }
  }

  /**
   * Handle combat updates
   */
  onCombatUpdate(combat, changes) {
    if (!this.isEnabled || !combat) return;

    try {
      // Create a combat event message
      const combatMessage = {
        id: `combat_${Date.now()}`,
        type: 'combat',
        content: `Combat update: ${JSON.stringify(changes)}`,
        timestamp: Date.now(),
        combat: {
          id: combat.id,
          active: combat.active,
          round: combat.round,
          turn: combat.turn,
          changes: changes
        }
      };

      this.addMessage(combatMessage);
      console.log('MessageCollector: Collected combat event');
    } catch (error) {
      console.error('MessageCollector: Error handling combat update:', error);
    }
  }

  /**
   * Format message for backend processing
   */
  formatMessage(message) {
    try {
      return {
        id: message.id || `msg_${Date.now()}_${Math.random().toString(36).substring(2, 15)}`,
        type: this.getMessageType(message),
        content: message.content || '',
        timestamp: message.timestamp || Date.now(),
        speaker: {
          id: message.speaker?.id || message.author?.id,
          name: message.speaker?.name || message.author?.name || 'Unknown',
          alias: message.speaker?.alias,
          avatar: message.speaker?.avatar
        },
        flags: message.flags || {},
        whisper: message.whisper || false,
        blind: message.blind || false,
        roll: message.roll || null,
        rolls: message.rolls || []
      };
    } catch (error) {
      console.error('MessageCollector: Error formatting message:', error);
      return null;
    }
  }

  /**
   * Format dice roll for backend processing
   */
  formatRoll(message) {
    try {
      if (!message.rolls || message.rolls.length === 0) {
        return null;
      }

      const primaryRoll = message.rolls[0]; // Use first roll as primary

      return {
        id: message.id || `roll_${Date.now()}_${Math.random().toString(36).substring(2, 15)}`,
        type: 'dice_roll',
        formula: primaryRoll.formula || '',
        total: primaryRoll.total || 0,
        results: primaryRoll.results || [],
        flavor: message.flavor || '',
        timestamp: message.timestamp || Date.now(),
        speaker: {
          id: message.speaker?.id || message.author?.id,
          name: message.speaker?.name || message.author?.name || 'Unknown'
        },
        roll: primaryRoll,
        rolls: message.rolls || []
      };
    } catch (error) {
      console.error('MessageCollector: Error formatting roll:', error);
      return null;
    }
  }

  /**
   * Get message type from Foundry message
   */
  getMessageType(message) {
    if (message.rolls && message.rolls.length > 0) {
      return 'dice_roll';
    }
    
    if (message.type === 0) {
      return 'chat';
    } else if (message.type === 1) {
      return 'emote';
    } else if (message.type === 2) {
      return 'whisper';
    } else if (message.type === 3) {
      return 'ooc';
    } else if (message.type === 4) {
      return 'ic';
    } else if (message.type === 5) {
      return 'system';
    }
    
    return 'chat';
  }

  /**
   * Add message to collection
   */
  addMessage(message) {
    if (!message) return;

    // Add timestamp if missing
    if (!message.timestamp) {
      message.timestamp = Date.now();
    }

    // Add to messages array
    this.messages.push(message);

    // Trim to max size
    if (this.messages.length > this.maxMessages) {
      this.messages = this.messages.slice(-this.maxMessages);
    }

    this.lastCollection = Date.now();
  }

  /**
   * Add roll to collection
   */
  addRoll(roll) {
    if (!roll) return;

    // Add timestamp if missing
    if (!roll.timestamp) {
      roll.timestamp = Date.now();
    }

    // Add to rolls array
    this.rolls.push(roll);

    // Trim to max size
    if (this.rolls.length > this.maxRolls) {
      this.rolls = this.rolls.slice(-this.maxRolls);
    }

    this.lastCollection = Date.now();
  }

  /**
   * Get recent messages for backend
   */
  getRecentMessages(count) {
    // Require explicit count parameter - no defaults
    if (!count || count <= 0) {
      console.warn('MessageCollector: getRecentMessages requires a valid count parameter');
      return [];
    }

    const recentMessages = this.messages.slice(-count);
    const recentRolls = this.rolls.slice(-count);

    // Combine and sort by timestamp
    const allMessages = [
      ...recentMessages.map(msg => ({ ...msg, _source: 'chat' })),
      ...recentRolls.map(roll => ({ ...roll, _source: 'roll' }))
    ];

    // Sort by timestamp (newest first)
    allMessages.sort((a, b) => b.timestamp - a.timestamp);

    // Return the requested count, sorted chronologically (oldest first)
    return allMessages.slice(-count).reverse();
  }

  /**
   * Get messages in WebSocket format
   */
  getWebSocketMessages(count) {
    // Require explicit count parameter - no defaults
    if (!count || count <= 0) {
      console.warn('MessageCollector: getWebSocketMessages requires a valid count parameter');
      return [];
    }

    const recentMessages = this.getRecentMessages(count);
    
    // Convert to compact WebSocket format
    return recentMessages.map(msg => {
      if (msg.type === 'dice_roll') {
        return {
          t: 'dr', // dice_roll
          f: msg.formula,
          tt: msg.total,
          r: msg.results || [],
          ft: msg.flavor || '',
          s: msg.speaker?.name || 'Unknown',
          timestamp: msg.timestamp
        };
      } else {
        return {
          t: 'cm', // chat_message
          s: msg.speaker?.name || 'Unknown',
          c: msg.content || '',
          timestamp: msg.timestamp
        };
      }
    });
  }

  /**
   * Start periodic collection
   */
  startPeriodicCollection() {
    this.stopPeriodicCollection();

    this.collectionInterval = setInterval(() => {
      if (this.isEnabled) {
        this.performPeriodicCollection();
      }
    }, 5000); // Collect every 5 seconds

    console.log('MessageCollector: Started periodic collection');
  }

  /**
   * Stop periodic collection
   */
  stopPeriodicCollection() {
    if (this.collectionInterval) {
      clearInterval(this.collectionInterval);
      this.collectionInterval = null;
      console.log('MessageCollector: Stopped periodic collection');
    }
  }

  /**
   * Perform periodic collection
   */
  performPeriodicCollection() {
    try {
      // Check for new messages in Foundry's message log
      if (game.messages && game.messages.size > this.messages.length) {
        const latestMessages = game.messages.contents
          .filter(msg => msg.timestamp > this.lastCollection)
          .slice(-10); // Get last 10 new messages

        latestMessages.forEach(message => {
          this.addMessage(this.formatMessage(message));
        });

        if (latestMessages.length > 0) {
          console.log(`MessageCollector: Periodic collection found ${latestMessages.length} new messages`);
        }
      }
    } catch (error) {
      console.error('MessageCollector: Error in periodic collection:', error);
    }
  }

  /**
   * Get collection status
   */
  getStatus() {
    return {
      enabled: this.isEnabled,
      messageCount: this.messages.length,
      rollCount: this.rolls.length,
      lastCollection: this.lastCollection,
      hooksRegistered: this.hooks.length
    };
  }

  /**
   * Clear all collected messages
   */
  clear() {
    this.messages = [];
    this.rolls = [];
    this.lastCollection = 0;
    console.log('MessageCollector: Cleared all messages');
  }

  /**
   * Set SettingsManager reference and update maxMessages from settings
   */
  setSettingsManager(settingsManager) {
    this.settingsManager = settingsManager;
    // Update maxMessages from settings
    if (this.settingsManager) {
      this.maxMessages = this.settingsManager.getSetting('maxMessageContext', 15);
      console.log(`MessageCollector: Updated maxMessages to ${this.maxMessages} from settings`);
    }
  }

  /**
   * Export messages for debugging
   */
  exportMessages() {
    return {
      messages: this.messages,
      rolls: this.rolls,
      status: this.getStatus(),
      exportTime: Date.now()
    };
  }
}

// Export for global access
window.MessageCollector = MessageCollector;

console.log('MessageCollector: Module loaded');
