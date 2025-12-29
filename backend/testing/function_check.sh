#!/bin/bash
# Definitive Testing Suite for The Gold Box
# Tests individual commands, multi-command execution, and WebSocket reset

export GOLD_BOX_ADMIN_PASSWORD="swag"
API_ENDPOINT="http://localhost:5000/api/admin"

echo "=========================================="
echo "Definitive Testing Suite for The Gold Box"
echo "=========================================="
echo ""

# Helper: Execute curl and show result
exec_curl() {
  local desc="$1"
  local data="$2"
  
  echo "━━━ $desc ━━━"
  echo ""
  
  response=$(curl -s -X POST "$API_ENDPOINT" \
    -H "Content-Type: application/json" \
    -H "X-Admin-Password: swag" \
    -d "$data")
  
  echo "$response" | jq '.'
  
  # Extract session ID if present
  if echo "$response" | jq -e '.test_session_id' > /dev/null; then
    TEST_SESSION_ID=$(echo "$response" | jq -r '.test_session_id')
    TEST_CLIENT_ID=$(echo "$response" | jq -r '.client_id')
    echo "$TEST_SESSION_ID" > .test_session_id
    echo "$TEST_CLIENT_ID" > .test_client_id
    echo ""
    echo "💾 Saved: session_id=$TEST_SESSION_ID, client_id=$TEST_CLIENT_ID"
  fi
  
  echo ""
  sleep 1
}

echo "Step 1: Start Test Session"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
exec_curl "Start Test Session" '{
  "command": "start_test_session"
}'

echo "Step 2: Test Individual Commands"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
exec_curl "Get Messages" '{
  "command": "test_command",
  "test_session_id": "'"$TEST_SESSION_ID"'",
  "test_command": "get_message_history 10"
}'

exec_curl "Single Post Message" '{
  "command": "test_command",
  "test_session_id": "'"$TEST_SESSION_ID"'",
  "test_command": "post \"Individual test message\""
}'

exec_curl "Check Status" '{
  "command": "test_command",
  "test_session_id": "'"$TEST_SESSION_ID"'",
  "test_command": "status"
}'

echo "Step 3: Test Dice Rolling (Feature 2)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
exec_curl "Single Dice Roll" '{
  "command": "test_command",
  "test_session_id": "'"$TEST_SESSION_ID"'",
  "test_command": "roll_dice rolls=[{\"formula\":\"1d20+5\",\"flavor\":\"Attack roll\"}]"
}'

exec_curl "Multiple Dice Rolls" '{
  "command": "test_command",
  "test_session_id": "'"$TEST_SESSION_ID"'",
  "test_command": "roll_dice rolls=[{\"formula\":\"2d6\",\"flavor\":\"Damage\"},{\"formula\":\"1d8+3\",\"flavor\":\"Bonus damage\"}]"
}'

exec_curl "Dice Roll Without Flavor" '{
  "command": "test_command",
  "test_session_id": "'"$TEST_SESSION_ID"'",
  "test_command": "roll_dice rolls=[{\"formula\":\"1d20\"}]"
}'

echo "Step 4: Test Combat Status (Feature 3)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
exec_curl "Get Encounter (Out of Combat)" '{
  "command": "test_command",
  "test_session_id": "'"$TEST_SESSION_ID"'",
  "test_command": "get_encounter"
}'

echo "📝 Manual Test: Start Combat in Foundry VTT"
echo "   - Click the 'Combat' tab in Foundry VTT"
echo "   - Click 'Start Combat' button"
echo "   - Add at least one combatant to the combat"
echo "   - Wait for combat to start"
echo ""
echo "⏸️  Press Enter when combat is started in Foundry VTT..."
read

exec_curl "Get Encounter (In Combat)" '{
  "command": "test_command",
  "test_session_id": "'"$TEST_SESSION_ID"'",
  "test_command": "get_encounter"
}'

echo "📝 Manual Test: End Combat in Foundry VTT"
echo "   - Click the 'End Combat' button in Foundry VTT"
echo "   - Wait for combat to end"
echo ""
echo "⏸️  Press Enter when combat has ended in Foundry VTT..."
read

exec_curl "Get Encounter (Combat Ended)" '{
  "command": "test_command",
  "test_session_id": "'"$TEST_SESSION_ID"'",
  "test_command": "get_encounter"
}'

echo "Step 5: Test Multi-Command Execution"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
exec_curl "Execute Multiple Commands" '{
  "command": "execute_test_commands",
  "test_session_id": "'"$TEST_SESSION_ID"'",
  "commands": [
    "get_message_history 5",
    "post_message [{\"content\":\"Multi-test message 1\",\"type\":\"chat-message\"},{\"content\":\"Multi-test message 2\",\"type\":\"chat-message\"}]",
    "post \"Multi-test message 3\"",
    "status"
  ]
}'

