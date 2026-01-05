# The Gold Box - Advanced Usage Guide

This document describes all environmental variables and configuration options available when starting The Gold Box backend server, along with detailed frontend settings reference.

## Quick Reference

| Setting Type | Location | Example |
|--------------|----------|---------|
| Server Port | Env var or backend.sh | `GOLD_BOX_PORT=8080` |
| CORS Origins | Env var (production required) | `CORS_ORIGINS=https://foundry.example.com` |
| Backend URL | Foundry Module Settings | `http://localhost:5000` |
| AI Provider | Foundry Module Settings | `openai`, `anthropic`, `ollama` |
| AI Model | Foundry Module Settings | `gpt-4`, `claude-3-5-sonnet-20241022` |

## Environment Variables

### Server Configuration

| Variable | Default | Description |
|-----------|----------|-------------|
| `GOLD_BOX_PORT` | `5000` | Server port number |
| `USE_DEVELOPMENT_SERVER` | `false` | Force development mode (auto-configures CORS, enables debug) |

### CORS Configuration

| Variable | Default | Description |
|-----------|----------|-------------|
| `CORS_ORIGINS` | *required in production* | Comma-separated allowed origins |

**Development Origins** (automatically configured): `http://localhost:30000-30002`, `http://127.0.0.1:30000-30002`

### Logging Configuration

| Variable | Default | Description |
|-----------|----------|-------------|
| `LOG_LEVEL` | `INFO` | `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL` |
| `LOG_FILE` | `goldbox.log` | Log file path |

### Security Configuration

| Variable | Default | Description |
|-----------|----------|-------------|
| `RATE_LIMIT_MAX_REQUESTS` | `5` | Maximum requests per time window |
| `RATE_LIMIT_WINDOW_SECONDS` | `60` | Time window in seconds |
| `SESSION_TIMEOUT_MINUTES` | `60` | Session timeout in minutes |
| `SESSION_WARNING_MINUTES` | `10` | Warning before timeout (minutes) |

### API Keys Configuration

The Gold Box supports multiple methods for API key configuration:

**Generic Pattern**: `{PROVIDER}_API_KEY` or `{provider}_api_key`

**Supported Providers**: `OPENAI`, `ANTHROPIC`, `GOOGLE`, `GROQ`, `TOGETHER_AI`, `REPLICATE`, `FIREWORKS_AI`, `XAI`, `COHERE`, `MISTRAL`

## Frontend Settings Reference

Access via **Game Settings → Module Settings → The Gold Box**.

### Connection Settings

| Setting | Default | Description |
|---------|---------|-------------|
| **Backend URL** | `http://localhost:5000` | URL of Python backend server |
| **Backend Password** | `""` | Admin password for backend operations |

### Local AI Providers

The Gold Box supports local AI providers that don't require API keys.

