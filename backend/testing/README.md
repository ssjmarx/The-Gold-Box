# Gold Box Testing Suite

## Overview

This directory contains modular test scripts for The Gold Box. Each test focuses on a specific feature area with circular verification to ensure operations work correctly.

## Test Structure

### Helper Scripts

- **`test_helpers.sh`** - Shared utility functions used by all test scripts
  - API request execution
  - Session management
  - Actor/token ID extraction
  - Verification functions

### Feature-Specific Tests

#### 1. **`test_messaging.sh`**
Tests messaging operations with circular verification.

**What it tests:**
- Message history retrieval
- Single message posting
- Multiple message posting (array)
- Message count verification

**Verification loop:** `get_message_history` → post → `get_message_history` (confirm messages added)

**Run:** `./test_messaging.sh`

---

#### 2. **`test_dice_rolling.sh`**
Tests dice rolling functionality.

**What it tests:**
- Single dice roll with flavor
- Multiple dice rolls in one command
- Dice rolls without flavor
- Dice roll count verification

**Verification loop:** `get_message_history` → roll → `get_message_history` (confirm dice rolls added)

**Run:** `./test_dice_rolling.sh`

---

#### 3. **`test_combat.sh`**
Tests combat lifecycle management with state verification.

**What it tests:**
- Encounter creation with initiative rolling
- Encounter creation error handling (already active)
- Turn advancement (multiple times)
- Turn advancement error handling (no combat)
- Encounter deletion
- Encounter deletion error handling (no combat)

**Verification loop:** `get_encounter` → action → `get_encounter` (confirm state changes at each step)

**Run:** `./test_combat.sh`

**Requirements:**
- Must have at least 2 tokens on the scene in Foundry VTT
- Tokens must have associated actors

---

#### 4. **`test_actor_operations.sh`**
Tests actor queries and health management with circular verification.

**What it tests:**
- Full actor sheet retrieval
- Grep-like search functionality (hp, sword, numeric, nonexistent terms)
- Damage application with verification
- Healing application with verification
- Absolute value setting with verification
- Combat state updates
- Error handling (invalid token_id, invalid attribute_path)

**Verification loop:** `get_actor_details` → modify → `get_actor_details` (confirm attribute changes)

**Run:** `./test_actor_operations.sh`

**Requirements:**
- Must have at least 1 token on the scene in Foundry VTT

---

#### 5. **`test_multi_command_and_deltas.sh`**
Tests batched command execution and delta tracking across AI turns.

**What it tests:**
- Multi-command execution (batch of commands in single request)
- WebSocket preservation (no reset between sessions)
- Delta tracking across AI turns
- Manual changes captured in subsequent session

**Features:**
- **Interactive:** Requires manual user input for delta test portion
- Tests first turn (full world state) vs subsequent turn (deltas only)

**Verification loop:** Execute batch → verify each command ran; End → Start → verify deltas captured

**Run:** `./test_multi_command_and_deltas.sh`

---

## Running Tests

### Prerequisites

1. Backend server must be running on `http://localhost:5000`
2. Foundry VTT must be loaded with The Gold Box module
3. Foundry VTT must have at least 2 tokens on the active scene (for combat tests)
4. `jq` must be installed for JSON parsing
5. `python3` must be installed for ID extraction
6. Test scripts must be executable: `chmod +x *.sh`

### Individual Tests

Run specific tests based on what you're working on:

```bash
# Test messaging only
./test_messaging.sh

# Test dice rolling only
./test_dice_rolling.sh

# Test combat operations
./test_combat.sh

# Test actor queries and health management
./test_actor_operations.sh

# Test multi-command and delta tracking
./test_multi_command_and_deltas.sh
```

### Running All Tests

You can run all tests in sequence manually:

```bash
./test_messaging.sh && \
./test_dice_rolling.sh && \
./test_combat.sh && \
./test_actor_operations.sh && \
./test_multi_command_and_deltas.sh
```

---

## Test Output

Each test provides:
- **Section headers** clearly marking each test phase
- **Verification steps** with ✅ PASSED or ❌ FAILED indicators
- **Data extraction** showing counts, IDs, and values at each step
- **Summary** of what was tested
- **Expected results** in Foundry VTT

---

## Circular Verification Pattern

All tests use circular verification to ensure operations actually change state:

1. **Baseline:** Query current state (e.g., message count, HP value, combat status)
2. **Action:** Perform operation (e.g., post message, apply damage, advance turn)
3. **Verify:** Query state again and confirm expected change occurred
4. **Compare:** Baseline vs. new state to verify operation succeeded

This pattern catches issues where operations appear to succeed but don't actually modify game state.

---

## Troubleshooting

### Test Fails to Start

- **Check:** Backend server is running (`http://localhost:5000`)
- **Check:** Admin password is set to "swag" in script (matches server config)

### No Actor/Token IDs Found

- **Check:** Foundry VTT has tokens placed on the active scene
- **Check:** Tokens have associated actors
- **Action:** Place tokens in Foundry VTT before running combat or actor tests

### WebSocket Connection Issues

- **Check:** Foundry VTT is connected to backend
- **Check:** No browser console errors for WebSocket
- **Action:** Refresh Foundry VTT page and ensure module loads

### Verification Failures

- **Review:** Test output for specific verification step that failed
- **Check:** Backend logs for errors
- **Check:** Foundry VTT console for errors during operation

---

## Helper Functions Reference

### `exec_request(desc, data)`
Execute API request, display response, save to `.last_response.json`

### `start_session()`
Start test session, save session ID and client ID to files

### `test_command(desc, cmd)`
Execute test command in current session

### `create_encounter(desc, actor_ids, roll_initiative)`
Create encounter using Python helper for JSON construction

### `end_session(reset=true/false)`
End test session, optionally reset WebSocket connection

### `extract_actor_ids()`
Extract actor IDs from saved world state JSON

### `extract_token_id()`
Extract token ID from saved world state JSON

### `verify_success()`
Check last response for success status

### `verify_error()`
Check last response for expected error

### `get_value(path)`
Extract value from `.last_response.json` using jq path

### `section_header(title)`
Display formatted section header

---

## Test Data Files

Each test creates/uses:
- **`.last_response.json`** - Most recent API response
- **`.test_session_id`** - Current session ID
- **`.test_client_id`** - Current client ID

These files can be useful for debugging failed tests.

---

## Migration from function_check.sh

The old `function_check.sh` has been removed and replaced by these modular tests:

| Old Test Area | New Test Script |
|---------------|------------------|
| Basic Commands | `test_messaging.sh` |
| Dice Rolling | `test_dice_rolling.sh` |
| Combat Status | `test_combat.sh` |
| Encounter Management | `test_combat.sh` |
| Turn Management | `test_combat.sh` |
| Actor Details | `test_actor_operations.sh` |
| Health Management | `test_actor_operations.sh` |
| Multi-Command | `test_multi_command_and_deltas.sh` |
| Delta Tracking | `test_multi_command_and_deltas.sh` |

---

## Development Workflow

When developing a new feature:

1. Identify which test script covers your feature
2. Run that specific test to verify baseline
3. Make your changes
4. Re-run the test to verify your changes work
5. Fix any issues found
6. Repeat until test passes

This focused testing approach speeds up development by isolating what you're testing.
