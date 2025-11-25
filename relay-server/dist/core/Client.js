"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.Client = void 0;
const logger_1 = require("../utils/logger");
const ws_1 = require("ws");
const ClientManager_1 = require("./ClientManager");
class Client {
    ws;
    id;
    apiKey;
    lastSeen;
    connectedSince; // Add this
    connected;
    worldId;
    worldTitle;
    foundryVersion;
    systemId;
    systemTitle;
    systemVersion;
    customName;
    constructor(ws, id, apiKey, worldId, worldTitle, foundryVersion = null, systemId = null, systemTitle = null, systemVersion = null, customName = null) {
        this.ws = ws;
        this.id = id;
        this.apiKey = apiKey;
        this.lastSeen = Date.now();
        this.connectedSince = Date.now(); // Add this
        this.connected = true;
        this.worldId = worldId;
        this.worldTitle = worldTitle;
        this.foundryVersion = foundryVersion;
        this.systemId = systemId;
        this.systemTitle = systemTitle;
        this.systemVersion = systemVersion;
        this.customName = customName;
        this.setupHandlers();
    }
    setupHandlers() {
        this.ws.on("message", (data) => {
            try {
                const message = JSON.parse(data.toString());
                logger_1.log.info(`Received message from client ${this.id}: ${message.type}`);
                this.handleMessage(data);
            }
            catch (error) {
                logger_1.log.error(`Error processing WebSocket message: ${error}`);
            }
        });
        this.ws.on("close", () => {
            this.connected = false;
            this.handleClose();
        });
    }
    ping() {
        if (this.isAlive()) {
            try {
                this.ws.send(JSON.stringify({ type: "ping" }));
            }
            catch (err) {
                // Connection might be dead
                this.connected = false;
            }
        }
    }
    handleMessage(data) {
        try {
            const message = JSON.parse(data.toString());
            this.updateLastSeen();
            // Handle ping messages directly without broadcasting
            if (message.type === "ping") {
                this.send({ type: "pong" });
                return;
            }
            // For all other messages 
            ClientManager_1.ClientManager.handleIncomingMessage(this.id, message);
        }
        catch (error) {
            logger_1.log.error("Error handling message", { error, clientId: this.id });
        }
    }
    handleClose() {
        logger_1.log.info("Client disconnected", { clientId: this.id });
        ClientManager_1.ClientManager.removeClient(this.id);
    }
    send(data) {
        if (!this.isAlive())
            return false;
        try {
            this.ws.send(typeof data === 'string' ? data : JSON.stringify(data));
            return true;
        }
        catch (error) {
            logger_1.log.error("Error sending message", { error, clientId: this.id });
            this.connected = false;
            return false;
        }
    }
    broadcast(message) {
        ClientManager_1.ClientManager.broadcastToGroup(this.id, message);
    }
    getId() {
        return this.id;
    }
    getApiKey() {
        return this.apiKey;
    }
    getWorldId() {
        return this.worldId;
    }
    getWorldTitle() {
        return this.worldTitle;
    }
    getFoundryVersion() {
        return this.foundryVersion;
    }
    getSystemId() {
        return this.systemId;
    }
    getSystemTitle() {
        return this.systemTitle;
    }
    getSystemVersion() {
        return this.systemVersion;
    }
    getCustomName() {
        return this.customName;
    }
    updateLastSeen() {
        this.lastSeen = Date.now();
    }
    getLastSeen() {
        return this.lastSeen;
    }
    isAlive() {
        // Only check if the WebSocket connection is still open
        // This relies on the WebSocket protocol-level ping/pong mechanism to verify connection health
        // As long as the client is responding to protocol pings, we consider it alive
        return (this.connected && this.ws.readyState === ws_1.WebSocket.OPEN);
    }
    disconnect() {
        if (this.connected && this.ws.readyState === ws_1.WebSocket.OPEN) {
            try {
                this.ws.close();
            }
            catch (error) {
                logger_1.log.error("Error closing WebSocket", { error, clientId: this.id });
            }
        }
        this.connected = false;
    }
    markDisconnected() {
        this.connected = false;
    }
}
exports.Client = Client;
