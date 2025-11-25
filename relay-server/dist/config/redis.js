"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.initRedis = initRedis;
exports.getRedisClient = getRedisClient;
exports.checkRedisHealth = checkRedisHealth;
exports.safeRedisOperation = safeRedisOperation;
exports.closeRedis = closeRedis;
const redis_1 = require("redis");
const logger_1 = require("../utils/logger");
// Global Redis client
let redisClient = null;
let redisConnected = false;
let redisReconnecting = false;
let lastRedisError = null;
// Redis connection details from environment
const REDIS_URL = process.env.REDIS_URL || '';
const REDIS_ENABLED = process.env.REDIS_ENABLED !== 'false';
// Initialize Redis client
async function initRedis() {
    if (!REDIS_ENABLED || !REDIS_URL) {
        logger_1.log.info('Redis is disabled by configuration');
        return false;
    }
    try {
        // Hide credentials when logging
        const sanitizedUrl = REDIS_URL.replace(/redis:\/\/.*@/, 'redis://***@');
        logger_1.log.info(`Initializing Redis client at ${sanitizedUrl}`);
        // Upstash requires TLS to be enabled
        const url = new URL(REDIS_URL);
        const isUpstash = url.hostname.includes('upstash.io');
        redisClient = (0, redis_1.createClient)({
            url: REDIS_URL,
            socket: {
                tls: isUpstash, // Enable TLS for Upstash connections
                rejectUnauthorized: false, // For self-signed certificates
                connectTimeout: 15000, // Increase connect timeout to 15s
                reconnectStrategy: (retries) => {
                    redisReconnecting = true;
                    const maxRetries = 20; // Increased max retries
                    if (retries >= maxRetries) {
                        logger_1.log.error(`Maximum Redis reconnection attempts (${maxRetries}) reached`);
                        return false; // Stop retrying
                    }
                    const delay = Math.min(retries * 500, 10000);
                    logger_1.log.warn(`Redis reconnect attempt ${retries}, next attempt in ${delay}ms`);
                    return delay;
                }
            },
            readonly: false,
            legacyMode: false,
            disableOfflineQueue: false
            // Connection retry behavior is handled by socket.reconnectStrategy above
        });
        // Set up event listeners for logging and state management
        redisClient.on('connect', () => {
            logger_1.log.info('Redis client connected');
        });
        redisClient.on('ready', () => {
            redisConnected = true;
            redisReconnecting = false;
            lastRedisError = null;
            logger_1.log.info('Redis client ready');
        });
        redisClient.on('error', (err) => {
            redisConnected = false;
            lastRedisError = err;
            logger_1.log.error(`Redis client error: ${err.message}`);
        });
        redisClient.on('end', () => {
            redisConnected = false;
            logger_1.log.warn('Redis client connection closed');
        });
        redisClient.on('reconnecting', () => {
            redisReconnecting = true;
            logger_1.log.warn('Redis client reconnecting...');
        });
        // Connect to Redis
        await redisClient.connect();
        logger_1.log.info('Redis client connected successfully');
        // Verify connection with a simple ping
        const pingResult = await redisClient.ping();
        logger_1.log.info(`Redis ping result: ${pingResult}`);
        redisConnected = true;
        return true;
    }
    catch (error) {
        redisConnected = false;
        lastRedisError = error;
        logger_1.log.error(`Failed to initialize Redis: ${error}`);
        return false;
    }
}
// Get Redis client with safety checks
function getRedisClient() {
    if (!REDIS_ENABLED) {
        return null;
    }
    if (!redisConnected && !redisReconnecting && redisClient) {
        // Try to reconnect if client exists but is disconnected
        logger_1.log.warn('Redis disconnected, attempting to reconnect...');
        redisClient.connect().catch(err => {
            logger_1.log.error(`Failed to reconnect to Redis: ${err}`);
        });
    }
    return redisClient;
}
// Check Redis health
function checkRedisHealth() {
    if (!REDIS_ENABLED) {
        return { healthy: true, error: 'Redis is disabled by configuration' };
    }
    if (!redisClient) {
        return { healthy: false, error: 'Redis client not initialized' };
    }
    if (!redisConnected) {
        return {
            healthy: false,
            error: lastRedisError ? `Redis disconnected: ${lastRedisError.message}` : 'Redis disconnected'
        };
    }
    return { healthy: true };
}
// Safely execute Redis operations with error handling
async function safeRedisOperation(operation, fallback) {
    if (!REDIS_ENABLED || !redisClient || !redisConnected) {
        return fallback;
    }
    try {
        return await operation();
    }
    catch (error) {
        logger_1.log.error(`Redis operation failed: ${error}`);
        return fallback;
    }
}
// Close Redis connection
async function closeRedis() {
    if (redisClient) {
        logger_1.log.info('Closing Redis connection');
        await redisClient.quit().catch(err => {
            logger_1.log.error(`Error closing Redis connection: ${err}`);
        });
        redisConnected = false;
        redisClient = null;
    }
}
