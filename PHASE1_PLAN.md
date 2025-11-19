Debug mode: False
API Keys Required: True# The Gold Box - Phase 1 "The Parrot" Implementation Plan

## Objective
Migrate from Flask to FastAPI + LiteLLM to enable real AI communication with multiple LLM providers (OpenAI Compatible, NovelAI, Local Models).

## Current Status
- Version: 0.2.2 (ready for 0.2.3 development)
- Backend: Flask with comprehensive security system
- Frontend: JavaScript with auto-discovery and basic echo server
- Security: Production-ready with UniversalInputValidator

## Phase 1 Roadmap

### Step 1: Foundation Migration (Day 1-2)
- **1.1 Replace Flask with FastAPI in server.py** [CURRENT STEP]
  - Basic FastAPI app structure
  - Keep existing endpoints: /api/process, /api/health, /api/info, /api/security
  - Verify basic functionality before security migration
  
- **1.2 Migrate Security Features to FastAPI**
  - Port UniversalInputValidator (reuse as-is)
  - Implement FastAPI middleware for security headers
  - Migrate rate limiting (slowapi)
  - Port session management
  - Update CORS configuration

### Step 2: LiteLLM Integration (Day 2-3)
- **2.1 Add LiteLLM Dependencies**
  - Update requirements.txt with FastAPI, LiteLLM, uvicorn
  - Basic LiteLLM setup and testingokay, lets
  
- **2.2 OpenAI Compatible Support**
  - Implement basic OpenAI provider integration
  - Test with existing API keys
  
- **2.3 NovelAI Custom Provider**
  - Create custom LiteLLM provider for NovelAI API
  - Handle NovelAI-specific authentication and format
  - Test integration with NovelAI API key
  
- **2.4 Local Model Support**
  - Add Ollama integration for local models
  - Test with local model setup

### Step 3: API Endpoints Enhancement (Day 3-4)
- **3.1 Async LLM Processing**
  - Convert /api/process to async endpoint
  - Implement provider selection logic
  - Add fallback mechanisms
  
- **3.2 Provider Management**
  - Add /api/providers endpoint
  - Provider status checking
  - Model selection per provider

### Step 4: Frontend Integration (Day 4-5)
- **4.1 Update Frontend API Client**
  - Modify gold-box.js for FastAPI response format
  - Add provider selection UI
  - Update error handling

- **4.2 Settings Enhancement**
  - Add LLM provider dropdown
  - Model selection per provider
  - Fallback provider options

### Step 5: Testing & Documentation (Day 5)
- **5.1 End-to-End Testing**
  - Test all three providers
  - Error scenario testing
  - Performance testing
  
- **5.2 Documentation Update**
  - Update backend README
  - Update CHANGELOG for 0.2.3
  - Update main project README

## Technical Requirements

### Dependencies to Add
```
fastapi==0.104.1
uvicorn[standard]==0.24.0
litellm==1.17.0
slowapi==0.1.9
pydantic==2.5.0
```

### Security Migration Checklist
- [x] UniversalInputValidator (reuse existing)
- [ ] Rate limiting middleware (slowapi)
- [ ] Security headers middleware
- [ ] CORS configuration
- [ ] Session management
- [ ] Input validation integration

### Provider Integration Strategy
- **OpenAI Compatible**: Direct LiteLLM support
- **NovelAI**: Custom provider wrapper
- **Local Models**: Ollama integration

## Success Criteria for Phase 1
- [ ] FastAPI server running with basic functionality
- [ ] Three LLM providers integrated and tested
- [ ] Frontend successfully communicates with new backend
- [ ] Provider selection functional
- [ ] All security features migrated
- [ ] Error handling and fallback logic working
- [ ] Documentation updated
- [ ] Ready for Phase 2 "The Observer"

## Notes
- Keep existing Flask server as backup during migration
- Focus on minimal working implementation first
- NovelAI integration may require additional research
- Maintain existing key management system
- Keep all existing validation and security patterns

---
*Created: 2025-11-18*
*Phase: 0.2.3 Development*
*Target: Complete Phase 1 "The Parrot"*
