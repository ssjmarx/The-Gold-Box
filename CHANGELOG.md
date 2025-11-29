# Changelog

All notable changes to The Gold Box project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0/).

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

### Backend Development
- **Python Backend Creation** - Initial backend implementation
- **API Key Management System** - Encrypted key storage and retrieval
- **Security Framework** - Foundation for secure API operations

## [0.1.14] through [0.1.10] - 2025-10-28 to 2025-11-03

### Critical Bug Fixes
- **Module.json Manifest Validation** - Fixed manifest validation errors
- **DOM Selector Fixes** - Updated selectors for Foundry VTT v13 compatibility
- **jQuery Wrapper Issues** - Fixed jQuery usage for proper DOM manipulation
- **JavaScript Syntax Errors** - Resolved missing commas and method issues

### UI/UX Improvements
- **Chat Button Creation** - Fixed "Take AI Turn" button not appearing
- **Hook Debugging** - Enhanced debugging for chat button lifecycle
- **Duplicate Prevention** - Added checks to prevent duplicate UI elements
- **FormApplicationV2 Implementation** - Updated to use latest Foundry patterns

### Technical Improvements
- **DOM Loading Timing** - Fixed button creation after DOM is ready
- **jQuery Usage** - Proper jQuery wrapper usage for Foundry VTT v13
- **Version Bumps** - Incremental version updates for each fix series

## [0.1.9] through [0.1.6] - 2025-10-20 to 2025-10-26

### Foundry VTT v13 Compatibility
- **DOM Structure Updates** - Adapted to new Foundry VTT v13 DOM structure
- **jQuery Integration** - Fixed jQuery usage for v13 compatibility
- **Button Creation Logic** - Enhanced button creation with better error handling
- **Hook System** - Improved hook usage for DOM readiness

### Stability Improvements
- **Syntax Error Resolution** - Fixed various JavaScript syntax issues
- **DOM Manipulation** - Improved DOM element selection and manipulation
- **Chat Console Pattern** - Implemented working ChatConsole UI pattern
- **Application Framework** - Updated to use FormApplicationV2

## [0.1.5] through [0.1.1] - 2025-10-15 to 2025-10-19

### Foundation Development
- **Initial Module Structure** - Basic Foundry VTT module setup
- **Chat Integration** - Basic chat system integration
- **UI Framework** - Initial user interface components
- **Backend Communication** - Basic client-server communication

### Early Development
- **Basic Functionality** - Core module features implemented
- **Error Handling** - Basic error management system
- **Configuration System** - Initial settings and configuration
- **Testing Framework** - Basic testing capabilities

## [0.1.0] - 2025-10-10

### Initial Release
- **Project Foundation** - Initial The Gold Box module creation
- **Basic Architecture** - Core module structure established
- **Foundry VTT Integration** - Basic integration with Foundry VTT
- **Documentation Setup** - Initial project documentation

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
