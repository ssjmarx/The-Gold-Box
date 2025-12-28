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

echo "Step 3: Test Multi-Command Execution"
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

echo "Step 4: End Test Session with WebSocket Reset"
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
echo "1. Check Foundry VTT chat - Should see 6 messages:"
echo "   - 'Individual test message'"
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
echo "   ✅ Multi-command execution tested (4 commands)"
echo "   ✅ WebSocket reset tested"
echo "   ✅ Total: 7 test commands executed"
echo ""
