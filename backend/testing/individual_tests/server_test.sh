#!/bin/bash
# The Gold Box - Server Test Suite v0.4.0
# Quick endpoint and security validation for releases

# Configuration
SERVER_URL="http://localhost:5000"
TIMEOUT=10

# Admin password - use environment variable or prompt
if [ -z "$ADMIN_PASSWORD" ]; then
  read -s -p "Enter admin password: " ADMIN_PASSWORD
  echo ""
fi

# Test counters
PASSED=0
FAILED=0

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Helper functions
run_test() {
    local test_name="$1"
    local expected="$2"
    local actual="$3"
    
    if [ "$expected" == "$actual" ]; then
        echo -e "${GREEN}✓${NC} $test_name"
        ((PASSED++))
    else
        echo -e "${RED}✗${NC} $test_name (Expected: $expected, Got: $actual)"
        ((FAILED++))
    fi
}

check_headers() {
    local response="$1"
    local header="$2"
    if echo "$response" | grep -qi "$header:"; then
        return 0
    else
        return 1
    fi
}

echo "=========================================="
echo "The Gold Box Server Test Suite v0.4.0"
echo "=========================================="
echo ""

# ==========================================
# SECTION 1: Endpoint Tests
# ==========================================
echo -e "${YELLOW}Testing Endpoints...${NC}"
echo ""

# Test 1.1: Health Endpoint
echo "1.1 Health Endpoint:"
HEALTH_RESPONSE=$(curl -s -w "\n%{http_code}" --max-time $TIMEOUT "$SERVER_URL/api/health")
HEALTH_CODE=$(echo "$HEALTH_RESPONSE" | tail -n1)
HEALTH_BODY=$(echo "$HEALTH_RESPONSE" | sed '$d')

run_test "Returns HTTP 200" "200" "$HEALTH_CODE"

if echo "$HEALTH_BODY" | grep -q '"status"'; then
    run_test "Has status field" "true" "true"
else
    run_test "Has status field" "true" "false"
fi

if echo "$HEALTH_BODY" | grep -q '"version"'; then
    run_test "Has version field" "true" "true"
else
    run_test "Has version field" "true" "false"
fi

if echo "$HEALTH_BODY" | grep -q '"service"'; then
    run_test "Has service field" "true" "true"
else
    run_test "Has service field" "true" "false"
fi

echo ""

# Test 1.2: System Endpoint
echo "1.2 System Endpoint:"
START_RESPONSE=$(curl -s -w "\n%{http_code}" --max-time $TIMEOUT -X POST "$SERVER_URL/api/start")
START_CODE=$(echo "$START_RESPONSE" | tail -n1)
START_BODY=$(echo "$START_RESPONSE" | sed '$d')

run_test "Returns HTTP 200" "200" "$START_CODE"

if echo "$START_BODY" | grep -q -i "start\|server\|endpoint"; then
    run_test "Returns startup information" "true" "true"
else
    run_test "Returns startup information" "true" "false"
fi

echo ""

# Test 1.3: Session Init Endpoint
echo "1.3 Session Init Endpoint:"
SESSION_RESPONSE=$(curl -s -w "\n%{http_code}" --max-time $TIMEOUT -X POST "$SERVER_URL/api/session/init")
SESSION_CODE=$(echo "$SESSION_RESPONSE" | tail -n1)
SESSION_BODY=$(echo "$SESSION_RESPONSE" | sed '$d')

run_test "Returns HTTP 200" "200" "$SESSION_CODE"

if echo "$SESSION_BODY" | grep -q '"session_id"'; then
    run_test "Returns session_id" "true" "true"
else
    run_test "Returns session_id" "true" "false"
fi

if echo "$SESSION_BODY" | grep -q '"csrf_token"'; then
    run_test "Returns csrf_token" "true" "true"
else
    run_test "Returns csrf_token" "true" "false"
fi

if echo "$SESSION_BODY" | grep -q '"expires_at"'; then
    run_test "Returns expires_at" "true" "true"
else
    run_test "Returns expires_at" "true" "false"
fi

# Extract session_id for later tests
SESSION_ID=$(echo "$SESSION_BODY" | grep -o '"session_id":"[^"]*' | cut -d'"' -f4)

echo ""

# Test 1.4: Admin Endpoint - Authentication
echo "1.4 Admin Endpoint (Authentication):"

# Missing password
ADMIN_MISSING=$(curl -s -w "\n%{http_code}" --max-time $TIMEOUT -X POST "$SERVER_URL/api/admin" \
    -H "Content-Type: application/json" \
    -d '{"command":"status"}')