echo "Step 6: End Test Session WITHOUT Reset (Prepare for Delta Test)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
exec_curl "End Session (No WebSocket Reset)" '{
  "command": "end_test_session",
  "test_session_id": "'"$TEST_SESSION_ID"'",
  "reset_connection": false
}'

echo ""
echo "Step 7: Test Delta Tracking (Feature 4)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📝 This test demonstrates delta tracking in action"
echo ""
echo "The test session was ended WITHOUT WebSocket reset."
echo "You'll now make changes in Foundry, and we'll start a new session"
echo "to show you exactly what delta gets injected into AI's initial prompt."
echo ""

echo "🎮 INSTRUCTIONS FOR DELTA TEST:"
echo "   Please make the following changes in Foundry VTT:"
echo "   • Create 2-3 new chat messages (type in chat and press Enter)"
echo "   • Roll some dice (Ctrl+Shift+D, then enter formulas like '1d20')"
echo "   • (Optional) Start or end combat (Combat tab → Start/End Combat)"
echo ""
echo "   After making changes, press Enter to start new test session"
echo ""
read -p "⏸️  Press Enter when ready to start new session... "

# Start NEW session to capture deltas
exec_curl "Start New Test Session (Capture Deltas)" '{
  "command": "start_test_session",
  "ai_role": "gm"
}'

# Save new session ID
TEST_SESSION_ID=$(cat .test_session_id)
TEST_CLIENT_ID=$(cat .test_client_id)

echo ""
echo "📊 DELTA INFORMATION:"
echo ""
echo "The initial_prompt below shows exactly what AI receives:"
echo "Look for the 'Recent changes to game' section."
echo ""
exec_curl "Show Initial Prompt with Deltas" '{
  "command": "test_command",
  "test_session_id": "'"$TEST_SESSION_ID"'",
  "test_command": "status"
}'

echo ""
echo "✅ Delta test complete!"
echo "   • Reviewed initial prompt above"
echo "   • Should see full delta JSON if you made changes"
echo "   • Should see 'No changes to game state' if you didn't"
echo ""

echo "Step 8: End Test Session with WebSocket Reset"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
exec_curl "End Test Session (WebSocket Reset)" '{
  "command": "end_test_session",
  "test_session_id": "'"$TEST_SESSION_ID"'"
}'

echo "=========================================="
echo "Testing Complete!"
echo "=========================================="
echo ""
echo "✅ Verification Checklist:"
echo ""
echo "1. Check Foundry VTT chat - Should see 7 messages:"
echo "   - 'Individual test message'"
echo "   - Dice roll: '1d20+5 (Attack roll) = X'"
echo "   - Dice roll: '2d6 (Damage) = X'"
echo "   - Dice roll: '1d8+3 (Bonus damage) = X'"
echo "   - Dice roll: '1d20 = X'"
echo "   - 'Multi-test message 1'"
echo "   - 'Multi-test message 2'"
echo "   - 'Multi-test message 3'"
echo ""
echo "2. Check browser console:"
echo "   - Should show: 'Testing session ended - reconnecting...'"
echo "   - Should show: 'Gold Box: Disconnecting WebSocket...'"
echo "   - Should show: 'Gold Box: Generating new client ID...'"
echo "   - Should show: 'Gold Box: New client ID: gb-...'"
echo "   - Should show: 'Gold Box: Reconnecting...'"
echo "   - Should show: 'WebSocket connection established'"
echo ""
echo "3. Check backend logs:"
echo "   - Should show: 'Started test session ...'"
echo "   - Should show: 'Executed 4 commands ...'"
echo "   - Should show: 'Forced WebSocket disconnect ...'"
echo "   - Should show: 'Ended test session ... (WebSocket reset)'"
echo ""
echo "4. Verify AI turn button:"
echo "   - Should be re-enabled after test session ends"
echo ""
echo "5. Verify client ID changed:"
echo "   - Run this in browser console to see new ID:"
echo "   window.goldBoxWebSocketClient.clientId"
echo ""
echo "📊 Test Results:"
echo "   ✅ Individual commands tested (3 commands)"
echo "   ✅ Dice rolling tested (3 commands)"
echo "   ✅ Combat status tested (3 commands)"
echo "   ✅ Multi-command execution tested (4 commands)"
echo "   ✅ WebSocket reset tested"
echo "   ✅ Total: 13 test commands executed"
echo ""
