"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.healthCheck = void 0;
const redis_1 = require("../config/redis");
const healthCheck = async (req, res) => {
    const redisStatus = (0, redis_1.checkRedisHealth)();
    const healthData = {
        status: 'ok',
        timestamp: new Date().toISOString(),
        uptime: process.uptime(),
        instance: process.env.FLY_ALLOC_ID || 'local',
        redis: {
            status: redisStatus.healthy ? 'connected' : 'disconnected',
            error: redisStatus.error
        },
        memory: {
            rss: Math.round(process.memoryUsage().rss / 1024 / 1024) + ' MB',
            heapTotal: Math.round(process.memoryUsage().heapTotal / 1024 / 1024) + ' MB',
            heapUsed: Math.round(process.memoryUsage().heapUsed / 1024 / 1024) + ' MB'
        }
    };
    res.json(healthData);
};
exports.healthCheck = healthCheck;
