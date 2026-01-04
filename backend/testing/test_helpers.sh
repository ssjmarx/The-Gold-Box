#!/bin/bash
# Shared helper functions for Gold Box tests

API_ENDPOINT="http://localhost:5000/api/admin"

# Ensure admin password is available
# If running from master script, ADMIN_PASSWORD will be set as environment variable
# If running standalone, prompt user for password
ensure_admin_password() {
  if [ -z "$ADMIN_PASSWORD" ]; then
    # Check if running in non-interactive mode
    if [ "$AUTO_MODE" = "true" ]; then
      echo "❌ ERROR: ADMIN_PASSWORD not set and running in AUTO_MODE"
      echo "   Set ADMIN_PASSWORD environment variable before running"
      exit 1
    fi
    
    # Interactive mode - prompt for password
    echo ""
    read -s -p "Enter admin password: " ADMIN_PASSWORD
    echo ""
    export ADMIN_PASSWORD
  fi
}

# Execute curl request and save response
exec_request() {
  local desc="$1"
  local data="$2"
  
  # Ensure password is available
  ensure_admin_password
  
  echo "━━━ $desc ━━━"
  response=$(curl -s -X POST "$API_ENDPOINT" \
    -H "Content-Type: application/json" \
    -H "X-Admin-Password: $ADMIN_PASSWORD" \
    -d "$data")
  
  echo "$response" | jq '.'
  echo "$response" > .last_response.json
  echo ""
}

# Start test session and save IDs
start_session() {
  exec_request "Start Test Session" '{
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

# Validate session and restart if invalid
validate_session() {
  # Check if we have a valid session ID
  if [ ! -f ".test_session_id" ]; then
    echo "⚠️  No session file found, starting new session..."
    start_session
    return
  fi
  
  # Load session ID from file
  local saved_session_id=$(cat .test_session_id | head -n 1)
  
  # Check if session ID is null or empty
  if [ "$saved_session_id" = "null" ] || [ -z "$saved_session_id" ]; then
    echo "⚠️  Session ID is null/invalid, starting new session..."
    start_session
    return
  fi
  
  # Optionally: Test if session is still valid by sending a status command
  # This is disabled for now to avoid slowing down tests
}

# Execute test command
test_command() {
  local desc="$1"
  local cmd="$2"
  local encounter_id="$3"  # Optional 3rd parameter for encounter_id
  
  # Ensure password is available
  ensure_admin_password
  
  # Validate session before executing command
  validate_session
  
  # Ensure TEST_SESSION_ID is loaded from file (after validation)
  if [ -f ".test_session_id" ]; then
    TEST_SESSION_ID=$(cat .test_session_id | head -n 1)
  fi
  
  echo "━━━ $desc ━━━"
  
  # Build command with optional encounter_id
  # For encounter operations, embed encounter_id directly in command string
  if [ -n "$encounter_id" ]; then
    if [[ "$cmd" == "advance_combat_turn" ]] || [[ "$cmd" == "delete_encounter" ]] || [[ "$cmd" == "get_encounter" ]]; then
      # These commands need encounter_id as a parameter
      cmd_with_id="$cmd encounter_id=\"$encounter_id\""
      request_json=$(python3 ./create_command_helper.py "$TEST_SESSION_ID" "$cmd_with_id")
    else
      # Other commands that might accept encounter_id
      request_json=$(python3 ./create_command_helper.py "$TEST_SESSION_ID" "$cmd" --encounter_id "$encounter_id")
    fi
  else
    request_json=$(python3 ./create_command_helper.py "$TEST_SESSION_ID" "$cmd")
  fi
  
  response=$(curl -s -X POST "$API_ENDPOINT" \
    -H "Content-Type: application/json" \
    -H "X-Admin-Password: $ADMIN_PASSWORD" \
    -d "$request_json")
  
  echo "$response" | jq '.'
  echo "$response" > .last_response.json
  
  # If create_encounter was called, extract and save combat_id
  if [[ "$cmd" == create_encounter* ]]; then
    COMBAT_ID=$(cat .last_response.json | jq -r '.result.combat_id // empty')
    if [ "$COMBAT_ID" != "null" ] && [ -n "$COMBAT_ID" ]; then
      echo "$COMBAT_ID" > .combat_id
      echo "💾 Saved combat_id: $COMBAT_ID"
    fi
  fi
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

    # Set environment variables for to Python script
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
    
    echo "$response" | jq '.'
    echo "$response" > .last_response.json
    
    # Extract and save combat_id to specified file
    COMBAT_ID=$(echo "$response" | jq -r '.result.combat_id // empty')
    if [ "$COMBAT_ID" != "null" ] && [ -n "$COMBAT_ID" ]; then
      echo "$COMBAT_ID" > "$combat_id_file"
      echo "💾 Saved combat_id to file: $combat_id_file (ID: $COMBAT_ID)"
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
    
    echo "$response" | jq '.'
    echo "$response" > .last_response.json
    
    echo ""
}

# End test session
end_session() {
  local reset="${1:-true}"
  
  exec_request "End Test Session" "{
    \"command\": \"end_test_session\",
    \"test_session_id\": \"$TEST_SESSION_ID\",
    \"reset_connection\": $reset
  }"
}

