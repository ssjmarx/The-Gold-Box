"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.initializeDatabase = initializeDatabase;
const sequelize_1 = require("../sequelize");
const user_1 = require("./user");
const crypto_1 = __importDefault(require("crypto"));
const logger_1 = require("../utils/logger");
async function initializeDatabase() {
    try {
        logger_1.log.info('Starting database initialization...');
        logger_1.log.info('Using database', { databaseUrl: process.env.DATABASE_URL });
        // Test the connection first
        await sequelize_1.sequelize.authenticate();
        logger_1.log.info('Database connection has been established successfully.');
        // Sync all models - this creates the tables
        logger_1.log.info('Syncing database models...');
        await sequelize_1.sequelize.sync({ force: true });
        logger_1.log.info('Database models synchronized.');
        // Create a default admin user with a plain password - it will be hashed by the hook
        logger_1.log.info('Creating admin user...');
        const user = await user_1.User.create({
            email: 'admin@example.com',
            password: 'admin123',
            apiKey: crypto_1.default.randomBytes(16).toString('hex'),
            requestsThisMonth: 0
        });
        // Check if user was created successfully
        if (!user) {
            logger_1.log.error('Failed to create admin user!');
            return false;
        }
        logger_1.log.info('Admin user created', { apiKey: user.getDataValue('apiKey') });
        logger_1.log.info('Database initialization complete!');
        return true;
    }
    catch (error) {
        logger_1.log.error('Database initialization failed', { error });
        return false;
    }
}
// Run the function if this script is executed directly
if (require.main === module) {
    initializeDatabase()
        .then((result) => {
        logger_1.log.info(`Initialization ${result ? 'succeeded' : 'failed'}`);
        process.exit(result ? 0 : 1);
    })
        .catch(error => {
        logger_1.log.error('Failed to initialize database', { error });
        process.exit(1);
    });
}
