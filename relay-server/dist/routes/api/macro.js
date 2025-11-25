"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.macroRouter = void 0;
const express_1 = require("express");
const requestForwarder_1 = require("../../middleware/requestForwarder");
const auth_1 = require("../../middleware/auth");
const route_helpers_1 = require("../route-helpers");
exports.macroRouter = (0, express_1.Router)();
const commonMiddleware = [requestForwarder_1.requestForwarderMiddleware, auth_1.authMiddleware, auth_1.trackApiUsage];
/**
 * Get all macros
 *
 * Retrieves a list of all macros available in the Foundry world.
 *
 * @route GET /macros
 * @returns {object} An array of macros with details
 */
exports.macroRouter.get("/macros", ...commonMiddleware, (0, route_helpers_1.createApiRoute)({
    type: 'macros',
    requiredParams: [
        { name: 'clientId', from: 'query', type: 'string' } // The ID of the Foundry client to connect to
    ]
}));
/**
 * Execute a macro by UUID
 *
 * Executes a specific macro in the Foundry world by its UUID.
 *
 * @route POST /macro/:uuid/execute
 * @returns {object} Result of the macro execution
 */
exports.macroRouter.post("/macro/:uuid/execute", ...commonMiddleware, (0, route_helpers_1.createApiRoute)({
    type: 'macro-execute',
    requiredParams: [
        { name: 'clientId', from: 'query', type: 'string' }, // The ID of the Foundry client to connect to
        { name: 'uuid', from: 'params', type: 'string' } // UUID of the macro to execute
    ],
    optionalParams: [
        { name: 'args', from: 'body', type: 'object' } // Optional arguments to pass to the macro execution
    ]
}));
