# The Gold Box

An AI-powered Foundry VTT module that provides intelligent TTRPG assistance through a sophisticated Python backend. Currently chat-only, this plugin is being developed with the eventual goal of enabling fully single-player play of any adventure module in any TTRPG system supported by Foundry.

## Features

- **LLM Responses**: The LLM can read and react to all of Foundry's chat messages, responding with its own based on what it sees.
- **Multi-Provider Support**: Connect to 70+ AI providers including OpenAI, Anthropic, and more
- **Secure Backend**: Encrypted API key storage with comprehensive security framework
- **User Privacy**: None of your data is collected, none of your information goes anywhere you don't want it

## Quick Start

### 1. Install in Foundry
In Foundry, select **Add-on Modules → Install Module** and paste this URL:
```
https://github.com/ssjmarx/gold-Box/releases/latest/download/module.json
```

### 2. Start Backend Server
An AI-powered Foundry VTT module that provides intelligent TTRPG assistance through a sophisticated Python backend. Currently chat-only, this plugin is being developed with the eventual goal of enabling fully single-player play of any adventure module in any TTRPG system supported by Foundry.

## Features

- **LLM Responses**: The LLM can read and react to all of Foundry's chat messages, responding with its own based on what it sees.
- **Multi-Provider Support**: Connect to 70+ AI providers including OpenAI, Anthropic, and more
- **Secure Backend**: Encrypted API key storage with comprehensive security framework
- **User Privacy**: None of your data is collected, none of your information goes anywhere you don't want it

## Quick Start

### 1. Install in Foundry
In Foundry, select **Add-on Modules → Install Module** and paste this URL:
```
https://github.com/ssjmarx/gold-Box/releases/latest/download/module.json
```

### 2. Start Backend Server
```bash
# Navigate to the module directory
cd ~/.local/share/FoundryVTT/Data/modules/gold-box/
cd ~/.local/share/FoundryVTT/Data/modules/gold-box/

# Run the setup script (recommended)
# Run the setup script (recommended)
./backend.sh

# Or start manually
cd backend
source venv/bin/activate
python server.py
```

Note: DO NOT CLOSE THE TERMINAL WINDOW!  The server must be running in order for the plugin to work.

The setup script will:
- Automatically install all Python dependencies
- Guide you through API key setup if needed
- Start the server on an available port (5000-5020)
- Display connection information

### 3. Configure in Foundry
# Or start manually
cd backend
source venv/bin/activate
python server.py
```

Note: DO NOT CLOSE THE TERMINAL WINDOW!  The server must be running in order for the plugin to work.

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

The Gold Box supports three distinct chat processing modes:

1. **Simple Mode** (`/api/simple_chat`)
   - Direct HTML-based message collection from Foundry chat
   - Minimal processing overhead
   - Compatible with all Foundry versions

2. **Processed Mode** (`/api/process_chat`)
   - Enhanced HTML processing with structured data extraction
   - Token-efficient compact JSON format
   - Better context preservation for AI

3. **API Mode** (`/api/api_chat`) - *New in v0.3.0*
   - REST API-based message collection via Foundry Gold API module
   - Most reliable and maintainable approach
   - Foundation for advanced Foundry integration features

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
Gold-Box/
├── module.json               # Foundry module manifest
├── scripts/
│   ├── gold-box.js           # Main frontend logic
│   └── connection-manager.js # Backend communication
├── styles/
│   └── gold-box.css          # Module styling
├── lang/
│   └── en.json               # English translations
├── backend/
│   ├── server.py             # FastAPI application
│   ├── requirements.txt      # Python dependencies
│   ├── endpoints/            # API endpoints
│   ├── security/             # Security framework
│   └── server_files/         # Runtime files
├── licenses/                 # Dependency licenses
└── README.md                 # This file
```
   - **Backend Password**: Set from server startup (admin operations)
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
Gold-Box/
├── module.json               # Foundry module manifest
├── scripts/
│   ├── gold-box.js           # Main frontend logic
│   └── connection-manager.js # Backend communication
├── styles/
│   └── gold-box.css          # Module styling
├── lang/
│   └── en.json               # English translations
├── backend/
│   ├── server.py             # FastAPI application
│   ├── requirements.txt      # Python dependencies
│   ├── endpoints/            # API endpoints
│   ├── security/             # Security framework
│   └── server_files/         # Runtime files
├── licenses/                 # Dependency licenses
└── README.md                 # This file
```

## Dependencies

### Backend (Python)
- **FastAPI** - Modern web framework (MIT License)
### Backend (Python)
- **FastAPI** - Modern web framework (MIT License)
- **Uvicorn** - ASGI server (BSD 3-Clause License)
- **LiteLLM** - Unified LLM interface (MIT License)
- **cryptography** - Encryption security (BSD 3-Clause License)
- **cryptography** - Encryption security (BSD 3-Clause License)
- **pydantic** - Data validation (MIT License)
- **python-dotenv** - Environment management (BSD 3-Clause License)
- **python-dotenv** - Environment management (BSD 3-Clause License)

### Frontend (JavaScript)
### Frontend (JavaScript)
- **Foundry VTT API** - Game system integration
- **Modern JavaScript** - ES6+ features and patterns
- **CSS3** - Responsive design and animations
- **Modern JavaScript** - ES6+ features and patterns
- **CSS3** - Responsive design and animations

## License

This project is licensed under **Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International License**. See [LICENSE](LICENSE) file for details.
This project is licensed under **Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International License**. See [LICENSE](LICENSE) file for details.

## Support

- **GitHub Issues**: [Report Issues](https://github.com/ssjmarx/Gold-Box/issues)
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

**Current Version: 0.2.5** - Enhanced security framework, comprehensive chat context processor, and multi-provider support

## Release Readiness Checklist ✅

### ✅ Completed Tasks
- [x] Updated module.json to v0.3.0 with clean dependencies
- [x] Updated CHANGELOG.md with comprehensive v0.3.0 changes
- [x] Fixed duplicate esmodules entries in module.json
- [x] Updated README.md to reflect current architecture
- [x] Removed build-relay-server.sh script (no longer needed)
- [x] Cleaned up submodule references from documentation
- [x] Updated description to remove submodule requirements

### 🚀 Ready for Release
The Gold Box v0.3.0 is ready for GitHub release with:
- **Enhanced chat processing** with three modes (Simple, Processed, API)
- **Critical bug fixes** for unified settings and client ID management
- **Updated documentation** reflecting current architecture
- **Clean module manifest** without duplicate entries
- **Comprehensive changelog** covering all improvements

### 📋 Release Steps
1. **Build Relay Server**: `./build-relay-server.sh` (to package latest relay server)
2. **Commit changes**: `git add . && git commit -m "v0.3.0: REST API integration and bug fixes"`
3. **Create tag**: `git tag v0.3.0`
4. **Push to GitHub**: `git push origin main --tags`
5. **Create GitHub Release** through GitHub web interface
6. **Update manifest URLs** to point to new release

### 🔧 Development Tools
- **build-relay-server.sh**: Script to build and package the latest relay server for inclusion in releases
- Run this script before committing to ensure relay-server/ contains the latest build

## Quick Start
