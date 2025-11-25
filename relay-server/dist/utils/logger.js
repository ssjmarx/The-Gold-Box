"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.register = exports.log = void 0;
const pino_1 = __importDefault(require("pino"));
const prom_client_1 = require("prom-client");
const types_1 = require("../types/types");
// Create Pino logger
const logger = (0, pino_1.default)({
    level: process.env.LOG_LEVEL || types_1.LogLevel.INFO,
    transport: {
        target: 'pino-pretty',
        options: {
            colorize: true,
            translateTime: 'SYS:standard',
            ignore: 'pid,hostname'
        }
    }
});
// Create Prometheus metrics with typed labels
const logCounter = new prom_client_1.Counter({
    name: "pino_logs_total",
    help: "Total number of log messages",
    labelNames: ["level"],
});
const register = new prom_client_1.Registry();
exports.register = register;
register.setDefaultLabels({ app: "foundryvtt-rest-api-relay" });
register.registerMetric(logCounter);
(0, prom_client_1.collectDefaultMetrics)({ register });
exports.log = {
    info: (message, meta = {}) => {
        logCounter.inc({ level: types_1.LogLevel.INFO });
        logger.info(meta, message);
    },
    warn: (message, meta = {}) => {
        logCounter.inc({ level: types_1.LogLevel.WARN });
        logger.warn(meta, message);
    },
    error: (message, meta = {}) => {
        logCounter.inc({ level: types_1.LogLevel.ERROR });
        logger.error(meta, message);
    },
    debug: (message, meta = {}) => {
        logCounter.inc({ level: types_1.LogLevel.DEBUG });
        logger.debug(meta, message);
    },
};
