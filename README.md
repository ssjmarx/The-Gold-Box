# The Gold Box

An AI-powered Foundry VTT module that provides intelligent TTRPG assistance through a sophisticated Python backend. This project creates a single-player TTRPG experience where an AI can serve as Dungeon Master, DM Assistant, or Player, with full user control and transparency.

## Project Vision

The Gold Box transforms Foundry VTT into an intelligent TTRPG assistant that can:
- Act as a complete Dungeon Master for solo play (or group play when no traditional GM is available)
- Serve as a DM Assistant to help human DMs
- Play as an AI-controlled Player character
- Generate contextual content based on game state
- Execute in-game actions through structured commands
- Provide multi-modal experiences (text, images, audio)

## Architecture Overview

```
+-----------+      (1) User Action     +---------------------+       (2) Request (Prompt + State)    +-------------------+   (3) API Call      +----------+
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
- Gathers comprehensive game state (scenes, tokens, characters, chat history)
- Executes structured commands from the backend
- Provides a detailed Action Log with undo/redo/retry functionality
- Displays AI responses and generated content

### 2. Python Backend (FastAPI)
The intelligence layer that:
- Manages API keys securely
- Handles prompt engineering and context management
- Communicates with various AI services (LLM, Image Generation, TTS)
- Maintains AI turn/thread state
- Orchestrates multiple AI agents for different tasks

### 3. External APIs
The AI services that provide:
- Language models (GPT, Novel AI, etc.)
- Image generation (DALL-E, Stable Diffusion)
- Text-to-Speech/Speech-to-Text (ElevenLabs, Whisper)

## Implementation Phases

### Phase 1: The "Parrot" - Basic Communication
**Goal:** Establish basic LLM communication with Foundry chat
- Create Foundry UI window with input/output areas
- Implement basic "Take AI Turn" button
- Set up FastAPI backend with simple `/simple_chat` endpoint
- Display AI responses in both UI module and Foundry chat

### Phase 2: The "Observer" - Context-Aware Responses
**Goal:** Make AI responses relevant to the actual game situation
- Expand game state gathering (scenes, tokens, characters, journals, chat history)
- Add AI Role selection (DM, DM Assistant, Player)
- Implement sophisticated prompt engineering
- Create `/contextual_action` endpoint with rich context processing

### Phase 3: The "Actor" - Tool-Driven Actions
**Goal:** Allow AI to perform actions in the game world
- Implement LLM function calling/tool use
- Create `executeAction()` function in Foundry for various action types:
  - Dice rolling
  - Token movement
  - Actor health updates
  - Chat message creation
- Establish action-result communication loop

### Phase 4: The "Orchestrator" - Advanced Features
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
- **Action Log UI:** Lists every AI action with status and description
- **Undo/Redo/Retry:** Every action can be reversed or retried
- **Transparency:** Users can see exactly what the AI is doing and why

### Multi-Role Support
- **DM:** Full access to all tools and game controls
- **DM Assistant:** Limited to enemy control and assistance functions
- **Player:** Restricted to personal character actions only

### Variable Focus
Capable of doing everything from minimal GM assistance, emulating a player or players, to emulating a GM for a single player or group of playes, by restricting the AI's permissions.

## Technology Stack

### Frontend (Foundry VTT Module)
- JavaScript/ES6+
- Foundry VTT API
- Webpack for bundling
- CSS for styling

### Backend (Python)
- Flask for web framework with security-first configuration
- Universal Input Validation system with comprehensive protection
- Flask-CORS with environment-based origin restrictions
- HTTP clients for API integration
- Rate limiting and security headers
- Environment-based configuration management

### AI Services
- OpenAI API
- Novel AI API
- Locally-run models

## Development Setup

### Prerequisites
- Foundry VTT installation
- Python 3.8+
- Node.js 16+
- API keys for chosen AI services

### Installation
1. Clone this repository into Foundry's Modules folder
2. Set up Python backend with 'start-backend.py'
3. Start Foundry while backend is running
4. Enable plugin in Foundry world settings
5. Configure plugin through Foundry settings menu

### Configuration
- API keys configured through backend environment variables
- AI permissions and tool access controlled by role settings
- Custom prompts and behavior adjustable through configuration files

### 📋 Privacy & Security

**Important**: The Gold Box is designed with privacy-first principles. Your AI prompts and responses are **NOT logged** on the server side - only technical metadata for monitoring.

**Key Points:**
- ✅ **No Content Logging**: Your actual prompts and AI responses remain private
- ✅ **API Key Security**: Keys stored in environment variables only
- ✅ **Local Control**: You control server exposure and configuration
- ✅ **Rate Limiting**: Built-in protection against abuse

**For complete privacy details, see** `PRIVACY_NOTICE.md`

⚠️ **Server Security Notice**: When running in production mode, ensure proper CORS configuration and network security practices.

### 🔧 Server Configuration for Production

#### **Local Development (Default)**
```bash
# Works out-of-the-box for local FoundryVTT
./start-backend.py
```

#### **Production/Server Hosting**
Configure your FoundryVTT domain(s) for external access:

```bash
# For The Forge hosting
export CORS_ORIGINS="https://your-campaign.forge-vtt.com"
./start-backend.py

# For self-hosted domain
export CORS_ORIGINS="https://rpg.yourdomain.com"
./start-backend.py

# For multiple domains
export CORS_ORIGINS="https://foundry.yourdomain.com,https://backup.yourdomain.com"
./start-backend.py

# Development + production mix
export CORS_ORIGINS="http://localhost:30000,https://your-foundry-domain.com"
./start-backend.py
```

## Security Features

The Gold Box backend implements comprehensive security measures to ensure safe pre-alpha deployment:

### 🛡️ **Input Validation & Sanitization**
- **Universal Input Validator**: Comprehensive validation for all input types
- **Dangerous Pattern Detection**: Blocks XSS, SQL injection, command injection, path traversal
- **Character Set Enforcement**: Regex-based character validation per input type
- **Size Limits**: Prevents buffer overflow attacks
- **HTML Escaping**: Prevents XSS in displayed content

### 🔒 **API Security**
- **Rate Limiting**: Configurable request throttling (5 requests/minute default)
- **CORS Protection**: Environment-based origin whitelisting
- **API Key Authentication**: Secure key validation and format checking
- **Security Headers**: X-Content-Type-Options, X-Frame-Options, X-XSS-Protection

### 🚀 **Environment-Based Configuration**
- **Development Mode**: Localhost-only origins with relaxed settings
- **Production Mode**: Explicit origin configuration required
- **Fail-Safe Approach**: No access unless explicitly configured

### 📊 **Monitoring & Logging**
- **Comprehensive Logging**: All security events logged with client IP
- **Validation Error Reporting**: Step-by-step failure identification
- **Health Endpoints**: Service status and security configuration monitoring

## Contributing

This project is currently under active development. Contributions are welcome, especially in:
- Additional AI service integrations
- New tool implementations for Foundry VTT
- Improved prompt engineering
- UI/UX enhancements

## License

This project is licensed under the Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International Public License. See the [LICENSE](LICENSE) file for details.

## Roadmap

- [ ] Phase 0: Minimal security configuration
- [ ] Phase 1: Basic LLM communication
- [ ] Phase 2: Context-aware responses
- [ ] Phase 3: Tool-driven actions
- [ ] Phase 4: Multi-modal orchestration
