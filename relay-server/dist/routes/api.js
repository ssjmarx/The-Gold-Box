"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.apiRoutes = exports.VERSION = exports.apiKeyToSession = exports.browserSessions = void 0;
const express_1 = __importDefault(require("express"));
const path_1 = __importDefault(require("path"));
// import { log } from "../middleware/logger";
const ClientManager_1 = require("../core/ClientManager");
const axios_1 = __importDefault(require("axios"));
const jsdom_1 = require("jsdom");
const auth_1 = require("../middleware/auth");
const requestForwarder_1 = require("../middleware/requestForwarder");
const shared_1 = require("./shared");
const dnd5e_1 = require("./api/dnd5e");
const health_1 = require("../routes/health");
const redis_1 = require("../config/redis");
const htmlResponseTemplate_1 = require("../config/htmlResponseTemplate");
const promises_1 = __importDefault(require("fs/promises"));
const search_1 = require("./api/search");
const entity_1 = require("./api/entity");
const roll_1 = require("./api/roll");
const utility_1 = require("./api/utility");
const fileSystem_1 = require("./api/fileSystem");
const session_1 = require("./api/session");
const encounter_1 = require("./api/encounter");
const sheet_1 = require("./api/sheet");
const macro_1 = require("./api/macro");
const structure_1 = require("./api/structure");
const chat_1 = require("./api/chat");
const logger_1 = require("../utils/logger");
exports.browserSessions = new Map();
exports.apiKeyToSession = new Map();
exports.VERSION = '2.0.16';
const INSTANCE_ID = process.env.INSTANCE_ID || 'default';
const HEADLESS_SESSION_TIMEOUT = 10 * 60 * 1000; // 10 minutes in milliseconds
function cleanupInactiveSessions() {
    const now = Date.now();
    for (const [apiKey, session] of exports.apiKeyToSession.entries()) {
        if (now - session.lastActivity > HEADLESS_SESSION_TIMEOUT) {
            logger_1.log.info(`Closing inactive headless session ${session.sessionId} for API key ${apiKey.substring(0, 8)}... (inactive for ${Math.round((now - session.lastActivity) / 60000)} minutes)`);
            try {
                // Close browser if it exists
                if (exports.browserSessions.has(session.sessionId)) {
                    const browser = exports.browserSessions.get(session.sessionId);
                    browser?.close().catch(err => logger_1.log.error(`Error closing browser: ${err}`));
                    exports.browserSessions.delete(session.sessionId);
                }
                // Clean up the session mapping
                exports.apiKeyToSession.delete(apiKey);
            }
            catch (error) {
                logger_1.log.error(`Error during inactive session cleanup: ${error}`);
            }
        }
    }
}
// Start the session cleanup interval when module is loaded
setInterval(cleanupInactiveSessions, 60000); // Check every minute
const apiRoutes = (app) => {
    // Setup handlers for storing search results and entity data from WebSocket
    setupMessageHandlers();
    // Create a router instead of using app directly
    const router = express_1.default.Router();
    // Define routes on router
    router.get("/", (req, res) => {
        res.sendFile(path_1.default.join(__dirname, "../../_test/test-client.html"));
    });
    router.get("/health", health_1.healthCheck);
    router.get("/api/status", (req, res) => {
        res.json({
            status: "ok",
            version: exports.VERSION,
            websocket: "/relay"
        });
    });
    // Get all connected clients
    router.get("/clients", auth_1.authMiddleware, async (req, res) => {
        try {
            const apiKey = req.header('x-api-key') || '';
            const redis = (0, redis_1.getRedisClient)();
            // Array to store all client details
            let allClients = [];
            if (redis) {
                // Step 1: Get all client IDs from Redis for this API key
                const clientIds = await redis.sMembers(`apikey:${apiKey}:clients`);
                if (clientIds.length > 0) {
                    // Step 2: For each client ID, get details from Redis
                    const clientDetailsPromises = clientIds.map(async (clientId) => {
                        try {
                            // Get the instance this client is connected to
                            const instanceId = await redis.get(`client:${clientId}:instance`);
                            if (!instanceId)
                                return null;
                            // Get the last seen timestamp if stored
                            const lastSeen = await redis.get(`client:${clientId}:lastSeen`) || Date.now();
                            const connectedSince = await redis.get(`client:${clientId}:connectedSince`) || lastSeen;
                            // Return client details including its instance
                            return {
                                id: clientId,
                                instanceId,
                                lastSeen: parseInt(lastSeen.toString()),
                                connectedSince: parseInt(connectedSince.toString()),
                                worldId: await redis.get(`client:${clientId}:worldId`) || '',
                                worldTitle: await redis.get(`client:${clientId}:worldTitle`) || '',
                                foundryVersion: await redis.get(`client:${clientId}:foundryVersion`) || '',
                                systemId: await redis.get(`client:${clientId}:systemId`) || '',
                                systemTitle: await redis.get(`client:${clientId}:systemTitle`) || '',
                                systemVersion: await redis.get(`client:${clientId}:systemVersion`) || '',
                                customName: await redis.get(`client:${clientId}:customName`) || ''
                            };
                        }
                        catch (err) {
                            logger_1.log.error(`Error getting details for client ${clientId}: ${err}`);
                            return null;
                        }
                    });
                    // Resolve all promises and filter out nulls
                    const clientDetails = (await Promise.all(clientDetailsPromises)).filter(client => client !== null);
                    allClients = clientDetails;
                }
            }
            else {
                // Fallback to local clients if Redis isn't available
                const localClientIds = await ClientManager_1.ClientManager.getConnectedClients(apiKey);
                // Use Promise.all to wait for all getClient calls to complete
                allClients = await Promise.all(localClientIds.map(async (id) => {
                    const client = await ClientManager_1.ClientManager.getClient(id);
                    return {
                        id,
                        instanceId: INSTANCE_ID,
                        lastSeen: client?.getLastSeen() || Date.now(),
                        connectedSince: client?.getLastSeen() || Date.now(),
                        worldId: client?.getWorldId() || '',
                        worldTitle: client?.getWorldTitle() || '',
                        foundryVersion: client?.getFoundryVersion() || '',
                        systemId: client?.getSystemId() || '',
                        systemTitle: client?.getSystemTitle() || '',
                        systemVersion: client?.getSystemVersion() || '',
                        customName: client?.getCustomName() || ''
                    };
                }));
            }
            // Send combined response
            (0, shared_1.safeResponse)(res, 200, {
                total: allClients.length,
                clients: allClients
            });
        }
        catch (error) {
            logger_1.log.error(`Error aggregating clients: ${error}`);
            (0, shared_1.safeResponse)(res, 500, { error: "Failed to retrieve clients" });
        }
    });
    // Proxy asset requests to Foundry
    router.get('/proxy-asset/:path(*)', requestForwarder_1.requestForwarderMiddleware, async (req, res) => {
        try {
            // Get Foundry URL from client metadata or use default
            const clientId = req.query.clientId;
            let foundryBaseUrl = 'http://localhost:30000'; // Default Foundry URL
            // If we have client info, use its URL
            if (clientId) {
                const client = await ClientManager_1.ClientManager.getClient(clientId);
                if (client && 'metadata' in client && client.metadata && client.metadata.origin) {
                    foundryBaseUrl = client.metadata.origin;
                }
            }
            const assetPath = req.params.path;
            const assetUrl = `${foundryBaseUrl}/${assetPath}`;
            logger_1.log.debug(`Proxying asset request to: ${assetUrl}`);
            // Check if it's a Font Awesome file - redirect to CDN if so
            if (assetPath.includes('/webfonts/fa-') || assetPath.includes('/fonts/fontawesome/') ||
                assetPath.includes('/fonts/fa-')) {
                // Extract the filename
                const filename = assetPath.split('/').pop() || '';
                // Redirect to CDN
                const cdnUrl = `https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.2/webfonts/${filename}`;
                logger_1.log.debug(`Redirecting Font Awesome asset to CDN: ${cdnUrl}`);
                res.redirect(cdnUrl);
                return;
            }
            // Handle The Forge specific assets
            if (assetPath.includes('forgevtt-module.css') || assetPath.includes('forge-vtt.com')) {
                logger_1.log.debug(`Skipping The Forge asset: ${assetPath}`);
                // Return an empty CSS file for Forge assets to prevent errors
                if (assetPath.endsWith('.css')) {
                    res.type('text/css').send('/* Placeholder for The Forge CSS */');
                    return;
                }
                else if (assetPath.endsWith('.js')) {
                    res.type('application/javascript').send('// Placeholder for The Forge JS');
                    return;
                }
                else {
                    // Return a transparent 1x1 pixel for images
                    res.type('image/png').send(Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII=', 'base64'));
                    return;
                }
            }
            // Check for texture files - use GitHub raw content as fallback
            if (assetPath.includes('texture1.webp') || assetPath.includes('texture2.webp') ||
                assetPath.includes('parchment.jpg')) {
                logger_1.log.debug(`Serving texture file from GitHub fallback`);
                res.redirect('https://raw.githubusercontent.com/foundryvtt/dnd5e/master/ui/parchment.jpg');
                return;
            }
            // Additional asset fallbacks...
            // Try to make the request to Foundry with better error handling
            try {
                const response = await (0, axios_1.default)({
                    method: 'get',
                    url: assetUrl,
                    responseType: 'stream',
                    timeout: 30000, // Increased timeout to 30s
                    maxRedirects: 5,
                    validateStatus: (status) => status < 500 // Only treat 500+ errors as errors
                });
                // Copy headers
                Object.keys(response.headers).forEach(header => {
                    res.setHeader(header, response.headers[header]);
                });
                // Set CORS headers
                res.setHeader('Access-Control-Allow-Origin', '*');
                // Stream the response
                response.data.pipe(res);
            }
            catch (error) {
                logger_1.log.error(`Request failed: ${assetUrl}`);
                // For CSS files, return an empty CSS file
                if (assetPath.endsWith('.css')) {
                    res.type('text/css').send('/* CSS not available */');
                }
                else if (assetPath.endsWith('.js')) {
                    res.type('application/javascript').send('// JavaScript not available');
                }
                else {
                    // Return a transparent 1x1 pixel for images and other files
                    res.type('image/png').send(Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII=', 'base64'));
                }
            }
        }
        catch (error) {
            logger_1.log.error(`Error in proxy asset handler: ${error}`);
            res.status(404).send('Asset not found');
        }
    });
    // API Documentation endpoint - returns all available endpoints with their documentation
    router.get("/api/docs", async (req, res) => {
        try {
            // Try multiple possible paths for the API docs file
            const possiblePaths = [
                path_1.default.resolve(__dirname, '../../../public/api-docs.json'), // Development path
                path_1.default.resolve(__dirname, '../../public/api-docs.json'), // Alternative path
                path_1.default.resolve(process.cwd(), 'public/api-docs.json'), // Production path from app root
                path_1.default.resolve(process.cwd(), 'dist/public/api-docs.json'), // If public is copied to dist
            ];
            let docsContent = null;
            let usedPath = null;
            // Try each path until we find the file
            for (const docsPath of possiblePaths) {
                try {
                    docsContent = await promises_1.default.readFile(docsPath, 'utf8');
                    usedPath = docsPath;
                    break;
                }
                catch (err) {
                    // File not found at this path, try next one
                    logger_1.log.debug(`API docs not found at: ${docsPath}`);
                }
            }
            if (!docsContent) {
                throw new Error(`API docs file not found at any of the expected paths: ${possiblePaths.join(', ')}`);
            }
            logger_1.log.debug(`Successfully loaded API docs from: ${usedPath}`);
            const apiDocs = JSON.parse(docsContent);
            // Dynamically set the baseUrl
            apiDocs.baseUrl = `${req.protocol}://${req.get('host')}`;
            res.json(apiDocs);
        }
        catch (error) {
            logger_1.log.error('Failed to load API documentation:', {
                error: error instanceof Error ? error.message : String(error),
                cwd: process.cwd(),
                __dirname: __dirname
            });
            // Provide a basic fallback response
            res.status(500).json({
                error: 'API documentation is currently unavailable.',
                message: 'The documentation file could not be loaded. Please check if the server was built correctly.',
                baseUrl: `${req.protocol}://${req.get('host')}`
            });
        }
    });
    // Mount the router
    app.use("/", router);
    app.use('/', search_1.searchRouter);
    app.use('/', entity_1.entityRouter);
    app.use('/', roll_1.rollRouter);
    app.use('/', utility_1.utilityRouter);
    app.use('/', fileSystem_1.fileSystemRouter);
    app.use('/', session_1.sessionRouter);
    app.use('/', encounter_1.encounterRouter);
    app.use('/', sheet_1.sheetRouter);
    app.use('/', macro_1.macroRouter);
    app.use('/', structure_1.structureRouter);
    app.use('/', chat_1.chatRouter);
    app.use('/dnd5e', dnd5e_1.dnd5eRouter);
};
exports.apiRoutes = apiRoutes;
const REQUEST_TYPES_WITH_SPECIAL_RESPONSE_HANDLERS = [
    'actor-sheet', 'download-file'
];
// Setup WebSocket message handlers to route responses back to API requests
function setupMessageHandlers() {
    for (const type of shared_1.PENDING_REQUEST_TYPES) {
        if (REQUEST_TYPES_WITH_SPECIAL_RESPONSE_HANDLERS.includes(type)) {
            continue;
        }
        ClientManager_1.ClientManager.onMessageType(`${type}-result`, (client, data) => {
            logger_1.log.info(`Received ${type} response for requestId: ${data.requestId}`);
            if (data.requestId && shared_1.pendingRequests.has(data.requestId)) {
                const pending = shared_1.pendingRequests.get(data.requestId);
                if (!pending) {
                    logger_1.log.warn(`Pending request ${data.requestId} was deleted before processing`);
                    return;
                }
                const response = {
                    requestId: data.requestId,
                    clientId: pending.clientId || client.getId()
                };
                for (const [key, value] of Object.entries(data)) {
                    if (key !== 'requestId') {
                        response[key] = value;
                    }
                }
                if (response.error) {
                    (0, shared_1.safeResponse)(pending.res, 400, response);
                }
                else {
                    (0, shared_1.safeResponse)(pending.res, 200, response);
                }
                shared_1.pendingRequests.delete(data.requestId);
                return;
            }
        });
    }
    // Handler for actor sheet HTML response
    ClientManager_1.ClientManager.onMessageType("get-sheet-response", (client, data) => {
        logger_1.log.info(`Received actor sheet HTML response for requestId: ${data.requestId}`);
        try {
            // Extract the UUID from either data.uuid or data.data.uuid
            const responseUuid = data.uuid || (data.data && data.data.uuid);
            // Debug what we're receiving
            logger_1.log.debug(`Actor sheet response data structure:`, {
                requestId: data.requestId,
                uuid: responseUuid,
                dataKeys: data.data ? Object.keys(data.data) : [],
                html: data.data && data.data.html ? `${data.data.html.substring(0, 100)}...` : undefined,
                cssLength: data.data && data.data.css ? data.data.css.length : 0
            });
            if (data.requestId && shared_1.pendingRequests.has(data.requestId)) {
                const pending = shared_1.pendingRequests.get(data.requestId);
                // Compare with either location
                if (pending.type === 'get-sheet' && pending.uuid === responseUuid) {
                    if (data.error || (data.data && data.data.error)) {
                        const errorMsg = data.error || (data.data && data.data.error) || "Unknown error";
                        (0, shared_1.safeResponse)(pending.res, 404, {
                            requestId: data.requestId,
                            clientId: pending.clientId,
                            uuid: pending.uuid,
                            error: errorMsg
                        });
                    }
                    else {
                        // Get HTML content from either data or data.data
                        let html = data.html || (data.data && data.data.html) || '';
                        const css = data.css || (data.data && data.data.css) || '';
                        // Get the system ID for use in HTML output
                        const gameSystemId = client.metadata?.systemId || 'unknown';
                        if (pending.format === 'json') {
                            // Send response as JSON
                            (0, shared_1.safeResponse)(pending.res, 200, {
                                requestId: data.requestId,
                                clientId: pending.clientId,
                                uuid: pending.uuid,
                                html: html,
                                css: css
                            });
                        }
                        else {
                            // Get the scale and tab parameters from pending request
                            const initialScale = pending.initialScale || null;
                            // Convert activeTab to a number if it exists, or keep as null
                            const activeTabIndex = pending.activeTab !== null ? Number(pending.activeTab) : null;
                            // If a specific tab index is requested, pre-process HTML to activate that tab
                            if (activeTabIndex !== null && !isNaN(activeTabIndex)) {
                                try {
                                    // Create a virtual DOM to manipulate HTML
                                    const dom = new jsdom_1.JSDOM(html);
                                    const document = dom.window.document;
                                    // Find all tab navigation elements
                                    const tabsElements = document.querySelectorAll('nav.tabs, .tabs');
                                    tabsElements.forEach(tabsElement => {
                                        // Find all tab items and content tabs
                                        const tabs = Array.from(tabsElement.querySelectorAll('.item'));
                                        const sheet = tabsElement.closest('.sheet');
                                        if (sheet && tabs.length > 0 && activeTabIndex < tabs.length) {
                                            const tabContent = sheet.querySelectorAll('.tab');
                                            if (tabs.length > 0 && tabContent.length > 0) {
                                                // Deactivate all tabs first
                                                tabs.forEach(tab => tab.classList.remove('active'));
                                                tabContent.forEach(content => content.classList.remove('active'));
                                                // Get the tab at the specified index
                                                const targetTab = tabs[activeTabIndex];
                                                if (targetTab) {
                                                    // Get the data-tab attribute from this tab
                                                    const tabName = targetTab.getAttribute('data-tab');
                                                    // Find the corresponding content tab
                                                    let targetContent = null;
                                                    for (let i = 0; i < tabContent.length; i++) {
                                                        if (tabContent[i].getAttribute('data-tab') === tabName) {
                                                            targetContent = tabContent[i];
                                                            break;
                                                        }
                                                    }
                                                    // Activate both the tab and its content
                                                    targetTab.classList.add('active');
                                                    if (targetContent) {
                                                        targetContent.classList.add('active');
                                                        logger_1.log.debug(`Pre-activated tab index ${activeTabIndex} with data-tab: ${tabName}`);
                                                    }
                                                }
                                            }
                                        }
                                    });
                                    // Get the modified HTML
                                    html = document.querySelector('body')?.innerHTML || html;
                                }
                                catch (error) {
                                    logger_1.log.warn(`Failed to pre-process HTML for tab selection: ${error}`);
                                    // Continue with the original HTML if there was an error
                                }
                            }
                            // If dark mode is requested, flag it for later use in the full HTML document
                            const darkModeEnabled = pending.darkMode || false;
                            // Determine if we should include interactive JavaScript
                            const includeInteractiveJS = initialScale === null && activeTabIndex === null;
                            // Generate the full HTML document
                            const fullHtml = (0, htmlResponseTemplate_1.returnHtmlTemplate)(responseUuid, html, css, gameSystemId, darkModeEnabled, includeInteractiveJS, activeTabIndex || 0, initialScale || 0, pending);
                            pending.res.send(fullHtml);
                        }
                    }
                    // Remove pending request
                    shared_1.pendingRequests.delete(data.requestId);
                }
                else {
                    // Log an issue if UUID doesn't match what we expect
                    logger_1.log.warn(`Received actor sheet response with mismatched values: expected type=${pending.type}, uuid=${pending.uuid}, got uuid=${responseUuid}`);
                }
            }
            else {
                logger_1.log.warn(`Received actor sheet response for unknown requestId: ${data.requestId}`);
            }
        }
        catch (error) {
            logger_1.log.error(`Error handling actor sheet HTML response:`, { error });
            logger_1.log.debug(`Response data that caused error:`, {
                requestId: data.requestId,
                hasData: !!data.data,
                dataType: typeof data.data
            });
        }
    });
    // Handler for file download result
    ClientManager_1.ClientManager.onMessageType("download-file-result", (client, data) => {
        logger_1.log.info(`Received file download result for requestId: ${data.requestId}`);
        if (data.requestId && shared_1.pendingRequests.has(data.requestId)) {
            const request = shared_1.pendingRequests.get(data.requestId);
            shared_1.pendingRequests.delete(data.requestId);
            if (data.error) {
                (0, shared_1.safeResponse)(request.res, 500, {
                    clientId: client.getId(),
                    requestId: data.requestId,
                    error: data.error
                });
                return;
            }
            // Check if the client wants raw binary data or JSON response
            const format = request.format || 'binary'; // Default to binary format
            if (format === 'binary' || format === 'raw') {
                // Extract the base64 data and send as binary
                const base64Data = data.fileData.split(',')[1];
                const buffer = Buffer.from(base64Data, 'base64');
                // Set the appropriate content type
                request.res.setHeader('Content-Type', data.mimeType || 'application/octet-stream');
                request.res.setHeader('Content-Disposition', `attachment; filename="${data.filename}"`);
                request.res.setHeader('Content-Length', buffer.length);
                // Send the binary data
                request.res.status(200).end(buffer);
            }
            else {
                // Send JSON response with file data
                (0, shared_1.safeResponse)(request.res, 200, {
                    clientId: client.getId(),
                    requestId: data.requestId,
                    success: true,
                    path: data.path,
                    filename: data.filename,
                    mimeType: data.mimeType,
                    fileData: data.fileData,
                    size: Buffer.from(data.fileData.split(',')[1], 'base64').length
                });
            }
        }
    });
    // Clean up old pending requests periodically
    setInterval(() => {
        const now = Date.now();
        for (const [requestId, request] of shared_1.pendingRequests.entries()) {
            // Remove requests older than 30 seconds
            if (now - request.timestamp > 30000) {
                logger_1.log.warn(`Request ${requestId} timed out and was never completed`);
                shared_1.pendingRequests.delete(requestId);
            }
        }
    }, 10000);
}