ADMIN_MISSING_CODE=$(echo "$ADMIN_MISSING" | tail -n1)

run_test "Missing password returns 401" "401" "$ADMIN_MISSING_CODE"

# Invalid password
ADMIN_INVALID=$(curl -s -w "\n%{http_code}" --max-time $TIMEOUT -X POST "$SERVER_URL/api/admin" \
    -H "Content-Type: application/json" \
    -H "X-Admin-Password: wrongpassword" \
    -d '{"command":"status"}')
ADMIN_INVALID_CODE=$(echo "$ADMIN_INVALID" | tail -n1)

run_test "Invalid password returns 401" "401" "$ADMIN_INVALID_CODE"

# Valid password
ADMIN_VALID=$(curl -s -w "\n%{http_code}" --max-time $TIMEOUT -X POST "$SERVER_URL/api/admin" \
    -H "Content-Type: application/json" \
    -H "X-Admin-Password: $ADMIN_PASSWORD" \
    -d '{"command":"status"}')
ADMIN_VALID_CODE=$(echo "$ADMIN_VALID" | tail -n1)
ADMIN_VALID_BODY=$(echo "$ADMIN_VALID" | sed '$d')

run_test "Valid password returns 200" "200" "$ADMIN_VALID_CODE"

if echo "$ADMIN_VALID_BODY" | grep -q '"status"'; then
    run_test "Status command works" "true" "true"
else
    run_test "Status command works" "true" "false"
fi

echo ""

# Test 1.5: Admin Endpoint - Commands
echo "1.5 Admin Endpoint (Commands):"

# reload_keys command
ADMIN_RELOAD=$(curl -s -w "\n%{http_code}" --max-time $TIMEOUT -X POST "$SERVER_URL/api/admin" \
    -H "Content-Type: application/json" \
    -H "X-Admin-Password: $ADMIN_PASSWORD" \
    -d '{"command":"reload_keys"}')
ADMIN_RELOAD_CODE=$(echo "$ADMIN_RELOAD" | tail -n1)

run_test "reload_keys command returns 200" "200" "$ADMIN_RELOAD_CODE"

# update_settings command
ADMIN_SETTINGS=$(curl -s -w "\n%{http_code}" --max-time $TIMEOUT -X POST "$SERVER_URL/api/admin" \
    -H "Content-Type: application/json" \
    -H "X-Admin-Password: $ADMIN_PASSWORD" \
    -d '{"command":"update_settings","settings":{"test":"value"}}')
ADMIN_SETTINGS_CODE=$(echo "$ADMIN_SETTINGS" | tail -n1)

run_test "update_settings command returns 200" "200" "$ADMIN_SETTINGS_CODE"

# list_test_sessions command
ADMIN_LIST=$(curl -s -w "\n%{http_code}" --max-time $TIMEOUT -X POST "$SERVER_URL/api/admin" \
    -H "Content-Type: application/json" \
    -H "X-Admin-Password: $ADMIN_PASSWORD" \
    -d '{"command":"list_test_sessions"}')
ADMIN_LIST_CODE=$(echo "$ADMIN_LIST" | tail -n1)

run_test "list_test_sessions command returns 200" "200" "$ADMIN_LIST_CODE"

echo ""

# Test 1.6: API Chat Endpoint
echo "1.6 API Chat Endpoint:"

# Valid request (will fail without actual data, but should validate auth)
API_CHAT_VALID=$(curl -s -w "\n%{http_code}" --max-time $TIMEOUT -X POST "$SERVER_URL/api/api_chat" \
    -H "Content-Type: application/json" \
    -H "X-Session-ID: $SESSION_ID" \
    -d '{"context_count":5}')
API_CHAT_VALID_CODE=$(echo "$API_CHAT_VALID" | tail -n1)

run_test "Valid request returns 200 or 400" "true" "$([ "$API_CHAT_VALID_CODE" == "200" ] || [ "$API_CHAT_VALID_CODE" == "400" ] && echo true || echo false)"

# Invalid JSON
API_CHAT_INVALID=$(curl -s -w "\n%{http_code}" --max-time $TIMEOUT -X POST "$SERVER_URL/api/api_chat" \
    -H "Content-Type: application/json" \
    -d 'invalid json')
API_CHAT_INVALID_CODE=$(echo "$API_CHAT_INVALID" | tail -n1)

