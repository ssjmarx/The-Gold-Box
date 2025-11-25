"use strict";
var __createBinding = (this && this.__createBinding) || (Object.create ? (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    var desc = Object.getOwnPropertyDescriptor(m, k);
    if (!desc || ("get" in desc ? !m.__esModule : desc.writable || desc.configurable)) {
      desc = { enumerable: true, get: function() { return m[k]; } };
    }
    Object.defineProperty(o, k2, desc);
}) : (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    o[k2] = m[k];
}));
var __setModuleDefault = (this && this.__setModuleDefault) || (Object.create ? (function(o, v) {
    Object.defineProperty(o, "default", { enumerable: true, value: v });
}) : function(o, v) {
    o["default"] = v;
});
var __importStar = (this && this.__importStar) || (function () {
    var ownKeys = function(o) {
        ownKeys = Object.getOwnPropertyNames || function (o) {
            var ar = [];
            for (var k in o) if (Object.prototype.hasOwnProperty.call(o, k)) ar[ar.length] = k;
            return ar;
        };
        return ownKeys(o);
    };
    return function (mod) {
        if (mod && mod.__esModule) return mod;
        var result = {};
        if (mod != null) for (var k = ownKeys(mod), i = 0; i < k.length; i++) if (k[i] !== "default") __createBinding(result, mod, k[i]);
        __setModuleDefault(result, mod);
        return result;
    };
})();
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.sessionRouter = exports.apiKeyToSession = exports.browserSessions = void 0;
const express_1 = require("express");
const express_2 = __importDefault(require("express"));
const requestForwarder_1 = require("../../middleware/requestForwarder");
const auth_1 = require("../../middleware/auth");
const ClientManager_1 = require("../../core/ClientManager");
const shared_1 = require("../shared");
const logger_1 = require("../../utils/logger");
const crypto_1 = __importDefault(require("crypto"));
const puppeteer = __importStar(require("puppeteer"));
const redis_1 = require("../../config/redis");
const headlessSessions_1 = require("../../workers/headlessSessions");
const pendingHandshakes = new Map();
exports.browserSessions = new Map();
exports.apiKeyToSession = new Map();
const pendingHeadlessSessionsRequests = new Map();
exports.sessionRouter = (0, express_1.Router)();
const commonMiddleware = [requestForwarder_1.requestForwarderMiddleware, auth_1.authMiddleware, auth_1.trackApiUsage];
/**
 * Create a handshake token for the client to use for secure authentication
 *
 * @route POST /session-handshake
 * @param {string} x-api-key - [header] API key header
 * @param {string} x-foundry-url - [header] Foundry URL header
 * @param {string} x-world-name - [header,?] World name header
 * @param {string} x-username - [header] Username header
 * @returns {object} Handshake token and encryption details
 */
