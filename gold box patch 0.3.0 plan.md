# Gold Box v0.3.0 Integration Plan
## Foundry REST API Integration

### Objective
Integrate Foundry REST API module and relay server into Gold Box to provide comprehensive Foundry data access for AI services, enabling advanced features like token manipulation, board state awareness, and action execution.

### Version Information
- **Target Version**: Gold Box v0.3.0
- **Integration Date**: November 2025
- **Priority**: HIGH - This integration brings Gold Box much closer to public release

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

## Integration Strategy

### Repository Structure Changes

#### Target Structure
```
Gold-Box/
├── backend/                    # ✅ Existing Python FastAPI
│   ├── server.py             # Main backend server
│   ├── requirements.txt         # Python dependencies
│   └── endpoints/              # Gold Box API endpoints
├── scripts/                    # ✅ Existing orchestration
├── foundry-module/              # 🆕 Foundry REST API Module
│   ├── src/ts/               # TypeScript code for Foundry
│   ├── module.json           # Foundry module manifest
│   └── styles/               # CSS for Foundry UI
├── relay-server/               # 🆕 Foundry REST API Relay Server
│   ├── src/                  # Node.js/TypeScript server
│   ├── package.json          # Relay dependencies
│   └── docker-compose.yml     # Relay deployment
├── integration/                 # 🆕 Gold Box integration layer
│   ├── relay_client.py        # Python client for relay server
│   ├── foundry_bridge.py      # Bridge between Gold Box and Foundry
│   ├── api_key_manager.py    # Automatic API key generation
│   └── config_manager.py     # Configuration management
├── docker-compose.yml             # 🆕 Unified deployment file
└── gold box patch 0.3.0 plan.md  # 🆕 This document
```

---

## Phase-Based Implementation

### Phase 1: Repository Setup (Day 1-2)

#### 1.1 Add Submodules
```bash
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
# Pin specific versions for stability
cd foundry-module && git checkout v1.2.0
cd ../relay-server && git checkout v2.0.16

# Commit submodule pins
git add foundry-module relay-server
git commit -m "Pin Foundry module v1.2.0 and relay server v2.0.16"
```

#### 1.3 Create Integration Directory
```bash
# Create integration layer directory
mkdir -p integration
touch integration/__init__.py

# Create integration files
touch integration/relay_client.py
touch integration/foundry_bridge.py
touch integration/api_key_manager.py
touch integration/config_manager.py
```

### Phase 2: Backend Integration (Day 3-5)

#### 2.1 Relay Client Integration
Create `integration/relay_client.py`:
```python
import requests
import json
import asyncio
from typing import Dict, Any, Optional

class RelayClient:
    """Client for communicating with embedded Foundry REST API relay server"""
    
    def __init__(self, relay_url: str = "http://localhost:3010"):
        self.relay_url = relay_url
        self.api_key = None
        self.session = requests.Session()
        
    async def register_service(self, service_name: str) -> Dict[str, Any]:
        """Register Gold Box service with relay server"""
        try:
            response = self.session.post(
                f"{self.relay_url}/api/register",
                json={"service_name": service_name, "description": "Gold Box AI Service"}
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {"error": str(e)}
    
    async def create_session(self, client_id: str) -> Dict[str, Any]:
        """Create WebSocket session for Foundry connection"""
        try:
            response = self.session.post(
                f"{self.relay_url}/api/session/init",
                json={"client_id": client_id}
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {"error": str(e)}
    
    def send_to_foundry(self, endpoint: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Send data to Foundry through relay server"""
        try:
            response = self.session.post(
                f"{self.relay_url}/api/{endpoint}",
                json=data,
                headers={"X-API-Key": self.api_key}
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {"error": str(e)}
```

