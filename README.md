# The Gold Box

An AI-powered Foundry VTT module that provides intelligent TTRPG assistance through a sophisticated Python backend. This project creates a single-player TTRPG experience where an AI can serve as Dungeon Master, DM Assistant, or Player, with full user control and transparency.

## Version 0.2.3

### 🚀 Latest Features (v0.2.3)

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

The Gold Box transforms Foundry VTT into an intelligent TTRPG assistant that can:
- Act as a complete Dungeon Master for solo play (or group play when no traditional GM is available)
- Serve as a DM Assistant to help human DMs
- Play as an AI-controlled Player character
- Generate contextual content based on game state and chat history
- Execute in-game actions through structured commands
- Provide multi-modal experiences (text, images, audio)

## Architecture Overview

```
+-----------+      (1) User Action     +---------------------+       (2) Request (Prompt + Context)    +-------------------+   (3) API Call      +----------+
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

### 2. Python Backend (FastAPI)
The intelligence layer that:
- Manages API keys securely with encrypted storage
- Handles prompt engineering and context management
- Communicates with various AI services (LLM, Image Generation, TTS)
- Maintains AI turn/thread state
- Orchestrates multiple AI agents for different tasks
- Provides comprehensive validation and security features

### 3. External APIs
The AI services that provide:
- Language models (GPT, Novel AI, OpenCode/GLM, etc.)
- Image generation (DALL-E, Stable Diffusion)
- Text-to-Speech/Speech-to-Text (ElevenLabs, Whisper)

## Implementation Phases

### ✅ Phase 1: The "Parrot" - Basic Communication
**Status: COMPLETE with v0.2.3 enhancements**
- ✅ Create Foundry UI with input/output areas
- ✅ Implement "Take AI Turn" button with proper functionality
- ✅ Set up FastAPI backend with `/simple_chat` endpoint
- ✅ Display AI responses in both UI module and Foundry chat
- ✅ **NEW**: Full message context collection and processing
- ✅ **NEW**: Enhanced debugging and error handling
- ✅ **NEW**: Fixed JavaScript syntax errors

### 🔄 Phase 2: The "Observer" - Context-Aware Responses
**Status: IN PROGRESS**
- ✅ Expand game state gathering (chat history with context)
- ✅ Add AI Role selection (DM, DM Assistant, Player)
- ✅ Implement sophisticated prompt engineering
- ✅ **NEW**: Create `/simple_chat` endpoint with rich context processing
- 🔄 Implement `/contextual_action` endpoint with scene/token context
- 🔄 Add character and scene awareness

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
- Foundry VTT API integration
- CSS for responsive styling
- Message context collection from DOM
- Multi-service API communication

### Backend (Python)
- FastAPI for modern web framework
- Uvicorn ASGI server for production
- Universal Input Validation system with comprehensive protection
- Flask-CORS with environment-based origin restrictions
- HTTP clients for multiple AI service APIs
- Rate limiting and security headers
- Environment-based configuration management
- Encrypted API key storage with admin password protection

### AI Services
- **OpenAI Compatible**: GPT-3.5, GPT-4, and compatible models
- **NovelAI**: Specialized TTRPG-focused models
- **OpenCode Compatible**: GLM-4.6 and other coding-focused models
- **Local LLM**: Self-hosted model support

## Development Setup

### Prerequisites
- Foundry VTT installation (v12+ recommended, v13 supported)
- Python 3.8+
- Node.js 16+ (for development)
- API keys for chosen AI services

### Installation
1. Clone this repository into Foundry's Data/modules folder
2. Set up Python backend following backend/README.md instructions
3. Start Foundry while backend is running
4. Enable "The Gold Box" in Foundry world settings
5. Configure module through Foundry settings menu

### Configuration
- **Backend URL**: Set to `http://localhost:5000` (or your server port)
- **Backend Password**: Admin password for secure operations
- **AI Role**: Choose DM, DM Assistant, or Player
- **LLM Service**: Select OpenAI, NovelAI, OpenCode, or Local
- **Message Context**: Configure how many recent messages to include
- **Service-Specific Settings**: API endpoints and model names per service

## Usage Instructions

### 1. Start the Backend
```bash
# Navigate to backend directory
cd backend

# Install dependencies
pip install -r requirements.txt

# Start the server
python server.py
```

### 2. Configure Foundry Module
1. Go to **Game Settings → Module Settings**
2. Find **The Gold Box** in the list
3. Configure:
   - **Backend URL**: `http://localhost:5000`
   - **Backend Password**: Your admin password
   - **General LLM**: Choose your AI service
   - **AI Role**: DM, DM Assistant, or Player
   - **Maximum Message Context**: Number of recent messages (default: 15)

### 3. Use the Module
1. **Configure API Keys**: First-time setup will prompt for API keys
2. **Test Connection**: Use "Discover Backend" button to verify connection
3. **Take AI Turn**: Click the button in chat sidebar
4. **View Responses**: AI responses appear in chat with full context awareness

### 4. Message Context Features
The module automatically:
- **Collects Recent Messages**: Gathers last N messages from chat
- **Preserves Formatting**: Maintains dice rolls and HTML content
- **Sends Chronologically**: Orders messages oldest to newest
- **Includes Metadata**: Sender information and timestamps
- **Context Window**: Configurable size for context length

## Privacy & Security

**Important**: The Gold Box is designed with privacy-first principles. Your AI prompts and responses are handled securely.

### 🔒 Security Features
- **Encrypted Key Storage**: API keys encrypted with AES-256
- **Admin Password Protection**: Secure admin operations
- **Input Validation**: Comprehensive security checking
- **Rate Limiting**: Protection against abuse
- **CORS Protection**: Environment-based origin control
- **Session Management**: Secure session handling

### 🔐 Privacy Protection
- **No Content Logging**: Chat content is not stored permanently
- **Local Processing**: You control server exposure
- **User Control**: Explicit action required for AI responses
- **Transparent Context**: You can see exactly what context is sent

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

### Connection Issues
1. **Backend Not Running**
   - Start backend: `cd backend && python server.py`
   - Check port is available (default: 5000)

2. **CORS Problems**
   - Verify Foundry URL is in allowed origins
   - Check backend CORS configuration

3. **API Key Issues**
   - Run backend key management wizard
   - Verify keys are properly encrypted

### Debug Mode
Enable detailed logging:
```bash
LOG_LEVEL=DEBUG python server.py
```

## Dependencies

### Core Backend Dependencies
- **FastAPI** - Modern Python web framework (MIT License)
- **Uvicorn** - ASGI server (BSD 3-Clause License)
- **python-dotenv** - Environment variable management (BSD 3-Clause License)
- **cryptography** - Encryption and security (Apache 2.0 License)
- **pydantic** - Data validation (MIT License)

### Frontend Dependencies
- **Foundry VTT API** - Game system integration
- **Modern JavaScript** - ES6+ features
- **CSS3** - Styling and responsive design

## Contributing

This project is actively developed. Contributions are welcome in:
- Additional AI service integrations
- New tool implementations for Foundry VTT
- Improved prompt engineering
- UI/UX enhancements
- Bug fixes and performance improvements

## License

This project is licensed under **Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International License**. See the [LICENSE](LICENSE) file for details.

## Roadmap

### ✅ Completed (v0.2.3)
- [x] Basic LLM communication with context
- [x] JavaScript syntax error fixes
- [x] Enhanced debugging and logging
- [x] Message context collection
- [x] Multi-service AI support
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

**Version 0.2.3** - Enhanced message context, fixed JavaScript integration, and improved debugging capabilities
