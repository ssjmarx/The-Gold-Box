# The Gold Box - Testing Harness

## Overview

The Testing Harness allows you to test AI functions without calling an actual AI service. It intercepts chat requests and routes them to simulated AI responses controlled via curl commands.

## Architecture

```
┌─────────────────┐
│   Frontend     │
│  (Foundry VTT) │
└────────┬────────┘
         │ WebSocket
         ▼
┌──────────────────────────────┐
│      Backend Server         │
│                            │
│  ┌────────────────────┐   │
│  │ Test Session Start  │───┐
│  └────────────────────┘   │
│                             │
│  ┌────────────────────┐   │
│  │  WebSocket Handler │   │
│  └────────────────────┘   │
│           │               │
│           │ Test session?  │
│           ▼               │
│  ┌────────────────────┐   │
│  │ Testing Harness    │◀──┼── Admin Endpoint
│  │  (Mock AI)        │   │   (curl commands)
│  └────────────────────┘   │
│                            │
└────────────────────────────┘
```

## Quick Start

### 1. Start a Test Session

```bash
cd backend
GOLD_BOX_ADMIN_PASSWORD=your_password bash -c \
  'source testing/test_harness_helpers.sh && start_test <client_id>'
```

Example:
```bash
GOLD_BOX_ADMIN_PASSWORD=swag bash -c \
  'source testing/test_harness_helpers.sh && start_test gb-wo2BPutUGT9XDlH9-c45265b0'
```

**What happens:**
- Creates a test session in backend
- Generates initial prompt (same format as real AI)
- Sends `test_session_start` WebSocket message to frontend
- Frontend displays test session notification
- AI turn button is blocked (testing mode active)

### 2. Get Client ID

From Foundry VTT console:
```javascript
game.settings.get('the-gold-box', 'clientId')
```

Or check backend logs for:
```
WebSocket connection confirmed: {client_id: 'gb-...'}
```

### 3. Run Test Commands

```bash
# Get messages from chat
GOLD_BOX_ADMIN_PASSWORD=swag bash -c \
  'source testing/test_harness_helpers.sh && send_test_command "" "get_messages 15"'

# Post a test message
GOLD_BOX_ADMIN_PASSWORD=swag bash -c \
  'source testing/test_harness_helpers.sh && send_test_command "" "post Hello from testing"'

# Get session status
GOLD_BOX_ADMIN_PASSWORD=swag bash -c \
  'source testing/test_harness_helpers.sh && send_test_command "" "status"'

# End test session
GOLD_BOX_ADMIN_PASSWORD=swag bash -c \
  'source testing/test_harness_helpers.sh && send_test_command "" "stop"'
```

## Test Commands Reference

### get_messages `<count>`

Collects `<count>` messages from Foundry chat (default: 15)

**Example:**
```bash
send_test_command "" "get_messages 10"
```

**Returns:**
```json
{
  "messages": [
    {"content": "Hello", "speaker": "John", "type": "chat", "ts": 1234567890},
    ...
  ],
  "count": 10
}
```

### post `<message>`

Posts a single message to chat (as if AI said it)

**Example:**
```bash
send_test_command "" "post The goblin attacks with his dagger!"
```

**Returns:**
```json
{
  "success": true,
  "message": "Message posted to chat",
  "message_content": "The goblin attacks with his dagger!"
}
```

### post_messages `<message1>` `<message2>` ...

Posts multiple messages to chat

**Example:**
```bash
send_test_command "" "post_messages \"Roll 1d20\" \"Roll 1d8\""
```

### stop

Ends the test session

**Example:**
```bash
send_test_command "" "stop"
```

**Returns:**
```json
{
  "success": true,
  "message": "Test session ended",
  "session_summary": {
    "duration_seconds": 45,
    "commands_executed": 5,
    "messages_posted": 3
  }
}
```

### status

Get current session status

**Example:**
```bash
send_test_command "" "status"
```

