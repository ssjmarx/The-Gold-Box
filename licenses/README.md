# Licenses

This folder contains the licenses for third-party libraries used in The Gold Box project.

## Included Libraries

### FastAPI Framework
- **License**: MIT License
- **File**: `FastAPI-MIT.txt`
- **Copyright**: (c) 2018 Sebastián Ramírez
- **Website**: https://fastapi.tiangolo.com/
- **Version**: 0.121.3

FastAPI is a modern, fast (high-performance) web framework for building APIs with Python 3.6+ based on standard Python type hints.

### Uvicorn ASGI Server
- **License**: BSD 3-Clause License
- **File**: `Uvicorn-BSD-3-Clause.txt`
- **Copyright**: (c) 2017, Tom Christie
- **Website**: https://www.uvicorn.org/
- **Version**: 0.38.0

Uvicorn is an ASGI server implementation, using uvloop and httptools. It's intended to be a very fast, lightweight HTTP server.

### Pydantic Data Validation
- **License**: MIT License
- **File**: `Pydantic-MIT.txt`
- **Copyright**: (c) 2017 Samuel Colvin
- **Website**: https://pydantic-docs.helpmanual.io/
- **Version**: 2.12.4

Pydantic is a library using Python type annotations for data validation and settings management.

### BeautifulSoup4 HTML Parser
- **License**: MIT License
- **File**: `BeautifulSoup4-MIT.txt`
- **Copyright**: (c) 2004-2021 Leonard Richardson
- **Website**: https://www.crummy.com/software/BeautifulSoup/bs4/doc/
- **Version**: 4.12.3

Beautiful Soup is a Python library for pulling data out of HTML and XML files. It works with your favorite parser to provide idiomatic ways of navigating, searching, and modifying the parse tree.

### LiteLLM Unified LLM Interface
- **License**: MIT License
- **File**: `LiteLLM-MIT.txt`
- **Copyright**: (c) 2023 Berri AI
- **Website**: https://docs.litellm.ai/
- **Version**: 1.80.0

LiteLLM provides a unified interface for calling 100+ LLM APIs including OpenAI, Cohere, Hugging Face, and more.

### SlowAPI Rate Limiting
- **License**: MIT License
- **File**: `SlowAPI-MIT.txt`
- **Copyright**: (c) 2020 Lauris Vlakov
- **Website**: https://slowapi.readthedocs.io/
- **Version**: 0.1.9

SlowAPI is a rate limiting extension for FastAPI, using the slowapi library.

### Gunicorn WSGI Server
- **License**: BSD 3-Clause License
- **File**: `Gunicorn-BSD-3-Clause.txt`
- **Copyright**: (c) 2011-2018 Benoit Chesneau
- **Website**: https://gunicorn.org/
- **Version**: 21.2.0

Gunicorn 'Green Unicorn' is a Python WSGI HTTP Server for UNIX. It's a pre-fork worker model.

### Cryptography Library
- **License**: BSD 3-Clause License
- **File**: `Cryptography-BSD-3-Clause.txt`
- **Copyright**: (c) 2013-2017 The Cryptography Project
- **Website**: https://cryptography.io/
- **Version**: >=41.0.0

Cryptography is a package which provides cryptographic recipes and primitives to Python developers.

### Flask (Legacy Support)
- **License**: BSD 3-Clause License
- **File**: `Flask-BSD-3-Clause.txt`
- **Copyright**: (c) 2010, Armin Ronacher
- **Website**: https://flask.palletsprojects.com/
- **Version**: 3.1.2

Flask is a lightweight WSGI web application framework. Used for legacy fallback support during migration.

### Flask-CORS (Legacy Support)
- **License**: MIT License
- **File**: `Flask-CORS-MIT.txt`
- **Copyright**: (c) 2014 Cory Dolphin
- **Website**: https://flask-cors.readthedocs.io/
- **Version**: 6.0.1

A Flask extension for handling Cross Origin Resource Sharing (CORS). Used for legacy fallback support.

### python-dotenv Environment Management
- **License**: BSD 3-Clause License
- **File**: `python-dotenv-BSD-3-Clause.txt`
- **Copyright**: (c) 2014, Saurabh Kumar, 2013, Ted Tieken, 2013, Jacob Kaplan-Moss
- **Website**: https://github.com/theskumar/python-dotenv
- **Version**: 1.2.1

