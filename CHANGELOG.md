# Changelog

All notable changes to The Gold Box project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0/).

## [0.3.10] - 2026-01-05

### Major Release: The Combatant

#### Added
- **Combat Encounter Management**: AI can create and delete combat encounters using Foundry's native API
- **Turn Management**: AI can advance combat turns to move through initiative order
- **Actor Details Query**: AI can retrieve detailed stat blocks for token-specific actor instances with grep-like search functionality
- **Token Attribute Management**: AI can modify any token attribute (damage, healing, absolute values) system-agnostically
- **Enhanced Delta Tracking**: Tracks turn advances and any token attribute changes between AI turns
- **Local Model Support**: Automatic detection and authentication bypass for local providers (Ollama, vLLM, LM Studio, etc.)
- **Enhanced Model Name Validation**: Expanded regex to support colons and slashes in model names (e.g., `qwen3:14b`, `openrouter/anthropic/claude-3`)
- **Prompt Engineering Efficiency**: Added batching guidance to tool descriptions and role prompts

#### Changed
- **Tool Descriptions**: All tools now include efficiency instructions for batching operations
- **Provider Configuration**: Added `requires_auth` and `provider_type` fields to all providers
- **LiteLLM Provider List**: Synchronized with 103 total providers (removed 18 outdated, added 48 new)

#### Fixed
- **Combat Creation Error Handling**: Duplicate combat creation now returns immediate error instead of 30s timeout
- **Context Parameter Bug**: Fixed "name 'context' is not defined" error in unified message processor

#### Migration Notes
- Existing provider configurations work automatically with new fields
- Local providers no longer require dummy API keys
- Backward compatible - all existing features work unchanged

---

## [0.3.9] - 2025-12-30

### Major Release: The Foundation

#### Added
- **Dice Rolling**: AI can execute dice rolls in Foundry with flavor text support
- **Combat Status Queries**: AI can query current combat state and encounter information
- **Enhanced Delta Tracking**: Smart filtering of game state changes with full JSON deltas when changes detected
- **Initial Context System**: First turn provides complete world state; subsequent turns provide deltas only
- **World State Synchronization**: Frontend sends session info, party compendium, active scene, and compendium index to backend
- **Testing Infrastructure**: Comprehensive test suite with automated validation scripts

#### Changed
- **Tool Names**: `get_messages` → `get_message_history`, `post_messages` → `post_message`
- **Connection Stability**: Increased health check timeout to 5s, fixed WebSocket port discovery, added race condition protection
- **AI Turn Button**: Complete rewrite with 3-state machine (DISCONNECTED, CONNECTED, THINKING) with auto-reconnection
- **Logging**: Reduced logspam with consolidated combat state logging, DEBUG-level tool availability, consolidated roll results

#### Fixed
- **Combat State Transmission**: Removed automatic combat_state transmissions to reduce unnecessary logging
- **Settings Sync**: Added handler for `settings_sync_response` messages
- **Deprecated Settings**: Removed all references to deprecated `maxMessageContext` setting

#### Breaking Changes
- Tool name changes affect API compatibility
- Initial context format now includes all world state fields when available
- Delta format uses `hasChanges` flag to determine JSON vs text message format

#### Migration Notes
- Automatic upgrade - existing installations adapt to new tool names
- No manual migration required
- Enhanced context uses world_state if available, falls back to placeholders

---

## [0.3.8] - 2025-12-26

### Added
- **Testing Harness**: Complete mock AI service for testing without API costs
- **Test Commands**: `start_test_session`, `test_command`, `end_test_session`, `list_test_sessions`, `get_test_session_state`
- **Simplified Syntax**: Easy-to-use commands for get_messages, post, tool calls, stop, status
- **Session Management**: Unique test sessions with isolation and expiration (1 hour)
- **Documentation**: Comprehensive testing guide and helper scripts

---

## [0.3.7] - 2025-12-25

### Added
- **AI-Native Function Calling**: Industry-standard OpenAI function calling format with multi-turn workflow
- **Tool Definitions**: `get_message_history` and `post_message` tools for AI control
- **Automatic Tool Execution Loop**: Backend manages function calls until AI signals completion
- **Frontend Delta Tracking**: Real-time tracking of new/deleted messages with injection into system prompt
- **WebSocket Progress Messages**: Real-time notifications of tool execution for debugging

#### Changed
- **Initial Prompt Format**: Function calling mode sends system + role only (no message context initially)
- **Settings**: `maxHistoryTokens` replaces "Maximum Message Context" (default: 5000 tokens)
- **Message Labeling**: All AI messages include "The Gold Box AI" subtitle via Foundry hook

