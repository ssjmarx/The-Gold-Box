# The Gold Box - Future Enhancements

**Version:** 0.3.9-extras-4  
**Related Patch:** 0.3.9-the-foundation  
**Status:** Saved for Future Implementation  
**Date:** 2025-12-29  
**Last Updated:** January 5, 2026 (trimmed)

---

## Overview

Features identified during 0.3.9 development but deferred to future updates. These are nice-to-have enhancements, not blocking functionality.

---

## Saved Features

### 1. Enhanced Logger with JSON Pretty-Printing

**Status:** SAVED FOR LATER

**Problem:** JSON objects logged as single-line strings, difficult to read in logs.

**Planned Implementation:** Custom logging formatter to auto-detect and pretty-print JSON objects with indentation.

**Files to Modify (Future):**
- `backend/shared/startup/startup.py` - Add custom JSON formatter
- `backend/shared/startup/config.py` - Update logging configuration

---

### 2. Selective Logging Cleanup

**Status:** SAVED FOR LATER

**Problem:** Logs overly verbose with routine operations, making it difficult to find important information.

**Planned Cleanup Rules:**

**KEEP (INFO level):**
- AI Conversation Messages (all message blocks)
- Endpoint Reports (HTTP request/response logs from Uvicorn)
- Outbound Connection Updates (LiteLLM provider logs)
- WebSocket Connection Status (connection/disconnected messages)
- Critical Errors (ERROR and WARNING level logs)

**REMOVE or MOVE TO DEBUG:**
- Tool listing messages
- WebSocket routine routing messages
- Delta "no changes" messages
- Session ID messages (keep only in ADD MESSAGE blocks)
- Roll result processing steps (consolidate from 6 lines to 2-3)
- Combat state double logging

**Expected Outcome:** ~70% reduction in log volume while preserving critical debugging information.

**Files to Modify (Future):**
- `backend/services/ai_services/ai_orchestrator.py`
- `backend/services/ai_tools/ai_tool_executor.py`
- `backend/services/message_services/websocket_message_collector.py`
- `backend/services/system_services/websocket_handler.py`

---

### 3. Remove All Emojis from Project

**Status:** SAVED FOR LATER

**Problem:** Emojis used throughout project may not align with accessibility requirements.

**Current Emoji Locations:**
- `lang/en.json` - 1 occurrence (❌ in CONNECTION_FAILED message)
- `backend/services/system_services/registry.py` - 8 occurrences (❌ in error logs)
- `backend/testing/TESTING.md` - 8 occurrences (❌ in documentation tables)

**Planned Replacement:**
- `❌` (red X) → Replace with "ERROR:" or "FAILED:"

**Files to Modify (Future):**
- `lang/en.json`
- `backend/services/system_services/registry.py`
- `backend/testing/TESTING.md`

**Expected Outcome:** Zero emojis in codebase, improved accessibility for screen readers.

---

## Complete as-Is

### 4. User-Friendly WebSocket Authentication Errors

**Status:** COMPLETE - NO CHANGES NEEDED

Authentication failures already show clear error messages with appropriate user guidance.

---

## Abandoned

### 5. Settings Menu Reorganization

**Status:** ABANDONED - Requires Heavy Rewrite

**Problem:** Settings menu lists all LLM settings together, making it long and difficult to navigate.

**Original Plan:** Add dropdown selector to show/hide General or Tactical settings groups.

**Why Abandoned:** Requires very heavy code rewrite to Foundry's settings system. Current settings menu is functional.

**Alternative Approaches (Future):**
1. Create separate configuration pages/tabs
2. Use Foundry's built-in settings categories (if available)
3. Consider custom settings UI implementation

---

## Summary

**Features Saved for Later:**
1. Enhanced Logger with JSON Pretty-Printing - Nice-to-have
2. Selective Logging Cleanup - Optimization
3. Remove All Emojis from Project - Accessibility improvement

**Features Complete as-Is:**
4. User-Friendly WebSocket Authentication Errors - Already adequate

**Features Abandoned:**
5. Settings Menu Reorganization - Requires heavy rewrite

**Note:** No code changes at this time. All features documented for future implementation.
