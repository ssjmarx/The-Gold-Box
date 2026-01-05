#!/bin/bash
# Shared helper functions for Gold Box tests

# Import truncation utility for JSON logging
export PYTHONPATH="${PYTHONPATH:-backend}"
alias python3="python3 -c \"import sys; sys.path.insert(0, '$PYTHONPATH'); from shared.utils.log_utils import truncate_for_log; exec(sys.argv)\""

API_ENDPOINT="http://localhost:5000/api/admin"

# Execute curl request and save response
exec_request() {
  local desc="$1"
  local data="$2"
  
  echo "━━━ $desc ━━━"
  response=$(curl -s -X POST "$API_ENDPOINT" \
    -H "Content-Type: application/json" \
    -H "X-Admin-Password: swag" \
    -d "$data")
  
  echo "$response" | jq '.'
  echo "$response" > .last_response.json
  echo ""
}

# Execute curl request with truncation for JSON responses
exec_request_with_truncation() {
  local desc="$1"
  local data="$2"
  
  # Ensure password is available
  ensure_admin_password
  
  echo "━━━ $desc ━━━"
  response=$(curl -s -X POST "$API_ENDPOINT" \
    -H "Content-Type: application/json" \
    -H "X-Admin-Password: $ADMIN_PASSWORD" \
    -d "$data")
  
  # Truncate JSON responses using Python truncation utility
  echo "$response" | python3 -c "import sys, os; sys.path.insert(0, '..'); from shared.utils.log_utils import truncate_for_log; import json; data = sys.stdin.read(); print(truncate_for_log(json.loads(data)))"
  echo "$response" > .last_response.json
  echo ""
}

# Start test session and save IDs
start_session() {
  exec_request_with_truncation "Start Test Session" '{
    "command": "start_test_session"
  }'
  
  # Extract and save IDs
  TEST_SESSION_ID=$(cat .last_response.json | jq -r '.test_session_id')
  TEST_CLIENT_ID=$(cat .last_response.json | jq -r '.client_id')
  
  if [ "$TEST_SESSION_ID" != "null" ] && [ -n "$TEST_SESSION_ID" ]; then
    echo "$TEST_SESSION_ID" > .test_session_id
  fi
  if [ "$TEST_CLIENT_ID" != "null" ] && [ -n "$TEST_CLIENT_ID" ]; then
    echo "$TEST_CLIENT_ID" > .test_client_id
  fi
  
  sleep 1
}

# Execute test command
test_command() {
  local desc="$1"
  local cmd="$2"
  
  exec_request "$desc" "{
    \"command\": \"test_command\",
    \"test_session_id\": \"$TEST_SESSION_ID\",
    \"test_command\": \"$cmd\"
  }"
}

# Create encounter using Python helper
create_encounter() {
  local desc="$1"
  local actor_ids="$2"
  local roll_initiative="$3"
  
  echo "━━━ $desc ━━━"
  request_json=$(python3 ./create_encounter_helper.py "$actor_ids" "$TEST_SESSION_ID" $roll_initiative)
  
  # Execute curl with truncation for JSON responses
  response=$(curl -s -X POST "$API_ENDPOINT" \
    -H "Content-Type: application/json" \
    -H "X-Admin-Password: swag" \
    -d "$request_json")
  
  # Save full response to file FIRST (before truncation)
  echo "$response" > .last_response.json
  
  # Then display truncated version for logging
  echo "$response" | python3 -c "import sys, os; sys.path.insert(0, '..'); from shared.utils.log_utils import truncate_for_log; import json; data = sys.stdin.read(); print(truncate_for_log(json.loads(data)))"
  
  echo ""
}