#### 2.2 Foundry Bridge
Create `integration/foundry_bridge.py`:
```python
import asyncio
import websockets
import json
from typing import Dict, Any, List
from .relay_client import RelayClient
from .api_key_manager import APIKeyManager

class FoundryBridge:
    """Bridge between Gold Box backend and Foundry VTT - CONTROLLER LAYER"""
    
    def __init__(self):
        self.relay_client = RelayClient()
        self.api_key_manager = APIKeyManager()
        self.active_sessions = {}
        
    async def initialize_bridge(self):
        """Initialize bridge with auto-generated API key"""
        # Get or create API key for relay communication
        api_key = await self.api_key_manager.get_or_create_key("gold_box_relay")
        self.relay_client.api_key = api_key
        
        # Register Gold Box service with relay server
        registration = await self.relay_client.register_service("gold-box")
        if "error" not in registration:
            print(f"Gold Box registered with relay: {registration['id']}")
            return True
        else:
            print(f"Registration failed: {registration['error']}")
            return False
    
    async def send_foundry_command(self, command: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Send Gold Box AI commands to Foundry through relay server"""
        # Pre-process AI command for Foundry compatibility
        foundry_action = self._convert_to_foundry_format(command, params)
        
        # Send through relay server
        response = self.relay_client.send_to_foundry("utility", foundry_action)
        return response
    
    async def get_foundry_data(self, endpoint: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """Retrieve data from Foundry through relay server"""
        try:
            if params:
                response = self.session.post(
                    f"{self.relay_url}/api/{endpoint}",
                    json=params,
                    headers={"X-API-Key": self.relay_client.api_key}
                )
            else:
                response = self.session.get(
                    f"{self.relay_url}/api/{endpoint}",
                    headers={"X-API-Key": self.relay_client.api_key}
                )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {"error": str(e)}
    
    def _convert_to_foundry_format(self, command: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Convert Gold Box AI commands to Foundry REST API format"""
        # Map AI commands to Foundry endpoints
        command_mapping = {
            "move_token": {"endpoint": "move", "method": "POST"},
            "select_token": {"endpoint": "select", "method": "POST"},
            "roll_dice": {"endpoint": "roll", "method": "POST"},
            "get_board_state": {"endpoint": "structure", "method": "GET"},
            "search_items": {"endpoint": "search", "method": "POST"},
            "get_scenes": {"endpoint": "structure", "method": "GET"},
            "get_tokens": {"endpoint": "entity", "method": "GET"},
            "modify_token": {"endpoint": "entity", "method": "POST"},
            "create_item": {"endpoint": "entity", "method": "POST"},
            "get_actors": {"endpoint": "entity", "method": "GET"}
        }
        
        if command in command_mapping:
            return {
                **command_mapping[command],
                "data": {**params, "source": "gold_box_ai"}
            }
        else:
            return {"error": f"Unknown command: {command}"}
```

#### 2.3 API Key Manager
Create `integration/api_key_manager.py`:
```python
import secrets
import hashlib
import json
import time
from pathlib import Path

class APIKeyManager:
    """Automatic API key generation and management for Gold Box integration"""
    
    def __init__(self, keys_file: str = "integration/api_keys.json"):
        self.keys_file = Path(keys_file)
        self.keys = self._load_keys()
    
    def _load_keys(self) -> Dict[str, str]:
        """Load existing API keys"""
        if self.keys_file.exists():
            with open(self.keys_file, 'r') as f:
                return json.load(f)
        return {}
    
    def _save_keys(self):
        """Save API keys to file"""
        with open(self.keys_file, 'w') as f:
            json.dump(self.keys, f, indent=2)
    
    async def get_or_create_key(self, service_name: str) -> str:
        """Get existing key or create new one"""
        if service_name in self.keys:
            return self.keys[service_name]
        
        # Generate new API key
        new_key = self._generate_secure_key(service_name)
        self.keys[service_name] = new_key
        self._save_keys()
        return new_key
    
    def _generate_secure_key(self, service_name: str) -> str:
        """Generate cryptographically secure API key"""
        # Create seed from service name + timestamp + random
        seed = f"{service_name}_{int(time.time())}_{secrets.token_urlsafe(16)}"
        
        # Generate API key
        api_key = hashlib.sha256(seed.encode()).hexdigest()[:32]
        return f"gb_{api_key}"
    
    def validate_key(self, api_key: str) -> bool:
        """Validate API key format and existence"""
        return (
            api_key.startswith("gb_") and
            len(api_key) == 35 and  # gb_ + 32 char hash
            api_key in self.keys.values()
        )
```

