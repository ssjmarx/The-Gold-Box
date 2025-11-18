# Testing The Gold Box Backend Server

This document provides curl commands to test all API endpoints of The Gold Box backend server from the terminal.

## Prerequisites
1. Make sure the server is running (should be on localhost:5000 or the next available port)
2. The server will display the actual port when it starts
3. Install curl if not already available on your system

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

## Testing the Main Processing Endpoint

### 5. Basic Process Test (Simple Text)
```bash
curl -X POST http://localhost:5000/api/process \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Hello world, this is a test prompt"}'
```
*Expected*: Sanitized prompt echoed back with validation success message

### 6. Process Test with AI Parameters
```bash
curl -X POST http://localhost:5000/api/process \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Generate a fantasy character description",
    "max_tokens": 150,
    "temperature": 0.8,
    "top_p": 0.9,
    "frequency_penalty": 0.1,
    "presence_penalty": 0.1
  }'
```
*Expected*: Validated AI request with parameters echoed back

## Security & Validation Tests

### 7. Test XSS Protection (Should be blocked/sanitized)
```bash
curl -X POST http://localhost:5000/api/process \
  -H "Content-Type: application/json" \
  -d '{"prompt": "<script>alert(\"xss\")</script>Test prompt"}'
```
*Expected*: Sanitized output with script tags escaped or blocked

### 8. Test SQL Injection Protection (Should be blocked)
```bash
curl -X POST http://localhost:5000/api/process \
  -H "Content-Type: application/json" \
  -d '{"prompt": "SELECT * FROM users WHERE 1=1; DROP TABLE users;"}'
```
*Expected*: Error response indicating dangerous content detected

### 9. Test Command Injection Protection (Should be blocked)
```bash
curl -X POST http://localhost:5000/api/process \
  -H "Content-Type: application/json" \
  -d '{"prompt": "test; rm -rf /; echo done"}'
```
*Expected*: Error response indicating dangerous content detected

### 10. Test Rate Limiting (Run multiple times quickly)
```bash
for i in {1..6}; do
  echo "Request $i:"
  curl -X POST http://localhost:5000/api/process \
    -H "Content-Type: application/json" \
    -d "{\"prompt\": \"Test request number $i\"}"
  echo ""
  sleep 0.1
done
```
*Expected*: First 5 requests succeed, 6th returns rate limit error (429)

## Error Handling Tests

### 11. Test Invalid JSON
```bash
curl -X POST http://localhost:5000/api/process \
  -H "Content-Type: application/json" \
  -d '{"prompt": "test", invalid json}'
```
*Expected*: 400 error about invalid JSON

### 12. Test Missing Required Field
```bash
curl -X POST http://localhost:5000/api/process \
  -H "Content-Type: application/json" \
  -d '{"not_prompt": "test"}'
```
*Expected*: 400 error about missing required prompt field

### 13. Test Too Long Prompt
```bash
curl -X POST http://localhost:5000/api/process \
  -H "Content-Type: application/json" \
  -d '{"prompt": "'$(printf 'a'%.s {1..11000})'"}'
```
*Expected*: 400 error about prompt being too long (exceeds 10000 character limit)

## Parameter Validation Tests

### 14. Test Invalid AI Parameters
```bash
curl -X POST http://localhost:5000/api/process \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Test prompt",
    "temperature": 5.0,
    "max_tokens": -100
  }'
```
*Expected*: 400 error about invalid parameter ranges

### 15. Test Nonexistent Endpoint
```bash
curl -X GET http://localhost:5000/api/nonexistent
```
*Expected*: 404 error with list of available endpoints

## Advanced Testing with Headers

### 16. Test with Custom Headers
```bash
curl -X POST http://localhost:5000/api/process \
  -H "Content-Type: application/json" \
  -H "X-API-Key: test-key-123" \
  -d '{"prompt": "Test with API key header"}'
```
*Expected*: Will process but API key validation depends on server configuration

## Utility Commands

### Pretty Print JSON Responses
For better readability, pipe responses to `jq`:
```bash
curl -X GET http://localhost:5000/api/info | jq .
```

### Testing Different Ports
If the server starts on a different port (like 5001), just update the URLs:
```bash
curl -X GET http://localhost:5001/api/health
```

### Monitoring Server Logs
You can monitor the server logs in real-time while testing:
```bash
tail -f goldbox.log
```

### Save Responses to File
```bash
curl -X GET http://localhost:5000/api/info > response.json
```

## Test Script Automation

### Quick Test Script
Save this as `test_server.sh` and make it executable:
```bash
#!/bin/bash

echo "=== The Gold Box Backend Test Suite ==="
echo

# Test basic endpoints
echo "1. Testing health check..."
curl -s -X GET http://localhost:5000/api/health | jq .
echo

echo "2. Testing service info..."
curl -s -X GET http://localhost:5000/api/info | jq '.name, .version, .status'
echo

echo "3. Testing basic process..."
curl -s -X POST http://localhost:5000/api/process \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Test prompt"}' | jq '.status, .validation_passed'
echo

echo "4. Testing security validation..."
curl -s -X POST http://localhost:5000/api/process \
  -H "Content-Type: application/json" \
  -d '{"prompt": "<script>alert(\"xss\")</script>"}' | jq '.status, .error'
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

These tests will help you verify all the security features, validation logic, and functionality of The Gold Box backend server.
