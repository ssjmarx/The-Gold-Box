"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.storeHeadlessSession = storeHeadlessSession;
exports.getSessionForClient = getSessionForClient;
exports.getSessionData = getSessionData;
exports.getSessionForApiKey = getSessionForApiKey;
exports.cleanupHeadlessSession = cleanupHeadlessSession;
exports.redisSessionMiddleware = redisSessionMiddleware;
const redis_1 = require("../config/redis");
const logger_1 = require("../utils/logger");
// Store headless session data in Redis
async function storeHeadlessSession(sessionId, userId, apiKey, instanceId) {
    const redis = (0, redis_1.getRedisClient)();
    if (!redis)
        return false;
    const clientId = `foundry-${userId}`;
    try {
        // Store session data with 3 hour expiry
        await redis.hSet(`headless_session:${sessionId}`, {
            clientId,
            apiKey,
            instanceId,
            created: Date.now().toString()
        });
        await redis.expire(`headless_session:${sessionId}`, 10800);
        // Store clientId to sessionId mapping
        await redis.set(`headless_client:${clientId}`, sessionId);
        await redis.expire(`headless_client:${clientId}`, 10800);
        // Store apiKey to sessionId mapping for quick lookups
        await redis.set(`headless_apikey:${apiKey}:session`, sessionId);
        await redis.expire(`headless_apikey:${apiKey}:session`, 10800);
        logger_1.log.info(`Stored headless session ${sessionId} for client ${clientId} in Redis`);
        return true;
    }
    catch (error) {
        logger_1.log.error(`Failed to store headless session in Redis: ${error}`);
        return false;
    }
}
// Get session ID for a client
async function getSessionForClient(clientId) {
    return await (0, redis_1.safeRedisOperation)(async () => {
        const redis = (0, redis_1.getRedisClient)();
        if (!redis)
            return null;
        return await redis.get(`headless_client:${clientId}`);
    }, null);
}
// Get session data by session ID
async function getSessionData(sessionId) {
    return await (0, redis_1.safeRedisOperation)(async () => {
        const redis = (0, redis_1.getRedisClient)();
        if (!redis)
            return null;
        const exists = await redis.exists(`headless_session:${sessionId}`);
        if (!exists)
            return null;
        return await redis.hGetAll(`headless_session:${sessionId}`);
    }, null);
}
// Get active sessions for API key
async function getSessionForApiKey(apiKey) {
    return await (0, redis_1.safeRedisOperation)(async () => {
        const redis = (0, redis_1.getRedisClient)();
        if (!redis)
            return null;
        return await redis.get(`headless_apikey:${apiKey}:session`);
    }, null);
}
// Clean up session data
async function cleanupHeadlessSession(sessionId) {
    return await (0, redis_1.safeRedisOperation)(async () => {
        const redis = (0, redis_1.getRedisClient)();
        if (!redis)
            return false;
        // Get session data first to find clientId and apiKey
        const sessionData = await redis.hGetAll(`headless_session:${sessionId}`);
        if (!sessionData)
            return false;
        const { clientId, apiKey } = sessionData;
        // Clean up all related Redis keys
        await redis.del(`headless_session:${sessionId}`);
        if (clientId)
            await redis.del(`headless_client:${clientId}`);
        if (apiKey)
            await redis.del(`headless_apikey:${apiKey}:session`);
        logger_1.log.info(`Cleaned up Redis data for session ${sessionId}`);
        return true;
    }, false);
}
// Redis middleware to ensure cross-instance awareness
function redisSessionMiddleware(req, res, next) {
    const clientId = req.query.clientId;
    // If no client ID, continue with the request
    if (!clientId || !clientId.startsWith('foundry-')) {
        return next();
    }
    // Check if this client has a session in Redis
    getSessionForClient(clientId)
        .then(sessionId => {
        if (sessionId) {
            // Add session ID to request for other middleware/handlers
            req.headlessSessionId = sessionId;
            // Get full session data
            return getSessionData(sessionId);
        }
        return null;
    })
        .then(sessionData => {
        if (sessionData) {
            // Add session data to request
            req.headlessSessionData = sessionData;
        }
        next();
    })
        .catch(error => {
        logger_1.log.error(`Error in Redis session middleware: ${error}`);
        next();
    });
}
