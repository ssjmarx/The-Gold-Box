# The Gold Box v0.3.9 - Extras #4: Future Enhancements

**Version:** 0.3.9-extras-4  
**Related Patch:** 0.3.9-the-foundation  
**Status:** Saved for Future Implementation  
**Date:** 2025-12-29

---

## Overview

This plan contains features that were identified during the 0.3.9-the-foundation-extras-3 planning phase but were determined to be better addressed in future updates. These features are saved here for future consideration.

---

## Saved Feature 1: Enhanced Logger with JSON Pretty-Printing

### Status: SAVED FOR LATER

### Original Problem
Current logger outputs JSON objects as single-line strings, making them difficult to read in logs. Nested JSON objects are particularly hard to parse.

### Why Saved
We have colorful console output in place, but full JSON prettification is not yet implemented. This is a nice-to-have enhancement but not blocking any functionality.

### Planned Implementation
Create a custom logging formatter that automatically detects and pretty-prints JSON objects with proper indentation.

### Files to Modify (Future)
- `backend/shared/startup/startup.py` - Add custom JSON formatter
- `backend/shared/startup/config.py` - Update logging configuration

### Notes
- Current logging is functional with color coding
- JSON objects are readable but could be improved with indentation
- No urgency to implement

---

## Saved Feature 2: Selective Logging Cleanup

### Status: SAVED FOR LATER

### Original Problem
Logs are overly verbose with routine operations, making it difficult to find important information.

### Why Saved
Logs are functional and not causing issues. Cleanup can be done when we have time for optimization.

### Planned Cleanup Rules

**KEEP (INFO level):**
1. AI Conversation Messages:
   - `"===== SENDING INITIAL MESSAGES TO AI ====="` through `"===== END SENDING INITIAL MESSAGES ====="`
   - `"===== ADDING MESSAGE TO CONVERSATION ====="` through `"===== END ADDING MESSAGE ====="`
   - `"===== SENDING TO AI ====="` through `"===== END SENDING TO AI ====="`
   - `"===== RECEIVED FROM AI ====="` through `"===== END RECEIVED FROM AI ====="`

2. Endpoint Reports:
   - `INFO: ::1:44276 - "GET /api/health HTTP/1.1" 200 OK`
   - All HTTP request/response logs from Uvicorn

3. Outbound Connection Updates:
   - `03:45:08 - LiteLLM:INFO: utils.py:3427 - LiteLLM completion() model= glm-4.7; provider = openai`
   - All LiteLLM provider connection logs

4. WebSocket Connection Status:
   - Connection established/closed messages
   - Client connected/disconnected messages

5. Critical Errors:
   - All ERROR and WARNING level logs

**REMOVE or MOVE TO DEBUG:**
- `"Tools available to AI: 4 tools"` and tool listing
- `"WebSocket: [FAST PATH] Handling X for client Y"` routine routing messages
- `"WebSocket: [SLOW PATH] Creating background task for X"`
- `"Game delta stored for client X"` (keep only if hasChanges=True)
- `"Delta hasChanges: False - no changes to report"`
- `"Session: ai_session_XXX"` (keep only in ADD MESSAGE blocks)
- `"Role: assistant/tool/user"` (keep only in ADD MESSAGE blocks)
- Roll result processing steps (6+ lines, consolidate to 2-3)
- Combat state double logging

### Files to Modify (Future)
- `backend/services/ai_services/ai_orchestrator.py`
- `backend/services/ai_tools/ai_tool_executor.py`
- `backend/services/message_services/websocket_message_collector.py`
- `backend/services/system_services/websocket_handler.py`

### Expected Outcome (Future)
- Logs are significantly cleaner while preserving all critical debugging information
- AI conversation flow remains fully traceable
- Connection status and health checks still visible
- ~70% reduction in log volume for routine operations

---

## Saved Feature 3: Remove All Emojis from Project

### Status: SAVED FOR LATER

### Original Problem
Emojis are used throughout the project for visual appeal but may not align with all user preferences or accessibility requirements.

### Why Saved
Emojis were found in project files. This is a code freeze scenario, so we're documenting the remaining work for later.

### Current Emoji Locations

**Files with emojis (excluding venv):**
1. `lang/en.json` - 1 occurrence (❌ in CONNECTION_FAILED message)
2. `backend/services/system_services/registry.py` - 8 occurrences (❌ in error logs)
3. `backend/testing/TESTING.md` - 8 occurrences (❌ in documentation tables)

### Planned Removal (Future)

Replace or remove:
- `❌` (red X) - Replace with "ERROR:" or "FAILED:"
- Other emojis if found during comprehensive search

### Files to Modify (Future)
- `lang/en.json`
- `backend/services/system_services/registry.py`
- `backend/testing/TESTING.md`

### Verification Steps (Future)
1. Search codebase for remaining emojis
2. Review all user-facing text for emoji usage
3. Test all notifications and UI messages
4. Ensure readability is maintained

### Expected Outcome (Future)
- Zero emojis in codebase
- All text remains clear and readable
- No loss of functionality or clarity
- Improved accessibility for screen readers

---

## Saved Feature 4: User-Friendly WebSocket Authentication Errors

### Status: COMPLETE AS-IS

### Original Problem
When WebSocket connection fails due to missing password or auth token, users see generic error messages without guidance on how to fix issue.

### Why Saved (Marked Complete)
Authentication errors are already sufficiently user-friendly. No changes needed at this time.

### Current State
- Authentication failures show clear error messages
- Backend already provides guidance
- Frontend displays notifications appropriately

### Notes
- Existing authentication error handling is adequate
- Users are directed to appropriate settings
- No blocking issues identified

---

## Saved Feature 5: Settings Menu Reorganization

### Status: ABANDONED - Requires Heavy Rewrite

### Original Problem
The settings menu lists all LLM settings (general and tactical) together, making it long and difficult to navigate.

### Why Abandoned
Adding a dropdown selector to show/hide General or Tactical settings groups was determined to require a very heavy code rewrite to Foundry's settings system.

### Original Plan
Add a dropdown selector to show/hide General or Tactical settings groups.

### Files That Would Need Modification (If Revisited)
- `scripts/gold-box.js` - Settings registration and UI
- `module.json` - Settings structure

### Alternative Approaches (Future Consideration)
1. Create separate configuration pages/tabs
2. Use Foundry's built-in settings categories (if available)
3. Consider custom settings UI implementation

### Notes
- Foundry's settings system is not easily customizable
- Dropdown grouping would require significant architectural changes
- Current settings menu is functional, though lengthy
- Can be revisited if user feedback indicates urgency

---

## Summary

**Features Saved for Later:**
1. Enhanced Logger with JSON Pretty-Printing - Nice-to-have, not blocking
2. Selective Logging Cleanup - Optimization, not blocking
3. Remove All Emojis from Project - Accessibility improvement, not blocking

**Features Complete as-Is:**
4. User-Friendly WebSocket Authentication Errors - Already adequate

**Features Abandoned:**
5. Settings Menu Reorganization - Requires heavy rewrite, not worth it currently

**Code Freeze Status:**
- No code changes to be made at this time
- All features documented for future implementation
- Project can proceed to next phase of development

---

**End of Plan**
