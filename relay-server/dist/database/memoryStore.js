"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.MemoryStore = void 0;
// src/database/memoryStore.ts
const logger_1 = require("../utils/logger");
class MemoryStore {
    users = new Map();
    apiKeys = new Map();
    globalOptions = { define: {} };
    // These are just stubs to make User.init() work using local memory
    define() {
        return { sync: () => Promise.resolve() };
    }
    async authenticate() {
        logger_1.log.info('Memory store initialized');
        return true;
    }
    async sync() {
        return true;
    }
    getUser(apiKey) {
        const email = this.apiKeys.get(apiKey);
        return email ? this.users.get(email) : null;
    }
    incrementUserRequests(apiKey) {
        const email = this.apiKeys.get(apiKey);
        if (email) {
            const user = this.users.get(email);
            user.requestsThisMonth += 1;
            return true;
        }
        return false;
    }
}
exports.MemoryStore = MemoryStore;