exports.sessionRouter.post('/session-handshake', auth_1.authMiddleware, async (req, res) => {
    try {
        const apiKey = req.header('x-api-key');
        const foundryUrl = req.header('x-foundry-url');
        const worldName = req.header('x-world-name');
        const username = req.header('x-username');
        if (!foundryUrl || !username) {
            res.status(400).json({ error: "Missing required parameters" });
            return;
        }
        // Generate an RSA key pair for this handshake
        const { publicKey, privateKey } = crypto_1.default.generateKeyPairSync('rsa', {
            modulusLength: 2048,
            publicKeyEncoding: {
                type: 'spki',
                format: 'pem'
            },
            privateKeyEncoding: {
                type: 'pkcs8',
                format: 'pem'
            }
        });
        // Generate a random handshake token that will be valid for 5 minutes
        const handshakeToken = crypto_1.default.randomBytes(32).toString('hex');
        const expires = Date.now() + (5 * 60 * 1000); // 5 minutes
        const nonce = crypto_1.default.randomBytes(16).toString('hex');
        const instanceId = process.env.FLY_ALLOC_ID || 'local';
        // Store handshake in Redis instead of local memory
        const redis = (0, redis_1.getRedisClient)();
        if (redis) {
            // Store all handshake data in Redis with an expiry
            await redis.hSet(`handshake:${handshakeToken}`, {
                apiKey,
                foundryUrl,
                worldName: worldName || '',
                username,
                publicKey,
                privateKey,
                nonce,
                expires: expires.toString(),
                instanceId
            });
            // Set expiry for 5 minutes
            await redis.expire(`handshake:${handshakeToken}`, 300);
            logger_1.log.info(`Created handshake token ${handshakeToken.substring(0, 8)}... for ${foundryUrl} in Redis`);
        }
        else {
            // Fallback to local storage if Redis is unavailable
            pendingHandshakes.set(handshakeToken, {
                apiKey,
                foundryUrl,
                worldName,
                username,
                publicKey,
                privateKey,
                nonce,
                expires
            });
            // Set cleanup timeout for local storage
            setTimeout(() => {
                pendingHandshakes.delete(handshakeToken);
                logger_1.log.debug(`Handshake token ${handshakeToken.substring(0, 8)}... expired and removed from local storage`);
            }, 5 * 60 * 1000);
            logger_1.log.info(`Created handshake token ${handshakeToken.substring(0, 8)}... for ${foundryUrl} in local storage`);
        }
        // Return the token and public key to the client
        res.status(200).json({
            token: handshakeToken,
            publicKey: publicKey,
            nonce,
            expires
        });
        return;
    }
    catch (error) {
        logger_1.log.error(`Error creating handshake: ${error}`);
        res.status(500).json({ error: 'Failed to create handshake' });
        return;
    }
});
/**
 * Start a headless Foundry session using puppeteer
 *
 * @route POST /start-session
 * @param {string} handshakeToken - [body] The token received from session-handshake
 * @param {string} encryptedPassword - [body] Password encrypted with the public key
 * @param {string} x-api-key - [header] API key header
 * @returns {object} Session information including sessionId and clientId
 */
