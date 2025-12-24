# The Gold Box - Advanced Usage Guide

This document describes all environmental variables and configuration options available when starting The Gold Box backend server, along with detailed frontend settings reference.

## Environment Variables

### Server Configuration

| Variable | Default | Description | Example |
|-----------|----------|-------------|----------|
| `GOLD_BOX_PORT` | `5000` | Server port number | `GOLD_BOX_PORT=8080` |
| `USE_DEVELOPMENT_SERVER` | `false` | Force development mode via environment | `USE_DEVELOPMENT_SERVER=true` |

### Environment Modes

**Development Mode (`USE_DEVELOPMENT_SERVER=true`)**:
- CORS automatically configured for localhost Foundry VTT ports
- Debug endpoints enabled (`/docs`, `/redoc`)
- Verbose logging enabled
- Auto-reload on code changes

**Production Mode (default)**:
- CORS must be explicitly configured via `CORS_ORIGINS`
- Debug endpoints disabled
- Optimized logging
- Enhanced security headers

### CORS Configuration

| Variable | Default | Description | Example |
|-----------|----------|-------------|----------|
| `CORS_ORIGINS` | *required in production* | Comma-separated allowed origins | `CORS_ORIGINS=https://foundry.example.com,https://game.foundryvtt.com` |

**Development Origins** (automatically configured):
- `http://localhost:30000`
- `http://127.0.0.1:30000`
- `http://localhost:30001`
- `http://127.0.0.1:30001`
- `http://localhost:30002`
- `http://127.0.0.1:30002`

### Logging Configuration

| Variable | Default | Description | Example |
|-----------|----------|-------------|----------|
| `LOG_LEVEL` | `INFO` | Logging level (`DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`) | `LOG_LEVEL=DEBUG` |
| `LOG_FILE` | `goldbox.log` | Log file path | `LOG_FILE=/var/log/goldbox.log` |

**Log Levels Explained**:
- **`DEBUG`**: All events including detailed request/response data
- **`INFO`**: General server information and important events
- **`WARNING`**: Potential issues and non-critical errors
- **`ERROR`**: Errors that don't stop the server
- **`CRITICAL`**: Critical errors that may cause server shutdown

### Security Configuration

| Variable | Default | Description | Example |
|-----------|----------|-------------|----------|
| `RATE_LIMIT_MAX_REQUESTS` | `5` | Maximum requests per time window | `RATE_LIMIT_MAX_REQUESTS=10` |
| `RATE_LIMIT_WINDOW_SECONDS` | `60` | Time window in seconds | `RATE_LIMIT_WINDOW_SECONDS=30` |
| `SESSION_TIMEOUT_MINUTES` | `60` | Session timeout in minutes | `SESSION_TIMEOUT_MINUTES=120` |
| `SESSION_WARNING_MINUTES` | `10` | Warning before timeout (minutes) | `SESSION_WARNING_MINUTES=15` |

### API Keys Configuration

The Gold Box supports multiple methods for API key configuration:

| Variable Pattern | Description | Example |
|----------------|-------------|----------|
| `{PROVIDER}_API_KEY` | Generic API key pattern | `ANTHROPIC_API_KEY=sk-ant-...` |
| `{provider}_API_KEY` | Lowercase variant | `anthropic_api_key=sk-ant-...` |

**Supported Provider Variables**:
- `OPENAI_API_KEY` - OpenAI services
- `ANTHROPIC_API_KEY` - Anthropic Claude
- `GOOGLE_API_KEY` - Google Gemini
- `GROQ_API_KEY` - Groq
- `TOGETHER_AI_API_KEY` - Together AI
- `REPLICATE_API_TOKEN` - Replicate
- `FIREWORKS_AI_API_KEY` - Fireworks AI
- `XAI_API_KEY` - xAI (Grok)
- `COHERE_API_KEY` - Cohere
- `MISTRAL_API_KEY` - Mistral AI

## Frontend Settings Reference

The Gold Box module provides configurable settings through the Foundry VTT interface. Access these via **Game Settings → Module Settings → The Gold Box**.

### Connection Settings

| Setting | Description | Default |
|---------|-------------|---------|
| **Backend URL** | URL of the Python backend server | `http://localhost:5000` |
| **Backend Password** | Admin password for backend operations (from server startup) | `""` |

### AI Configuration

