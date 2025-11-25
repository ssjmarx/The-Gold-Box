"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.searchRouter = void 0;
const express_1 = require("express");
const requestForwarder_1 = require("../../middleware/requestForwarder");
const auth_1 = require("../../middleware/auth");
const route_helpers_1 = require("../route-helpers");
exports.searchRouter = (0, express_1.Router)();
const commonMiddleware = [requestForwarder_1.requestForwarderMiddleware, auth_1.authMiddleware, auth_1.trackApiUsage];
/**
 * Search entities
 *
 * This endpoint allows searching for entities in the Foundry world based on a query string.
 * Requires Quick Insert module to be installed and enabled.
 *
 * @route GET /search
 * @returns {object} Search results containing matching entities
 */
exports.searchRouter.get("/search", ...commonMiddleware, (0, route_helpers_1.createApiRoute)({
    type: 'search',
    requiredParams: [
        { name: 'clientId', from: 'query', type: 'string' }, // Client ID for the Foundry world
        { name: 'query', from: 'query', type: 'string' } // Search query string
    ],
    optionalParams: [
        { name: 'filter', from: 'query', type: 'string' } // Filter to apply (simple: filter="Actor", property-based: filter="key:value,key2:value2")
    ]
}));
