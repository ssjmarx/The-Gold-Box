"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.corsMiddleware = void 0;
const corsMiddleware = (options = {}) => {
    const defaultOptions = {
        origin: "*", // Allow all origins
        methods: ["GET", "HEAD", "PUT", "PATCH", "POST", "DELETE"],
        allowedHeaders: ["Content-Type", "Authorization", "X-Requested-With", "x-api-key"],
        exposedHeaders: [],
        credentials: true, // Important for cookies/auth to work
        maxAge: 86400, // 24 hours
        preflightContinue: false,
    };
    // Merge provided options with defaults
    const corsOptions = { ...defaultOptions, ...options };
    return async (req, res, next) => {
        // Handle CORS headers
        res.header("Access-Control-Allow-Origin", "*");
        res.header("Access-Control-Allow-Methods", corsOptions.methods.join(", "));
        res.header("Access-Control-Allow-Headers", "Origin, X-Requested-With, Content-Type, Accept, Authorization, x-api-key");
        if (corsOptions.credentials) {
            res.header("Access-Control-Allow-Credentials", "true");
        }
        // Handle preflight requests
        if (req.method === "OPTIONS") {
            res.status(200).end();
            return;
        }
        next();
    };
};
exports.corsMiddleware = corsMiddleware;
