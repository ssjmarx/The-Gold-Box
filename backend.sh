#!/bin/bash

# The Gold Box - Backend Launcher
# Single entry point for backend setup

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

# Check if we're in the right directory
check_project_structure() {
    log_info "Checking project structure..."
    
    if [ ! -f "module.json" ]; then
        log_error "module.json not found!"
        log_error "Please run this script from The The Gold Box module directory."
        log_error "Current directory: $(pwd)"
        exit 1
    fi
    
    if [ ! -d "backend" ]; then
        log_error "backend directory not found!"
        log_error "Please run this script from the The Gold Box module directory."
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
    
    # Check pip availability
    if ! command -v pip3 >/dev/null 2>&1 && ! $PYTHON_CMD -m pip --version >/dev/null 2>&1; then
        log_error "pip is not available"
        log_error "Please install pip:"
        log_error "  Ubuntu/Debian: sudo apt install python3-pip"
        log_error "  macOS: brew install python@3.10 (includes pip)"
        exit 1
    fi
    
    log_success "Python and pip availability verified"
}

# Node.js is no longer required - removed relay server dependency
# This function is kept for compatibility but does nothing
check_nodejs() {
    log_info "Node.js check skipped (relay server removed)"
    log_success "WebSocket integration eliminates external dependencies"
}

# Install Node.js based on operating system
install_nodejs() {
    log_info "Installing Node.js for your operating system..."
    
    # Detect OS
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        # Linux
        log_info "Detected Linux. Installing Node.js via NodeSource repository..."
        
        # Check if we can use sudo
        if ! command -v sudo >/dev/null 2>&1; then
            log_error "sudo is required for Node.js installation on Linux"
            log_error "Please install Node.js manually:"
            log_error "  Visit https://nodejs.org/ and download the Linux binaries"
            log_error "  Or use your distribution's package manager"
            exit 1
        fi
        
        # Install Node.js via NodeSource (official method)
        log_info "Adding NodeSource repository..."
        if curl -fsSL https://deb.nodesource.com/setup_current.x | sudo -E bash -; then
            log_info "Installing Node.js (latest version)..."
            if sudo apt-get install -y nodejs; then
                log_success "Node.js installed successfully"
            else
                log_error "Failed to install Node.js"
                log_error "Please install Node.js manually from https://nodejs.org/"
                exit 1
            fi
        else
            log_error "Failed to add NodeSource repository"
            log_error "Please install Node.js manually from https://nodejs.org/"
            exit 1
        fi
        
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        log_info "Detected macOS. Checking for Homebrew..."
        
        if command -v brew >/dev/null 2>&1; then
            log_info "Installing Node.js via Homebrew..."
            if brew install node; then
                log_success "Node.js installed successfully via Homebrew"
            else
                log_error "Failed to install Node.js via Homebrew"
                log_error "Please install Node.js manually from https://nodejs.org/"
                exit 1
            fi
        else
            log_warning "Homebrew not found"
            log_info "Please install Node.js manually:"
            log_error "  1. Visit https://nodejs.org/"
            log_error "  2. Download the macOS installer"
            log_error "  3. Run the installer and follow instructions"
            exit 1
        fi
        
    elif [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "cygwin" ]]; then
        # Windows
        log_info "Detected Windows."
        log_error "Automatic Node.js installation not supported on Windows yet"
        log_error "Please install Node.js manually:"
        log_error "  1. Visit https://nodejs.org/"
        log_error "  2. Download the Windows installer"
        log_error "  3. Run the installer and follow instructions"
        log_error "  4. Restart this script after installation"
        exit 1
        
    else
        log_error "Unsupported operating system: $OSTYPE"
        log_error "Please install Node.js manually from https://nodejs.org/"
        exit 1
    fi
    
    # Verify installation
    if command -v node >/dev/null 2>&1 && command -v npm >/dev/null 2>&1; then
        NODE_VERSION=$(node --version 2>&1 | sed 's/v//')
        NPM_VERSION=$(npm --version 2>&1)
        log_success "Node.js $NODE_VERSION and npm $NPM_VERSION installed successfully"
    else
        log_error "Node.js installation verification failed"
        log_error "Please install Node.js manually from https://nodejs.org/"
        exit 1
    fi
}

