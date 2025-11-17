# The Gold Box Backend Setup

This Python backend provides the AI processing capabilities for The Gold Box Foundry VTT module.

## Quick Start

### 1. Install Dependencies

```bash
# Navigate to the backend directory
cd backend

# Install Python packages
pip install -r requirements.txt
```

### 2. Start the Server

```bash
# Development mode (with debug output)
python server.py

# Or production mode
FLASK_DEBUG=False python server.py
```

The server will start on `http://localhost:5000` by default.

### 3. Test the Backend

Open your browser or use curl to test:

```bash
# Health check
curl http://localhost:5000/api/health

# Service info
curl http://localhost:5000/api/info

# Test prompt processing
curl -X POST http://localhost:5000/api/process \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Hello, AI!"}'
```

## Configuration

### Environment Variables

- `FLASK_DEBUG`: Set to `True` for development, `False` for production
- Server runs on `localhost:5000` by default

### Security Features

- **Rate Limiting**: 5 requests per minute per IP
- **Input Validation**: HTML sanitization and length limits
- **CORS Protection**: Restricted to Foundry VTT origins
- **Error Handling**: Comprehensive error responses

## API Endpoints

### GET /api/health
Health check endpoint.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2024-01-01T12:00:00",
  "version": "0.1.0",
  "service": "The Gold Box Backend"
}
```

### GET /api/info
Service information endpoint.

**Response:**
```json
{
  "name": "The Gold Box Backend",
  "description": "AI-powered Foundry VTT Module Backend",
  "version": "0.1.0",
  "status": "running",
  "endpoints": {...},
  "license": "CC-BY-NC-SA 4.0",
  "dependencies": {...}
}
```

### POST /api/process
Main AI processing endpoint.

**Request:**
```json
{
  "prompt": "Your AI prompt here"
}
```

**Response:**
```json
{
  "status": "success",
  "response": "Echoed prompt",
  "original_prompt": "Your AI prompt here",
  "timestamp": "2024-01-01T12:00:00",
  "processing_time": 0.001,
  "message": "AI functionality: Basic echo server - prompt returned unchanged"
}
```

## Integration with Foundry

1. **Configure Foundry Module:**
   - Go to Game Settings → Module Settings → The Gold Box Configuration
   - Set Backend URL to `http://localhost:5000`
   - Click "Test Connection" to verify
   - Configure your AI prompt and role

2. **Use the Module:**
   - Click the "Take AI Turn" button in chat
   - The prompt will be sent to this backend
   - Response will appear in the chat

## Logging

- Logs are written to `goldbox.log` in the backend directory
- Console output shows real-time activity
- Logs include timestamps, client IPs, and request sizes

## Troubleshooting

### Common Issues

1. **Port already in use:**
   ```bash
   # Find what's using port 5000
   lsof -i :5000
   
   # Kill the process or change port in server.py
   ```

2. **CORS errors:**
   - Make sure Foundry is running on `localhost:30000`
   - Check that no other services are blocking requests

3. **Connection refused:**
   - Verify the backend is running
   - Check firewall settings
   - Ensure the URL in Foundry settings is correct

### Development Tips

- Use `FLASK_DEBUG=True` for detailed error messages
- Check browser console for JavaScript errors
- Monitor the backend logs for request details

## License

This backend is licensed under CC-BY-NC-SA 4.0, compatible with all dependencies:

- Flask (BSD 3-Clause License)
- Flask-CORS (MIT License)

## Next Steps

This is a basic echo server. Future versions will include:

- Actual AI integration (OpenAI, Anthropic, etc.)
- Advanced prompt management
- Conversation history
- Multiple AI roles and personalities
- Streaming responses
