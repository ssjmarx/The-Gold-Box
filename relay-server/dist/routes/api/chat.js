"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.chatRouter = void 0;
const express_1 = require("express");
const requestForwarder_1 = require("../../middleware/requestForwarder");
const auth_1 = require("../../middleware/auth");
const route_helpers_1 = require("../route-helpers");
exports.chatRouter = (0, express_1.Router)();
const commonMiddleware = [requestForwarder_1.requestForwarderMiddleware, auth_1.authMiddleware, auth_1.trackApiUsage];
/**
 * Send a chat message to Foundry VTT
 *
 * This endpoint sends a chat message to the Foundry world's chat log.
 * Requires the Foundry module to be installed and connected to the relay server.
 *
 * @route POST /chat
 * @param {string} clientId - Client ID for the Foundry world
 * @param {object} message - The chat message to send
 * @param {string} message.message - The message content
 * @param {string} message.speaker - The name of the speaker
 * @param {string} message.type - The type of message (ic, ooc, em, etc.)
 * @returns {object} Success response with message details
 */
exports.chatRouter.post("/chat", ...commonMiddleware, (0, route_helpers_1.createApiRoute)({
    type: 'chat',
    requiredParams: [
        { name: 'clientId', from: 'body', type: 'string' }, // Client ID for the Foundry world
        { name: 'message', from: 'body', type: 'object' }, // The complete message object
        { name: 'message.message', from: 'body', type: 'string' }, // Message content
        { name: 'message.speaker', from: 'body', type: 'string' }, // Speaker name
        { name: 'message.type', from: 'body', type: 'string' } // Message type (ic, ooc, em, etc.)
    ],
    optionalParams: [
        { name: 'message.timestamp', from: 'body', type: 'number' }, // Custom timestamp (defaults to current time)
        { name: 'message.whisper', from: 'body', type: 'boolean' }, // Whether this is a whisper message
        { name: 'message.blind', from: 'body', type: 'boolean' }, // Whether this is a blind message (GM only)
        { name: 'message.roll', from: 'body', type: 'object' } // Optional roll data
    ]
}));
/**
 * Get chat messages from Foundry VTT
 *
 * This endpoint retrieves recent chat messages from the Foundry world's chat log.
 * Requires the Foundry module to be installed and connected to the relay server.
 *
 * @route GET /chat/messages
 * @returns {object} Chat messages containing content, timestamps, users, etc.
 */
exports.chatRouter.get("/messages", ...commonMiddleware, (0, route_helpers_1.createApiRoute)({
    type: 'chat-messages',
    requiredParams: [
        { name: 'clientId', from: 'query', type: 'string' } // Client ID for the Foundry world
    ],
    optionalParams: [
        { name: 'limit', from: 'query', type: 'number' }, // Maximum number of messages to return (default: 20)
        { name: 'sort', from: 'query', type: 'string' }, // Field to sort by (default: timestamp)
        { name: 'order', from: 'query', type: 'string' }, // Sort order (asc or desc, default: desc)
        { name: 'user', from: 'query', type: 'string' }, // Filter messages by specific user
        { name: 'type', from: 'query', type: 'string' } // Filter messages by type (roll, chat, ooc, etc.)
    ]
}));
exports.default = exports.chatRouter;
