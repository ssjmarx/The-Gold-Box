# Implementation Plan: Patch 0.3.9 Foundation Testing Fixes

## Overview

This plan addresses issues discovered during testing of Patch 0.3.9 features:
- World State Overview not appearing in test initial prompts
- Testing command processor using old function names
- client_id saving issue in test scripts
- Missing delta testing automation
- No non-reset session end flag for delta testing

## Investigation Results

### Issue 1: World State Overview Not Appearing in Test Initial Prompts

**Root Cause:** In `testing_harness.py:generate_initial_prompt()`, call to `generate_enhanced_system_prompt()` is NOT passing the `world_state_overview` parameter, even though it's available in the function signature.

**Secondary Issue:** Uses camelCase for delta fields (`new_messages`, `deleted_messages`) instead of PascalCase like `api_chat.py` uses.

### Issue 2: Testing Command Processor Uses Old Tool Names

**Root Cause:** `testing_command_processor.py` still references old function names:
- `get_messages` → should be `get_message_history`
- `post_messages` → should be `post_message`
- Missing support for new tools: `roll_dice`, `get_encounter`

### Issue 3: client_id Saving Shows "null"

**Root Cause:** The test script extracts `client_id` from EVERY curl response, but only the first response (`start_test_session`) actually contains a `client_id` field. Subsequent commands don't return it, so `jq` returns `null`, which overwrites the saved file.

### Issue 4: No Non-Reset Session End Flag

**Root Cause:** `admin.py:handle_end_test_session()` always sets `reset_connection: True`. No flag exists to skip WebSocket reset for delta testing.

### Issue 5: Delta Testing Not Implemented

**Root Cause:** No command exists to inject arbitrary delta data for testing delta tracking across multiple AI turns.

## Implementation Plan

### Phase 1: Fix World State Overview in Test Sessions

**File: `backend/services/ai_services/testing_harness.py`**

**Changes needed:**

1. **Generate WSO for test sessions** (Lines 54-88):
   - Check if this is first turn (no conversation history)
   - Generate World State Overview for first turn
   - Import and use world_state_generator

2. **Update delta format to PascalCase** (Lines 78-82):
   - Change from camelCase to PascalCase
   - `new_messages` → `NewMessages`
   - `deleted_messages` → `DeletedMessages`

3. **Pass WSO to system prompt** (Line 84):
   - Pass `world_state_overview` parameter to `generate_enhanced_system_prompt()`

### Phase 2: Update Testing Command Processor

**File: `backend/services/ai_services/testing_command_processor.py`**

**Changes needed:**

1. **Update command parsing**:
   - Change `get_messages` → `get_message_history`
   - Update parameter from `count` to `limit`
   - Change `post_messages` → `post_message`
   - Update structure from array to single object

2. **Remove post_messages support**:
   - Delete `post_messages` parsing block entirely
   - Feature dropped as specified

3. **Add support for new tools**:
   - Add `roll_dice <formula> [flavor]`
   - Add `get_encounter`

4. **Update available commands list**:
   - Update to reflect new command names

5. **Update validation logic**:
   - Change parameter validation for new tools

6. **Update help text**:
   - Update command descriptions
   - Remove `post_messages` from help
   - Add `roll_dice` and `get_encounter` examples

7. **Update format_response**:
   - Update tool result handling for new tool names

### Phase 3: Add Non-Reset Session End Flag

**File: `backend/api/admin.py`**

**Changes needed:**

1. **Update handle_end_test_session**:
   - Add `reset_connection` parameter (default: True)
   - Use flag value in WebSocket message
   - Only disconnect if `reset_connection` is True
   - Add appropriate logging

### Phase 4: Add Delta Testing Automation

**File: `backend/api/admin.py`**

**Add new command handler:**

- `handle_set_delta` - Set delta data for testing
- Update router to handle `set_delta` command
- Add `update_session_settings` method to TestingSessionManager

### Phase 5: Fix client_id Saving in Test Scripts

**File: `backend/testing/function_check.sh`**

**Changes needed:**

1. **Update exec_curl function**:
   - Only extract session_id and client_id from `start_test_session` response
   - Check command type before attempting extraction
   - Prevent overwriting with "null"

### Phase 6: Update Test Scripts

**File: `backend/testing/function_check.sh`**

**Add new test sections:**

**Step 2.5: Test New AI Functions**
- Test `get_message_history`
- Test `post_message`
- Test `roll_dice`
- Test `get_encounter`

**Step 3.5: Test Delta Tracking**
- Set custom delta data
- End session WITHOUT resetting WebSocket
- Start second round on same session
- Post completion message
- Final end with reset

**Update existing steps:**
- Step 2: Use new command names
- Step 3: Remove `post_messages` tests
- Step 4: Already correct

## Implementation Order

1. Fix `testing_harness.py` - Add WSO generation, update delta format
2. Fix `testing_command_processor.py` - Update to new tool names, add new tools
3. Update `admin.py` - Add non-reset flag, add set_delta command
4. Update `function_check.sh` - Fix client_id saving, add new tests
5. Add `TestingSessionManager.update_session_settings` - Support delta updates
6. Update `TESTING.md` - Document new commands and flow

## Verification Plan

After implementation, verify:

1. **WSO in Initial Prompt:**
   - Start test session
   - Check initial_prompt contains "World State Overview:" section
   - Should NOT show "Changes since last prompt:" on first turn

2. **Delta on Second Turn:**
   - Run delta test flow
   - On second round initial_prompt should show "Changes since last prompt:"
   - Should include NewDiceRolls, EncounterStarted, etc.

3. **New Tool Names Work:**
   - `get_message_history 15` succeeds
   - `post "message"` succeeds
   - `roll_dice 1d20+5` succeeds
   - `get_encounter` succeeds

4. **WebSocket Reset Control:**
   - End with `reset_connection: false` keeps connection
   - End without flag (or `true`) resets connection

5. **client_id Saves Correctly:**
   - Only saves on start_test_session
   - Subsequent calls don't overwrite with "null"

## Related Files

- `backend/services/ai_services/testing_harness.py`
- `backend/services/ai_services/testing_command_processor.py`
- `backend/api/admin.py`
- `backend/services/system_services/testing_session_manager.py`
- `backend/testing/function_check.sh`
- `backend/testing/TESTING.md`

## Status

**Created:** 2025-12-27
**Status:** Ready for implementation
**Priority:** High - Testing infrastructure fixes required for Patch 0.3.9
