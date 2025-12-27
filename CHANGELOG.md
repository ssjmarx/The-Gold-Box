# Changelog

All notable changes to The Gold Box project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0/).

## [0.3.8] - 2025-12-26

### Testing Harness Implementation

#### Core Testing Infrastructure
- **Testing Session Manager** - Comprehensive session lifecycle management for test sessions
- **Testing Harness Service** - Mock AI service that acts as a stand-in for real AI during testing
- **Testing Command Processor** - Parses simplified curl commands and converts to AI tool calls
- **Admin Endpoint Integration** - Complete testing commands accessible via admin API

#### Testing Commands
- **start_test_session** - Initiate a test session for any client ID
- **test_command** - Send testing commands (get_messages, post_messages, tool calls)
- **end_test_session** - Terminate test session with summary statistics
- **list_test_sessions** - View all active test sessions
- **get_test_session_state** - Get detailed state of a specific test session

#### Simplified Command Syntax
- `get_messages [count]` - Retrieve chat messages (default: 15)
- `post "message content"` - Post simple chat message
- `post_messages <json>` - Post full message structure
- `tool_name param1=value1 param2=value2` - Call any AI tool
- `stop` - End testing session
- `status` - Show current test session state
- `help` - List available commands

#### Testing Features
- **Initial Prompt Generation** - Generates the same system prompt real AI would receive
- **Tool Execution in Test Mode** - All AI tools execute normally during testing
- **Conversation History Tracking** - Maintains conversation history for test sessions
- **Session Isolation** - Each test session has unique ID with no cross-contamination
- **Session Expiry** - Test sessions expire after 1 hour of inactivity
- **Audit Logging** - All test commands logged to security audit log

#### Security & Safety
- **Admin Authentication** - All test commands require admin password
- **Session Isolation** - Test sessions isolated from production data
- **Rate Limiting** - Test commands subject to same rate limits as admin endpoints
- **Security Headers** - Full security protection for all testing endpoints

#### Documentation & Tools
- **Testing Helper Scripts** - Bash scripts for common testing operations
- **Comprehensive Documentation** - Complete usage guide in TESTING.md
- **Example Test Scripts** - Pre-built examples for common testing scenarios
- **Curl Command Examples** - Detailed workflow examples in documentation

#### Service Integration
- **Service Factory Registration** - Testing services registered in ServiceRegistry
- **Startup Integration** - Automatic initialization of testing services
- **Dependency Injection** - Proper service lifecycle management

#### New Backend Services
- `backend/services/system_services/testing_session_manager.py` - Session management
- `backend/services/ai_services/testing_harness.py` - Testing harness service
- `backend/services/ai_services/testing_command_processor.py` - Command processor
- `backend/testing/test_harness_helpers.sh` - Helper scripts
- `backend/testing/TESTING.md` - Testing documentation

#### Updated Files
- `backend/api/admin.py` - Added testing command handlers
- `backend/services/system_services/service_factory.py` - Added service getters
- `backend/shared/startup/services.py` - Service registration
- `.gitignore` - Added test session ID files

#### Workflow Example
1. Start test session via admin endpoint with client ID
2. Receive initial prompt (same format as real AI would get)
3. Execute AI tools via simplified curl commands
4. View results in real-time in Foundry chat
5. End session with comprehensive summary

#### Benefits
- **No AI Service Dependency** - Test all AI functions without calling real AI
- **Rapid Iteration** - Test tool calls and workflows quickly
- **Cost Savings** - No API token usage during testing
- **Reproducible Testing** - Consistent test scenarios without AI variability
- **Full Functionality** - Test every AI tool with complete functionality

#### Testing Use Cases
- Basic tool testing (get_messages, post_messages)
- Combat scenario testing
- Multi-turn conversation testing
- Error handling testing
- Workflow validation
- Tool argument validation

#### Implementation Status
- ✅ Core testing infrastructure complete
- ✅ Admin endpoint integration complete
- ✅ Service factory integration complete
- ✅ Documentation complete
- ✅ Helper scripts complete
- 🔄 Ready for comprehensive testing and validation

## [0.3.7] - 2025-12-25

### Major Release: AI-Native Function Calling

#### Function Calling Architecture
- **AI-Native Tool Usage** - AI now uses tools to gather context and post responses instead of parsing free-form responses
- **Multi-Turn Function Calling Workflow** - AI can call multiple functions per turn, with each call and result appended to conversation history
- **Automatic Tool Execution Loop** - Backend manages function call loop until AI signals completion
- **OpenAI Function Calling Format** - Industry-standard format compatible with LiteLLM and multiple providers
- **Max Iterations Safeguard** - Configurable safety limit (default: 10 iterations) with graceful continuation

#### Tool Definitions
- **get_messages Tool** - AI retrieves recent chat messages from Foundry on-demand
  - Fresh data collection without delta filtering
  - Configurable message count (1-50, default: 15)
  - Returns compact JSON with type codes, abbreviations, schemas, and dynamic field definitions
  - No caching - always returns fresh data based on AI's count parameter
  
- **post_messages Tool** - AI sends chat messages or chat cards to Foundry
  - Accepts both compact JSON and full Foundry API format
  - Supports multiple messages in single call
  - Automatic format conversion as needed

#### AI Service Enhancements
- **AIOrchestrator Service** - New service dedicated to managing function call workflow
- **Function Calling Support in AIService** - Added `tools` parameter to `call_ai_provider()` for LiteLLM integration
- **Tool Call Parsing** - Handles multiple `tool_calls` per response from AI providers
- **Conversation History Integration** - All tool calls and results stored in conversation history via AISessionManager

#### Service Factory Integration
- **Tool Definitions Registration** - Tool schemas registered in ServiceRegistry during startup
- **AI Tool Executor Service** - New service for executing individual tools
- **AI Orchestrator Factory Function** - `get_ai_orchestrator()` for consistent service access
- **Tool Executor Factory Function** - `get_ai_tool_executor()` for consistent service access
- **Service Lifecycle Management** - Proper registration order during server startup

#### API Endpoint Updates
- **Dual Mode Operation** - `/api/api_chat` supports both function calling mode and backward compatibility mode
- **Function Calling Mode Flow**:
  - Initial prompt sends only system prompt + role instructions (no message context)
  - AI decides to call get_messages tool to gather context
  - Backend manages tool execution loop internally
  - AI signals completion via `finish_reason = "stop"` or empty `tool_calls` array
- **Completion Signals** - Response includes `ai_turn_complete` and `reached_limit` flags for frontend
- **Graceful Continuation** - When max iterations reached, work preserved and user can continue

