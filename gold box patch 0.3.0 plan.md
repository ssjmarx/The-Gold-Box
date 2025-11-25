# Gold Box v0.3.0 Core Functionality Plan
## REST API Chat Processing Integration

### Objective
Implement REST API-based chat processing as an alternative to HTML scraping, providing a more robust and maintainable approach to AI-assisted gameplay while maintaining full backward compatibility with existing functionality.

### Version Information
- **Target Version**: Gold Box v0.3.0
- **Integration Date**: November 2025
- **Priority**: HIGH - Core functionality milestone for public release readiness

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    Gold Box v0.3.0 (Unified)                            │
│                                                                         │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐      │
│  │ Foundry REST    │    │ Foundry REST    │    │ Gold Box        │      │
│  │ API Relay       │◄──►│ API Module      │◄──►│ Frontend        │      │
│  │ Server          │    │ (TypeScript)    │    │ (JavaScript)    │      │
│  └─────────────────┘    └─────────────────┘    └─────────────────┘      │
│         │                        │                         │            │
│         └────────────────────────┬─────────────────────────┘            │
│                                  ▼                                      │
│                        ┌─────────────────┐                              │
│                        │                 │                              │
│                        │  The Gold Box   │                              │
│                        │                 │                              │
│                        └─────────────────┘                              │
│                                  ▼                                      │
│                        ┌─────────────────┐                              │
│                        │ AI Services     │                              │
│                        │                 │                              │
│                        └─────────────────┘                              │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Core Milestone: API Chat Implementation

**Key Goal**: Implement "API Chat" mode that collects chat data via REST API instead of HTML scraping, while maintaining full backward compatibility with existing "Simple" and "Processed" modes.

### Repository Structure Changes

#### Target Structure
```
Gold-Box/
├── backend/                    # ✅ Existing Python FastAPI
│   ├── server.py             # Main backend server (enhanced)
│   ├── requirements.txt         # Python dependencies
│   ├── endpoints/              # Gold Box API endpoints
│   │   ├── api_chat.py       # 🆕 API Chat endpoint
│   │   ├── process_chat.py   # ✅ Existing endpoint
│   │   └── simple_chat.py   # ✅ Existing endpoint
│   └── server/               # Backend processing modules
│       ├── api_chat_processor.py    # 🆕 Convert API data to compact JSON
│       ├── ai_chat_processor.py     # 🆕 Convert AI responses to API format
│       ├── ai_service.py            # ✅ Existing
│       ├── key_manager.py          # ✅ Existing
│       ├── processor.py             # ✅ Existing
│       └── provider_manager.py      # ✅ Existing
├── scripts/                    # ✅ Existing orchestration
│   ├── gold-box.js         # ✅ Enhanced for API mode
│   ├── connection-manager.js # ✅ Existing
│   └── api-bridge.js       # 🆕 API communication bridge
├── foundry-module/              # 🆕 Foundry REST API Module (submodule)
├── relay-server/               # 🆕 Foundry REST API Relay Server (submodule)
├── backend.sh                  # ✅ Enhanced for submodules
├── module.json                # ✅ Updated version
└── gold box patch 0.3.0 plan.md  # ✅ This document
```

---

## Phase-Based Implementation

### Phase 1: Repository Setup (Day 1)

#### 1.1 Add Submodules
```bashssjmarx@eMachine:~/Gold Box$ cd /home/ssjmarx/Gold\ Box && git tag -d v0.3.0
Deleted tag 'v0.3.0' (was fb3c05f)
ssjmarx@eMachine:~/Gold Box$ cd /home/ssjmarx/Gold\ Box && git push origin :refs/tags/v0.3.0
To https://github.com/ssjmarx/Gold-Box.git
 - [deleted]         v0.3.0
ssjmarx@eMachine:~/Gold Box$ cd /home/ssjmarx/Gold\ Box && git tag --list | grep v0.3.0 || echo "Tag v0.3.0 successfully removed"
Tag v0.3.0 successfully removed
ssjmarx@eMachine:~/Gold Box$ curl -s "https://api.github.com/repos/ssjmarx/Gold-Box/releases" | jq -r '.[] | select(.tag_name == "v0.3.0") | .tag_name' || echo "Release v0.3.0 successfully removed from GitHub"
ssjmarx@eMachine:~/Gold Box$ 

# Navigate to Gold Box repository
cd "/home/ssjmarx/Gold Box"

# Add Foundry REST API module
git submodule add https://github.com/ThreeHats/foundryvtt-rest-api.git foundry-module

# Add Foundry REST API relay server
git submodule add https://github.com/ThreeHats/foundryvtt-rest-api-relay.git relay-server

# Initialize submodules
git submodule update --init --recursive
```

