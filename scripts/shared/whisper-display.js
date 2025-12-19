/**
 * Whisper Display Manager for The Gold Box
 * Handles display of AI thinking whispers to GM in Foundry
 * Integrates with backend Whisper Service
 */

class WhisperDisplayManager {
    constructor() {
        this.whisperHistory = [];
        this.maxHistorySize = 50;
        this.isGM = false;
        this.displayEnabled = true;
        
        // Initialize GM status check
        this.checkGMStatus();
        
        // Hook into chat message processing
        this.initChatHooks();
        
        console.log("Whisper Display Manager initialized");
    }
    
    /**
     * Check if current user is GM
     */
    checkGMStatus() {
        try {
            this.isGM = game.user.isGM;
            console.log(`Whisper Display: User is GM: ${this.isGM}`);
        } catch (error) {
            console.warn("Whisper Display: Could not determine GM status:", error);
            this.isGM = false;
        }
    }
    
    /**
     * Initialize Foundry chat hooks
     */
    initChatHooks() {
        // Hook into chat message processing
        Hooks.on('renderChatMessage', (message, html, data) => {
            this.processChatMessage(message, html, data);
        });
        
        // Hook into chat log creation
        Hooks.on('createChatMessage', (message) => {
            this.processIncomingMessage(message);
        });
    }
    
    /**
     * Process incoming chat messages for whispers
     * @param {ChatMessage} message - Foundry chat message
     */
    processIncomingMessage(message) {
        try {
            // Check if this is a GM whisper from our system
            if (this.isGMWhisper(message)) {
                this.displayThinkingWhisper(message);
                this.addToHistory(message);
            }
        } catch (error) {
            console.error("Whisper Display: Error processing incoming message:", error);
        }
    }
    
    /**
     * Process rendered chat messages
     * @param {ChatMessage} message - Foundry chat message
     * @param {jQuery} html - Rendered HTML
     * @param {Object} data - Message data
     */
    processChatMessage(message, html, data) {
        try {
            // Add styling for thinking whispers
            if (this.isGMWhisper(message)) {
                this.styleThinkingWhisper(html);
            }
        } catch (error) {
            console.error("Whisper Display: Error processing chat message:", error);
        }
    }
    
    /**
     * Check if message is a GM thinking whisper
     * @param {ChatMessage} message - Foundry chat message
     * @returns {boolean} - True if this is a thinking whisper
     */
    isGMWhisper(message) {
        try {
            // Check message type and content
            const content = message.content || '';
            const whisperTo = message.whisper;
            
            // Handle different whisper formats in Foundry VTT
            let isWhisper = false;
            if (whisperTo) {
                if (typeof whisperTo === 'string') {
                    isWhisper = whisperTo.toLowerCase().includes('gm');
                } else if (Array.isArray(whisperTo)) {
                    isWhisper = whisperTo.some(w => w && w.toLowerCase && w.toLowerCase().includes('gm'));
                } else if (whisperTo && typeof whisperTo.toString === 'function') {
                    isWhisper = whisperTo.toString().toLowerCase().includes('gm');
                }
            }
            
            const hasThinking = content.toLowerCase().includes('thinking:');
            const hasSystemMarker = content.includes('[System]') || content.includes('[AI Assistant]');
            
            return isWhisper && (hasThinking || hasSystemMarker);
        } catch (error) {
            console.warn("Whisper Display: Error checking whisper type:", error);
            return false;
        }
    }
    
    /**
     * Display thinking whisper with special formatting
     * @param {ChatMessage} message - Foundry chat message
     */
    displayThinkingWhisper(message) {
        if (!this.displayEnabled || !this.isGM) return;
        
        try {
            console.log("Whisper Display: Displaying thinking whisper");
            
            // The message is already displayed by Foundry, just ensure it's visible
            // Additional processing could include:
            // - Highlighting the message
            // - Adding to a special thinking log
            // - Triggering notifications
            
            this.highlightThinkingMessage(message);
            
        } catch (error) {
            console.error("Whisper Display: Error displaying thinking whisper:", error);
        }
    }
    
    /**
     * Style thinking whisper HTML
     * @param {jQuery} html - Message HTML element
     */
    styleThinkingWhisper(html) {
        if (!this.displayEnabled) return;
        
        try {
            // Add CSS class for styling
            html.addClass('gold-box-thinking-whisper');
            
            // Add custom styling
            html.css({
                'background-color': 'rgba(100, 100, 255, 0.1)',
                'border-left': '4px solid #6464ff',
                'margin': '4px 0',
                'padding': '8px',
                'border-radius': '4px'
            });
            
            // Add thinking indicator
            const thinkingIcon = '<i class="fas fa-brain" style="color: #6464ff; margin-right: 8px;"></i>';
            html.find('.message-header').prepend(thinkingIcon);
            
        } catch (error) {
            console.error("Whisper Display: Error styling whisper:", error);
        }
    }
    
    /**
     * Highlight thinking message in chat log
     * @param {ChatMessage} message - Foundry chat message
     */
    highlightThinkingMessage(message) {
        try {
            // Find the message element
            const messageElement = $(`[data-message-id="${message.id}"]`);
            
            if (messageElement.length > 0) {
                // Add highlight animation
                messageElement.addClass('thinking-highlight');
                
                // Remove highlight after animation
                setTimeout(() => {
                    messageElement.removeClass('thinking-highlight');
                }, 3000);
            }
        } catch (error) {
            console.error("Whisper Display: Error highlighting message:", error);
        }
    }
    
