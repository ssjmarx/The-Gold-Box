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
}

# Verify success in last response
verify_success() {
  local success=$(cat .last_response.json | jq -r '.success // .result.success // false')
  if [ "$success" = "true" ]; then
    echo "✅ Verification: SUCCESS"
    return 0
  else
    echo "❌ Verification: FAILED"
    return 1
  fi
}

# Verify error in last response
verify_error() {
  local success=$(cat .last_response.json | jq -r '.success // true')
  local message=$(cat .last_response.json | jq -r '.message // ""')
  
  if [ "$success" = "false" ] || [[ "$message" == *"error"* ]] || [[ "$message" == *"Error"* ]] || [[ "$message" == *"failed"* ]]; then
    echo "✅ Verification: Expected error detected - $message"
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