#### 1.2 Version Pinning
```bash
# Pin to latest stable releases
cd foundry-module && git checkout $(git describe --tags --abbrev=0)
cd ../relay-server && git checkout $(git describe --tags --abbrev=0)

# Commit submodule pins
git add foundry-module relay-server
git commit -m "v0.3.0: Add Foundry REST API submodules"
```

### Phase 2: Backend Integration (Days 2-3)

#### 2.1 Create API Chat Processor
Create `backend/server/api_chat_processor.py`:
```python
"""
API Chat Processor for Gold Box v0.3.0
Converts REST API chat data to compact JSON format for AI processing
"""

import json
import logging
from typing import List, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)

class APIChatProcessor:
    """Convert Foundry REST API chat data to token-efficient compact format"""
    
    def __init__(self):
        self.type_codes = {
            "chat-message": "cm",
            "dice-roll": "dr", 
            "whisper": "wp",
            "gm-message": "gm",
            "card": "cd"
        }
    
    def process_api_messages(self, api_messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Convert Foundry REST API chat messages to compact JSON format
        
        Args:
            api_messages: List of chat messages from Foundry REST API
            
        Returns:
            List of compact JSON messages for AI processing
        """
        compact_messages = []
        
        for msg in api_messages:
            try:
                compact_msg = self._convert_to_compact(msg)
                if compact_msg:
                    compact_messages.append(compact_msg)
            except Exception as e:
                logger.warning(f"Failed to process message {msg.get('id', 'unknown')}: {e}")
                continue
        
        logger.info(f"Processed {len(compact_messages)} messages from API data")
        return compact_messages
    
    def _convert_to_compact(self, api_message: Dict[str, Any]) -> Dict[str, Any]:
        """Convert single API message to compact format"""
        # Determine message type
        msg_type = self._detect_message_type(api_message)
        
        if msg_type not in self.type_codes:
            return None  # Skip unsupported message types
        
        compact_msg = {"t": self.type_codes[msg_type]}
        
        # Extract common fields
        if "content" in api_message:
            compact_msg["c"] = api_message["content"]
        
        if "author" in api_message:
            compact_msg["s"] = api_message["author"]["name"] if isinstance(api_message["author"], dict) else api_message["author"]
        
        if "timestamp" in api_message:
            compact_msg["ts"] = api_message["timestamp"]
        
        # Handle specific message types
        if msg_type == "dice-roll" and "roll" in api_message:
            compact_msg.update(self._process_dice_roll(api_message["roll"]))
        
        elif msg_type == "whisper" and "whisperTo" in api_message:
            compact_msg["tg"] = api_message["whisperTo"]
        
        return compact_msg
    
    def _detect_message_type(self, api_message: Dict[str, Any]) -> str:
        """Detect message type from API message structure"""
        if "roll" in api_message:
            return "dice-roll"
        elif "whisperTo" in api_message:
            return "whisper"
        elif "author" in api_message and api_message.get("author", {}).get("role") == "gm":
            return "gm-message"
        elif "card" in api_message:
            return "card"
        else:
            return "chat-message"
    
    def _process_dice_roll(self, roll_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process dice roll data into compact format"""
        compact_roll = {}
        
        if "formula" in roll_data:
            compact_roll["f"] = roll_data["formula"]
        
        if "result" in roll_data:
            compact_roll["r"] = roll_data["result"]
        
        if "total" in roll_data:
            compact_roll["tt"] = roll_data["total"]
        
        return compact_roll
```

