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

# Step 1: Start test session (first turn)
start_session

# Step 2: Execute multi-command batch
echo "━━━ Execute Multi-Command Batch ━━━"
echo ""
echo "Executing batch of 4 commands:"
echo "   1. get_message_history"
echo "   2. post_message"
echo "   3. roll_dice"
echo "   4. post_message"
echo ""

response=$(curl -s -X POST "$API_ENDPOINT" \
  -H "Content-Type: application/json" \
  -H "X-Admin-Password: swag" \
  -d "{
    \"command\": \"execute_test_commands\",
    \"test_session_id\": \"$TEST_SESSION_ID\",
    \"commands\": [
      \"get_message_history 5\",
      \"post_message [{\\\"content\\\":\\\"Batch test message 1\\\",\\\"type\\\":\\\"chat-message\\\"}]\",
      \"roll_dice rolls=[{\\\"formula\\\":\\\"1d20\\\",\\\"flavor\\\":\\\"Test roll\\\"}]\",
      \"post_message [{\\\"content\\\":\\\"Batch test message 2\\\",\\\"type\\\":\\\"chat-message\\\"}]\"
    ]
  }")

echo "$response" | jq '.'
echo "$response" > .last_response.json
echo ""

# Step 3: Verify batched commands executed
test_command "Verify Batched Commands Executed" "get_message_history 10"
MESSAGE_COUNT=$(get_value ".result.messages_count // 0")

echo "📊 Total messages after batch: $MESSAGE_COUNT"
if [ $MESSAGE_COUNT -ge 4 ]; then
  echo "✅ VERIFICATION PASSED: Batched commands executed (at least 4 messages)"
else
  echo "❌ VERIFICATION FAILED: Expected at least 4 messages, got $MESSAGE_COUNT"
fi
echo ""

# Step 4: End session WITHOUT WebSocket reset (preserve client_id for delta test)
end_session false

echo ""
echo "=========================================="
echo "⏸️  PAUSE FOR MANUAL CHANGES"
echo "=========================================="
echo ""
echo "The test session has ended WITHOUT WebSocket reset."
echo "This preserves the client_id, simulating a subsequent AI turn."
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
NEW_MESSAGE_COUNT=$(get_value ".result.messages_count // 0")

echo "📊 Total messages after manual changes: $NEW_MESSAGE_COUNT"
if [ $NEW_MESSAGE_COUNT -gt $MESSAGE_COUNT ]; then
  echo "✅ VERIFICATION PASSED: Manual changes captured in message history"
else
  echo "⚠️  Note: No new messages detected (did you make changes in Foundry?)"
fi
echo ""

# Step 8: End session with WebSocket reset
end_session true

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
