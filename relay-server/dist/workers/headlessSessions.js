"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.browserSessions = void 0;
exports.isHeadlessClient = isHeadlessClient;
exports.getHeadlessClientId = getHeadlessClientId;
exports.registerHeadlessSession = registerHeadlessSession;
exports.validateHeadlessSession = validateHeadlessSession;
exports.getSessionForClient = getSessionForClient;
exports.checkPendingHeadlessSessions = checkPendingHeadlessSessions;
exports.scheduleHeadlessSessionsCheck = scheduleHeadlessSessionsCheck;
const logger_1 = require("../utils/logger");
const redis_1 = require("../config/redis");
// Store active browser sessions locally
exports.browserSessions = new Map(); // Using 'any' for puppeteer.Browser
// Check if a client ID is from a headless session
function isHeadlessClient(clientId) {
    return clientId.startsWith('foundry-');
}
// Generate consistent client IDs for headless sessions
function getHeadlessClientId(userId) {
    return `foundry-${userId}`;
}
// Track pending headless sessions
async function registerHeadlessSession(sessionId, userId, apiKey) {
    const redis = (0, redis_1.getRedisClient)();
    if (!redis)
        return;
    const clientId = getHeadlessClientId(userId);
    const instanceId = process.env.FLY_ALLOC_ID || 'local';
    try {
        // Store the session mapping
        await redis.hSet(`headless_session:${sessionId}`, {
            clientId,
            apiKey,
            instanceId,
            created: Date.now()
        });
        // Set expiration (3 hours)
        await redis.expire(`headless_session:${sessionId}`, 10800);
        // Store reverse lookup from clientId to sessionId
        await redis.set(`headless_client:${clientId}`, sessionId);
        await redis.expire(`headless_client:${clientId}`, 10800);
        // Store apiKey to instanceId mapping - CRITICAL FOR REQUEST FORWARDING
        await redis.set(`apikey:${apiKey}:instance`, instanceId);
        await redis.expire(`apikey:${apiKey}:instance`, 10800);
        // Also store client to instance mapping for socket lookups
        await redis.set(`client:${clientId}:instance`, instanceId);
        await redis.expire(`client:${clientId}:instance`, 10800);
        logger_1.log.info(`Registered headless session ${sessionId} for client ${clientId} on instance ${instanceId}`);
    }
    catch (error) {
        logger_1.log.error(`Failed to register headless session: ${error}`);
    }
}
// Validate client connections - MODIFIED TO HANDLE INSTANCE MIGRATIONS
async function validateHeadlessSession(clientId, token) {
    // Skip non-headless clients
    if (!isHeadlessClient(clientId)) {
        return true;
    }
    try {
        const redis = (0, redis_1.getRedisClient)();
        if (!redis)
            return true; // Allow if Redis is not available
        // Get the session ID for this client
        const sessionId = await redis.get(`headless_client:${clientId}`);
        if (!sessionId) {
            logger_1.log.warn(`No session found for headless client ${clientId}`);
            return true; // Allow connection but log warning
        }
        // Get session data
        const sessionData = await redis.hGetAll(`headless_session:${sessionId}`);
        if (!sessionData || !sessionData.apiKey) {
            logger_1.log.warn(`Session data not found for session ${sessionId}`);
            return true;
        }
        // Check if API key matches
        if (sessionData.apiKey !== token) {
            logger_1.log.warn(`API key mismatch for headless client ${clientId}`);
            return false; // Reject the connection
        }
        // Update the instance ID in case client connects to a different instance
        const currentInstanceId = process.env.FLY_ALLOC_ID || 'local';
        // Always update the instance location when validating a session
        await redis.hSet(`headless_session:${sessionId}`, "instanceId", currentInstanceId);
        await redis.set(`client:${clientId}:instance`, currentInstanceId);
        await redis.set(`apikey:${sessionData.apiKey}:instance`, currentInstanceId);
        // Touch all keys to refresh TTL
        await redis.expire(`headless_session:${sessionId}`, 10800);
        await redis.expire(`headless_client:${clientId}`, 10800);
        await redis.expire(`apikey:${sessionData.apiKey}:instance`, 10800);
        await redis.expire(`client:${clientId}:instance`, 10800);
        logger_1.log.info(`Headless client ${clientId} validated successfully`);
        return true;
    }
    catch (error) {
        logger_1.log.error(`Error validating headless session: ${error}`);
        return true; // Allow connection on error to avoid blocking legitimate connections
    }
}
// Get session ID from client ID
async function getSessionForClient(clientId) {
    try {
        const redis = (0, redis_1.getRedisClient)();
        if (!redis)
            return null;
        return await redis.get(`headless_client:${clientId}`);
    }
    catch (error) {
        logger_1.log.error(`Error getting session for client: ${error}`);
        return null;
    }
}
// Process pending session requests that were forwarded from other instances
async function checkPendingHeadlessSessions() {
    try {
        const redis = (0, redis_1.getRedisClient)();
        if (!redis)
            return;
        const instanceId = process.env.FLY_ALLOC_ID || 'local';
        // Find all handshakes that belong to this instance
        const handshakeKeys = await redis.keys('handshake:*');
        for (const key of handshakeKeys) {
            const handshakeData = await redis.hGetAll(key);
            if (handshakeData.instanceId === instanceId) {
                const handshakeToken = key.split(':')[1];
                // Check if there's a pending session request for this handshake
                const pendingSessionKey = `pending_session:${handshakeToken}`;
                const pendingSessionExists = await redis.exists(pendingSessionKey);
                if (pendingSessionExists) {
                    const sessionData = await redis.hGetAll(pendingSessionKey);
                    logger_1.log.info(`Processing pending session request for handshake ${handshakeToken.substring(0, 8)}...`);
                    // Process the session request here
                    // This should trigger your session creation logic without going through the API endpoint
                    // Clean up the pending request
                    await redis.del(pendingSessionKey);
                }
            }
        }
    }
    catch (error) {
        logger_1.log.error(`Error checking pending headless sessions: ${error}`);
    }
}
// Schedule this to run regularly
function scheduleHeadlessSessionsCheck() {
    setInterval(checkPendingHeadlessSessions, 5000); // Check every 5 seconds
}