#### Breaking Changes
- AI must call `get_message_history` tool instead of receiving pre-collected context
- Settings migration to `maxHistoryTokens` automatic

---

## [0.3.6] - 2025-12-24

### Added
- **Conversation History Management**: Full history storage in OpenAI format with token-based pruning
- **Memory Configuration**: User-configurable limits for tokens, message count, and time-based expiration
- **Enhanced Context Assembly**: Combines conversation history with delta-filtered new messages
- **Automatic Memory Cleanup**: Configurable time and count limits with automatic expiration

#### Default Memory Limits
- 5000 tokens (configurable)
- 50 messages (configurable)
- 24 hours (configurable)

---

## [0.3.5] - 2025-12-18

### Added
- **Dynamic Chat Card Translation**: Game-agnostic field discovery and algorithmic code generation
- **Combat-Aware AI Prompts**: Context-aware instructions based on combat state with turn order
- **AI Thinking Transparency**: AI reasoning displayed as GM whispers in Foundry chat
- **Advanced Post-Processing**: Pattern consolidation and duplicate value abbreviation for 90% token reduction
- **Combat Integration**: Automatic combat detection with tactical LLM support

#### Changed
- Chat card codes generated dynamically instead of using static mappings
- System prompts include combat context and dynamic field definitions

---

## [0.3.4] - 2025-12-14

### Major Architecture Refactor

#### Added
- **Service Factory Pattern**: Dependency injection system for service management
- **Service Registry**: Centralized service access patterns
- **Unified WebSocket Architecture**: Native FastAPI WebSocket support (removed relay server)
- **Shared Component Library**: Common functionality extracted to shared modules
- **Enhanced Startup System**: Comprehensive initialization and validation

#### Changed
- **Backend Structure**: Reorganized into api/, services/, shared/ directories
- **Frontend Services**: Separated connection manager, session manager, settings manager
- **Communication**: Direct WebSocket communication replaces relay server

#### Breaking Changes
- All service imports now use factory pattern and registry
- Removed relay server dependency
- Module structure significantly changed

#### Migration Notes
- Services accessed through `get_service_name()` functions
- Settings accessed through universal settings manager
- Direct WebSocket replaces relay server communication

---

## [0.3.3] - 2025-12-06

### Added
- **Service Factory Pattern**: Centralized service management with dependency injection
- **Unified Message Processor**: Consolidated message processing component
- **WebSocket-Only Communication**: Complete removal of relay server dependencies

#### Changed
- **Processing Modes**: Reduced from 4 to 2 modes: "API (recommended)" and "Context (unfinished)"
- **Default Mode**: New installations default to "API" mode
- **API Mode**: Enhanced WebSocket communication with structured AI responses

#### Breaking Changes
- `/api/simple_chat` and `/api/process_chat` endpoints deprecated
- Existing "Simple" or "Processed" mode users switched to "API" mode

#### Migration Notes
- Automatic upgrade - no action required
- Users may need to re-select "API (recommended)" mode if using deprecated modes

---

## [0.3.2] - 2025-11-28

### Added
- **Context Chat Endpoint**: Complete board state integration for AI processing
- **System-Agnostic Attribute Mapping**: Dynamic detection and coding of arbitrary game system attributes
- **Complete Board State Collection**: Scene data, walls, lighting, tokens, templates, map notes
- **Token-Efficient Format**: Optimized JSON reducing token usage by 90%+

#### Changed
- **Context Processing Mode**: New "Context (unfinished)" option in settings
- **Button Text**: Changes to "AI Context Turn" in context mode

#### Fixed
- **Module Name Issue**: Corrected namespace inconsistency between `gold-box` and `the-gold-box`
- **Settings Storage**: Fixed frontend settings not being properly saved/retrieved
- **Mode Labels**: Enhanced clarity with "deprecated" and "recommended" indicators

---

## [0.3.1] - 2025-11-28

### Added
- **Context Chat Endpoint**: Complete board state integration for AI processing
- **System-Agnostic Attribute Mapping**: Dynamic detection and coding of arbitrary game system attributes
- **Complete Board State Collection**: Scene data, walls, lighting, tokens, templates, map notes
- **Token-Efficient Format**: Optimized JSON reducing token usage by 90%+

#### Changed
- **Context Processing Mode**: New "Context (unfinished)" option in settings
- **Button Text**: Changes to "AI Context Turn" in context mode

#### Fixed
- **Module Name Issue**: Corrected namespace inconsistency between `gold-box` and `the-gold-box`
- **Settings Storage**: Fixed frontend settings not being properly saved/retrieved
- **Mode Labels**: Enhanced clarity with "deprecated" and "recommended" indicators