| Setting | Description | Default |
|---------|-------------|---------|
| **AI Role** | Role AI should play in your game (`dm`, `dm_assistant`, `player`) | `dm` |
| **General LLM Provider** | LiteLLM provider name (e.g., `openai`, `anthropic`, `glm`) | `""` |
| **General LLM Model** | Model name for the provider (e.g., `gpt-3.5-turbo`, `claude-3-5-sonnet-20241022`) | `""` |
| **General LLM Base URL** | Custom base URL for provider endpoints (optional) | `""` |
| **General LLM API Version** | API version for the provider | `v1` |
| **General LLM Timeout** | Request timeout in seconds | `30` |
| **General LLM Max Retries** | Maximum retry attempts for failed requests | `3` |
| **General LLM Custom Headers** | Custom headers in JSON format (advanced) | `""` |

### Tactical AI Configuration

| Setting | Description | Default |
|---------|-------------|---------|
| **Tactical LLM Provider** | Provider for combat-specific AI (placeholder) | `""` |
| **Tactical LLM Model** | Model for combat scenarios (placeholder) | `""` |
| **Tactical LLM Base URL** | Custom base URL for tactical AI (placeholder) | `""` |
| **Tactical LLM API Version** | API version for tactical AI | `v1` |
| **Tactical LLM Timeout** | Request timeout in seconds | `30` |
| **Tactical LLM Max Retries** | Maximum retry attempts | `3` |
| **Tactical LLM Custom Headers** | Custom headers in JSON format | `""` |

### Context Configuration

| Setting | Description | Default |
|---------|-------------|---------|
| **Maximum Message Context** | Number of recent chat messages to include in AI context | `15` |
| **AI Response Timeout** | Maximum time to wait for AI response before re-enabling button (seconds) | `60` |

## Key Management

### Interactive Key Setup

| Variable | Default | Description | Example |
|-----------|----------|-------------|----------|
| `GOLD_BOX_KEYCHANGE` | `false` | Force key management wizard | `GOLD_BOX_KEYCHANGE=true` |

**Key Management Features**:
- **Encrypted Storage**: AES-256 encryption for all API keys
- **Admin Password Protection**: Single password for encryption and admin operations
- **Multiple Service Support**: Configure keys for multiple AI services
- **Environment Variable Loading**: Secure key injection from environment
- **Dynamic Provider Support**: Add new providers without code changes

### Setup Commands

```bash
# First-time setup with interactive wizard
python server.py

# Force key change mode
GOLD_BOX_KEYCHANGE=true python server.py

# Start with existing keys
python server.py  # Will prompt for encryption password

# Start with environment variables
export OPENAI_API_KEY=sk-your-key
export ANTHROPIC_API_KEY=sk-ant-your-key
python server.py
```

### Key Management Interface

The interactive key management wizard provides:
- **Add New Keys**: Securely add API keys for any supported provider
- **Update Existing Keys**: Change encrypted stored keys
- **Delete Keys**: Remove unused provider keys
- **Test Connections**: Verify API key validity
- **Import from Environment**: Load keys from environment variables
- **Export to Environment**: Export keys to environment variables

## Custom Provider Wizard

The Gold Box supports creating custom AI providers that follow OpenAI-compatible API format.

### Creating a Custom Provider

1. **Start Backend Server**: Run `python server.py` or use the key management wizard with `GOLD_BOX_KEYCHANGE=true`

2. **Select Key Management**: Choose the key management menu option

3. **Add Custom Provider**: Select "Add Custom Provider" from the menu

4. **Enter Provider Name**: Choose a unique identifier (e.g., `my-provider`, `local-llm`)

5. **Enter Base URL**: Provide the API base URL (e.g., `https://api.example.com/v1`)

6. **Enter Model Name**: Specify the default model name (e.g., `my-model-name`)

7. **Enter API Key**: Provide your API key for the custom provider

8. **Test Connection**: The wizard will test the connection to verify configuration

9. **Save Configuration**: Confirm to save your custom provider settings

### Custom Provider Description

The custom provider wizard creates a new AI provider configuration that follows OpenAI-compatible API standards. Once created, your custom provider will appear in Foundry VTT module settings under "General LLM Provider" and can be used just like any built-in provider.

**Supported Features for Custom Providers**:
- OpenAI-compatible chat completion endpoints
- Standard request/response format
- API key authentication
- Custom base URL support
- Model selection

### Example Custom Provider Configuration

```bash
# Example: Setting up a local LLM server
Provider Name: local-llm
Base URL: http://localhost:11434/v1
Model Name: llama-3.2-3b-instruct
API Key: sk-local-key-12345
```

After configuration, select `local-llm` as your "General LLM Provider" in Foundry module settings.

## Memory Configuration

The Gold Box provides full conversation history support with intelligent token management, allowing the AI to remember complete conversation threads while staying within token limits.

### Memory Settings

Memory settings are configured in the `memorySettings` object:

```javascript
{
  "memorySettings": {
    "maxHistoryTokens": 5000,      // Maximum tokens for conversation history
    "maxHistoryMessages": 50,        // Maximum number of messages to keep
    "maxHistoryHours": 24            // Maximum age of messages (hours)
  }
}
```