#### 2.2 Create AI Chat Processor
Create `backend/server/ai_chat_processor.py`:
```python
"""
AI Chat Processor for Gold Box v0.3.0
Converts AI responses to Foundry REST API format
"""

import json
import logging
from typing import List, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)

class AIChatProcessor:
    """Convert AI responses to Foundry REST API format"""
    
    def __init__(self):
        self.reverse_type_codes = {
            "cm": "chat-message",
            "dr": "dice-roll", 
            "wp": "whisper",
            "gm": "gm-message",
            "cd": "card"
        }
    
    def process_ai_response(self, ai_response: str, context: List[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Convert AI response to Foundry REST API format
        
        Args:
            ai_response: Raw AI response string
            context: Original message context for reference
            
        Returns:
            Formatted message ready for Foundry REST API
        """
        try:
            # Try to parse compact JSON from AI response
            compact_messages = self._extract_compact_json(ai_response)
            
            if compact_messages:
                # Convert compact JSON to API format
                api_messages = []
                for compact_msg in compact_messages:
                    api_msg = self._convert_compact_to_api(compact_msg)
                    if api_msg:
                        api_messages.append(api_msg)
                
                return {
                    "type": "multi-message",
                    "messages": api_messages,
                    "success": True
                }
            else:
                # No compact JSON found, treat as simple chat message
                return {
                    "type": "chat-message",
                    "content": ai_response,
                    "author": {
                        "name": "The Gold Box AI",
                        "role": "assistant"
                    },
                    "timestamp": datetime.now().isoformat(),
                    "success": True
                }
                
        except Exception as e:
            logger.error(f"Failed to process AI response: {e}")
            return {
                "type": "chat-message",
                "content": ai_response,
                "author": {
                    "name": "The Gold Box AI",
                    "role": "assistant"
                },
                "timestamp": datetime.now().isoformat(),
                "success": True,
                "error": f"Processing error: {e}"
            }
    
    def _extract_compact_json(self, text: str) -> List[Dict[str, Any]]:
        """Extract compact JSON objects from AI response text"""
        import re
        
        # Look for JSON blocks in the response
        json_pattern = r'\{[^{}]*"t"\s*:\s*"[^"]*"[^{}]*\}'
        json_matches = re.findall(json_pattern, text, re.DOTALL)
        
        compact_messages = []
        for json_str in json_matches:
            try:
                compact_msg = json.loads(json_str)
                compact_messages.append(compact_msg)
            except json.JSONDecodeError:
                # Invalid JSON, skip
                continue
        
        return compact_messages
    
    def _convert_compact_to_api(self, compact_msg: Dict[str, Any]) -> Dict[str, Any]:
        """Convert compact message to Foundry REST API format"""
        msg_type = compact_msg.get("t", "")
        
        if msg_type not in self.reverse_type_codes:
            return None
        
        api_msg = {
            "type": self.reverse_type_codes[msg_type],
            "timestamp": datetime.now().isoformat()
        }
        
        # Handle common fields
        if "s" in compact_msg:
            api_msg["author"] = {"name": compact_msg["s"]}
        
        if "c" in compact_msg:
            api_msg["content"] = compact_msg["c"]
        
        # Handle specific message types
        if msg_type == "dr":  # dice roll
            api_msg["roll"] = self._expand_dice_roll(compact_msg)
        elif msg_type == "wp":  # whisper
            if "tg" in compact_msg:
                api_msg["whisperTo"] = compact_msg["tg"]
        
        return api_msg
    
    def _expand_dice_roll(self, compact_roll: Dict[str, Any]) -> Dict[str, Any]:
        """Expand compact dice roll to full API format"""
        expanded = {}
        
        if "f" in compact_roll:
            expanded["formula"] = compact_roll["f"]
        
        if "r" in compact_roll:
            expanded["result"] = compact_roll["r"]
        
        if "tt" in compact_roll:
            expanded["total"] = compact_roll["tt"]
        
        return expanded
```