exports.sessionRouter.post("/start-session", requestForwarder_1.requestForwarderMiddleware, auth_1.authMiddleware, express_2.default.json(), async (req, res) => {
    try {
        const { handshakeToken, encryptedPassword } = req.body;
        const apiKey = req.header('x-api-key');
        // Get handshake data from Redis or local storage
        let handshake = null;
        let fromRedis = false;
        const redis = (0, redis_1.getRedisClient)();
        if (redis) {
            // Try to get handshake from Redis
            const handshakeExists = await redis.exists(`handshake:${handshakeToken}`);
            if (handshakeExists) {
                const handshakeData = await redis.hGetAll(`handshake:${handshakeToken}`);
                // Check if this instance should handle the request
                const handshakeInstanceId = handshakeData.instanceId;
                const currentInstanceId = process.env.FLY_ALLOC_ID || 'local';
                if (handshakeInstanceId !== currentInstanceId) {
                    // This should be handled by a different instance
                    logger_1.log.info(`Handshake ${handshakeToken.substring(0, 8)}... belongs to instance ${handshakeInstanceId}, current instance is ${currentInstanceId}`);
                    // Store the client's request in Redis for the correct instance to pick up
                    await redis.hSet(`pending_session:${handshakeToken}`, {
                        apiKey,
                        encryptedPassword: encryptedPassword,
                        timestamp: Date.now().toString()
                    });
                    // Set expiry for 5 minutes
                    await redis.expire(`pending_session:${handshakeToken}`, 300);
                    // Wait for the other instance to process the request and return the result
                    logger_1.log.info(`Waiting for instance ${handshakeInstanceId} to process headless session request`);
                    // Set a timeout for waiting
                    const maxWaitTime = 600000; // 10 minute timeout
                    const startTime = Date.now();
                    // Poll Redis for the result
                    const checkInterval = setInterval(async () => {
                        try {
                            // Check if the result has been posted back
                            const resultKey = `session_result:${handshakeToken}`;
                            const hasResult = await redis.exists(resultKey);
                            if (hasResult) {
                                // Get the result data
                                const resultData = await redis.get(resultKey);
                                await redis.del(resultKey); // Clean up the result
                                clearInterval(checkInterval);
                                // Parse and return the actual response - handle null case with default response
                                const result = JSON.parse(resultData || '{"statusCode":200, "data":{"message":"Session started on another instance"}}');
                                return (0, shared_1.safeResponse)(res, result.statusCode || 200, result.data || {
                                    message: "Session started on another instance"
                                });
                            }
                            else if (Date.now() - startTime > maxWaitTime) {
                                // Timeout reached
                                clearInterval(checkInterval);
                                await redis.del(`pending_session:${handshakeToken}`);
                                return (0, shared_1.safeResponse)(res, 408, {
                                    error: "Timeout waiting for session to be processed by other instance",
                                    handshakeInstance: handshakeInstanceId
                                });
                            }
                        }
                        catch (err) {
                            logger_1.log.error(`Error polling for session result: ${err}`);
                            clearInterval(checkInterval);
                            return (0, shared_1.safeResponse)(res, 500, {
                                error: "Error while waiting for session to be processed"
                            });
                        }
                    }, 2000); // Check every 2 seconds
                }
                // Parse numeric fields
                handshakeData.expires = handshakeData.expires;
                handshake = handshakeData;
                fromRedis = true;
            }
        }
        // If not found in Redis, try local storage
        if (!handshake && pendingHandshakes.has(handshakeToken)) {
            handshake = pendingHandshakes.get(handshakeToken);
        }
        // Verify handshake token exists
        if (!handshake) {
            return (0, shared_1.safeResponse)(res, 401, { error: 'Invalid or expired handshake token' });
        }
        // Verify API key matches
        if (handshake.apiKey !== apiKey) {
            // Clean up
            if (fromRedis && redis) {
                await redis.del(`handshake:${handshakeToken}`);
            }
            else {
                pendingHandshakes.delete(handshakeToken);
            }
            return (0, shared_1.safeResponse)(res, 401, { error: 'Unauthorized' });
        }
        // Verify token is not expired
        if (handshake.expires < Date.now()) {
            // Clean up
            if (fromRedis && redis) {
                await redis.del(`handshake:${handshakeToken}`);
            }
            else {
                pendingHandshakes.delete(handshakeToken);
            }
            return (0, shared_1.safeResponse)(res, 401, { error: 'Handshake token expired' });
        }
        // Decrypt the password and nonce using the handshake's private key
        let password;
        let nonce;
        try {
            const buffer = Buffer.from(encryptedPassword, 'base64');
            const decryptedData = crypto_1.default.privateDecrypt({
                key: handshake.privateKey,
                padding: crypto_1.default.constants.RSA_PKCS1_OAEP_PADDING
            }, buffer).toString('utf8');
            // Parse the decrypted data as JSON which should contain password and nonce
            const parsedData = JSON.parse(decryptedData);
            password = parsedData.password;
            nonce = parsedData.nonce;
            // Verify the nonce matches
            if (!nonce || nonce !== handshake.nonce) {
                if (fromRedis && redis) {
                    await redis.del(`handshake:${handshakeToken}`);
                }
                else {
                    pendingHandshakes.delete(handshakeToken);
                }
                res.status(401).json({ error: 'Invalid nonce' });
                return;
            }
        }
        catch (error) {
            logger_1.log.error(`Failed to decrypt data: ${error}`);
            if (fromRedis && redis) {
                await redis.del(`handshake:${handshakeToken}`);
            }
            else {
                pendingHandshakes.delete(handshakeToken);
            }
            res.status(400).json({ error: 'Invalid encrypted data' });
            return;
        }
        // Remove the handshake token immediately after use
        const { foundryUrl, worldName, username } = handshake;
        // Remove the handshake token from pending handshakes
        if (fromRedis && redis) {
            await redis.del(`handshake:${handshakeToken}`);
        }
        else {
            pendingHandshakes.delete(handshakeToken);
        }
        // Launch Puppeteer and connect to Foundry
        try {
            logger_1.log.info(`Starting headless Foundry session for URL: ${foundryUrl}`);
            const browser = await puppeteer.launch({
                headless: true,
                executablePath: process.env.PUPPETEER_EXECUTABLE_PATH || undefined,
                args: [
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--enable-gpu-rasterization',
                    '--enable-oop-rasterization',
                    '--disable-dev-shm-usage',
                    '--no-first-run',
                    '--no-zygote',
                    '--disable-extensions',
                    '--disable-web-security',
                    '--disable-features=site-per-process,IsolateOrigins,site-isolation-trials',
                    '--disable-background-networking',
                    '--disable-background-timer-throttling',
                    '--disable-backgrounding-occluded-windows',
                    '--disable-renderer-backgrounding',
                    '--disable-sync',
                    '--disable-breakpad',
                    '--disable-component-extensions-with-background-pages',
                    '--disable-default-apps',
                    '--disable-infobars',
                    '--disable-popup-blocking',
                    '--disable-translate',
                    '--metrics-recording-only',
                    '--mute-audio',
                    '--log-level=0',
                    '--js-flags="--max_old_space_size=8192"',
                ],
                defaultViewport: { width: 1280, height: 720 }
            });
            const page = await browser.newPage();
            // Enable logging
            page.on('pageerror', (error) => {
                const message = error instanceof Error ? error.message : String(error);
                logger_1.log.error(`Browser page error: ${message}`);
            });
            page.on('requestfailed', (request) => logger_1.log.error(`Request failed: ${request.url()}`));
            // Navigate to Foundry
            logger_1.log.debug(`Navigating to Foundry URL: ${foundryUrl}`);
            await page.goto(foundryUrl, { waitUntil: 'networkidle0', timeout: 180000 });
            // Debug: Log current URL
            logger_1.log.debug(`Current page URL: ${page.url()}`);
            // First, check if there are any overlays or tours to dismiss
            logger_1.log.debug("Checking for overlays or tours to dismiss");
            try {
                // Look for various types of overlays and dismiss them
                const selectors = [
                    '.tour-overlay', '.tour', '.tour-fadeout',
                    'a.step-button[data-action="exit"]', 'button.tour-exit'
                ];
                for (const selector of selectors) {
                    const elements = await page.$$(selector);
                    if (elements.length > 0) {
                        logger_1.log.debug(`Found ${elements.length} ${selector} elements, attempting to dismiss`);
                        await page.click(selector).catch((e) => {
                            const message = e instanceof Error ? e.message : String(e);
                            logger_1.log.debug(`Couldn't click ${selector}: ${message}`);
                        });
                        await new Promise(resolve => setTimeout(resolve, 1000)); // Wait for a second
                    }
                }
            }
            catch (e) {
                logger_1.log.info(`Overlay handling: ${e.message}`);
            }
            // Handle world selection
            if (worldName) {
                logger_1.log.info(`Looking for world: ${worldName}`);
                try {
                    // Wait for world list to load
                    await page.waitForSelector('li.package.world', { timeout: 10000 })
                        .catch(() => {
                        logger_1.log.info('Could not find world list, checking page content');
                        return page.content().then((html) => {
                            logger_1.log.info(`Page HTML preview: ${html.substring(0, 1000)}...`);
                        });
                    });
                    // Try to find and click on the world using multiple strategies
                    logger_1.log.info('Attempting to find and launch the world');
                    // Strategy 1: Try to find the play button directly associated with the world name
                    const worldLaunched = await page.evaluate((worldName) => {
                        // Find all world titles
                        const titles = Array.from(document.querySelectorAll('h3.package-title'));
                        for (const title of titles) {
                            if (title.textContent && title.textContent.trim() === worldName) {
                                // Find the parent li element
                                const worldLi = title.closest('li.package.world');
                                if (worldLi) {
                                    // Find and click the play button
                                    const playButton = worldLi.querySelector('a.control.play');
                                    if (playButton) {
                                        playButton.click();
                                        return true;
                                    }
                                }
                            }
                        }
                        return false;
                    }, worldName);
                    await new Promise(resolve => setTimeout(resolve, 2000)); // Give time for action to complete
                    if (worldLaunched) {
                        logger_1.log.info('World launch button clicked successfully');
                    }
                    else {
                        logger_1.log.info('Failed to find/click world launch button');
                        // Strategy 2: Try using a more direct selector
                        try {
                            logger_1.log.info('Trying alternative launch approach');
                            // Look for all world elements and try to find a match by text content
                            const worlds = await page.$$('li.package.world');
                            logger_1.log.info(`Found ${worlds.length} world elements`);
                            let launched = false;
                            for (const worldElement of worlds) {
                                const title = await worldElement.$eval('h3.package-title', (el) => el.textContent?.trim())
                                    .catch(() => null);
                                logger_1.log.info(`Found world with title: ${title}`);
                                if (title === worldName) {
                                    logger_1.log.info('Found matching world, looking for play button');
                                    const playButton = await worldElement.$('a.control.play');
                                    if (playButton) {
                                        logger_1.log.info('Clicking play button');
                                        await playButton.click();
                                        launched = true;
                                        break;
                                    }
                                }
                            }
                            if (!launched) {
                                logger_1.log.info('Failed to launch world using alternative approach');
                            }
                        }
                        catch (error) {
                            logger_1.log.info(`Error in alternative launch approach: ${error.message}`);
                        }
                    }
                    // Wait and check if we have navigated to a login page
                    logger_1.log.info('Waiting to see if we reached the login page...');
                    await new Promise(resolve => setTimeout(resolve, 6000));
                    // info: Log current URL again
                    logger_1.log.info(`Current URL after world selection: ${page.url()}`);
                    // Check if we're on a login page by looking for various login elements
                    const loginElements = ['select[name="userid"]', 'input[name="userid"]', 'input[name="password"]'];
                    let loginFormFound = false;
                    for (const selector of loginElements) {
                        const element = await page.$(selector);
                        if (element) {
                            logger_1.log.info(`Found login element: ${selector}`);
                            loginFormFound = true;
                            break;
                        }
                    }
                    if (!loginFormFound) {
                        // If we don't see login elements, check the HTML to see what page we're on
                        const html = await page.content();
                        logger_1.log.info(`Page HTML after world selection (preview): ${html.substring(0, 500)}...`);
                        throw new Error('Login form not found after world selection');
                    }
                }
                catch (error) {
                    await browser.close();
                    const errorMessage = error instanceof Error ? error.message : String(error);
                    pendingHeadlessSessionsRequests.delete(apiKey);
                    return (0, shared_1.safeResponse)(res, 404, { error: `Failed to find or launch world: ${worldName}`, details: errorMessage });
                }
            }
            // Handle the login process
            logger_1.log.debug('Attempting to log in...');
            // Handle username input (could be select or input)
            let userId = username; // Default
            let userSelectFound = false;
            let retries = 0;
            const maxRetries = 10;
            const retryInterval = 10000; // 10 seconds between retries
            while (!userSelectFound && retries < maxRetries) {
                const hasUserSelect = await page.$('select[name="userid"]')
                    .then((element) => !!element)
                    .catch(() => false);
                if (hasUserSelect) {
                    logger_1.log.debug('Found username dropdown, selecting user');
                    userSelectFound = true;
                    // Get all available users from dropdown
                    const options = await page.$$eval('select[name="userid"] option', (options) => options.map((opt) => ({ value: opt.value, text: opt.textContent?.trim() })));
                    logger_1.log.debug(`Available users: ${JSON.stringify(options)}`);
                    // Find matching username
                    const matchingOption = options.find((opt) => opt.text === username);
                    if (matchingOption) {
                        logger_1.log.info(`Selected user ${username} with value ${matchingOption.value}`);
                        await page.select('select[name="userid"]', matchingOption.value);
                        userId = matchingOption.value; // Use the value attribute as userId
                    }
                    else {
                        throw new Error(`Username "${username}" not found in dropdown`);
                    }
                }
                else {
                    retries++;
                    logger_1.log.info(`No username dropdown found yet. Attempt ${retries}/${maxRetries}, checking again in ${retryInterval / 1000} seconds...`);
                    if (retries < maxRetries) {
                        await new Promise(resolve => setTimeout(resolve, retryInterval));
                    }
                    else {
                        logger_1.log.info('Max retries reached. Assuming direct username input is required.');
                        // Try to input username directly if there's an input field
                        const hasUserInput = await page.$('input[name="userid"]')
                            .then((element) => !!element)
                            .catch(() => false);
                        if (hasUserInput) {
                            logger_1.log.info(`Found username input field, entering username: ${username}`);
                            await page.type('input[name="userid"]', username);
                        }
                        else {
                            logger_1.log.warn('No username input field found after retries');
                        }
                    }
                }
            }
            // Enter password
            await page.type('input[name="password"]', password);
            // Submit form
            logger_1.log.info('Submitting login form');
            await page.click('button[type="submit"]')
                .catch(() => page.evaluate(() => {
                document.querySelector('form')?.submit();
            }));
            // Wait for the game to load
            logger_1.log.info('Waiting for game to load...');
            await page.waitForSelector('#ui-left, #sidebar, .vtt, #game', { timeout: 30000 })
                .catch(async (error) => {
                const message = error instanceof Error ? error.message : String(error);
                logger_1.log.error(`Error waiting for game selectors: ${message}`);
                throw error;
            });
            // Create a unique session ID and store it
            const sessionId = crypto_1.default.randomUUID();
            exports.browserSessions.set(sessionId, browser);
            // Register this session in Redis for cross-instance support
            await (0, headlessSessions_1.registerHeadlessSession)(sessionId, userId, apiKey);
            // The expected client ID will be in format "foundry-{userId}"
            const expectedClientId = `foundry-${userId}`;
            logger_1.log.info(`Waiting for Foundry client connection with ID: ${expectedClientId}`);
            // Create a promise that resolves when the client connects or rejects on timeout
            const clientConnectionPromise = new Promise((resolve, reject) => {
                // Initial check for existing client
                const checkExistingClient = async () => {
                    const client = await ClientManager_1.ClientManager.getClient(expectedClientId);
                    if (client && client.getApiKey() === apiKey) {
                        return expectedClientId;
                    }
                    else if (client) {
                        // If the client ID matches but the API key doesn't, log a warning
                        logger_1.log.warn(`Client ID ${expectedClientId} found but API key mismatch`);
                        return 'invalid';
                    }
                    return null;
                };
                // Set up polling for client connection with reduced verbosity
                let logCounter = 0;
                const checkInterval = setInterval(async () => {
                    try {
                        const clientId = await checkExistingClient();
                        if (clientId) {
                            // Only log the connection once
                            if (clientId === 'invalid') {
                                // close the browser session
                                await browser.close();
                                exports.browserSessions.delete(sessionId);
                                clearInterval(checkInterval);
                                clearTimeout(timeoutId);
                                reject(new Error(`Unauthorized client connection attempt`));
                                return;
                            }
                            logger_1.log.info(`Client connected successfully: ${clientId}`);
                            clearInterval(checkInterval);
                            clearTimeout(timeoutId);
                            resolve(clientId);
                        }
                        else {
                            // Log less frequently to reduce noise
                            if (++logCounter % 10 === 0) {
                                logger_1.log.debug(`Waiting for client connection: ${expectedClientId} (${logCounter} checks)`);
                            }
                        }
                    }
                    catch (error) {
                        logger_1.log.error(`Error checking for client: ${error}`);
                    }
                }, 2000);
                // Set timeout for client connection
                const timeoutId = setTimeout(() => {
                    clearInterval(checkInterval);
                    reject(new Error(`Timeout waiting for client connection: ${expectedClientId}`));
                }, 300000); // Wait up to 5 minutes for the client to connect
            });
            try {
                // Wait for client connection
                const connectedClientId = await clientConnectionPromise;
                // Store the session in our API key mapping
                exports.apiKeyToSession.set(apiKey, {
                    sessionId,
                    clientId: connectedClientId,
                    lastActivity: Date.now()
                });
                // Return success with the session ID and client ID
                pendingHeadlessSessionsRequests.delete(apiKey);
                return (0, shared_1.safeResponse)(res, 200, {
                    success: true,
                    message: "Foundry session started successfully",
                    sessionId,
                    clientId: connectedClientId
                });
            }
            catch (error) {
                // Close the browser if client connection times out
                await browser.close();
                exports.browserSessions.delete(sessionId);
                const errorMessage = error instanceof Error ? error.message : String(error);
                pendingHeadlessSessionsRequests.delete(apiKey);
                return (0, shared_1.safeResponse)(res, 408, {
                    error: "Client connection timeout",
                    details: errorMessage,
                    message: "Foundry client failed to connect to the API within the timeout period"
                });
            }
        }
        catch (error) {
            logger_1.log.error(`Error starting headless Foundry session: ${error}`);
            const errorMessage = error instanceof Error ? error.message : String(error);
            return (0, shared_1.safeResponse)(res, 500, { error: "Failed to start headless Foundry session", details: errorMessage });
        }
    }
    catch (error) {
        logger_1.log.error(`Error in start-session handler: ${error}`);
        return (0, shared_1.safeResponse)(res, 500, { error: "Internal server error" });
    }
});
/**
 * Stop a headless Foundry session
 *
 * @route DELETE /end-session
 * @param {string} sessionId - [query] The ID of the session to end
 * @param {string} x-api-key - [header] API key header
 * @returns {object} Status of the operation
 */
