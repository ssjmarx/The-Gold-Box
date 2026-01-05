# WebSocket Enhancements

**Status**: DRAFT - Not on Roadmap
**Created**: December 28, 2025
**Purpose**: Reference document for potential future improvements

---

## Overview

This document captures speculative enhancements discussed during architecture analysis. These are NOT planned for implementation, but preserved for reference. The current implementation is sound and well-designed for the project's specific requirements.

**Current Architecture Strengths:**
- Single server → Single Foundry deployment
- One AI at a time (natural concurrency limit)
- User-triggered only (human rate limiting)
- Poll-based AI (request/response pattern)
- Roll results via Foundry (multi-step function call workflow)
- Fast/slow path WebSocket separation
- Hybrid WebSocket + HTTP communication

---

## Potential Enhancements

### Roll Result Reliability
1. **Roll Result Timeout Monitoring** - Track latency and failures for roll results
2. **Client-Side Retry** - Add retry logic for transient WebSocket failures
3. **HTTP Fallback** - HTTP endpoint for roll result transmission when WebSocket fails

### Concurrency and State Management
1. **Single-AI Processing Lock** - Explicit lock to ensure only one AI processes at a time (defensive programming)
2. **Request-Response Correlation** - Track pending AI requests with timeout detection
3. **AI Processing Metrics** - Monitor AI processing state and duration

### User Experience
1. **Settings Changed Indicator** - Visual indicator when settings have changed but not synced
2. **Immediate Settings Sync** - Sync settings immediately when changed (vs on "Take AI Turn")

### Communication Enhancements
1. **Enhanced Metrics** - Comprehensive metrics for WebSocket connections and message handling
2. **Metrics Endpoint** - HTTP endpoint to collect and report metrics

---

## NOT Recommended (Current Approach is Optimal)

These enhancements would be over-engineering for the current architecture:

- **Message Queue for Chat Requests** - Single AI = natural sequential processing
- **Priority Queue System** - Fast/slow path separation already provides prioritization
- **Circuit Breaker Pattern** - Single AI = no cascade failure risk
- **Worker Pools/Semaphores** - Human-triggered = natural concurrency limit
- **Horizontal Scaling** - Project requirements: single server → single Foundry

---

## Recommendations

**High Value, Low Effort:**
1. Single-AI Processing Lock - Defensive programming with minimal overhead
2. Request-Response Correlation - Useful for debugging timeout issues
3. Settings Changed Indicator - Minor UX improvement

**Consider If Issues Arise:**
1. HTTP Fallback for Roll Results - If WebSocket reliability issues
2. Client-Side Retry for Roll Results - If transient connection issues
3. Enhanced Metrics - If monitoring needs arise

**Focus Areas (if implementing):**
1. Reliability of roll result path (fast path)
2. Defensive programming (locks, error handling)
3. Monitoring and metrics (for debugging)
4. Minor UX improvements (visual indicators)

**Avoid:**
1. Over-engineering for single-server deployment
2. Complex message queues or priority systems
3. Circuit breakers or worker pools
4. Horizontal scaling support

---

**Document Status**: Speculative
**Last Updated**: January 5, 2026 (trimmed)
