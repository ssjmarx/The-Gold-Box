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
    """Handle start_test_session command"""
    try:
        from services.system_services.service_factory import (
            get_testing_session_manager,
            get_testing_harness,
            get_websocket_manager
        )
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
        
        # Get universal settings (simulated from request)
        # In real use, these would come from the frontend's chat_request
        universal_settings = request_data.get('universal_settings', {})
        if not universal_settings:
            # Create minimal settings if none provided
            universal_settings = {
                'ai role': 'gm',
                'message_delta': {'new_messages': 0, 'deleted_messages': 0}
            }
        
        # Create test session
        test_session_id = testing_session_manager.create_session(client_id, universal_settings)
        
        # Generate initial prompt
        initial_prompt_result = testing_harness.generate_initial_prompt(
            client_id,
            universal_settings
        )
        
        if not initial_prompt_result['success']:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to generate initial prompt: {initial_prompt_result.get('error')}"
            )
        
        # Store initial prompt in session
        testing_session_manager.set_initial_prompt(
            test_session_id,
            initial_prompt_result['initial_prompt']
        )
        
        # Send WebSocket message to frontend to trigger chat request with test flag
        from services.system_services.service_factory import get_websocket_manager
        ws_manager = get_websocket_manager()
        await ws_manager.send_to_client(client_id, {
            'type': 'test_session_start',
            'data': {
                'test_session_id': test_session_id,
                'ai_role': initial_prompt_result.get('ai_role'),
                'initial_prompt': initial_prompt_result['initial_prompt'],
                'timestamp': datetime.now().isoformat()
            }
        })
        
        logger.info(f"Started test session {test_session_id} for client {client_id}")
        
        return {
            'status': 'success',
            'command': 'start_test_session',
            'test_session_id': test_session_id,
            'client_id': client_id,
            'initial_prompt': initial_prompt_result['initial_prompt'],
            'session_state': 'awaiting_input',
            'ai_role': initial_prompt_result.get('ai_role'),
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
        
        logger.info(f"Executed test command in session {test_session_id}: {command[:50]}...")
        
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
    """Handle end_test_session command - forces WebSocket reset for clean state"""
    try:
        from services.system_services.service_factory import get_testing_session_manager, get_testing_harness, get_websocket_manager
        
        # Get test session ID
        test_session_id = request_data.get('test_session_id')
        if not test_session_id:
            raise HTTPException(
                status_code=400,
                detail="test_session_id is required"
            )
        
        # Get services
        testing_session_manager = get_testing_session_manager()
        testing_harness = get_testing_harness()
        ws_manager = get_websocket_manager()
        
        # Get the session before ending it to retrieve client_id
        session = testing_session_manager.get_session(test_session_id)
        if not session:
            raise HTTPException(
                status_code=404,
                detail=f"Test session {test_session_id} not found"
            )
        
        client_id = session['client_id']
        
        # Send WebSocket message to frontend to indicate test session has ended WITH reset flag
        await ws_manager.send_to_client(client_id, {
            'type': 'test_session_end',
            'data': {
                'test_session_id': test_session_id,
                'reset_connection': True,
                'timestamp': datetime.now().isoformat()
            }
        })
        
        # Force disconnect WebSocket connection (default behavior for clean state)
        try:
            await ws_manager.disconnect(client_id)
            logger.info(f"Forced WebSocket disconnect for client {client_id} during test session end")
        except Exception as e:
            logger.warning(f"Failed to disconnect WebSocket for {client_id}: {e}")
        
        # End session
        result = testing_harness.end_test(test_session_id, testing_session_manager)
        
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
                logger.warning(f"Command {index} failed: {command[:50]}... - {e}")
        
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