**Note**: As of v0.3.6, memory settings are not exposed in the Foundry module settings UI and must be configured via backend API or direct modification.

### Memory Settings Options

| Setting | Default | Description | Range |
|---------|----------|-------------|--------|
| `maxHistoryTokens` | `5000` | Maximum tokens for conversation history | 100-100000 |
| `maxHistoryMessages` | `50` | Maximum number of messages to store | 1-1000 |
| `maxHistoryHours` | `24` | Maximum age of messages in hours | 1-168 (1 week) |

### Memory Management Features

**Token-Based Pruning**: Automatically removes oldest messages when token limit exceeded, preserving system messages.

**Time-Based Expiration**: Messages older than specified time limit are automatically removed during retrieval.

**Message Count Limits**: When message count exceeds limit, oldest messages are removed first.

### Memory Configuration Examples

**Default Configuration**:
```javascript
{
  "memorySettings": {
    "maxHistoryTokens": 5000,
    "maxHistoryMessages": 50,
    "maxHistoryHours": 24
  }
}
```

**Large Memory for Long Conversations**:
```javascript
{
  "memorySettings": {
    "maxHistoryTokens": 20000,      // 20k tokens for complex scenarios
    "maxHistoryMessages": 200,       // Keep up to 200 messages
    "maxHistoryHours": 72           // Remember up to 3 days
  }
}
```

**Small Memory for Quick Sessions**:
```javascript
{
  "memorySettings": {
    "maxHistoryTokens": 1000,       // 1k tokens for brief sessions
    "maxHistoryMessages": 20,        // Keep last 20 messages
    "maxHistoryHours": 12           // Remember last 12 hours
  }
}
```

**No Conversation History (Delta Only)**:
```javascript
{
  "memorySettings": {
    "maxHistoryTokens": 0,          // Disable history
    "maxHistoryMessages": 0,
    "maxHistoryHours": 0
  }
}
```

## Advanced Configuration

### Production Deployment

```bash
# Production configuration example
export GOLD_BOX_PORT=8080
export CORS_ORIGINS=https://your-foundry-domain.com
export LOG_LEVEL=WARNING
export RATE_LIMIT_MAX_REQUESTS=20
export RATE_LIMIT_WINDOW_SECONDS=60
export SESSION_TIMEOUT_MINUTES=120
export GOLD_BOX_OPENAI_COMPATIBLE_API_KEY=your-production-key

python server.py
```

### Development Configuration

```bash
# Development configuration example
export USE_DEVELOPMENT_SERVER=true
export GOLD_BOX_PORT=5000
export LOG_LEVEL=DEBUG
export GOLD_BOX_OPENAI_COMPATIBLE_API_KEY=your-dev-key

python server.py
```

### Backend Script Configuration

```bash
# Using backend.sh script with environment variables
export USE_DEVELOPMENT_SERVER=true
export GOLD_BOX_PORT=5000
export LOG_LEVEL=DEBUG

# Run setup script
./backend.sh

# Force development mode via script
./backend.sh --dev

# Force development mode via environment
USE_DEVELOPMENT_SERVER=true ./backend.sh
```

### Docker Configuration

**Dockerfile**:
```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

# Production configuration
ENV GOLD_BOX_PORT=8080
ENV LOG_LEVEL=INFO
ENV CORS_ORIGINS=https://your-foundry-domain.com

EXPOSE 8080
CMD ["python", "server.py"]
```

**docker-compose.yml**:
```yaml
version: '3.8'
services:
  gold-box-backend:
    build: .
    ports:
      - "8080:8080"
    environment:
      - GOLD_BOX_PORT=8080
      - LOG_LEVEL=INFO
      - CORS_ORIGINS=https://foundry.example.com
      - GOLD_BOX_OPENAI_COMPATIBLE_API_KEY=${OPENAI_API_KEY}
    volumes:
      - ./goldbox.log:/app/goldbox.log
```

### Environment File

Create a `.env` file for local development:

```bash
# .env file example
FLASK_ENV=development
FLASK_DEBUG=true
GOLD_BOX_PORT=5000
LOG_LEVEL=DEBUG
RATE_LIMIT_MAX_REQUESTS=10
SESSION_TIMEOUT_MINUTES=60
GOLD_BOX_OPENAI_COMPATIBLE_API_KEY=your-openai-key
GOLD_BOX_NOVELAI_API_API_KEY=your-novelai-key
GOLD_BOX_OPENCODE_COMPATIBLE_API_KEY=your-opencode-key
USE_DEVELOPMENT_SERVER=true
```

### Security Configuration File

The `backend/security_config.ini` file provides endpoint-specific security settings:

