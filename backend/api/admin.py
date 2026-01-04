#!/usr/bin/env python3
"""
Admin endpoint
Password-protected admin endpoint for server management
"""

from fastapi import APIRouter, Request, HTTPException
from datetime import datetime
from typing import Dict, Any
import logging
import os
import asyncio

logger = logging.getLogger(__name__)

def create_admin_router(global_config):
    """
    Create and configure admin router
    
    Args:
        global_config: Global configuration dictionary
    """
    router = APIRouter()
    
    @router.post("/admin")
    async def admin_endpoint(request: Request):
        """
        Password-protected admin endpoint for server management
        Requires admin password in X-Admin-Password header
        Security is now handled by UniversalSecurityMiddleware
        """
        try:
            # Get admin password from headers
            admin_password = request.headers.get('X-Admin-Password')
            if not admin_password:
                raise HTTPException(
                    status_code=401,
                    detail="Admin password required in X-Admin-Password header",
                    headers={"WWW-Authenticate": 'Basic realm="The Gold Box Admin"'}
                )
            
            # Use service factory to get key manager
            from services.system_services.service_factory import get_key_manager, get_settings_manager
            
            key_manager = get_key_manager()
            
            # Verify admin password using service factory
            is_valid, error_msg = key_manager.verify_password(admin_password)
            if not is_valid:
                logger.warning(f"Invalid admin password attempt from {request.client.host if request.client else 'unknown'}")
                raise HTTPException(
                    status_code=401,
                    detail=f"Admin authentication failed: {error_msg}",
                    headers={"WWW-Authenticate": 'Basic realm="The Gold Box Admin"'}
                )
            
            # Get request body for admin commands
            try:
                request_data = await request.json()
            except Exception:
                raise HTTPException(
                    status_code=400,
                    detail="Invalid JSON in request body"
                )
            
            # Get validated data from middleware if available
            if hasattr(request.state, 'validated_body') and request.state.validated_body:
                request_data = request.state.validated_body
            
            # Process admin commands
            command = request_data.get('command', '')
            client_host = request.client.host if request.client else "unknown"
            
            if command == 'status':
                # Return server and key status
                return {
                    "service": "The Gold Box Backend",
                    "version": "0.2.3",
                    "status": "running",
                    "features": [
                        "Universal Security Middleware",
                        "Rate Limiting",
                        "Input Validation",
                        "Security Headers",
                        "Audit Logging",
                        "OpenAI Compatible API support",
                        "NovelAI API support", 
                        "OpenCode Compatible API support",
                        "Local LLM support",
                        "Simple chat endpoint",
                        "Admin settings management",
                        "Health check endpoint",
                        "Auto-start instructions",
                        "Advanced key management",
                        "Enhanced message context processing",
                        "Fixed JavaScript syntax errors",
                        "Improved API debugging",
                        "Better error handling and logging"
                    ],
                    "endpoints": {
                        "health": "/api/health",
                        "process": "/api/process",
                        "admin": "/api/admin",
                        "start": "/api/start"
                    },
                    "security": "Universal Security Middleware is active"
                }
            
            elif command == 'reload_keys':
                # Reload environment variables using service factory
                if key_manager.set_environment_variables():
                    # Reload global variables
                    OPENAI_API_KEY = os.environ.get('GOLD_BOX_OPENAI_COMPATIBLE_API_KEY', '')
                    NOVELAI_API_KEY = os.environ.get('GOLD_BOX_NOVELAI_API_API_KEY', '')
                    
                    logger.info("Environment variables reloaded successfully")
                    return {
                        'status': 'success',
                        'command': 'reload_keys',
                        'message': 'Environment variables reloaded successfully',
                        'timestamp': datetime.now().isoformat(),
                        'keys_status': key_manager.get_key_status()
                    }
                else:
                    raise HTTPException(
                        status_code=500,
                        detail="Failed to set environment variables"
                    )
            
            elif command == 'set_admin_password':
                # Set new admin password using service factory
                new_password = request_data.get('password', '')
                if key_manager.set_password(new_password):
                    # Save updated configuration
                    if key_manager.save_keys(key_manager.keys_data):
                        logger.info("Admin password updated successfully")
                        return {
                            'status': 'success',
                            'command': 'set_admin_password',
                            'message': 'Admin password updated successfully',
                            'timestamp': datetime.now().isoformat()
                        }
                    else:
                        raise HTTPException(
                            status_code=500,
                            detail="Failed to save updated admin password"
                        )
                else:
                    raise HTTPException(
                        status_code=400,
                        detail="Failed to set new admin password"
                    )
            
            elif command == 'update_settings':
                # Update frontend settings using service factory
                settings_mgr = get_settings_manager()
                
                frontend_settings_data = request_data.get('settings', {})
                
                if settings_mgr.update_settings(frontend_settings_data):
                    return {
                        'status': 'success',
                        'command': 'update_settings',
                        'message': f'Frontend settings updated: {len(frontend_settings_data)} settings loaded',
                        'timestamp': datetime.now().isoformat(),
                        'settings_count': len(frontend_settings_data),
                        'current_settings': settings_mgr.get_settings()
                    }
                else:
                    raise HTTPException(
                        status_code=500,
                        detail="Failed to update frontend settings"
                    )
            
            elif command == 'start_test_session':
                # Start a test session for a client
                return await handle_start_test_session(request_data, logger)
            
            elif command == 'test_command':
                # Execute a command during testing
                return await handle_test_command(request_data, logger)
            
            elif command == 'end_test_session':
                # End a test session
                return await handle_end_test_session(request_data, logger)
            
            elif command == 'list_test_sessions':
                # List all active test sessions
                return await handle_list_test_sessions(logger)
            
            elif command == 'get_test_session_state':
                # Get detailed state of a test session
                return await handle_get_test_session_state(request_data, logger)
            
            elif command == 'execute_test_commands':
                # Execute multiple test commands in one call
                return await handle_execute_test_commands(request_data, logger)
            
            else:
                raise HTTPException(
                    status_code=400,
                    detail=f"Unknown admin command: {command}",
                    headers={"X-Supported-Commands": "status, reload_keys, set_admin_password, update_settings, start_test_session, test_command, end_test_session, list_test_sessions, get_test_session_state, execute_test_commands"}
                )
            
        except HTTPException:
            # Re-raise HTTP exceptions (security failures already logged by middleware)
            raise
        except Exception as e:
                logger.error(f"Admin endpoint error: {str(e)}")
                raise HTTPException(
                    status_code=500,
                    detail="Internal server error in admin endpoint"
                )
    
    return router


