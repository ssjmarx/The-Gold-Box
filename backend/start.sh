#!/bin/bash

# Gold Box Backend Production Launcher with Key Management

# Function to run key management
manage_keys() {
    local keychange=$1
    echo "Gold Box - Starting Key Management..."
    
    # Change to backend directory for key management
    cd "$(dirname "$0")"
    
    # Check if keychange flag is set or no key file exists
    if [ "$keychange" = "true" ] || [ ! -f "keys.enc" ]; then
        echo "Running key setup wizard..."
        python3 -c "
import sys
import getpass
sys.path.append('.')
from key_manager import MultiKeyManager

manager = MultiKeyManager()
if manager.interactive_setup():
    print('\nSet encryption password for your keys.')
    print('This password will be required on every server startup.')
    password = getpass.getpass('Encryption password (blank for unencrypted): ')
    manager.save_keys(manager.keys_data, password if password else None)
else:
    exit(1)
        "
        
        if [ $? -ne 0 ]; then
            echo "Key setup cancelled or failed"
            exit 1
        fi
    fi
    
    # Load keys (encrypted or unencrypted)
    echo "Loading API keys..."
    python3 -c "
import sys
import getpass
sys.path.append('.')
from key_manager import MultiKeyManager

manager = MultiKeyManager()
if manager.load_keys():
    manager.set_environment_variables()
else:
    print('Failed to load keys')
    exit(1)
        "
    
    if [ $? -ne 0 ]; then
        echo "Failed to load API keys"
        exit 1
    fi
    
    echo "API keys loaded successfully"
}

# Check for keychange flag
if [ "$1" = "-keychange" ]; then
    manage_keys "true"
else
    manage_keys "false"
fi

# Get configuration from environment or use defaults
BIND_ADDRESS=${BACKEND_BIND:-0.0.0.0:5001}
WORKERS=${BACKEND_WORKERS:-2}
ACCESS_LOG=${BACKEND_ACCESS_LOG:--}
ERROR_LOG=${BACKEND_ERROR_LOG:--}
TIMEOUT=${BACKEND_TIMEOUT:-30}

# Set production CORS origins (fallback to localhost if not configured)
CORS_ORIGINS=${CORS_ORIGINS:-http://localhost:30000,http://127.0.0.1:30000,http://localhost:30001,http://127.0.0.1:30001,http://localhost:30002,http://127.0.0.1:30002}

echo "Starting Gold Box Backend with Gunicorn..."
echo "Bind: $BIND_ADDRESS"
echo "Workers: $WORKERS"
echo "Timeout: ${TIMEOUT}s"

# Set production environment variables
export FLASK_ENV=production
export PRODUCTION_MODE=true
export CORS_ORIGINS="$CORS_ORIGINS"

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    echo "Activating virtual environment..."
    source venv/bin/activate
    echo "Virtual environment activated ✓"
else
    echo "Warning: No virtual environment found, using system Python"
fi

# Start Gunicorn with production-safe settings
exec gunicorn \
    --bind "$BIND_ADDRESS" \
    --workers "$WORKERS" \
    --timeout "$TIMEOUT" \
    --access-logfile "$ACCESS_LOG" \
    --error-logfile "$ERROR_LOG" \
    --worker-class sync \
    --max-requests 1000 \
    --max-requests-jitter 100 \
    --preload \
    server:app