#### 2.4 Backend Server Integration
Modify `backend/server.py` to include integration:
```python
# Add to imports
from integration.foundry_bridge import FoundryBridge
from integration.api_key_manager import APIKeyManager

# Add to server initialization
foundry_bridge = None

@app.on_event("startup")
async def startup_event():
    global foundry_bridge
    foundry_bridge = FoundryBridge()
    await foundry_bridge.initialize_bridge()
    print("Gold Box Bridge initialized with Foundry REST API")

# Add new endpoint for Foundry commands
@app.post("/api/foundry-command")
async def foundry_command(request: FoundryCommandRequest):
    """Process Gold Box AI commands for Foundry VTT"""
    if not foundry_bridge:
        return {"error": "Foundry bridge not initialized"}
    
    result = await foundry_bridge.send_foundry_command(
        request.command, 
        request.params
    )
    return result

# Add endpoint for Foundry data retrieval
@app.get("/api/foundry-data/{endpoint}")
async def foundry_data(endpoint: str, params: Dict[str, str] = None):
    """Retrieve Foundry data through bridge"""
    if not foundry_bridge:
        return {"error": "Foundry bridge not initialized"}
    
    result = await foundry_bridge.get_foundry_data(endpoint, params)
    return result

# Add health check for bridge
@app.get("/api/bridge-status")
async def bridge_status():
    """Check status of Gold Box to Foundry bridge"""
    if foundry_bridge:
        return {
            "status": "active",
            "bridge_initialized": True,
            "relay_connected": foundry_bridge.relay_client.api_key is not None
        }
    else:
        return {"status": "inactive", "bridge_initialized": False}
```

### Phase 3: Frontend Enhancements (Day 6-8)

#### 3.1 Modified Foundry Module Integration
Create custom Gold Box frontend for Foundry integration:
```javascript
// foundry-module/scripts/gold-box-bridge.js
class GoldBoxBridge {
    constructor() {
        this.relayUrl = game.settings.get('gold-box.relay-url') || 'ws://localhost:3010';
        this.apiKey = game.settings.get('gold-box.api-key');
        this.isConnected = false;
    }
    
    async initialize() {
        try {
            // Connect to embedded relay server
            this.socket = new WebSocket(this.relayUrl);
            
            this.socket.onopen = () => {
                console.log('Gold Box connected to Foundry REST API relay');
                this.isConnected = true;
                ui.notifications.info('Gold Box Bridge Active');
            };
            
            this.socket.onmessage = (event) => {
                const message = JSON.parse(event.data);
                this.handleRelayMessage(message);
            };
            
        } catch (error) {
            console.error('Failed to connect to relay:', error);
            ui.notifications.error('Gold Box Bridge Connection Failed');
        }
    }
    
    handleRelayMessage(message) {
        switch(message.type) {
            case 'ai_command':
                this.executeAICommand(message.data);
                break;
            case 'token_update':
                this.updateTokenDisplay(message.data);
                break;
            case 'board_sync':
                this.syncBoardState(message.data);
                break;
        }
    }
    
    async executeAICommand(data) {
        // Execute Gold Box AI commands in Foundry
        const command = data.command;
        const params = data.parameters;
        
        switch(command) {
            case 'move_token':
                await this.moveToken(params);
                break;
            case 'select_token':
                await this.selectToken(params);
                break;
            case 'roll_dice':
                await this.rollDice(params);
                break;
            case 'get_board_state':
                await this.getBoardState(params);
                break;
        }
    }
    
    async moveToken(params) {
        if (params.tokenId) {
            const token = canvas.tokens.get(params.tokenId);
            if (token && params.destination) {
                await token.document.update({x: params.destination.x, y: params.destination.y});
                ui.notifications.info(`Token moved by AI: ${token.name}`);
            }
        }
    }
    
    async selectToken(params) {
        if (params.tokenIds) {
            const tokens = params.tokenIds.map(id => canvas.tokens.get(id));
            if (tokens.length > 0) {
                for (const token of tokens) {
                    token.control({release: false});
                }
                await canvas.tokens.releaseAll();
                
                for (const token of tokens) {
                    token.control();
                }
                ui.notifications.info(`${tokens.length} token(s) selected by AI`);
            }
        }
    }
}

// Register hook for initialization
Hooks.on('ready', () => {
    window.goldBoxBridge = new GoldBoxBridge();
    window.goldBoxBridge.initialize();
});
```