#### 2.3 Create API Chat Endpoint
Create `backend/endpoints/api_chat.py`:
```python
"""
API Chat Endpoint for Gold Box v0.3.0
Handles chat processing via Foundry REST API instead of HTML scraping
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
import logging
import json
import asyncio
import subprocess
import os
from datetime import datetime

from server.api_chat_processor import APIChatProcessor
from server.ai_chat_processor import AIChatProcessor
from server.ai_service import AIService
from server.processor import ChatContextProcessor

# Configure logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api", tags=["api_chat"])

# Request models
class APIChatRequest(BaseModel):
    """Request model for API chat endpoint"""
    context_count: Optional[int] = Field(15, description="Number of recent messages to retrieve", ge=1, le=50)
    settings: Optional[Dict[str, Any]] = Field(None, description="Frontend settings including provider info")

class APIChatResponse(BaseModel):
    """Response model for API chat endpoint"""
    success: bool = Field(..., description="Whether the request was successful")
    response: Optional[str] = Field(None, description="AI response as formatted text")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")
    error: Optional[str] = Field(None, description="Error message if failed")

# Global instances
api_chat_processor = APIChatProcessor()
ai_chat_processor = AIChatProcessor()
ai_service = AIService(None)  # Will be initialized with provider manager
relay_server_process = None

async def ensure_relay_server():
    """Ensure relay server is running"""
    global relay_server_process
    
    # Check if relay server is already running
    try:
        import requests
        response = requests.get("http://localhost:3010/api/health", timeout=2)
        if response.status_code == 200:
            logger.info("Relay server already running")
            return True
    except:
        logger.info("Relay server not running, starting...")
    
    # Start relay server
    try:
        relay_path = "relay-server"
        if not os.path.exists(relay_path):
            logger.error("Relay server submodule not found. Run: git submodule update --init --recursive")
            return False
        
        # Start relay server as subprocess
        relay_server_process = subprocess.Popen(
            ["npm", "start"],
            cwd=relay_path,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        # Wait for it to start
        await asyncio.sleep(3)
        
        # Check if it's running
        try:
            response = requests.get("http://localhost:3010/api/health", timeout=2)
            if response.status_code == 200:
                logger.info("Relay server started successfully")
                return True
        except:
            pass
        
        logger.error("Failed to start relay server")
        return False
        
    except Exception as e:
        logger.error(f"Error starting relay server: {e}")
        return False

@router.post("/api_chat", response_model=APIChatResponse)
async def api_chat(request: APIChatRequest):
    """
    Process chat using Foundry REST API instead of HTML scraping
    
    This endpoint:
    1. Ensures relay server is running
    2. Collects chat messages via REST API
    3. Converts to compact JSON for AI processing
    4. Processes through AI services
    5. Returns formatted response
    """
    try:
        # Step 1: Ensure relay server is running
        if not await ensure_relay_server():
            return APIChatResponse(
                success=False,
                error="Failed to start relay server"
            )
        
        # Step 2: Collect chat messages via REST API
        logger.info(f"Collecting {request.context_count} chat messages via REST API")
        api_messages = await collect_chat_messages_api(request.context_count)
        
        # Step 3: Convert to compact JSON
        compact_messages = api_chat_processor.process_api_messages(api_messages)
        
        # Step 4: Process through AI (reuse existing logic)
        if not request.settings:
            # Use default settings for backward compatibility
            request.settings = {
                'general llm provider': 'openai',
                'general llm model': 'gpt-3.5-turbo',
                'general llm base url': None,
                'general llm timeout': 30,
                'general llm max retries': 3,
                'general llm custom headers': None
            }
        
        # Convert compact messages to JSON string for AI
        compact_json_context = json.dumps(compact_messages, indent=2)
        
        # Prepare AI messages
        from server.processor import ChatContextProcessor
        processor = ChatContextProcessor()
        system_prompt = processor.generate_system_prompt()
        
        ai_messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Chat Context (Compact JSON Format):\n{compact_json_context}\n\nPlease respond to this conversation as an AI assistant for tabletop RPGs."}
        ]
        
        # Call AI service
        ai_response_data = await ai_service.process_compact_context(
            processed_messages=compact_messages,
            system_prompt=system_prompt,
            settings=request.settings
        )
        
        ai_response = ai_response_data.get("response", "")
        tokens_used = ai_response_data.get("tokens_used", 0)
        
        # Step 5: Process AI response back to API format (for future use)
        api_formatted = ai_chat_processor.process_ai_response(ai_response, compact_messages)
        
        # For now, return the text response for display
        return APIChatResponse(
            success=True,
            response=ai_response,
            metadata={
                "context_count": len(compact_messages),
                "tokens_used": tokens_used,
                "api_formatted": api_formatted
            }
        )
        
    except Exception as e:
        logger.error(f"API chat processing error: {e}")
        return APIChatResponse(
            success=False,
            error=str(e)
        )

async def collect_chat_messages_api(count: int) -> List[Dict[str, Any]]:
    """Collect recent chat messages via Foundry REST API"""
    try:
        import requests
        
        # Get chat messages from relay server
        response = requests.get(
            f"http://localhost:3010/api/chat/messages",
            params={"limit": count, "sort": "timestamp", "order": "desc"},
            timeout=10
        )
        
        if response.status_code == 200:
            messages = response.json()
            # Reverse to get chronological order (oldest first)
            return list(reversed(messages))
        else:
            logger.error(f"Failed to collect chat messages: {response.status_code}")
            return []
            
    except Exception as e:
        logger.error(f"Error collecting chat messages via API: {e}")
        return []
```