**Returns:**
```json
{
  "test_session_id": "8f5135eb-9442-4d8b-a162-ecf72eb66590",
  "state": "awaiting_input",
  "conversation_length": 2,
  "commands_executed": 3,
  "tools_used": ["get_messages", "post"],
  "start_time": "2025-12-26T17:27:05.963989",
  "last_activity": "2025-12-26T17:28:30.123456"
}
```

### help

Show available commands

**Example:**
```bash
send_test_command "" "help"
```

## Testing AI Functions

### Testing Dice Rolls

```bash
# Get chat context
send_test_command "" "get_messages 10"

# Simulate dice roll (as AI would call the tool)
# You can manually roll dice in Foundry and test the results
send_test_command "" "post The bandit rolls 1d20+5 for his attack: 14"
```

### Testing Function Calling

The testing harness can simulate any AI tool call:

```bash
# Test scene description
send_test_command "" "post The tavern is dimly lit with a few patrons scattered around."

# Test NPC dialogue
send_test_command "" "post \"The barkeep says: 'Welcome, traveler!'\""

# Test combat actions
send_test_command "" "post_messages \"The orc rolls for initiative: 12\" \"The orc attacks with his greatsword!\""
```

### Testing Multiple Tool Calls

```bash
# Simulate AI making multiple function calls in one turn
send_test_command "" "post_messages \
  \"The dungeon entrance looms before you.\" \
  \"A guard notices you and shouts: 'Halt!'" \
  \"The guard rolls for initiative: 8\""
```

### Testing Multiple Commands in One Call

```bash
# Execute multiple commands sequentially
curl -X POST http://localhost:5000/api/admin \
  -H "X-Admin-Password: swag" \
  -H "Content-Type: application/json" \
  -d '{
    "command": "execute_test_commands",
    "test_session_id": "...",
    "commands": [
      "get_messages 10",
      "post_messages [{\"content\":\"Message 1\",\"type\":\"chat-message\"},{\"content\":\"Message 2\",\"type\":\"chat-message\"}]",
      "status"
    ]
  }'
```

**Benefits:**
- Single network request for multiple operations
- Faster test execution
- Atomic test scenarios
- Better for automated testing

## Admin Endpoint API

You can also use the admin endpoint directly with curl:

### Start Test Session

```bash
curl -X POST http://localhost:5000/api/admin \
  -H "X-Admin-Password: swag" \
  -H "Content-Type: application/json" \
  -d '{
    "command": "start_test_session",
    "client_id": "gb-wo2BPutUGT9XDlH9-c45265b0",
    "universal_settings": {
      "ai role": "gm"
    }
  }'
```

### Execute Test Command

```bash
curl -X POST http://localhost:5000/api/admin \
  -H "X-Admin-Password: swag" \
  -H "Content-Type: application/json" \
  -d '{
    "command": "test_command",
    "test_session_id": "8f5135eb-9442-4d8b-a162-ecf72eb66590",
    "test_command": "get_messages 15"
  }'
```

### End Test Session

**Note:** Ending a test session automatically resets the WebSocket connection and forces the frontend to reconnect with a new client ID. This ensures clean state between test sessions.

```bash
curl -X POST http://localhost:5000/api/admin \
  -H "X-Admin-Password: swag" \
  -H "Content-Type: application/json" \
  -d '{
    "command": "end_test_session",
    "test_session_id": "8f5135eb-9442-4d8b-a162-ecf72eb66590"
  }'
```

### Execute Multiple Test Commands

Executes multiple test commands in a single API call. Commands are executed sequentially, and results are returned for each command even if some fail.

```bash
curl -X POST http://localhost:5000/api/admin \
  -H "X-Admin-Password: swag" \
  -H "Content-Type: application/json" \
  -d '{
    "command": "execute_test_commands",
    "test_session_id": "8f5135eb-9442-4d8b-a162-ecf72eb66590",
    "commands": [
      "get_messages 10",
      "post_messages [{\"content\":\"Message 1\",\"type\":\"chat-message\"},{\"content\":\"Message 2\",\"type\":\"chat-message\"}]",
      "post \"Single message\"",
      "status"
    ]
  }'
```