#### 3.2 Enhanced Module Settings
Add to `foundry-module/src/ts/settings.ts`:
```typescript
// Gold Box specific settings
export interface GoldBoxSettings {
    relayUrl: string;
    apiKey: string;
    autoConnect: boolean;
    aiCommandsEnabled: boolean;
    boardSyncInterval: number;
}

export const goldBoxSettings: GoldBoxSettings = {
    relayUrl: 'ws://localhost:3010',
    apiKey: '',  // Will be auto-generated
    autoConnect: true,
    aiCommandsEnabled: true,
    boardSyncInterval: 30000  // 30 seconds
};

export function registerGoldBoxSettings() {
    // Register Gold Box specific settings in Foundry
    game.settings.register('gold-box.relay-url', {
        name: 'Gold Box Relay URL',
        hint: 'WebSocket URL for Gold Box relay server',
        scope: 'world',
        config: true,
        type: String,
        default: goldBoxSettings.relayUrl
    });
    
    game.settings.register('gold-box.api-key', {
        name: 'Gold Box API Key',
        hint: 'API key for Gold Box integration (auto-generated)',
        scope: 'world',
        config: true,
        type: String,
        default: goldBoxSettings.apiKey
    });
    
    game.settings.register('gold-box.auto-connect', {
        name: 'Auto Connect',
        hint: 'Automatically connect to relay server on startup',
        scope: 'world',
        config: true,
        type: Boolean,
        default: goldBoxSettings.autoConnect
    });
    
    game.settings.register('gold-box.ai-commands', {
        name: 'Enable AI Commands',
        hint: 'Allow AI to execute commands in Foundry',
        scope: 'world',
        config: true,
        type: Boolean,
        default: goldBoxSettings.aiCommandsEnabled
    });
}
```

### Phase 4: Unified Deployment (Day 9-12)

#### 4.1 Docker Compose Configuration
Create `docker-compose.yml`:
```yaml
version: '3.8'

services:
  # Gold Box Python Backend
  gold-box-backend:
    build: 
      context: ./backend
      dockerfile: Dockerfile
    ports:
      - "5000:5000"
    environment:
      - GOLD_BOX_PORT=5000
      - RELAY_SERVER_URL=http://relay-server:3010
      - DB_TYPE=sqlite
      - DATABASE_URL=sqlite:///goldbox.db
    volumes:
      - goldbox_data:/app/data
    depends_on:
      - relay-server
    restart: unless-stopped
    
  # Foundry REST API Relay Server
  relay-server:
    build: 
      context: ./relay-server
      dockerfile: Dockerfile
    ports:
      - "3010:3010"
    environment:
      - PORT=3010
      - NODE_ENV=production
      - DB_TYPE=memory  # Use memory store for Gold Box integration
      - CORS_ORIGINS=http://gold-box-backend:5000,http://localhost:5000
    volumes:
      - relay_data:/app/data
    restart: unless-stopped
    
  # Build Foundry Module
  foundry-module:
    build:
      context: ./foundry-module
      dockerfile: Dockerfile
    volumes:
      - ./foundry-module/dist:/app/dist
    command: ["npm", "run", "build"]
    
volumes:
  goldbox_data:
  relay_data:

networks:
  default:
    driver: bridge
```

