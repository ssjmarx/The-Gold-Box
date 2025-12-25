/**
 * The Gold Box - Frontend Delta Service
 * Tracks message counts (new/deleted) since last AI turn
 * 
 * Purpose:
 * - Track new messages added to Foundry chat since last AI turn
 * - Track deleted messages removed from Foundry chat since last AI turn
 * - Display these counts to AI in system prompt (function calling mode only)
 * - Help AI understand what changed without seeing entire message history again
 */

export class FrontendDeltaService {
  constructor() {
    this.newMessages = 0;
    this.deletedMessages = 0;
    console.log('The Gold Box: FrontendDeltaService initialized');
  }

  /**
   * Get current delta counts
   * @returns {Object} Delta counts object with new_messages and deleted_messages (snake_case to match backend)
   */
  getDeltaCounts() {
    return {
      new_messages: this.newMessages,
      deleted_messages: this.deletedMessages
    };
  }

  /**
   * Reset delta counts to zero
   * Called when AI turn completes to prepare for next turn
   */
  resetDeltaCounts() {
    const countsBeforeReset = this.getDeltaCounts();
    this.newMessages = 0;
    this.deletedMessages = 0;
    console.log(`The Gold Box: Delta counts reset. Before reset: New=${countsBeforeReset.newMessages}, Deleted=${countsBeforeReset.deletedMessages}`);
  }

  /**
   * Increment new messages counter
   * Called when a message is created in Foundry
   */
  incrementNewMessages() {
    this.newMessages++;
    console.log(`The Gold Box: New message detected. Total new messages: ${this.newMessages}`);
  }

  /**
   * Increment deleted messages counter
   * Called when a message is deleted from Foundry
   */
  incrementDeletedMessages() {
    this.deletedMessages++;
    console.log(`The Gold Box: Deleted message detected. Total deleted messages: ${this.deletedMessages}`);
  }
}

// Create global instance and attach to window
if (!window.FrontendDeltaService) {
  window.FrontendDeltaService = new FrontendDeltaService();
  console.log('The Gold Box: FrontendDeltaService attached to window');
}

// Register Foundry hooks for message tracking
Hooks.on('createChatMessage', (chatMessage) => {
  // Only increment counter for user-created messages, not AI-generated messages
  // AI-generated messages have the isAIMessage flag
  const isAIMessage = chatMessage.flags?.['gold-box']?.isAIMessage;
  if (!isAIMessage) {
    window.FrontendDeltaService?.incrementNewMessages();
  }
});

Hooks.on('deleteChatMessage', (document, options) => {
  // Only increment counter for user-created messages, not AI-generated messages
  const isAIMessage = document.flags?.['gold-box']?.isAIMessage;
  if (!isAIMessage) {
    window.FrontendDeltaService?.incrementDeletedMessages();
  }
});

console.log('The Gold Box: Frontend delta service loaded and Foundry hooks registered');
