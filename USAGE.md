# The Gold Box - Usage Guide

This document describes all environmental variables and configuration options available when starting The Gold Box backend server.

## Quick Start

```bash
# Navigate to backend directory
cd backend

# Start with default settings
python server.py

# Or start with custom configuration
GOLD_BOX_PORT=8080 FLASK_ENV=development python server.py
```

## Server Configuration

### Port and Environment

| Variable | Default | Description | Example |
|-----------|----------|-------------|----------|
| `GOLD_BOX_PORT` | `5000` | Server port number | `GOLD_BOX_PORT=8080` |
| `FLASK_ENV` | `production` | Environment mode (`development`/`production`) | `FLASK_ENV=development` |
| `FLASK_DEBUG` | `False` | Enable debug mode (`true`/`false`) | `FLASK_DEBUG=true` |
| `USE_DEVELOPMENT_SERVER` | `false` | Force development mode via environment | `USE_DEVELOPMENT_SERVER=true` |

### Environment Modes

**Development Mode (`FLASK_ENV=development` or `USE_DEVELOPMENT_SERVER=true`)**:
- CORS automatically configured for localhost Foundry VTT ports
- Debug endpoints enabled (`/docs`, `/redoc`)
- Verbose logging enabled
- Auto-reload on code changes

**Production Mode (`FLASK_ENV=production`)**:
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

## Logging Configuration

### Log Settings

| Variable | Default | Description | Example |
|-----------|----------|-------------|----------|
| `LOG_LEVEL` | `INFO` | Logging level (`DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`) | `LOG_LEVEL=DEBUG` |
| `LOG_FILE` | `goldbox.log` | Log file path | `LOG_FILE=/var/log/goldbox.log` |

### Log Levels Explained

- **`DEBUG`**: All events including detailed request/response data
- **`INFO`**: General server information and important events
- **`WARNING`**: Potential issues and non-critical errors
- **`ERROR`**: Errors that don't stop the server
- **`CRITICAL`**: Critical errors that may cause server shutdown

## Security Configuration

### Rate Limiting

| Variable | Default | Description | Example |
|-----------|----------|-------------|----------|
| `RATE_LIMIT_MAX_REQUESTS` | `5` | Maximum requests per time window | `RATE_LIMIT_MAX_REQUESTS=10` |
| `RATE_LIMIT_WINDOW_SECONDS` | `60` | Time window in seconds | `RATE_LIMIT_WINDOW_SECONDS=30` |

### Session Management

| Variable | Default | Description | Example |
|-----------|----------|-------------|----------|
| `SESSION_TIMEOUT_MINUTES` | `60` | Session timeout in minutes | `SESSION_TIMEOUT_MINUTES=120` |
| `SESSION_WARNING_MINUTES` | `10` | Warning before timeout (minutes) | `SESSION_WARNING_MINUTES=15` |

## API Keys Configuration

### OpenAI Compatible Services

| Variable | Description | Example |
|-----------|-------------|----------|
| `GOLD_BOX_OPENAI_COMPATIBLE_API_KEY` | OpenAI or compatible API key | `GOLD_BOX_OPENAI_COMPATIBLE_API_KEY=sk-...` |

**Compatible Services**:
- OpenAI (GPT-3.5, GPT-4, GPT-4o)
- Azure OpenAI
- Google AI (Gemini)
- Anthropic Claude
- Groq
- Together AI
- Any OpenAI-compatible API service

### OpenCode Compatible Services

| Variable | Description | Example |
|-----------|-------------|----------|
| `GOLD_BOX_OPENCODE_COMPATIBLE_API_KEY` | OpenCode or compatible API key | `GOLD_BOX_OPENCODE_COMPATIBLE_API_KEY=...` |

**Compatible Services**:
- Z.AI (GLM-4.6)
- Other coding-focused AI services
- Local model servers with OpenAI-compatible endpoints

### Dynamic API Key Loading

The Gold Box supports dynamic API key loading for any provider:

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

## AI Service Configuration

### Available Services

The Gold Box supports 70+ AI providers through LiteLLM integration:

**Major Cloud Providers**:
- OpenAI (GPT-4, GPT-4o, GPT-3.5-turbo)
- Anthropic Claude (Claude-3-haiku, Claude-3-sonnet, Claude-3-opus)
- Google AI (Gemini 1.5 Pro, Gemini 1.5 Flash)
- Azure OpenAI
- Cohere

