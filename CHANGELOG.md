# Changelog

All notable changes to The Gold Box will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.13] - 2025-11-16

### Added
- Python Flask backend server with CORS support
- Virtual environment setup with requirements.txt
- HTTP API endpoints for health check and AI processing
- Backend auto-start functionality in plugin settings
- Start/Stop backend buttons in configuration UI
- Real-time connection testing and status display
- End-to-end prompt sending and response handling
- Input validation and sanitization for security
- Rate limiting to prevent abuse
- Styled chat messages for AI responses
- Comprehensive error handling and user feedback
- Backend status management (running/stopped/manual states)

### Changed
- Updated default backend URL to port 5001
- Enhanced settings menu with backend management controls
- Improved error messages and notifications

### Fixed
- Port conflict issues by using alternative port 5001
- Connection testing reliability
- Button styling and UX improvements

### Technical Details
- Compatible with Foundry VTT v12+
- Flask 2.3.3 with Flask-CORS 4.0.0
- CC-BY-NC-SA 4.0 licensing maintained
- Full backend-frontend communication workflow implemented

### Planned
- Phase 2: Real AI service integration (OpenAI, Anthropic, etc.)
- Phase 3: Conversation history and context management
- Phase 4: Advanced AI personalities and tool integration

## [0.1.12] - 2025-11-16

### Added
- Initial bare bones module structure
- Basic manifest configuration
- Main JavaScript module with placeholder functionality
- Minimal CSS styling for AI controls
- English language support
- "Take AI Turn" button in chat sidebar
- Module info button in settings menu

## [0.1.0] - 2024-11-16

### Added
- Initial project setup
- Basic module structure that can be loaded by Foundry VTT
- Placeholder UI elements for future AI functionality
- Git repository initialization
- Project documentation

### Technical Details
- Compatible with Foundry VTT v12+
- ES6 module structure
- Basic styling framework
- Internationalization support foundation
