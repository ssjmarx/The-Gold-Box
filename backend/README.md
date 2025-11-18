# The Gold Box Backend Setup

This Python backend provides the AI processing capabilities for The Gold Box Foundry VTT module.

## Quick Start

### 1. Install Dependencies

```bash
# Navigate to the backend directory
cd backend

# Install Python packages
pip install -r requirements.txt
```

### 2. Start the Server

```bash
# Use the unified launcher script (recommended)
./backend.sh

# Or run server directly
python server.py
```

The server will:
- Default to **production mode** with Gunicorn WSGI server
- Fall back to Flask development server if Gunicorn is not available
- Start on the first available port from 5000 upwards
- Automatically trigger key management setup on first run

**Development Mode:**
```bash
# Force development mode
./backend.sh --dev

# Or set environment variable
USE_DEVELOPMENT_SERVER=true ./backend.sh
```

### 3. Test the Backend

Open your browser or use curl to test:

```bash
# Health check
curl http://localhost:5000/api/health

# Service info
curl http://localhost:5000/api/info

# Test prompt processing
curl -X POST http://localhost:5000/api/process \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Hello, AI!"}'
```

## Configuration

### Environment Variables

- `FLASK_DEBUG`: Set to `True` for development, `False` for production
- `GOLD_BOX_PORT`: Server port (default: 5000)
- `RATE_LIMIT_MAX_REQUESTS`: Maximum requests per time window (default: 5)
- `RATE_LIMIT_WINDOW_SECONDS`: Time window for rate limiting in seconds (default: 60)
- `SESSION_TIMEOUT_MINUTES`: Session timeout duration (default: 30)
- `SESSION_WARNING_MINUTES`: Session warning time before timeout (default: 5)
- `CORS_ORIGINS`: Comma-separated list of allowed origins (production only, e.g., "https://example.com,https://app.example.com")
- `LOG_LEVEL`: Logging level (DEBUG, INFO, WARNING, ERROR, default: INFO)
- `LOG_FILE`: Log file path (default: goldbox.log)
- `GOLD_BOX_OPENAI_COMPATIBLE_API_KEY`: OpenAI-compatible API key
- `GOLD_BOX_NOVELAI_API_API_KEY`: NovelAI API key

Server runs on `localhost:5000` by default, with automatic port discovery if the default port is occupied.

### Security Features

- **Universal Input Validation**: Comprehensive input validation with type-specific checking, security pattern detection, and sanitization
- **Session Management**: Configurable session timeouts with warnings (30-minute timeout, 5-minute warnings by default)
- **Rate Limiting**: Configurable rate limiting per IP address (5 requests per minute by default)
- **Enhanced Security Headers**: X-Content-Type-Options, X-Frame-Options, X-XSS-Protection, Referrer-Policy
- **CORS Protection**: Environment-based CORS configuration with security-focused defaults
- **File Integrity Verification**: SHA256 hash checking for critical files
- **Virtual Environment Verification**: Ensures proper isolation
- **Permission Verification**: Automated file permission security checks
- **XSS Protection**: HTML escaping and script injection prevention
- **SQL Injection Protection**: Pattern-based SQL injection detection
- **Command Injection Protection**: Command execution attempt detection
- **Error Handling**: Comprehensive error responses with detailed validation feedback

## API Endpoints

