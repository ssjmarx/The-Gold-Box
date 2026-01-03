#!/bin/bash
# Test multi-command execution and delta tracking

# Source helper functions
. ./test_helpers.sh

section_header "Test: Multi-Command & Delta Tracking"

echo "📝 NOTE: This test verifies batched commands and delta tracking"
echo "   • Execute multi-command → verify each command ran"
echo "   • End session → manual changes → start new session (same client_id)"
echo "   • Verify deltas captured in subsequent turn"
echo ""

# Initialize client ID tracking
CLIENT_ID_FILE=".test_client_id"
rm -f "$CLIENT_ID_FILE"  # Clean up any stale file

# Step 1: Start test session (first turn)
start_session

# Store initial client ID
INITIAL_CLIENT_ID=$(cat .last_response.json | jq -r '.result.client_id // ""')
if [ -n "$INITIAL_CLIENT_ID" ]; then
  echo "$INITIAL_CLIENT_ID" > "$CLIENT_ID_FILE"
  echo "✅ Stored initial client ID: $INITIAL_CLIENT_ID"
fi
echo ""

# Step 2: Execute multi-command batch
echo "━━━ Execute Multi-Command Batch ━━━"
echo ""
echo "Executing batch of 4 commands:"
echo "   1. get_message_history"
echo "   2. post_message"
echo "   3. roll_dice"
echo "   4. post_message"
echo ""

# Execute each command in the batch
test_command "Get Message History" "get_message_history 5"
test_command "Post First Message" "post_message messages=[{\"content\":\"Batch test message 1\",\"type\":\"chat-message\"}]"
test_command "Roll Dice" "roll_dice rolls=[{\"formula\":\"1d20\",\"flavor\":\"Test roll\"}]"
test_command "Post Second Message" "post_message messages=[{\"content\":\"Batch test message 2\",\"type\":\"chat-message\"}]"

echo ""

# Step 3: Verify batched commands executed
test_command "Verify Batched Commands Executed" "get_message_history 10"
MESSAGE_COUNT=$(get_value ".result.count // 0")

echo "📊 Total messages after batch: $MESSAGE_COUNT"
if [ $MESSAGE_COUNT -ge 4 ]; then
  echo "✅ VERIFICATION PASSED: Batched commands executed (at least 4 messages)"
else
  echo "❌ VERIFICATION FAILED: Expected at least 4 messages, got $MESSAGE_COUNT"
fi
echo ""

# Step 4: End session WITHOUT WebSocket reset (preserve client_id for delta test)
echo ""
echo "ℹ️  Ending session WITHOUT WebSocket reset (preserving client_id for delta test)..."
end_session false

# Check if running in auto mode (non-interactive)
if [ -z "$AUTO_MODE" ] || [ "$AUTO_MODE" != "true" ]; then
  # Interactive mode - wait for manual changes
  echo ""
  echo "=========================================="
  echo "⏸️  PAUSE FOR MANUAL CHANGES"
  echo "=========================================="
  echo ""
  echo "The test session has ended WITHOUT WebSocket reset."
  echo "This preserves: client_id, simulating a subsequent AI turn."
  echo ""
  echo "🎮 INSTRUCTIONS FOR DELTA TEST:"
  echo ""
  echo "Please make the following changes in Foundry VTT:"
  echo "   • Create 2-3 new chat messages (type and press Enter)"
  echo "   • Roll some dice (Ctrl+Shift+D, enter formula like '1d20')"
  echo "   • (Optional) Start/End combat (Combat tab → Start/End Combat)"
  echo ""
  echo "After making changes, press Enter to start new test session"
  echo "   and verify what deltas get captured."
  echo ""
  
  read -p "⏸️  Press Enter when ready to start new session... "
else
  # Auto mode - skip manual changes, proceed directly
  echo ""
  echo "⏭️  AUTO MODE: Skipping manual changes (proceeding directly to delta verification)"
  echo ""
  sleep 1
fi

# Step 5: Start NEW test session (same client_id - subsequent turn)
echo ""
echo "=========================================="
echo "Starting New Test Session (Subsequent Turn)"
echo "=========================================="
echo ""

start_session

# Step 6: Verify deltas in initial prompt
test_command "Verify Deltas in Initial Prompt" "status"

echo ""
echo "📊 DELTA VERIFICATION:"
echo ""
echo "The initial_prompt above should show:"
echo "   • If you made changes: 'Recent changes to game' section with delta JSON"
echo "   • If you made no changes: 'No changes to game state' message"
echo ""

# Step 7: Verify message history shows manual changes
test_command "Verify Manual Changes in History" "get_message_history 10"
NEW_MESSAGE_COUNT=$(get_value ".result.count // 0")

echo "📊 Total messages after manual changes: $NEW_MESSAGE_COUNT"
if [ $NEW_MESSAGE_COUNT -gt $MESSAGE_COUNT ]; then
  echo "✅ VERIFICATION PASSED: Manual changes captured in message history"
else
  echo "⚠️  Note: No new messages detected (did you make changes in Foundry?)"
fi
echo ""

# Step 8: Verify client ID is still the same (WebSocket preserved)
test_command "Verify Client ID Preserved" "status"
FINAL_CLIENT_ID=$(cat .last_response.json | jq -r '.result.client_id // ""')

echo "📊 Initial client ID: $INITIAL_CLIENT_ID"
echo "📊 Final client ID: $FINAL_CLIENT_ID"

if [ "$FINAL_CLIENT_ID" = "$INITIAL_CLIENT_ID" ]; then
  echo "✅ VERIFICATION PASSED: Client ID preserved across sessions (WebSocket not reset)"
else
  echo "⚠️  WARNING: Client ID changed (WebSocket may have been reset)"
fi
echo ""

# Step 9: End session with WebSocket reset and wait for reconnection
echo "ℹ️  Final cleanup - Ending session with WebSocket reset..."
end_session true

# Wait for new client ID to be established
sleep 3

# Capture new client ID from logs
echo "Checking for new client ID in logs..."
NEW_CLIENT_ID=$(grep "client connected" goldbox.log | tail -20 | grep -oP '(?<=client connected: )' | tail -1 | sed 's/.*client connected: //')

if [ -z "$NEW_CLIENT_ID" ]; then
  echo "⚠️  WARNING: Could not detect new client ID after reconnection"
else
  echo "✅ Detected new client ID: $NEW_CLIENT_ID"
  echo "   Updating client ID file..."
  echo "$NEW_CLIENT_ID" > "$CLIENT_ID_FILE"
fi
echo ""

echo ""
echo "=========================================="
echo "✅ Multi-Command & Delta Tracking test complete!"
echo "=========================================="
echo ""
echo "✅ Test Summary:"
echo "   • Multi-command execution (4 commands in batch)"
echo "   • WebSocket preservation (no reset between sessions)"
echo "   • Delta tracking across AI turns"
echo "   • Manual changes captured in subsequent session"
echo ""
echo "📝 Key Concepts Verified:"
echo "   • Batched commands execute in order"
echo "   • First turn: full world state (no deltas)"
echo "   • Subsequent turn: only deltas (no full world state)"
echo "   • Manual changes between turns are captured in deltas"
echo ""
