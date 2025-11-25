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
Object.defineProperty(exports, "__esModule", { value: true });
exports.setupCronJobs = setupCronJobs;
exports.stopCronJobs = stopCronJobs;
exports.getCronJobStatus = getCronJobStatus;
exports.triggerMonthlyReset = triggerMonthlyReset;
exports.triggerDailyReset = triggerDailyReset;
const cron = __importStar(require("node-cron"));
const monthlyReset_1 = require("./monthlyReset");
const dailyReset_1 = require("./dailyReset");
const logger_1 = require("../utils/logger");
// Track scheduled jobs - use the correct type
let monthlyResetJob = null;
let dailyResetJob = null;
/**
 * Set up all cron jobs for the application
 */
function setupCronJobs() {
    if (!monthlyResetJob) {
        // Reset request counts at midnight on the first day of each month
        // Cron format: minute hour day month day-of-week
        monthlyResetJob = cron.schedule('0 0 1 * *', async () => {
            logger_1.log.info('Running scheduled monthly request count reset');
            try {
                await (0, monthlyReset_1.resetMonthlyRequests)();
                logger_1.log.info('Monthly request count reset completed successfully via cron job');
            }
            catch (error) {
                logger_1.log.error(`Error in monthly reset cron job: ${error}`);
                // Add retry logic
                setTimeout(async () => {
                    logger_1.log.info('Retrying monthly request count reset after failure');
                    try {
                        await (0, monthlyReset_1.resetMonthlyRequests)();
                        logger_1.log.info('Monthly request count reset retry successful');
                    }
                    catch (retryError) {
                        logger_1.log.error(`Monthly reset retry also failed: ${retryError}`);
                    }
                }, 5 * 60 * 1000); // Retry after 5 minutes
            }
        }, {
            timezone: 'UTC'
        });
        monthlyResetJob.start();
        logger_1.log.info('Monthly reset cron job scheduled');
        // Also run immediately when starting the server if it's the 1st day of month
        const now = new Date();
        if (now.getDate() === 1) {
            logger_1.log.info('Today is the 1st day of the month - running request reset immediately');
            (0, monthlyReset_1.resetMonthlyRequests)().catch(error => {
                logger_1.log.error(`Error running immediate monthly reset: ${error}`);
            });
        }
    }
    else {
        logger_1.log.info('Monthly reset cron job already scheduled');
    }
    if (!dailyResetJob) {
        // Reset daily request counts at midnight every day
        // Cron format: minute hour day month day-of-week
        dailyResetJob = cron.schedule('0 0 * * *', async () => {
            logger_1.log.info('Running scheduled daily request count reset');
            try {
                await (0, dailyReset_1.resetDailyRequests)();
                logger_1.log.info('Daily request count reset completed successfully via cron job');
            }
            catch (error) {
                logger_1.log.error(`Error in daily reset cron job: ${error}`);
                // Add retry logic
                setTimeout(async () => {
                    logger_1.log.info('Retrying daily request count reset after failure');
                    try {
                        await (0, dailyReset_1.resetDailyRequests)();
                        logger_1.log.info('Daily request count reset retry successful');
                    }
                    catch (retryError) {
                        logger_1.log.error(`Daily reset retry also failed: ${retryError}`);
                    }
                }, 5 * 60 * 1000); // Retry after 5 minutes
            }
        }, {
            timezone: 'UTC'
        });
        dailyResetJob.start();
        logger_1.log.info('Daily reset cron job scheduled');
    }
    else {
        logger_1.log.info('Daily reset cron job already scheduled');
    }
    logger_1.log.info('Cron jobs setup completed');
}
/**
 * Stop all cron jobs (useful for graceful shutdown)
 */
function stopCronJobs() {
    if (monthlyResetJob) {
        monthlyResetJob.stop();
        monthlyResetJob = null;
        logger_1.log.info('Monthly reset cron job stopped');
    }
    if (dailyResetJob) {
        dailyResetJob.stop();
        dailyResetJob = null;
        logger_1.log.info('Daily reset cron job stopped');
    }
}
/**
 * Get status of cron jobs
 */
function getCronJobStatus() {
    return {
        monthlyReset: {
            scheduled: monthlyResetJob !== null,
            active: monthlyResetJob !== null
        },
        dailyReset: {
            scheduled: dailyResetJob !== null,
            active: dailyResetJob !== null
        }
    };
}
/**
 * Manually trigger the monthly reset (for testing or emergency use)
 */
async function triggerMonthlyReset() {
    logger_1.log.info('Manually triggering monthly request count reset');
    await (0, monthlyReset_1.resetMonthlyRequests)();
}
/**
 * Manually trigger the daily reset (for testing or emergency use)
 */
async function triggerDailyReset() {
    logger_1.log.info('Manually triggering daily request count reset');
    await (0, dailyReset_1.resetDailyRequests)();
}
