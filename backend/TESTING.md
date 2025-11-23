# Testing The Gold Box Backend Server (v0.2.5)

This document provides comprehensive curl commands to test all API endpoints and security features of The Gold Box backend server from the terminal.

> **Important**: Before testing chat endpoints, you must configure API keys through the key management system. Run the server without API keys configured and follow the interactive setup wizard, or set `GOLD_BOX_KEYCHANGE=true` environment variable to force the key management interface.

> **Note**: For comprehensive environmental variable configuration options, see [USAGE.md](../USAGE.md).

## Prerequisites
1. Make sure the server is running (should be on localhost:5000 or next available port)
2. The server will display the actual port when it starts
3. Install curl if not already available on your system
4. **Configure API keys** through the key management system before testing chat endpoints
5. **Initialize a session** for endpoints that require authentication

## Session Management Setup

### Session Variables
```bash
# Initialize a session and store variables for subsequent tests
SESSION_RESPONSE=$(curl -s -X POST http://localhost:5000/api/session/init \
  -H "Content-Type: application/json" \
  -d '{}')

# Extract session ID and CSRF token
SESSION_ID=$(echo $SESSION_RESPONSE | jq -r '.session_id')
CSRF_TOKEN=$(echo $SESSION_RESPONSE | jq -r '.csrf_token')

echo "Session ID: $SESSION_ID"
echo "CSRF Token: $CSRF_TOKEN"
```

## Endpoint Tests (One Test Per Endpoint)

### 1. Health Check Endpoint
```bash
curl -X GET http://localhost:5000/api/health | jq .
```
*Expected*: Server status, version, and basic configuration info

### 2. Service Information Endpoint
```bash
curl -X GET http://localhost:5000/api/info | jq .
```
*Expected*: Detailed information about features, validation capabilities, and security status

### 3. Security Verification Endpoint
```bash
curl -X GET http://localhost:5000/api/security | jq .
```
*Expected*: Comprehensive security check results including file integrity, permissions, and dependencies

### 4. Startup Instructions Endpoint
```bash
curl -X POST http://localhost:5000/api/start | jq .
```
*Expected*: Manual startup instructions and environment information

### 5. Session Initialization Endpoint
```bash
curl -X POST http://localhost:5000/api/session/init \
  -H "Content-Type: application/json" \
  -d '{}' | jq .
```
*Expected*: New session with ID, CSRF token, and expiry time

### 6. Session Extension Endpoint
```bash
curl -X POST http://localhost:5000/api/session/init \
  -H "Content-Type: application/json" \
  -d '{"session_id": "'$SESSION_ID'", "extend_existing": true}' | jq .
```
*Expected*: Extended session with updated expiry time

### 7. Simple Chat Endpoint (Requires API Keys)
```bash
curl -X POST http://localhost:5000/api/simple_chat \
  -H "Content-Type: application/json" \
  -H "X-Session-ID: $SESSION_ID" \
  -H "X-CSRF-Token: $CSRF_TOKEN" \
  -d '{
    "settings": {
      "general llm provider": "openai",
      "general llm model": "gpt-3.5-turbo"
    },
    "messages": [
      {"sender": "User", "content": "Hello world, this is a test prompt"}
    ]
  }' | jq .
```
*Expected*: AI response from configured provider with success status

### 8. Process Chat Endpoint (Requires API Keys)
```bash
curl -X POST http://localhost:5000/api/process_chat \
  -H "Content-Type: application/json" \
  -H "X-Session-ID: $SESSION_ID" \
  -H "X-CSRF-Token: $CSRF_TOKEN" \
  -d '{
    "messages": [
      "<div class=\"chat-message\"><div class=\"message-content\"><p>Hello from Foundry!</p></div></div>",
      "<div class=\"chat-message dice-roll\"><div class=\"dice-result\">3d6: 2, 4, 2 = 8</div></div>"
    ],
    "settings": {
      "general llm provider": "openai",
      "general llm model": "gpt-3.5-turbo"
    }
  }' | jq .
```
*Expected*: Processed AI response with compact JSON conversion and HTML rendering