# Testing harness command handlers

async def handle_start_test_session(request_data: Dict[str, Any], logger: logging.Logger) -> Dict[str, Any]:
    """Handle start_test_session command - creates transparent AI interceptor"""
    try:
        from services.system_services.service_factory import (
            get_testing_session_manager,
            get_testing_harness,
            get_websocket_manager
        )
        from services.ai_services.ai_session_manager import get_ai_session_manager
        from services.system_services.universal_settings import extract_universal_settings
        
        # Get client ID (auto-detect if not provided)
        client_id = request_data.get('client_id')
        
        if not client_id:
            # Auto-detect connected client
            ws_manager = get_websocket_manager()
            connected_clients = list(ws_manager.connection_info.keys())
            
            if not connected_clients:
                raise HTTPException(
                    status_code=400,
                    detail="No connected clients found. Ensure Foundry VTT is connected."
                )
            
            # Use the first connected client
            client_id = connected_clients[0]
            logger.info(f"Auto-detected client ID: {client_id}")
        
        # Get services
        testing_session_manager = get_testing_session_manager()
        testing_harness = get_testing_harness()
        ws_manager = get_websocket_manager()
        ai_session_manager = get_ai_session_manager()
        
        # Clear any stale delta from previous test session
        try:
            from services.message_services.websocket_message_collector import get_websocket_message_collector
            message_collector = get_websocket_message_collector()
            message_collector.clear_game_delta(client_id)
            logger.info(f"Cleared stale delta for client {client_id}")
        except Exception as e:
            logger.warning(f"Failed to clear stale delta for client {client_id}: {e}")
        
        # Send WebSocket message to frontend to trigger chat request with test flag
        # This must happen before we try to retrieve delta, because frontend only sends
        # delta after receiving "test_session_start" message
        await ws_manager.send_to_client(client_id, {
            'type': 'test_session_start',
            'data': {
                'test_session_id': 'pending',  # Will be updated after session creation
                'ai_role': 'gm',
                'timestamp': datetime.now().isoformat()
            }
        })
        
        logger.info(f"Sent test_session_start to client {client_id}")
        
        # NOTE: No need to explicitly request settings sync
        # The frontend's onTakeAITurn() -> sendChatRequest() flow already calls
        # syncSettingsToBackend() automatically, which sends settings to backend.
        # Requesting sync here would create a race condition with double syncs.
        
        # Sync frontend settings first (frontend is source of truth)
        from services.system_services.frontend_settings_handler import get_all_frontend_settings
        try:
            frontend_settings = get_all_frontend_settings()
            logger.info(f"Retrieved {len(frontend_settings)} frontend settings for test session")
        except Exception as e:
            logger.warning(f"Failed to retrieve frontend settings: {e}")
            frontend_settings = {}
        
        # Create universal_settings with required fields, merging with frontend settings
        provided_settings = request_data.get('universal_settings', {})
        universal_settings = {
            'ai role': 'gm',
            'disable function calling': False
        }
        
        # Merge frontend settings (frontend is source of truth)
        universal_settings.update(frontend_settings)
        
        # Override with any explicitly provided settings
        if provided_settings:
            universal_settings.update(provided_settings)
            logger.info(f"Merged {len(provided_settings)} provided settings with frontend settings")
        else:
            logger.info(f"Using frontend settings for test session (no explicit settings provided)")
        
        # Get provider config for session uniqueness
        from services.system_services.universal_settings import get_provider_config
        try:
            provider_config = get_provider_config(universal_settings, use_tactical=False)
            provider = provider_config.get('provider', 'test')
            model = provider_config.get('model', 'test')
        except Exception as e:
            logger.warning(f"Failed to get provider config, using defaults: {e}")
            provider = 'test'
            model = 'test'
        
        # Check if there's an existing active test session for this client (for session reuse)
        existing_session = testing_session_manager.get_session_by_client(client_id)
        if existing_session and existing_session.get('ai_session_id'):
            # Reuse existing AI session to maintain first-turn state
            ai_session_id = existing_session.get('ai_session_id')
            logger.info(f"Reusing AI session {ai_session_id} for client {client_id} (existing test session)")
        else:
            # Create new AI session only if no existing test session
            ai_session_id = ai_session_manager.create_or_get_session(client_id, None, provider, model)
            logger.info(f"Created new AI session {ai_session_id} for client {client_id}")
        
        # Add ai_session_id to universal_settings
        universal_settings['ai_session_id'] = ai_session_id
        
        # Create test session
        test_session_id = testing_session_manager.create_session(client_id, universal_settings)
        
        # Store ai_session_id in test session for later reference
        testing_session_manager.update_session(test_session_id, {'ai_session_id': ai_session_id})
        
        # Generate initial prompt using TRANSPARENT INTERCEPTOR
        # This now triggers world_state_refresh and uses exact same code path as production
        initial_prompt_result = await testing_harness.generate_initial_prompt(
            client_id,
            universal_settings,
            ai_session_id  # Pass AI session ID for first-turn detection
        )
        
        if not initial_prompt_result['success']:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to generate initial prompt: {initial_prompt_result.get('error')}"
            )
        
        # Store the exact messages that would be sent to AI
        initial_messages = initial_prompt_result.get('initial_messages', [])
        testing_session_manager.set_initial_prompt(
            test_session_id,
            initial_prompt_result['initial_prompt']
        )
        
        logger.info(f"Started transparent test session {test_session_id} for client {client_id} with AI session {ai_session_id}")
        
        return {
            'status': 'success',
            'command': 'start_test_session',
            'test_session_id': test_session_id,
            'ai_session_id': ai_session_id,
            'client_id': client_id,
            'initial_messages': initial_messages,  # Exact OpenAI format messages AI would receive
            'session_state': 'awaiting_input',
            'ai_role': initial_prompt_result.get('ai_role'),
            'is_first_turn': initial_prompt_result.get('is_first_turn', True),
            'message_delta': initial_prompt_result.get('message_delta'),
            'timestamp': datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error starting test session: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


async def handle_test_command(request_data: Dict[str, Any], logger: logging.Logger) -> Dict[str, Any]:
    """Handle test_command command"""
    try:
        from services.system_services.service_factory import (
            get_testing_session_manager,
            get_testing_harness,
            get_testing_command_processor
        )
        
        # Get test session ID
        test_session_id = request_data.get('test_session_id')
        if not test_session_id:
            raise HTTPException(
                status_code=400,
                detail="test_session_id is required"
            )
        
        # Get command (use test_command field for the actual command to execute)
        command = request_data.get('test_command')
        
        # DEBUG: Log what command we're receiving
        logger.info(f"===== TEST COMMAND DEBUG =====")
        logger.info(f"test_session_id: {test_session_id}")
        logger.info(f"test_command type: {type(command)}")
        logger.info(f"test_command value: {command}")
        logger.info(f"===== END TEST COMMAND DEBUG =====")
        
        if not command:
            raise HTTPException(
                status_code=400,
                detail="test_command is required"
            )
        
        # Get services
        testing_session_manager = get_testing_session_manager()
        testing_harness = get_testing_harness()
        testing_command_processor = get_testing_command_processor()
        
        # Check if session exists
        session = testing_session_manager.get_session(test_session_id)
        if not session:
            raise HTTPException(
                status_code=404,
                detail=f"Test session {test_session_id} not found"
            )
        
        # Get client ID
        client_id = session['client_id']
        
        # Process command
        result = await testing_harness.process_command(
            test_session_id,
            command,
            client_id,
            testing_session_manager,
            testing_command_processor
        )
        
        if not result['success']:
            raise HTTPException(
                status_code=400,
                detail=result.get('error', 'Command execution failed')
            )
        
        # Handle both string and dict commands for logging
        command_display = command[:50] if isinstance(command, str) else str(command)[:50]
        logger.info(f"Executed test command in session {test_session_id}: {command_display}...")
        
        return {
            'status': 'success',
            'command': 'test_command',
            'test_session_id': test_session_id,
            **result
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error executing test command: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


async def handle_end_test_session(request_data: Dict[str, Any], logger: logging.Logger) -> Dict[str, Any]:
    """Handle end_test_session command - optionally forces WebSocket reset for clean state"""
    try:
        from services.system_services.service_factory import get_testing_session_manager, get_testing_harness, get_websocket_manager
        
        # Get test session ID
        test_session_id = request_data.get('test_session_id')
        if not test_session_id:
            raise HTTPException(
                status_code=400,
                detail="test_session_id is required"
            )
        
        # Get reset connection flag (default to True for backward compatibility)
        reset_connection = request_data.get('reset_connection', True)
        
        # Get services
        testing_session_manager = get_testing_session_manager()
        testing_harness = get_testing_harness()
        ws_manager = get_websocket_manager()
        
        # Get session before ending it to retrieve client_id
        session = testing_session_manager.get_session(test_session_id)
        if not session:
            raise HTTPException(
                status_code=404,
                detail=f"Test session {test_session_id} not found"
            )
        
        client_id = session['client_id']
        
        # Send WebSocket message to frontend to indicate test session has ended
        # Include reset_connection flag so frontend knows whether to disconnect
        await ws_manager.send_to_client(client_id, {
            'type': 'test_session_end',
            'data': {
                'test_session_id': test_session_id,
                'reset_connection': reset_connection,
                'timestamp': datetime.now().isoformat()
            }
        })
        
        # Force disconnect WebSocket connection only if reset_connection is True
        if reset_connection:
            try:
                await ws_manager.disconnect(client_id)
                logger.info(f"Forced WebSocket disconnect for client {client_id} during test session end")
            except Exception as e:
                logger.warning(f"Failed to disconnect WebSocket for {client_id}: {e}")
        else:
            logger.info(f"Test session {test_session_id} ended for client {client_id} without WebSocket reset")
        
        # End session (await since end_test is now async)
        result = await testing_harness.end_test(test_session_id, testing_session_manager)
        
        if not result['success']:
            raise HTTPException(
                status_code=404,
                detail=result.get('error', 'Test session not found')
            )
        
        logger.info(f"Ended test session {test_session_id} for client {client_id} (WebSocket reset)")
        
        return {
            'status': 'success',
            'command': 'end_test_session',
            **result
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error ending test session: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


async def handle_list_test_sessions(logger: logging.Logger) -> Dict[str, Any]:
    """Handle list_test_sessions command"""
    try:
        from services.system_services.service_factory import get_testing_session_manager
        
        # Get testing session manager
        testing_session_manager = get_testing_session_manager()
        
        # List sessions
        sessions = testing_session_manager.list_sessions()
        
        return {
            'status': 'success',
            'command': 'list_test_sessions',
            'sessions': sessions,
            'count': len(sessions),
            'timestamp': datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error listing test sessions: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


async def handle_execute_test_commands(request_data: Dict[str, Any], logger: logging.Logger) -> Dict[str, Any]:
    """Handle execute_test_commands - execute multiple commands in one call"""
    try:
        from services.system_services.service_factory import (
            get_testing_session_manager,
            get_testing_harness,
            get_testing_command_processor
        )
        
        # Get test session ID
        test_session_id = request_data.get('test_session_id')
        if not test_session_id:
            raise HTTPException(
                status_code=400,
                detail="test_session_id is required"
            )
        
        # Get commands array
        commands = request_data.get('commands', [])
        if not commands:
            raise HTTPException(
                status_code=400,
                detail="commands array is required"
            )
        
        # Get services
        testing_session_manager = get_testing_session_manager()
        testing_harness = get_testing_harness()
        testing_command_processor = get_testing_command_processor()
        
        # Get session to retrieve client_id
        session = testing_session_manager.get_session(test_session_id)
        if not session:
            raise HTTPException(
                status_code=404,
                detail=f"Test session {test_session_id} not found"
            )
        
        client_id = session['client_id']
        
        # Execute commands sequentially
        results = []
        succeeded = 0
        failed = 0
        
        for index, command in enumerate(commands):
            try:
                result = await testing_harness.process_command(
                    test_session_id,
                    command,
                    client_id,
                    testing_session_manager,
                    testing_command_processor
                )
                
                if result['success']:
                    succeeded += 1
                    results.append({
                        "index": index,
                        "command": command,
                        "status": "success",
                        "result": result
                    })
                else:
                    failed += 1
                    results.append({
                        "index": index,
                        "command": command,
                        "status": "error",
                        "error": result.get('error', 'Command failed')
                    })
                    
            except Exception as e:
                failed += 1
                results.append({
                    "index": index,
                    "command": command,
                    "status": "error",
                    "error": str(e)
                })
                # Handle both string and dict commands for logging
                command_display = command[:50] if isinstance(command, str) else str(command)[:50]
                logger.warning(f"Command {index} failed: {command_display}... - {e}")
        
        logger.info(f"Executed {len(commands)} commands for session {test_session_id}: {succeeded} succeeded, {failed} failed")
        
        return {
            'status': 'success',
            'command': 'execute_test_commands',
            'test_session_id': test_session_id,
            'results': results,
            'summary': {
                'total': len(commands),
                'succeeded': succeeded,
                'failed': failed
            },
            'timestamp': datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error executing test commands: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


async def handle_get_test_session_state(request_data: Dict[str, Any], logger: logging.Logger) -> Dict[str, Any]:
    """Handle get_test_session_state command"""
    try:
        from services.system_services.service_factory import get_testing_session_manager
        
        # Get test session ID
        test_session_id = request_data.get('test_session_id')
        if not test_session_id:
            raise HTTPException(
                status_code=400,
                detail="test_session_id is required"
            )
        
        # Get testing session manager
        testing_session_manager = get_testing_session_manager()
        
        # Get session
        session = testing_session_manager.get_session(test_session_id)
        if not session:
            raise HTTPException(
                status_code=404,
                detail=f"Test session {test_session_id} not found"
            )
        
        # Build session state response
        session_state = {
            'test_session_id': test_session_id,
            'client_id': session['client_id'],
            'state': session['state'],
            'conversation_length': len(session.get('conversation_history', [])),
            'commands_executed': session.get('commands_executed', 0),
            'tools_used': session.get('tools_used', []),
            'start_time': session['start_time'].isoformat(),
            'last_activity': session['last_activity'].isoformat(),
            'has_initial_prompt': session.get('initial_prompt') is not None,
            'initial_prompt': session.get('initial_prompt', ''),
            'universal_settings': session.get('universal_settings', {})
        }
        
        return {
            'status': 'success',
            'command': 'get_test_session_state',
            'session_state': session_state,
            'timestamp': datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting test session state: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )
