# The Gold Box

An AI-powered Foundry VTT module that provides intelligent TTRPG assistance through a sophisticated Python backend. This project creates a single-player TTRPG experience where an AI can serve as Dungeon Master, DM Assistant, or Player, with full user control and transparency.

## Version 0.2.4

### 🚀 Latest Features (v0.2.4) - Completed Phase One of Roadmap

#### Enhanced Message Context Processing
- **Full Chat History Context** - Automatically collects recent chat messages for AI context
- **Configurable Context Length** - User-adjustable message context window (default: 15 messages)
- **Chronological Ordering** - Messages sent in proper time sequence (oldest to newest)
- **HTML Content Preservation** - Maintains dice rolls, formatting, and rich content
- **Smart Content Extraction** - Preserves Foundry's native HTML structure

#### Fixed JavaScript Integration
- **Resolved Syntax Errors** - Fixed all JavaScript syntax issues preventing module loading
- **Restored Settings Menu** - Module settings now properly display in Foundry configuration
- **Fixed Chat Button** - "Take AI Turn" button appears and functions correctly
- **Enhanced Error Handling** - Better error messages and debugging information

#### Improved Backend Communication
- **Enhanced API Debugging** - Detailed logging for content extraction and processing
- **Better Error Messages** - Smart error handling with user-friendly feedback
- **Fixed Content Display** - Resolved issues with AI response content not showing
- **Improved Service Integration** - Better handling of OpenCode-compatible API responses

#### Advanced AI Service Support
- **OpenAI Compatible API** - Full support for OpenAI and compatible services
- **NovelAI API Integration** - Specialized support for NovelAI services
- **OpenCode Compatible API** - Support for coding-focused AI services like Z.AI
- **Local LLM Support** - Integration with local language models
- **Service Selection** - User-configurable LLM service selection

## Project Vision

The Gold Box transforms Foundry VTT into an intelligent TTRPG assistant that will be able to:
- Act as a complete Dungeon Master for solo play (or group play when no traditional GM is available)
- Serve as a DM Assistant to help human DMs
- Play as an AI-controlled Player character
- Generate contextual content based on game state and chat history
- Execute in-game actions through structured commands
- Provide multi-modal experiences (text, images, audio)

## Architecture Overview

```
+-----------+      (1) User Action     +---------------------+       (2) Request (Prompt + Context)  +-------------------+   (3) API Call      +----------+
|           |------------------------->|                     |-------------------------------------->|                   |-------------------->|          |
|   User    |                          | Foundry VTT Module  |                                       | Python Backend    |                     |   LLM    |
|           |<-------------------------|    (JavaScript)     |<--------------------------------------|  (FastAPI/Flask)  |<--------------------|  APIs    |
+-----------+      (6) Final Update    +---------------------+      (5) Structured Command           +-------------------+    (4) Response     +----------+
      ^                                                                                   |
      |                                                                                   |
      +--------------------------------(7) Other APIs (Image, TTS)------------------------+
```

## Components

### 1. Foundry VTT Module (JavaScript)
The user interface and game interaction layer that:
- Handles all user interactions through the **"Take AI Turn"** button
- Gathers comprehensive game state and chat history for context
- Executes structured commands from the backend
- Provides detailed AI responses with role-based formatting
- Displays contextual responses based on recent chat messages
- Supports multiple AI roles (DM, DM Assistant, Player)
- Auto-discovers backend ports for seamless connection
- Manages comprehensive settings for multiple LLM providers

### 2. Python Backend (FastAPI)
The intelligence layer that:
- Manages API keys securely with encrypted storage
- Handles prompt engineering and context management
- Communicates with various AI services through LiteLLM integration
- Maintains AI turn/thread state
- Orchestrates multiple AI agents for different tasks
- Provides comprehensive validation and security features
- Supports 70+ AI providers through unified interface

### 3. External APIs (via LiteLLM)
The AI services that provide:
- Language models (GPT, Novel AI, OpenCode/GLM, etc.)
- Image generation (DALL-E, Stable Diffusion)
- Text-to-Speech/Speech-to-Text (ElevenLabs, Whisper)
- Access to 70+ providers through single interface

## Implementation Phases

### ✅ Phase 1: The "Parrot" - Basic Communication
**Status: COMPLETE with v0.2.3 enhancements**
- ✅ Create Foundry UI with input/output areas
- ✅ Implement "Take AI Turn" button with proper functionality
- ✅ Set up FastAPI backend with `/simple_chat` endpoint
- ✅ Display AI responses in Foundry chat

### 🔄 Phase 2: The "Observer" - Context-Aware Responses
**Status: IN PROGRESS**
- Expand game state gathering (more than just chat history)
- Functional AI Role selection (DM, DM Assistant, Player)
- Create new API endpoint `/ai_turn`
- Implement sophisticated prompt engineering for data in `/ai_turn`

### ⏳ Phase 3: The "Actor" - Tool-Driven Actions
**Goal:** Allow AI to perform actions in the game world
- Implement LLM function calling/tool use
- Create `executeAction()` function in Foundry for various action types:
  - Dice rolling
  - Token movement
  - Actor health updates
  - Chat message creation
- Establish action-result communication loop

### ⏳ Phase 4: The "Orchestrator" - Advanced Features
**Goal:** Add multi-modal capabilities and complex agent systems
- Build comprehensive Action Log UI with undo/redo/retry
- Implement multi-agent architecture:
  - Narrator Agent for descriptions
  - Tactical Agent for combat
  - Image Generation Agent
  - TTS/STT Agent
- Add state management for turn history and reversibility

## Key Design Principles

### No Unprompted AI Action
The **"Take AI Turn"** button is the single point of entry. All AI logic is triggered only by explicit user action.

### Full User Control
- **Chat Integration**: AI responses appear directly in Foundry chat
- **Transparency**: Users can see exactly what context is sent to AI
- **Role Selection**: Different AI behaviors based on selected role
- **Service Choice**: Users select which AI service to use

### Multi-Role Support
- **DM:** Full access to all tools and game controls
- **DM Assistant:** Limited to enemy control and assistance functions
- **Player:** Restricted to personal character actions only

### Context-Aware Responses
The AI now receives full chat context:
- **Recent Messages**: Configurable number of recent chat messages
- **Chronological Order**: Messages sent in proper time sequence
- **Rich Content**: Preserves dice rolls, formatting, and HTML structure
- **Sender Information**: Maintains who said what in the conversation

## Technology Stack

### Frontend (Foundry VTT Module)
- JavaScript/ES6+ with modern syntax
- Foundry VTT API integration (v12+ supported, v13 verified)
- CSS for responsive styling
- Message context collection from DOM with HTML preservation
- Provider-agnostic API communication via unified settings
- Auto-discovery of backend ports
- Comprehensive settings management for multiple LLM providers

### Backend (Python)
- FastAPI for modern web framework (primary)
- Uvicorn ASGI server for production
- Flask fallback for legacy compatibility
- LiteLLM integration for 70+ AI provider support
- Universal Input Validation system with comprehensive protection
- Flask-CORS with environment-based origin restrictions
- Rate limiting and security headers
- Environment-based configuration management
- Encrypted API key storage with admin password protection
- ProviderManager for multi-provider configuration
- Enhanced message context processing

### AI Services (via LiteLLM)
- **70+ Providers**: OpenAI, Anthropic, Google AI, Azure OpenAI, Cohere, Groq, Together AI, Replicate, Fireworks AI, xAI, AWS Bedrock, Google Vertex AI, Mistral AI, Perplexity AI, OpenRouter, NovelAI, and many more
- **Custom Providers**: Support for self-hosted and custom endpoints
- **Provider-Agnostic**: Single interface for all AI services
- **OpenCode Compatible**: GLM-4.6, Z.AI, and other coding-focused models
- **Local LLM**: Self-hosted model support through LiteLLM

## Development Setup

### Prerequisites
- Foundry VTT installation (v12+ recommended, v13 supported)
- Python 3.8+ (3.13 compatible)
- Node.js 16+ (for development)
- API keys for chosen AI services

### Installation
1. Clone this repository into Foundry's Data/modules folder
2. Set up Python backend following backend/README.md instructions
3. Start Foundry while backend is running
4. Enable "The Gold Box" in Foundry world settings
5. Configure module through Foundry settings menu

> **Note**: For detailed environmental variable configuration options, see [USAGE.md](USAGE.md).

### Configuration
- **Backend URL**: Set to `http://localhost:5000` (or your server port)
- **Backend Password**: Admin password for secure operations
- **AI Role**: Choose DM, DM Assistant, or Player
- **General LLM Provider**: Select from 70+ available providers
- **General LLM Model**: Choose specific model for selected provider
- **General LLM Base URL**: Custom endpoint for providers
- **Maximum Message Context**: Configure how many recent messages to include (default: 15)
- **Service-Specific Settings**: API endpoints, models, timeouts, retries, and custom headers

## Usage Instructions

## 1. Install in Foundry
In foundry, select "add on modules" in the setup menu, and paste this into the "manifest url"

https://github.com/ssjmarx/Gold-Box/releases/download/latest/module.json

This will register the plugin with your copy of Foundry, allowing it to be enabled in your game worlds and recieve auto-updates.

### 2. Start the Backend
```bash
# Navigate to the module directory
(on linux) cd ~/.local/share/FoundryVTT/Data/modules/gold-box/

# Run setup script
./backend.sh

# Setup script will automatically install all requirements and start the server
# Or, you can start the server manually
source ./backend/venv/bin/activate && python ./backend/server.py

# If no API key file exists, the server will guide you through the key registration process

# Once server is running, launch your Foundry world with the plugin installed and activated
# Or if it is already running, navigate to the plugin settings and click "Rediscover Backend"
```

