"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.structureRouter = void 0;
const express_1 = require("express");
const requestForwarder_1 = require("../../middleware/requestForwarder");
const auth_1 = require("../../middleware/auth");
const route_helpers_1 = require("../route-helpers");
exports.structureRouter = (0, express_1.Router)();
const commonMiddleware = [requestForwarder_1.requestForwarderMiddleware, auth_1.authMiddleware, auth_1.trackApiUsage];
/**
 * Get the structure of the Foundry world
 *
 * Retrieves the folder and compendium structure for the specified Foundry world.
 *
 * @route GET /structure
 * @returns {object} The folder and compendium structure
 */
exports.structureRouter.get("/structure", ...commonMiddleware, (0, route_helpers_1.createApiRoute)({
    type: 'structure',
    requiredParams: [
        { name: 'clientId', from: 'query', type: 'string' } // Client ID for the Foundry world
    ],
    optionalParams: [
        { name: 'includeEntityData', from: 'query', type: 'boolean' }, // Whether to include full entity data or just UUIDs and names
        { name: 'path', from: 'query', type: 'string' }, // Path to read structure from (null = root)
        { name: 'recursive', from: 'query', type: 'boolean' }, // Whether to read down the folder tree
        { name: 'recursiveDepth', from: 'query', type: 'number' }, // Depth to recurse into folders (default 5)
        { name: 'types', from: 'query', type: 'string' } // Types to return (Scene/Actor/Item/JournalEntry/RollTable/Cards/Macro/Playlist), can be comma-separated or JSON array
    ],
    buildPayload: (params) => {
        // Handle types parameter - can be comma-separated string or JSON array
        if (params.types && typeof params.types === 'string') {
            try {
                // Try to parse as JSON first
                params.types = JSON.parse(params.types);
            }
            catch {
                // If not JSON, split by comma
                params.types = params.types.split(',').map((t) => t.trim());
            }
        }
        return params;
    }
}));
/**
 * This route is deprecated - use /structure with the path query parameter instead
 *
 * @route GET /contents/:path
 * @returns {object} Error message directing to use /structure endpoint
 */
exports.structureRouter.get("/contents/:path", (req, res) => {
    res.status(400).json({
        error: "This endpoint is deprecated",
        message: "Please use GET /structure with the 'path' query parameter instead",
        example: `/structure?clientId=${req.query.clientId}&path=${req.params.path}`
    });
});
/**
 * Get a specific folder by name
 *
 * @route GET /get-folder
 * @returns {object} The folder information and its contents
 */
exports.structureRouter.get("/get-folder", ...commonMiddleware, (0, route_helpers_1.createApiRoute)({
    type: 'get-folder',
    requiredParams: [
        { name: 'clientId', from: ['body', 'query'], type: 'string' }, // Client ID for the Foundry world
        { name: 'name', from: ['body', 'query'], type: 'string' } // Name of the folder to retrieve
    ]
}));
/**
 * Create a new folder
 *
 * @route POST /create-folder
 * @returns {object} The created folder information
 */
exports.structureRouter.post("/create-folder", ...commonMiddleware, (0, route_helpers_1.createApiRoute)({
    type: 'create-folder',
    requiredParams: [
        { name: 'clientId', from: ['body', 'query'], type: 'string' }, // Client ID for the Foundry world
        { name: 'name', from: ['body', 'query'], type: 'string' }, // Name of the new folder
        { name: 'folderType', from: ['body', 'query'], type: 'string' } // Type of folder (Scene, Actor, Item, JournalEntry, RollTable, Cards, Macro, Playlist)
    ],
    optionalParams: [
        { name: 'parentFolderId', from: ['body', 'query'], type: 'string' } // ID of the parent folder (optional for root level)
    ]
}));
/**
 * Delete a folder
 *
 * @route DELETE /delete-folder
 * @returns {object} Confirmation of deletion
 */
exports.structureRouter.delete("/delete-folder", ...commonMiddleware, (0, route_helpers_1.createApiRoute)({
    type: 'delete-folder',
    requiredParams: [
        { name: 'clientId', from: ['body', 'query'], type: 'string' }, // Client ID for the Foundry world
        { name: 'folderId', from: ['body', 'query'], type: 'string' } // ID of the folder to delete
    ],
    optionalParams: [
        { name: 'deleteAll', from: ['body', 'query'], type: 'boolean' } // Whether to delete all entities in the folder
    ]
}));