**Returns:**
```json
{
  "status": "success",
  "command": "execute_test_commands",
  "test_session_id": "8f5135eb-9442-4d8b-a162-ecf72eb66590",
  "results": [
    {
      "index": 0,
      "command": "get_messages 10",
      "status": "success",
      "result": {
        "messages": [...],
        "count": 10
      }
    },
    {
      "index": 1,
      "command": "post_messages [...]",
      "status": "success",
      "result": {
        "messages_sent": 2,
        "results": [...]
      }
    },
    {
      "index": 2,
      "command": "post \"Single message\"",
      "status": "error",
      "error": "Invalid JSON in request body"
    }
  ],
  "summary": {
    "total": 3,
    "succeeded": 2,
    "failed": 1
  }
}
```

### List All Test Sessions

```bash
curl -X POST http://localhost:5000/api/admin \
  -H "X-Admin-Password: swag" \
  -H "Content-Type: application/json" \
  -d '{
    "command": "list_test_sessions"
  }'
```

### Get Test Session State

```bash
curl -X POST http://localhost:5000/api/admin \
  -H "X-Admin-Password: swag" \
  -H "Content-Type: application/json" \
  -d '{
    "command": "get_test_session_state",
    "test_session_id": "8f5135eb-9442-4d8b-a162-ecf72eb66590"
  }'
```

## How It Works

### 1. Session Creation

When you start a test session:
1. Admin endpoint creates a session with unique ID
2. Backend generates initial prompt (same format as real AI)
3. Backend sends `test_session_start` WebSocket message to frontend
4. Frontend receives notification and enters testing mode
5. AI turn button is blocked (visually disabled)
6. Session state is "awaiting_input"

### 2. Command Execution

When you send a test command:
1. Admin endpoint receives command via HTTP (curl)
2. Command is parsed and validated
3. TestingHarness executes the command
4. Results are formatted as AI responses
5. Messages are sent to Foundry chat
6. Session state is updated
7. Response is returned to curl

### 3. Session End

When you send `stop` command:
1. Session summary is generated
2. WebSocket connection is disconnected (forces frontend to reconnect with new client ID)
3. Backend sends `test_session_end` message to frontend
4. Frontend receives notification and exits testing mode
5. Frontend automatically reconnects with new client ID
6. AI turn button is re-enabled
7. Final summary is returned

**WebSocket Reset Behavior:**
- The WebSocket connection is always reset when ending a test session
- Frontend disconnects and reconnects after 1 second
- A new client ID is generated (new UUID suffix)
- This ensures clean state for subsequent test sessions

## Frontend Integration

The testing harness is transparent to the frontend:

- **WebSocket Messages:**
  - `test_session_start` - Triggers test mode
  - `test_chat_response` - Displays test results

- **Visual Indicators:**
  - Notification when test session starts
  - Chat message with test session details
  - AI turn button is disabled during testing

- **Normal Flow:**
  - Frontend sends `chat_request` with `test: true` flag
  - Backend detects active test session
  - Request is routed to testing harness instead of AI service

## Troubleshooting

### "Unknown message type: test_session_start"

Ensure frontend JavaScript is updated with test session handlers:
- `scripts/api/websocket-client.js` should have `handleTestSessionStart()` and `handleTestChatResponse()` methods

### Test session not routing to testing harness

Check backend logs for:
```
Active test session found for client <client_id>
Routing chat_request to testing harness
```

If not appearing, check that:
- Test session was started with correct client_id
- Session is still active (not ended)
- WebSocket handler has test session routing logic

### Messages not appearing in chat

Check that:
- Messages have valid content
- You have permission to post to chat
- Backend is connected to Foundry API
- No errors in backend logs

### Client ID mismatch

Always use the current client_id from the frontend:
```javascript
// Foundry VTT console
window.goldBoxWebSocketClient.clientId
```

Or check backend logs for the current connected client.

## Advanced Usage

### Automated Testing Script

Create a test script to run multiple commands:

