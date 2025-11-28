"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.rollRouter = void 0;
const express_1 = require("express");
const express_2 = __importDefault(require("express"));
const requestForwarder_1 = require("../../middleware/requestForwarder");
const auth_1 = require("../../middleware/auth");
const route_helpers_1 = require("../route-helpers");
exports.rollRouter = (0, express_1.Router)();
const commonMiddleware = [requestForwarder_1.requestForwarderMiddleware, auth_1.authMiddleware, auth_1.trackApiUsage, express_2.default.json()];
/**
 * Get recent rolls
 *
 * Retrieves a list of up to 20 recent rolls made in the Foundry world.
 * Supports a 'clear' parameter to force fresh data retrieval by clearing the rolls cache.
 *
 * @route GET /rolls
 * @returns {object} An array of recent rolls with details
 */
exports.rollRouter.get("/rolls", ...commonMiddleware, (0, route_helpers_1.createApiRoute)({
    type: 'rolls',
    requiredParams: [
        { name: 'clientId', from: 'query', type: 'string' } // Client ID for the Foundry world
    ],
    optionalParams: [
        { name: 'limit', from: 'query', type: 'number' }, // Optional limit on number of rolls to return (default is 20)
        { name: 'clear', from: 'query', type: 'boolean' }, // Optional flag to clear rolls cache and get fresh data
        { name: 'refresh', from: 'query', type: 'boolean' } // Optional flag to refresh rolls data
    ],
    buildPayload: (params) => {
        const payload = {};
        if (params.limit)
            payload.limit = params.limit;
        // Add clear/refresh flags to force fresh data
        if (params.clear || params.refresh) {
            payload.clear = true;
            payload.refresh = true;
        }
        return payload;
    }
}));
/**
 * Get the last roll
 *
 * Retrieves the most recent roll made in the Foundry world.
 *
 * @route GET /lastroll
 * @returns {object} The most recent roll with details
 */
exports.rollRouter.get("/lastroll", ...commonMiddleware, (0, route_helpers_1.createApiRoute)({
    type: 'last-roll',
    requiredParams: [
        { name: 'clientId', from: 'query', type: 'string' } // Client ID for the Foundry world
    ]
}));
/**
 * Make a roll
 *
 * Executes a roll with the specified formula
 *
 * @route POST /roll
 * @returns {object} Result of the roll operation
 */
exports.rollRouter.post("/roll", ...commonMiddleware, (0, route_helpers_1.createApiRoute)({
    type: 'roll',
    requiredParams: [
        { name: 'clientId', from: 'query', type: 'string' }, // Client ID for the Foundry world
        { name: 'formula', from: 'body', type: 'string' } // The roll formula to evaluate (e.g., "1d20 + 5")
    ],
    optionalParams: [
        { name: 'flavor', from: 'body', type: 'string' }, // Optional flavor text for the roll
        { name: 'createChatMessage', from: 'body', type: 'boolean' }, // Whether to create a chat message for the roll
        { name: 'speaker', from: 'body', type: 'string' }, // The speaker for the roll
        { name: 'whisper', from: 'body', type: 'array' } // Users to whisper the roll result to
    ]
}));