# Create virtual environment if it doesn't exist
create_virtual_environment() {
    log_info "Checking virtual environment..."
    
    VENV_PATH="backend/venv"
    
    if [ ! -d "$VENV_PATH" ]; then
        log_info "Creating Python virtual environment..."
        
        # Try to create virtual environment
        if $PYTHON_CMD -m venv "$VENV_PATH" 2>/dev/null; then
            log_success "Virtual environment created"
        else
            log_error "Failed to create virtual environment"
            log_error "Please install python3-venv or virtualenv:"
            log_error "  Ubuntu/Debian: sudo apt install python3-venv"
            log_error "  macOS: brew install python@3.10"
            exit 1
        fi
    else
        log_info "Virtual environment already exists"
    fi
    
    # Verify virtual environment structure
    if [ ! -f "$VENV_PATH/bin/python" ] && [ ! -f "$VENV_PATH/Scripts/python.exe" ]; then
        log_error "Virtual environment appears to be corrupted"
        log_error "Please delete $VENV_PATH and try again"
        exit 1
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
        log_error "Please delete $VENV_PATH and try again"
        exit 1
    fi
    
    # Verify we're using the right Python
    if [ -z "$VIRTUAL_ENV" ]; then
        log_error "Failed to activate virtual environment"
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
    if python -m pip install --upgrade pip >/dev/null 2>&1; then
        log_success "pip upgraded"
    else
        log_warning "Failed to upgrade pip (continuing anyway)"
    fi
    
    # Install requirements
    log_info "Installing Python dependencies..."
    if python -m pip install -r requirements.txt; then
        log_success "Dependencies installed"
    else
        log_error "Failed to install dependencies"
        cd ..
        exit 1
    fi
    
    cd ..
}

# Start the server
start_server() {
    log_info "Starting backend server..."
    echo "=================================================="
    echo " The Gold Box Backend Server is Starting..."
    echo "=================================================="
    
    cd backend
    
    # Run server.py directly - let server.py handle everything internally
    python server.py
}

# Display usage information
show_usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  -h, --help              Show this help message"
    echo "  --dev                   Force development server mode (Flask)"
    echo ""
    echo "Environment Variables:"
    echo "  CORS_ORIGINS            Comma-separated list of allowed CORS origins"
    echo "  FLASK_ENV               Flask environment mode (development/production)"
    echo "  FLASK_DEBUG             Enable Flask debug mode (true/false)"
    echo "  GOLD_BOX_KEYCHANGE     Force key management wizard (set to 'true')"
    echo "  USE_DEVELOPMENT_SERVER  Force development mode (set to 'true')"
    echo ""
    echo "Examples:"
    echo "  $0                      Start with default settings"
    echo "  $0 --dev                Force development mode"
    echo "  USE_DEVELOPMENT_SERVER=true $0  Force development mode via environment"
    echo ""
    echo "Advanced Usage:"
    echo "  After setup, advanced users can run the server directly:"
    echo "    cd backend && source venv/bin/activate && python server.py"
    echo ""
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            show_usage
            exit 0
            ;;
        --dev)
            export USE_DEVELOPMENT_SERVER=true
            shift
            ;;
        *)
            log_error "Unknown option: $1"
            show_usage
            exit 1
            ;;
    esac
done

# Main execution flow
main() {
    echo "The Gold Box - Unified Backend Setup & Start Script"
    echo "=================================================="
    
    check_project_structure
    check_python
    create_virtual_environment
    activate_virtual_environment
    install_dependencies
    start_server
}

# Run main function
main "$@"
