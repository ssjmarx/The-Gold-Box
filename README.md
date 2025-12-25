# The Gold Box

An AI-powered Foundry VTT module that provides intelligent TTRPG assistance through a sophisticated Python backend. Currently chat-only, this plugin is being developed with the eventual goal of enabling fully single-player play of any adventure module in any TTRPG system supported by Foundry.

## Acknowledgments

This project would not be possible without the following:

- **Foundry Virtual Tabletop** - The excellent TTRPG platform that makes this integration possible
- **Foundry VTT REST API by ThreeHats** - Robust REST API integration for Foundry
- **GLM AI (Zhipu AI)** - Powerful AI models that drive this project
- **Visual Studio Code** - The excellent IDE used throughout development
- **Cline AI Assistant** - The AI assistant that helped write this codebase

## Features

- **AI-Powered TTRPG Assistant**: Intelligent responses that remember conversation history and context
- **Dynamic Chat Card Translation**: Game-agnostic field discovery and dynamic code generation for any Foundry module
- **Combat-Aware AI**: Context-aware instructions based on combat state with turn order awareness
- **Multi-Provider Support**: Connect to 70+ AI providers including OpenAI, Anthropic, GLM, and more
- **Secure Backend**: Encrypted API key storage with comprehensive security framework
- **Advanced Processing**: Token-efficient delta filtering and intelligent conversation history management

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

**Important**: DO NOT CLOSE THE TERMINAL WINDOW! The server must be running for the module to work.

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
   - **General LLM Provider**: Your AI service (e.g., openai, anthropic, openrouter).  Should be the same one you set up an API for with in the server.
   - **General LLM Model**: Your model (e.g., gpt-3.5-turbo, claude-3-5-sonnet-20241022, glm-4.6).  Should be one of the models supported by your provider as given by litellm, see: https://models.litellm.ai/
   - **Maximum Message Context**: Recent messages to include (default: 15)

### 4. Use in Game
Press the **"Take AI Turn"** button in the chat sidebar to send your conversation context to the AI and receive intelligent responses.

## Support

- **GitHub Issues**: [Report Issues](https://github.com/ssjmarx/The-Gold-Box/issues)
- **Detailed Usage Guide**: [USAGE.md](USAGE.md) - Advanced configuration and settings
- **Dependencies**: [DEPENDENCIES.md](DEPENDENCIES.md) - Complete dependency list
- **Changelog**: [CHANGELOG.md](CHANGELOG.md) - Version history and changes

## Donations

If you like the project and want to support future development, consider donating!

[![Donation Button](https://img.shields.io/badge/PayPal-00457C?style=for-the-badge&logo=paypal&logoColor=white)](https://www.paypal.com/donate/?business=NW7VGF3US6V8G&no_recurring=0&item_name=If+you+like+this+project+and+want+to+support+future+development.&currency_code=USD)

## License

This project is licensed under **Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International License**. See [LICENSE](LICENSE) file for details.

**Current Version: 0.3.6** - Full conversation history support with intelligent token management