# Create encounter using universal command helper
create_encounter() {
  local desc="$1"
  local actor_ids="$2"
  local roll_initiative="$3"
  local combat_id_file="${4:-.combat_id}"  # Optional 4th param for custom file name
    
    # Ensure password is available
  ensure_admin_password
    
    echo "━━━ $desc ━━━"
    
    # Create temporary Python script to avoid bash escaping issues with JSON arrays
    # Build test_command string that backend expects (single string with parameters)
    cat > /tmp/create_encounter_req.py <<'EOF'
import json, sys, os

test_session_id = os.environ.get('TEST_SESSION_ID', '')
actor_ids_str = os.environ.get('ACTOR_IDS', '[]')
roll_initiative_flag = os.environ.get('ROLL_INITIATIVE', 'false')

# Build the command string as backend expects it
command_str = f"create_encounter actor_ids={actor_ids_str} roll_initiative={roll_initiative_flag}"

request = {
    'command': 'test_command',
    'test_session_id': test_session_id,
    'test_command': command_str
}
print(json.dumps(request))
EOF

    # Set environment variables for Python script
    export TEST_SESSION_ID="$TEST_SESSION_ID"
    export ACTOR_IDS="$actor_ids"
    export ROLL_INITIATIVE="$([ "$roll_initiative" = "--roll_initiative" ] && echo 'true' || echo 'false')"
    
    # Execute temporary Python script
    request_json=$(python3 /tmp/create_encounter_req.py)
    rm /tmp/create_encounter_req.py
    
    response=$(curl -s -X POST "$API_ENDPOINT" \
    -H "Content-Type: application/json" \
    -H "X-Admin-Password: $ADMIN_PASSWORD" \
    -d "$request_json")
  
  # Save full response to file FIRST (before truncation)
  echo "$response" > .last_response.json
  
  # Then display truncated version for logging
  echo "$response" | python3 -c "import sys, os; sys.path.insert(0, '..'); from shared.utils.log_utils import truncate_for_log; import json; data = sys.stdin.read(); print(truncate_for_log(json.loads(data)))"
  
  echo ""
    
    # Extract and save combat_id to specified file
    COMBAT_ID=$(echo "$response" | jq -r '.result.combat_id // empty')
    if [ "$COMBAT_ID" != "null" ] && [ -n "$COMBAT_ID" ]; then
      echo "$COMBAT_ID" > "$combat_id_file"
      echo "💾 Saved combat_id: $COMBAT_ID"
    else
      echo "❌ VERIFICATION FAILED: No combat_id returned"
      return 1
    fi
    
    echo ""
    sleep 1
}

# Activate combat encounter helper
activate_encounter() {
  local encounter_id="$1"
    
    if [ -z "$encounter_id" ]; then
      echo "⚠️  No encounter_id provided, skipping activation"
      return
    fi
    
    echo "━━━ Activate Encounter ($encounter_id) ━━━"
    
    # Build activation request
    cat > /tmp/activate_encounter_req.py <<'EOF'
import json, sys, os

test_session_id = os.environ.get('TEST_SESSION_ID', '')
encounter_id = os.environ.get('ENCOUNTER_ID', '')

# Build the command string as backend expects it
command_str = f"activate_combat encounter_id=\"{encounter_id}\""

request = {
    'command': 'test_command',
    'test_session_id': test_session_id,
    'test_command': command_str
}
print(json.dumps(request))
EOF

    # Set environment variables for Python script
    export TEST_SESSION_ID="$TEST_SESSION_ID"
    export ENCOUNTER_ID="$encounter_id"
    
    # Execute temporary Python script
    request_json=$(python3 /tmp/activate_encounter_req.py)
    rm /tmp/activate_encounter_req.py
    
    response=$(curl -s -X POST "$API_ENDPOINT" \
    -H "Content-Type: application/json" \
    -H "X-Admin-Password: $ADMIN_PASSWORD" \
    -d "$request_json")
  
  # Save full response to file FIRST (before truncation)
  echo "$response" > .last_response.json
  
  # Then display truncated version for logging
  echo "$response" | python3 -c "import sys, os; sys.path.insert(0, '..'); from shared.utils.log_utils import truncate_for_log; import json; data = sys.stdin.read(); print(truncate_for_log(json.loads(data)))"
  
  echo ""
}

