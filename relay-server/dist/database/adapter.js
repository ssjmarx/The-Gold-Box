"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.DatabaseAdapter = void 0;
// src/database/adapter.ts
const sequelize_1 = require("sequelize");
const logger_1 = require("../utils/logger");
const memoryStore_1 = require("./memoryStore");
const path_1 = __importDefault(require("path"));
const fs_1 = __importDefault(require("fs"));
class DatabaseAdapter {
    static getSequelize() {
        const dbUrl = process.env.DATABASE_URL;
        const dbType = process.env.DB_TYPE || 'postgres';
        if (dbType === 'memory') {
            logger_1.log.info('Using in-memory database');
            return new memoryStore_1.MemoryStore();
        }
        if (dbType === 'sqlite') {
            logger_1.log.info('Using SQLite database');
            // Ensure data directory exists
            const dataDir = path_1.default.join(process.cwd(), 'data');
            if (!fs_1.default.existsSync(dataDir)) {
                fs_1.default.mkdirSync(dataDir, { recursive: true });
            }
            const dbPath = path_1.default.join(dataDir, 'relay.db');
            logger_1.log.info(`SQLite database path: ${dbPath}`);
            return new sequelize_1.Sequelize({
                dialect: 'sqlite',
                storage: dbPath,
                logging: false
            });
        }
        // Default to PostgreSQL for production
        if (!dbUrl) {
            logger_1.log.error('DATABASE_URL environment variable is not set - stopping');
            process.exit(1);
        }
        const isProduction = process.env.NODE_ENV === 'production';
        return new sequelize_1.Sequelize(dbUrl, {
            dialect: 'postgres',
            protocol: 'postgres',
            dialectOptions: {
                ssl: isProduction ? {
                    require: true,
                    rejectUnauthorized: false
                } : false
            },
            logging: false
        });
    }
}
exports.DatabaseAdapter = DatabaseAdapter;