#### Frontend Delta Tracking
- **Frontend Delta Service** - New service tracks new/deleted messages since last AI turn
- **Foundry Hooks Integration** - Hooks on `createChatMessage` and `deleteChatMessage` for real-time tracking
- **Delta Display in System Prompt** - AI informed of message changes: `[New Messages: X, Deleted Messages: Y]`
- **Counter Reset on Completion** - Delta counts reset when AI turn completes
- **Function Calling Mode Only** - Delta tracking for function calling mode; standard mode uses backend delta service

#### Settings Management
- **Enable Function Calling Toggle** - Frontend setting to enable/disable function calling (default: enabled)
  - Allows users to disable for providers that don't support function calling
  - Backward compatibility mode available when disabled
- **maxHistoryTokens Setting** - Replaced "Maximum Message Context" with token-based limit
  - Controls conversation history size (default: 5000 tokens)
  - Integrated with AISessionManager for automatic pruning
- **Memory Settings Group** - Centralized memory configuration with validation

#### Frontend Message Handling
- **Foundry Hook for Subtitle Override** - `renderChatMessageHTML` hook sets subtitle to "The Gold Box AI"
- **isAIMessage Flag** - All AI-generated messages include flag for hook identification
- **Speaker Name Preservation** - AI-provided speaker name shown as title, "The Gold Box AI" as subtitle
- **Native Foundry Rendering** - Does not break dice rolls or chat card rendering

#### WebSocket Progress Messages
- **New Message Types** - `TYPE_TOOL_CALL` and `TYPE_TOOL_RESULT` for progress feedback
- **Real-time Updates** - Frontend receives notifications of tool execution
- **Debugging Support** - Tool results sent to frontend for logging and debugging

#### Architectural Improvements
- **Single Source of Truth** - All services accessed via ServiceFactory pattern
- **Separation of Concerns**:
  - AIService: Focus on API calls to providers
  - AIOrchestrator: Manage tool calling workflow
  - AIToolExecutor: Execute individual tools
- **Client ID Flow** - Transient client_id explicitly passed through API → Orchestrator → Executor → MessageCollector
- **OpenAI vs Compact JSON Format** - Clear distinction: conversation history uses OpenAI format, tool results contain compact JSON data

#### Error Handling
- **Tool Execution Errors** - Failures returned as error results in conversation for AI to handle
- **Max Iterations Recovery** - Graceful continuation without losing work
- **Invalid Tool Arguments** - Validation with descriptive error messages
- **Network Timeout Handling** - Proper timeout handling during tool execution

#### Testing & Validation
- **Unit Tests for Tools** - get_messages and post_messages with various parameters
- **Function Call Loop Tests** - Single and multiple tool calls, max iterations, conversation history
- **Integration Tests** - Full workflow from initial prompt to completion
- **Backward Compatibility Tests** - Verify old behavior when function calling disabled
- **Performance Tests** - Token usage, response time, large conversation histories

#### Breaking Changes
- **Initial Prompt Format** - Function calling mode sends system + role only (no message context initially)
- **Tool-Based Context Retrieval** - AI must call get_messages tool instead of receiving pre-collected context
- **Settings Migration** - "Maximum Message Context" replaced with "maxHistoryTokens" (defaults to 5000 tokens)

#### Migration Notes
- **Automatic Upgrade** - Existing installations will automatically use function calling mode
- **Provider Compatibility** - Most modern providers support function calling; older providers can use backward compatibility mode
- **Settings Update** - "maxHistoryTokens" automatically set to 5000 tokens (approximately equivalent to previous 15 messages)
- **No Data Loss** - Conversation history and session management work as before

#### New Files
- `backend/services/ai_tools/__init__.py`
- `backend/services/ai_tools/ai_tool_definitions.py`
- `backend/services/ai_tools/ai_tool_executor.py`
- `backend/services/ai_services/ai_orchestrator.py`
- `scripts/services/frontend-delta-service.js`

#### Modified Files
- `backend/services/ai_services/ai_service.py` - Added tools parameter support
- `backend/services/ai_services/ai_session_manager.py` - Token limit integration
- `backend/api/api_chat.py` - Dual mode operation, function calling integration
- `backend/services/system_services/service_factory.py` - Added get_ai_orchestrator() and get_ai_tool_executor()
- `backend/shared/startup/startup.py` - Tool services registration
- `scripts/api/backend-communicator.js` - Frontend handling of completion signals
- `scripts/api/websocket-client.js` - Delta tracking integration
- `scripts/shared/ui-manager.js` - Added isAIMessage flag to all ChatMessage.create() calls
- `scripts/gold-box.js` - Foundry renderChatMessageHTML hook registration
- `backend/shared/core/message_protocol.py` - New tool call message types

## [0.3.6] - 2025-12-24

### Major Release: Full Conversation History Support

#### Conversation History Management
- **Enhanced AI Session Manager** - Complete conversation history storage in OpenAI format for AI compatibility
- **Token-Based Memory Management** - Configurable token limits with intelligent pruning (default: 5000 tokens)
- **Smart Context Assembly** - Combines conversation history with delta-filtered new messages for optimal AI responses
- **Automatic Memory Cleanup** - Configurable time-based and count-based limits with automatic expiration

#### Memory Configuration
- **User-Configurable Limits** - Backend supports memorySettings for token, message count, and time limits
- **Default Token Limit** - 5000 tokens (configurable via maxHistoryTokens)
- **Message Count Limits** - Optional maxHistoryMessages setting (default: 50 messages)
- **Time-Based Expiration** - Optional maxHistoryHours setting (default: 24 hours)
- **Settings Validation** - FrontendSettingsHandler validates memory settings structure

#### Enhanced Delta Service
- **get_enhanced_context() Method** - Combines conversation history with new delta-filtered messages
- **Improved Timestamp Normalization** - Supports both 'ts' (compact format) and 'timestamp' (legacy format)
- **Critical Timestamp Fix** - No longer overwrites AI response timestamps with user message timestamps
- **Better Context Logging** - Detailed logging of history + new message counts

#### AI Service Integration
- **Direct History Access** - AI Service calls get_conversation_history() with token pruning
- **Conversation Message Storage** - Both user messages and AI responses stored in history
- **Timestamp Management** - Session timestamp updated only when AI responses are stored
- **OpenAI Format Messages** - Messages stored in standard OpenAI format for provider compatibility

#### Session Management Enhancements
- **add_conversation_message()** - Store messages in conversation history
- **get_conversation_history()** - Retrieve history with configurable limits
- **prune_by_tokens()** - Remove oldest messages when token limit exceeded
- **clear_conversation_history()** - Clear history for session
- **get_session_info()** - Get session statistics including history metrics

#### Backend Services Updated
- **AISessionManager** - Added conversation history storage and retrieval methods
- **MessageDeltaService** - Enhanced with get_enhanced_context() and improved timestamp handling
- **FrontendSettingsHandler** - Added validation for memorySettings structure
- **AIService** - Integrated conversation history with process_compact_context()

