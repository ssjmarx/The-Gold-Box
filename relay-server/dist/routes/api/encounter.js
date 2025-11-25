"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.encounterRouter = void 0;
const express_1 = require("express");
const express_2 = __importDefault(require("express"));
const requestForwarder_1 = require("../../middleware/requestForwarder");
const auth_1 = require("../../middleware/auth");
const route_helpers_1 = require("../route-helpers");
exports.encounterRouter = (0, express_1.Router)();
const commonMiddleware = [requestForwarder_1.requestForwarderMiddleware, auth_1.authMiddleware, auth_1.trackApiUsage];
/**
 * Get all active encounters
 *
 * Retrieves a list of all currently active encounters in the Foundry world.
 *
 * @route GET /encounters
 * @returns {object} An array of active encounters with details
 */
exports.encounterRouter.get("/encounters", ...commonMiddleware, (0, route_helpers_1.createApiRoute)({
    type: 'encounters',
    requiredParams: [
        { name: 'clientId', from: 'query', type: 'string' } // The ID of the Foundry client to connect to
    ]
}));
/**
 * Start a new encounter
 *
 * Initiates a new encounter in the Foundry world.
 *
 * @route POST /start-encounter
 * @returns {object} Details of the started encounter
 */
exports.encounterRouter.post("/start-encounter", ...commonMiddleware, express_2.default.json(), (0, route_helpers_1.createApiRoute)({
    type: 'start-encounter',
    requiredParams: [
        { name: 'clientId', from: 'query', type: 'string' } // The ID of the Foundry client to connect to
    ],
    optionalParams: [
        { name: 'tokens', from: 'body', type: 'array' }, // Array of token UUIDs to include in the encounter
        { name: 'startWithSelected', from: 'body', type: 'boolean' }, // Whether to start with selected tokens
        { name: 'startWithPlayers', from: 'body', type: 'boolean' }, // Whether to start with players
        { name: 'rollNPC', from: 'body', type: 'boolean' }, // Whether to roll for NPCs
        { name: 'rollAll', from: 'body', type: 'boolean' }, // Whether to roll for all tokens
        { name: 'name', from: 'body', type: 'string' } // The name of the encounter (unused)
    ]
}));
/**
 * Advance to the next turn in the encounter
 *
 * Moves the encounter to the next turn.
 *
 * @route POST /next-turn
 * @returns {object} Details of the next turn
 */
exports.encounterRouter.post("/next-turn", ...commonMiddleware, express_2.default.json(), (0, route_helpers_1.createApiRoute)({
    type: 'next-turn',
    requiredParams: [
        { name: 'clientId', from: 'query', type: 'string' } // The ID of the Foundry client to connect to
    ],
    optionalParams: [
        { name: 'encounter', from: ['query', 'body'], type: 'string' } // The ID of the encounter to advance (optional, defaults to current encounter)
    ]
}));
/**
 * Advance to the next round in the encounter
 *
 * Moves the encounter to the next round.
 *
 * @route POST /next-round
 * @returns {object} Details of the next round
 */
exports.encounterRouter.post("/next-round", ...commonMiddleware, express_2.default.json(), (0, route_helpers_1.createApiRoute)({
    type: 'next-round',
    requiredParams: [
        { name: 'clientId', from: 'query', type: 'string' } // The ID of the Foundry client to connect to
    ],
    optionalParams: [
        { name: 'encounter', from: ['query', 'body'], type: 'string' } // The ID of the encounter to advance (optional, defaults to current encounter)
    ]
}));
/**
 * Advance to the last turn in the encounter
 *
 * Moves the encounter to the last turn.
 *
 * @route POST /last-turn
 * @returns {object} Details of the last turn
 */
exports.encounterRouter.post("/last-turn", ...commonMiddleware, express_2.default.json(), (0, route_helpers_1.createApiRoute)({
    type: 'last-turn',
    requiredParams: [
        { name: 'clientId', from: 'query', type: 'string' } // The ID of the Foundry client to connect to
    ],
    optionalParams: [
        { name: 'encounter', from: ['query', 'body'], type: 'string' } // The ID of the encounter to advance (optional, defaults to current encounter)
    ]
}));
/**
 * Advance to the last round in the encounter
 *
 * Moves the encounter to the last round.
 *
 * @route POST /last-round
 * @returns {object} Details of the last round
 */
exports.encounterRouter.post("/last-round", ...commonMiddleware, express_2.default.json(), (0, route_helpers_1.createApiRoute)({
    type: 'last-round',
    requiredParams: [
        { name: 'clientId', from: 'query', type: 'string' } // The ID of the Foundry client to connect to
    ],
    optionalParams: [
        { name: 'encounter', from: ['query', 'body'], type: 'string' } // The ID of the encounter to advance (optional, defaults to current encounter)
    ]
}));
/**
 * End an encounter
 *
 * Ends the current encounter in the Foundry world.
 *
 * @route POST /end-encounter
 * @returns {object} Details of the ended encounter
 */
exports.encounterRouter.post("/end-encounter", ...commonMiddleware, express_2.default.json(), (0, route_helpers_1.createApiRoute)({
    type: 'end-encounter',
    requiredParams: [
        { name: 'clientId', from: 'query', type: 'string' } // The ID of the Foundry client to connect to
    ],
    optionalParams: [
        { name: 'encounter', from: ['query', 'body'], type: 'string' } // The ID of the encounter to end (optional, defaults to current encounter)
    ]
}));
/**
 * Add tokens to an encounter
 *
 * Adds selected tokens or specified UUIDs to the current encounter.
 *
 * @route POST /add-to-encounter
 * @returns {object} Details of the updated encounter
 */
exports.encounterRouter.post("/add-to-encounter", ...commonMiddleware, express_2.default.json(), (0, route_helpers_1.createApiRoute)({
    type: 'add-to-encounter',
    requiredParams: [
        { name: 'clientId', from: 'query', type: 'string' } // The ID of the Foundry client to connect to
    ],
    optionalParams: [
        { name: 'encounter', from: ['query', 'body'], type: 'string' }, // The ID of the encounter to add tokens to (optional, defaults to current encounter)
        { name: 'selected', from: 'body', type: 'boolean' }, // Whether to add selected tokens (optional, defaults to false)
        { name: 'uuids', from: 'body', type: 'array' }, // The UUIDs of the tokens to add (optional, defaults to empty array)
        { name: 'rollInitiative', from: 'body', type: 'boolean' } // Whether to roll initiative for the added tokens (optional, defaults to false)
    ]
}));
/**
 * Remove tokens from an encounter
 *
 * Removes selected tokens or specified UUIDs from the current encounter.
 *
 * @route POST /remove-from-encounter
 * @returns {object} Details of the updated encounter
 */
exports.encounterRouter.post("/remove-from-encounter", ...commonMiddleware, express_2.default.json(), (0, route_helpers_1.createApiRoute)({
    type: 'remove-from-encounter',
    requiredParams: [
        { name: 'clientId', from: 'query', type: 'string' } // The ID of the Foundry client to connect to 
    ],
    optionalParams: [
        { name: 'encounter', from: ['query', 'body'], type: 'string' }, // The ID of the encounter to remove tokens from (optional, defaults to current encounter)
        { name: 'selected', from: 'body', type: 'boolean' }, // Whether to remove selected tokens (optional, defaults to false)
        { name: 'uuids', from: 'body', type: 'array' } // The UUIDs of the tokens to remove (optional, defaults to empty array)
    ]
}));