exports.sessionRouter.delete("/end-session", requestForwarder_1.requestForwarderMiddleware, auth_1.authMiddleware, async (req, res) => {
    try {
        const sessionId = req.query.sessionId;
        const apiKey = req.header('x-api-key');
        if (!sessionId) {
            return (0, shared_1.safeResponse)(res, 400, { error: "Session ID is required" });
        }
        // Check if we have this session locally
        const browser = exports.browserSessions.get(sessionId);
        let sessionClosed = false;
        // Try to close browser if we have it locally
        if (browser) {
            try {
                await browser.close();
                exports.browserSessions.delete(sessionId);
                sessionClosed = true;
                logger_1.log.info(`Closed browser for session ${sessionId} locally`);
            }
            catch (error) {
                logger_1.log.error(`Failed to close browser: ${error}`);
            }
        }
        // Clean up session data in Redis regardless
        try {
            const redis = (0, redis_1.getRedisClient)();
            if (redis) {
                // Get session data to find associated client
                const sessionData = await redis.hGetAll(`headless_session:${sessionId}`);
                if (sessionData && sessionData.apiKey === apiKey) {
                    // Delete all session-related keys
                    if (sessionData.clientId) {
                        await redis.del(`headless_client:${sessionData.clientId}`);
                    }
                    await redis.del(`headless_apikey:${apiKey}`);
                    await redis.del(`headless_session:${sessionId}`);
                    logger_1.log.info(`Cleaned up Redis data for session ${sessionId}`);
                    return (0, shared_1.safeResponse)(res, 200, {
                        success: true,
                        message: sessionClosed ? "Foundry session terminated" : "Foundry session data cleaned up"
                    });
                }
                else {
                    return (0, shared_1.safeResponse)(res, 403, { error: "Not authorized to terminate this session" });
                }
            }
        }
        catch (error) {
            logger_1.log.error(`Error cleaning up Redis session data: ${error}`);
        }
        // If we got here with sessionClosed true, we closed the browser but failed Redis cleanup
        if (sessionClosed) {
            return (0, shared_1.safeResponse)(res, 200, { success: true, message: "Foundry session terminated (partial cleanup)" });
        }
        return (0, shared_1.safeResponse)(res, 404, { error: "Session not found" });
    }
    catch (error) {
        logger_1.log.error(`Error in end-session handler: ${error}`);
        return (0, shared_1.safeResponse)(res, 500, { error: "Internal server error" });
    }
});
/**
 * Get all active headless Foundry sessions
 *
 * @route GET /session
 * @param {string} x-api-key - [header] API key header
 * @returns {object} List of active sessions for the current API key
 */