#### 4.2 Startup Scripts
Create `scripts/start-gold-box.sh`:
```bash
#!/bin/bash
# Gold Box v0.3.0 Unified Startup Script

set -e

echo "🎮 Gold Box v0.3.0 Starting..."
echo "🔗 Foundry REST API Integration"

# Check dependencies
echo "📦 Checking dependencies..."
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose not found"
    exit 1
fi

if ! command -v git &> /dev/null; then
    echo "❌ Git not found"
    exit 1
fi

# Update submodules
echo "📥 Updating submodules..."
git submodule update --init --recursive

# Build and start services
echo "🚀 Starting Gold Box services..."
docker-compose up --build -d

# Wait for services to be ready
echo "⏳ Waiting for services to start..."
sleep 10

# Check service health
echo "🏥 Checking service health..."

# Check relay server
if curl -f http://localhost:3010/api/health &> /dev/null; then
    echo "✅ Relay server healthy"
else
    echo "❌ Relay server not responding"
    docker-compose logs relay-server
fi

# Check Gold Box backend
if curl -f http://localhost:5000/api/health &> /dev/null; then
    echo "✅ Gold Box backend healthy"
else
    echo "❌ Gold Box backend not responding"
    docker-compose logs gold-box-backend
fi

# Check bridge status
if curl -f http://localhost:5000/api/bridge-status &> /dev/null; then
    echo "✅ Gold Box to Foundry bridge active"
else
    echo "⚠️ Bridge not initialized"
fi

echo ""
echo "🎯 Gold Box v0.3.0 is running!"
echo "📋 Access points:"
echo "   Gold Box Backend: http://localhost:5000"
echo "   Relay Server: http://localhost:3010"
echo "   API Documentation: http://localhost:3010/docs"
echo "   Foundry Module: ./foundry-module/dist/"
echo ""
echo "🔧 Management commands:"
echo "   Stop: docker-compose down"
echo "   Logs: docker-compose logs [service]"
echo "   Restart: docker-compose restart [service]"
```

#### 4.3 Development Setup
Create `scripts/dev-gold-box.sh`:
```bash
#!/bin/bash
# Gold Box Development Environment Setup

echo "🔧 Gold Box v0.3.0 Development Setup"

# Start relay server in development mode
echo "🔄 Starting relay server (development)..."
cd relay-server
npm run dev &
RELAY_PID=$!

# Start Gold Box backend in development mode
echo "🔄 Starting Gold Box backend (development)..."
cd ../backend
source venv/bin/activate
python server.py &
BACKEND_PID=$!

# Build Foundry module
echo "🔨 Building Foundry module..."
cd ../foundry-module
npm run build &
BUILD_PID=$!

# Wait for services
echo "⏳ Waiting for services..."
wait $RELAY_PID $BACKEND_PID $BUILD_PID

echo "✅ All Gold Box services running in development mode"
echo "📊 Relay Server: http://localhost:3010"
echo "🤖 Gold Box Backend: http://localhost:5000"
echo "📜 Foundry Module: ./foundry-module/dist/"
```

### Phase 5: Testing & Validation (Day 13-15)