#### 2.4 Update Main Server
Modify `backend/server.py` to include the new endpoint:
```python
# Add to imports near the top
from endpoints.api_chat import router as api_chat_router

# After the existing router includes
app.include_router(api_chat_router)
```

### Phase 3: Frontend Integration (Day 4)

#### 3.1 Update Frontend Settings
Modify `scripts/gold-box.js` to add API Chat mode:
```javascript
// In the registerHooks() method, update the chatProcessingMode setting

// Register Chat Processing Mode setting
game.settings.register('gold-box', 'chatProcessingMode', {
    name: "Chat Processing Mode",
    hint: "Choose how AI processes chat messages",
    scope: "world",
    config: true,
    type: String,
    choices: {
        "simple": "Simple (existing /api/simple_chat)",
        "processed": "Processed (existing /api/process_chat)",
        "api": "API Chat (new REST API mode)"
    },
    default: "simple"
});
```

#### 3.2 Update Message Collection
Modify the `sendMessageContext` method to handle API mode:
```javascript
// In GoldBoxAPI.sendMessageContext() method

async sendMessageContext(messages) {
    try {
        // Choose endpoint based on processing mode
        const processingMode = game.settings.get('gold-box', 'chatProcessingMode') || 'simple';
        let endpoint;
        let requestData;
        
        switch(processingMode) {
            case 'api':
                endpoint = '/api/api_chat';
                // For API mode, just send context count, not the messages
                requestData = {
                    context_count: game.settings.get('gold-box', 'maxMessageContext') || 15,
                    settings: this.getFrontendSettings()
                };
                break;
            case 'processed':
                endpoint = '/api/process_chat';
                requestData = {
                    settings: this.getFrontendSettings(),
                    messages: messages
                };
                break;
            default: // simple
                endpoint = '/api/simple_chat';
                requestData = {
                    settings: this.getFrontendSettings(),
                    messages: messages
                };
        }
        
        console.log(`The Gold Box: Using ${processingMode} mode, endpoint: ${endpoint}`);
        
        // Use ConnectionManager for request
        const response = await this.connectionManager.makeRequest(endpoint, requestData);
        
        return response;
        
    } catch (error) {
        console.error('Gold Box API Error:', error);
        throw error;
    }
}
```

### Phase 4: Deployment Updates (Day 5)