**Supported Local Providers**:
- `ollama` (http://localhost:11434)
- `vllm` (http://localhost:8000/v1)
- `lm_studio` (http://localhost:1234/v1)
- `llamafile` (http://localhost:8080/v1)
- `xinference` (http://localhost:9997/v1)
- `lemonade` (custom URL)

| Setting | Description | Example |
|---------|-------------|----------|
| **General LLM Provider** | Local provider name | `ollama` |
| **General LLM Model** | Model name for local provider | `qwen3:14b` |
| **General LLM Base URL** | Local instance URL | `http://localhost:11434` |

#### Local Provider Setup

1. Start your local provider (Ollama, vLLM, etc.)
2. Configure in Foundry: Module Settings → The Gold Box → AI Configuration
3. Select local provider from "General LLM Provider" dropdown
4. Enter model name and base URL
5. No API key required

#### Model Naming Conventions

**Ollama**: `ollama/qwen3:14b` (with tag), `ollama/llama3.2:latest`
**vLLM**: `meta-llama/Llama-3.2-3B-Instruct` (no tag)
**LM Studio**: `llama-3.2-3b-instruct` (simple name)

**Note**: Some providers require prefix (`ollama/`), others don't. Try both if connection fails.

#### Dual Provider Configuration

Configure different providers for general and tactical AI:

```javascript
{
  "aiRole": "dm",
  "generalProvider": "ollama",
  "generalModel": "ollama/qwen3:14b",
  "generalBaseURL": "http://localhost:11434",
  "tacticalProvider": "openai",  // Future feature
  "tacticalModel": "gpt-4",
  "tacticalBaseURL": "https://api.openai.com/v1"
}
```

### AI Configuration

**⚠️ Model Compatibility Note**

The Gold Box is primarily designed for SOTA (State-of-the-Art) function-calling models.

**Recommended Models**:
- GLM-4.7 (excellent function calling)
- GPT-4/GPT-4o (strong support)
- Claude 3.5 Sonnet (good capabilities)
- Gemini 2.0 Pro (capable)

**Less Powerful Models**: May struggle with complex function calling. Consider disabling function calling for better performance.

| Setting | Default | Description |
|---------|---------|-------------|
| **AI Role** | `dm` | Role: `dm`, `dm_assistant`, `player` |
| **General LLM Provider** | `""` | LiteLLM provider name |
| **General LLM Model** | `""` | Model name |
| **General LLM Base URL** | `""` | Custom base URL (optional) |
| **General LLM API Version** | `v1` | API version |
| **General LLM Timeout** | `30` | Request timeout (seconds) |
| **General LLM Max Retries** | `3` | Maximum retry attempts |
| **General LLM Custom Headers** | `""` | Custom headers (JSON format) |

### Function Calling Mode

| Setting | Default | Description |
|---------|---------|-------------|
| **Disable Function Calling** | `false` | Enable legacy compatibility mode |

**Function Calling Enabled (`false`, default)**:
- AI uses structured tools: `get_message_history`, `post_message`, `roll_dice`, `get_encounter`, `create_encounter`, `delete_encounter`, `advance_combat_turn`, `get_actor_details`, `modify_token_attribute`
- Dynamically queries game state and performs actions
- **Best for**: SOTA models

**Function Calling Disabled (`true`)**:
- Legacy mode prepackages context into single prompt
- AI receives 15 recent messages and combat state upfront
- AI cannot query game state, manage combat, or modify attributes
- **Best for**: Older/local models or faster responses

**Performance Comparison**:

| Aspect | Function Calling | Legacy Mode |
|--------|-------------------|--------------|
| Response Time | Slower (tool loop) | 30-50% faster |
| API Calls | Multiple per turn | Single per turn |
| Capabilities | Full tool access | Chat + dice only |
| Model Requirements | SOTA models needed | Any model |

### Tactical AI Configuration (Future Feature)

Placeholder for future releases. Currently, all AI responses use General LLM Provider and Model settings.

### Context Configuration

| Setting | Default | Description |
|---------|---------|-------------|
| **Maximum Message Context** | `15` | Recent chat messages in AI context |
| **AI Response Timeout** | `60` | Max time to wait for AI response (seconds) |

## Key Management

### Interactive Key Setup

| Variable | Default | Description |
|-----------|----------|-------------|
| `GOLD_BOX_KEYCHANGE` | `false` | Force key management wizard |

**Key Management Features**:
- AES-256 encryption for all API keys
- Admin password protection
- Multiple service support
- Environment variable loading
- Dynamic provider support

### Setup Commands

```bash
# First-time setup
python server.py

# Force key change
GOLD_BOX_KEYCHANGE=true python server.py

# With environment variables
export OPENAI_API_KEY=sk-your-key
export ANTHROPIC_API_KEY=sk-ant-your-key
python server.py
```

## Custom Provider Wizard

The Gold Box supports creating custom AI providers following OpenAI-compatible API format.

### Creating a Custom Provider

1. Start backend: `python server.py` or `GOLD_BOX_KEYCHANGE=true python server.py`
2. Select "Add Custom Provider" from key management menu
3. Enter provider name (e.g., `my-provider`, `local-llm`)
4. Enter base URL (e.g., `https://api.example.com/v1`, `http://localhost:11434/v1`)
5. Enter model name (e.g., `my-model-name`, `qwen3:14b`)
6. Enter API key (or select "None" for local providers)
7. Test connection and save

### Authentication Options

1. **Bearer Token** - Standard JWT/API token
2. **API Key in Header** - Custom header name
3. **API Key in Query** - URL parameter
4. **Basic Authentication** - Username:Password
5. **Custom Header** - Specify header name and value
6. **None (Local Provider)** - No authentication

### Provider Type

Choose between **Remote Provider** (cloud API requiring auth) or **Local Provider** (self-hosted, no auth).

### Model Name Guidelines

- **Allowed**: Letters, numbers, dots, hyphens, underscores, colons, slashes
- **No spaces**
- **Examples**: ✅ `gpt-4`, `qwen3:14b`, `openrouter/anthropic/claude-3` | ❌ `gpt 4` (space), `model@name` (@ symbol)

## Memory Configuration

The Gold Box provides conversation history support with intelligent token management.

**Note**: As of v0.3.6, memory settings are not exposed in Foundry UI and must be configured via backend API.

### Memory Settings

| Setting | Default | Range | Description |
|---------|---------|-------|-------------|
| `maxHistoryTokens` | `5000` | 100-100000 | Maximum tokens for history |
| `maxHistoryMessages` | `50` | 1-1000 | Maximum messages to store |
| `maxHistoryHours` | `24` | 1-168 | Maximum age (hours) |

### Memory Management Features

**Token-Based Pruning**: Removes oldest messages when token limit exceeded
**Time-Based Expiration**: Removes messages older than specified time
**Message Count Limits**: Removes oldest messages when count exceeded

### Configuration Examples

```javascript
// Default
{"memorySettings": {"maxHistoryTokens": 5000, "maxHistoryMessages": 50, "maxHistoryHours": 24}}

// Large memory for long conversations
{"memorySettings": {"maxHistoryTokens": 20000, "maxHistoryMessages": 200, "maxHistoryHours": 72}}

// Small memory for quick sessions
{"memorySettings": {"maxHistoryTokens": 1000, "maxHistoryMessages": 20, "maxHistoryHours": 12}}

// No conversation history (delta only)
{"memorySettings": {"maxHistoryTokens": 0, "maxHistoryMessages": 0, "maxHistoryHours": 0}}
```

## Advanced Configuration

### Production Deployment

```bash
export GOLD_BOX_PORT=8080
export CORS_ORIGINS=https://your-foundry-domain.com
export LOG_LEVEL=WARNING
export RATE_LIMIT_MAX_REQUESTS=20
export SESSION_TIMEOUT_MINUTES=120

python server.py
```

### Development Configuration

```bash
export USE_DEVELOPMENT_SERVER=true
export GOLD_BOX_PORT=5000
export LOG_LEVEL=DEBUG

python server.py

# or using backend.sh
./backend.sh --dev
```

### Docker Configuration

**Dockerfile**:
```dockerfile
FROM python:3.9-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
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
      - OPENAI_API_KEY=${OPENAI_API_KEY}
    volumes:
      - ./goldbox.log:/app/goldbox.log
```

### Environment File (.env)

```bash
FLASK_ENV=development
GOLD_BOX_PORT=5000
LOG_LEVEL=DEBUG
OPENAI_API_KEY=your-openai-key
ANTHROPIC_API_KEY=your-anthropic-key
USE_DEVELOPMENT_SERVER=true
```

### Security Configuration File

The `backend/security_config.ini` file provides endpoint-specific settings:

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

## Troubleshooting

### Common Issues

**Port Already in Use**: Server automatically finds next available port

**CORS Issues in Production**: `export CORS_ORIGINS=https://your-foundry-domain.com`

**API Key Problems**: `GOLD_BOX_KEYCHANGE=true python server.py` to reconfigure

**Rate Limiting Too Strict**: `export RATE_LIMIT_MAX_REQUESTS=20`

**Local Provider Connection Failed**:
- Verify local provider is running
- Check base URL (include `/v1` if needed)
- Try both model name formats (with/without prefix like `ollama/`)

**Local Provider Model Not Found**:
- Verify model name format matches your provider
- Check model is downloaded/available
- Try without version tags (e.g., `llama3.2` instead of `llama3.2:3b`)

### Debug Mode

```bash
export LOG_LEVEL=DEBUG
python server.py
```

### Testing Configuration

```bash
# Health check
curl http://localhost:5000/api/health

# Service information
curl http://localhost:5000/api/info

# Security verification
curl http://localhost:5000/api/security
```

## Security Best Practices

### Production Security

1. **Explicit CORS**: `export CORS_ORIGINS=https://your-domain.com`
2. **Strong Admin Password**: Minimum 12 characters with numbers, symbols, mixed case
3. **API Key Protection**: Use environment variables, rotate regularly, monitor usage
4. **Session Management**: Reasonable timeout (60-120 minutes)

### Key Storage Security

- AES-256 encryption for API keys
- PBKDF2 key derivation (100,000 iterations)
- Secure file permissions (0o600 for keys file)
- Admin password protection

### Network Security

- Rate limiting prevents abuse
- CORS restrictions limit cross-origin requests
- Input validation blocks injection attacks
- Session management prevents hijacking

## Performance Optimization

### High-Traffic Configuration

```bash
export RATE_LIMIT_MAX_REQUESTS=50
export SESSION_TIMEOUT_MINUTES=15
export LOG_LEVEL=WARNING
```

### Resource Management

```bash
export FLASK_ENV=production
export LOG_FILE=/dev/null
export SESSION_TIMEOUT_MINUTES=30
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
#!/bin/bash
response=$(curl -s http://localhost:5000/api/health)
status=$(echo $response | jq -r '.status')

if [ "$status" != "healthy" ]; then
    echo "Alert: The Gold Box backend unhealthy"
fi
```

## Support

- **Backend README**: `backend/README.md`
- **Main Project**: `README.md`
- **Dependencies**: `DEPENDENCIES.md`
- **GitHub Issues**: https://github.com/ssjmarx/The-Gold-Box/issues
