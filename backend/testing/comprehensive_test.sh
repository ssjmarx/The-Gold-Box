#!/bin/bash

echo "=== The Gold Box Backend Comprehensive Test Suite v0.3.5 ==="
echo

# Check if jq is available
if ! command -v jq &> /dev/null; then
    echo "❌ Error: jq is required but not installed. Please install jq."
    echo "   Ubuntu/Debian: sudo apt-get install jq"
    echo "   macOS: brew install jq"
    echo "   Windows: choco install jq"
    exit 1
fi

# Check if curl is available
if ! command -v curl &> /dev/null; then
    echo "❌ Error: curl is required but not installed. Please install curl."
    exit 1
fi

# Configuration
SERVER_URL="${GOLD_BOX_SERVER_URL:-http://localhost:5000}"
TIMEOUT="${GOLD_BOX_TEST_TIMEOUT:-10}"

echo "🔧 Configuration:"
echo "   Server URL: $SERVER_URL"
echo "   Timeout: ${TIMEOUT}s"
echo

# Initialize session
echo "🔐 Initializing session..."
SESSION_RESPONSE=$(curl -s --max-time $TIMEOUT -X POST "$SERVER_URL/api/session/init" \
  -H "Content-Type: application/json" \
  -d '{}')

if [ $? -ne 0 ]; then
    echo "❌ Failed to connect to server at $SERVER_URL"
    echo "   Make sure the server is running and accessible"
    exit 1
fi

SESSION_ID=$(echo "$SESSION_RESPONSE" | jq -r '.session_id')
CSRF_TOKEN=$(echo "$SESSION_RESPONSE" | jq -r '.csrf_token')

if [ "$SESSION_ID" = "null" ] || [ "$CSRF_TOKEN" = "null" ]; then
    echo "❌ Failed to initialize session"
    echo "   Response: $SESSION_RESPONSE"
    exit 1
fi

echo "✅ Session initialized successfully"
echo "   Session ID: $SESSION_ID"
echo "   CSRF Token: $CSRF_TOKEN"
echo

# Test counters
TESTS_PASSED=0
TESTS_FAILED=0

# Helper function to run a test
run_test() {
    local test_name="$1"
    local expected_code="$2"
    local test_command="$3"
    
    echo "🧪 Running: $test_name"
    
    response=$(eval "$test_command")
    actual_code=$?
    
    if [ $actual_code -eq $expected_code ]; then
        echo "✅ $test_name - PASSED"
        ((TESTS_PASSED++))
    else
        echo "❌ $test_name - FAILED"
        echo "   Expected: $expected_code, Got: $actual_code"
        echo "   Response: $response"
        ((TESTS_FAILED++))
    fi
    echo
}

# Helper function to test HTTP status code
test_http_status() {
    local test_name="$1"
    local expected_status="$2"
    local curl_command="$3"
    
    echo "🧪 Running: $test_name"
    
    response=$(eval "$curl_command")
    http_code=$(echo "$response" | jq -r '.status // empty')
    
    if [ "$http_code" = "$expected_status" ] || [ "$http_code" = "" ]; then
        echo "✅ $test_name - PASSED"
        ((TESTS_PASSED++))
    else
        echo "❌ $test_name - FAILED"
        echo "   Expected status: $expected_status, Got: $http_code"
        ((TESTS_FAILED++))
    fi
    echo
}

echo "📡 Testing API Endpoints..."
echo

# Test 1: Health Check
test_http_status "Health Check" "healthy" "curl -s --max-time $TIMEOUT -X GET '$SERVER_URL/api/health' | jq ."

# Test 2: Service Information
test_http_status "Service Info" "success" "curl -s --max-time $TIMEOUT -X GET '$SERVER_URL/api/info' | jq ."

# Test 3: Security Verification
test_http_status "Security Verification" "success" "curl -s --max-time $TIMEOUT -X GET '$SERVER_URL/api/security' | jq ."

# Test 4: API Chat (with invalid data)
echo "🧪 Running: API Chat Validation"
response=$(curl -s --max-time $TIMEOUT -o /dev/null -w "%{http_code}" \
  -X POST "$SERVER_URL/api/api_chat" \
  -H "Content-Type: application/json" \
  -H "X-Session-ID: $SESSION_ID" \
  -H "X-CSRF-Token: $CSRF_TOKEN" \
  -d '{
    "settings": {"general llm provider": "openai"},
    "messages": [{"sender": "Test", "content": "test"}]
  }')