```bash
#!/bin/bash
# test_scenario.sh

source backend/testing/test_harness_helpers.sh

# Start test
start_test gb-wo2BPutUGT9XDlH9-c45265b0

# Get context
send_test_command "" "get_messages 10"

# Test AI response
send_test_command "" "post The goblin approaches cautiously."

# Test multiple messages
send_test_command "" "post_messages \"Goblin rolls for initiative: 15\" \"Goblin attacks with short sword!\""

# Check status
send_test_command "" "status"

# End test
send_test_command "" "stop"
```

### Testing AI Function Responses

Simulate how AI would respond to specific tools:

```bash
# Scene description
send_test_command "" "post The ancient temple is overgrown with vines."

# NPC action
send_test_command "" "post \"The priestess kneels before the altar.\""

# Dice roll
send_test_command "" "post Rolling for perception check: 1d20+4 = 16"

# Multiple NPCs
send_test_command "" "post_messages \
  \"Goblin 1: Attacks with dagger\" \
  \"Goblin 2: Shoots arrow at fighter\" \
  \"Goblin 3: Retreats into darkness\""
```

### Testing Different AI Roles

```bash
# Start test with different roles
curl -X POST http://localhost:5000/api/admin \
  -H "X-Admin-Password: swag" \
  -H "Content-Type: application/json" \
  -d '{
    "command": "start_test_session",
    "client_id": "gb-wo2BPutUGT9XDlH9-c45265b0",
    "universal_settings": {
      "ai role": "player"
    }
  }'
```

Available roles:
- `gm` - Game Master (default)
- `player` - Player assistant
- `narrator` - Storyteller
- `combat` - Combat assistant

## Benefits

### vs. Real AI Service

| Testing Harness | Real AI Service |
|----------------|-----------------|
| ✅ No API costs | ❌ Token costs |
| ✅ Instant responses | ❌ Variable latency |
| ✅ Deterministic results | ❌ Random AI outputs |
| ✅ Easy to debug | ❌ Hard to reproduce issues |
| ✅ Test specific scenarios | ❌ Can't force specific behavior |
| ✅ No rate limits | ❌ Rate limited |
| ❌ Limited to your commands | ✅ Creative responses |

### Testing Capabilities

- **Function Calling:** Test any AI function call
- **Dice Rolls:** Simulate and verify dice mechanics
- **NPC Actions:** Test multiple NPC turns
- **Combat:** Test initiative, attacks, damage
- **Scene Description:** Test world-building functions
- **Dialogue:** Test NPC and player interactions

## Implementation Details

### Backend Components

1. **TestingSessionManager** (`backend/services/system_services/testing_session_manager.py`)
   - Session lifecycle management
   - State tracking and cleanup

2. **TestingHarness** (`backend/services/ai_services/testing_harness.py`)
   - Command processing
   - AI response simulation
   - Tool execution

3. **TestingCommandProcessor** (`backend/services/ai_services/testing_command_processor.py`)
   - Command parsing
   - Validation
   - Error handling

4. **Admin Endpoint** (`backend/api/admin.py`)
   - HTTP API for test commands
   - WebSocket integration

5. **WebSocket Handler** (`backend/shared/startup/services.py`)
   - Test session routing
   - Message interception

### Frontend Components

1. **WebSocket Client** (`scripts/api/websocket-client.js`)
   - `test_session_start` handler
   - `test_chat_response` handler
   - Test mode indicators

2. **Helper Scripts** (`backend/testing/test_harness_helpers.sh`)
   - Bash functions for testing
   - Session management

## Available Test Scripts

### `function_check.sh` - Testing Harness Validation

Tests the testing harness functionality including multi-command execution and WebSocket reset.

**Purpose:**
- Validate testing harness functionality
- Test individual commands
- Test multi-command execution
- Test WebSocket reset on session end

**Usage:**
```bash
cd backend/testing
./function_check.sh
```

**What it tests:**
1. Start test session
2. Individual commands (3 commands):
   - Get messages from chat
   - Post single message
   - Check session status
3. Multi-command execution (4 commands):
   - Get messages
   - Post multiple messages (JSON array)
   - Post single message
   - Check status
4. End session with WebSocket reset

**Expected Results:**
- All 7 commands execute successfully
- 6 messages appear in Foundry VTT chat
- WebSocket disconnects and reconnects
- New client ID is generated
- AI turn button re-enables

