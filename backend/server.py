#!/usr/bin/env python3
"""
The Gold Box - Python Backend Server
AI-powered Foundry VTT Module Backend

License: CC-BY-NC-SA 4.0 (compatible with dependencies)
Dependencies: Flask (BSD 3-Clause), Flask-CORS (MIT)
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import logging
import time
import os
from datetime import datetime

# Initialize Flask app
app = Flask(__name__)

# Configure CORS for development - restrict to specific origins in production
CORS(app, 
     origins=['http://localhost:30000', 'http://127.0.0.1:30000'],
     methods=['POST'],
     allow_headers=['Content-Type', 'X-API-Key'])

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('goldbox.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Simple in-memory rate limiting for basic protection
class RateLimiter:
    def __init__(self, max_requests=10, window_seconds=60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests = {}
    
    def is_allowed(self, client_id):
        now = time.time()
        if client_id not in self.requests:
            self.requests[client_id] = []
        
        # Remove old requests
        self.requests[client_id] = [
            req_time for req_time in self.requests[client_id] 
            if now - req_time < self.window_seconds
        ]
        
        # Check if under limit
        if len(self.requests[client_id]) >= self.max_requests:
            return False
        
        # Add current request
        self.requests[client_id].append(now)
        return True

rate_limiter = RateLimiter(max_requests=5, window_seconds=60)

def validate_prompt(prompt):
    """
    Basic input validation for the prompt
    """
    if not prompt:
        raise ValueError("Prompt cannot be empty")
    
    if len(prompt) > 10000:
        raise ValueError("Prompt too long (max 10000 characters)")
    
    # Basic HTML sanitization
    prompt = prompt.replace('<', '&lt;').replace('>', '&gt;')
    
    return prompt

@app.route('/api/process', methods=['POST'])
def process_prompt():
    """
    Main endpoint for processing AI prompts
    For now, just echoes the prompt back unchanged
    """
    try:
        # Rate limiting
        client_id = request.remote_addr
        if not rate_limiter.is_allowed(client_id):
            return jsonify({
                'error': 'Rate limit exceeded. Please try again later.',
                'status': 'error'
            }), 429
        
        # Get JSON data
        data = request.get_json()
        if not data or 'prompt' not in data:
            return jsonify({
                'error': 'Invalid request. Prompt is required.',
                'status': 'error'
            }), 400
        
        # Validate and sanitize prompt
        prompt = validate_prompt(data['prompt'])
        
        # Log the request (without sensitive content)
        logger.info(f"Processing request from {client_id}: {len(prompt)} characters")
        
        # For now, just echo the prompt back
        # This will be replaced with actual AI processing later
        response = {
            'status': 'success',
            'response': prompt,  # Echo back unchanged for now
            'original_prompt': prompt,
            'timestamp': datetime.now().isoformat(),
            'processing_time': 0.001,  # Simulated processing time
            'message': 'AI functionality: Basic echo server - prompt returned unchanged'
        }
        
        logger.info(f"Response sent to {client_id}: Success")
        
        return jsonify(response)
        
    except ValueError as e:
        logger.warning(f"Validation error from {client_id}: {str(e)}")
        return jsonify({
            'error': str(e),
            'status': 'error'
        }), 400
        
    except Exception as e:
        logger.error(f"Unexpected error from {client_id}: {str(e)}")
        return jsonify({
            'error': 'Internal server error',
            'status': 'error'
        }), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    """
    Health check endpoint
    """
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'version': '0.1.0',
        'service': 'The Gold Box Backend'
    })

@app.route('/api/info', methods=['GET'])
def service_info():
    """
    Service information endpoint
    """
    return jsonify({
        'name': 'The Gold Box Backend',
        'description': 'AI-powered Foundry VTT Module Backend',
        'version': '0.1.0',
        'status': 'running',
        'endpoints': {
            'process': 'POST /api/process - Process AI prompts',
            'health': 'GET /api/health - Health check',
            'info': 'GET /api/info - Service information'
        },
        'license': 'CC-BY-NC-SA 4.0',
        'dependencies': {
            'Flask': 'BSD 3-Clause License',
            'Flask-CORS': 'MIT License'
        }
    })

@app.errorhandler(404)
def not_found(error):
    return jsonify({
        'error': 'Endpoint not found',
        'status': 'error',
        'available_endpoints': ['/api/process', '/api/health', '/api/info']
    }), 404

@app.errorhandler(405)
def method_not_allowed(error):
    return jsonify({
        'error': 'Method not allowed',
        'status': 'error'
    }), 405

if __name__ == '__main__':
    # Check if running in development or production
    debug_mode = os.environ.get('FLASK_DEBUG', 'True').lower() == 'true'
    
    print("=" * 50)
    print("The Gold Box Backend Server")
    print("=" * 50)
    print(f"Debug mode: {debug_mode}")
    print(f"Server starting on http://localhost:5000")
    print("Available endpoints:")
    print("  POST /api/process - Process AI prompts")
    print("  GET  /api/health  - Health check")
    print("  GET  /api/info    - Service information")
    print("=" * 50)
    
    # Start the server
    app.run(
        host='localhost',
        port=5001,
        debug=debug_mode
    )
