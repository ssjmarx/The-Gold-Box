# The Gold Box Backend

A sophisticated Python backend server for The Gold Box Foundry VTT module, providing AI-powered TTRPG assistance with enterprise-grade security and validation.

## Version 0.2.3

### 🚀 Core Features

#### AI Service Integration
- **OpenAI Compatible API** - Full support for OpenAI and compatible services
- **NovelAI API** - Specialized integration for NovelAI services
- **OpenCode Compatible API** - Support for coding-focused AI services
- **Local LLM Support** - Integration with local language models

#### API Endpoints
- **POST `/api/process`** - Process AI prompts with enhanced validation
- **POST `/api/simple_chat`** - Simplified chat interface for OpenCode services
- **GET `/api/health`** - Health check and system status
- **GET `/api/info`** - Detailed service information
- **GET `/api/security`** - Security verification and integrity checks
- **POST `/api/start`** - Server startup instructions
- **POST `/api/admin`** - Password-protected admin operations

#### Enhanced Features (v0.2.3)
- **Message Context Processing** - Full chat history context support
- **Enhanced Debugging** - Improved API response logging and debugging
- **Better Error Handling** - Comprehensive error management and user feedback
- **Fixed JavaScript Integration** - Resolved frontend syntax errors
- **Advanced Key Management** - Encrypted API key storage with admin password protection

#### Security Features
- **Universal Input Validation** - Comprehensive validation with type-specific checking
- **Session Management** - Configurable timeouts with warnings (30-min default)
- **Rate Limiting** - IP-based rate limiting (5 requests/minute default)
- **Enhanced Security Headers** - XSS, CSRF, and injection protection
- **CORS Protection** - Environment-based configuration
- **File Integrity Verification** - SHA256 hash checking
- **Virtual Environment Verification** - Ensures proper isolation
- **Permission Verification** - Automated security checks

## Quick Start

### 1. Install Dependencies

```bash
# Navigate to backend directory
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
- Default to **production mode** with FastAPI
- Start on the first available port from 5000 upwards
- Automatically trigger key management setup on first run
- Enable comprehensive security features

**Development Mode:**
```bash
# Force development mode
FLASK_ENV=development python server.py
```

### 3. Test the Backend

```bash
# Health check
curl http://localhost:5000/api/health

# Service info
curl http://localhost:5000/api/info

# Test simple chat
curl -X POST http://localhost:5000/api/simple_chat \
  -H "Content-Type: application/json" \
  -d '{"service_key": "z_ai", "prompt": "Hello, AI!"}'
```

## Configuration

### Environment Variables

- `FLASK_DEBUG`: Development mode (`True`/`False`, default: `False`)
- `FLASK_ENV`: Environment (`development`/`production`, default: `production`)
- `GOLD_BOX_PORT`: Server port (default: 5000)
- `RATE_LIMIT_MAX_REQUESTS`: Max requests per window (default: 5)
- `RATE_LIMIT_WINDOW_SECONDS`: Time window in seconds (default: 60)
- `SESSION_TIMEOUT_MINUTES`: Session timeout (default: 30)
- `SESSION_WARNING_MINUTES`: Warning before timeout (default: 5)
- `CORS_ORIGINS`: Comma-separated origins (production only)
- `LOG_LEVEL`: Logging level (default: `INFO`)
- `LOG_FILE`: Log file path (default: `goldbox.log`)
- `GOLD_BOX_OPENAI_COMPATIBLE_API_KEY`: OpenAI-compatible API key
- `GOLD_BOX_NOVELAI_API_API_KEY`: NovelAI API key

### Key Management

The backend includes advanced key management with encryption:

```bash
# First-time setup - interactive wizard
python server.py