# End test session
end_session() {
  local reset="${1:-true}"
  
  exec_request_with_truncation "End Test Session" "{
    \"command\": \"end_test_session\",
    \"test_session_id\": \"$TEST_SESSION_ID\",
    \"reset_connection\": $reset
  }"
}

# Extract actor IDs from saved world state
extract_actor_ids() {
  # Use truncation utility to truncate JSON output from Python script
  ACTOR_IDS=$(python3 <<'PYTHON_SCRIPT'
import json
try:
    with open('.last_response.json', 'r') as f:
        data = json.load(f)
    content = data.get('initial_messages', [{}])[0].get('content', '')
    marker = "World State Overview:\n"
    if marker in content:
        json_str = content.split(marker, 1)[1]
        world_data = json.loads(json_str)
        tokens = world_data.get('active_scene', {}).get('tokens', [])
        actor_ids = [t['actor_id'] for t in tokens if 'actor_id' in t]
        print(json.dumps(actor_ids))
    else:
        print("[]")
except Exception as e:
    print("[]")
PYTHON_SCRIPT
)
  
  if [ "$ACTOR_IDS" != "" ]; then
    echo "$ACTOR_IDS" > .actor_ids
  fi
}

# Extract token ID from saved world state
extract_token_id() {
  TOKEN_ID=$(python3 <<'PYTHON_SCRIPT'
import json
try:
    with open('.last_response.json', 'r') as f:
        data = json.load(f)
    content = data.get('initial_messages', [{}])[0].get('content', '')
    marker = "World State Overview:\n"
    if marker in content:
        json_str = content.split(marker, 1)[1]
        world_data = json.loads(json_str)
        tokens = world_data.get('active_scene', {}).get('tokens', [])
        if tokens:
            print(tokens[0].get('id', ''))
        else:
            print("")
    else:
        print("")
except Exception as e:
    print("")
PYTHON_SCRIPT
)
}

# Verify success in last response
verify_success() {
  local success=$(cat .last_response.json | jq -r '.success // .result.success // false')
  local result_success=$(cat .last_response.json | jq -r '.result.success // true')
  local detail=$(cat .last_response.json | jq -r '.detail // ""')
  local result_error=$(cat .last_response.json | jq -r '.result.error // ""')
  
  # Check for success indicators:
  # - success=true
  # - result.success=true (for nested operations)
  # - No error in .detail or .result.error (either empty or literal "null")
  if [ "$success" = "true" ] && [ "$result_success" = "true" ] && [ -z "$detail" ] && ([ -z "$result_error" ] || [ "$result_error" = "null" ]); then
    echo "✅ Verification: SUCCESS"
    return 0
  else
    echo "❌ Verification: FAILED"
    if [ -n "$detail" ]; then
      echo "   Detail: $detail"
    fi
    if [ "$result_error" != "null" ] && [ -n "$result_error" ]; then
      echo "   Error: $result_error"
    fi
    return 1
  fi
}

# Verify success and exit test if failed (prevents false positives)
verify_or_fail() {
  if ! verify_success "$@"; then
    echo ""
    echo "❌ TEST FAILED - Verification failed, exiting test"
    exit 1
  fi
}

