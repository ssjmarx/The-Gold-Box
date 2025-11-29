"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.createApiRoute = createApiRoute;
const ClientManager_1 = require("../core/ClientManager");
const shared_1 = require("./shared");
const logger_1 = require("../utils/logger");
/**
 * Creates a standardized Express route handler for API endpoints.
 * This function abstracts away the boilerplate of handling client lookups,
 * request tracking, and timeouts.
 *
 * @param config - The configuration for the API route.
 * @returns An Express route handler function.
 */
function createApiRoute(config) {
    return async (req, res) => {
        // Extract parameters from request body, query or path params
        const params = {};
        const allParamDefs = [...(config.requiredParams || []), ...(config.optionalParams || [])];
        for (const p of allParamDefs) {
            const sources = Array.isArray(p.from) ? p.from : [p.from];
            let value;
            for (const source of sources) {
                value = req[source]?.[p.name];
                if (value !== undefined) {
                    break;
                }
            }
            params[p.name] = value;
        }
        // Type validation and coercion
        for (const p of allParamDefs) {
            let value = params[p.name];
            if (value === undefined || value === null)
                continue;
            if (p.type) {
                let coercedValue = value;
                let validationError = null;
                switch (p.type) {
                    case 'number':
                        if (typeof value !== 'number') {
                            coercedValue = parseFloat(value);
                        }
                        if (isNaN(coercedValue)) {
                            validationError = `'${p.name}' must be a valid number.`;
                        }
                        break;
                    case 'boolean':
                        if (typeof value !== 'boolean') {
                            if (String(value).toLowerCase() === 'true')
                                coercedValue = true;
                            else if (String(value).toLowerCase() === 'false')
                                coercedValue = false;
                            else
                                validationError = `'${p.name}' must be a valid boolean.`;
                        }
                        break;
                    case 'array':
                        if (!Array.isArray(value)) {
                            // Try to parse as array if it's a string from query params
                            try {
                                if (typeof value === 'string') {
                                    coercedValue = JSON.parse(value);
                                    if (!Array.isArray(coercedValue)) {
                                        validationError = `'${p.name}' must be an array.`;
                                    }
                                }
                                else {
                                    validationError = `'${p.name}' must be an array.`;
                                }
                            }
                            catch (e) {
                                validationError = `'${p.name}' must be a valid array.`;
                            }
                        }
                        break;
                    case 'string':
                        if (typeof value !== 'string')
                            validationError = `'${p.name}' must be a string.`;
                        break;
                    case 'object':
                        if (typeof value !== 'object' || Array.isArray(value))
                            validationError = `'${p.name}' must be an object.`;
                        break;
                }
                if (validationError) {
                    return (0, shared_1.safeResponse)(res, 400, { error: validationError });
                }
                params[p.name] = coercedValue;
            }
        }
        // Validate parameters
        const validationResult = (await config.validateParams?.(params, req)) || null;
        if (validationResult) {
            return (0, shared_1.safeResponse)(res, 400, validationResult);
        }
        // Validate that all required parameters are present
        for (const p of config.requiredParams || []) {
            if (params[p.name] === undefined || params[p.name] === null) {
                return (0, shared_1.safeResponse)(res, 400, { error: `'${p.name}' is required` });
            }
        }
        const clientId = params.clientId;
        // Get client instance
        const client = await ClientManager_1.ClientManager.getClient(clientId);
        if (!client) {
            return (0, shared_1.safeResponse)(res, 404, { error: "Invalid client ID" });
        }
        try {
            const requestId = `${config.type}_${Date.now()}`;
            // Register pending request
            const pendingRequestData = {
                res,
                type: config.type,
                clientId,
                timestamp: Date.now(),
                ...(config.buildPendingRequest ? config.buildPendingRequest(params) : {}),
            };
            shared_1.pendingRequests.set(requestId, pendingRequestData);
            // Build the payload for the client
            const payloadSource = config.buildPayload
                ? await config.buildPayload(params, req)
                : params;
            const { clientId: _clientId, type: userDefinedType, ...payload } = payloadSource;
            // Debug logging to track what's being sent to Foundry client
            console.log("=== RELAY SENDING TO FOUNDRY ===");
            console.log("Type:", config.type);
            console.log("Request ID:", requestId);
            console.log("Payload:", JSON.stringify(payload, null, 2));
            logger_1.log.info(`Sending ${config.type} request to Foundry client ${clientId}:`, payload);
            // Send message to Foundry client
            const sent = client.send({
                type: config.type,
                requestId,
                ...payload,
                data: {
                    ...payload.data,
                }
            });
            // If sending fails, clean up and respond with an error
            if (!sent) {
                shared_1.pendingRequests.delete(requestId);
                return (0, shared_1.safeResponse)(res, 500, { error: "Failed to send request to Foundry client" });
            }
            // Set a timeout for the request
            const timeoutDuration = config.timeout || 10000;
            setTimeout(() => {
                if (shared_1.pendingRequests.has(requestId)) {
                    shared_1.pendingRequests.delete(requestId);
                    (0, shared_1.safeResponse)(res, 408, { error: "Request timed out" });
                }
            }, timeoutDuration);
        }
        catch (error) {
            logger_1.log.error(`Error processing ${config.type} request:`, { error });
            (0, shared_1.safeResponse)(res, 500, { error: `Internal server error during ${config.type} request` });
        }
    };
}