#### Technical Improvements
- **Token Estimation** - Rough estimation (~4 characters per token) for memory management
- **System Message Preservation** - System messages preserved during token pruning
- **Automatic Cleanup** - Auto-cleanup triggered during session operations
- **Memory Statistics** - Session info includes conversation history metrics

#### Backend Configuration
- **Default Memory Limits** - 50 messages, 24 hours, 5000 tokens (configurable)
- **Session Timeout** - 2 weeks (20160 minutes) unchanged
- **Cleanup Interval** - 10 minutes for automatic session and history cleanup

#### API Changes
- **Session Management** - Sessions now track conversation history alongside timestamps
- **Context Assembly** - AI receives full conversation context within token limits
- **Memory Efficiency** - Delta filtering still applies to new messages for token savings

#### Future Enhancements
- Frontend UI for memory configuration
- User-accessible clear history functionality
- Memory usage statistics display
- Session monitoring dashboard

#### Migration Notes
- **Automatic Upgrade** - Existing installations will automatically support conversation history
- **No Settings Changes Required** - Default memory limits apply automatically
- **Backward Compatible** - Delta filtering and session management work as before
- **Enhanced AI Responses** - AI now has full conversation context within token limits

## [0.3.5] - 2025-12-18

### Major AI Enhancement Release
- **Dynamic Chat Card Translation System** - Complete overhaul of chat card processing with game-agnostic field discovery and dynamic code generation
- **Combat-Aware AI Prompts** - AI now receives context-aware instructions based on combat state with dynamic prompt generation
- **AI Thinking Extraction** - AI reasoning process is extracted and displayed as GM whispers in Foundry for transparency
- **Chat Card Post-Processing** - Advanced optimization with pattern consolidation and duplicate value abbreviation for token efficiency
- **Combat Detection Integration** - System detects combat encounters and provides turn order context to AI for tactical responses

#### Dynamic Chat Card Translation System
- **Game-Agnostic Field Discovery** - System dynamically identifies ALL fields in chat cards without hard-coded game system patterns
- **Universal Attribute Mapping** - Pure algorithmic code generation using `SimpleAttributeMapper` for any Foundry module or game system
- **Bidirectional Translation** - Seamless conversion between Foundry HTML and compact JSON format with full data fidelity
- **Comprehensive Field Extraction** - Captures pills, roll data, effects, enchantments, data attributes, and nested structures
- **Real-Time Schema Generation** - Dynamic system prompt updates with discovered field definitions and examples
- **Context-Aware Code Generation** - Generates meaningful attribute codes based on card type, field patterns, and semantic grouping

#### Combat-Aware AI System
- **Combat Encounter Detection** - Automatic detection of combat state through Foundry combat event monitoring
- **Turn Order Context** - AI receives current turn order, initiative values, and whose turn it is during combat
- **Dynamic Prompt Templates** - Three distinct prompt types for no combat, player turn, and NPC group turn scenarios
- **Tactical LLM Integration** - Support for combat-specific AI models when configured
- **Turn-Based Instructions** - AI receives targeted guidance based on current combat phase and active combatants

#### AI Thinking Transparency
- **Reasoning Extraction** - Extracts AI's thinking process from LiteLLM responses across different providers
- **GM Whisper Display** - AI reasoning displayed as GM whispers in Foundry chat for full transparency
- **Multi-Provider Support** - Compatible with reasoning content from OpenAI, Anthropic, and other providers
- **Structured Thinking Format** - Consistent formatting for AI reasoning regardless of provider

#### Advanced Chat Card Processing
- **Universal Pattern Detection** - Regex-based detection of numbered field patterns (`field1`, `field2`, etc.) with array consolidation
- **Duplicate Value Optimization** - Identifies repeated values across cards and replaces with abbreviations (`@v1`, `@v2`, etc.)
- **Token Efficiency** - Significant reduction in token usage while maintaining complete data fidelity
- **Value Dictionary Management** - Message-level value reference for AI to access abbreviated content
- **Backward Compatibility** - Maintains compatibility with existing card formats while adding optimizations

#### Combat Integration Features
- **Frontend Combat Monitoring** - Local Foundry combat event tracking with on-demand state transmission
- **WebSocket Communication** - Combat state transmitted to backend only when AI turn is requested
- **NPC Group Processing** - Intelligent grouping of consecutive NPC turns for coordinated actions
- **Turn Sequence Analysis** - Determines next player combatant and NPC turn groups dynamically
- **Combat State Caching** - Efficient local caching with periodic synchronization

#### New Backend Services
- **`DynamicChatCardAnalyzer`** - Advanced HTML structure analysis and field pattern detection
- **`ChatCardTranslationCache`** - Lifecycle management for dynamic code mappings with cleanup
- **`ChatCardTranslator`** - Bidirectional translation engine with post-processing optimizations
- **`CombatEncounterService`** - Combat state management and turn order processing
- **`WhisperService`** - GM whisper creation and delivery for AI thinking display
- **`CombatPromptGenerator`** - Dynamic prompt generation based on combat state

#### Enhanced Processing Pipeline
- **Unified Message Collection** - Single WebSocket message workflow with combat state integration
- **Dynamic Schema Updates** - Real-time system prompt updates with discovered card structures
- **Post-Processing Optimizations** - Automatic pattern consolidation and value abbreviation
- **Cache Lifecycle Management** - Proper cleanup of translation caches after AI responses
- **Error Recovery** - Graceful fallbacks for unknown card structures and extraction failures

#### Breaking Changes
- **Dynamic Field Mappings** - Chat card codes are now generated dynamically rather than using static mappings
- **Enhanced AI Prompts** - System prompts now include combat context and dynamic field definitions
- **WebSocket Message Format** - Updated to include combat state and thinking extraction data
- **Processing Pipeline Changes** - Enhanced message collection with combat integration

#### Migration Notes
- **Automatic Code Generation** - No need to pre-define field mappings - system discovers and codes fields automatically
- **Combat Detection** - System automatically detects combat state without user configuration
- **Thinking Display** - AI reasoning appears as GM whispers and can be disabled if desired
- **Performance Improvements** - Token optimization reduces AI costs while maintaining functionality

#### Documentation Updates
- **Enhanced Feature Documentation** - Comprehensive documentation for new dynamic translation system
- **Combat Integration Guide** - Detailed setup and usage instructions for combat-aware features
- **AI Thinking Explanation** - Documentation of reasoning extraction and display system
- **Migration Guide** - Instructions for transitioning from static to dynamic field mappings

## [0.3.4] - 2025-12-14

### Major Architecture Refactor
- **Complete Module Reorganization** - Restructured entire backend into logical service-oriented architecture
- **Service Factory Pattern** - Implemented dependency injection system for service management and lifecycle
- **Service Registry** - Created centralized service registry for consistent service access patterns
- **Unified WebSocket Communication** - Moved to WebSocket-only architecture with native FastAPI WebSocket support
- **Shared Component Library** - Extracted common functionality into shared modules for code reuse