# Verify error and exit test if unexpected success
verify_error_or_fail() {
  local success=$(cat .last_response.json | jq -r '.success // true')
  local message=$(cat .last_response.json | jq -r '.message // ""')
  
  # Check for error indicators:
  # - success=false
  # - result.success=false (for nested timeout errors)
  # - "error" in message, detail, result.error
  # - "Error" in message, detail, result.error
  # - "failed" in message or detail
  # - "Timeout" in message, detail, result.error
  # - "unable" or "Unable" in message, detail, result.error (case-insensitive)
  if [ "$success" = "false" ] || [ "$result_success" = "false" ] || \
     [[ "$message" == *"error"* ]] || \
     [[ "$message" == *"Error"* ]] || \
     [[ "$message" == *"failed"* ]] || \
     [[ "$message" == *"Timeout"* ]] || \
     [[ "$(echo "$message" | tr '[:upper:]' '[:lower:]')" == *"unable"* ]] || \
     [[ "$detail" == *"error"* ]] || \
     [[ "$detail" == *"Error"* ]] || \
     [[ "$detail" == *"Timeout"* ]] || \
     [[ "$detail" == *"timeout"* ]] || \
     [[ "$(echo "$detail" | tr '[:upper:]' '[:lower:]')" == *"unable"* ]] || \
     [ -n "$result_error" ]; then
    if [ -n "$detail" ]; then
      echo "✅ Verification: Expected error detected - $detail"
    elif [ -n "$result_error" ]; then
      echo "✅ Verification: Expected error detected - $result_error"
    else
      echo "✅ Verification: Expected error detected - $message"
    fi
    return 0
  else
    echo "❌ Verification: Expected error but got success"
    return 1
  fi
}

# Get value from last response
get_value() {
  local path="$1"
  cat .last_response.json | jq -r "$path"
}

# Section header
section_header() {
  echo ""
  echo "=========================================="
  echo "$1"
  echo "=========================================="
  echo ""
}

# Test pass/fail tracking
TEST_FAILED=0
TEST_FAIL_COUNT=0

# Mark a test as failed
track_failure() {
  TEST_FAILED=1
  TEST_FAIL_COUNT=$((TEST_FAIL_COUNT + 1))
}

# Check if any failures occurred
has_failures() {
  [ $TEST_FAILED -eq 1 ]
}

# Wrapper that marks failure and exits with status 1
test_failed() {
  local reason="$1"
  if [ -n "$reason" ]; then
    echo "❌ TEST FAILED - $reason"
  else
    echo "❌ TEST FAILED"
  fi
  track_failure
  exit 1
}

# Checks success and continues (doesn't exit)
test_passed() {
  local check="$1"
  if verify_success "$@"; then
    echo "✅ Verification: $check"
    return 0
  else
    echo "❌ Verification: $check"
    track_failure
    return 1
  fi
}