---

## [0.3.0] - 2025-11-27

### Added
- **Foundry REST API Integration**: Complete integration with Foundry REST API
- **Relay Server Support**: Enhanced communication between components
- **Three Processing Modes**: Simple, Processed, and API modes
- **Submodule Architecture**: Foundry REST API and relay server as submodules
- **Auto-Discovery**: Automatic port discovery and connection management

#### Changed
- **Backend**: New `/api/api_chat` endpoint for REST-based message collection
- **Frontend**: API bridge integration and enhanced settings menu

#### Breaking Changes
- Requires git submodule initialization for full functionality
- Relay server requires Node.js and npm for API chat mode
- Some configuration options may have moved

---

## [0.2.5] - 2025-11-23

### Added
- **Modular Architecture**: Complete backend reorganization into logical directories
- **Security Module**: Separated security components into dedicated modules
- **Centralized Configuration**: Consolidated security and server configuration
- **Enhanced Security Framework**: Universal security middleware, session validator, persistent rate limiting

#### Changed
- **Directory Structure**: backend/security/, backend/endpoints/, backend/server/
- **Input Validation**: Multi-level system with HTML-safe modes for Foundry VTT compatibility
- **Chat Context Processor**: Token-efficient message format (90-93% reduction)

#### Breaking Changes
- Chat endpoints now require session initialization and CSRF tokens
- Some configuration files moved to new locations

---

## [0.2.4] - 2025-11-21

### Added
- **Phase One Completion**: Successfully completed first phase of development roadmap
- **Documentation Updates**: Streamlined project documentation

---

## [0.2.3] - 2025-11-20

### Added
- **Full Chat History Context**: Automatic collection with configurable length (default: 15 messages)
- **OpenCode Compatible API**: Full integration with Z.AI and similar services
- **Service Selection**: User-configurable LLM service selection
- **Multi-Service Architecture**: Support for OpenAI, NovelAI, OpenCode, and Local LLMs

#### Changed
- **simple_chat Endpoint**: Improved handling of message context

#### Fixed
- **JavaScript Syntax Errors**: Resolved all issues preventing module loading
- **Settings Menu**: Module settings now properly display
- **Chat Button**: "Take AI Turn" button appears and functions correctly
- **Content Display**: Resolved problems with AI response content not showing

---

## [0.2.2] - 2025-11-15

### Added
- **FastAPI Migration**: Migrated from Flask to FastAPI
- **Enhanced Security**: Comprehensive input validation and security headers
- **Admin Password System**: Password-protected admin operations
- **Key Management**: Encrypted API key storage
- **Session Management**: Configurable timeouts and automatic cleanup
- **Rate Limiting**: IP-based protection with configurable windows

---

## [0.2.1] - 2025-11-10

### Added
- **OpenAI Compatible API**: Full support for OpenAI and compatible services
- **NovelAI API Integration**: Specialized support for NovelAI services
- **Simple Chat Endpoint**: Basic chat interface for AI communication
- **Health Check System**: Basic server health monitoring
- **Environment Configuration**: Flexible environment-based settings
- **CORS Protection**: Environment-based origin restrictions

---

## [0.1.15] - 2025-11-05

### Added
- **Multi-Service API Key Storage**: Secure storage system for multiple AI services
- **Comprehensive Security Overhaul**: Pre-alpha safety improvements

---

## [0.1.14] through [0.1.10] - 2025-10-28 to 2025-11-03

### Fixed
- Module.json manifest validation and DOM selectors for Foundry VTT v13
- jQuery wrapper issues and JavaScript syntax errors
- "Take AI Turn" button functionality with proper DOM loading
- Duplicate prevention and FormApplicationV2 implementation
- Series of incremental stability improvements

---

## [0.1.9] through [0.1.6] - 2025-10-20 to 2025-10-26

### Changed
- Adapted to new Foundry VTT v13 DOM structure
- Fixed jQuery integration and button creation logic
- Implemented working ChatConsole UI pattern

---

## [0.1.5] through [0.1.1] - 2025-10-15 to 2025-10-19

### Added
- Initial Foundry VTT module structure and chat integration
- Basic UI framework and backend communication
- Core functionality, error handling, and configuration system

---

## [0.1.0] - 2025-10-10

### Added
- Project foundation and basic module structure
- Initial Foundry VTT integration and documentation setup

---

**Note**: This changelog covers significant user-facing changes. For detailed technical documentation, see ROADMAP.md (for planned features) and the archived plan files in `docs/archive/` (for implementation details of completed releases).