#### Backend Architecture Changes
- **API Layer (`backend/api/`)** - Consolidated all API endpoints into dedicated module
- **Services Layer (`backend/services/`)** - Organized into ai_services, message_services, and system_services
- **Shared Components (`backend/shared/`)** - Created shared library for core utilities, security, and providers
- **Startup System (`backend/shared/startup/`)** - Comprehensive initialization and validation system

#### Service Factory Implementation
- **Dependency Injection** - Automatic service instantiation and dependency management
- **Service Lifecycle Management** - Proper initialization, configuration, and cleanup
- **Consistent Access Patterns** - Standardized service retrieval through factory functions
- **Configuration Integration** - Services automatically receive configuration and security components

#### WebSocket Architecture
- **Native FastAPI WebSocket** - Removed relay server dependency, implemented direct WebSocket endpoint
- **Connection Management** - Centralized client connection and session management
- **Message Protocol** - Structured WebSocket message format for reliable communication
- **Real-time Communication** - Enhanced performance with direct server-client communication

#### Frontend Refactoring
- **Backend Communicator** - New unified WebSocket client for server communication
- **Separated Services** - Split connection manager, session manager, and settings manager
- **Message Collection** - Dedicated service for chat message collection and processing
- **UI Management** - Shared utilities for consistent user interface handling

#### Security and Configuration
- **Universal Settings** - Centralized configuration management across all services
- **Enhanced Key Management** - Improved API key storage and retrieval system
- **Security Integration** - Consistent security middleware across all endpoints
- **Validation Framework** - Comprehensive input validation and sanitization

#### Code Quality Improvements
- **Module Separation** - Clear separation of concerns across service boundaries
- **Import Optimization** - Updated all imports to use service registry and factory
- **Error Handling** - Standardized error handling and logging across services
- **Documentation Alignment** - Code structure now matches documentation

#### Breaking Changes
- **Import Changes** - All service imports now use factory pattern and registry
- **Configuration Updates** - Settings management moved to universal settings system
- **Endpoint Updates** - Deprecated endpoints removed in favor of WebSocket communication
- **Module Structure** - File organization significantly changed from previous versions

#### Migration Notes
- **Service Factory Usage** - All services now accessed through `get_service_name()` functions
- **Configuration Access** - Settings accessed through universal settings manager
- **WebSocket Communication** - Direct WebSocket replaces relay server communication
- **Shared Components** - Common functionality moved to shared modules

#### README.md Updates
- **Current File Structure** - Updated to reflect actual backend organization (api/, services/, shared/)
- **WebSocket Architecture** - Added WebSocket-only communication documentation
- **Processing Modes** - Updated to reflect current 2-mode system (API and Context)
- **Dependency Updates** - Removed Flask references, updated to FastAPI-only architecture
- **Installation Instructions** - Streamlined for simplified dependency requirements

#### USAGE.md Enhancements
- **FastAPI Configuration** - Replaced Flask configuration with FastAPI-specific settings
- **WebSocket Settings** - Added WebSocket communication configuration options
- **Service Factory Pattern** - Documented new dependency injection system
- **Universal Settings** - Added comprehensive settings management documentation
- **Real-time Sync** - Documented new data synchronization features
- **Removed Relay References** - Eliminated deprecated relay server documentation

#### Testing Structure Reorganization
- **Testing Folder Created** - Moved testing documentation to dedicated `backend/testing/` folder
- **Comprehensive Test Script** - Added runnable `comprehensive_test.sh` with automated testing
- **Updated Documentation** - All references now point to new testing folder structure
- **WebSocket Testing** - Added WebSocket connection and communication tests
- **API Chat Tests** - Added comprehensive tests for primary chat endpoint
- **Security Feature Tests** - Updated for current security framework
- **Removed Deprecated Tests** - Eliminated tests for removed endpoints

#### Technical Documentation
- **Unified Message Processor** - Documented central message processing component
- **Service Factory** - Added documentation for new service management pattern
- **Client Management** - Documented WebSocket client lifecycle management
- **Message Protocol** - Added WebSocket message format specification
- **Real-time Features** - Documented new synchronization capabilities

## [0.3.3] - 2025-12-06

### Major Release: Unified Architecture & Code Cleanup

#### Architecture Unification
- **Service Factory Pattern** - Implemented centralized service management with dependency injection
- **Unified Message Processor** - Consolidated all message processing into single component
- **WebSocket-Only Communication** - Complete removal of relay server dependencies
- **Shared Components** - Created shared library for common functionality across services
- **Enhanced Startup System** - Comprehensive startup validation and service initialization

#### Codebase Streamlining
- **Deprecated Endpoint Removal** - Completely removed "Simple" and "Processed" chat endpoints and all associated code
- **Simplified Processing Modes** - Reduced from 4 modes to 2: "API (recommended)" and "Context (unfinished)"
- **Cleaned Up Legacy Code** - Removed ~50% of chat processing code that was no longer needed
- **Updated Default Settings** - Changed default processing mode from 'simple' to 'api' for new installations

#### API Mode Enhancement
- **WebSocket Integration** - Enhanced WebSocket communication with real-time message exchange
- **Structured AI Responses** - Added support for chat messages, dice rolls, and interactive cards
- **Clear AI Labeling** - All AI-generated content now clearly labeled as "The Gold Box"
- **Improved Error Handling** - Better error messages and fallback mechanisms
- **Current API Compliance** - Updated to use latest Foundry VTT API without deprecation warnings

#### Backend Cleanup
- **Removed Deprecated Files** - Deleted legacy endpoint files
- **Updated Server Configuration** - Removed imports and router registration for deprecated endpoints
- **Helpful Error Messages** - Deprecated endpoints now return 501 errors directing users to API endpoint
- **Maintained Backward Compatibility** - Existing installations gracefully handle endpoint deprecation

#### Frontend Updates
- **Settings Menu Refinement** - Updated chat processing mode options to reflect current state
- **Button Text Logic** - Dynamic button text updates for remaining modes
- **Removed Fallback Code** - Eliminated code paths that referenced deprecated endpoints
- **Enhanced User Experience** - Clearer mode labels and recommended option highlighting

#### Documentation Updates
- **README.md Overhaul** - Updated with current feature set and streamlined instructions
- **USAGE.md Enhancement** - Comprehensive environment variable documentation
- **Release Preparation** - All documentation updated for production release
- **Professional Presentation** - Clean and clear documentation without deprecated references

#### Technical Improvements
- **Codebase Reduction** - Significant reduction in complexity and maintenance burden
- **Performance Optimization** - Faster startup and reduced memory footprint
- **Future-Proof Foundation** - Clean codebase for continued development
- **Testing Validation** - Verified all functionality works with streamlined architecture

