"use strict";
/**
 * Main entry point for the FoundryVTT REST API Relay Server.
 *
 * This server provides WebSocket connectivity and a REST API to access Foundry VTT data remotely.
 * It facilitates communication between Foundry VTT clients and external applications through
 * WebSocket relays and HTTP endpoints.
 *
 * @author ThreeHats
 * @since 1.8.1
 */
var __createBinding = (this && this.__createBinding) || (Object.create ? (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    var desc = Object.getOwnPropertyDescriptor(m, k);
    if (!desc || ("get" in desc ? !m.__esModule : desc.writable || desc.configurable)) {
      desc = { enumerable: true, get: function() { return m[k]; } };
    }
    Object.defineProperty(o, k2, desc);
}) : (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    o[k2] = m[k];
}));
var __setModuleDefault = (this && this.__setModuleDefault) || (Object.create ? (function(o, v) {
    Object.defineProperty(o, "default", { enumerable: true, value: v });
}) : function(o, v) {
    o["default"] = v;
});
var __importStar = (this && this.__importStar) || (function () {
    var ownKeys = function(o) {
        ownKeys = Object.getOwnPropertyNames || function (o) {
            var ar = [];
            for (var k in o) if (Object.prototype.hasOwnProperty.call(o, k)) ar[ar.length] = k;
            return ar;
        };
        return ownKeys(o);
    };
    return function (mod) {
        if (mod && mod.__esModule) return mod;
        var result = {};
        if (mod != null) for (var k = ownKeys(mod), i = 0; i < k.length; i++) if (k[i] !== "default") __createBinding(result, mod, k[i]);
        __setModuleDefault(result, mod);
        return result;
    };
})();
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
const express_1 = __importDefault(require("express"));
const http_1 = require("http");
const ws_1 = require("ws");
const cors_1 = require("./middleware/cors");
const logger_1 = require("./utils/logger");
const websocket_1 = require("./routes/websocket");
const api_1 = require("./routes/api");
const auth_1 = __importDefault(require("./routes/auth"));
const dotenv_1 = require("dotenv");
const path = __importStar(require("path"));
const fs = __importStar(require("fs"));
const sequelize_1 = require("./sequelize");
const stripe_1 = __importDefault(require("./routes/stripe"));
const webhook_1 = __importDefault(require("./routes/webhook"));
const redis_1 = require("./config/redis");
const headlessSessions_1 = require("./workers/headlessSessions");
const redisSession_1 = require("./middleware/redisSession");
const healthCheck_1 = require("./utils/healthCheck");
const cron_1 = require("./cron");
const addDailyRequestTracking_1 = require("./migrations/addDailyRequestTracking");
(0, dotenv_1.config)();
/**
 * Express application instance
 * @public
 */
const app = (0, express_1.default)();
/**
 * HTTP server instance that wraps the Express app
 * @public
 */
const httpServer = (0, http_1.createServer)(app);
// Disable timeouts to keep WebSocket connections open may want to sent a long timeout in the future instead
httpServer.setTimeout(0);
httpServer.keepAliveTimeout = 0;
httpServer.headersTimeout = 0;
// Setup CORS
app.use((0, cors_1.corsMiddleware)());
app.use('/api/webhooks/stripe', express_1.default.raw({ type: 'application/json' }));
// Special handling for /upload endpoint to preserve raw body for binary uploads
app.use('/upload', (req, res, next) => {
    const contentType = req.headers['content-type'] || '';
    if (!contentType.includes('application/json')) {
        express_1.default.raw({
            type: '*/*',
            limit: '250mb'
        })(req, res, next);
    }
    else {
        // For JSON requests to /upload, use the regular JSON parser
        express_1.default.json({
            limit: '250mb'
        })(req, res, next);
    }
});
// Parse JSON bodies for all other routes with 250MB limit
app.use(express_1.default.json({ limit: '250mb' }));
// Add Redis session middleware
app.use(redisSession_1.redisSessionMiddleware);
// Serve static files from public directory
app.use("/static", express_1.default.static(path.join(__dirname, "../public")));
app.use("/static/css", express_1.default.static(path.join(__dirname, "../public/css")));
app.use("/static/js", express_1.default.static(path.join(__dirname, "../public/js")));
// Redirect trailing slashes in docs routes to clean URLs
app.use('/docs', (req, res, next) => {
    if (req.path !== '/' && req.path.endsWith('/')) {
        const cleanPath = req.path.slice(0, -1);
        const queryString = req.url.includes('?') ? req.url.substring(req.url.indexOf('?')) : '';
        return res.redirect(301, `/docs${cleanPath}${queryString}`);
    }
    next();
});
// Serve Docusaurus documentation from /docs route
const docsPath = path.resolve(__dirname, "../docs/build");
try {
    // Check if docs build directory exists
    if (fs.existsSync(docsPath)) {
        app.use("/docs", express_1.default.static(docsPath, {
            index: 'index.html',
            fallthrough: true
        }));
        // Handle SPA routing for docs - serve index.html for any unmatched doc routes
        app.get('/docs/*', (req, res) => {
            res.sendFile(path.join(docsPath, 'index.html'));
        });
    }
    else {
        logger_1.log.warn('Documentation build directory not found, docs will not be available');
        app.get('/docs*', (req, res) => {
            res.status(404).json({ error: 'Documentation not available' });
        });
    }
}
catch (error) {
    logger_1.log.error('Error setting up documentation routes:', { error: error instanceof Error ? error.message : String(error) });
    app.get('/docs*', (req, res) => {
        res.status(500).json({ error: 'Documentation setup failed' });
    });
}
// Serve the main HTML page at the root URL
app.get("/", (req, res) => {
    res.sendFile(path.join(__dirname, "../public/index.html"));
});
// Create WebSocket server
const wss = new ws_1.WebSocketServer({ server: httpServer });
// Setup WebSocket routes
(0, websocket_1.wsRoutes)(wss);
// Setup API routes
(0, api_1.apiRoutes)(app);
// Setup Auth routes
app.use("/", auth_1.default);
app.use('/api/subscriptions', stripe_1.default);
app.use('/api/webhooks', webhook_1.default);
// Add default static image for tokens
app.get("/default-token.png", (req, res) => {
    res.sendFile(path.join(__dirname, "../public/default-token.png"));
});
// Add health endpoint
app.get('/api/health', (req, res) => {
    try {
        const health = (0, healthCheck_1.getSystemHealth)();
        res.status(200).json(health);
    }
    catch (error) {
        // Always return 200 during startup
        logger_1.log.warn('Health check error during startup:', { error: error instanceof Error ? error.message : String(error) });
        res.status(200).json({
            healthy: true,
            status: 'starting',
            timestamp: Date.now(),
            instanceId: process.env.FLY_ALLOC_ID || 'local',
            message: 'Service initializing'
        });
    }
});
/**
 * Server port number, defaults to 3010 if not specified in environment
 */
