"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.fileSystemRouter = void 0;
const express_1 = require("express");
const express_2 = __importDefault(require("express"));
const requestForwarder_1 = require("../../middleware/requestForwarder");
const auth_1 = require("../../middleware/auth");
const ClientManager_1 = require("../../core/ClientManager");
const shared_1 = require("../shared");
const logger_1 = require("../../utils/logger");
exports.fileSystemRouter = (0, express_1.Router)();
const commonMiddleware = [requestForwarder_1.requestForwarderMiddleware, auth_1.authMiddleware, auth_1.trackApiUsage];
/**
 * Get file system structure
 *
 * @route GET /file-system
 * @param {string} clientId - [query] The ID of the Foundry client to connect to
 * @param {string} path - [query,?] The path to retrieve (relative to source)
 * @param {string} source - [query,?] The source directory to use (data, systems, modules, etc.)
 * @param {boolean} recursive - [query,?] Whether to recursively list all subdirectories
 * @returns {object} File system structure with files and directories
 */
exports.fileSystemRouter.get("/file-system", ...commonMiddleware, async (req, res) => {
    const clientId = req.query.clientId;
    const path = req.query.path || "";
    const source = req.query.source || "data";
    const recursive = req.query.recursive === "true";
    if (!clientId) {
        (0, shared_1.safeResponse)(res, 400, {
            error: "Client ID is required",
            howToUse: "Add ?clientId=yourClientId to your request"
        });
        return;
    }
    const client = await ClientManager_1.ClientManager.getClient(clientId);
    if (!client) {
        (0, shared_1.safeResponse)(res, 404, {
            error: "Invalid client ID"
        });
        return;
    }
    try {
        const requestId = `file_system_${Date.now()}_${Math.random().toString(36).substring(2, 9)}`;
        shared_1.pendingRequests.set(requestId, {
            res,
            type: 'file-system',
            clientId,
            timestamp: Date.now()
        });
        const sent = client.send({
            type: "file-system",
            path,
            source,
            recursive,
            requestId
        });
        if (!sent) {
            shared_1.pendingRequests.delete(requestId);
            (0, shared_1.safeResponse)(res, 500, { error: "Failed to send request to Foundry client" });
            return;
        }
        setTimeout(() => {
            if (shared_1.pendingRequests.has(requestId)) {
                shared_1.pendingRequests.delete(requestId);
                (0, shared_1.safeResponse)(res, 504, { error: "Request timed out" });
            }
        }, 15000);
    }
    catch (error) {
        logger_1.log.error(`Error processing file system request: ${error}`);
        (0, shared_1.safeResponse)(res, 500, { error: "Failed to process file system request" });
        return;
    }
});
/**
 * Upload a file to Foundry's file system (handles both base64 and binary data)
 *
 * @route POST /upload
 * @param {string} clientId - [query] The ID of the Foundry client to connect to
 * @param {string} path - [query/body] The directory path to upload to
 * @param {string} filename - [query/body] The filename to save as
 * @param {string} source - [query/body,?] The source directory to use (data, systems, modules, etc.)
 * @param {string} mimeType - [query/body,?] The MIME type of the file
 * @param {boolean} overwrite - [query/body,?] Whether to overwrite an existing file
 * @param {string} fileData - [body,?] Base64 encoded file data (if sending as JSON) 250MB limit
 * @returns {object} Result of the file upload operation
 */