exports.sessionRouter.get("/session", requestForwarder_1.requestForwarderMiddleware, auth_1.authMiddleware, async (req, res) => {
    try {
        const apiKey = req.header('x-api-key');
        const redis = (0, redis_1.getRedisClient)();
        let sessions = [];
        // Try to get session data from Redis first
        if (redis) {
            // Check if this API key has a headless session in Redis - FIX: Use correct key pattern
            const sessionId = await redis.get(`headless_apikey:${apiKey}:session`);
            if (sessionId) {
                // Get full session details
                const sessionData = await redis.hGetAll(`headless_session:${sessionId}`);
                if (sessionData) {
                    // Parse timestamps
                    const lastActivity = parseInt(sessionData.lastActivity || '0');
                    sessions.push({
                        id: sessionId,
                        clientId: sessionData.clientId || '',
                        lastActivity: lastActivity,
                        idleMinutes: Math.round((Date.now() - lastActivity) / 60000),
                        instanceId: sessionData.instanceId || 'unknown'
                    });
                }
            }
        }
        // Fall back to local storage if no Redis session found
        if (sessions.length === 0) {
            const userSession = exports.apiKeyToSession.get(apiKey);
            if (userSession) {
                sessions.push({
                    id: userSession.sessionId,
                    clientId: userSession.clientId,
                    lastActivity: userSession.lastActivity,
                    idleMinutes: Math.round((Date.now() - userSession.lastActivity) / 60000),
                    instanceId: process.env.FLY_ALLOC_ID || 'local'
                });
            }
        }
        (0, shared_1.safeResponse)(res, 200, {
            activeSessions: sessions
        });
    }
    catch (error) {
        logger_1.log.error(`Error retrieving headless sessions: ${error}`);
        (0, shared_1.safeResponse)(res, 500, { error: "Failed to retrieve session data" });
    }
});