A Python module to read key-value pairs from a .env file and set them as environment variables.

### WebSockets Server
- **License**: BSD 3-Clause License
- **File**: `websockets-BSD-3-Clause.txt`
- **Copyright**: (c) 2013, Aymeric Augustin
- **Website**: https://websockets.readthedocs.io/
- **Version**: >=11.0.3

An implementation of the WebSocket Protocol (RFC 6455) for Python.

### FoundryVTT REST API (ThreeHats Fork)
- **License**: MIT License
- **File**: `FoundryVTT-REST-API-MIT.txt`
- **Copyright**: (c) 2025 Three Hats
- **Website**: https://github.com/ThreeHats/foundryvtt-rest-api
- **Version**: Latest stable release

Forked Foundry VTT REST API module providing enhanced chat endpoints including POST /chat and GET /messages for AI-powered TTRPG assistance.

### FoundryVTT REST API Relay (ThreeHats Fork)
- **License**: MIT License
- **File**: `FoundryVTT-REST-API-Relay-MIT.txt`
- **Copyright**: (c) 2025 Three Hats
- **Website**: https://github.com/ThreeHats/foundryvtt-rest-api-relay
- **Version**: Latest stable release

Forked relay server for Foundry REST API providing WebSocket communication and message relay functionality between Foundry VTT and external services.

## Usage in The Gold Box

### Primary Framework (FastAPI-based)
1. **FastAPI**: Modern web framework providing the main API infrastructure
2. **Uvicorn**: ASGI server serving the FastAPI application
3. **Pydantic**: Data validation and serialization for API requests/responses
4. **SlowAPI**: Rate limiting for API endpoints
5. **LiteLLM**: Unified interface for multiple AI providers
6. **BeautifulSoup4**: HTML parsing for Foundry VTT chat messages
7. **Cryptography**: Encryption and security functions for key management
8. **python-dotenv**: Environment variable management
9. **WebSockets**: WebSocket server implementation for real-time communication

### Legacy Framework (Flask-based - Fallback)
1. **Flask**: Legacy web framework for backward compatibility
2. **Flask-CORS**: Cross-origin requests for legacy endpoints
3. **Gunicorn**: Production WSGI server for Flask fallback
4. **python-dotenv**: Environment variable management (shared)

## License Compatibility Analysis

### Core Project License
- **The Gold Box**: CC-BY-NC-SA 4.0 (Creative Commons Attribution-NonCommercial-ShareAlike)

### Dependency Licenses
- **MIT License**: FastAPI, Pydantic, BeautifulSoup4, LiteLLM, SlowAPI, Flask-CORS
- **BSD 3-Clause License**: Uvicorn, Gunicorn, Cryptography, Flask, python-dotenv, WebSockets

### Compatibility Assessment
✅ **MIT License**: Fully compatible with CC-BY-NC-SA 4.0
- MIT is permissive and allows sublicensing under CC-BY-NC-SA
- No copyleft conflicts
- Attribution requirements compatible

✅ **BSD 3-Clause License**: Fully compatible with CC-BY-NC-SA 4.0
- BSD is permissive and allows sublicensing under CC-BY-NC-SA
- No copyleft conflicts
- Attribution requirements compatible

### Compliance Requirements Met
1. **Attribution**: All copyright notices and license terms preserved in license files
2. **NonCommercial**: Dependencies used in non-commercial context consistent with CC-BY-NC-SA
3. **ShareAlike**: Distribution under compatible license terms
4. **License Files**: All dependency licenses included in `/licenses` folder
5. **Documentation**: Complete attribution and license information maintained

## Summary

The Gold Box project uses exclusively permissive open-source licenses (MIT and BSD 3-Clause) that are fully compatible with CC-BY-NC-SA 4.0 license. All 13 dependencies have their respective license files properly included, and the project maintains full compliance with all license requirements.

**Total Dependencies**: 13
**License Types**: MIT (8), BSD 3-Clause (5)
**Compatibility**: 100% compatible with CC-BY-NC-SA 4.0
**License Files**: Complete and up-to-date for v0.3.0

### New Dependencies in v0.3.0
- **FoundryVTT REST API (ThreeHats Fork)**: MIT License - Enhanced chat endpoints for API mode
- **FoundryVTT REST API Relay (ThreeHats Fork)**: MIT License - WebSocket relay server for API communication