#### Breaking Changes
- **Deprecated Endpoints** - `/api/simple_chat` and `/api/process_chat` no longer functional
- **Default Mode Change** - New installations default to "API (recommended)" mode
- **Settings Migration** - Existing "Simple" or "Processed" mode users will be switched to "API" mode
- **Reduced Complexity** - Simplified configuration options for easier user experience

#### Migration Instructions
- **No Action Required** - Existing installations will automatically adapt to new architecture
- **Settings Update** - Users may need to re-select "API (recommended)" mode if using deprecated modes
- **Clear Documentation** - All guides updated to reflect current system state

### Backend WebSocket Implementation
- **FastAPI WebSocket Endpoint** - Native `/ws` endpoint for real-time communication
- **WebSocket Connection Manager** - Built-in connection handling and client management
- **Message Protocol Handler** - Structured message processing for chat requests
- **Automatic Reconnection** - Robust connection recovery and error handling
- **Client ID Management** - Persistent client identification and session tracking

### Frontend WebSocket Client
- **New WebSocket Client Class** - `GoldBoxWebSocketClient` for direct backend communication
- **Connection State Management** - Real-time connection status and health monitoring
- **Fallback Mechanism** - Automatic fallback to HTTP API when WebSocket unavailable
- **Message Protocol Support** - Structured message format for reliable communication
- **Integration with Existing Systems** - Seamless replacement for relay server functionality

### Module Dependency Cleanup
- **Removed Gold API Requirement** - Eliminated "foundryvtt-gold-api" dependency
- **Removed API Bridge** - No longer loads `api-bridge.js` script
- **Zero External Dependencies** - Module now requires only core Foundry VTT
- **Standalone Installation** - Simplified setup without external modules
- **Reduced Installation Complexity** - Single module installation process

### Technical Improvements
- **Enhanced Performance** - Direct WebSocket communication reduces latency
- **Better Reliability** - Native WebSocket handling more stable than relay server
- **Simplified Debugging** - Direct communication paths easier to troubleshoot
- **Reduced Resource Usage** - No longer running separate Node.js relay server
- **Cleaner Codebase** - Removed legacy relay server integration code

### Breaking Changes
- **Relay Server No Longer Supported** - Existing relay server installations will be ignored
- **Gold API Module Not Required** - Can be safely uninstalled from Foundry
- **Simplified Module Structure** - Some configuration options may have moved

### Migration Instructions
- **Uninstall Gold API Module** - Safely remove "foundryvtt-gold-api" from Foundry
- **Delete Relay Server** - Remove any existing relay server installations
- **No Configuration Changes Required** - Existing settings automatically migrate
- **Restart Foundry VTT** - Required for module dependency changes to take effect

### Testing & Validation
- **End-to-End WebSocket Testing** - Verified complete communication workflow
- **Fallback Mechanism Testing** - Confirmed HTTP API fallback works correctly
- **Dependency Testing** - Validated standalone operation without external modules
- **Performance Benchmarking** - Measured improved response times with direct WebSocket
- **Compatibility Testing** - Verified with existing Foundry VTT installations

## [0.3.2] - 2025-11-28

### Major New Feature: Context Chat Implementation
- **New `/api/context_chat` Endpoint** - Complete board state integration for AI processing
- **System-Agnostic Attribute Mapping** - Dynamic detection and coding of arbitrary game system attributes
- **Complete Board State Collection** - Scene data, walls, lighting, tokens, templates, and map notes
- **Mechanical Code Generation** - Pure algorithmic attribute code generation without semantic assumptions
- **Universal Game System Support** - Works with D&D, Pathfinder, Call of Cthulhu, Savage Worlds, and any custom system
- **Enhanced AI Prompts** - Dynamic system prompt generation with attribute code dictionaries
- **Token-Efficient Data Format** - Optimized JSON representation reducing token usage by 90%+

### New Backend Components
- **Context Processor (`backend/server/context_processor.py`)** - Core logic for board state transformation
- **Simple Attribute Mapper (`backend/server/simple_attribute_mapper.py`)** - Dynamic attribute code generation
- **Board Collector (`backend/server/board_collector.py`)** - Complete board state gathering
- **Dice Collector (`backend/server/dice_collector.py`)** - Combined chat and dice message collection
- **JSON Optimizer (`backend/server/json_optimizer.py`)** - Token-efficient data compression
- **AI Prompt Validator (`backend/server/ai_prompt_validator.py`)** - Data quality validation before AI processing

### Frontend Integration
- **Context Processing Mode** - New "Context (unfinished)" option in chat processing settings
- **Context-Aware Button Text** - Button changes to "AI Context Turn" when in context mode
- **Enhanced Response Display** - Shows context elements, attributes mapped, and compression stats
- **Scene ID Integration** - Automatically detects current scene for board state collection
- **Relay Server Integration** - Uses existing Foundry REST API infrastructure for data collection

### Technical Architecture
- **Modular Endpoint Design** - Clean separation between context collection and AI processing
- **Universal Settings Integration** - Uses backend storage for configuration management
- **Error Handling & Validation** - Comprehensive data quality validation before AI processing
- **Relay Server Communication** - Leverages existing relay server for Foundry data access
- **AI Response Processing** - Converts AI responses back to Foundry chat format

### Critical Bug Fixes
- **Fixed "Unmapped" Module Name Issue** - Corrected namespace inconsistency between `gold-box` and `the-gold-box` in settings registration
- **Resolved Settings Storage Problems** - Fixed frontend settings not being properly saved and retrieved due to namespace mismatch
- **Enhanced Processing Mode Labels** - Updated chat processing mode labels for better user clarity:
  - "Simple (deprecated)" - Clearly marks legacy mode
  - "Processed (deprecated)" - Indicates deprecated processing mode  
  - "API (recommended)" - Highlights recommended current mode
  - "Context (unfinished)" - Indicates experimental mode status (now implemented)

### Technical Improvements
- **Namespace Consistency** - Standardized all module references to use `the-gold-box` throughout the codebase
- **Settings Registration Fix** - Corrected all `game.settings.register()` calls to use proper module namespace
- **Settings Retrieval Fix** - Fixed all `game.settings.get()` calls to use consistent namespace
- **Professional Documentation** - Removed all emojis from project documentation for professional presentation

### Documentation Updates
- **Comprehensive Changelog** - Added detailed v0.3.2 feature notes with technical implementation details
- **Version Tracking** - Updated version number in module.json for proper version management
- **Professional Presentation** - Cleaned documentation while preserving comprehensive content

## [0.3.1] - 2025-11-28

