#!/bin/bash
# Test "Get Nearby Objects" command

# Redirect all output to test_results.log (overwriting previous contents)
exec > ../test_results.log 2>&1

# Source helper functions
. ./test_helpers.sh

# Disable JSON truncation to see full world state
export DISABLE_TRUNCATION=true

section_header "Test: Get Nearby Objects"

echo "📝 NOTE: This test verifies that get_nearby_objects works correctly"
echo "   • First test: Get objects near first token found in world state"
echo "   • Second test: Get objects near a point one grid square away from token"
echo ""

# Step 1: Start test session (world state is included in the response)
start_session

# Extract first token's information from world state
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
            token = tokens[0]
            print(token.get('id', ''))
        else:
            print("")
    else:
        print("")
except Exception as e:
    print("")
PYTHON_SCRIPT
)

TOKEN_X=$(python3 <<'PYTHON_SCRIPT'
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
            token = tokens[0]
            print(token.get('x', 0))
        else:
            print(0)
    else:
        print(0)
except Exception as e:
    print(0)
PYTHON_SCRIPT
)

TOKEN_Y=$(python3 <<'PYTHON_SCRIPT'
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
            token = tokens[0]
            print(token.get('y', 0))
        else:
            print(0)
    else:
        print(0)
except Exception as e:
    print(0)
PYTHON_SCRIPT
)

echo "📍 First token found:"
echo "   Token ID: $TOKEN_ID"
echo "   Position: ($TOKEN_X, $TOKEN_Y)"
echo ""

# Verify we found a token
if [ -z "$TOKEN_ID" ]; then
  echo "❌ ERROR: No tokens found in world state"
  end_session
  exit 1
fi

# Step 3: Get nearby objects for token
# Note: get_nearby_objects requires 'origin' parameter (token_id string or {x, y} object) and 'radius'
test_command "Get Nearby Objects (Token)" "get_nearby_objects origin=\"$TOKEN_ID\" radius=5"

# Verify the command succeeded
verify_or_fail "get_nearby_objects for token succeeded"

echo "✅ Step 1 complete: Retrieved nearby objects for token"
echo ""

# Step 4: Calculate a nearby point (one grid square away, assuming 100px grid)
# Move 100 pixels in X direction to get a nearby point
NEARBY_X=$((TOKEN_X + 100))
NEARBY_Y=$TOKEN_Y

echo "📍 Nearby point calculated:"
echo "   Point: ($NEARBY_X, $NEARBY_Y) (100 pixels right of token)"
echo ""

# Step 5: Get nearby objects for point
# Build request JSON directly with Python to avoid test_command parsing issues
cat > /tmp/spatial_search_req.py <<'EOF'
import json, sys, os

test_session_id = os.environ.get('TEST_SESSION_ID', '')
nearby_x = int(os.environ.get('NEARBY_X', '0'))
nearby_y = int(os.environ.get('NEARBY_Y', '0'))

# Build origin JSON object directly
origin_dict = {"x": nearby_x, "y": nearby_y}

# Build request with the origin as a dict, not a string
# This avoids test_command parsing entirely
request = {
    'command': 'test_command',
    'test_session_id': test_session_id,
    'test_command': f'get_nearby_objects origin={json.dumps(origin_dict)} radius=5'
}
print(json.dumps(request))
EOF

# Set environment variables for Python script
export TEST_SESSION_ID="$TEST_SESSION_ID"
export NEARBY_X="$NEARBY_X"
export NEARBY_Y="$NEARBY_Y"

# Execute temporary Python script
request_json=$(python3 /tmp/spatial_search_req.py)
rm /tmp/spatial_search_req.py

# Send request
response=$(curl -s -X POST "$API_ENDPOINT" \
  -H "Content-Type: application/json" \
  -H "X-Admin-Password: $ADMIN_PASSWORD" \
  -d "$request_json")

# Save full response to file FIRST (before truncation)
echo "$response" > .last_response.json

# Check if truncation is disabled via environment variable
if [ "$DISABLE_TRUNCATION" = "true" ]; then
  # Show full JSON without truncation
  echo "$response" | jq '.'
else
  # Then display truncated version for logging
  echo "$response" | python3 -c "import sys, os; sys.path.insert(0, '..'); from shared.utils.log_utils import truncate_for_log; import json; data = sys.stdin.read(); print(truncate_for_log(json.loads(data)))"
fi

echo ""

# Verify the command succeeded
verify_or_fail "get_nearby_objects for point succeeded"

echo "✅ Step 2 complete: Retrieved nearby objects for nearby point"
echo ""

# Step 6: Check session status
test_command "Check Session Status" "status"

# Step 7: End session
echo ""
echo "ℹ️  Ending test session..."
end_session

# Report final test result
report_test_result "Get Nearby Objects" \
  "Get nearby objects for token (first token in world state)" \
  "Get nearby objects for point (nearby location, 1 grid square away)"

# Exit with appropriate code
if has_failures; then
  exit 1
fi

# Run pretty print script on the output to make it human-readable
echo ""
echo "━━━ Formatting Output for Readability ━━━"
python3 ../pretty_print_content.py ../test_results.log
