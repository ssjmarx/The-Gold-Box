"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.isStripeDisabled = exports.SUBSCRIPTION_PRICES = exports.stripe = void 0;
const stripe_1 = __importDefault(require("stripe"));
const logger_1 = require("../utils/logger");
// Check if we're using memory store or SQLite (local development)
const isMemoryStore = process.env.DB_TYPE === 'memory';
const isSQLiteStore = process.env.DB_TYPE === 'sqlite';
const isStripeDisabled = isMemoryStore || isSQLiteStore;
exports.isStripeDisabled = isStripeDisabled;
// Initialize Stripe conditionally
let stripe;
const SUBSCRIPTION_PRICES = {
    monthly: process.env.STRIPE_PRICE_ID || '' // Your Stripe price ID for monthly subscription
};
exports.SUBSCRIPTION_PRICES = SUBSCRIPTION_PRICES;
if (isStripeDisabled) {
    logger_1.log.info('Stripe disabled in local/memory mode');
    // Export a disabled version with no-op functions
    exports.stripe = stripe = {
        disabled: true,
        customers: { create: async () => ({ id: 'disabled' }) },
        checkout: { sessions: { create: async () => ({ url: '#' }) } },
        webhooks: { constructEvent: () => ({ type: 'disabled', data: { object: {} } }) }
    };
}
else {
    // Initialize real Stripe with your secret key
    if (!process.env.STRIPE_SECRET_KEY) {
        logger_1.log.warn('STRIPE_SECRET_KEY not provided, subscription features will not work');
        // Create a disabled stripe instance when no key is provided
        exports.stripe = stripe = {
            disabled: true,
            customers: { create: async () => ({ id: 'disabled' }) },
            checkout: { sessions: { create: async () => ({ url: '#' }) } },
            webhooks: { constructEvent: () => ({ type: 'disabled', data: { object: {} } }) }
        };
    }
    else {
        exports.stripe = stripe = new stripe_1.default(process.env.STRIPE_SECRET_KEY, {
            apiVersion: '2025-02-24.acacia' // Use the latest API version
        });
    }
}