### Major New Feature: Context Chat Implementation
- **New `/api/context_chat` Endpoint** - Complete board state integration for AI processing
- **System-Agnostic Attribute Mapping** - Dynamic detection and coding of arbitrary game system attributes
- **Complete Board State Collection** - Scene data, walls, lighting, tokens, templates, and map notes
- **Mechanical Code Generation** - Pure algorithmic attribute code generation without semantic assumptions
- **Universal Game System Support** - Works with D&D, Pathfinder, Call of Cthulhu, Savage Worlds, and any custom system
- **Enhanced AI Prompts** - Dynamic system prompt generation with attribute code dictionaries
- **Token-Efficient Data Format** - Optimized JSON representation reducing token usage by 90%+

### New Backend Components
- **Context Processor (`backend/server/context_processor.py`)** - Core logic for board state transformation
- **Simple Attribute Mapper (`backend/server/simple_attribute_mapper.py`)** - Dynamic attribute code generation
- **Board Collector (`backend/server/board_collector.py`)** - Complete board state gathering
- **Dice Collector (`backend/server/dice_collector.py`)** - Combined chat and dice message collection
- **JSON Optimizer (`backend/server/json_optimizer.py`)** - Token-efficient data compression

### Frontend Integration
- **Context Processing Mode** - New "Context (unfinished)" option in chat processing settings
- **Context-Aware Button Text** - Button changes to "AI Context Turn" when in context mode
- **Enhanced Response Display** - Shows context elements, attributes mapped, and compression stats
- **Scene ID Integration** - Automatically detects current scene for board state collection
- **Relay Server Integration** - Uses existing Foundry REST API infrastructure for data collection

### Technical Architecture
- **Modular Endpoint Design** - Clean separation between context collection and AI processing
- **Universal Settings Integration** - Uses backend storage for configuration management
- **Error Handling & Validation** - Comprehensive data quality validation before AI processing
- **Relay Server Communication** - Leverages existing relay server for Foundry data access
- **AI Response Processing** - Converts AI responses back to Foundry chat format

### Critical Bug Fixes
- **Fixed "Unmapped" Module Name Issue** - Corrected namespace inconsistency between `gold-box` and `the-gold-box` in settings registration
- **Resolved Settings Storage Problems** - Fixed frontend settings not being properly saved and retrieved due to namespace mismatch
- **Enhanced Processing Mode Labels** - Updated chat processing mode labels for better user clarity:
  - "Simple (deprecated)" - Clearly marks legacy mode
  - "Processed (deprecated)" - Indicates deprecated processing mode  
  - "API (recommended)" - Highlights recommended current mode
  - "Context (unfinished)" - Indicates experimental mode status (now implemented)

### Technical Improvements
- **Namespace Consistency** - Standardized all module references to use `the-gold-box` throughout the codebase
- **Settings Registration Fix** - Corrected all `game.settings.register()` calls to use proper module namespace
- **Settings Retrieval Fix** - Fixed all `game.settings.get()` calls to use consistent namespace
- **Version Bump** - Updated version from 0.3.0 to 0.3.1 for feature release
- **Documentation Cleanup** - Removed all emojis from project documentation for professional presentation

### Documentation Updates
- **Changelog Update** - Added detailed 0.3.1 feature notes with technical implementation details
- **Module Manifest Update** - Updated version number in module.json for proper version tracking
- **Professionalization** - Cleaned all emojis from documentation while preserving comprehensive content

## [0.3.0] - 2025-11-27

### Major Release: REST API Integration
- **Foundry REST API Integration** - Complete integration with Foundry REST API for robust data collection
- **Relay Server Support** - Added relay server for enhanced communication between components
- **Three Processing Modes** - Simple, Processed, and API modes for different use cases
- **Submodule Architecture** - Integrated Foundry REST API module and relay server as submodules
- **Enhanced Auto-Discovery** - Automatic port discovery and connection management

### Backend Architecture Improvements
- **API Chat Endpoint** - New `/api/api_chat` endpoint for REST-based message collection
- **API Chat Processor** - Converts Foundry REST API data to compact JSON format
- **AI Chat Processor** - Converts AI responses back to Foundry REST API format
- **Universal Settings System** - Comprehensive settings management across all components
- **Enhanced Settings Sync** - Frontend-to-backend settings synchronization with admin API

### Critical Bug Fixes
- **Unified Settings Object** - Fixed empty settings `{}` issue preventing proper configuration
- **Client ID Management** - Resolved client ID extraction and relay server communication
- **Request Data Flow** - Fixed NoneType errors in API chat endpoint
- **Multi-Endpoint Stability** - Resolved issues across all three chat endpoints
- **Settings Structure Validation** - Implemented comprehensive settings validation and testing

### Frontend Enhancements
- **API Bridge Integration** - Added communication bridge to Foundry REST API module
- **Enhanced Settings Menu** - Added API chat processing mode option
- **Connection Manager** - Improved backend connection and port discovery
- **Visual Feedback** - Enhanced processing indicators and error handling
- **WebSocket Management** - Automatic connection to relay server with client ID storage

### Security & Infrastructure
- **Relaxed Security Configuration** - Optimized security settings for API chat functionality
- **Enhanced Error Handling** - Comprehensive error reporting with detailed debugging
- **Improved Logging** - Added extensive debugging for settings and client ID issues
- **Fallback Mechanisms** - Multi-tier client ID resolution and connection recovery

### Repository Structure
```
The-Gold-Box/
├── backend/                    # Enhanced Python FastAPI backend
│   ├── endpoints/
│   │   ├── api_chat.py       # NEW API Chat endpoint
│   │   ├── process_chat.py   # Enhanced endpoint
│   │   └── simple_chat.py   # Enhanced endpoint
│   └── server/
│       ├── api_chat_processor.py    # NEW API data processing
│       ├── ai_chat_processor.py     # NEW AI response processing
│       └── universal_settings.py   # NEW Settings management
├── scripts/                    # Enhanced frontend
│   ├── api-bridge.js       # NEW Foundry REST API bridge
│   └── gold-box.js         # Enhanced with API mode
├── foundry-module/              # NEW Foundry REST API submodule
├── relay-server/               # NEW Relay server submodule
└── backend.sh                  # Enhanced for submodules
```

### Breaking Changes
- **Submodule Dependencies** - Requires git submodule initialization for full functionality
- **Node.js Requirement** - Relay server requires Node.js and npm for API chat mode
- **Settings Migration** - Existing settings may require reconfiguration for API mode

### Testing & Validation
- **Comprehensive Test Suite** - Added validation scripts for settings and client ID
- **End-to-End Testing** - Verified complete API chat workflow
- **Performance Benchmarking** - Compared API vs HTML scraping performance
- **Integration Testing** - Tested all three processing modes with various configurations

### Documentation Updates
- **API Integration Guide** - Complete documentation for REST API setup and usage
- **Submodule Management** - Instructions for initializing and updating submodules
- **Troubleshooting Guide** - Enhanced debugging for common API chat issues
- **Migration Instructions** - Step-by-step upgrade guide from v0.2.x

