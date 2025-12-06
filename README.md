# The Gold Box

An AI-powered Foundry VTT module that provides intelligent TTRPG assistance through a sophisticated Python backend. Currently chat-only, this plugin is being developed with the eventual goal of enabling fully single-player play of any adventure module in any TTRPG system supported by Foundry.

## Acknowledgments

This project was inspired by and learned significantly from the **Foundry VTT REST API** project by **ThreeHats**. While The Gold Box ultimately follows a different architectural approach (direct WebSocket integration vs. relay server), the developer gained valuable experience in:

- Foundry VTT module development patterns
- WebSocket communication in Foundry
- Session management and security practices
- Real-time data synchronization techniques

The Gold Box owes a debt of gratitude to ThreeHats for their module and for providing a foundation of knowledge that made this project possible.

**Original Project**: [Foundry VTT REST API by ThreeHats](https://github.com/ThreeHats/foundryvtt-rest-api)

## Features

- **LLM Responses**: The LLM can read and react to all of Foundry's chat messages, responding with its own based on what it sees.
- **Multi-Provider Support**: Connect to 70+ AI providers including OpenAI, Anthropic, and more
- **Secure Backend**: Encrypted API key storage with comprehensive security framework
- **User Privacy**: None of your data is collected, none of your information goes anywhere you don't want it

## Quick Start

### 1. Install in Foundry
In Foundry, select **Add-on Modules → Install Module** and paste this URL:
```
https://github.com/ssjmarx/The-Gold-Box/releases/latest/download/module.json
```

### 2. Start Backend Server
```bash
# Navigate to the module directory
cd ~/.local/share/FoundryVTT/Data/modules/the-gold-box/

# Run the setup script (recommended)
./backend.sh

# Or start manually
cd backend
source venv/bin/activate
python server.py
```

Note: DO NOT CLOSE THE TERMINAL WINDOW! The server must be running for the module to work.

The setup script will:
- Automatically install all Python dependencies
- Guide you through API key setup if needed
- Start the server on an available port (5000-5020)
- Display connection information

### 3. Configure in Foundry
1. Go to **Game Settings → Module Settings**
2. Find **The Gold Box** in the list
3. Configure:
   - **Backend Password**: Set from server startup (admin operations)
   - **Chat Processing Mode**: Choose "API (recommended)" or "Context (unfinished)"
   - **AI Role**: Choose DM, DM Assistant, or Player
   - **General LLM Provider**: Your AI service (e.g., openai, anthropic)
   - **General LLM Model**: Your model (e.g., gpt-3.5-turbo, claude-3-5-sonnet-20241022)
   - **Maximum Message Context**: Recent messages to include (default: 15)

### 4. Use in Game
Press the **"Take AI Turn"** button in the chat sidebar to send your conversation context to the AI and receive intelligent responses.

## Architecture

```
Foundry VTT (Frontend)     Python Backend (API)          AI Services
├── Chat Integration         ├── FastAPI Server          ├── OpenAI
├── Settings Management      ├── Session Management      ├── Anthropic
├── Message Context          ├── Security Framework      └── 70+ Others
├── Auto-Discovery           ├── Multi-Provider Support  
└── Error Handling           └── Encrypted Storage
```

### Processing Modes

The Gold Box supports two chat processing modes:

1. **API Mode** (`/api/api_chat`) - *Recommended*
   - Direct WebSocket communication with real-time message exchange
   - Most reliable and maintainable approach
   - Native integration without external dependencies
   - Supports structured AI responses (chat messages, dice rolls, cards)

2. **Context Mode** (`/api/context_chat`) - *Experimental/Unfinished*
   - Full board state integration including tokens, walls, lighting, and map notes
   - Complete scene context for AI processing
   - Currently in development - not fully implemented

**Note**: Previous "Simple" and "Processed" modes have been deprecated and removed to streamline the codebase and improve user experience.

## Supported AI Providers

The Gold Box supports 70+ AI providers through LiteLLM integration:

### Popular Providers
- **OpenAI**: GPT-3.5, GPT-4, GPT-4 Turbo, DALL-E
- **Anthropic**: Claude 3, Claude 3.5 Sonnet
- **Google AI**: Gemini models

### Coding-Focused Providers
- **OpenCode/GLM**: Z.AI coding models
- **OpenRouter**: Multiple provider access
- **Together AI**: Open-source models
- **Replicate**: Community models

### Self-Hosted
- **Local LLM**: Ollama, LM Studio, and other local setups
- **Custom Endpoints**: Any OpenAI-compatible API

### File Structure
```
The-Gold-Box/
├── module.json               # Foundry module manifest
├── backend.sh               # Backend setup and startup script
├── README.md               # This file
├── CHANGELOG.md            # Version history and changes
├── USAGE.md               # Detailed usage instructions
├── LICENSE                 # Creative Commons license
├── scripts/
│   ├── gold-box.js           # Main frontend logic and UI
│   ├── connection-manager.js # Backend communication manager
│   ├── websocket-client.js   # WebSocket client implementation
│   ├── message-collector.js # Chat message collection
│   └── api-bridge.js       # API compatibility layer
├── styles/
│   └── gold-box.css        # Module styling and UI components
├── lang/
│   └── en.json             # English translations
├── backend/
│   ├── server.py            # FastAPI application entry point
│   ├── requirements.txt     # Python dependencies
│   ├── security_config.ini  # Security configuration
│   ├── TESTING.md          # Backend testing guide
│   ├── endpoints/          # API endpoint implementations
│   │   ├── __init__.py
│   │   ├── api_chat.py     # Primary chat processing endpoint
│   │   └── context_chat.py # Context-aware chat endpoint
│   ├── security/           # Security and validation framework
│   │   ├── __init__.py
│   │   ├── input_validator.py # Request validation
│   │   ├── security.py     # Encryption and security utilities
│   │   └── sessionvalidator.py # Session management
│   ├── server/             # Core server logic and processors
│   │   ├── __init__.py
│   │   ├── ai_chat_processor.py # AI chat processing
│   │   ├── ai_prompt_validator.py # Prompt validation
│   │   ├── ai_service.py    # AI service integration
│   │   ├── api_chat_processor.py # API chat processing
│   │   ├── board_collector.py # Game board state collection
│   │   ├── client_manager.py # WebSocket client management
│   │   ├── context_processor.py # Context data processing
│   │   ├── dice_collector.py # Dice roll collection
│   │   ├── json_optimizer.py # JSON optimization utilities
│   │   ├── key_manager.py   # API key management
│   │   ├── message_collector.py # Message collection logic
│   │   ├── message_protocol.py # WebSocket message protocol
│   │   ├── processor.py     # General processing utilities
│   │   ├── provider_manager.py # AI provider management
│   │   ├── simple_attribute_mapper.py # Attribute mapping
│   │   ├── universal_settings.py # Global settings
│   │   └── websocket_server.py # WebSocket server implementation
│   └── server_files/       # Runtime configuration files
│       └── litellm_providers.json # Supported AI providers
└── licenses/                # Dependency license documentation
    ├── README.md
    ├── BeautifulSoup4-MIT.txt
    ├── Cryptography-BSD-3-Clause.txt
    ├── FastAPI-MIT.txt
    ├── Flask-BSD-3-Clause.txt
    ├── Flask-CORS-MIT.txt
    ├── FoundryVTT-REST-API-MIT.txt
    ├── FoundryVTT-REST-API-Relay-MIT.txt
    ├── Gunicorn-BSD-3-Clause.txt
    ├── LiteLLM-MIT.txt
    ├── Pydantic-MIT.txt
    ├── python-dotenv-BSD-3-Clause.txt
    ├── SlowAPI-MIT.txt
    └── Uvicorn-BSD-3-Clause.txt
```

## Dependencies

### Backend (Python)
- **FastAPI 0.121.3** - Modern web framework (MIT License)
- **Uvicorn 0.38.0[standard]** - ASGI server (BSD 3-Clause License)
- **Pydantic 2.12.4** - Data validation (MIT License)
- **LiteLLM 1.80.0** - Unified LLM interface (MIT License)
- **Cryptography >=41.0.0** - Encryption security (BSD 3-Clause License)
- **python-dotenv 1.2.1** - Environment management (BSD 3-Clause License)
- **WebSockets >=11.0.3** - WebSocket server implementation (BSD 3-Clause License)
- **SlowAPI 0.1.9** - Rate limiting for FastAPI (MIT License)
- **BeautifulSoup4 4.12.3** - HTML parsing for Foundry chat messages (MIT License)

#### Legacy Dependencies (Fallback Support)
- **Flask 3.1.2** - Legacy web framework (BSD 3-Clause License)
- **Flask-CORS 6.0.1** - Cross-origin requests (MIT License)
- **Gunicorn 21.2.0** - Production WSGI server (BSD 3-Clause License)

### Frontend (JavaScript)
- **Foundry VTT API** - Game system integration
- **Modern JavaScript (ES6+)** - Features and patterns
- **CSS3** - Responsive design and animations
- **WebSocket API** - Real-time communication
- **Fetch API** - HTTP requests
- **Crypto API** - Secure random generation

## License

This project is licensed under **Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International License**. See [LICENSE](LICENSE) file for details.

## Support

- **GitHub Issues**: [Report Issues](https://github.com/ssjmarx/The-Gold-Box/issues)
- **Documentation**: [Backend Documentation](backend/README.md)
- **Changelog**: [Version History](CHANGELOG.md)

## Development Roadmap

### Current Focus
- Enhanced context including entire board state and token attributes
- LLM model switching based on context (ie using a "tactical AI" while in combat)
- Enable LLM actions in Foundry such as dice rolls and token movement
- LLM Action history with undo/redo/retry

### Future Features
- Smart scene switching, descriptions, other noncombat gm actions
- Advanced context gathering through Compendium
- Define LLM "role" with Foundry permissions
- Access other generative services, such as image and voice

**Current Version: 0.3.3** - Deprecated endpoint cleanup, API mode refinement, and release preparation