### `server_test.sh` - Server/API Health Check

Comprehensive server and API endpoint testing including security validation.

**Purpose:**
- Verify server health
- Test API endpoints
- Validate security features
- Check CSRF protection
- Test input validation

**Usage:**
```bash
cd backend/testing
./server_test.sh
```

**What it tests:**
1. Health check endpoint
2. Service information endpoint
3. Security verification endpoint
4. API chat validation
5. CSRF protection (invalid/missing token)
6. Input validation (XSS, SQL injection)
7. Session validation
8. Admin authentication
9. Security headers

**Expected Results:**
- All API endpoints respond correctly
- Security features properly reject invalid requests
- Appropriate HTTP status codes returned
- Security headers present

**Configuration:**
```bash
# Custom server URL
GOLD_BOX_SERVER_URL=http://localhost:5001 ./server_test.sh

# Custom timeout
GOLD_BOX_TEST_TIMEOUT=15 ./server_test.sh
```

### `test_harness_helpers.sh` - Interactive Testing Helper

Bash functions for interactive testing sessions.

**Purpose:**
- Interactive testing of AI functions
- Manual command execution
- Session management

**Usage:**
```bash
cd backend
GOLD_BOX_ADMIN_PASSWORD=swag bash -c \
  'source testing/test_harness_helpers.sh && start_test <client_id>'

# Run test commands
GOLD_BOX_ADMIN_PASSWORD=swag bash -c \
  'source testing/test_harness_helpers.sh && send_test_command "" "get_messages 15"'

# End session
GOLD_BOX_ADMIN_PASSWORD=swag bash -c \
  'source testing/test_harness_helpers.sh && send_test_command "" "stop"'
```

## Test Script Summary

| Script | Purpose | Automation | Scope |
|--------|----------|-------------|--------|
| `function_check.sh` | Testing harness validation | ✅ Automated | Testing harness functionality |
| `server_test.sh` | Server/API health | ✅ Automated | Server endpoints and security |
| `test_harness_helpers.sh` | Interactive testing | ❌ Manual | Manual command execution |

## Future Enhancements

- [x] Multi-command execution in single API call
- [x] WebSocket reset on test session end
- [ ] Test scenario recording and replay
- [ ] Automated test suites
- [ ] Performance benchmarking
- [ ] Test result comparison
- [ ] Visual test editor UI
- [ ] Test coverage reporting

## Recent Enhancements (v0.3.6)

### Multi-Command Execution
- Added `execute_test_commands` admin command
- Execute multiple test commands in single API call
- Returns results for each command with success/failure status
- Continues execution even if some commands fail

### WebSocket Reset on Test End
- Test session end automatically disconnects WebSocket
- Frontend reconnects with new client ID
- Ensures clean state between test sessions
- Prevents stale connections

### Test Scripts Reorganized
- `function_check.sh` - Testing harness validation (renamed from `definitive_test.sh`)
- `server_test.sh` - Server/API health check (renamed from `comprehensive_test.sh`)
- `test_harness_helpers.sh` - Interactive testing helper (unchanged)
- Documentation updated to reflect new script names and purposes

## Running Tests

### Quick Start - Run All Tests

```bash
cd backend/testing

# Test server health and security
./server_test.sh

# Test testing harness functionality
./function_check.sh
```

### Interactive Testing

```bash
cd backend

# Start interactive test session
GOLD_BOX_ADMIN_PASSWORD=swag bash -c \
  'source testing/test_harness_helpers.sh && start_test'

# Then use send_test_command to run tests interactively
```

## Support

For issues or questions:
1. Check backend logs at `backend/shared/server_files/goldbox.log`
2. Check frontend browser console for errors
3. Verify admin password is correct
4. Ensure client_id matches connected client
5. Confirm backend server is running on port 5000
6. Ensure `jq` is installed for test scripts (`sudo apt-get install jq`)
7. Ensure `curl` is installed for test scripts

## License

CC-BY-NC-SA 4.0 (compatible with The Gold Box dependencies)