```ini
[global]
enabled = True
audit_logging = False

[endpoint:/api/process_chat]
rate_limit_requests = 10
rate_limit_window = 60
input_validation = basic
session_required = True
security_headers = True

[endpoint:/api/admin]
rate_limit_requests = 10
rate_limit_window = 60
input_validation = strict
session_required = True
security_headers = True
```

**Security Options**:
- **`enabled`**: Global security switch
- **`audit_logging`**: Enable security event logging
- **`rate_limit_requests`**: Max requests per endpoint
- **`rate_limit_window`**: Time window for rate limiting
- **`input_validation`**: `none`, `basic`, or `strict` validation
- **`session_required`**: Require authenticated session
- **`security_headers`**: Enable security HTTP headers

## Troubleshooting

### Common Issues

**Port Already in Use**:
```bash
# Server automatically finds next available port
# Check console for actual port used
```

**CORS Issues in Production**:
```bash
# Must explicitly set CORS origins
export CORS_ORIGINS=https://your-foundry-domain.com
```

**API Key Problems**:
```bash
# Force key management wizard
GOLD_BOX_KEYCHANGE=true python server.py

# Check environment variables
python server.py --check-keys
```

**Rate Limiting Too Strict**:
```bash
# Increase rate limits
export RATE_LIMIT_MAX_REQUESTS=20
export RATE_LIMIT_WINDOW_SECONDS=30
```

**Development Mode Issues**:
```bash
# Force development mode
export USE_DEVELOPMENT_SERVER=true
# or
./backend.sh --dev
```

### Debug Mode

Enable detailed debugging:
```bash
export LOG_LEVEL=DEBUG
export FLASK_DEBUG=true
python server.py
```

### Testing Configuration

Test your configuration:
```bash
# Health check
curl http://localhost:5000/api/health

# Service information
curl http://localhost:5000/api/info

# Security verification
curl http://localhost:5000/api/security

# Test with specific environment
GOLD_BOX_PORT=5001 python server.py
```

## Security Best Practices

### Production Security

1. **Explicit CORS Configuration**:
   ```bash
   export CORS_ORIGINS=https://your-domain.com,https://backup-domain.com
   ```

2. **Strong Admin Password**:
   - Use minimum 12 characters
   - Include numbers, symbols, and mixed case
   - Store securely (password manager)

3. **API Key Protection**:
   - Use environment variables, not hardcoded keys
   - Rotate keys regularly
   - Monitor usage for unusual activity

4. **Session Management**:
   ```bash
   export SESSION_TIMEOUT_MINUTES=60  # Reasonable timeout
   export SESSION_WARNING_MINUTES=10  # User warning
   ```

### Key Storage Security

The Gold Box uses encrypted storage with:
- **AES-256 encryption** for API keys
- **PBKDF2 key derivation** (100,000 iterations)
- **Secure file permissions** (0o600 for keys file)
- **Admin password protection** for key management

### Network Security

- **Rate limiting** prevents abuse
- **CORS restrictions** limit cross-origin requests
- **Input validation** blocks injection attacks
- **Session management** prevents session hijacking

## Performance Optimization

### High-Traffic Configuration

```bash
# Handle increased traffic
export RATE_LIMIT_MAX_REQUESTS=50
export RATE_LIMIT_WINDOW_SECONDS=60
export SESSION_TIMEOUT_MINUTES=15  # Shorter sessions
export LOG_LEVEL=WARNING  # Reduce logging overhead
```

### Resource Management

```bash
# Optimize for performance
export FLASK_ENV=production  # Disable debug overhead
export LOG_FILE=/dev/null  # No file logging (syslog instead)
export SESSION_TIMEOUT_MINUTES=30  # Regular cleanup
```

## Monitoring and Maintenance

### Log Analysis

```bash
# Monitor error rates
grep "ERROR" goldbox.log | wc -l

# Check rate limiting
grep "rate limit" goldbox.log

# Monitor API usage
grep "API call" goldbox.log

# Monitor session activity
grep "session" goldbox.log
```

### Health Monitoring

```bash
# Automated health check
#!/bin/bash
response=$(curl -s http://localhost:5000/api/health)
status=$(echo $response | jq -r '.status')

if [ "$status" != "healthy" ]; then
    echo "Alert: The Gold Box backend unhealthy"
    # Send notification, restart service, etc.
fi
```

## Support

For configuration help:
- **Documentation**: [Backend README](backend/README.md)
- **Main Project**: [The Gold Box README](README.md)
- **Dependencies**: [DEPENDENCIES.md](DEPENDENCIES.md)
- **Issues**: [GitHub Issues](https://github.com/ssjmarx/The-Gold-Box/issues)
