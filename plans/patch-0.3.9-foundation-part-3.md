# Patch 0.3.9 Foundation - Part 3: Testing Fixes & Frontend Integration

**Status:** In Progress
**Branch:** feature/0.3.9-the-foundation
**Previous Commits:**
- 04cdef91: Core Implementation (AI functions, WSO, delta tracking)
- 518a61d6: Testing Infrastructure Updates

---

## Overview

This document outlines the third and final phase of Patch 0.3.9 "The Foundation" implementation:
1. Fix remaining tool name references
2. Implement universal JSON pretty-printing for test outputs
3. Add multi-turn delta testing to verify WSO behavior
4. Document frontend integration requirements

---

## Issues Identified from Testing

### Issue 1: Old Tool Name References Still Present

**Root Cause:** `testing_harness.py` still checks for old command names in `_handle_tool_call` method.

**Current Code:**
```python
elif command in ['get_messages', 'post', 'post_messages', 'tool_call']:
    return await self._handle_tool_call(...)
```

**Expected Code:**
```python
elif command in ['get_message_history', 'post_message', 'roll_dice', 'get_encounter', 'tool_call']:
    return await self._handle_tool_call(...)
```

**Impact:** Tools are parsed correctly but routing fails, causing "Unknown command" errors.

### Issue 2: initial_prompt Has Escaped Newlines

**Root Cause:** JSON fields in admin responses are returned as raw strings with `\n` escape sequences instead of formatted JSON.

**Current Output:**
```json
{
  "initial_prompt": "You are an AI assistant...\n\nWorld State Overview:\n{\n  \"session_info\": {\n    ..."
}
```

**Expected Output:**
```json
{
  "initial_prompt": "You are an AI assistant...\n\nWorld State Overview:\n{\n  \"session_info\": {\n    \"game_system\": \"dnd5e\",\n    ..."
}
```

**Note:** The issue is that `\n` should be literal newlines when displayed, not escaped sequences.

### Issue 3: No Multi-Turn Delta Testing

**Root Cause:** `function_check.sh` only tests a single session. No verification that:
- First session receives World State Overview
- Second session (without WebSocket reset) receives delta updates
- Subsequent turns use delta format instead of full WSO

**Impact:** Can't verify critical WSO/delta functionality works correctly.

---

## Phase 1: Fix Tool Name References

### 1.1 Update testing_harness.py

**File:** `backend/services/ai_services/testing_harness.py`

**Change:** Update command check in `_handle_tool_call` method

**Location:** Around line 470

```python
# BEFORE:
elif command in ['get_messages', 'post', 'post_messages', 'tool_call']:

# AFTER:
elif command in ['get_message_history', 'post_message', 'roll_dice', 'get_encounter', 'tool_call']:
```

### 1.2 Check ai_tool_executor.py

**File:** `backend/services/ai_tools/ai_tool_executor.py`

**Actions:**
1. Verify tool routing uses correct names
2. Update any remaining old references in comments
3. Ensure method names match new tool names

**Expected Methods:**
- `execute_get_message_history` (not `execute_get_messages`)
- `execute_post_message` (not `execute_post_messages`)
- `execute_roll_dice`
- `execute_get_encounter`

### 1.3 Update Documentation

**Files to Update:**
- `CHANGELOG.md` - Update tool references
- `backend/services/system_services/universal_settings.py` - Update description
- `backend/api/api_chat.py` - Update comments
- `backend/testing/TESTING.md` - Update all examples

**Search & Replace:**
- `get_messages` → `get_message_history`
- `post_messages` → `post_message`
- Update parameter: `count` → `limit`

---

## Phase 2: Universal JSON Pretty-Printing Solution

### 2.1 Create Utility Function

**File:** `backend/api/admin.py`

**Add this function at the top of the file (after imports):**

