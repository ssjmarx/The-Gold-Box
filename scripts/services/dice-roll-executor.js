/**
 * The Gold Box - Dice Roll Executor
 * Handles dice roll requests from backend and executes them via Foundry's native API
 */

class DiceRollExecutor {
    /**
     * Initialize Dice Roll Executor
     */
    constructor() {
        this.handlers = {
            'execute_roll': this.handleExecuteRoll.bind(this)
        };
        console.log('DiceRollExecutor initialized');
    }

    /**
     * Get message handlers for WebSocket
     * @returns {Object} Map of message type to handler function
     */
    getMessageHandlers() {
        return this.handlers;
    }

    /**
     * Handle execute_roll message from backend
     * @param {Object} message - The execute_roll message
     * @param {Object} message.data - Message data containing rolls
     * @param {string} message.request_id - Request ID for correlation
     */
    async handleExecuteRoll(message) {
        const { data, request_id } = message;
        const { rolls } = data;

        console.log(`DiceRollExecutor: Received execute_roll request (request_id: ${request_id}, rolls: ${rolls.length})`);

        const results = [];

        try {
            // Execute each roll
            for (let i = 0; i < rolls.length; i++) {
                const roll = rolls[i];
                const { formula, flavor } = roll;

                console.log(`DiceRollExecutor: Executing roll ${i + 1}/${rolls.length}: ${formula}${flavor ? ` (${flavor})` : ''}`);

                try {
                    const result = await this.executeRoll(formula, flavor);
                    results.push({
                        formula: formula,
                        flavor: flavor || '',
                        result: result.total,
                        details: result,
                        success: true
                    });
                } catch (error) {
                    console.error(`DiceRollExecutor: Failed to execute roll ${formula}:`, error);
                    results.push({
                        formula: formula,
                        flavor: flavor || '',
                        result: null,
                        details: { error: error.message },
                        success: false,
                        error: error.message
                    });
                }
            }

            // Send results back to backend
            this.sendRollResult(request_id, results);
            console.log(`DiceRollExecutor: Sent ${results.length} roll results for request ${request_id}`);

        } catch (error) {
            console.error('DiceRollExecutor: Error handling execute_roll:', error);
            // Send error result
            this.sendRollResult(request_id, [{
                formula: 'unknown',
                flavor: '',
                result: null,
                details: { error: error.message },
                success: false,
                error: error.message
            }]);
        }
    }

    /**
     * Execute a single dice roll using Foundry's native API
     * @param {string} formula - Dice formula (e.g., '1d20+5', '2d6')
     * @param {string} flavor - Optional flavor text
     * @returns {Promise<Object>} Roll result object
     */
    async executeRoll(formula, flavor = '') {
        try {
            // Use Foundry's Roll class to execute roll
            const roll = new Roll(formula);

            // Evaluate roll asynchronously (required for some dice formulas)
            await roll.evaluate();
            
            // Get roll details
            const result = {
                formula: formula,
                total: roll.total,
                dice: roll.dice.map(die => ({
                    number: die.number,
                    results: die.results.map(r => ({
                        result: r.result,
                        active: r.active,
                        discarded: r.discarded
                    }))
                })),
                modifiers: roll.modifiers,
                parts: roll.parts
            };

            // Show roll in the chat
            try {
                await roll.toMessage({
                    flavor: flavor,
                    speaker: ChatMessage.getSpeaker(),
                    flags: {
                        'gold-box': {
                            automated: true
                        }
                    }
                });
                
                // CRITICAL FIX: Also send roll data via message collector for immediate backend sync
                // This ensures dice rolls are available for get_message_history in same session
                if (window.goldBox && window.goldBox.messageCollector) {
                    window.goldBox.messageCollector.sendDiceRoll({
                        formula: formula,
                        total: roll.total,
                        results: roll.dice.map(d => ({
                            number: d.number,
                            results: d.results.map(r => ({
                                result: r.result,
                                active: r.active,
                                discarded: r.discarded
                            }))
                        })),
                        flavor: flavor || '',
                        timestamp: Date.now()
                    });
                    console.log('DiceRollExecutor: Roll data sent via message collector');
                }
            } catch (err) {
                console.error('DiceRollExecutor: Error sending roll to chat:', err);
                // Continue anyway - roll was evaluated successfully
            }

            console.log(`DiceRollExecutor: Roll executed: ${formula} = ${roll.total}`);
            return result;

        } catch (error) {
            console.error('DiceRollExecutor: Error executing roll:', error);
            throw error;
        }
    }

    /**
     * Send roll result back to backend via WebSocket
     * @param {string} requestId - Request ID
     * @param {Array} results - Array of roll results
     */
    sendRollResult(requestId, results) {
        const message = {
            type: 'roll_result',
            request_id: requestId,
            data: {
                results: results,
                timestamp: new Date().toISOString()
            }
        };

        // Send via WebSocket client instance from goldBox
        if (window.goldBox && window.goldBox.webSocketClient) {
            window.goldBox.webSocketClient.send(message)
                .catch(error => {
                    console.error('DiceRollExecutor: Failed to send roll result:', error);
                });
        } else {
            console.error('DiceRollExecutor: WebSocket client not available (window.goldBox.webSocketClient)');
        }
    }
}

// Export for global access in other scripts
window.DiceRollExecutor = DiceRollExecutor;