### 3. Configure Foundry Module
1. Go to **Game Settings → Module Settings**
2. Find **The Gold Box** in the list
3. Configure:
   - **Backend Password**: Your server password (configured by the server when it starts for the first time)
   - **AI Role**: DM, DM Assistant, or Player
    - This project uses litellm, view litellm's list of supported models/providers at https://docs.litellm.ai/docs/providers or https://models.litellm.ai/
    - For some providers, connectivity may be possible even if it's not officially documented.  Contact your AI service's customer support if you are having issues connecting.
   - **General LLM Provider**: Input your provider name
   - **General LLM Model**: Select specific model
   - **General LLM Base URL**: Custom endpoint if needed
   - **Maximum Message Context**: Number of recent Foundry messages to send as context (default: 15)
    - WARNING: If you exceed the context limit of your subscription, your request may be denied, or your service may choose to charge you for excess tokens.  It is your responsibility to monitor your usage to ensure that you remain within the bounds of your subscription and budget.

### 4. Take AI Turn
Press the `Take AI Turn` button, located under the chat window in Foundry, to send your current settings and chat context to the server.  If everything is configured correctly, you will recieve a response in a few seconds depending on the model you are connected to and your internet speed.
  - NOTE: If you are unsure of whether your message was sent to the AI service, check the server terminal.  If you see a message like `Sending to OpenRouter API: openrouter with model: openai/glm-4.6`, keep waiting as the message has been sent and the server is waiting for the response.  If your message fails for any reason, you should see the recieved error code in both the server log and the Foundry chat.

## Privacy & Security

**Important**: The Gold Box is designed with privacy-first principles. Your AI prompts and responses are handled securely, and neither the module nor the server collect any user data.  Nothing gets sent to any web servers except for the AI API endpoints that you specifically configure, however you should be aware of your chosen AI service's privacy policy before conducting chats that contain sensitive information.

### 🔒 Security Features
- **Encrypted Key Storage**: API keys encrypted with AES-256
- **Admin Password Protection**: Secure admin operations
- **Input Validation**: Comprehensive security checking
- **Rate Limiting**: Protection against abuse
- **CORS Protection**: Environment-based origin control
- **Session Management**: Secure session handling

### 🔐 Privacy Protection
- **No Content Logging**: Chat content is not stored permanantly by the server, however it may be stored by Foundry.
- **Local Processing**: You control server exposure
- **User Control**: Explicit action required for AI responses

### 🛡️ Production Security
- **Environment-Based Config**: Different security for dev/prod
- **Fail-Safe Approach**: No access unless explicitly configured
- **Comprehensive Headers**: XSS, CSRF, injection protection
- **Health Monitoring**: Security verification endpoints

## Troubleshooting

### Common Issues (v0.2.3)

#### ✅ **FIXED**: JavaScript Syntax Errors
- **Previous**: Module wouldn't load due to syntax errors
- **Solution**: All JavaScript syntax issues resolved in v0.2.3

#### ✅ **FIXED**: Settings Menu Not Appearing
- **Previous**: Module settings not showing in Foundry
- **Solution**: Fixed settings registration in v0.2.3

#### ✅ **FIXED**: Chat Button Not Working
- **Previous**: "Take AI Turn" button not appearing
- **Solution**: Fixed button creation and event handling

#### ✅ **FIXED**: API Content Not Showing
- **Previous**: AI responses appearing empty
- **Solution**: Enhanced content extraction and logging

## Dependencies

### Core Backend Dependencies
- **FastAPI** - Modern Python web framework (MIT License)
- **Uvicorn** - ASGI server (BSD 3-Clause License)
- **LiteLLM** - Unified LLM interface (MIT License)
- **python-dotenv** - Environment variable management (BSD 3-Clause License)
- **cryptography** - Encryption and security (Apache 2.0 License)
- **pydantic** - Data validation (MIT License)
- **slowapi** - Rate limiting for FastAPI (MIT License)

### Frontend Dependencies
- **Foundry VTT API** - Game system integration
- **Modern JavaScript** - ES6+ features
- **CSS3** - Styling and responsive design

## Contributing

This project is actively developed. Contributions are welcome in all areas, contact me via Github if you would like to contribute.

## License

This project is licensed under **Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International License**. See the [LICENSE](LICENSE) file for details.

## Roadmap

### ✅ Completed (v0.2.3)
- [x] Basic LLM communication with chat context
- [x] Enhanced debugging and logging
- [x] Multi-service AI support (70+ providers)
- [x] Secure key management

### 🔄 In Progress
- [ ] Context-aware responses with scene/token information
- [ ] Tool-driven actions (dice rolling, token movement)
- [ ] Enhanced error handling and recovery

### ⏳ Future Features
- [ ] Multi-modal capabilities (images, audio)
- [ ] Advanced AI agent orchestration
- [ ] Action history with undo/redo
- [ ] Performance optimization
- [ ] Additional AI service integrations

## Support

For issues and feature requests:
- **GitHub Issues**: [Repository Issues](https://github.com/ssjmarx/Gold-Box/issues)
- **Documentation**: [Backend README](backend/README.md)
- **Changelog**: [CHANGELOG.md](CHANGELOG.md)

---

**Version 0.2.3** - Enhanced message context, fixed JavaScript integration, improved debugging capabilities, and LiteLLM integration for 70+ AI providers
