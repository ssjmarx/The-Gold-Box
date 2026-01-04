#!/bin/bash
# Test messaging operations with circular verification

# Source helper functions
. ./test_helpers.sh

section_header "Test: Messaging Operations"

echo "📝 NOTE: This test verifies message operations with circular verification"
echo "   • get_message_history → post → get_message_history (confirm messages added)"
echo ""

# Step 1: Start test session
start_session

# Step 2: Get baseline message count
test_command "Get Baseline Message History" "get_message_history 10"
BASELINE_COUNT=$(get_value ".result.count // 0")
echo "📊 Baseline message count: $BASELINE_COUNT"
echo ""

# Step 3: Post single message
test_command "Post Single Message" "post \"Individual test message\""

# Step 4: Post multiple messages as array
test_command "Post Multiple Messages" "post_message [{\"content\":\"Multi-test message 1\",\"type\":\"chat-message\"},{\"content\":\"Multi-test message 2\",\"type\":\"chat-message\"},{\"content\":\"Multi-test message 3\",\"type\":\"chat-message\"}]"

# Allow time for messages to propagate and be cached
sleep 2

# Step 5: Verify messages were added
test_command "Verify Messages Added" "get_message_history 15"
NEW_COUNT=$(get_value ".result.count // 0")
ADDED=$((NEW_COUNT - BASELINE_COUNT))

echo "📊 New message count: $NEW_COUNT"
echo "📊 Messages added: $ADDED (expected: 3-4)"
echo ""

# Allow for 3-4 messages (system messages may cause variance)
if [ $ADDED -ge 3 ] && [ $ADDED -le 4 ]; then
  echo "✅ VERIFICATION PASSED: $ADDED messages added successfully"
else
  echo "❌ VERIFICATION FAILED: Expected 3-4 messages, got $ADDED"
  track_failure
fi
echo ""

# Step 6: Check session status
test_command "Check Session Status" "status"

# Step 7: End session with WebSocket reset
echo ""
echo "ℹ️  Ending session with WebSocket reset..."
end_session true

# Report final test result
report_test_result "Messaging Operations" \
  "Single message posting" \
  "Multiple message posting as array" \
  "Message count verification (3-4 messages added)"

# Exit with appropriate code
if has_failures; then
  exit 1
fi
