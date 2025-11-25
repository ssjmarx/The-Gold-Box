"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.getSystemHealth = getSystemHealth;
exports.logSystemHealth = logSystemHealth;
exports.startHealthMonitoring = startHealthMonitoring;
const logger_1 = require("../utils/logger");
const redis_1 = require("../config/redis");
const os_1 = __importDefault(require("os"));
function getSystemHealth() {
    // Get Redis health
    const redisHealth = (0, redis_1.checkRedisHealth)();
    // Get system metrics
    const freeMem = os_1.default.freemem();
    const totalMem = os_1.default.totalmem();
    const memUsedPercent = ((totalMem - freeMem) / totalMem) * 100;
    const uptime = os_1.default.uptime();
    const cpuLoad = os_1.default.loadavg();
    // System is healthy if memory usage is under 90%
    const systemHealthy = memUsedPercent < 90;
    // Overall health status
    const healthy = redisHealth.healthy && systemHealthy;
    return {
        healthy,
        services: {
            redis: redisHealth,
            system: {
                healthy: systemHealthy,
                freeMem,
                totalMem,
                memUsedPercent,
                uptime,
                cpuLoad
            }
        },
        timestamp: Date.now(),
        instanceId: process.env.FLY_ALLOC_ID || 'local'
    };
}
function logSystemHealth() {
    const health = getSystemHealth();
    logger_1.log.info(`System health: ${health.healthy ? 'HEALTHY' : 'UNHEALTHY'}`);
    logger_1.log.info(`  Memory: ${Math.round(health.services.system.memUsedPercent)}% used (${Math.round(health.services.system.freeMem / 1024 / 1024)}MB free)`);
    logger_1.log.info(`  CPU Load: ${health.services.system.cpuLoad.map(v => v.toFixed(2)).join(', ')}`);
    logger_1.log.info(`  Redis: ${health.services.redis.healthy ? 'CONNECTED' : 'DISCONNECTED'} ${health.services.redis.message || ''}`);
}
function startHealthMonitoring(intervalMs = 300000) {
    return setInterval(logSystemHealth, intervalMs);
}