    /**
     * Add message to thinking history
     * @param {ChatMessage} message - Foundry chat message
     */
    addToHistory(message) {
        try {
            const historyEntry = {
                id: message.id,
                content: message.content,
                timestamp: message.timestamp || Date.now(),
                type: 'thinking_whisper'
            };
            
            this.whisperHistory.unshift(historyEntry);
            
            // Limit history size
            if (this.whisperHistory.length > this.maxHistorySize) {
                this.whisperHistory = this.whisperHistory.slice(0, this.maxHistorySize);
            }
            
        } catch (error) {
            console.error("Whisper Display: Error adding to history:", error);
        }
    }
    
    /**
     * Get thinking whisper history
     * @param {number} limit - Maximum number of entries to return
     * @returns {Array} - Array of thinking messages
     */
    getThinkingHistory(limit = 20) {
        return this.whisperHistory.slice(0, limit);
    }
    
    /**
     * Clear thinking history
     */
    clearHistory() {
        this.whisperHistory = [];
        console.log("Whisper Display: Thinking history cleared");
    }
    
    /**
     * Enable/disable whisper display
     * @param {boolean} enabled - Whether to enable display
     */
    setDisplayEnabled(enabled) {
        this.displayEnabled = enabled;
        console.log(`Whisper Display: Display ${enabled ? 'enabled' : 'disabled'}`);
    }
    
    /**
     * Get display statistics
     * @returns {Object} - Statistics about thinking whispers
     */
    getStats() {
        return {
            totalThinkingWhispers: this.whisperHistory.length,
            isGM: this.isGM,
            displayEnabled: this.displayEnabled,
            lastWhisperTime: this.whisperHistory.length > 0 ? this.whisperHistory[0].timestamp : null
        };
    }
    
    /**
     * Create custom thinking whisper (for testing or manual use)
     * @param {string} thinkingContent - Thinking content to display
     */
    createManualThinkingWhisper(thinkingContent) {
        if (!this.isGM) {
            console.warn("Whisper Display: Only GMs can create manual thinking whispers");
            return;
        }
        
        try {
            const formattedContent = `Thinking: ${thinkingContent}`;
            
            ChatMessage.create({
                user: game.user.id,
                speaker: { alias: "AI Assistant" },
                content: formattedContent,
                whisper: game.users.contents.filter(u => u.isGM).map(u => u.id),
                type: CONST.CHAT_MESSAGE_TYPES.WHISPER
            });
            
        } catch (error) {
            console.error("Whisper Display: Error creating manual thinking whisper:", error);
        }
    }
    
    /**
     * Process thinking data from backend
     * @param {Object} thinkingData - Thinking data from backend
     */
    processBackendThinking(thinkingData) {
        if (!this.displayEnabled || !this.isGM) return;
        
        try {
            const thinking = thinkingData.thinking || thinkingData.content || '';
            const originalPrompt = thinkingData.original_prompt || '';
            
            if (thinking.trim()) {
                this.displayBackendThinking(thinking, originalPrompt);
            }
            
        } catch (error) {
            console.error("Whisper Display: Error processing backend thinking:", error);
        }
    }
    
    /**
     * Display thinking from backend
     * @param {string} thinking - Thinking content
     * @param {string} originalPrompt - Original prompt (optional)
     */
    displayBackendThinking(thinking, originalPrompt = '') {
        try {
            let displayContent = thinking;
            
            // Add prompt context if available
            if (originalPrompt) {
                displayContent = `${thinking}\n\n<small><em>Context: ${originalPrompt}</em></small>`;
            }
            
            ChatMessage.create({
                user: game.user.id,
                speaker: { alias: "AI Assistant" },
                content: displayContent,
                whisper: game.users.contents.filter(u => u.isGM).map(u => u.id),
                type: CONST.CHAT_MESSAGE_TYPES.WHISPER
            });
            
        } catch (error) {
            console.error("Whisper Display: Error displaying backend thinking:", error);
        }
    }
}

// Export for global access
window.WhisperDisplayManager = WhisperDisplayManager;

// Auto-initialize when module is ready
Hooks.once('ready', () => {
    window.WhisperDisplayManager = new WhisperDisplayManager();
});

// Add CSS for thinking whispers
Hooks.on('ready', () => {
    const style = document.createElement('style');
    style.textContent = `
        .gold-box-thinking-whisper {
            background-color: rgba(100, 100, 255, 0.1) !important;
            border-left: 4px solid #6464ff !important;
            margin: 4px 0 !important;
            padding: 8px !important;
            border-radius: 4px !important;
        }
        
        .thinking-highlight {
            animation: thinkingPulse 2s ease-in-out;
        }
        
        @keyframes thinkingPulse {
            0% { background-color: rgba(100, 100, 255, 0.1); }
            50% { background-color: rgba(100, 100, 255, 0.3); }
            100% { background-color: rgba(100, 100, 255, 0.1); }
        }
        
        .gold-box-thinking-whisper .message-header {
            color: #6464ff;
            font-weight: bold;
        }
        
        .gold-box-thinking-whisper .message-content {
            font-style: italic;
        }
    `;
    document.head.appendChild(style);
});
