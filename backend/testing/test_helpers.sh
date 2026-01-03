#!/bin/bash
# Shared helper functions for Gold Box tests

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
  # response=$(curl -s -X POST "$API_ENDPOINT" \
  #   -H "Content-Type: application/json" \
  #   -H "X-Admin-Password: swag" \
  #   -d "{\"command\":\"get_test_session_state\",\"test_session_id\":\"$saved_session_id\"}")
  # local is_valid=$(echo "$response" | jq -r '.success // false')
  # 
  # if [ "$is_valid" != "true" ]; then
  #   echo "⚠️  Session is invalid/expired, starting new session..."
  #   start_session
  # fi
}

# Execute test command
test_command() {
  local desc="$1"
  local cmd="$2"
  
  # Validate session before executing command
  validate_session
  
  # Ensure TEST_SESSION_ID is loaded from file (after validation)
  if [ -f ".test_session_id" ]; then
    TEST_SESSION_ID=$(cat .test_session_id | head -n 1)
  fi
  
  echo "━━━ $desc ━━━"
  request_json=$(python3 ./create_command_helper.py "$TEST_SESSION_ID" "$cmd")
  
  response=$(curl -s -X POST "$API_ENDPOINT" \
    -H "Content-Type: application/json" \
    -H "X-Admin-Password: swag" \
    -d "$request_json")
  
  echo "$response" | jq '.'
  echo "$response" > .last_response.json
  echo ""
}

# Create encounter using universal command helper
create_encounter() {
  local desc="$1"
  local actor_ids="$2"
  local roll_initiative="$3"
  
  echo "━━━ $desc ━━━"
  
  # actor_ids should be a JSON array, pass it as-is
  # Build create_encounter command string
  if [ "$roll_initiative" = "--roll_initiative" ]; then
    local cmd="create_encounter actor_ids=$actor_ids roll_initiative=true"
  else
    local cmd="create_encounter actor_ids=$actor_ids roll_initiative=false"
  fi
  
  # Use universal command helper
  request_json=$(python3 ./create_command_helper.py "$TEST_SESSION_ID" "$cmd")
  
  response=$(curl -s -X POST "$API_ENDPOINT" \
    -H "Content-Type: application/json" \
    -H "X-Admin-Password: swag" \
    -d "$request_json")
  
  echo "$response" | jq '.'
  echo "$response" > .last_response.json
  echo ""
  sleep 1
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

# Force cleanup of any existing combat
cleanup_combat() {
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
    -H "X-Admin-Password: swag" \
    -d "$request_json")
  
  # Don't care if it succeeds or fails, just want to ensure no combat exists
  echo "Combat cleanup completed"
  echo ""
}
