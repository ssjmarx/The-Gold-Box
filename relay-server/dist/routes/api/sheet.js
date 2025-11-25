"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.sheetRouter = void 0;
const ClientManager_1 = require("../../core/ClientManager");
const express_1 = require("express");
const express_2 = __importDefault(require("express"));
const requestForwarder_1 = require("../../middleware/requestForwarder");
const auth_1 = require("../../middleware/auth");
const shared_1 = require("../shared");
const logger_1 = require("../../utils/logger");
exports.sheetRouter = (0, express_1.Router)();
const commonMiddleware = [requestForwarder_1.requestForwarderMiddleware, auth_1.authMiddleware, auth_1.trackApiUsage, express_2.default.json()];
/**
 * Get actor sheet HTML
 *
 * This endpoint retrieves the HTML for an actor sheet based on the provided UUID or selected actor. Only works on Foundry version 12.
 *
 * @route GET /sheet
 * @param {string} uuid - [query,?] The UUID of the actor to get the sheet for
 * @param {boolean} selected - [query,?] Whether to get the sheet for the selected actor
 * @param {boolean} actor - [query,?] Whether this is an actor sheet (true) or item sheet (false)
 * @param {string} clientId - [query] The ID of the Foundry client to connect to
 * @param {string} format - [query,?] The format to return the sheet in (html, json)
 * @param {number} scale - [query,?] The initial scale of the sheet
 * @param {number} tab - [query,?] The active tab index to open
 * @param {boolean} darkMode - [query,?] Whether to use dark mode for the sheet
 * @returns {object} The sheet HTML or data depending on format requested
 */
exports.sheetRouter.get("/sheet", ...commonMiddleware, async (req, res) => {
    const uuid = req.query.uuid;
    const selected = req.query.selected === 'true';
    const actor = req.query.actor === 'true';
    const clientId = req.query.clientId;
    const format = req.query.format || 'html';
    const initialScale = parseFloat(req.query.scale) || null;
    const activeTab = req.query.tab ? (isNaN(Number(req.query.tab)) ? null : Number(req.query.tab)) : null;
    const darkMode = req.query.darkMode === 'true';
    if (!clientId) {
        (0, shared_1.safeResponse)(res, 400, {
            error: "Client ID is required to identify the Foundry instance"
        });
        return;
    }
    if (!uuid && !selected) {
        (0, shared_1.safeResponse)(res, 400, { error: "UUID or selected parameter is required" });
        return;
    }
    // Find a connected client with this ID
    const client = await ClientManager_1.ClientManager.getClient(clientId);
    if (!client) {
        (0, shared_1.safeResponse)(res, 404, {
            error: "Invalid client ID"
        });
        return;
    }
    try {
        // Generate a unique requestId for this request
        const requestId = `actor_sheet_${Date.now()}_${Math.random().toString(36).substring(2, 9)}`;
        // Store the response object in a request map
        shared_1.pendingRequests.set(requestId, {
            res,
            type: 'get-sheet',
            uuid,
            clientId,
            format,
            initialScale,
            activeTab,
            darkMode,
            timestamp: Date.now()
        });
        // Send request to Foundry for actor sheet HTML
        const sent = client.send({
            type: "get-sheet",
            uuid,
            selected,
            actor,
            requestId,
            initialScale,
            activeTab,
            darkMode
        });
        if (!sent) {
            shared_1.pendingRequests.delete(requestId);
            (0, shared_1.safeResponse)(res, 500, {
                error: "Failed to send actor sheet request to Foundry client",
                suggestion: "The client may be disconnecting or experiencing issues"
            });
            return;
        }
        // Set timeout for request
        setTimeout(() => {
            if (shared_1.pendingRequests.has(requestId)) {
                shared_1.pendingRequests.delete(requestId);
                (0, shared_1.safeResponse)(res, 408, {
                    error: "Actor sheet request timed out",
                    tip: "The Foundry client might be busy or the actor UUID might not exist."
                });
            }
        }, 20000); // 20 seconds timeout
    }
    catch (error) {
        logger_1.log.error(`Error processing actor sheet request: ${error}`);
        (0, shared_1.safeResponse)(res, 500, { error: "Failed to process actor sheet request" });
        return;
    }
});
