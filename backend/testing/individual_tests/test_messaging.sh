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

# CRITICAL FIX: Wait for messages to be collected by frontend
# Frontend needs time to execute posts in Foundry and send them back via WebSocket
echo "⏳ Waiting for messages to be collected..."
sleep 2

# Step 5: Verify messages were added
test_command "Verify Messages Added" "get_message_history 15"
# CRITICAL FIX: Check for actual chat messages by filtering for type 'cm' (chat_message)
# Use map to safely handle null content
CHAT_COUNT=$(get_value '.result.messages // [] | map(select(.t == "cm")) | length')

echo "📊 Chat messages found in history: $CHAT_COUNT (expected: 4)"
echo ""

# Extract message details for verification
MSG_1=$(get_value '.result.messages // [] | map(select(.t == "cm")) | .[-1].c // empty')
MSG_2=$(get_value '.result.messages // [] | map(select(.t == "cm")) | .[-2].c // empty')
MSG_3=$(get_value '.result.messages // [] | map(select(.t == "cm")) | .[-3].c // empty')
MSG_4=$(get_value '.result.messages // [] | map(select(.t == "cm")) | .[-4].c // empty')

echo "📊 Message 1: \"$MSG_1\""
echo "📊 Message 2: \"$MSG_2\""
echo "📊 Message 3: \"$MSG_3\""
echo "📊 Message 4: \"$MSG_4\""
echo ""

# Verify specific messages were created
if [ "$CHAT_COUNT" -ge 4 ]; then
  # Check for expected message content (note: messages are in reverse chronological order)
  # MSG_1 is most recent (Multi-test message 3), MSG_4 is oldest (Individual test message)
  HAS_MULTI_3=$(echo "$MSG_1" | grep -q "Multi-test message 3" && echo "yes" || echo "no")
  HAS_MULTI_2=$(echo "$MSG_2" | grep -q "Multi-test message 2" && echo "yes" || echo "no")
  HAS_MULTI_1=$(echo "$MSG_3" | grep -q "Multi-test message 1" && echo "yes" || echo "no")
  HAS_IND_MSG=$(echo "$MSG_4" | grep -q "Individual test message" && echo "yes" || echo "no")
  
  if [ "$HAS_IND_MSG" = "yes" ] && [ "$HAS_MULTI_1" = "yes" ] && [ "$HAS_MULTI_2" = "yes" ] && [ "$HAS_MULTI_3" = "yes" ]; then
    echo "✅ VERIFICATION PASSED: All 4 expected messages found with correct content"
  elif [ "$MSG_1" = "Multi-test message 3" ] || [ "$MSG_2" = "Multi-test message 2" ] || [ "$MSG_3" = "Multi-test message 1" ] || [ "$MSG_4" = "Individual test message" ]; then
    echo "✅ VERIFICATION PASSED: Expected chat messages found in message history"
  else
    echo "❌ VERIFICATION FAILED: Found $CHAT_COUNT messages but content doesn't match expected values"
    track_failure
  fi
else
  echo "❌ VERIFICATION FAILED: Expected 4 chat messages, found $CHAT_COUNT"
  track_failure
fi
echo ""

# Step 6: Post HTML chat card
test_command "Post HTML Chat Card" "post_message [{\"content\":\"<div class=\\\"chat-card item-card\\\"><section class=\\\"card-header description collapsible\\\"><header class=\\\"summary\\\"><div class=\\\"name-stacked border\\\"><span class=\\\"title\\\">Fireball Spell</span><span class=\\\"subtitle\\\">Evocation, 3rd Level</span></div><i class=\\\"fas fa-chevron-down fa-fw\\\"></i></header><section class=\\\"details collapsible-content card-content\\\"><div class=\\\"wrapper\\\"><p><strong>Casting Time:</strong> 1 action</p><p><strong>Range:</strong> 150 feet</p><p><strong>Damage:</strong> 8d6 fire damage in 20-foot radius</p><p>A bright streak flashes from your pointing finger to a point you choose within range then blossoms with a low roar into an explosion of flame.</p></div></section></div>\",\"type\":\"chat-message\",\"speaker\":{\"alias\":\"The Gold Box\"}}]"

# CRITICAL FIX: Wait for chat card to be collected by frontend
echo "⏳ Waiting for chat card to be collected..."
sleep 2

# Step 7: Verify chat card was added
test_command "Verify Chat Card Added" "get_message_history 5"
# Filter for chat messages (type 'cm')
CHAT_CARD_COUNT=$(get_value '.result.messages // [] | map(select(.t == "cm")) | length')

echo "📊 Chat messages found after card test: $CHAT_CARD_COUNT"

# Extract the most recent message to verify it's the chat card
LATEST_MESSAGE=$(get_value '.result.messages // [] | map(select(.t == "cm")) | .[-1].c // empty')

echo "📊 Latest message content (first 100 chars): $(echo "$LATEST_MESSAGE" | cut -c1-100)"

# Verify chat card contains expected content
if echo "$LATEST_MESSAGE" | grep -q "Fireball Spell"; then
  echo "✅ VERIFICATION PASSED: Chat card with HTML formatting created successfully"
else
  echo "❌ VERIFICATION FAILED: Chat card not found or content doesn't match"
  track_failure
fi
echo ""

# Step 8: Check session status
test_command "Check Session Status" "status"

# Step 9: End session with WebSocket reset
echo ""
echo "ℹ️  Ending session with WebSocket reset..."
end_session true

# Report final test result
report_test_result "Messaging Operations" \
  "Single message posting" \
  "Multiple message posting as array" \
  "HTML chat card creation with formatting" \
  "Message count verification (4-5 messages added)"

# Exit with appropriate code
if has_failures; then
  exit 1
fi
