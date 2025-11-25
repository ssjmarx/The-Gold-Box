"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
const express_1 = __importDefault(require("express"));
const stripe_1 = require("../config/stripe");
const user_1 = require("../models/user");
const logger_1 = require("../utils/logger");
const router = express_1.default.Router();
// Stripe webhook handler
router.post('/stripe', async (req, res) => {
    const sig = req.headers['stripe-signature'];
    let event;
    try {
        event = stripe_1.stripe.webhooks.constructEvent(req.body, sig, process.env.STRIPE_WEBHOOK_SECRET || '');
    }
    catch (err) {
        logger_1.log.error(`Webhook Error: ${err}`);
        res.status(400).send(`Webhook Error: ${err}`);
        return;
    }
    // Handle the event
    switch (event.type) {
        case 'customer.subscription.created':
        case 'customer.subscription.updated':
            await handleSubscriptionUpdated(event.data.object);
            break;
        case 'customer.subscription.deleted':
            await handleSubscriptionDeleted(event.data.object);
            break;
        case 'invoice.payment_succeeded':
            await handlePaymentSucceeded(event.data.object);
            break;
        case 'invoice.payment_failed':
            await handlePaymentFailed(event.data.object);
            break;
        default:
            logger_1.log.info(`Unhandled event type: ${event.type}`);
    }
    // Return a 200 response to acknowledge receipt of the event
    res.send();
});
// Handle subscription updates
async function handleSubscriptionUpdated(subscription) {
    try {
        const customerId = subscription.customer;
        const user = await user_1.User.findOne({ where: { stripeCustomerId: customerId } });
        if (!user) {
            logger_1.log.error(`User not found for customer: ${customerId}`);
            return;
        }
        await user.update({
            subscriptionStatus: subscription.status,
            subscriptionId: subscription.id,
            subscriptionEndsAt: new Date(subscription.current_period_end * 1000)
        });
        logger_1.log.info(`Updated subscription for user ${user.id} to status: ${subscription.status}`);
    }
    catch (error) {
        logger_1.log.error(`Error updating subscription: ${error}`);
    }
}
// Handle subscription deletions
async function handleSubscriptionDeleted(subscription) {
    try {
        const customerId = subscription.customer;
        const user = await user_1.User.findOne({ where: { stripeCustomerId: customerId } });
        if (!user) {
            logger_1.log.error(`User not found for customer: ${customerId}`);
            return;
        }
        await user.update({
            subscriptionStatus: 'canceled',
            subscriptionEndsAt: new Date(subscription.canceled_at * 1000)
        });
        logger_1.log.info(`Subscription canceled for user ${user.id}`);
    }
    catch (error) {
        logger_1.log.error(`Error handling subscription deletion: ${error}`);
    }
}
// Handle successful payments
async function handlePaymentSucceeded(invoice) {
    try {
        if (invoice.subscription) {
            const customerId = invoice.customer;
            const user = await user_1.User.findOne({ where: { stripeCustomerId: customerId } });
            if (!user) {
                logger_1.log.error(`User not found for customer: ${customerId}`);
                return;
            }
            // Log the payment success only - request count management is handled by
            // the monthly cron job in src/cron/monthlyReset.ts
            logger_1.log.info(`Payment success recorded for user ${user.id} (subscription: ${user.subscriptionStatus})`);
        }
    }
    catch (error) {
        logger_1.log.error(`Error handling payment success: ${error}`);
    }
}
// Handle failed payments
async function handlePaymentFailed(invoice) {
    try {
        if (invoice.subscription) {
            const customerId = invoice.customer;
            const user = await user_1.User.findOne({ where: { stripeCustomerId: customerId } });
            if (!user) {
                logger_1.log.error(`User not found for customer: ${customerId}`);
                return;
            }
            // Mark subscription as past_due
            await user.update({
                subscriptionStatus: 'past_due'
            });
            logger_1.log.info(`Updated subscription status to past_due for user ${user.id}`);
        }
    }
    catch (error) {
        logger_1.log.error(`Error handling payment failure: ${error}`);
    }
}
exports.default = router;