#### 4.1 Update backend.sh
Enhance `backend.sh` to handle submodules:
```bash
#!/bin/bash

# The Gold Box - Backend Launcher v0.3.0
# Enhanced for REST API integration

set -e  # Exit on any error

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check and initialize submodules
check_submodules() {
    log_info "Checking submodules..."
    
    if [ ! -d "foundry-module" ] || [ ! -d "relay-server" ]; then
        log_info "Initializing submodules..."
        git submodule update --init --recursive
        log_success "Submodules initialized"
    else
        log_info "Submodules already exist"
    fi
    
    # Check if submodules are properly initialized
    if [ ! -f "foundry-module/package.json" ] || [ ! -f "relay-server/package.json" ]; then
        log_error "Submodules not properly initialized"
        log_error "Run: git submodule update --init --recursive"
        exit 1
    fi
    
    log_success "Submodules verified"
}

# Install Node.js dependencies for relay server
install_relay_dependencies() {
    log_info "Installing relay server dependencies..."
    
    cd relay-server
    
    # Check if node_modules exists
    if [ ! -d "node_modules" ]; then
        if command -v npm >/dev/null 2>&1; then
            npm install
            log_success "Relay server dependencies installed"
        else
            log_warning "npm not found, relay server will need manual setup"
        fi
    else
        log_info "Relay server dependencies already installed"
    fi
    
    cd ..
}

# Check if we're in the right directory
check_project_structure() {
    log_info "Checking project structure..."
    
    if [ ! -f "module.json" ]; then
        log_error "module.json not found!"
        log_error "Please run this script from the Gold Box module directory."
        exit 1
    fi
    
    if [ ! -d "backend" ]; then
        log_error "backend directory not found!"
        log_error "Please run this script from the Gold Box module directory."
        exit 1
    fi
    
    log_success "Project structure verified"
}

# Check Python version and availability
check_python() {
    log_info "Checking Python installation..."
    
    # Try different Python commands
    PYTHON_CMD=""
    for cmd in python3 python; do
        if command -v "$cmd" >/dev/null 2>&1; then
            PYTHON_VERSION=$($cmd --version 2>&1 | awk '{print $2}')
            PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
            PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)
            
            if [ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -ge 8 ]; then
                PYTHON_CMD="$cmd"
                log_success "Found Python $PYTHON_VERSION"
                break
            else
                log_warning "Found Python $PYTHON_VERSION, but version 3.8+ is required"
            fi
        fi
    done
    
    if [ -z "$PYTHON_CMD" ]; then
        log_error "Python 3.8 or higher is required but not found"
        log_error "Please install Python 3.8+:"
        log_error "  Ubuntu/Debian: sudo apt install python3 python3-pip python3-venv"
        log_error "  macOS: brew install python@3.10"
        log_error "  Windows: Use python.org installer"
        exit 1
    fi
    
    log_success "Python and pip availability verified"
}

# Create virtual environment if it doesn't exist
create_virtual_environment() {
    log_info "Checking virtual environment..."
    
    VENV_PATH="backend/venv"
    
    if [ ! -d "$VENV_PATH" ]; then
        log_info "Creating Python virtual environment..."
        $PYTHON_CMD -m venv "$VENV_PATH"
        log_success "Virtual environment created"
    else
        log_info "Virtual environment already exists"
    fi
    
    log_success "Virtual environment verified"
}

# Activate virtual environment
activate_virtual_environment() {
    log_info "Activating virtual environment..."
    
    VENV_PATH="backend/venv"
    
    if [ -f "$VENV_PATH/bin/activate" ]; then
        source "$VENV_PATH/bin/activate"
        log_success "Virtual environment activated (Unix)"
    elif [ -f "$VENV_PATH/Scripts/activate" ]; then
        source "$VENV_PATH/Scripts/activate"
        log_success "Virtual environment activated (Windows)"
    else
        log_error "Virtual environment activation script not found"
        exit 1
    fi
    
    log_success "Virtual environment active: $VIRTUAL_ENV"
}

# Install and upgrade dependencies
install_dependencies() {
    log_info "Installing dependencies..."
    
    cd backend
    
    # Check if requirements.txt exists
    if [ ! -f "requirements.txt" ]; then
        log_warning "requirements.txt not found, skipping dependency installation"
        cd ..
        return
    fi
    
    # Upgrade pip first
    log_info "Upgrading pip..."
    python -m pip install --upgrade pip >/dev/null 2>&1
    
    # Install requirements
    log_info "Installing Python dependencies..."
    python -m pip install -r requirements.txt
    log_success "Dependencies installed"
    
    cd ..
}

# Start the server
start_server() {
    log_info "Starting backend server..."
    echo "=================================================="
    echo " The Gold Box Backend Server v0.3.0 is Starting..."
    echo " With Foundry REST API Integration"
    echo "=================================================="
    
    cd backend
    
    # Run server.py directly
    python server.py
}

# Main execution flow
main() {
    echo "The Gold Box v0.3.0 - Unified Backend Setup & Start Script"
    echo "=================================================="
    
    check_project_structure
    check_submodules
    install_relay_dependencies
    check_python
    create_virtual_environment
    activate_virtual_environment
    install_dependencies
    start_server
}

# Run main function
main "$@"
```