```python
def pretty_print_json_fields(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Recursively detect and pretty-print JSON string fields in dictionaries.
    
    Args:
        data: Dictionary that may contain JSON string fields
        
    Returns:
        Dictionary with JSON fields pretty-printed
    """
    result = {}
    
    for key, value in data.items():
        if isinstance(value, dict):
            # Recursively process nested dictionaries
            result[key] = pretty_print_json_fields(value)
        elif isinstance(value, list):
            # Process lists of dictionaries
            result[key] = [
                pretty_print_json_fields(item) if isinstance(item, dict) else item
                for item in value
            ]
        elif isinstance(value, str):
            # Try to parse as JSON and pretty-print
            try:
                parsed = json.loads(value)
                result[key] = json.dumps(parsed, indent=2, ensure_ascii=False)
            except (json.JSONDecodeError, TypeError):
                # Not JSON, return as-is
                result[key] = value
        else:
            # Non-string, non-dict values
            result[key] = value
    
    return result
```

### 2.2 Apply to All Admin Responses

**Update these response return statements in `admin.py`:**

1. **handle_start_test_session** - Apply to `initial_prompt_result`
2. **handle_test_command** - Apply to `result`
3. **handle_execute_test_commands** - Apply to `results` array
4. **handle_get_test_session_state** - Apply to `session_state`

**Example for handle_start_test_session:**

```python
# BEFORE:
return {
    'status': 'success',
    'command': 'start_test_session',
    'test_session_id': test_session_id,
    'client_id': client_id,
    'initial_prompt': initial_prompt_result['initial_prompt'],
    ...
}

# AFTER:
return pretty_print_json_fields({
    'status': 'success',
    'command': 'start_test_session',
    'test_session_id': test_session_id,
    'client_id': client_id,
    'initial_prompt': initial_prompt_result['initial_prompt'],
    ...
})
```

**Benefits:**
- ✅ Universal - works for all current and future tools
- ✅ Recursive - handles nested JSON structures
- ✅ Non-breaking - only affects JSON string fields
- ✅ Automatic - no updates needed for new admin commands

---

## Phase 3: Add Multi-Turn Delta Testing

### 3.1 Add Delta Test to function_check.sh

**File:** `backend/testing/function_check.sh`

**Add this new step after "Step 4: End Test Session":**

```bash
echo "Step 5: Delta Testing (Multi-Turn)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# End session WITHOUT WebSocket reset
exec_curl "End Session (Keep WebSocket)" '{
  "command": "end_test_session",
  "test_session_id": "'"$TEST_SESSION_ID"'",
  "reset_connection": false
}'

echo "⏸️  WebSocket connection preserved for next session..."
echo ""

# Start new session (should use delta, not full WSO)
echo "Starting second session to verify delta updates..."
exec_curl "Start Session 2 (Delta Test)" '{
  "command": "start_test_session"
}'

# Get new session ID from response
echo "📝 Note: Compare initial_prompt above with Session 1:"
echo "   - Session 1 should have: 'World State Overview'"
echo "   - Session 2 should have: 'Changes since last prompt'"
echo ""

# Test commands on second session
exec_curl "Get Message History (Delta Turn)" '{
  "command": "test_command",
  "test_session_id": "'"$TEST_SESSION_ID"'",
  "test_command": "get_message_history 5"
}'

# End final session
exec_curl "End Session 2" '{
  "command": "end_test_session",
  "test_session_id": "'"$TEST_SESSION_ID"'",
  "reset_connection": true
}'
```

### 3.2 Update Verification Checklist

**Update the verification section at the end of function_check.sh:**

