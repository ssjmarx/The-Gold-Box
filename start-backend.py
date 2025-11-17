"""
The Gold Box - Universal Backend Automation Script
Cross-platform Python script that sets up virtual environment and starts backend server
Works on Windows, macOS, and Linux without any external dependencies
"""

import sys
import os
import subprocess
import platform
from pathlib import Path

def run_command_in_venv(cmd, venv_path, description):
    """Run a command within the virtual environment"""
    print(f"[INFO] {description}...")
    try:
        if platform.system() == "Windows":
            # Windows: Use python from venv
            python_exe = venv_path / "Scripts" / "python.exe"
            pip_exe = venv_path / "Scripts" / "pip.exe"
        else:
            # Unix: Use python from venv
            python_exe = venv_path / "bin" / "python"
            pip_exe = venv_path / "bin" / "pip"
        
        if cmd == "pip":
            cmd_exe = pip_exe
        else:
            cmd_exe = python_exe
        
        result = subprocess.run(cmd, shell=False, capture_output=True, text=True, executable=str(cmd_exe))
        
        if result.returncode == 0:
            print(f"[SUCCESS] {description} ✓")
            return True
        else:
            print(f"[ERROR] {description} failed")
            if result.stderr:
                print(f"[ERROR] {result.stderr}")
            return False
    except Exception as e:
        print(f"[ERROR] {description} failed: {e}")
        return False

def check_python():
    """Check if Python 3.8+ is available"""
    print(f"[INFO] Python version: {sys.version}")
    
    if sys.version_info < (3, 8):
        print("[ERROR] Python 3.8 or higher is required")
        print(f"[ERROR] Found: {sys.version}")
        return False
    return True

def check_pip():
    """Check if pip is available"""
    try:
        import pip
        print("[SUCCESS] pip available ✓")
        return True
    except ImportError:
        print("[ERROR] pip is not available")
        return False

def create_venv():
    """Create virtual environment if it doesn't exist"""
    venv_path = Path("venv")
    
    if not venv_path.exists():
        print("[INFO] Creating Python virtual environment...")
        
        # Try different venv creation methods
        venv_commands = [
            [sys.executable, "-m", "venv", "venv"],
            ["python3", "-m", "venv", "venv"],
            ["python", "-m", "venv", "venv"]
        ]
        
        for cmd in venv_commands:
            try:
                result = subprocess.run(cmd, capture_output=True, text=True)
                if result.returncode == 0:
                    print("[SUCCESS] Virtual environment created ✓")
                    return True
            except FileNotFoundError:
                continue
        
        print("[ERROR] Failed to create virtual environment")
        print("[ERROR] Please install python3-venv or virtualenv")
        print("[ERROR] Ubuntu/Debian: sudo apt install python3-venv")
        print("[ERROR] macOS: brew install python@3.10")
        print("[ERROR] Windows: Use python.org installer (includes venv)")
        return False
    else:
        print("[INFO] Virtual environment already exists")
        return True

def install_dependencies():
    """Install dependencies from requirements.txt"""
    req_file = Path("requirements.txt")
    venv_path = Path("venv")
    
    if not req_file.exists():
        print("[WARNING] requirements.txt not found, skipping dependency installation")
        return True
    
    print("[INFO] Installing Python dependencies...")
    
    # Use pip from the virtual environment
    if platform.system() == "Windows":
        pip_exe = str(venv_path / "Scripts" / "pip.exe")
    else:
        pip_exe = str(venv_path / "bin" / "pip")
    
    # First upgrade pip
    upgrade_cmd = [pip_exe, "install", "--upgrade", "pip"]
    result = subprocess.run(upgrade_cmd, capture_output=True, text=True)
    if result.returncode == 0:
        print("[SUCCESS] Upgrading pip ✓")
    else:
        print(f"[WARNING] Failed to upgrade pip (continuing anyway): {result.stderr}")
    
    # Then install requirements
    install_cmd = [pip_exe, "install", "-r", "requirements.txt"]
    result = subprocess.run(install_cmd, capture_output=True, text=True)
    if result.returncode == 0:
        print("[SUCCESS] Dependencies installed ✓")
        return True
    else:
        print(f"[ERROR] Failed to install dependencies: {result.stderr}")
        return False

def start_server():
    """Start the backend server using the virtual environment Python"""
    server_file = Path("server.py")
    venv_path = Path("venv")
    
    if not server_file.exists():
        print("[ERROR] server.py not found in backend directory!")
        return False
    
    print("[INFO] Starting backend server...")
    print("=" * 50)
    print("🚀 The Gold Box Backend Server is Starting...")
    print("📍 Server will find an available port starting from 5001")
    print("🛑 Press Ctrl+C to stop the server")
    print("=" * 50)
    
    # Use Python from virtual environment to start server
    if platform.system() == "Windows":
        python_exe = venv_path / "Scripts" / "python.exe"
    else:
        python_exe = venv_path / "bin" / "python"
    
    if not python_exe.exists():
        print(f"[ERROR] Virtual environment Python not found: {python_exe}")
        return False
    
    try:
        # Start the server with the virtual environment Python
        subprocess.call([str(python_exe), "server.py"])
    except KeyboardInterrupt:
        print("\n[INFO] Server stopped by user")
        return True
    except Exception as e:
        print(f"[ERROR] Failed to start server: {e}")
        return False

def main():
    """Main function"""
    print("The Gold Box - Universal Backend Setup & Start Script")
    print("=" * 60)
    
    # Check if we're in the right directory
    if not Path("module.json").exists():
        print("[ERROR] module.json not found!")
        print("[ERROR] Please run this script from the Gold Box module directory.")
        print(f"[ERROR] Current directory: {os.getcwd()}")
        return False
    
    if not Path("backend").exists():
        print("[ERROR] backend directory not found!")
        print("[ERROR] Please run this script from the Gold Box module directory.")
        return False
    
    # Change to backend directory
    os.chdir("backend")
    print(f"[INFO] Changed to backend directory: {os.getcwd()}")
    
    # Check Python version
    if not check_python():
        return False
    
    # Check pip availability
    if not check_pip():
        return False
    
    # Create virtual environment
    if not create_venv():
        return False
    
    # Install dependencies
    if not install_dependencies():
        return False
    
    # Start the server
    return start_server()

if __name__ == "__main__":
    try:
        success = main()
        if success:
            print("\n[SUCCESS] Backend server completed!")
        else:
            print("\n[ERROR] Backend setup failed!")
            print("[INFO] Please check the error messages above and fix any issues.")
            sys.exit(1)
    except Exception as e:
        print(f"\n[ERROR] Unexpected error: {e}")
        sys.exit(1)