exports.fileSystemRouter.post("/upload", ...commonMiddleware, async (req, res) => {
    // Handle different content types
    const contentType = req.get('Content-Type') || '';
    let parsePromise;
    if (contentType.includes('application/json')) {
        // Parse as JSON with size limit
        parsePromise = new Promise((resolve, reject) => {
            express_2.default.json({ limit: '250mb' })(req, res, (err) => {
                if (err)
                    reject(err);
                else
                    resolve();
            });
        });
    }
    else {
        // Parse as raw binary data
        parsePromise = new Promise((resolve, reject) => {
            express_2.default.raw({ limit: '250mb', type: '*/*' })(req, res, (err) => {
                if (err)
                    reject(err);
                else
                    resolve();
            });
        });
    }
    try {
        await parsePromise;
    }
    catch (error) {
        (0, shared_1.safeResponse)(res, 400, {
            error: "Failed to parse request body",
            details: error instanceof Error ? error.message : String(error),
            suggestion: "Check your request size (max 250MB) and content type"
        });
        return;
    }
    const clientId = req.query.clientId;
    const path = req.query.path || req.body?.path;
    const filename = req.query.filename || req.body?.filename;
    const source = req.query.source || req.body?.source || "data";
    const mimeType = req.query.mimeType || req.body?.mimeType || "application/octet-stream";
    const overwrite = req.query.overwrite === "true" || req.body?.overwrite === "true" || req.body?.overwrite === true;
    const fileData = req.body?.fileData;
    if (!clientId) {
        (0, shared_1.safeResponse)(res, 400, {
            error: "Client ID is required",
            howToUse: "Add ?clientId=yourClientId to your request"
        });
        return;
    }
    if (!path || !filename) {
        (0, shared_1.safeResponse)(res, 400, {
            error: "Required parameters missing",
            requiredParams: "path, filename",
            howToUse: "Add ?path=your/path&filename=your-file.png to your request"
        });
        return;
    }
    const client = await ClientManager_1.ClientManager.getClient(clientId);
    if (!client) {
        (0, shared_1.safeResponse)(res, 404, {
            error: "Invalid client ID"
        });
        return;
    }
    try {
        let binaryData = null;
        let processedFileData = null;
        // Handle different types of file data
        if (fileData) {
            // Handle base64 data from JSON body
            const base64Match = fileData.match(/^data:([A-Za-z-+\/]+);base64,(.+)$/);
            if (!base64Match) {
                (0, shared_1.safeResponse)(res, 400, {
                    error: "Invalid file data format",
                    expected: "Base64 encoded data URL (e.g., data:image/png;base64,...)",
                    received: fileData.substring(0, 50) + "..."
                });
                return;
            }
            // Validate base64 data
            try {
                const base64Data = base64Match[2];
                const buffer = Buffer.from(base64Data, 'base64');
                if (buffer.length === 0) {
                    throw new Error("Empty file data");
                }
                processedFileData = fileData;
                logger_1.log.info(`Processing base64 file data: ${buffer.length} bytes`);
            }
            catch (error) {
                (0, shared_1.safeResponse)(res, 400, {
                    error: "Invalid base64 data",
                    details: error instanceof Error ? error.message : String(error)
                });
                return;
            }
        }
        else if (contentType.includes('application/octet-stream') || !contentType.includes('application/json')) {
            // Handle binary data from raw body
            if (Buffer.isBuffer(req.body) && req.body.length > 0) {
                binaryData = Array.from(req.body);
                logger_1.log.info(`Processing binary file data: ${req.body.length} bytes`);
            }
            else {
                (0, shared_1.safeResponse)(res, 400, {
                    error: "No file data received",
                    tip: "Send binary file data with Content-Type: application/octet-stream, or JSON with base64 fileData field",
                    contentType: contentType
                });
                return;
            }
        }
        else {
            (0, shared_1.safeResponse)(res, 400, {
                error: "No file data provided",
                howToProvide: [
                    "Option 1: Send JSON with fileData field containing base64 data URL",
                    "Option 2: Send binary data with Content-Type: application/octet-stream"
                ]
            });
            return;
        }
        // Generate a unique requestId
        const requestId = `upload_file_${Date.now()}_${Math.random().toString(36).substring(2, 9)}`;
        shared_1.pendingRequests.set(requestId, {
            res,
            type: 'upload-file',
            clientId,
            timestamp: Date.now()
        });
        const payload = {
            type: "upload-file",
            path,
            filename,
            source: source || "data",
            overwrite: overwrite || false,
            requestId
        };
        if (processedFileData) {
            payload.fileData = processedFileData;
            payload.mimeType = mimeType;
        }
        else if (binaryData) {
            payload.binaryData = binaryData;
            payload.mimeType = mimeType;
        }
        else {
            shared_1.pendingRequests.delete(requestId);
            (0, shared_1.safeResponse)(res, 400, {
                error: "No valid file data to send",
                debug: { hasFileData: !!processedFileData, hasBinaryData: !!binaryData }
            });
            return;
        }
        logger_1.log.info(`Sending upload request: ${JSON.stringify({
            requestId,
            path,
            filename,
            source,
            hasFileData: !!processedFileData,
            hasBinaryData: !!binaryData,
            payloadSize: processedFileData ? processedFileData.length : (binaryData ? binaryData.length : 0)
        })}`);
        const sent = client.send(payload);
        if (!sent) {
            shared_1.pendingRequests.delete(requestId);
            (0, shared_1.safeResponse)(res, 500, { error: "Failed to send request to Foundry client" });
            return;
        }
        // Set timeout for request - file uploads may take longer
        setTimeout(() => {
            if (shared_1.pendingRequests.has(requestId)) {
                shared_1.pendingRequests.delete(requestId);
                (0, shared_1.safeResponse)(res, 504, {
                    error: "File upload request timed out",
                    suggestion: "Try uploading a smaller file or check your connection to Foundry"
                });
            }
        }, 30000); // 30 second timeout for uploads
    }
    catch (error) {
        logger_1.log.error(`Error processing file upload request: ${error}`);
        if (error instanceof Error) {
            logger_1.log.error(`Upload error stack: ${error.stack}`);
        }
        (0, shared_1.safeResponse)(res, 500, {
            error: "Failed to process file upload request",
            details: error instanceof Error ? error.message : String(error)
        });
        return;
    }
});
/**
 * Download a file from Foundry's file system
 *
 * @route GET /download
 * @param {string} clientId - [query] The ID of the Foundry client to connect to
 * @param {string} path - [query] The full path to the file to download
 * @param {string} source - [query,?] The source directory to use (data, systems, modules, etc.)
 * @param {string} format - [query,?] The format to return the file in (binary, base64)
 * @returns {binary|object} File contents in the requested format
 */