#### 4.2 Update Module Version
Update `module.json`:
```json
{
  "id": "gold-box",
  "title": "The Gold Box",
  "description": "An AI-powered Foundry VTT module that provides intelligent TTRPG assistance through a sophisticated Python backend with REST API integration.",
  "version": "0.3.0",
  "url": "https://github.com/ssjmarx/Gold-Box",
  "license": "CC-BY-NC-SA-4.0",
  "readme": "https://github.com/ssjmarx/Gold-Box/blob/main/README.md",
  "bugs": "https://github.com/ssjmarx/Gold-Box/issues",
  "changelog": "https://github.com/ssjmarx/Gold-Box/blob/main/CHANGELOG.md",
  "esmodules": [
    "scripts/connection-manager.js",
    "scripts/gold-box.js"
  ],
  "styles": [
    "styles/gold-box.css"
  ],
  "languages": [
    {
      "lang": "en",
      "name": "English",
      "path": "lang/en.json"
    }
  ],
  "socket": true,
  "manifest": "https://github.com/ssjmarx/Gold-Box/releases/latest/download/module.json",
  "download": "https://github.com/ssjmarx/Gold-Box/releases/latest/download/module.zip",
  "compatibility": {
    "minimum": "12",
    "verified": "13"
  }
}
```

### Phase 5: GitHub Release Action (Day 6)

#### 5.1 Review and Update Release Workflow
The existing GitHub release workflow should be updated to include submodule contents. The key change is ensuring that when creating the release zip, the submodule contents are included.

```yaml
# .github/workflows/release.yml - Key additions
- name: Checkout submodules
  run: |
    git submodule update --init --recursive
    git submodule foreach --recursive git pull origin main

- name: Build package
  run: |
    # Create package directory
    mkdir -p package
    cp -r * package/ 2>/dev/null || true
    cp -r .* package/ 2>/dev/null || true
    
    # Ensure submodules are included
    cp -r foundry-module package/ 2>/dev/null || true
    cp -r relay-server package/ 2>/dev/null || true
    
    # Create zip
    cd package
    zip -r ../module.zip .
    cd ..

- name: Upload Release Asset
  uses: actions/upload-release-asset@v1
  with:
    upload_url: ${{ steps.create_release.outputs.upload_url }}
    asset_path: ./module.zip
    asset_name: module.zip
    asset_content_type: application/zip
```

# Patch Part 2: Correctly Connecting to Relay Server from Frontend

## Streamlined Plan - Core Functionality Only:

### Goal: Make API Chat endpoint work by getting client ID from frontend to backend

### Phase 1: Frontend Client ID Storage

__Objective__: Store relay client ID in universal settings so backend can use it

1. __Add Client ID to Universal Settings__

   - Extend universal settings to include: `relayClientId: string`
   - When WebSocket connects successfully, store the client ID
   - When WebSocket disconnects, clear or null out the client ID

2. __Update WebSocketManager Integration__

   - Add method to get current client ID for external access
   - Trigger universal settings update when connection state changes
   - Keep it simple - just store the ID, no complex status tracking

### Phase 2: Backend Integration

__Objective__: Use the stored client ID instead of hardcoded "default"

1. __Update API Chat Endpoint__

   - Accept `clientId` parameter from universal settings
   - Use provided client ID when calling relay server `/chat/messages`
   - Keep existing fallback behavior if no client ID provided

2. __Modify "Take AI Turn" Logic__

   - Read client ID from universal settings passed to backend
   - Pass it to the API chat processor
   - Continue to work if no client ID (current behavior)

### Phase 3: Basic Connection Management

__Objective__: Ensure frontend automatically connects and stores client ID

1. __Ensure WebSocket Auto-Connection__

   - Verify WebSocket connects automatically on Foundry startup
   - Confirm client ID gets stored when connection succeeds
   - Handle basic connection errors gracefully

