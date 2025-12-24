# The Gold Box - Dependencies

This document lists all dependencies used by The Gold Box project.

## Backend Dependencies (Python)

### Core Framework

| Package | Version | License | Description |
|----------|---------|----------|-------------|
| **FastAPI** | 0.121.3 | MIT License | Modern web framework for building APIs |
| **Uvicorn** | 0.38.0[standard] | BSD 3-Clause License | ASGI server for running FastAPI |
| **Pydantic** | 2.12.4 | MIT License | Data validation using Python type annotations |
| **LiteLLM** | 1.80.0 | MIT License | Unified interface for 70+ AI providers |

### Security & Encryption

| Package | Version | License | Description |
|----------|---------|----------|-------------|
| **Cryptography** | >=41.0.0 | BSD 3-Clause License | Cryptographic recipes and primitives |
| **python-dotenv** | 1.2.1 | BSD 3-Clause License | Read key-value pairs from .env file |

### Web & Communication

| Package | Version | License | Description |
|----------|---------|----------|-------------|
| **WebSockets** | >=11.0.3 | BSD 3-Clause License | WebSocket client and server implementation |
| **BeautifulSoup4** | 4.12.3 | MIT License | Screen-scraping library for parsing HTML |

### Rate Limiting

| Package | Version | License | Description |
|----------|---------|----------|-------------|
| **SlowAPI** | 0.1.9 | MIT License | Rate limiting extension for FastAPI |

### Legacy Support (Fallback)

| Package | Version | License | Description |
|----------|---------|----------|-------------|
| **Flask** | 3.1.2 | BSD 3-Clause License | Legacy web framework (fallback support) |
| **Flask-CORS** | 6.0.1 | MIT License | Cross-origin resource sharing for Flask (fallback) |
| **Gunicorn** | 21.2.0 | BSD 3-Clause License | Production WSGI server (fallback) |

## Frontend Dependencies (JavaScript)

### Foundry VTT Integration

| Technology | Description |
|-------------|-------------|
| **Foundry VTT API** | Game system integration and module framework |

### Web Technologies

| Technology | Description |
|-------------|-------------|
| **Modern JavaScript (ES6+)** | Modern JavaScript features and patterns |
| **CSS3** | Styling, animations, and responsive design |
| **WebSocket API** | Real-time bidirectional communication |
| **Fetch API** | HTTP requests and responses |
| **Crypto API** | Secure random number generation |

## Installation

### Backend Dependencies

All backend dependencies are automatically installed via the setup script:

```bash
cd backend
pip install -r requirements.txt
```

Or use the automated setup script:

```bash
./backend.sh
```

### Frontend Dependencies

Frontend dependencies are provided by Foundry VTT and require no separate installation.

## License Information

All dependencies are open source software. Individual license files are available in the `/licenses/` directory:

- `BeautifulSoup4-MIT.txt`
- `Cryptography-BSD-3-Clause.txt`
- `FastAPI-MIT.txt`
- `Flask-BSD-3-Clause.txt`
- `Flask-CORS-MIT.txt`
- `FoundryVTT-REST-API-MIT.txt`
- `FoundryVTT-REST-API-Relay-MIT.txt`
- `Gunicorn-BSD-3-Clause.txt`
- `LiteLLM-MIT.txt`
- `Pydantic-MIT.txt`
- `python-dotenv-BSD-3-Clause.txt`
- `SlowAPI-MIT.txt`
- `Uvicorn-BSD-3-Clause.txt`
- `websockets-BSD-3-Clause.txt`

## Version Updates

Dependencies are updated regularly for security patches and new features. The `backend/requirements.txt` file contains the authoritative list of versions for production use.

## Adding New Dependencies

When adding new dependencies to The Gold Box:

1. Add the dependency to `backend/requirements.txt`
2. Update this document with the package information
3. Add the license file to `/licenses/` directory
4. Update `backend.sh` if needed for installation
5. Test thoroughly before committing

## Security Notes

- All dependencies are from trusted sources
- Regular security updates are applied
- Pinning ensures version stability
- License compatibility verified for CC-BY-NC-SA-4.0 project license