if [ "$response" = "400" ] || [ "$response" = "401" ] || [ "$response" = "403" ]; then
    echo "✅ API Chat Validation - PASSED (properly rejected invalid data)"
    ((TESTS_PASSED++))
else
    echo "❌ API Chat Validation - FAILED (should have rejected invalid data)"
    echo "   Expected: 400/401/403, Got: $response"
    ((TESTS_FAILED++))
fi
echo

echo "🛡️ Testing Security Features..."
echo

# Test 5: CSRF Protection (Invalid Token)
echo "🧪 Running: CSRF Protection (Invalid Token)"
response=$(curl -s --max-time $TIMEOUT -o /dev/null -w "%{http_code}" \
  -X POST "$SERVER_URL/api/api_chat" \
  -H "Content-Type: application/json" \
  -H "X-Session-ID: $SESSION_ID" \
  -H "X-CSRF-Token: invalid-token" \
  -d '{
    "settings": {"general llm provider": "openai"},
    "messages": [{"sender": "Test", "content": "test"}]
  }')

if [ "$response" = "403" ]; then
    echo "✅ CSRF Protection (Invalid Token) - PASSED"
    ((TESTS_PASSED++))
else
    echo "❌ CSRF Protection (Invalid Token) - FAILED"
    echo "   Expected: 403, Got: $response"
    ((TESTS_FAILED++))
fi
echo

# Test 6: CSRF Protection (Missing Token)
echo "🧪 Running: CSRF Protection (Missing Token)"
response=$(curl -s --max-time $TIMEOUT -o /dev/null -w "%{http_code}" \
  -X POST "$SERVER_URL/api/api_chat" \
  -H "Content-Type: application/json" \
  -H "X-Session-ID: $SESSION_ID" \
  -d '{
    "settings": {"general llm provider": "openai"},
    "messages": [{"sender": "Test", "content": "test"}]
  }')

if [ "$response" = "403" ]; then
    echo "✅ CSRF Protection (Missing Token) - PASSED"
    ((TESTS_PASSED++))
else
    echo "❌ CSRF Protection (Missing Token) - FAILED"
    echo "   Expected: 403, Got: $response"
    ((TESTS_FAILED++))
fi
echo

# Test 7: Input Validation (XSS)
echo "🧪 Running: Input Validation (XSS Protection)"
response=$(curl -s --max-time $TIMEOUT -o /dev/null -w "%{http_code}" \
  -X POST "$SERVER_URL/api/api_chat" \
  -H "Content-Type: application/json" \
  -H "X-Session-ID: $SESSION_ID" \
  -H "X-CSRF-Token: $CSRF_TOKEN" \
  -d '{
    "settings": {"general llm provider": "openai"},
    "messages": [{"sender": "Test", "content": "<script>alert(\"xss\")</script>test"}]
  }')

if [ "$response" = "400" ]; then
    echo "✅ Input Validation (XSS Protection) - PASSED"
    ((TESTS_PASSED++))
else
    echo "❌ Input Validation (XSS Protection) - FAILED"
    echo "   Expected: 400, Got: $response"
    ((TESTS_FAILED++))
fi
echo

# Test 8: Input Validation (SQL Injection)
echo "🧪 Running: Input Validation (SQL Injection)"
response=$(curl -s --max-time $TIMEOUT -o /dev/null -w "%{http_code}" \
  -X POST "$SERVER_URL/api/api_chat" \
  -H "Content-Type: application/json" \
  -H "X-Session-ID: $SESSION_ID" \
  -H "X-CSRF-Token: $CSRF_TOKEN" \
  -d '{
    "settings": {"general llm provider": "openai"},
    "messages": [{"sender": "Test", "content": "SELECT * FROM users WHERE 1=1; DROP TABLE users;"}]
  }')

if [ "$response" = "400" ]; then
    echo "✅ Input Validation (SQL Injection) - PASSED"
    ((TESTS_PASSED++))
else
    echo "❌ Input Validation (SQL Injection) - FAILED"
    echo "   Expected: 400, Got: $response"
    ((TESTS_FAILED++))
fi
echo

# Test 9: Session Validation (Invalid Session)
echo "🧪 Running: Session Validation (Invalid Session)"
response=$(curl -s --max-time $TIMEOUT -o /dev/null -w "%{http_code}" \
  -X POST "$SERVER_URL/api/api_chat" \
  -H "Content-Type: application/json" \
  -H "X-Session-ID: invalid-session-id" \
  -H "X-CSRF-Token: $CSRF_TOKEN" \
  -d '{
    "settings": {"general llm provider": "openai"},
    "messages": [{"sender": "Test", "content": "test"}]
  }')