**Fast Inference Providers**:
- Groq (ultra-fast LLaMA inference)
- Together AI (open source models)
- Replicate (serverless deployment)
- Fireworks AI (affordable inference)
- xAI (Grok models)

**Enterprise Platforms**:
- AWS Bedrock (Claude, Titan models)
- Google Vertex AI
- Mistral AI
- Perplexity AI

**Specialized Services**:
- OpenRouter (model routing)
- Local LLM servers
- Custom provider endpoints
- Z.AI (GLM-4.6 and coding models)

### Service Selection

Configure your preferred service in Foundry VTT module settings:
1. Go to **Game Settings → Module Settings → The Gold Box**
2. Set **Backend URL** to `http://localhost:5000`
3. Select **General LLM Provider** from 70+ available options
4. Configure **General LLM Model** for the selected provider
5. Set **General LLM Base URL** for custom endpoints (if needed)
6. Configure **General LLM Version**, **Timeout**, **Max Retries**, and **Custom Headers** as needed

## Advanced Configuration

### Production Deployment

```bash
# Production configuration example
export FLASK_ENV=production
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
export FLASK_ENV=development
export FLASK_DEBUG=true
export GOLD_BOX_PORT=5000
export LOG_LEVEL=DEBUG
export GOLD_BOX_OPENAI_COMPATIBLE_API_KEY=your-dev-key

python server.py
```

### Backend Script Configuration

```bash
# Using backend.sh script with environment variables
export FLASK_ENV=development
export GOLD_BOX_PORT=5000
export LOG_LEVEL=DEBUG

# Run the setup script
./backend.sh

# Force development mode via script
./backend.sh --dev

# Force development mode via environment
USE_DEVELOPMENT_SERVER=true ./backend.sh
```

### Docker Configuration

```dockerfile
# Dockerfile example
FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

# Production configuration
ENV FLASK_ENV=production
ENV GOLD_BOX_PORT=8080
ENV LOG_LEVEL=INFO
ENV CORS_ORIGINS=https://your-foundry-domain.com

EXPOSE 8080
CMD ["python", "server.py"]
```

```yaml
# docker-compose.yml example
version: '3.8'
services:
  gold-box-backend:
    build: .
    ports:
      - "8080:8080"
    environment:
      - FLASK_ENV=production
      - GOLD_BOX_PORT=8080
      - LOG_LEVEL=INFO
      - CORS_ORIGINS=https://foundry.example.com
      - GOLD_BOX_OPENAI_COMPATIBLE_API_KEY=${OPENAI_API_KEY}
    volumes:
      - ./goldbox.log:/app/goldbox.log
```

## Environment File

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

## Security Configuration File

The `backend/security_config.ini` file provides endpoint-specific security settings:

### Security Sections

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

[endpoint:/api/simple_chat]
rate_limit_requests = 10
rate_limit_window = 60
input_validation = strict
session_required = True
security_headers = True

[endpoint:/api/admin]
rate_limit_requests = 10
rate_limit_window = 60
input_validation = strict
session_required = True
security_headers = True
```

### Security Options

- **`enabled`**: Global security switch
- **`audit_logging`**: Enable security event logging
- **`rate_limit_requests`**: Max requests per endpoint
- **`rate_limit_window`**: Time window for rate limiting
- **`input_validation`**: `none`, `basic`, or `strict` validation
- **`session_required`**: Require authenticated session
- **`security_headers`**: Enable security HTTP headers

## Troubleshooting

### Common Issues

1. **Port Already in Use**
   ```bash
   # Server automatically finds next available port
   # Check console for actual port used
   ```

2. **CORS Issues in Production**
   ```bash
   # Must explicitly set CORS origins
   export CORS_ORIGINS=https://your-foundry-domain.com
   ```

3. **API Key Problems**
   ```bash
   # Force key management wizard
   GOLD_BOX_KEYCHANGE=true python server.py
   
   # Check environment variables
   python server.py --check-keys
   ```

4. **Rate Limiting Too Strict**
   ```bash
   # Increase rate limits
   export RATE_LIMIT_MAX_REQUESTS=20
   export RATE_LIMIT_WINDOW_SECONDS=30
   ```

5. **Development Mode Issues**
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

1. **Explicit CORS Configuration**
   ```bash
   export CORS_ORIGINS=https://your-domain.com,https://backup-domain.com
   ```

2. **Strong Admin Password**
   - Use minimum 12 characters
   - Include numbers, symbols, and mixed case
   - Store securely (password manager)

3. **API Key Protection**
   - Use environment variables, not hardcoded keys
   - Rotate keys regularly
   - Monitor usage for unusual activity

4. **Session Management**
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

## Integration Examples

### Foundry VTT Integration

1. **Module Settings Configuration**:
   - Backend URL: `http://localhost:5000`
   - Backend Password: Your admin password
   - AI Role: DM, DM Assistant, or Player
   - LLM Service: Choose from 70+ providers