exports.fileSystemRouter.get("/download", ...commonMiddleware, async (req, res) => {
    const clientId = req.query.clientId;
    const path = req.query.path;
    const source = req.query.source || "data";
    const format = req.query.format || "binary"; // Default to binary format for downloads
    if (!clientId) {
        (0, shared_1.safeResponse)(res, 400, {
            error: "Client ID is required",
            howToUse: "Add ?clientId=yourClientId to your request"
        });
        return;
    }
    if (!path) {
        (0, shared_1.safeResponse)(res, 400, {
            error: "Path parameter is required",
            howToUse: "Add &path=yourFilePath to your request"
        });
        return;
    }
    const client = await ClientManager_1.ClientManager.getClient(clientId);
    if (!client) {
        (0, shared_1.safeResponse)(res, 404, {
            error: "Invalid client ID"
        });
        return;
    }
    try {
        // Generate a unique requestId
        const requestId = `download_file_${Date.now()}_${Math.random().toString(36).substring(2, 9)}`;
        shared_1.pendingRequests.set(requestId, {
            res,
            type: 'download-file',
            clientId,
            format, // Store the requested format in the pending request
            timestamp: Date.now()
        });
        const sent = client.send({
            type: "download-file",
            path,
            source,
            requestId
        });
        if (!sent) {
            shared_1.pendingRequests.delete(requestId);
            (0, shared_1.safeResponse)(res, 500, { error: "Failed to send request to Foundry client" });
            return;
        }
        // Set timeout for request
        setTimeout(() => {
            if (shared_1.pendingRequests.has(requestId)) {
                shared_1.pendingRequests.delete(requestId);
                (0, shared_1.safeResponse)(res, 504, { error: "File download request timed out" });
            }
        }, 45000); // 45 second timeout for downloads
    }
    catch (error) {
        logger_1.log.error(`Error processing file download request: ${error}`);
        (0, shared_1.safeResponse)(res, 500, { error: "Failed to process file download request" });
        return;
    }
});