### 9. Process Chat Status Endpoint
```bash
curl -X GET http://localhost:5000/api/process_chat/status/test_req_123456 | jq .
```
*Expected*: Processing status for specified request ID (not_found if request doesn't exist)

### 10. Process Chat Validation Endpoint
```bash
curl -X POST http://localhost:5000/api/process_chat/validate \
  -H "Content-Type: application/json" \
  -H "X-Session-ID: $SESSION_ID" \
  -H "X-CSRF-Token: $CSRF_TOKEN" \
  -d '[
    "<div class=\"chat-message\"><div class=\"message-content\"><p>Test message</p></div></div>",
    {
      "sender": "User",
      "content": "<div class=\"dice-roll\">1d20: 15</div>",
      "timestamp": "2025-01-01T12:00:00Z"
    }
  ]' | jq .
```
*Expected*: Validation results for each message with compact JSON conversion

### 11. Process Chat Schemas Endpoint
```bash
curl -X GET http://localhost:5000/api/process_chat/schemas | jq .
```
*Expected*: Compact JSON schemas, type codes, and system prompt

### 12. Process Chat Test Endpoint
```bash
curl -X GET http://localhost:5000/api/process_chat/test | jq .
```
*Expected*: Operational status confirming processor and provider manager are loaded

### 13. Admin Status Endpoint (Requires Admin Password)
```bash
curl -X POST http://localhost:5000/api/admin \
  -H "Content-Type: application/json" \
  -H "X-Admin-Password: your-admin-password" \
  -d '{"command": "status"}' | jq .
```
*Expected*: Server status, features, and endpoints list

### 14. Admin Reload Keys Endpoint
```bash
curl -X POST http://localhost:5000/api/admin \
  -H "Content-Type: application/json" \
  -H "X-Admin-Password: your-admin-password" \
  -d '{"command": "reload_keys"}' | jq .
```
*Expected*: Environment variables reloaded with updated keys status

### 15. Admin Set Password Endpoint
```bash
curl -X POST http://localhost:5000/api/admin \
  -H "Content-Type: application/json" \
  -H "X-Admin-Password: your-admin-password" \
  -d '{"command": "set_admin_password", "password": "new-secure-password"}' | jq .
```
*Expected*: Admin password updated successfully

### 16. Admin Update Settings Endpoint
```bash
curl -X POST http://localhost:5000/api/admin \
  -H "Content-Type: application/json" \
  -H "X-Admin-Password: your-admin-password" \
  -d '{"command": "update_settings", "settings": {"test_setting": "test_value"}}' | jq .
```
*Expected*: Frontend settings updated with confirmation

## Security Feature Tests (One Test Per Security Feature)

### 17. Rate Limiting Test
```bash
echo "Testing rate limiting (should succeed first 5, fail on 6th)..."
for i in {1..6}; do
  echo "Request $i:"
  response=$(curl -s -o /dev/null -w "%{http_code}" \
    -X POST http://localhost:5000/api/simple_chat \
    -H "Content-Type: application/json" \
    -H "X-Session-ID: $SESSION_ID" \
    -H "X-CSRF-Token: $CSRF_TOKEN" \
    -d '{
      "settings": {"general llm provider": "openai"},
      "messages": [{"sender": "User", "content": "Rate limit test $i"}]
    }')
  echo "HTTP $response"
  if [ "$response" = "429" ]; then
    echo "✓ Rate limiting activated on request $i"
  fi
  sleep 0.1
done
```
*Expected*: First 5 requests succeed (200), 6th fails with 429 rate limit error

### 18. CSRF Protection Test (Invalid Token)
```bash
curl -s -X POST http://localhost:5000/api/simple_chat \
  -H "Content-Type: application/json" \
  -H "X-Session-ID: $SESSION_ID" \
  -H "X-CSRF-Token: invalid-csrf-token" \
  -d '{
    "settings": {"general llm provider": "openai"},
    "messages": [{"sender": "User", "content": "CSRF test"}]
  }' | jq .
```
*Expected*: 403 Forbidden error with CSRF token validation failed message

### 19. CSRF Protection Test (Missing Token)
```bash
curl -s -X POST http://localhost:5000/api/simple_chat \
  -H "Content-Type: application/json" \
  -H "X-Session-ID: $SESSION_ID" \
  -d '{
    "settings": {"general llm provider": "openai"},
    "messages": [{"sender": "User", "content": "No CSRF token test"}]
  }' | jq .
```
*Expected*: 403 Forbidden error with CSRF token required message

### 20. Session Validation Test (Invalid Session)
```bash
curl -s -X POST http://localhost:5000/api/simple_chat \
  -H "Content-Type: application/json" \
  -H "X-Session-ID: invalid-session-id" \
  -H "X-CSRF-Token: $CSRF_TOKEN" \
  -d '{
    "settings": {"general llm provider": "openai"},
    "messages": [{"sender": "User", "content": "Invalid session test"}]
  }' | jq .
```
*Expected*: 401 Unauthorized error with session validation failed message

### 21. Session Validation Test (Missing Session)
```bash
curl -s -X POST http://localhost:5000/api/simple_chat \
  -H "Content-Type: application/json" \
  -H "X-CSRF-Token: $CSRF_TOKEN" \
  -d '{
    "settings": {"general llm provider": "openai"},
    "messages": [{"sender": "User", "content": "No session test"}]
  }' | jq .
```
*Expected*: 401 Unauthorized error with session required message

### 22. Input Validation Test (XSS Protection)
```bash
curl -s -X POST http://localhost:5000/api/simple_chat \
  -H "Content-Type: application/json" \
  -H "X-Session-ID: $SESSION_ID" \
  -H "X-CSRF-Token: $CSRF_TOKEN" \
  -d '{
    "settings": {"general llm provider": "openai"},
    "messages": [{"sender": "User", "content": "<script>alert(\"xss\")</script>Test prompt"}]
  }' | jq .
```
*Expected*: 400 Bad Request error with dangerous content detected (XSS)

### 23. Input Validation Test (SQL Injection)
```bash
curl -s -X POST http://localhost:5000/api/simple_chat \
  -H "Content-Type: application/json" \
  -H "X-Session-ID: $SESSION_ID" \
  -H "X-CSRF-Token: $CSRF_TOKEN" \
  -d '{
    "settings": {"general llm provider": "openai"},
    "messages": [{"sender": "User", "content": "SELECT * FROM users WHERE 1=1; DROP TABLE users;"}]
  }' | jq .
```
*Expected*: 400 Bad Request error with dangerous content detected (SQL injection)

### 24. Input Validation Test (Command Injection)
```bash
curl -s -X POST http://localhost:5000/api/simple_chat \
  -H "Content-Type: application/json" \
  -H "X-Session-ID: $SESSION_ID" \
  -H "X-CSRF-Token: $CSRF_TOKEN" \
  -d '{
    "settings": {"general llm provider": "openai"},
    "messages": [{"sender": "User", "content": "test; rm -rf /; echo done"}]
  }' | jq .
```
*Expected*: 400 Bad Request error with dangerous content detected (command injection)

### 25. Input Validation Test (HTML Safe Mode - Foundry VTT)
```bash
curl -s -X POST http://localhost:5000/api/process_chat \
  -H "Content-Type: application/json" \
  -H "X-Session-ID: $SESSION_ID" \
  -H "X-CSRF-Token: $CSRF_TOKEN" \
  -d '{
    "messages": [
      "<div class=\"chat-message player-chat\"><div class=\"message-content\"><p>Safe Foundry HTML</p></div></div>",
      "<div class=\"chat-message dice-roll\"><div class=\"dice-formula\">3d6</div><div class=\"dice-result\">8</div></div>"
    ],
    "settings": {"general llm provider": "openai"}
  }' | jq '.processed_context'
```
*Expected*: Successfully processed messages with HTML structure preserved in compact JSON format

### 26. Security Headers Test
```bash
curl -I -X GET http://localhost:5000/api/health
```
*Expected*: Security headers including:
- X-Content-Type-Options: nosniff
- X-Frame-Options: DENY
- X-XSS-Protection: 1; mode=block
- Referrer-Policy: strict-origin-when-cross-origin
- Cache-Control: no-store, no-cache, must-revalidate

### 27. CORS Protection Test
```bash
curl -H "Origin: https://malicious-site.com" \
  -H "Access-Control-Request-Method: POST" \
  -H "Access-Control-Request-Headers: Content-Type" \
  -X OPTIONS http://localhost:5000/api/simple_chat
```
*Expected*: 403 Forbidden or no Access-Control-Allow-Origin header (depending on CORS configuration)

### 28. File Integrity Test
```bash
# This is tested via the security endpoint
curl -s -X GET http://localhost:5000/api/security | jq '.checks.file_integrity'
```
*Expected*: File integrity verification with hash checks for critical files

### 29. Virtual Environment Test
```bash
# This is tested via the security endpoint
curl -s -X GET http://localhost:5000/api/security | jq '.checks.virtual_environment'
```
*Expected*: Virtual environment isolation verification

### 30. Permission Security Test
```bash
# This is tested via the security endpoint
curl -s -X GET http://localhost:5000/api/security | jq '.checks.file_permissions'
```
*Expected*: File permissions security verification

### 31. Audit Logging Test
```bash
# Make a request that should be logged
curl -s -X POST http://localhost:5000/api/simple_chat \
  -H "Content-Type: application/json" \
  -H "X-Session-ID: $SESSION_ID" \
  -H "X-CSRF-Token: $CSRF_TOKEN" \
  -d '{"settings": {"general llm provider": "openai"}, "messages": [{"sender": "User", "content": "Audit log test"}]}' > /dev/null

# Check if audit log was created/updated
tail -n 5 server_files/security_audit.log | jq .
```
*Expected*: Recent audit log entries showing the request with timestamp, client info, and endpoint

### 32. Session Expiration Test
```bash
# Create a session and wait for expiration (or manually expire)
OLD_SESSION_RESPONSE=$(curl -s -X POST http://localhost:5000/api/session/init \
  -H "Content-Type: application/json" \
  -d '{}')

OLD_SESSION_ID=$(echo $OLD_SESSION_RESPONSE | jq -r '.session_id')

# Try to use expired session (will work immediately after creation, fail after timeout)
curl -s -X POST http://localhost:5000/api/simple_chat \
  -H "Content-Type: application/json" \
  -H "X-Session-ID: $OLD_SESSION_ID" \
  -H "X-CSRF-Token: $CSRF_TOKEN" \
  -d '{"settings": {"general llm provider": "openai"}, "messages": [{"sender": "User", "content": "Session test"}]}' | jq .
```
*Expected*: Success initially, 401 error after session expires

### 33. Admin Authentication Test (Invalid Password)
```bash
curl -s -X POST http://localhost:5000/api/admin \
  -H "Content-Type: application/json" \
  -H "X-Admin-Password: wrong-password" \
  -d '{"command": "status"}' | jq .
```
*Expected*: 401 Unauthorized error with invalid admin password message

### 34. Admin Authentication Test (Missing Password)
```bash
curl -s -X POST http://localhost:5000/api/admin \
  -H "Content-Type: application/json" \
  -d '{"command": "status"}' | jq .
```
*Expected*: 401 Unauthorized error with admin password required message

## Comprehensive Test Script

Save this as `comprehensive_test.sh` and make it executable:

```bash
#!/bin/bash

echo "=== The Gold Box Backend Comprehensive Test Suite v0.2.5 ==="
echo

# Initialize session
echo "🔐 Initializing session..."
SESSION_RESPONSE=$(curl -s -X POST http://localhost:5000/api/session/init \
  -H "Content-Type: application/json" \
  -d '{}')

SESSION_ID=$(echo $SESSION_RESPONSE | jq -r '.session_id')
CSRF_TOKEN=$(echo $SESSION_RESPONSE | jq -r '.csrf_token')

echo "Session ID: $SESSION_ID"
echo "CSRF Token: $CSRF_TOKEN"
echo

# Test endpoints
echo "📡 Testing API Endpoints..."
echo

echo "1. Health Check..."
curl -s -X GET http://localhost:5000/api/health | jq '.status, .version'
echo

echo "2. Service Info..."
curl -s -X GET http://localhost:5000/api/info | jq '.name, .version, .status'
echo

echo "3. Security Verification..."
curl -s -X GET http://localhost:5000/api/security | jq '.overall_status, .security_score'
echo

echo "4. Process Chat Schemas..."
curl -s -X GET http://localhost:5000/api/process_chat/schemas | jq '.type_codes | keys'
echo

echo "5. Process Chat Test..."
curl -s -X GET http://localhost:5000/api/process_chat/test | jq '.status'
echo

# Test security features
echo "🛡️ Testing Security Features..."
echo

echo "6. CSRF Protection (Invalid Token)..."
response=$(curl -s -o /dev/null -w "%{http_code}" \
  -X POST http://localhost:5000/api/simple_chat \
  -H "Content-Type: application/json" \
  -H "X-Session-ID: $SESSION_ID" \
  -H "X-CSRF-Token: invalid-token" \
  -d '{"settings": {"general llm provider": "openai"}, "messages": [{"sender": "Test", "content": "test"}]}')
if [ "$response" = "403" ]; then echo "✓ CSRF protection working"; else echo "✗ CSRF protection failed"; fi
echo

echo "7. Input Validation (XSS)..."
response=$(curl -s -o /dev/null -w "%{http_code}" \
  -X POST http://localhost:5000/api/simple_chat \
  -H "Content-Type: application/json" \
  -H "X-Session-ID: $SESSION_ID" \
  -H "X-CSRF-Token: $CSRF_TOKEN" \
  -d '{"settings": {"general llm provider": "openai"}, "messages": [{"sender": "Test", "content": "<script>alert(\"xss\")</script>"}]}')
if [ "$response" = "400" ]; then echo "✓ XSS protection working"; else echo "✗ XSS protection failed"; fi
echo

echo "8. Rate Limiting..."
echo "Testing rate limit (first 5 should succeed, 6th should fail)..."
success_count=0
for i in {1..6}; do
  response=$(curl -s -o /dev/null -w "%{http_code}" \
    -X POST http://localhost:5000/api/simple_chat \
    -H "Content-Type: application/json" \
    -H "X-Session-ID: $SESSION_ID" \
    -H "X-CSRF-Token: $CSRF_TOKEN" \
    -d '{"settings": {"general llm provider": "openai"}, "messages": [{"sender": "Test", "content": "rate test $i"}]}')
  if [ "$response" = "200" ]; then
    ((success_count++))
  elif [ "$response" = "429" ]; then
    echo "✓ Rate limiting activated on request $i"
    break
  fi
  sleep 0.1
done
if [ $success_count -eq 5 ]; then echo "✓ Rate limiting working correctly"; else echo "✗ Rate limiting issue (successes: $success_count)"; fi
echo

echo "9. Admin Authentication..."
response=$(curl -s -o /dev/null -w "%{http_code}" \
  -X POST http://localhost:5000/api/admin \
  -H "Content-Type: application/json" \
  -H "X-Admin-Password: wrong-password" \
  -d '{"command": "status"}')
if [ "$response" = "401" ]; then echo "✓ Admin authentication working"; else echo "✗ Admin authentication failed"; fi
echo

echo "10. Security Headers..."
headers=$(curl -I -X GET http://localhost:5000/api/health 2>/dev/null)
if echo "$headers" | grep -q "X-Content-Type-Options"; then echo "✓ Security headers present"; else echo "✗ Security headers missing"; fi
echo

echo "=== Test Suite Complete ==="
echo "Note: Some tests may require valid API keys for full functionality"
```

Make it executable:
```bash
chmod +x comprehensive_test.sh
./comprehensive_test.sh
```

## Utility Commands

### Pretty Print JSON Responses
For better readability, pipe responses to `jq`:
```bash
curl -X GET http://localhost:5000/api/info | jq .
```

### Testing Different Ports
If server starts on a different port (like 5001), just update URLs:
```bash
curl -X GET http://localhost:5001/api/health
```

### Monitoring Server Logs
You can monitor server logs in real-time while testing:
```bash
tail -f server_files/goldbox.log
```

### Monitoring Security Audit Log
```bash
tail -f server_files/security_audit.log
```

### Testing with Custom Timeouts
```bash
curl --max-time 10 -X POST http://localhost:5000/api/simple_chat \
  -H "Content-Type: application/json" \
  -H "X-Session-ID: $SESSION_ID" \
  -H "X-CSRF-Token: $CSRF_TOKEN" \
  -d '{"settings": {"general llm provider": "openai"}, "messages": [{"sender": "User", "content": "timeout test"}]}'
```

## Expected Behavior Summary

### Successful Responses
- Status code: 200
- JSON format with `status: "success"` where applicable
- Validated and sanitized input returned
- AI response from configured provider
- Session and CSRF tokens validated

### Error Responses
- Status codes: 400, 401, 403, 404, 429, 500
- JSON format with `status: "error"` where applicable
- Descriptive error messages with validation step information
- Security violations logged to audit log

### Security Features Verified
- ✅ CSRF protection (token validation)
- ✅ Session management (creation, validation, expiration)
- ✅ Rate limiting (configurable per endpoint)
- ✅ Input validation (XSS, SQL injection, command injection)
- ✅ HTML-safe mode for Foundry VTT compatibility
- ✅ Security headers (CSP, XSS protection, etc.)
- ✅ CORS restrictions (origin-based)
- ✅ File integrity verification
- ✅ Virtual environment verification
- ✅ Permission security checks
- ✅ Audit logging (structured JSON)
- ✅ Admin authentication (password protected)

## Troubleshooting

### Connection Issues
- Check if server is running with `ps aux | grep python`
- Verify correct port number from server startup output
- Check firewall settings: `ufw status` or `iptables -L`

### Authentication Issues
- Ensure session is properly initialized
- Check CSRF token is included in headers
- Verify session hasn't expired (default 60 minutes)
- Confirm admin password is correct

### Rate Limiting
- Wait for rate limit window to reset (default 60 seconds)
- Check rate limit configuration in security_config.ini
- Monitor rate limit data in server_files/rate_limits.json

### Validation Errors
- Check request format matches expected schemas
- Verify no dangerous content patterns in input
- Ensure HTML content is properly formatted for Foundry VTT
- Check message length limits

### Security Verification
- Run security endpoint: `curl -X GET http://localhost:5000/api/security`
- Check audit log for security events
- Verify file permissions on server_files directory
- Confirm virtual environment isolation

This comprehensive testing suite covers all endpoints and security features implemented in The Gold Box v0.2.5 backend server.