2. **Message Context Configuration**:
   - Maximum Message Context: 15 (default)
   - Context Collection: Automatic
   - HTML Preservation: Enabled

3. **Service-Specific Settings**:
   - Model selection per service
   - Temperature and token limits
   - Custom endpoint configuration

### Multiple Environments

```bash
# Development
export FLASK_ENV=development
export GOLD_BOX_PORT=5000

# Staging
export FLASK_ENV=production
export GOLD_BOX_PORT=5001
export CORS_ORIGINS=https://staging.foundry.example.com

# Production
export FLASK_ENV=production
export GOLD_BOX_PORT=80
export CORS_ORIGINS=https://foundry.example.com
```

## Advanced Usage Patterns

### Custom Provider Integration

```bash
# Add support for custom provider
export CUSTOM_PROVIDER_API_KEY=your-custom-key
export CUSTOM_PROVIDER_BASE_URL=https://api.custom.com/v1
export CUSTOM_PROVIDER_MODEL=custom-model-name

# Server will automatically detect and configure
python server.py
```

### Load Balancing Configuration

```bash
# Multiple instances for load balancing
export GOLD_BOX_PORT=5000  # Instance 1
export GOLD_BOX_PORT=5001  # Instance 2
export GOLD_BOX_PORT=5002  # Instance 3

# Configure reverse proxy (nginx, etc.) to distribute load
```

### Backup and Recovery

```bash
# Backup encrypted keys
cp backend/server_files/keys.enc backup/keys-$(date +%Y%m%d).enc

# Recovery with new password
GOLD_BOX_KEYCHANGE=true python server.py
# Follow prompts to restore from backup
```

## Support

For configuration help:
- **Documentation**: [Backend README](backend/README.md)
- **Testing Guide**: [Testing Guide](backend/TESTING.md)
- **Main Project**: [The Gold Box README](README.md)
- **Issues**: [GitHub Issues](https://github.com/ssjmarx/The-Gold-Box/issues)

---

**Last Updated**: Version 0.3.1 - REST API integration, enhanced processing modes, and critical bug fixes

---

## Processing Mode Configuration

The Gold Box supports four distinct chat processing modes, configurable in Foundry module settings:

### Available Modes

1. **Simple Mode** (`/api/simple_chat`) - *Deprecated*
   - Direct HTML-based message collection from Foundry chat
   - Minimal processing overhead
   - Compatible with all Foundry versions

2. **Processed Mode** (`/api/process_chat`) - *Deprecated*
   - Enhanced HTML processing with structured data extraction
   - Token-efficient compact JSON format
   - Better context preservation for AI

3. **API Mode** (`/api/api_chat`) - *Recommended*
   - REST API-based message collection via Foundry Gold API module
   - Most reliable and maintainable approach
   - Foundation for advanced Foundry integration features

4. **Context Mode** (`/api/context_chat`) - *Experimental/Unfinished*
   - Full board state integration including tokens, walls, lighting, and map notes
   - Complete scene context for AI processing
   - Currently in development - not fully implemented

### Mode Selection

Configure processing mode in Foundry VTT:
1. Go to **Game Settings → Module Settings → The Gold Box**
2. Set **Chat Processing Mode** to your preferred option
3. **Recommended**: Use "API (recommended)" for most reliable operation
4. **Experimental**: Use "Context (unfinished)" for testing (may have issues)

### Recent Changes (v0.3.1)

- **Fixed Module Name Issue**: Resolved "Unmapped" settings problem by standardizing namespace to `the-gold-box`
- **Updated Mode Labels**: Added status indicators (deprecated, recommended, unfinished) for clarity
- **Enhanced Settings Storage**: Fixed frontend settings not being properly saved/retrieved
- **Version Bump**: Updated to version 0.3.1 for patch release