```bash
echo "✅ Verification Checklist:"
echo ""
echo "1. Check Session 1 initial_prompt:"
echo "   ✓ Should contain: 'World State Overview:'"
echo "   ✓ Should show: session_info, active_scene, party_compendium, etc."
echo ""
echo "2. Check Session 2 initial_prompt:"
echo "   ✓ Should NOT contain: 'World State Overview:'"
echo "   ✓ Should contain: 'Changes since last prompt:'"
echo "   ✓ Should show: [NewMessages: X, DeletedMessages: Y]"
echo ""
echo "3. Check Foundry VTT chat - Should see 7 messages:"
echo "   - 'Individual test message'"
echo "   - 'Multi-test message 1, 2, 3'"
echo ""
echo "4. Check Foundry VTT dice rolls - Should see 2 dice roll results:"
echo "   - First: roll_dice 1d20+5"
echo "   - Second: roll_dice 2d6"
echo ""
echo "5. Check backend logs:"
echo "   - Session 1: 'World State Overview generated'"
echo "   - Session 2: No WSO generation (using deltas)"
echo ""
echo "📊 Test Results:"
echo "   ✅ Session 1: 10 commands executed (full WSO)"
echo "   ✅ Session 2: 2 commands executed (delta mode)"
echo "   ✅ WebSocket preserved between sessions"
echo "   ✅ Total: 12 test commands across 2 sessions"
```

---

## Phase 4: Frontend Integration Requirements

### 4.1 WebSocket Message Protocol

**Initial Connection:**

Frontend must send these messages immediately after WebSocket connection:

```javascript
// Send scene information
ws.send(JSON.stringify({
  type: 'scene_info',
  data: {
    scene_id: currentScene.id,
    scene_name: currentScene.name,
    active_actors: getActiveActors(),
    grid_size: canvas.scene.grid.size
  }
}));

// Send party information
ws.send(JSON.stringify({
  type: 'party_info',
  data: {
    party_members: getPartyMembers(),
    party_level: getPartyLevel(),
    party_classes: getPartyClasses()
  }
}));
```

### 4.2 Delta Tracking Service

**New Service: `frontend-delta-service.js`**

**Responsibilities:**
1. Track dice rolls as they occur
2. Track combat events (start, end, turn changes)
3. Build PascalCase delta objects
4. Send deltas before AI requests

**Delta Format:**
```javascript
class FrontendDeltaService {
  constructor() {
    this.lastMessageCount = 0;
    this.lastDeletedCount = 0;
    this.currentDelta = {
      NewMessages: 0,
      DeletedMessages: 0,
      NewDiceRolls: [],
      EncounterStarted: false,
      EncounterEnded: false,
      CurrentTurnActor: null
    };
  }

  trackDiceRoll(roll) {
    this.currentDelta.NewDiceRolls.push({
      formula: roll.formula,
      result: roll.result,
      total: roll.total,
      actor: roll.actorName,
      timestamp: Date.now()
    });
  }

  trackCombatEvent(eventType, data) {
    if (eventType === 'encounter_start') {
      this.currentDelta.EncounterStarted = true;
    } else if (eventType === 'encounter_end') {
      this.currentDelta.EncounterEnded = true;
    } else if (eventType === 'turn_change') {
      this.currentDelta.CurrentTurnActor = data.actorName;
    }
  }

  getDelta() {
    const delta = {...this.currentDelta};
    this.currentDelta = this.resetDelta();
    return delta;
  }

  resetDelta() {
    return {
      NewMessages: 0,
      DeletedMessages: 0,
      NewDiceRolls: [],
      EncounterStarted: false,
      EncounterEnded: false,
      CurrentTurnActor: null
    };
  }
}
```

### 4.3 Chat Request Updates

**Modified Request Format:**

```javascript
async function sendAIRequest(prompt, delta = null) {
  const request = {
    session_id: currentSessionId,
    messages: [{role: 'user', content: prompt}],
    universal_settings: {
      'ai role': settings.aiRole,
      'provider': settings.provider,
      'model': settings.model,
      'message_delta': delta || {
        NewMessages: 0,
        DeletedMessages: 0
      }
    }
  };

  const response = await fetch('/api/chat', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify(request)
  });
  
  return await response.json();
}
```

### 4.4 Session Management

**Multi-Turn Flow:**