2. __Add Simple Rediscover Function__

   - Extend existing "rediscover backend" to also check WebSocket
   - Reconnect WebSocket if needed
   - Update stored client ID after successful connection

## Minimal Implementation Details:

### Frontend Changes:

```typescript
// In universal settings object
const universalSettings = {
  // ... existing settings
  relayClientId: wsManager?.getClientId() || null
};

// In WebSocketManager - when connection succeeds
updateUniversalSettings({ relayClientId: this.clientId });
```

### Backend Changes:

```python
# In api_chat.py
def collect_chat_messages(context_count, request_data=None):
    # Use client ID from request instead of hardcoded "default"
    client_id = request_data.get('relayClientId') if request_data else None
    if not client_id:
        client_id = "default"  # Fallback to current behavior
    
    # Use the client_id in relay server request
```

## Benefits of This Simplified Approach:

- __Fast Implementation__: Focuses on the core problem only
- __Minimal Risk__: Doesn't disrupt existing functionality
- __Quick Wins__: API chat endpoint should work immediately after implementation
- __Easy Testing__: Clear success criteria (client ID gets passed and used)

## Success Criteria:

1. ✅ Frontend connects to relay server on startup
2. ✅ Client ID gets stored in universal settings
3. ✅ Backend receives and uses client ID in API calls
4. ✅ `/api/api_chat` works with real Foundry client context
5. ✅ Fallback behavior still works when no client ID

This approach gets us from "API chat doesn't work" to "API chat works with real Foundry data" with the minimum necessary changes. We can always add the fancy connection status UI later.

---

## Success Criteria

### Technical Success Criteria
- [ ] Foundry REST API submodules added and initialized
- [ ] Relay server starts automatically when needed
- [ ] API Chat endpoint (`/api/api_chat`) functional
- [ ] Frontend "API Chat" mode working
- [ ] Chat messages collected via REST API instead of HTML scraping
- [ ] AI responses processed and displayed correctly
- [ ] Backward compatibility maintained with existing modes

### User Experience Criteria
- [ ] Settings include "API Chat" option
- [ ] Backend.sh automatically handles submodules
- [ ] Installation via Foundry manifest includes all necessary files
- [ ] Error handling provides clear user feedback
- [ ] Performance comparable to existing modes

### Release Readiness Criteria
- [ ] All new functionality tested
- [ ] Documentation updated
- [ ] GitHub release workflow includes submodules
- [ ] Version bumped to 0.3.0
- [ ] CHANGELOG.md updated with new features

---

## Implementation Timeline

**Day 1**: Repository setup and submodule integration
**Day 2**: Backend API chat processor implementation  
**Day 3**: Backend AI chat processor and endpoint integration
**Day 4**: Frontend settings and API mode integration
**Day 5**: Deployment scripts and module updates
**Day 6**: GitHub release workflow verification and testing

**Total Estimated Time: 6 days**

---

## Key Benefits of v0.3.0

### Immediate Benefits
- **Robust Data Collection**: REST API is more reliable than HTML scraping
- **Future Extensibility**: Foundation for advanced Foundry integration
- **Backward Compatibility**: All existing functionality preserved
- **Simplified Maintenance**: API-based approach is easier to maintain

### Long-term Benefits
- **Performance**: More efficient data collection and processing
- **Reliability**: Less prone to breaking from Foundry UI changes
- **Scalability**: Easy to extend to other Foundry data types
- **Professional**: Clean separation of concerns between frontend and backend

---

## Conclusion

Gold Box v0.3.0 focuses on the core milestone of implementing REST API-based chat processing while maintaining the simplicity and reliability that users expect. This approach:

1. **Maintains Simplicity**: No Docker, no complex deployment, system-agnostic setup
2. **Proves Concept**: Establishes REST API approach for future enhancements  
3. **Preserves Compatibility**: All existing functionality remains intact
4. **Enables Growth**: Foundation for advanced Foundry integration features

This focused approach delivers significant technical benefits while avoiding scope creep, ensuring a timely and stable 0.3.0 release that brings Gold Box closer to public readiness.