#### 5.1 Integration Testing
Create `tests/integration_test.py`:
```python
import asyncio
import aiohttp
import json
from integration.relay_client import RelayClient
from integration.foundry_bridge import FoundryBridge

async def test_gold_box_integration():
    """Comprehensive integration test suite"""
    print("🧪 Starting Gold Box v0.3.0 Integration Tests")
    
    # Test 1: Relay server connection
    print("📡 Testing relay server connection...")
    relay_client = RelayClient()
    registration = await relay_client.register_service("gold-box-test")
    
    if "error" in registration:
        print(f"❌ Relay connection failed: {registration['error']}")
        return False
    else:
        print("✅ Relay server connection successful")
    
    # Test 2: Foundry bridge initialization
    print("🌉 Testing Foundry bridge...")
    bridge = FoundryBridge()
    bridge_init = await bridge.initialize_bridge()
    
    if bridge_init:
        print("✅ Foundry bridge initialized")
    else:
        print("❌ Foundry bridge failed to initialize")
        return False
    
    # Test 3: AI command execution
    print("🤖 Testing AI command execution...")
    test_command = {
        "command": "get_board_state",
        "parameters": {"detailed": True}
    }
    
    command_result = await bridge.send_foundry_command(
        "get_board_state", 
        test_command["parameters"]
    )
    
    if "error" in command_result:
        print(f"❌ AI command failed: {command_result['error']}")
        return False
    else:
        print("✅ AI command execution successful")
        print(f"📊 Board state retrieved: {len(command_result.get('tokens', []))} tokens")
    
    # Test 4: API key management
    print("🔑 Testing API key management...")
    from integration.api_key_manager import APIKeyManager
    
    key_manager = APIKeyManager()
    test_key = await key_manager.get_or_create_key("integration_test")
    
    if key_manager.validate_key(test_key):
        print("✅ API key management working")
    else:
        print("❌ API key management failed")
        return False
    
    print("\n🎉 All integration tests passed!")
    return True

if __name__ == "__main__":
    asyncio.run(test_gold_box_integration())
```

#### 5.2 End-to-End Testing
Create `tests/e2e_test.py`:
```python
import asyncio
import aiohttp
from integration.relay_client import RelayClient

async def test_complete_workflow():
    """Test complete Gold Box → Foundry → AI workflow"""
    print("🔄 Testing Complete Gold Box Workflow")
    
    # Step 1: Gold Box registers with relay
    relay_client = RelayClient()
    reg_result = await relay_client.register_service("gold-box-e2e")
    print(f"📋 Registration: {'✅' if 'error' not in reg_result else '❌'}")
    
    # Step 2: Create Foundry session
    session_result = await relay_client.create_session("test-client-001")
    print(f"🔗 Session: {'✅' if 'error' not in session_result else '❌'}")
    
    # Step 3: Send test commands
    test_commands = [
        {"command": "select_token", "parameters": {"name": "Test Character"}},
        {"command": "roll_dice", "parameters": {"formula": "1d20+5", "reason": "Attack roll"}},
        {"command": "get_board_state", "parameters": {"tokens": True}}
    ]
    
    for i, command in enumerate(test_commands):
        result = relay_client.send_to_foundry("utility", command)
        status = "✅" if "error" not in result else "❌"
        print(f"  Command {i+1}: {status}")
        await asyncio.sleep(1)  # Rate limiting
    
    print("\n🏁 Complete workflow test finished")
    return True

if __name__ == "__main__":
    asyncio.run(test_complete_workflow())
```

---

## Success Metrics

### Technical Success Criteria
- [ ] Submodules added and pinned to specific versions
- [ ] Relay server starts successfully on port 3010
- [ ] Gold Box backend starts successfully on port 5000
- [ ] API key auto-generation working
- [ ] Foundry bridge initializes without errors
- [ ] AI commands execute in Foundry successfully
- [ ] End-to-end workflow functions properly

### Feature Success Criteria
- [ ] Token manipulation (move, select, update stats)
- [ ] Board state awareness (token positions, scene data)
- [ ] Dice rolling integration
- [ ] Search functionality (items, actors, scenes)
- [ ] Real-time synchronization
- [ ] Error handling and recovery
- [ ] Performance monitoring and logging

### Release Readiness Criteria
- [ ] All integration tests passing
- [ ] Docker deployment working
- [ ] Documentation complete
- [ ] Security audit passed
- [ ] Performance benchmarks met (<100ms response time)
- [ ] Backward compatibility maintained

---

## Implementation Commands