# Reports final test result based on failures
report_test_result() {
  local test_name="$1"
  shift
  
  echo ""
  echo "=========================================="
  if has_failures; then
    echo "❌ $test_name Test: FAILED"
    echo "=========================================="
    echo ""
    echo "❌ Test Summary:"
    while [ $# -gt 0 ]; do
      echo "   • $1"
      shift
    done
    echo ""
    echo "1 check(s) FAILED"
  else
    echo "✅ $test_name Test: PASSED"
    echo "=========================================="
    echo ""
    echo "✅ Test Summary:"
    while [ $# -gt 0 ]; do
      echo "   • $1"
      shift
    done
  fi
}

# Force cleanup of any existing combat
cleanup_combat() {
  # Ensure password is available
  ensure_admin_password
  
  echo "━━━ Cleanup Existing Combat ━━━"
  
  # Validate session before cleanup
  validate_session
  
  # Ensure TEST_SESSION_ID is loaded from file (after validation)
  if [ -f ".test_session_id" ]; then
    TEST_SESSION_ID=$(cat .test_session_id | head -n 1)
  fi
  
  # Get all encounters first
  echo "Getting all active encounters..."
  local request_json=$(python3 ./create_command_helper.py "$TEST_SESSION_ID" "get_encounter")
  
  response=$(curl -s -X POST "$API_ENDPOINT" \
    -H "Content-Type: application/json" \
    -H "X-Admin-Password: $ADMIN_PASSWORD" \
    -d "$request_json")
  
  # Check if any encounters exist
  local in_combat=$(echo "$response" | jq -r '.result.in_combat // false')
  local active_count=$(echo "$response" | jq -r '.result.active_count // 0')
  
  if [ "$in_combat" = "false" ] || [ "$active_count" -eq 0 ]; then
    echo "✅ No active encounters to clean up"
    echo ""
    return 0
  fi
  
  echo "Found $active_count active encounter(s), deleting..."
  
  # Delete each encounter individually
  local encounters=$(echo "$response" | jq -r '.result.encounters[] | .combat_id')
  
  for encounter_id in $encounters; do
    echo "  Deleting encounter: $encounter_id"
    local delete_json=$(python3 ./create_command_helper.py "$TEST_SESSION_ID" "delete_encounter encounter_id=\"$encounter_id\"")
    
    response=$(curl -s -X POST "$API_ENDPOINT" \
      -H "Content-Type: application/json" \
      -H "X-Admin-Password: $ADMIN_PASSWORD" \
      -d "$delete_json")
    
    echo "  ✅ Deleted encounter: $encounter_id"
    sleep 0.5
  done
  
  echo "Combat cleanup completed"
  echo ""
}

# Verify admin API connection is available
verify_connection() {
  # Ensure password is available
  ensure_admin_password
  
  echo "━━━ Verifying Connection ━━━"
  
  # Check if server is running via health endpoint
  local health_response=$(curl -s "http://localhost:5000/api/health")
  local status=$(echo "$health_response" | jq -r '.status // ""' 2>/dev/null)
  
  # Server can return "running" or "healthy"
  if [ "$status" = "running" ] || [ "$status" = "healthy" ]; then
    echo "✅ Server verified: Backend is running (status: $status)"
    return 0
  else
    echo "❌ Connection failed: Backend is not accessible"
    echo "   Response: $health_response"
    return 1
  fi
}

# Wait for WebSocket reconnection after session reset
wait_for_websocket_reconnect() {
  local timeout="${1:-10}"  # Default 10 second timeout
  local log_file="${2:-goldbox.log}"
  
  echo "━━━ Waiting for WebSocket Reconnection ━━━"
  echo "   Timeout: ${timeout} seconds"
  echo "   Log file: $log_file"
  
  if [ ! -f "$log_file" ]; then
    echo "⚠️  WARNING: Log file not found: $log_file"
    echo "   Cannot verify reconnection, proceeding anyway"
    return 0
  fi
  
  # Get the previous client ID from the test session
  local previous_client_id=""
  if [ -f ".test_client_id" ]; then
    previous_client_id=$(cat .test_client_id | head -n 1)
  fi
  
  # If no previous client ID, we can't detect reconnection by client ID change
  if [ -z "$previous_client_id" ]; then
    echo "⚠️  No previous client ID found, skipping reconnection check"
    return 0
  fi
  
  local elapsed=0
  local reconnected=false
  
  while [ $elapsed -lt $timeout ]; do
    if [ -f "$log_file" ]; then
      # Check for any disconnect message for the previous client
      local disconnect_found=$(tail -50 "$log_file" | grep "WebSocket client disconnected: $previous_client_id")
      
      if [ -n "$disconnect_found" ]; then
        # Found disconnect, now check for activity from a different client
        # Look for the most recent client ID in the logs
        local current_client_id=$(tail -20 "$log_file" | grep -oP "client [a-zA-Z0-9\-]+" | tail -1 | grep -oP "client \K[a-zA-Z0-9\-]+")
        
        if [ -n "$current_client_id" ] && [ "$current_client_id" != "$previous_client_id" ]; then
          reconnected=true
          echo ""
          echo "✅ WebSocket reconnected (from $previous_client_id to $current_client_id)"
          return 0
        fi
      fi
    fi
    
    sleep 1
    elapsed=$((elapsed + 1))
    echo -n "."
  done
  
  echo ""
  echo "⚠️  WARNING: WebSocket reconnection not detected within ${timeout} seconds"
  echo "   Proceeding anyway - connection may have been established"
  return 0  # Don't fail, just warn
}
