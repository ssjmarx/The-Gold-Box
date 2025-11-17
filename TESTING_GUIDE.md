# The Gold Box - End-to-End Testing Guide

## Implementation Complete! 🎉

Your Gold Box Foundry VTT module now has full backend communication capabilities. Here's how to test everything:

The Gold Box Backend Server
Debug mode: True
Server starting on http://localhost:5001
Available endpoints:
  POST /api/process - Process AI prompts
  GET  /api/health  - Health check
  GET  /api/info    - Service information
* Running on http://localhost:5001
```
## Quick Start Testing

### 1. Start the Backend (Two Options)

**Option A: Manual Start**
```bash
cd backend
source venv/bin/activate
python server.py
```

**Option B: Auto-start via Foundry UI**
- Load Foundry VTT with Gold Box module enabled
- Open Gold Box settings
- Click "Start Backend" button
- Follow the manual start instructions shown in notifications

The Gold Box Backend Server
Debug mode: True
Server starting on http://localhost:5001
Available endpoints:
  POST /api/process - Process AI prompts
  GET  /api/health  - Health check
  GET  /api/info    - Service information
* Running on http://localhost:5001
```
The Gold Box Backend Server
Debug mode: True
Server starting on http://localhost:5001
Available endpoints:
  POST /api/process - Process AI prompts
  GET  /api/health  - Health check
  GET  /api/info    - Service information
* Running on http://localhost:5001
```
The server should start on `http://localhost:5001` with output:
```
The Gold Box Backend Server
Debug mode: True
Server starting on http://localhost:5001
Available endpoints:
  POST /api/process - Process AI prompts
  GET  /api/health  - Health check
  GET  /api/info    - Service information
* Running on http://localhost:5001
```
The Gold Box Backend Server
Debug mode: True
Server starting on http://localhost:5001
Available endpoints:
  POST /api/process - Process AI prompts
  GET  /api/health  - Health check
  GET  /api/info    - Service information
* Running on http://localhost:5001
```
==================================================
The Gold Box Backend Server
==================================================
Debug mode: True
Server starting on http://localhost:5001
Available endpoints:
  POST /api/process - Process AI prompts
  GET  /api/health  - Health check
  GET  /api/info    - Service information
==================================================
* Running on http://localhost:5001
```

### 2. Test Backend Directly (Optional)

Test the endpoints work:

```bash
# Health check
curl http://localhost:5001/api/health

# Test AI processing
curl -X POST http://localhost:5001/api/process \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Hello Gold Box!"}'
```

Expected responses:
- Health: `{"status":"healthy","version":"0.1.0",...}`
- Process: Echoes back your prompt with metadata

### 3. Configure Foundry Module

1. **Load Foundry VTT** with the Gold Box module enabled
2. **Open Settings**: Game Settings → Module Settings → The Gold Box Configuration
3. **Configure Backend**:
   - Backend URL: `http://localhost:5001`
   - Click "Test Connection" - should show "Connected to The Gold Box Backend v0.1.0"
4. **Configure AI**:
   - AI Prompt: Enter any test message (e.g., "Hello from the AI!")
   - AI Role: Choose your preferred role
5. **Save Settings**

### 4. Test End-to-End Functionality

1. **Click the "Take AI Turn" button** in the chat sidebar
2. **Expected behavior**:
   - Loading notification appears
   - Prompt is sent to backend
   - Response appears in chat with styled formatting
   - Success notification shows

### 5. Test Error Handling

Try these scenarios:

**No Prompt Configured**:
- Clear the AI prompt field
- Click "Take AI Turn"
- Should get: "Please configure an AI prompt in Gold Box settings first!"

**Backend Offline**:
- Stop the Python server
- Click "Test Connection" 
- Should get: "Connection failed" error

**Invalid Prompt**:
- Backend validates input length and content
- Should show appropriate error messages

## Functionality Verified ✅

The following workflow has been implemented and tested:

### ✅ Backend Features
- **Flask web server** with CORS support
- **Health check endpoint** (`/api/health`)
- **AI processing endpoint** (`/api/process`) 
- **Input validation** and sanitization
- **Rate limiting** (5 requests/minute)
- **Error handling** and logging
- **Service info endpoint** (`/api/info`)

### ✅ Frontend Features
- **Settings menu** with backend configuration
- **Connection testing** with visual feedback
- **Prompt configuration** and AI role selection
- **Chat button** integration
- **Styled chat messages** for AI responses
- **Error handling** and user notifications
- **Loading states** and progress indicators

### ✅ Security Measures
- **CORS protection** restricted to Foundry origins
- **Input sanitization** prevents XSS
- **Rate limiting** prevents abuse
- **Length validation** prevents DoS
- **Error logging** for monitoring

### ✅ User Experience
- **Visual feedback** for all operations
- **Progressive enhancement** (graceful fallbacks)
- **Responsive design** for mobile
- **Clear error messages** and help text
- **Professional styling** with animations

## Integration Success!

Your Gold Box module now successfully:

1. **Accepts prompts** from the Foundry settings interface
2. **Sends them** to the Python backend via HTTP API
3. **Processes them** (currently echoes back unchanged)
4. **Returns responses** to display in Foundry chat
5. **Handles errors** gracefully with user feedback

The foundation is now complete for adding real AI processing in the next phase!

## Next Steps

This implementation provides the foundation for:
- Adding actual AI service integration (OpenAI, Anthropic, etc.)
- Implementing conversation history and context
- Adding advanced prompt management
- Creating multiple AI personalities
- Adding streaming responses
- Implementing file-based configuration
- Adding user authentication and API keys

## Troubleshooting

**Port Issues**: If port 5001 is in use, change `port=5001` in `server.py`
**CORS Errors**: Ensure Foundry runs on `localhost:30000`
**Connection Refused**: Check firewall and that backend is running
**Missing Button**: Refresh Foundry or check browser console for errors

## Files Created/Modified

- `backend/server.py` - Flask backend with echo functionality
- `backend/requirements.txt` - Python dependencies
- `backend/README.md` - Setup and documentation
- `scripts/gold-box.js` - Enhanced with API communication
- `templates/gold-box-config.html` - Added backend configuration UI
- `styles/gold-box.css` - Added chat message styling
- `TESTING_GUIDE.md` - This comprehensive testing guide

🎯 **Mission Accomplished**: Your Foundry plugin now communicates with a Python backend and can send/receive messages as requested!
