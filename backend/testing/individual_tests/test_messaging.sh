#!/bin/bash
# Test messaging operations with circular verification

# Source helper functions
. ./test_helpers.sh

section_header "Test: Messaging Operations"

echo "📝 NOTE: This test verifies message operations with circular verification"
echo "   • get_message_history → post → get_message_history (confirm messages added)"
echo ""

# Initialize client ID tracking
CLIENT_ID_FILE=".test_client_id"
rm -f "$CLIENT_ID_FILE"  # Clean up any stale file

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
fi
echo ""

# Step 6: Check session status
test_command "Check Session Status" "status"

# Step 7: End session with WebSocket reset and wait for reconnection
echo ""
echo "ℹ️  Ending session and waiting for WebSocket reconnection..."
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
echo "✅ Messaging test complete!"
echo "=========================================="
echo ""
echo "Expected results in Foundry VTT chat:"
echo "   • 'Individual test message'"
echo "   • 'Multi-test message 1'"
echo "   • 'Multi-test message 2'"
echo "   • 'Multi-test message 3'"
echo ""
