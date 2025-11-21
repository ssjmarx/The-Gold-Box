# Testing The Gold Box Backend Server (v0.2.4)

This document provides curl commands to test all API endpoints of The Gold Box backend server from the terminal.

> **Important**: Before testing the `/api/simple_chat` endpoint, you must configure an API key through the key management system. Run the server without API keys configured and follow the interactive setup wizard, or set the `GOLD_BOX_KEYCHANGE=true` environment variable to force the key management interface.

> **Note**: For comprehensive environmental variable configuration options, see [USAGE.md](../USAGE.md).

## Prerequisites
1. Make sure the server is running (should be on localhost:5000 or the next available port)
2. The server will display the actual port when it starts
3. Install curl if not already available on your system
4. **Configure API keys** through the key management system before testing chat endpoints

## Basic Endpoint Tests

### 1. Health Check
```bash
curl -X GET http://localhost:5000/api/health
```
*Expected*: Server status, version, and basic configuration info

### 2. Service Information
```bash
curl -X GET http://localhost:5000/api/info
```
*Expected*: Detailed information about features, validation capabilities, and security status

### 3. Security Verification
```bash
curl -X GET http://localhost:5000/api/security
```
*Expected*: Comprehensive security check results including file integrity, permissions, and dependencies

### 4. Startup Instructions
```bash
curl -X POST http://localhost:5000/api/start
```
*Expected*: Manual startup instructions and environment information

## Main Chat Endpoint Test

### 5. Basic Simple Chat Test
```bash
curl -X POST http://localhost:5000/api/simple_chat \
  -H "Content-Type: application/json" \
  -d '{
    "settings": {
      "general llm provider": "openai",
      "general llm model": "gpt-3.5-turbo"
    },
    "messages": [
      {"sender": "User", "content": "Hello world, this is a test prompt"}
    ]
  }'
```
*Expected*: AI response from configured provider with success status

## Admin Endpoint Test

### 6. Admin Status Test
```bash
curl -X POST http://localhost:5000/api/admin \
  -H "Content-Type: application/json" \
  -H "X-Admin-Password: your-admin-password" \
  -d '{"command": "status"}'
```
*Expected*: Server status and features list

## Major Security Feature Tests

### 7. XSS Protection Test
```bash
curl -X POST http://localhost:5000/api/simple_chat \
  -H "Content-Type: application/json" \
  -d '{
    "settings": {
      "general llm provider": "openai"
    },
    "messages": [
      {"sender": "User", "content": "<script>alert(\"xss\")</script>Test prompt"}
    ]
  }'
```
*Expected*: Sanitized output with script tags escaped or blocked

### 8. SQL Injection Protection Test
```bash
curl -X POST http://localhost:5000/api/simple_chat \
  -H "Content-Type: application/json" \
  -d '{
    "settings": {
      "general llm provider": "openai"
    },
    "messages": [
      {"sender": "User", "content": "SELECT * FROM users WHERE 1=1; DROP TABLE users;"}
    ]
  }'
```
*Expected*: Error response indicating dangerous content detected

### 9. Command Injection Protection Test
```bash
curl -X POST http://localhost:5000/api/simple_chat \
  -H "Content-Type: application/json" \
  -d '{
    "settings": {
      "general llm provider": "openai"
    },
    "messages": [
      {"sender": "User", "content": "test; rm -rf /; echo done"}
    ]
  }'
```
*Expected*: Error response indicating dangerous content detected

### 10. Rate Limiting Test
```bash
for i in {1..6}; do
  echo "Request $i:"
  curl -X POST http://localhost:5000/api/simple_chat \
    -H "Content-Type: application/json" \
    -d '{
      "settings": {"general llm provider": "openai"},
      "messages": [{"sender": "User", "content": "Test request number $i"}]
    }'
  echo ""
  sleep 0.1
done
```
*Expected*: First 5 requests succeed, 6th returns rate limit error (429)

## Error Handling Test

### 11. Invalid Request Test
```bash
curl -X POST http://localhost:5000/api/simple_chat \
  -H "Content-Type: application/json" \
  -d '{
    "settings": {
      "general llm provider": "openai"
    }
  }'
```
*Expected*: 400 error about missing required messages field

## Utility Commands

### Pretty Print JSON Responses
For better readability, pipe responses to `jq`:
```bash
curl -X GET http://localhost:5000/api/info | jq .
```

### Testing Different Ports
If the server starts on a different port (like 5001), just update URLs:
```bash
curl -X GET http://localhost:5001/api/health
```

### Monitoring Server Logs
You can monitor server logs in real-time while testing:
```bash
tail -f goldbox.log
```

## Quick Test Script

Save this as `test_server.sh` and make it executable:
```bash
#!/bin/bash

echo "=== The Gold Box Backend Test Suite ==="
echo

echo "1. Testing health check..."
curl -s -X GET http://localhost:5000/api/health | jq .
echo

echo "2. Testing service info..."
curl -s -X GET http://localhost:5000/api/info | jq '.name, .version, .status'
echo

echo "3. Testing simple chat..."
curl -s -X POST http://localhost:5000/api/simple_chat \
  -H "Content-Type: application/json" \
  -d '{
    "settings": {"general llm provider": "openai"},
    "messages": [{"sender": "User", "content": "Test prompt"}]
  }' | jq '.status'
echo

echo "4. Testing security validation..."
curl -s -X POST http://localhost:5000/api/simple_chat \
  -H "Content-Type: application/json" \
  -d '{
    "settings": {"general llm provider": "openai"},
    "messages": [{"sender": "User", "content": "<script>alert(\"xss\")</script>"}]
  }' | jq '.status, .error'
echo

echo "5. Testing admin endpoint..."
curl -s -X POST http://localhost:5000/api/admin \
  -H "Content-Type: application/json" \
  -H "X-Admin-Password: your-admin-password" \
  -d '{"command": "status"}' | jq '.service, .version'
echo

echo "=== Test Suite Complete ==="
```

Make it executable:
```bash
chmod +x test_server.sh
./test_server.sh
```

## Expected Behavior Summary

### Successful Responses
- Status code: 200
- JSON format with `status: "success"`
- Validated and sanitized input returned
- AI response from configured provider

### Error Responses
- Status codes: 400, 401, 404, 429, 500
- JSON format with `status: "error"`
- Descriptive error messages with validation step information

### Security Features Verified
- XSS protection
- SQL injection prevention
- Command injection blocking
- Input sanitization
- Rate limiting
- Session management
- CORS restrictions

## Troubleshooting

### Connection Refused
- Check if server is running
- Verify correct port number
- Check firewall settings

### CORS Errors
- Ensure correct origin is configured
- Check development vs production CORS settings

### Rate Limiting
- Wait for the rate limit window to reset (default 60 seconds)
- Adjust rate limit settings in environment variables

### Validation Errors
- Check request format and required fields
- Verify input length limits
- Ensure no dangerous content patterns

These essential tests will help you verify the core functionality and security features of The Gold Box backend server.
