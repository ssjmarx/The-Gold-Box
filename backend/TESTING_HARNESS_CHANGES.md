# Testing Harness Transparency Improvements

## Overview
These changes make the test harness a transparent interceptor that shows the EXACT messages the AI would receive, using the same code paths as production.

## Changes Made

### 1. backend/services/ai_services/testing_harness.py
**Major Refactor:** `generate_initial_prompt()` method

**Before:** Used separate logic to manually construct prompts
**After:** Now uses exact same code path as production AI service:

- **Triggers `world_state_refresh`** on first turn (like `ai_orchestrator.py` does)
- **Uses `build_initial_messages_with_delta()`** from shared utility (same as production)
- **Integrates with `AISessionManager`** for first-turn detection
- **Returns `initial_messages` array** (exact OpenAI format messages AI would receive)
- **Clears delta after retrieval** (same as production)

**Key Addition:** `_decode_messages_for_display()` helper for better log readability

### 2. backend/api/admin.py
**Updated:** `handle_start_test_session()` function

**Changes:**
- Creates AI session via `AISessionManager` (integrated with production session tracking)
- Passes `ai_session_id` to testing harness for first-turn detection
- Returns `initial_messages` in response (exact AI messages)
- Returns `is_first_turn` flag
- Stores `ai_session_id` in test session for reference

**Result:** Test sessions now properly track first-turn status and show exact prompts

### 3. backend/shared/startup/services.py
**Status:** No changes needed - WebSocket handler already stores messages properly

The `_handle_test_chat_request()` function already:
- Stores messages in WebSocket message collector
- Uses `AISessionManager` for session tracking
- Works correctly with the updated testing harness

## How It Works Now

### First Turn (New Test Session)
1. User calls `start_test_session` via curl
2. Admin endpoint creates AI session via `AISessionManager`
3. Testing harness `generate_initial_prompt()` is called
4. **Sends `world_state_refresh`** to frontend (triggers full world state sync)
5. **Waits for frontend response** (session info, party, scene, etc.)
6. **Calls `ContextBuilder.build_initial_context()`** to gather world state
7. **Uses `build_initial_messages_with_delta()`** with `is_first_turn=True`
8. Injects full world state into system prompt
9. Returns exact messages AI would receive
10. User sees exact prompt with full context

### Subsequent Turns (Same Test Session, No WebSocket Reset)
1. User calls `start_test_session` again (same `ai_session_id`)
2. Testing harness checks `ai_session_manager.is_first_turn_complete()` → False
3. **Does NOT send `world_state_refresh`** (not first turn anymore)
4. **Retrieves game delta** from WebSocket message collector
5. **Uses `build_initial_messages_with_delta()`** with `is_first_turn=False`
6. Injects only delta (recent changes) into system prompt
7. Returns exact messages AI would receive
8. User sees exact prompt with delta context only

## Benefits

1. **True Transparency:** Test harness shows EXACT messages AI would receive
2. **First-Turn Handling:** Properly gathers full world state on first turn
3. **Delta Tracking:** Shows exact deltas on subsequent turns
4. **Session Consistency:** Uses same `AISessionManager` as production
5. **Code Reuse:** No duplicate logic - uses shared utilities

## Testing the Changes

### Test 1: First Turn
```bash
# Start test session
curl -X POST http://localhost:5000/api/admin \
  -H "Content-Type: application/json" \
  -H "X-Admin-Password: yourpassword" \
  -d '{
    "command": "start_test_session"
  }'

# Expected Response:
# - ai_session_id: UUID
# - is_first_turn: true
# - initial_messages: Array with full world state
# - initial_prompt: System prompt with session_info, party_compendium, active_scene, etc.
```

### Test 2: Subsequent Turn (No WebSocket Reset)
```bash
# End test session WITHOUT resetting connection
curl -X POST http://localhost:5000/api/admin \
  -H "Content-Type: application/json" \
  -H "X-Admin-Password: yourpassword" \
  -d '{
    "command": "end_test_session",
    "test_session_id": "previous_session_id",
    "reset_connection": false
  }'

# Start new test session immediately
curl -X POST http://localhost:5000/api/admin \
  -H "Content-Type: application/json" \
  -H "X-Admin-Password: yourpassword" \
  -d '{
    "command": "start_test_session"
  }'

# Expected Response:
# - ai_session_id: SAME as before (AISessionManager reuses session)
# - is_first_turn: false
# - initial_messages: Array with only delta (no full world state)
# - initial_prompt: System prompt with only recent changes
```

## Verification Checklist

- [ ] First turn shows full world state (session_info, party_compendium, active_scene)
- [ ] Subsequent turns show only delta (recent changes)
- [ ] `ai_session_id` is consistent across multiple test sessions (same client/provider/model)
- [ ] `is_first_turn` flag is correct (true on first, false on subsequent)
- [ ] `initial_messages` array matches OpenAI format
- [ ] World state refresh is triggered only on first turn
- [ ] Delta is cleared after retrieval (same as production)

## Files Modified

1. `backend/services/ai_services/testing_harness.py` - Core transparency fix
2. `backend/api/admin.py` - Integration with AISessionManager

## Files Unchanged (Already Correct)

1. `backend/shared/startup/services.py` - WebSocket handler
2. `backend/shared/utils/ai_prompt_builder.py` - Shared utility
3. `backend/services/message_services/context_builder.py` - World state builder
4. `backend/services/ai_services/ai_orchestrator.py` - Production orchestrator

## Notes

- Test harness is now a **transparent interceptor**, not a substitute
- All test mode flows use same code paths as production
- Session state is managed by `AISessionManager` for consistency
- No duplicate logic - everything uses shared utilities