### Initial Setup
```bash
# Navigate to Gold Box repository
cd "/home/ssjmarx/Gold Box"

# Create integration structure
mkdir -p integration tests scripts

# Add submodules
git submodule add https://github.com/ThreeHats/foundryvtt-rest-api.git foundry-module
git submodule add https://github.com/ThreeHats/foundryvtt-rest-api-relay.git relay-server

# Initialize submodules
git submodule update --init --recursive

# Pin versions
cd foundry-module && git checkout v1.2.0
cd ../relay-server && git checkout v2.0.16

# Commit setup
git add foundry-module relay-server integration tests scripts
git commit -m "v0.3.0: Add Foundry REST API integration setup"
```

### Development Workflow
```bash
# Start development environment
./scripts/dev-gold-box.sh

# Run integration tests
python tests/integration_test.py

# Run end-to-end tests
python tests/e2e_test.py
```

### Production Deployment
```bash
# Build and deploy
docker-compose -f docker-compose.yml up -d

# Check deployment status
./scripts/start-gold-box.sh
```

---

## Risk Assessment & Mitigation

### Technical Risks
- **Version Conflicts**: Submodule versions may have API incompatibilities
  - *Mitigation*: Pin specific versions and test compatibility
  
- **Performance Overhead**: Additional relay server may impact latency
  - *Mitigation*: Use memory store for relay server, optimize queries
  
- **Complexity**: Managing three services increases deployment complexity
  - *Mitigation*: Unified Docker compose and startup scripts

### Licensing Risks
- **MIT License Compliance**: Need to maintain MIT license for relay server
  - *Mitigation*: Keep relay server as separate submodule, don't modify core
  
- **CC-BY-NC-SA Compatibility**: Ensure integration doesn't violate non-commercial clause
  - *Mitigation*: Integration is for development/research purposes

### Operational Risks
- **Single Point of Failure**: Relay server becomes critical component
  - *Mitigation*: Use memory store, implement health checks
  
- **Security Surface**: Additional API endpoints increase attack surface
  - *Mitigation*: Use existing security framework, limit API access

---

## Timeline Estimate

### Phase 1 (Repository Setup): 2 days
- Submodule integration and version pinning

### Phase 2 (Backend Integration): 3 days  
- Relay client, Foundry bridge, API key management

### Phase 3 (Frontend Enhancements): 3 days
- Modified Foundry module, settings, UI integration

### Phase 4 (Unified Deployment): 2 days
- Docker compose, startup scripts, documentation

### Phase 5 (Testing & Validation): 3 days
- Integration tests, end-to-end workflow, performance testing

**Total Estimated Time: 13 days**

---

## Post-Integration Benefits

### Immediate Benefits
- **Complete Foundry Access**: Full read/write capabilities for AI
- **Token Manipulation**: AI can move, select, and control tokens
- **Board State Awareness**: AI understands current game state
- **Command Execution**: AI can perform game actions directly
- **Self-Contained**: No external dependencies for core functionality

### Long-Term Benefits
- **Scalable Architecture**: Easy to add new AI features
- **Professional Deployment**: Docker-based, production-ready
- **Modular Design**: Components can be updated independently
- **Community Integration**: Leverages existing Foundry REST API ecosystem

### Public Release Readiness
- **Feature Complete**: Core AI-assisted gameplay functionality
- **Production Ready**: Docker deployment, health checks, monitoring
- **Well Documented**: Comprehensive setup and usage guides
- **Security Focused**: API key management, input validation, rate limiting

---

## Conclusion

This integration plan positions Gold Box v0.3.0 as a **comprehensive Foundry VTT AI assistant** with:

1. **Complete Data Access**: Full Foundry world access through REST API
2. **Intelligent Commands**: AI can manipulate game state meaningfully  
3. **Professional Architecture**: Multi-service, containerized, documented
4. **Production Ready**: Thoroughly tested, monitored, secure

The integration leverages the **mature Foundry REST API ecosystem** while maintaining Gold Box's unique AI capabilities and user experience.

**This brings Gold Box significantly closer to first public release with enterprise-grade Foundry VTT integration.**
