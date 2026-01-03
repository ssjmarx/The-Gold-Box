#!/bin/bash
# Test dice rolling operations with circular verification

# Source helper functions
. ./test_helpers.sh

section_header "Test: Dice Rolling"

echo "📝 NOTE: This test verifies dice operations with circular verification"
echo "   • get_message_history → roll → get_message_history (confirm dice rolls added)"
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

# Step 3: Roll single dice with flavor
test_command "Single Dice Roll with Flavor" "roll_dice rolls=[{\"formula\":\"1d20+5\",\"flavor\":\"Attack roll\"}]"

# Step 4: Roll multiple dice in one command
test_command "Multiple Dice Rolls" "roll_dice rolls=[{\"formula\":\"2d6\",\"flavor\":\"Damage\"},{\"formula\":\"1d8+3\",\"flavor\":\"Bonus damage\"}]"

# Step 5: Roll dice without flavor
test_command "Dice Roll Without Flavor" "roll_dice rolls=[{\"formula\":\"1d20\"}]"

# Step 6: Verify dice rolls were added
test_command "Verify Dice Rolls Added" "get_message_history 15"
NEW_COUNT=$(get_value ".result.count // 0")
ADDED=$((NEW_COUNT - BASELINE_COUNT))

echo "📊 New message count: $NEW_COUNT"
echo "📊 Messages added: $ADDED (expected: 3 dice rolls)"
echo ""

if [ $ADDED -eq 3 ]; then
  echo "✅ VERIFICATION PASSED: 3 dice rolls added successfully"
else
  echo "❌ VERIFICATION FAILED: Expected 3 dice rolls, got $ADDED messages"
fi
echo ""

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
echo "✅ Dice rolling test complete!"
echo "=========================================="
echo ""
echo "Expected results in Foundry VTT chat:"
echo "   • Dice roll: '1d20+5 (Attack roll) = X'"
echo "   • Dice roll: '2d6 (Damage) = X'"
echo "   • Dice roll: '1d8+3 (Bonus damage) = X'"
echo "   • Dice roll: '1d20 = X'"
echo ""
