"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
const express_1 = require("express");
const bcryptjs_1 = __importDefault(require("bcryptjs"));
const user_1 = require("../models/user");
const crypto_1 = __importDefault(require("crypto"));
const shared_1 = require("./shared");
const logger_1 = require("../utils/logger");
const router = (0, express_1.Router)();
// Register a new user
router.post('/register', async (req, res) => {
    logger_1.log.info('Registration attempt in auth.ts');
    try {
        const { email, password } = req.body;
        logger_1.log.info(`Registration attempt for: ${email}`);
        if (!email || !password) {
            logger_1.log.warn('Missing email or password');
            (0, shared_1.safeResponse)(res, 400, { error: 'Email and password are required' });
            return;
        }
        // Check if user already exists
        const existingUser = await user_1.User.findOne({ where: { email } });
        if (existingUser) {
            logger_1.log.warn(`User already exists: ${email}`);
            (0, shared_1.safeResponse)(res, 409, { error: 'User already exists' });
            return;
        }
        logger_1.log.info('Creating new user...');
        // Create a new user
        const user = await user_1.User.create({
            email,
            password, // Will be hashed by the beforeCreate hook
            apiKey: crypto_1.default.randomBytes(16).toString('hex'), // Explicitly generate an API key
            requestsThisMonth: 0
        });
        logger_1.log.info(`User created: ${user.getDataValue('email')}`);
        // Return the user (exclude password but include API key)
        res.status(201).json({
            id: user.getDataValue('id'),
            email: user.getDataValue('email'),
            apiKey: user.getDataValue('apiKey'),
            createdAt: user.getDataValue('createdAt'),
            subscriptionStatus: user.getDataValue('subscriptionStatus') || 'free'
        });
        return;
    }
    catch (error) {
        logger_1.log.error('Registration error', { error });
        (0, shared_1.safeResponse)(res, 500, { error: 'Registration failed' });
        return;
    }
});
// Login route - update the password comparison logic
router.post('/login', async (req, res) => {
    try {
        const { email, password } = req.body;
        logger_1.log.info(`Login attempt for: ${email}`);
        if (!email || !password) {
            logger_1.log.warn('Missing email or password');
            res.status(400).json({ error: 'Email and password are required' });
            return;
        }
        // Find the user
        const user = await user_1.User.findOne({ where: { email } });
        if (!user) {
            logger_1.log.warn(`User not found: ${email}`);
            res.status(401).json({ error: 'Invalid credentials' });
            return;
        }
        logger_1.log.info(`User found: ${email}, comparing passwords...`);
        try {
            // Get the stored hash directly from the data value
            const storedHash = user.getDataValue('password');
            logger_1.log.debug('Stored hash status', { exists: !!storedHash });
            const isPasswordValid = await bcryptjs_1.default.compare(password, storedHash);
            logger_1.log.debug('Password comparison result', { isValid: isPasswordValid });
            if (!isPasswordValid) {
                logger_1.log.warn('Invalid password');
                res.status(401).json({ error: 'Invalid credentials' });
                return;
            }
            // Return the user (exclude password)
            res.status(200).json({
                id: user.getDataValue('id'),
                email: user.getDataValue('email'),
                apiKey: user.getDataValue('apiKey'),
                requestsThisMonth: user.getDataValue('requestsThisMonth'),
                createdAt: user.getDataValue('createdAt')
            });
            return;
        }
        catch (bcryptError) {
            logger_1.log.error('bcrypt comparison error', { error: bcryptError });
            res.status(500).json({ error: 'Authentication error' });
            return;
        }
    }
    catch (error) {
        logger_1.log.error('Login error', { error });
        res.status(500).json({ error: 'Login failed' });
        return;
    }
});
// Regenerate API key (for authenticated users)
router.post('/regenerate-key', async (req, res) => {
    try {
        const { email, password } = req.body;
        if (!email || !password) {
            res.status(400).json({ error: 'Email and password are required' });
            return;
        }
        // Find the user
        const user = await user_1.User.findOne({ where: { email } });
        if (!user) {
            res.status(401).json({ error: 'Invalid credentials' });
            return;
        }
        // Check password
        const isPasswordValid = await bcryptjs_1.default.compare(password, user.password);
        if (!isPasswordValid) {
            res.status(401).json({ error: 'Invalid credentials' });
            return;
        }
        // Generate new API key
        const newApiKey = crypto_1.default.randomBytes(16).toString('hex');
        await user.update({ apiKey: newApiKey });
        // Return the new API key
        res.status(200).json({
            apiKey: newApiKey
        });
    }
    catch (error) {
        logger_1.log.error('API key regeneration error', { error });
        res.status(500).json({ error: 'Failed to regenerate API key' });
    }
});
// Get user data (for authenticated users)
router.get('/user-data', async (req, res) => {
    try {
        // Get API key from header
        const apiKey = req.header('x-api-key');
        if (!apiKey) {
            res.status(401).json({ error: 'API key is required' });
            return;
        }
        // Find user by API key
        const user = await user_1.User.findOne({ where: { apiKey } });
        if (!user) {
            res.status(404).json({ error: 'User not found' });
            return;
        }
        // Return user data (exclude sensitive information)
        res.status(200).json({
            id: user.getDataValue('id'),
            email: user.getDataValue('email'),
            apiKey: user.getDataValue('apiKey'),
            requestsThisMonth: user.getDataValue('requestsThisMonth'),
            requestsToday: user.getDataValue('requestsToday') || 0,
            subscriptionStatus: user.getDataValue('subscriptionStatus') || 'free',
            limits: {
                dailyLimit: parseInt(process.env.DAILY_REQUEST_LIMIT || '1000'),
                monthlyLimit: parseInt(process.env.FREE_API_REQUESTS_LIMIT || '100'),
                unlimitedMonthly: (user.getDataValue('subscriptionStatus') === 'active')
            }
        });
        return;
    }
    catch (error) {
        logger_1.log.error('Error fetching user data', { error });
        res.status(500).json({ error: 'Failed to fetch user data' });
        return;
    }
});
exports.default = router;
