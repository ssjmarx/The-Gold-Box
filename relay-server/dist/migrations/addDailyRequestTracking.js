"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.migrateDailyRequestTracking = migrateDailyRequestTracking;
const sequelize_1 = require("../sequelize");
const logger_1 = require("../utils/logger");
/**
 * Migration to add daily request tracking columns
 * This adds requestsToday and lastRequestDate columns to the Users table
 */
async function migrateDailyRequestTracking() {
    try {
        logger_1.log.info('Starting migration to add daily request tracking columns');
        // Check if we're using memory store (skip migration)
        const isMemoryStore = process.env.DB_TYPE === 'memory';
        if (isMemoryStore) {
            logger_1.log.info('Using memory store - skipping database migration');
            return;
        }
        // Check if sequelize has query method (only available for SQL databases)
        if (!('query' in sequelize_1.sequelize)) {
            logger_1.log.warn('Database does not support migrations - skipping');
            return;
        }
        // Add requestsToday column
        try {
            await sequelize_1.sequelize.query(`
        ALTER TABLE "Users" 
        ADD COLUMN "requestsToday" INTEGER DEFAULT 0;
      `);
            logger_1.log.info('Added requestsToday column');
        }
        catch (error) {
            if (error.message.includes('already exists') || error.message.includes('duplicate column name')) {
                logger_1.log.info('requestsToday column already exists - skipping');
            }
            else {
                throw error;
            }
        }
        // Add lastRequestDate column
        try {
            await sequelize_1.sequelize.query(`
        ALTER TABLE "Users" 
        ADD COLUMN "lastRequestDate" DATE;
      `);
            logger_1.log.info('Added lastRequestDate column');
        }
        catch (error) {
            if (error.message.includes('already exists') || error.message.includes('duplicate column name')) {
                logger_1.log.info('lastRequestDate column already exists - skipping');
            }
            else {
                throw error;
            }
        }
        // Initialize existing users with default values
        await sequelize_1.sequelize.query(`
      UPDATE "Users" 
      SET "requestsToday" = 0, "lastRequestDate" = NULL 
      WHERE "requestsToday" IS NULL OR "lastRequestDate" IS NULL;
    `);
        logger_1.log.info('Migration completed successfully');
    }
    catch (error) {
        logger_1.log.error('Migration failed', { error });
        throw error;
    }
}