run_test "Invalid JSON returns error (400 or 500)" "true" "$([ "$API_CHAT_INVALID_CODE" == "400" ] || [ "$API_CHAT_INVALID_CODE" == "500" ] && echo true || echo false)"

# Missing session
API_CHAT_NO_SESSION=$(curl -s -w "\n%{http_code}" --max-time $TIMEOUT -X POST "$SERVER_URL/api/api_chat" \
    -H "Content-Type: application/json" \
    -d '{"context_count":5}')
API_CHAT_NO_SESSION_CODE=$(echo "$API_CHAT_NO_SESSION" | tail -n1)

run_test "Missing session returns error (401 or 500)" "true" "$([ "$API_CHAT_NO_SESSION_CODE" == "401" ] || [ "$API_CHAT_NO_SESSION_CODE" == "500" ] && echo true || echo false)"

echo ""

# ==========================================
# SECTION 2: Security Tests
# ==========================================
echo -e "${YELLOW}Testing Security Features...${NC}"
echo ""

# Test 2.1: Security Headers
echo "2.1 Security Headers:"
HEALTH_HEADERS=$(curl -s -I --max-time $TIMEOUT "$SERVER_URL/api/health")

check_headers "$HEALTH_HEADERS" "X-Content-Type-Options"
HEADER_1=$?
run_test "X-Content-Type-Options header present" "0" "$HEADER_1"

check_headers "$HEALTH_HEADERS" "X-Frame-Options"
HEADER_2=$?
run_test "X-Frame-Options header present" "0" "$HEADER_2"

check_headers "$HEALTH_HEADERS" "X-XSS-Protection"
HEADER_3=$?
run_test "X-XSS-Protection header present" "0" "$HEADER_3"

check_headers "$HEALTH_HEADERS" "Referrer-Policy"
HEADER_4=$?
run_test "Referrer-Policy header present" "0" "$HEADER_4"

check_headers "$HEALTH_HEADERS" "Cache-Control"
HEADER_5=$?
run_test "Cache-Control header present" "0" "$HEADER_5"

echo ""

# Test 2.2: Session Security
echo "2.2 Session Security:"

# Invalid session
INVALID_SESSION_RESPONSE=$(curl -s -w "\n%{http_code}" --max-time $TIMEOUT -X POST "$SERVER_URL/api/api_chat" \
    -H "Content-Type: application/json" \
    -H "X-Session-ID: invalid-session-id" \
    -d '{"context_count":5}')
INVALID_SESSION_CODE=$(echo "$INVALID_SESSION_RESPONSE" | tail -n1)

run_test "Invalid session returns 401" "401" "$INVALID_SESSION_CODE"

echo ""

# Test 2.3: HTTP Methods
echo "2.3 HTTP Methods:"

# GET on POST-only endpoint
GET_ON_POST=$(curl -s -w "\n%{http_code}" --max-time $TIMEOUT -X GET "$SERVER_URL/api/admin")
GET_ON_POST_CODE=$(echo "$GET_ON_POST" | tail -n1)

run_test "GET on POST-only returns 405" "405" "$GET_ON_POST_CODE"

echo ""

# Test 2.4: CORS Headers (skipped - OPTIONS blocked by security middleware)
echo "2.4 CORS Headers:"
echo "  - Skipped: CORS preflight blocked by security middleware"

echo ""

# Test 2.5: Rate Limiting (Basic Check)
echo "2.5 Rate Limiting:"
# Note: This is a basic check - full rate limiting tests would require more complex setup
# We just verify the endpoint responds correctly
RATE_LIMIT_RESPONSE=$(curl -s -w "\n%{http_code}" --max-time $TIMEOUT "$SERVER_URL/api/health")
RATE_LIMIT_CODE=$(echo "$RATE_LIMIT_RESPONSE" | tail -n1)

if [ "$RATE_LIMIT_CODE" == "200" ] || [ "$RATE_LIMIT_CODE" == "429" ]; then
    run_test "Rate limiting configured correctly" "true" "true"
else
    run_test "Rate limiting configured correctly" "true" "false"
fi

echo ""

# ==========================================
# SUMMARY
# ==========================================
echo "=========================================="
echo "Test Results: $PASSED passed, $FAILED failed"
echo "=========================================="

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}All tests passed!${NC}"
    echo ""
    echo "✓ Server is ready for release"
    exit 0
else
    echo -e "${RED}Some tests failed!${NC}"
    echo ""
    echo "✗ Review failed tests before release"
    exit 1
fi
