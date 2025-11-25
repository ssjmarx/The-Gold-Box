"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
const express_1 = __importDefault(require("express"));
const stripe_1 = require("../config/stripe");
const user_1 = require("../models/user");
const auth_1 = require("../middleware/auth");
const logger_1 = require("../utils/logger");
const path_1 = __importDefault(require("path"));
const router = express_1.default.Router();
// Get subscription status
router.get('/status', auth_1.authMiddleware, async (req, res) => {
    // If Stripe is disabled, return free tier status
    if (stripe_1.isStripeDisabled) {
        res.json({
            subscriptionStatus: 'free',
            subscriptionEndsAt: null
        });
        return;
    }
    try {
        const apiKey = req.headers['x-api-key'];
        const user = await user_1.User.findOne({ where: { apiKey } });
        if (!user) {
            res.status(404).json({ error: 'User not found' });
            return;
        }
        res.json({
            subscriptionStatus: user.dataValues.subscriptionStatus || 'free',
            subscriptionEndsAt: user.dataValues.subscriptionEndsAt || null
        });
        return;
    }
    catch (error) {
        logger_1.log.error(`Error getting subscription status: ${error}`);
        res.status(500).json({ error: 'Failed to get subscription status' });
        return;
    }
});
// Create checkout session
router.post('/create-checkout-session', auth_1.authMiddleware, async (req, res) => {
    try {
        logger_1.log.info('Creating checkout session');
        const apiKey = req.headers['x-api-key'];
        const user = await user_1.User.findOne({ where: { apiKey } });
        if (!user) {
            res.status(404).json({ error: 'User not found' });
            return;
        }
        // Get or create Stripe customer
        let customerId = user.stripeCustomerId;
        logger_1.log.info(`User: `, user);
        if (!customerId) {
            const customer = await stripe_1.stripe.customers.create({
                email: user.dataValues.email,
                metadata: { userId: user.dataValues.id.toString() }
            });
            customerId = customer.id;
            await user.update({ stripeCustomerId: customerId });
        }
        // Create checkout session
        const session = await stripe_1.stripe.checkout.sessions.create({
            customer: customerId,
            payment_method_types: ['card'],
            line_items: [
                {
                    price: stripe_1.SUBSCRIPTION_PRICES.monthly,
                    quantity: 1
                }
            ],
            mode: 'subscription',
            success_url: `${process.env.FRONTEND_URL}/api/subscriptions/subscription-success?session_id={CHECKOUT_SESSION_ID}`,
            cancel_url: `${process.env.FRONTEND_URL}/api/subscriptions/subscription-cancel`,
            metadata: { userId: user.dataValues.id.toString() }
        });
        res.json({ url: session.url });
    }
    catch (error) {
        logger_1.log.error(`Error creating checkout session: ${error}`);
        res.status(500).json({ error: 'Failed to create checkout session' });
    }
});
// Update the create-portal-session route
router.post('/create-portal-session', auth_1.authMiddleware, async (req, res) => {
    try {
        // You can still get user info if needed for analytics
        const apiKey = req.headers['x-api-key'];
        const user = await user_1.User.findOne({ where: { apiKey } });
        if (!user) {
            res.status(404).json({ error: 'User not found' });
            return;
        }
        // Instead of creating a session, redirect to the shared portal URL
        const portalUrl = process.env.STRIPE_PORTAL_URL;
        // Log the redirect for tracking
        logger_1.log.info(`Redirecting user ${user.id} to customer portal`);
        res.json({ url: portalUrl });
    }
    catch (error) {
        logger_1.log.error(`Error handling portal redirect: ${error}`);
        res.status(500).json({ error: 'Failed to access customer portal' });
    }
});
// Handle subscription success
router.get('/subscription-success', (req, res) => {
    res.sendFile(path_1.default.join(__dirname, '../../public/subscription-success.html'));
});
// Handle subscription cancel
router.get('/subscription-cancel', (req, res) => {
    res.sendFile(path_1.default.join(__dirname, '../../public/subscription-cancel.html'));
});
exports.default = router;