# Extract actor IDs from saved world state
extract_actor_ids() {
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
        # Return as JSON array string, properly formatted
        print(json.dumps(actor_ids))
    else:
        print("[]")
except Exception as e:
    print("[]")
PYTHON_SCRIPT
)
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
  
  if [ "$TOKEN_ID" != "" ]; then
    echo "$TOKEN_ID" > .token_id
  fi
}

# Verify success in last response
verify_success() {
  local success=$(cat .last_response.json | jq -r '.success // .result.success // false')
  local status_code=$(cat .last_response.json | jq -r '.status // ""')
  local message=$(cat .last_response.json | jq -r '.message // ""')
  
  if [ "$success" = "true" ]; then
    echo "✅ Verification: SUCCESS"
    return 0
  else
    echo "❌ Verification: FAILED"
    if [ -n "$status_code" ]; then
      echo "   Status: $status_code"
    fi
    if [ -n "$message" ]; then
      echo "   Message: $message"
    fi
    cat .last_response.json | jq '.'
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
  if ! verify_error "$@"; then
    echo ""
    echo "❌ TEST FAILED - Expected error not detected, exiting test"
    exit 1
  fi
}

# Verify error in last response
verify_error() {
  local success=$(cat .last_response.json | jq -r '.success // true')
  local result_success=$(cat .last_response.json | jq -r '.result.success // true')
  local message=$(cat .last_response.json | jq -r '.message // ""')
  local detail=$(cat .last_response.json | jq -r '.detail // ""')
  local result_error=$(cat .last_response.json | jq -r '.result.error // ""')
  
  # Check for error indicators:
  # - success=false
  # - result.success=false (for nested timeout errors)
  # - "error" in message, detail, result.error
  # - "Error" in message, detail, result.error
  # - "failed" in message or detail
  # - "Timeout" in message, detail, result.error
  # - "timeout" in message, detail, result.error
  # - "unable" or "Unable" in message, detail, result.error (case-insensitive)
  if [ "$success" = "false" ] || [ "$result_success" = "false" ] || \
     [[ "$message" == *"error"* ]] || \
     [[ "$message" == *"Error"* ]] || \
     [[ "$message" == *"failed"* ]] || \
     [[ "$message" == *"Timeout"* ]] || \
     [[ "$message" == *"timeout"* ]] || \
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
    cat .last_response.json | jq '.'
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
  
  # Ensure TEST_SESSION_ID is loaded (after validation)
  if [ -f ".test_session_id" ]; then
    TEST_SESSION_ID=$(cat .test_session_id | head -n 1)
  fi
  
  local request_json=$(python3 ./create_command_helper.py "$TEST_SESSION_ID" "delete_encounter")
  
  response=$(curl -s -X POST "$API_ENDPOINT" \
    -H "Content-Type: application/json" \
    -H "X-Admin-Password: $ADMIN_PASSWORD" \
    -d "$request_json")
  
  # Don't care if it succeeds or fails, just want to ensure no combat exists
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
  
  # Get the last client ID before we start waiting
  local last_client_id=$(tail -100 "$log_file" | grep -oP "from client \K[^\s]+" | tail -1)
  
  local elapsed=0
  local reconnected=false
  
  while [ $elapsed -lt $timeout ]; do
    # Check for a new WebSocket message from a different client
    # This indicates a new client has connected and sent a message
    local new_client_id=$(tail -20 "$log_file" | grep -oP "from client \K[^\s]+" | tail -1)
    
    if [ -n "$new_client_id" ] && [ "$new_client_id" != "$last_client_id" ]; then
      # Verify this is a recent message (within the last 5 seconds)
      local recent_message=$(tail -5 "$log_file" | grep "$new_client_id")
      if [ -n "$recent_message" ]; then
        reconnected=true
        echo ""
        echo "✅ WebSocket reconnected (new client: $new_client_id)"
        return 0
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