```javascript
class AISessionManager {
  constructor() {
    this.isFirstTurn = true;
    this.deltaService = new FrontendDeltaService();
  }

  async takeAITurn() {
    const delta = this.isFirstTurn ? null : this.deltaService.getDelta();
    
    const response = await sendAIRequest("Take your turn as GM", delta);
    
    // Process response...
    
    // Next turn is not first
    this.isFirstTurn = false;
  }

  resetSession() {
    this.isFirstTurn = true;
    this.deltaService.resetDelta();
  }
}
```

### 4.5 UI Enhancements

**Add to `ui-manager.js`:**

1. **Delta Indicator:**
```javascript
function showDeltaStatus(isFirstTurn) {
  const status = document.getElementById('delta-status');
  if (isFirstTurn) {
    status.textContent = 'Turn: 1 (World State Overview)';
    status.className = 'delta-indicator wso-mode';
  } else {
    status.textContent = 'Turn: >1 (Delta Updates)';
    status.className = 'delta-indicator delta-mode';
  }
}
```

2. **Turn Counter:**
```javascript
let turnNumber = 1;

function incrementTurn() {
  turnNumber++;
  showDeltaStatus(false);
  updateTurnCounter();
}
```

3. **Combat State Display:**
```javascript
function updateCombatState(delta) {
  if (delta.EncounterStarted) {
    showNotification('Combat Started');
  }
  if (delta.EncounterEnded) {
    showNotification('Combat Ended');
  }
  if (delta.CurrentTurnActor) {
    updateCurrentTurnDisplay(delta.CurrentTurnActor);
  }
}
```

---

## Testing & Validation

### Backend Tests

1. **Unit Tests:**
   - Test `pretty_print_json_fields` with various inputs
   - Test tool name routing in testing_harness
   - Test delta generation in world_state_generator

2. **Integration Tests:**
   - Run `function_check.sh` - should pass all 12 commands
   - Verify Session 1 has WSO, Session 2 has deltas
   - Verify JSON fields are pretty-printed

3. **Manual Testing:**
   - Start test session, check initial_prompt formatting
   - Execute roll_dice, verify output
   - Multi-turn session with WebSocket preserved

### Frontend Tests (TODO)

1. **WebSocket Tests:**
   - Verify scene_info sent on connection
   - Verify party_info sent on connection
   - Verify delta updates sent before AI requests

2. **Delta Service Tests:**
   - Track dice rolls, verify delta.NewDiceRolls
   - Start combat, verify delta.EncounterStarted
   - Change turns, verify delta.CurrentTurnActor

3. **Session Tests:**
   - First turn: Verify no delta sent, WSO in prompt
   - Second turn: Verify delta sent, no WSO in prompt
   - Reset session: Verify back to first turn behavior

---

## Success Criteria

✅ All tool name references updated (get_messages → get_message_history, etc.)
✅ initial_prompt displays with proper formatting (no escaped \n)
✅ Multi-turn delta test passes (WSO on first, deltas on subsequent)
✅ function_check.sh executes 12 commands across 2 sessions
✅ All JSON fields in admin responses are pretty-printed
✅ Frontend integration requirements documented

---

## Next Steps After This Phase

1. **Frontend Implementation:**
   - Update WebSocket client to send scene/party info
   - Implement delta tracking service
   - Update chat request format
   - Add UI indicators for WSO/delta modes

2. **End-to-End Testing:**
   - Test real multi-turn AI sessions
   - Verify WSO generation with real Foundry data
   - Verify delta tracking with real dice rolls/combat

3. **Documentation:**
   - Update user documentation with new tool names
   - Add frontend integration guide
   - Create video tutorial for delta testing

4. **Release:**
   - Update CHANGELOG.md with all changes
   - Tag release: v0.3.9
   - Update module.json version
   - Create release notes

---

**Last Updated:** 2025-12-27
**Maintainer:** @ssjmarx
