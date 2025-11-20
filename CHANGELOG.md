# Changelog

All notable changes to The Gold Box project will be documented in this file.

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

---

## Version Summary

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

---

**Note**: This changelog covers significant changes. For detailed technical documentation, see the respective README files in each component directory.
