"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.utilityRouter = void 0;
exports.validateScript = validateScript;
const express_1 = require("express");
const express_2 = __importDefault(require("express"));
const path_1 = __importDefault(require("path"));
const promises_1 = __importDefault(require("fs/promises"));
const multer_1 = __importDefault(require("multer"));
const stream_1 = require("stream");
const requestForwarder_1 = require("../../middleware/requestForwarder");
const auth_1 = require("../../middleware/auth");
const route_helpers_1 = require("../route-helpers");
const shared_1 = require("../shared");
const logger_1 = require("../../utils/logger");
const upload = (0, multer_1.default)({ dest: "uploads/" });
// Define a safe directory for uploads
const SAFE_UPLOAD_DIR = path_1.default.resolve("uploads");
exports.utilityRouter = (0, express_1.Router)();
const commonMiddleware = [requestForwarder_1.requestForwarderMiddleware, auth_1.authMiddleware, auth_1.trackApiUsage, express_2.default.json()];
function validateScript(script) {
    // Disallow dangerous patterns
    const forbiddenPatterns = [
        /localStorage/,
        /sessionStorage/,
        /document\.cookie/,
        /eval\(/,
        /new Worker\(/,
        /new SharedWorker\(/,
        /__proto__/,
        /atob\(/,
        /btoa\(/,
        /crypto\./,
        /Intl\./,
        /postMessage\(/,
        /XMLHttpRequest/,
        /importScripts\(/,
        /apiKey/,
        /privateKey/,
        /password/,
    ];
    return !forbiddenPatterns.some((pattern) => pattern.test(script));
}
// Middleware to handle `application/javascript` content type
async function handleJavaScriptFile(req, res, next) {
    if (req.is("application/javascript")) {
        try {
            // Generate a safe file path
            const tempFileName = `script_${Date.now()}.js`;
            const tempFilePath = path_1.default.join(SAFE_UPLOAD_DIR, tempFileName);
            // Ensure the resolved path is within the safe directory
            if (!tempFilePath.startsWith(SAFE_UPLOAD_DIR)) {
                throw new Error("Invalid file path");
            }
            function validateFileExtension(filePath) {
                const allowedExtensions = [".js"];
                const ext = path_1.default.extname(filePath).toLowerCase();
                return allowedExtensions.includes(ext);
            }
            if (!validateFileExtension(tempFilePath)) {
                throw new Error("Invalid file extension");
            }
            const chunks = [];
            req.on("data", (chunk) => chunks.push(chunk));
            req.on("end", async () => {
                const fileBuffer = Buffer.concat(chunks);
                await promises_1.default.writeFile(tempFilePath, fileBuffer);
                req.file = {
                    path: tempFilePath,
                    fieldname: "file",
                    originalname: "script.js",
                    encoding: "7bit",
                    mimetype: "application/javascript",
                    size: fileBuffer.length,
                    destination: "uploads/",
                    filename: path_1.default.basename(tempFilePath),
                    stream: new stream_1.PassThrough().end(fileBuffer),
                    buffer: fileBuffer
                }; // Simulate multer's `req.file`
                next();
            });
        }
        catch (error) {
            logger_1.log.error(`Error handling JavaScript file upload: ${error}`);
            (0, shared_1.safeResponse)(res, 500, { error: "Failed to process JavaScript file" });
        }
    }
    else {
        next();
    }
}
/**
 * Select token(s)
 *
 * Selects one or more tokens in the Foundry VTT client.
 *
 * @route POST /select
 * @returns {object} The selected token(s)
 */
exports.utilityRouter.post("/select", ...commonMiddleware, (0, route_helpers_1.createApiRoute)({
    type: 'select',
    requiredParams: [
        { name: 'clientId', from: 'query', type: 'string' } // Client ID for the Foundry world
    ],
    optionalParams: [
        { name: 'uuids', from: 'body', type: 'array' }, // Array of UUIDs to select
        { name: 'name', from: 'body', type: 'string' }, // Name of the token(s) to select
        { name: 'data', from: 'body', type: 'object' }, // Data to match for selection (e.g., "data.attributes.hp.value": 20)
        { name: 'overwrite', from: 'body', type: 'boolean' }, // Whether to overwrite existing selection
        { name: 'all', from: 'body', type: 'boolean' } // Whether to select all tokens on the canvas
    ],
    validateParams: (params) => {
        if (!params.uuids?.length && !params.name && !params.data) {
            return {
                error: "Either uuids array, name, or data is required",
                howToUse: "Provide uuids, name, or data parameters"
            };
        }
        return null;
    }
}));
/**
 * Get selected token(s)
 *
 * Retrieves the currently selected token(s) in the Foundry VTT client.
 *
 * @route GET /selected
 * @returns {object} The selected token(s)
 */
exports.utilityRouter.get("/selected", ...commonMiddleware, (0, route_helpers_1.createApiRoute)({
    type: 'selected',
    requiredParams: [
        { name: 'clientId', from: 'query', type: 'string' } // Client ID for the Foundry world
    ]
}));
/**
 * Execute JavaScript
 *
 * Executes a JavaScript script in the Foundry VTT client.
 *
 * @route POST /execute-js
 * @returns {object} The result of the executed script
 */
exports.utilityRouter.post("/execute-js", ...commonMiddleware, upload.single("scriptFile"), handleJavaScriptFile, (0, route_helpers_1.createApiRoute)({
    type: 'execute-js',
    requiredParams: [
        { name: 'clientId', from: 'query', type: 'string' } // Client ID for the Foundry world
    ],
    optionalParams: [
        { name: 'script', from: 'body', type: 'string' } // JavaScript script to execute
    ],
    validateParams: (params, req) => {
        if (!params.script && !req.file) {
            return {
                error: "A JavaScript script or scriptFile is required"
            };
        }
        if (params.script && !validateScript(params.script)) {
            logger_1.log.warn(`Request for ${params.clientId} contains forbidden patterns`);
            return {
                error: "Script contains forbidden patterns"
            };
        }
        return null;
    },
    buildPayload: async (params, req) => {
        let script = params.script;
        // Handle file upload if present
        if (req.file) {
            const filePath = req.file.path;
            script = await promises_1.default.readFile(filePath, "utf-8");
            await promises_1.default.unlink(filePath); // Clean up uploaded file
        }
        return {
            script
        };
    }
}));
