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
BASELINE_COUNT=$(get_value ".result.messages_count // 0")
echo "📊 Baseline message count: $BASELINE_COUNT"
echo ""

# Step 3: Post single message
test_command "Post Single Message" "post \"Individual test message\""

# Step 4: Post multiple messages as array
test_command "Post Multiple Messages" "post_messages [{\"content\":\"Multi-test message 1\",\"type\":\"chat-message\"},{\"content\":\"Multi-test message 2\",\"type\":\"chat-message\"},{\"content\":\"Multi-test message 3\",\"type\":\"chat-message\"}]"

# Step 5: Verify messages were added
test_command "Verify Messages Added" "get_message_history 15"
NEW_COUNT=$(get_value ".result.messages_count // 0")
ADDED=$((NEW_COUNT - BASELINE_COUNT))

echo "📊 New message count: $NEW_COUNT"
echo "📊 Messages added: $ADDED (expected: 4)"
echo ""

if [ $ADDED -eq 4 ]; then
  echo "✅ VERIFICATION PASSED: 4 messages added successfully"
else
  echo "❌ VERIFICATION FAILED: Expected 4 messages, got $ADDED"
fi
echo ""

# Step 6: Check session status
test_command "Check Session Status" "status"

# Step 7: End session with WebSocket reset
end_session true

echo ""
echo "=========================================="
echo "✅ Messaging test complete!"
echo "=========================================="
echo ""
echo "Expected results in Foundry VTT chat:"
echo "   • 'Individual test message'"
echo "   • 'Multi-test message 1'"
echo "   • 'Multi-test message 2'"
echo "   • 'Multi-test message 3'"
echo ""
