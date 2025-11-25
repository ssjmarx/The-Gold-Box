"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.PerformanceSettings = exports.WSCloseCodes = exports.SUB_MAX_RECONNECT_ATTEMPTS = exports.STATE_READY_TIMEOUT = exports.STATE_CONNECTING_TIMEOUT = exports.WS_BASE_RECONNECT_DELAY = exports.WS_MAX_RECONNECT_DELAY = void 0;
exports.WS_MAX_RECONNECT_DELAY = 5000;
exports.WS_BASE_RECONNECT_DELAY = 1000;
exports.STATE_CONNECTING_TIMEOUT = 5000;
exports.STATE_READY_TIMEOUT = 20_000;
exports.SUB_MAX_RECONNECT_ATTEMPTS = 5;
var WSCloseCodes;
(function (WSCloseCodes) {
    WSCloseCodes[WSCloseCodes["Normal"] = 1000] = "Normal";
    WSCloseCodes[WSCloseCodes["NoClientId"] = 4001] = "NoClientId";
    WSCloseCodes[WSCloseCodes["NoAuth"] = 4002] = "NoAuth";
    WSCloseCodes[WSCloseCodes["NoConnectedGuild"] = 4003] = "NoConnectedGuild";
    WSCloseCodes[WSCloseCodes["InternalError"] = 4000] = "InternalError";
    WSCloseCodes[WSCloseCodes["DuplicateConnection"] = 4004] = "DuplicateConnection";
    WSCloseCodes[WSCloseCodes["ServerShutdown"] = 4005] = "ServerShutdown";
})(WSCloseCodes || (exports.WSCloseCodes = WSCloseCodes = {}));
var PerformanceSettings;
(function (PerformanceSettings) {
    PerformanceSettings[PerformanceSettings["MaxMissedFrames"] = 3000] = "MaxMissedFrames";
    PerformanceSettings[PerformanceSettings["BufferSize"] = 4096] = "BufferSize";
})(PerformanceSettings || (exports.PerformanceSettings = PerformanceSettings = {}));