const port = process.env.PORT ? parseInt(process.env.PORT) : 3010;
/**
 * Initializes all server services in the correct order.
 *
 * This function performs the following initialization steps:
 * 1. Starts the HTTP and WebSocket servers first
 * 2. Synchronizes the database connection in background
 * 3. Initializes Redis if configured in background
 * 4. Sets up cron jobs for scheduled tasks in background
 * 5. Starts health monitoring in background
 *
 * @throws {Error} Exits the process if server startup fails
 * @returns {Promise<void>} Resolves when server is started
 */
async function initializeServices() {
    try {
        httpServer.listen(port, () => {
            logger_1.log.info(`Server running at http://localhost:${port}`);
            logger_1.log.info(`WebSocket server ready at ws://localhost:${port}/relay`);
        });
        // Do heavy initialization in background after server is running
        setImmediate(async () => {
            try {
                logger_1.log.info('Starting background initialization...');
                // First initialize database
                await sequelize_1.sequelize.sync();
                logger_1.log.info('Database synced');
                // Run migration to add daily request tracking columns
                await (0, addDailyRequestTracking_1.migrateDailyRequestTracking)();
                logger_1.log.info('Database migrations completed');
                if (process.env.REDIS_URL && process.env.REDIS_URL.length > 0) {
                    // Then initialize Redis
                    const redisInitialized = await (0, redis_1.initRedis)();
                    if (!redisInitialized) {
                        logger_1.log.warn('Redis initialization failed - continuing with local storage only');
                    }
                    else {
                        logger_1.log.info('Redis initialized successfully');
                    }
                }
                // Set up cron jobs
                (0, cron_1.setupCronJobs)();
                logger_1.log.info('Cron jobs initialized');
                // Start health monitoring
                (0, healthCheck_1.logSystemHealth)(); // Log initial health
                (0, healthCheck_1.startHealthMonitoring)(60000); // Check every minute
                logger_1.log.info('Health monitoring started');
                logger_1.log.info('All background services initialized successfully');
            }
            catch (error) {
                logger_1.log.error(`Error during background initialization: ${error}`);
                // Don't exit in production - let the server continue running
                if (process.env.NODE_ENV !== 'production') {
                    process.exit(1);
                }
            }
        });
    }
    catch (error) {
        logger_1.log.error(`Error starting server: ${error}`);
        process.exit(1);
    }
}
// Schedule the headless sessions worker
(0, headlessSessions_1.scheduleHeadlessSessionsCheck)();
// Note: Cron jobs are already initialized in initServices()
// Handle graceful shutdown
process.on('SIGTERM', async () => {
    logger_1.log.info('SIGTERM received, shutting down gracefully');
    await (0, redis_1.closeRedis)();
    process.exit(0);
});
process.on('SIGINT', async () => {
    logger_1.log.info('SIGINT received, shutting down gracefully');
    await (0, redis_1.closeRedis)();
    process.exit(0);
});
// Initialize services and start server
initializeServices().catch(err => {
    logger_1.log.error(`Failed to initialize services: ${err}`);
    process.exit(1);
});