## [0.2.5] - 2025-11-23

### Major Backend Reorganization
- **Complete Modular Architecture** - Reorganized backend into logical directories for better maintainability
- **Security Module Separation** - Split security components into dedicated modules (`security/`, `endpoints/`, `server/`)
- **Centralized Configuration** - Consolidated security and server configuration management
- **Improved File Organization** - Separated runtime files, logs, and application logic

### Enhanced Security Framework
- **Universal Security Middleware** - Implemented comprehensive security middleware protecting all endpoints
- **Dedicated Session Validator** - Created `SessionValidator` class for CSRF token generation and session management
- **Persistent Rate Limiting** - File-based rate limiting that survives server restarts
- **Enhanced Input Validation** - Multi-level validation system with HTML-safe mode for Foundry VTT compatibility
- **Comprehensive Audit Logging** - Structured security event logging with detailed tracking

### Foundry VTT Compatibility Fix
- **HTML Preservation in Input Validation** - Fixed critical issue where HTML sanitization broke Foundry chat messages
- **Multi-Level Validation System**:
  - `none`: Skip validation entirely
  - `basic`: Security pattern checking with HTML preservation
  - `strict`: Maximum security with HTML escaping
  - `html_safe`: Security patterns only, complete HTML preservation
- **Chat Message Structure Integrity** - Preserved dice rolls, chat cards, and rich content for AI processing

### Chat Context Processor Architecture
- **Token-Efficient Message Format** - Designed compact JSON format reducing token usage by 90-93%
- **Bidirectional Translation System** - Foundry HTML ↔ Compact JSON for AI processing
- **Structured Message Schemas** - Defined schemas for dice rolls, attacks, saves, whispers, and chat cards
- **Stateless Single-Call Design** - Simplified architecture with full context per request

### Comprehensive Security Coverage
- **CSRF Protection** - Token-based CSRF validation for all chat endpoints
- **Session Management** - File-based session storage with expiration handling
- **Enhanced Security Headers** - XSS, CSRF, and injection protection headers
- **Rate Limiting Per Endpoint** - Configurable rate limits for different endpoint types
- **Security Audit Trails** - Complete logging of all security events and violations

### Backend Directory Structure
```
backend/
├── security/           # Security components
│   ├── input_validator.py     # Input validation with HTML-safe modes
│   ├── sessionvalidator.py    # Session and CSRF management
│   └── security.py           # Universal security middleware
├── endpoints/          # API endpoints
│   ├── process_chat.py        # Enhanced chat processing
│   └── simple_chat.py         # Simple chat interface
├── server/             # Server core components
│   ├── ai_service.py         # AI service integration
│   ├── key_manager.py        # API key management
│   ├── processor.py          # Message processing logic
│   └── provider_manager.py   # LLM provider management
├── server_files/       # Runtime data
│   ├── keys.enc              # Encrypted API keys
│   ├── sessions.json         # Session storage
│   └── rate_limits.json      # Rate limiting data
└── logs/               # Application logs
    ├── goldbox.log           # Main application log
    └── security_audit.log    # Security events log
```

### Technical Improvements
- **Modular Import System** - Updated all import statements for new directory structure
- **Path Configuration Updates** - Modified file paths for runtime files and logs
- **Enhanced Error Handling** - Improved error responses with security context
- **Performance Optimization** - Reduced memory usage and improved response times

### Breaking Changes
- **Frontend Integration Requirements** - Chat endpoints now require session initialization and CSRF tokens
- **Configuration File Locations** - Some configuration files moved to new locations
- **Security Headers** - All endpoints now return security headers by default

### Documentation Updates
- **Security Integration Guide** - Complete frontend integration instructions for new security features
- **API Endpoint Documentation** - Updated with new security requirements and session management
- **Migration Instructions** - Step-by-step guide for upgrading from v0.2.4
- **Troubleshooting Guide** - Common issues and solutions for new security features

### Testing & Validation
- **Comprehensive Security Testing** - Automated tests for CSRF, rate limiting, and input validation
- **HTML Preservation Testing** - Verified Foundry VTT chat message integrity
- **Performance Benchmarking** - Measured token reduction and response time improvements
- **Integration Testing** - End-to-end testing of complete chat workflow

## [0.2.4] - 2025-11-21

### Major Milestone
- **Phase One Roadmap Complete** - Successfully completed the first phase of The Gold Box development roadmap
- **Changelog Restructure** - Streamlined project documentation for better maintainability
- **Production Ready Status** - Module and backend are now stable for production use

### Documentation
- **Updated Project Structure** - Reorganized documentation for clarity
- **Roadmap Alignment** - All initial project goals achieved

## [0.2.3] - 2025-11-20

### Major Features

#### Enhanced Message Context Processing
- **Full Chat History Context** - Automatically collects recent chat messages for AI context
- **Configurable Context Length** - User-adjustable message context window (default: 15 messages)
- **Chronological Ordering** - Messages sent in proper time sequence (oldest to newest)
- **HTML Content Preservation** - Maintains dice rolls, formatting, and rich content
- **Smart Content Extraction** - Preserves Foundry's native HTML structure

#### Advanced AI Service Integration
- **OpenCode Compatible API Support** - Full integration with Z.AI and similar services
- **Service Selection** - User-configurable LLM service selection in settings
- **Multi-Service Architecture** - Support for OpenAI, NovelAI, OpenCode, and Local LLMs
- **Enhanced simple_chat Endpoint** - Improved handling of message context and structured requests

### Bug Fixes

#### Critical JavaScript Issues Resolved
- **Fixed JavaScript Syntax Errors** - Resolved all syntax issues preventing module loading
- **Restored Settings Menu** - Module settings now properly display in Foundry configuration
- **Fixed Chat Button** - "Take AI Turn" button appears and functions correctly
- **Enhanced Error Handling** - Better error messages and debugging information

#### Backend Communication Fixes
- **Fixed Content Display Issues** - Resolved problems with AI response content not showing
- **Enhanced API Debugging** - Detailed logging for content extraction and processing
- **Better Error Messages** - Smart error handling with user-friendly feedback
- **Improved Service Integration** - Better handling of OpenCode-compatible API responses

### Security & Infrastructure

#### Enhanced Backend Security
- **Advanced Input Validation** - Comprehensive validation for all input types
- **Session Management** - Configurable timeouts with automatic cleanup
- **Rate Limiting** - IP-based protection with configurable limits
- **Enhanced Security Headers** - XSS, CSRF, and injection protection

#### Improved Key Management
- **Encrypted API Key Storage** - AES-256 encryption for secure key storage
- **Admin Password Protection** - Secure admin operations with password authentication
- **Multi-Service Key Support** - Separate keys for different AI services
- **Environment Variable Loading** - Secure key injection into environment

