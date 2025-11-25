"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.ClientManager = exports.wsRoutes = void 0;
// src/routes/websocket.ts
const ws_1 = require("ws");
const logger_1 = require("../utils/logger");
const ClientManager_1 = require("../core/ClientManager");
Object.defineProperty(exports, "ClientManager", { enumerable: true, get: function () { return ClientManager_1.ClientManager; } });
const headlessSessions_1 = require("../workers/headlessSessions");
// Read ping interval from environment variable, default to 20 seconds
const WEBSOCKET_PING_INTERVAL_MS = parseInt(process.env.WEBSOCKET_PING_INTERVAL_MS || '20000', 10);
// Read client cleanup interval from environment variable, default to 15 seconds
const CLIENT_CLEANUP_INTERVAL_MS = parseInt(process.env.CLIENT_CLEANUP_INTERVAL_MS || '15000', 10);
const wsRoutes = (wss) => {
    wss.on("connection", async (ws, req) => {
        try {
            // Parse URL parameters
            const url = new URL(req.url || "", `http://${req.headers.host}`);
            const id = url.searchParams.get("id");
            const token = url.searchParams.get("token");
            const worldId = url.searchParams.get("worldId");
            const worldTitle = url.searchParams.get("worldTitle");
            const foundryVersion = url.searchParams.get("foundryVersion");
            const systemId = url.searchParams.get("systemId");
            const systemTitle = url.searchParams.get("systemTitle");
            const systemVersion = url.searchParams.get("systemVersion");
            const customName = url.searchParams.get("customName");
            if (!id || !token) {
                logger_1.log.warn("Rejecting WebSocket connection: missing id or token");
                ws.close(1008, "Missing client ID or token");
                return;
            }
            // Validate headless session before accepting the connection
            const isValid = await (0, headlessSessions_1.validateHeadlessSession)(id, token);
            if (!isValid) {
                logger_1.log.warn(`Rejecting invalid headless client: ${id}`);
                ws.close(1008, "Invalid headless session");
                return;
            }
            // Register client
            const client = await ClientManager_1.ClientManager.addClient(ws, id, token, worldId, worldTitle, foundryVersion, systemId, systemTitle, systemVersion, customName);
            if (!client)
                return; // Connection already rejected
            // Add protocol-level ping/pong to keep the TCP connection active
            const pingInterval = setInterval(() => {
                if (ws.readyState === ws_1.WebSocket.OPEN) {
                    ws.ping(Buffer.from("keepalive"));
                    logger_1.log.debug(`Sent WebSocket protocol ping to ${id}`);
                }
            }, WEBSOCKET_PING_INTERVAL_MS); // Use configured interval
            // Handle disconnection
            ws.on("close", () => {
                clearInterval(pingInterval);
                ClientManager_1.ClientManager.removeClient(id);
            });
            // Handle pong responses to update client activity
            ws.on("pong", () => {
                // Update the client's last seen timestamp
                client.updateLastSeen();
            });
            // Handle errors
            ws.on("error", (error) => {
                clearInterval(pingInterval);
                logger_1.log.error(`WebSocket error for client ${id}: ${error}`);
                ClientManager_1.ClientManager.removeClient(id);
            });
        }
        catch (error) {
            logger_1.log.error(`WebSocket connection error: ${error}`);
            try {
                ws.close(1011, "Server error");
            }
            catch (e) {
                // Ignore errors closing socket
            }
        }
    });
    // Set up periodic cleanup
    setInterval(() => {
        ClientManager_1.ClientManager.cleanupInactiveClients();
    }, CLIENT_CLEANUP_INTERVAL_MS); // Use configured interval
};
exports.wsRoutes = wsRoutes;
