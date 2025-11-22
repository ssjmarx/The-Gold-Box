# Changelog

All notable changes to The Gold Box project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.4] - 2025-11-21

### 🎯 Major Milestone
- **Phase One Roadmap Complete** - Successfully completed the first phase of the Gold Box development roadmap
- **Changelog Restructure** - Streamlined project documentation for better maintainability
- **Production Ready Status** - Module and backend are now stable for production use

### 📝 Documentation
- **Updated Project Structure** - Reorganized documentation for clarity
- **Roadmap Alignment** - All initial project goals achieved

## [0.2.3] - 2025-11-20

### 🚀 Major Features

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

### 🔧 Bug Fixes

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

### 🔒 Security & Infrastructure

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

### 🎨 User Experience

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

### 🛠️ Development & Debugging

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

### 📚 Documentation

#### Comprehensive Documentation Updates
- **Updated Backend README** - Complete documentation for v0.2.3 features
- **Enhanced Main README** - Full project documentation with latest features
- **Installation Guides** - Step-by-step setup instructions
- **Troubleshooting Guide** - Common issues and solutions

## [0.2.2] - 2025-11-15

### 🔧 Backend Improvements
- **FastAPI Migration** - Migrated from Flask to FastAPI for better performance
- **Enhanced Security** - Added comprehensive input validation and security headers
- **Admin Password System** - Added password-protected admin operations
- **Key Management** - Encrypted API key storage with password protection
- **Session Management** - Added configurable session timeouts and warnings
- **Rate Limiting** - IP-based rate limiting with configurable windows

### 🛡️ Security Enhancements
- **Universal Input Validator** - Comprehensive validation system for all input types
- **Security Pattern Detection** - XSS, SQL injection, and command injection protection
- **File Integrity Verification** - SHA256 hash checking for critical files
- **Virtual Environment Verification** - Ensures proper Python environment isolation
- **Permission Verification** - Automated file permission security checks

### 📊 Monitoring & Logging
- **Structured Logging** - Enhanced logging with timestamps and client tracking
- **Health Check Endpoints** - Comprehensive system status monitoring
- **Security Verification** - Automated security integrity checks
- **Performance Metrics** - Request timing and response size tracking

## [0.2.1] - 2025-11-10

### 🚀 Initial Release Features
- **OpenAI Compatible API** - Full support for OpenAI and compatible services
- **NovelAI API Integration** - Specialized support for NovelAI services
- **Simple Chat Endpoint** - Basic chat interface for AI communication
- **Health Check System** - Basic server health monitoring
- **Environment Configuration** - Flexible environment-based settings
- **CORS Protection** - Environment-based origin restrictions

### 🎯 Core Functionality
- **Basic AI Communication** - Simple prompt/response system
- **API Key Management** - Basic API key handling
- **Error Handling** - Basic error responses and logging
- **Foundry Integration** - Basic module integration with chat system

### 📝 Documentation
- **Basic Setup Guide** - Initial installation and configuration instructions
- **API Documentation** - Basic endpoint documentation
- **Security Guidelines** - Basic security recommendations

## [0.1.15] - 2025-11-05

### 🔐 Security & Infrastructure
- **Multi-Service API Key Storage** - Secure storage system for multiple AI services
- **Comprehensive Security Overhaul** - Pre-alpha safety improvements
- **Documentation Updates** - Updated README with user-facing changes
- **License Compliance** - Added missing python-dotenv license file

### 🛠️ Backend Development
- **Python Backend Creation** - Initial backend implementation
- **API Key Management System** - Encrypted key storage and retrieval
- **Security Framework** - Foundation for secure API operations

## [0.1.14] through [0.1.10] - 2025-10-28 to 2025-11-03

### 🐛 Critical Bug Fixes
- **Module.json Manifest Validation** - Fixed manifest validation errors
- **DOM Selector Fixes** - Updated selectors for Foundry VTT v13 compatibility
- **jQuery Wrapper Issues** - Fixed jQuery usage for proper DOM manipulation
- **JavaScript Syntax Errors** - Resolved missing commas and method issues

### 🎨 UI/UX Improvements
- **Chat Button Creation** - Fixed "Take AI Turn" button not appearing
- **Hook Debugging** - Enhanced debugging for chat button lifecycle
- **Duplicate Prevention** - Added checks to prevent duplicate UI elements
- **FormApplicationV2 Implementation** - Updated to use latest Foundry patterns

### 🔧 Technical Improvements
- **DOM Loading Timing** - Fixed button creation after DOM is ready
- **jQuery Usage** - Proper jQuery wrapper usage for Foundry VTT v13
- **Version Bumps** - Incremental version updates for each fix series

## [0.1.9] through [0.1.6] - 2025-10-20 to 2025-10-26

### 🔄 Foundry VTT v13 Compatibility
- **DOM Structure Updates** - Adapted to new Foundry VTT v13 DOM structure
- **jQuery Integration** - Fixed jQuery usage for v13 compatibility
- **Button Creation Logic** - Enhanced button creation with better error handling
- **Hook System** - Improved hook usage for DOM readiness

### 🐛 Stability Improvements
- **Syntax Error Resolution** - Fixed various JavaScript syntax issues
- **DOM Manipulation** - Improved DOM element selection and manipulation
- **Chat Console Pattern** - Implemented working ChatConsole UI pattern
- **Application Framework** - Updated to use FormApplicationV2

## [0.1.5] through [0.1.1] - 2025-10-15 to 2025-10-19

### 🏗️ Foundation Development
- **Initial Module Structure** - Basic Foundry VTT module setup
- **Chat Integration** - Basic chat system integration
- **UI Framework** - Initial user interface components
- **Backend Communication** - Basic client-server communication

### 🔧 Early Development
- **Basic Functionality** - Core module features implemented
- **Error Handling** - Basic error management system
- **Configuration System** - Initial settings and configuration
- **Testing Framework** - Basic testing capabilities

## [0.1.0] - 2025-10-10

### 🎉 Initial Release
- **Project Foundation** - Initial Gold Box module creation
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
