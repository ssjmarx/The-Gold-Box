"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.pendingRequests = exports.PENDING_REQUEST_TYPES = void 0;
exports.safeResponse = safeResponse;
const logger_1 = require("../utils/logger");
// Extracted from api.ts
function sanitizeResponse(response) {
    if (response === null || response === undefined) {
        return response;
    }
    if (typeof response !== 'object') {
        return response;
    }
    // Custom deep clone and key removal
    function removeSensitiveKeys(obj) {
        if (obj === null || typeof obj !== 'object') {
            return obj;
        }
        if (Array.isArray(obj)) {
            return obj.map(item => removeSensitiveKeys(item));
        }
        const newObj = {};
        for (const key in obj) {
            if (key !== 'privateKey' && key !== 'apiKey' && key !== 'password') {
                newObj[key] = removeSensitiveKeys(obj[key]);
            }
        }
        return newObj;
    }
    return removeSensitiveKeys(response);
}
function safeResponse(res, statusCode, data) {
    if (res.headersSent) {
        logger_1.log.warn(`Headers already sent for request. Cannot send response:`, data);
        return;
    }
    const sanitizedData = sanitizeResponse(data);
    res.status(statusCode).json(sanitizedData);
}
exports.PENDING_REQUEST_TYPES = [
    'search', 'entity', 'structure', 'contents', 'create', 'update', 'delete',
    'rolls', 'last-roll', 'roll', 'get-sheet', 'macro-execute', 'macros',
    'encounters', 'start-encounter', 'next-turn', 'next-round', 'last-turn', 'last-round',
    'end-encounter', 'add-to-encounter', 'remove-from-encounter', 'kill', 'decrease', 'increase', 'give', 'remove', 'execute-js',
    'select', 'selected', 'file-system', 'upload-file', 'download-file',
    'get-actor-details', 'modify-item-charges', 'use-ability', 'use-feature', 'use-spell', 'use-item', 'modify-experience', 'add-item', 'remove-item',
    'get-folder', 'create-folder', 'delete-folder', 'chat-messages', 'chat'
];
exports.pendingRequests = new Map();