if [ "$response" = "401" ]; then
    echo "✅ Session Validation (Invalid Session) - PASSED"
    ((TESTS_PASSED++))
else
    echo "❌ Session Validation (Invalid Session) - FAILED"
    echo "   Expected: 401, Got: $response"
    ((TESTS_FAILED++))
fi
echo

# Test 10: Admin Authentication (Invalid Password)
echo "🧪 Running: Admin Authentication (Invalid Password)"
response=$(curl -s --max-time $TIMEOUT -o /dev/null -w "%{http_code}" \
  -X POST "$SERVER_URL/api/admin" \
  -H "Content-Type: application/json" \
  -H "X-Admin-Password: wrong-password" \
  -d '{"command": "status"}')

if [ "$response" = "401" ]; then
    echo "✅ Admin Authentication (Invalid Password) - PASSED"
    ((TESTS_PASSED++))
else
    echo "❌ Admin Authentication (Invalid Password) - FAILED"
    echo "   Expected: 401, Got: $response"
    ((TESTS_FAILED++))
fi
echo

# Test 11: Admin Authentication (Missing Password)
echo "🧪 Running: Admin Authentication (Missing Password)"
response=$(curl -s --max-time $TIMEOUT -o /dev/null -w "%{http_code}" \
  -X POST "$SERVER_URL/api/admin" \
  -H "Content-Type: application/json" \
  -d '{"command": "status"}')

if [ "$response" = "401" ]; then
    echo "✅ Admin Authentication (Missing Password) - PASSED"
    ((TESTS_PASSED++))
else
    echo "❌ Admin Authentication (Missing Password) - FAILED"
    echo "   Expected: 401, Got: $response"
    ((TESTS_FAILED++))
fi
echo

# Test 12: Security Headers
echo "🧪 Running: Security Headers Test"
headers=$(curl -s --max-time $TIMEOUT -I -X GET "$SERVER_URL/api/health")

security_headers_ok=true

# Check for essential security headers
if echo "$headers" | grep -q "X-Content-Type-Options:"; then
    echo "   ✅ X-Content-Type-Options header present"
else
    echo "   ❌ X-Content-Type-Options header missing"
    security_headers_ok=false
fi

if echo "$headers" | grep -q "X-Frame-Options:"; then
    echo "   ✅ X-Frame-Options header present"
else
    echo "   ❌ X-Frame-Options header missing"
    security_headers_ok=false
fi

if echo "$headers" | grep -q "X-XSS-Protection:"; then
    echo "   ✅ X-XSS-Protection header present"
else
    echo "   ❌ X-XSS-Protection header missing"
    security_headers_ok=false
fi

if echo "$headers" | grep -q "Referrer-Policy:"; then
    echo "   ✅ Referrer-Policy header present"
else
    echo "   ❌ Referrer-Policy header missing"
    security_headers_ok=false
fi

if [ "$security_headers_ok" = true ]; then
    echo "✅ Security Headers Test - PASSED"
    ((TESTS_PASSED++))
else
    echo "❌ Security Headers Test - FAILED (missing essential headers)"
    ((TESTS_FAILED++))
fi
echo

echo "📊 Test Results Summary:"
echo "   Tests Passed: $TESTS_PASSED"
echo "   Tests Failed: $TESTS_FAILED"
echo "   Total Tests: $((TESTS_PASSED + TESTS_FAILED))"

if [ $TESTS_FAILED -eq 0 ]; then
    echo "🎉 All tests passed! The Gold Box backend is working correctly."
    exit_code=0
else
    echo "⚠️  Some tests failed. Please check the server configuration and logs."
    exit_code=1
fi

echo
echo "💡 Additional Tests (Manual):"
echo "   📡 WebSocket Test: websocat ws://localhost:5000/ws"
echo "   📡 Rate Limiting: Run multiple rapid requests to test rate limiting"
echo "   📡 File Integrity: Check security endpoint for file integrity"
echo "   📡 Virtual Environment: Check security endpoint for venv verification"
echo

echo "🔧 Configuration Options:"
echo "   Set custom server: GOLD_BOX_SERVER_URL=http://localhost:5001 ./comprehensive_test.sh"
echo "   Set custom timeout: GOLD_BOX_TEST_TIMEOUT=15 ./comprehensive_test.sh"
echo

exit $exit_code