### User Experience

#### Enhanced Configuration
- **Comprehensive Settings Menu** - All module options available in Foundry settings
- **Service-Specific Configuration** - Individual settings for each AI service
- **Backend Discovery** - Automatic port discovery with manual override
- **Connection Testing** - Built-in backend connection verification

#### Improved Integration
- **Seamless Chat Integration** - AI responses appear directly in Foundry chat
- **Role-Based Responses** - Different AI behaviors based on selected role
- **Context Transparency** - Users can see exactly what context is sent to AI
- **Error Feedback** - Clear error messages and troubleshooting guidance

### Development & Debugging

#### Enhanced Debugging Capabilities
- **Comprehensive Logging** - Detailed logging for all API interactions
- **Content Extraction Debugging** - Step-by-step content processing logs
- **Error Tracking** - Detailed error reporting with stack traces
- **Performance Monitoring** - Request timing and response metrics

#### Improved Development Tools
- **Backend Health Endpoints** - Comprehensive system status monitoring
- **Security Verification** - Automated integrity and security checks
- **Admin API** - Password-protected server management interface
- **Service Status Monitoring** - Real-time API service status

### Documentation

#### Comprehensive Documentation Updates
- **Updated Backend README** - Complete documentation for v0.2.3 features
- **Enhanced Main README** - Full project documentation with latest features
- **Installation Guides** - Step-by-step setup instructions
- **Troubleshooting Guide** - Common issues and solutions

## [0.2.2] - 2025-11-15

### Backend Improvements
- **FastAPI Migration** - Migrated from Flask to FastAPI for better performance
- **Enhanced Security** - Added comprehensive input validation and security headers
- **Admin Password System** - Added password-protected admin operations
- **Key Management** - Encrypted API key storage with password protection
- **Session Management** - Added configurable session timeouts and warnings
- **Rate Limiting** - IP-based rate limiting with configurable windows

### Security Enhancements
- **Universal Input Validator** - Comprehensive validation system for all input types
- **Security Pattern Detection** - XSS, SQL injection, and command injection protection
- **File Integrity Verification** - SHA256 hash checking for critical files
- **Virtual Environment Verification** - Ensures proper Python environment isolation
- **Permission Verification** - Automated file permission security checks

### Monitoring & Logging
- **Structured Logging** - Enhanced logging with timestamps and client tracking
- **Health Check Endpoints** - Comprehensive system status monitoring
- **Security Verification** - Automated security integrity checks
- **Performance Metrics** - Request timing and response size tracking

## [0.2.1] - 2025-11-10

### Initial Release Features
- **OpenAI Compatible API** - Full support for OpenAI and compatible services
- **NovelAI API Integration** - Specialized support for NovelAI services
- **Simple Chat Endpoint** - Basic chat interface for AI communication
- **Health Check System** - Basic server health monitoring
- **Environment Configuration** - Flexible environment-based settings
- **CORS Protection** - Environment-based origin restrictions

### Core Functionality
- **Basic AI Communication** - Simple prompt/response system
- **API Key Management** - Basic API key handling
- **Error Handling** - Basic error responses and logging
- **Foundry Integration** - Basic module integration with chat system

### Documentation
- **Basic Setup Guide** - Initial installation and configuration instructions
- **API Documentation** - Basic endpoint documentation
- **Security Guidelines** - Basic security recommendations

## [0.1.15] - 2025-11-05

### Security & Infrastructure
- **Multi-Service API Key Storage** - Secure storage system for multiple AI services
- **Comprehensive Security Overhaul** - Pre-alpha safety improvements
- **Documentation Updates** - Updated README with user-facing changes
- **License Compliance** - Added missing python-dotenv license file

## [0.1.14] through [0.1.10] - 2025-10-28 to 2025-11-03

### Critical Bug Fixes & Compatibility
- Fixed module.json manifest validation and DOM selectors for Foundry VTT v13
- Resolved jQuery wrapper issues and JavaScript syntax errors
- Implemented "Take AI Turn" button functionality with proper DOM loading
- Added duplicate prevention and FormApplicationV2 implementation
- Series of incremental stability improvements and version updates

## [0.1.9] through [0.1.6] - 2025-10-20 to 2025-10-26

### Foundry VTT v13 Compatibility
- Adapted to new Foundry VTT v13 DOM structure
- Fixed jQuery integration and button creation logic
- Implemented working ChatConsole UI pattern
- Enhanced hook system for DOM readiness
- Improved DOM manipulation and error handling

## [0.1.5] through [0.1.1] - 2025-10-15 to 2025-10-19

### Foundation Development
- Initial Foundry VTT module structure and chat integration
- Basic UI framework and backend communication
- Core functionality, error handling, and configuration system
- Early testing framework implementation

## [0.1.0] - 2025-10-10

### Initial Release
- Project foundation and basic module structure
- Initial Foundry VTT integration and documentation setup

---

## Version Summary

### v0.2.4 - Milestone Completion Release
**Focus**: Phase One roadmap completion and project stabilization
**Key Features**: Documentation restructuring, production-ready status
**Stability**: Stable and ready for production deployment

### v0.2.3 - Context & Integration Release
**Focus**: Enhanced user experience with full chat context and seamless integration
**Key Features**: Message context processing, JavaScript fixes, multi-service support
**Stability**: Major improvements in reliability and error handling

### v0.2.2 - Security & Infrastructure Release
**Focus**: Enterprise-grade security and production readiness
**Key Features**: FastAPI migration, comprehensive security, admin operations
**Stability**: Major backend architecture improvements

### v0.2.1 - Foundation Release
**Focus**: Basic AI communication and module integration
**Key Features**: OpenAI/NovelAI support, basic chat functionality
**Stability**: Initial release with core functionality

### v0.1.15 - Security Architecture Release
**Focus**: Security foundation and backend infrastructure
**Key Features**: Multi-service API key storage, comprehensive security overhaul
**Stability**: Pre-alpha security improvements

### v0.1.14 to v0.1.6 - Compatibility & Stability Series
**Focus**: Foundry VTT v13 compatibility and bug fixes
**Key Features**: DOM fixes, jQuery integration, JavaScript improvements
**Stability**: Progressive stability improvements and compatibility updates

### v0.1.5 to v0.1.1 - Development Series
**Focus**: Core functionality and UI development
**Key Features**: Basic module features, chat integration, UI components
**Stability**: Early development with incremental improvements

### v0.1.0 - Initial Release
**Focus**: Project foundation and basic structure
**Key Features**: Initial module setup, basic Foundry integration
**Stability**: Proof of concept and initial release

---

**Note**: This changelog covers significant changes. For detailed technical documentation, see the respective README files in each component directory.

**Development Focus**: The Gold Box project follows a phased development approach, with each major release focusing on specific aspects of the AI-powered TTRPG assistant system.