### GET /api/health
Health check endpoint.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2024-01-01T12:00:00",
  "version": "0.1.0",
  "service": "The Gold Box Backend",
  "api_key_required": false,
  "environment": "development",
  "validation_enabled": true,
  "universal_validator": true,
  "rate_limiting": {
    "max_requests": 5,
    "window_seconds": 60
  },
  "cors": {
    "origins_count": 3,
    "configured": true,
    "methods": ["GET", "POST", "OPTIONS"]
  }
}
```

### GET /api/info
Service information endpoint.

**Response:**
```json
{
  "name": "The Gold Box Backend",
  "description": "AI-powered Foundry VTT Module Backend",
  "version": "0.1.0",
  "status": "running",
  "environment": "development",
  "api_key_required": false,
  "validation_features": {
    "universal_validator": true,
    "input_sanitization": true,
    "security_pattern_checking": true,
    "type_specific_validation": true,
    "structured_data_support": true,
    "ai_parameter_validation": true
  },
  "supported_input_types": ["text", "prompt", "api_key", "config", "url", "email", "filename"],
  "size_limits": {
    "prompt": 10000,
    "text": 50000,
    "api_key": 500,
    "config": 1000,
    "url": 2048,
    "email": 254,
    "filename": 255
  },
  "endpoints": {
    "process": "POST /api/process - Process AI prompts (enhanced validation)",
    "health": "GET /api/health - Health check",
    "info": "GET /api/info - Service information",
    "security": "GET /api/security - Security verification and integrity checks",
    "start": "POST /api/start - Server startup instructions"
  },
  "license": "CC-BY-NC-SA 4.0",
  "dependencies": {
    "Flask": "BSD 3-Clause License",
    "Flask-CORS": "MIT License"
  },
  "security": {
    "api_authentication": false,
    "rate_limiting": true,
    "cors_restrictions": true,
    "input_validation": "UniversalInputValidator",
    "security_headers": true,
    "xss_protection": true,
    "sql_injection_protection": true,
    "command_injection_protection": true
  }
}
```

### POST /api/process
Main AI processing endpoint with comprehensive input validation and session management.

**Request:**
```json
{
  "prompt": "Your AI prompt here",
  "max_tokens": 100,
  "temperature": 0.7,
  "top_p": 1.0,
  "frequency_penalty": 0.0,
  "presence_penalty": 0.0
}
```

**Response:**
```json
{
  "status": "success",
  "response": "Sanitized prompt echoed back",
  "original_prompt": "Your sanitized AI prompt here",
  "timestamp": "2024-01-01T12:00:00",
  "processing_time": 0.001,
  "message": "AI functionality: Basic echo server - prompt sanitized and returned unchanged",
  "validation_passed": true,
  "sanitization_applied": true,
  "rate_limit_remaining": 4,
  "ai_parameters": {
    "max_tokens": 100,
    "temperature": 0.7,
    "top_p": 1.0,
    "frequency_penalty": 0.0,
    "presence_penalty": 0.0
  }
}
```

### GET /api/security
Security verification endpoint for comprehensive integrity checks.

**Response:**
```json
{
  "timestamp": "2024-01-01T12:00:00",
  "status": "verified",
  "overall_status": "secure",
  "security_score": 5,
  "checks": {
    "virtual_environment": {
      "verified": true,
      "message": "Virtual environment isolation verified"
    },
    "file_integrity": {
      "verified": true,
      "hashes": ["requirements.txt: abc123...", "server.py: def456..."],
      "message": "Critical file integrity verified"
    },
    "file_permissions": {
      "verified": true,
      "issues": [],
      "message": "File permissions secure"
    },
    "dependencies": {
      "verified": true,
      "status": ["Flask: 2.3.0 - OK", "Flask-CORS: 4.0.0 - OK"],
      "message": "Dependencies verified"
    },
    "session_management": {
      "verified": true,
      "active_sessions": 2,
      "timeout_configured": true,
      "timeout_minutes": 30,
      "warning_minutes": 5,
      "message": "Session management active with 2 sessions"
    },
    "rate_limiting": {
      "verified": true,
      "max_requests": 5,
      "window_seconds": 60,
      "message": "Rate limiting configured and active"
    },
    "cors_configuration": {
      "verified": true,
      "origins_count": 3,
      "origins": ["http://localhost:30000", "http://127.0.0.1:30000"],
      "message": "CORS configured"
    }
  }
}
```

### POST /api/start
Server startup instructions endpoint.

**Response:**
```json
{
  "status": "info",
  "message": "Please start the backend manually: cd backend && source venv/bin/activate && python server.py",
  "instructions": {
    "step1": "Open terminal",
    "step2": "Navigate to backend directory",
    "step3": "Activate virtual environment: source venv/bin/activate",
    "step4": "Start server: python server.py"
  },
  "note": "Automatic process spawning is blocked by browser security restrictions",
  "environment_note": "Current environment: development",
  "validation_status": "Universal input validation is active",
  "cors_note": "CORS configured for 3 origins"
}
```

## Integration with Foundry

1. **Configure Foundry Module:**
   - Go to Game Settings → Module Settings → The Gold Box Configuration
   - Set Backend URL to `http://localhost:5000` (or the port where your backend is running)
   - Click "Test Connection" to verify the backend is accessible
   - **Note**: No API key configuration is required in the frontend - API keys are managed server-side

2. **Current Functionality:**
   - The backend operates as a **validation and echo server**
   - AI prompts are sanitized, validated, and echoed back unchanged
   - All input validation and security features are active
   - Rate limiting and session management are enforced

3. **Use the Module:**
   - Click the "Take AI Turn" button in chat
   - The prompt will be sent to this backend for validation
   - The validated prompt will be returned (currently echoed back unchanged)
   - Future versions will include actual AI processing capabilities

4. **Backend Status Monitoring:**
   - Use `GET /api/health` to check if the backend is running
   - Use `GET /api/security` to verify all security features are active
   - Monitor `goldbox.log` for detailed request/response information

## Logging

- Logs are written to `goldbox.log` in the backend directory
- Console output shows real-time activity
- Logs include timestamps, client IPs, and request sizes
