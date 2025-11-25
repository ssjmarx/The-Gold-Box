"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.resetMonthlyRequests = resetMonthlyRequests;
const user_1 = require("../models/user");
const logger_1 = require("../utils/logger");
const redis_1 = require("../config/redis");
/**
 * Reset the requestsThisMonth counter for all users
 * This is run on the first day of each month via a cron job
 * Previously this was done in the Stripe webhook when a payment was processed,
 * but that wasn't reliable for all users, especially those on the free tier
 */
async function resetMonthlyRequests() {
    const redis = (0, redis_1.getRedisClient)();
    const lockKey = 'monthly_reset_lock';
    const lockValue = `${process.env.FLY_ALLOC_ID || 'local'}_${Date.now()}`;
    const lockTTL = 300; // 5 minutes lock timeout
    try {
        // Try to acquire distributed lock
        if (redis) {
            // Use Redis SET with NX (not exists) and PX (expire in milliseconds) options
            const lockAcquired = await redis.set(lockKey, lockValue, {
                NX: true,
                PX: lockTTL * 1000
            });
            if (!lockAcquired) {
                logger_1.log.info('Monthly reset already running on another instance - skipping');
                return;
            }
            logger_1.log.info(`Acquired monthly reset lock on instance ${process.env.FLY_ALLOC_ID || 'local'}`);
        }
        else {
            logger_1.log.warn('Redis not available - proceeding with reset (single instance mode)');
        }
        const startTime = Date.now();
        logger_1.log.info(`Starting monthly API request count reset for all users at ${new Date().toISOString()}`);
        // For SQL databases, we can do a bulk update
        const [updatedCount] = await user_1.User.update({
            requestsThisMonth: 0,
            requestsToday: 0,
            lastRequestDate: null
        }, { where: {} } // Empty where clause updates all records
        );
        // Get total count of users for verification
        const totalUsers = await user_1.User.count();
        // Calculate execution time
        const executionTime = Date.now() - startTime;
        logger_1.log.info(`Successfully reset request count for ${updatedCount} of ${totalUsers} users (took ${executionTime}ms)`);
        // Verify the reset worked by checking a sample
        const sampleUser = await user_1.User.findOne({ where: {} });
        if (sampleUser) {
            const requestCount = sampleUser.getDataValue ?
                sampleUser.getDataValue('requestsThisMonth') : sampleUser.requestsThisMonth;
            logger_1.log.info(`Verification - Sample user request count: ${requestCount}`);
            if (requestCount !== 0) {
                logger_1.log.warn('Reset verification failed - some users may still have non-zero request counts');
            }
        }
        // Store completion timestamp in Redis for monitoring
        if (redis) {
            await redis.set('last_monthly_reset', new Date().toISOString());
            await redis.expire('last_monthly_reset', 86400 * 32); // Keep for 32 days
        }
    }
    catch (error) {
        logger_1.log.error(`Error resetting monthly request counts: ${error}`);
        // Try again with a different approach if the first method fails
        try {
            logger_1.log.info('Attempting alternate reset method using findAll + individual updates');
            // Get all users and update them individually
            const users = await user_1.User.findAll({});
            let successCount = 0;
            for (const user of users) {
                if ('setDataValue' in user && typeof user.setDataValue === 'function') {
                    user.setDataValue('requestsThisMonth', 0);
                    user.setDataValue('requestsToday', 0);
                    user.setDataValue('lastRequestDate', null);
                    await user.save();
                    successCount++;
                }
                else if ('requestsThisMonth' in user) {
                    user.requestsThisMonth = 0;
                    user.requestsToday = 0;
                    user.lastRequestDate = null;
                    if ('save' in user && typeof user.save === 'function') {
                        await user.save();
                        successCount++;
                    }
                }
            }
            logger_1.log.info(`Recovery method successful - reset ${successCount} users individually`);
        }
        catch (recoveryError) {
            logger_1.log.error(`Recovery attempt also failed: ${recoveryError}`);
        }
    }
    finally {
        // Release the lock
        if (redis) {
            try {
                // Only release if we still own the lock
                const script = `
          if redis.call("get", KEYS[1]) == ARGV[1] then
            return redis.call("del", KEYS[1])
          else
            return 0
          end
        `;
                await redis.eval(script, { keys: [lockKey], arguments: [lockValue] });
                logger_1.log.info('Released monthly reset lock');
            }
            catch (lockError) {
                logger_1.log.warn(`Error releasing lock: ${lockError}`);
            }
        }
    }
}
