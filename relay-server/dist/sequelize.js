"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.sequelize = void 0;
// src/sequelize.ts
const adapter_1 = require("./database/adapter");
const logger_1 = require("./utils/logger");
exports.sequelize = adapter_1.DatabaseAdapter.getSequelize();
// Test the connection
exports.sequelize.authenticate()
    .then(() => {
    logger_1.log.info('Database connection has been established successfully.');
})
    .catch(err => {
    logger_1.log.error(`Unable to connect to the database: ${err.message}`);
});