# Key change mode
GOLD_BOX_KEYCHANGE=true python server.py
```

Features:
- **Encrypted Storage** - AES-256 encryption for API keys
- **Admin Password Protection** - Secure admin operations
- **Multiple Service Support** - OpenAI, NovelAI, OpenCode, Local
- **Environment Variable Loading** - Secure key injection
- **Validation & Sanitization** - Input validation with security checks

## API Endpoints

### GET /api/health
Health check endpoint with comprehensive system status.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2024-01-01T12:00:00",
  "version": "0.2.3",
  "service": "The Gold Box Backend",
  "api_key_required": true,
  "environment": "production",
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

### POST /api/simple_chat
Enhanced chat endpoint for OpenCode-compatible services with message context support.

**Request:**
```json
{
  "service_key": "z_ai",
  "prompt": "Your AI prompt here",
  "message_context": [
    {"sender": "User", "content": "Hello"},
    {"sender": "AI", "content": "Hi there!"}
  ],
  "temperature": 0.1,
  "max_tokens": null
}
```

**Response:**
```json
{
  "status": "success",
  "response": "AI response here",
  "timestamp": "2024-01-01T12:00:00",
  "service_used": "z_ai",
  "metadata": {},
  "message": "OpenCode API response received successfully"
}
```

### POST /api/admin
Password-protected admin endpoint for server management.

**Request:**
```json
{
  "command": "status",
  "settings": {
    "maximum message context": 15,
    "ai role": "dm",
    "general llm": "opencode_compatible"
  }
}
```

**Headers:**
- `X-Admin-Password`: Admin password for authentication

**Response:**
```json
{
  "service": "The Gold Box Backend",
  "version": "0.2.3",
  "status": "running",
  "features": [
    "OpenAI Compatible API support",
    "NovelAI API support",
    "OpenCode Compatible API support",
    "Local LLM support",
    "Simple chat endpoint",
    "Admin settings management",
    "Health check endpoint",
    "Auto-start instructions",
    "Advanced key management",
    "Enhanced message context processing",
    "Fixed JavaScript syntax errors",
    "Improved API debugging",
    "Better error handling and logging"
  ],
  "endpoints": {
    "health": "/api/health",
    "process": "/api/process",
    "admin": "/api/admin",
    "simple_chat": "/api/simple_chat",
    "start": "/api/start"
  }
}
```

## Integration with Foundry VTT

### 1. Module Configuration
- Go to **Game Settings → Module Settings → The Gold Box**
- Set **Backend URL** to `http://localhost:5000` (or your server port)
- Configure **Backend Password** for admin operations
- Select preferred **LLM Service** (OpenAI, NovelAI, OpenCode, Local)

### 2. Using Message Context
The module now supports full chat context:

1. **Automatic Context Collection** - Recent chat messages are automatically collected
2. **Configurable Context Length** - Set maximum messages to include (default: 15)
3. **Chronological Ordering** - Messages are sent in proper time order
4. **HTML Preservation** - Dice rolls and formatting are maintained

### 3. AI Role Selection
Choose the AI's role in your game:
- **Dungeon Master** - Full GM control and narrative
- **DM Assistant** - Supporting role for human GM
- **Player** - Player character interaction

## Security & Validation

### Universal Input Validator
Comprehensive validation system with:

- **Type-Specific Validation** - Different rules for different input types
- **Security Pattern Detection** - XSS, SQL injection, command injection
- **Structured Data Support** - Validates JSON objects and arrays
- **AI Parameter Validation** - Temperature, tokens, and other AI parameters
- **Size Limits** - Configurable limits per input type
- **Character Pattern Validation** - Allowed characters per input type

### Session Management
- **30-minute timeout** with automatic cleanup
- **5-minute warnings** before session expiry
- **Activity tracking** with last seen timestamps
- **Grace period** for session recovery

### Rate Limiting
- **IP-based tracking** with configurable limits
- **Sliding window** implementation
- **Graceful degradation** with proper headers
- **Automatic cleanup** of old request data

## Logging & Monitoring

### Log Files
- **goldbox.log** - Main application log
- **Structured logging** with timestamps and client IPs
- **Security events** - Authentication failures, validation errors
- **Performance metrics** - Request timing and response sizes

### Debug Features (v0.2.3)
- **Enhanced content logging** for API responses
- **Context preservation verification**
- **Error tracking with detailed stack traces**
- **Frontend integration debugging**

## Troubleshooting

### Common Issues

1. **Port Already in Use**
   - Server automatically finds next available port
   - Check console for actual port used

2. **API Key Issues**
   - Run key management wizard: `python server.py`
   - Verify keys are properly encrypted

3. **CORS Problems**
   - Check `CORS_ORIGINS` environment variable
   - Verify Foundry URL is in allowed origins

4. **JavaScript Errors**
   - Check browser console for error messages
   - Verify module is properly installed in Foundry

### Debug Mode
Enable detailed logging:
```bash
LOG_LEVEL=DEBUG python server.py
```

## Dependencies

### Core Dependencies
- **FastAPI** - Modern Python web framework (MIT License)
- **Uvicorn** - ASGI server (BSD 3-Clause License)
- **python-dotenv** - Environment variable management (BSD 3-Clause License)
- **cryptography** - Encryption and security (Apache 2.0 License)
- **pydantic** - Data validation (MIT License)

### Development Dependencies
- **pytest** - Testing framework
- **black** - Code formatting
- **mypy** - Type checking

## License

The Gold Box Backend is licensed under **CC-BY-NC-SA 4.0**.

All dependencies maintain compatible open-source licenses for commercial use restrictions.

## Support

For issues and feature requests:
- **GitHub Issues**: [Repository Issues](https://github.com/ssjmarx/Gold-Box/issues)
- **Documentation**: [Main README](../README.md)
- **Changelog**: [CHANGELOG.md](../CHANGELOG.md)

---

**Version 0.2.3** - Enhanced message context, improved debugging, and fixed JavaScript integration
