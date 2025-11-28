"""
Context Chat Endpoint - Enhanced chat endpoint with full board state integration
New endpoint: /api/context_chat
Purpose: Enhanced chat endpoint with full board state integration
Input: Chat messages + board context parameters
Output: AI response with awareness of complete board state
Integration: Leverages existing relay server and Foundry API infrastructure
Scope: Single prompt/response (no real-time delta updates in this version)
"""

import logging
import asyncio
from typing import Dict, Any, Optional, List
from fastapi import HTTPException
from server.context_processor import ContextProcessor
from server.universal_settings import extract_universal_settings, get_provider_config
from server.processor import ChatContextProcessor


class ContextChatEndpoint:
    """
    Enhanced chat endpoint with full board state integration
    New endpoint: /api/context_chat
    """
    
    def __init__(self, ai_service, foundry_client=None):
        self.ai_service = ai_service
        self.logger = logging.getLogger(__name__)
        
        # Initialize foundry client if not provided
        if foundry_client is None:
            self.foundry_client = RealFoundryClient()
        else:
            self.foundry_client = foundry_client
        
        # Initialize context processor
        self.context_processor = ContextProcessor(self.foundry_client)
    
    async def handle_context_chat(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle context chat request
        
        Expected request format:
        {
            "client_id": "foundry_client_id",
            "scene_id": "current_scene_id", 
            "message": "user message",
            "context_options": {
                "include_chat_history": true,
                "message_count": 50,
                "include_scene_data": true,
                "include_tokens": true,
                "include_walls": true,
                "include_lighting": true,
                "include_map_notes": true,
                "include_templates": true
            },
            "ai_options": {
                "model": "gpt-4",
                "temperature": 0.7,
                "max_tokens": 2000
            }
        }
        """
        
        try:
            # Validate request
            validated_request = self._validate_request(request_data)
            
            self.logger.info(f"Processing context chat request for client {validated_request['client_id']}")
            
            # Step 1: Load universal settings from backend storage (like api_chat)
            try:
                from server import settings_manager
                stored_settings = settings_manager.get_settings()
                if stored_settings:
                    universal_settings = extract_universal_settings({'settings': stored_settings}, "context_chat")
                    self.logger.info(f"Loaded universal settings from backend storage: {len(universal_settings)} settings")
                else:
                    self.logger.warning("No stored settings available, using defaults")
                    universal_settings = extract_universal_settings({}, "context_chat")
            except ImportError as e:
                self.logger.error(f"Failed to import settings_manager: {e}")
                universal_settings = extract_universal_settings({}, "context_chat")
            
            # Step 2: Collect chat messages using same method as api_chat
            import json
            from endpoints.api_chat import collect_chat_messages_api
            
            # Collect messages using exact same method as api_chat
            message_count = validated_request['context_options']['message_count']
            request_data_for_api = {
                'settings': {
                    'relay client id': validated_request['client_id']
                }
            }
            
            chat_messages = await collect_chat_messages_api(message_count, request_data_for_api)
            
            # Process messages using same method as api_chat
            from server.api_chat_processor import APIChatProcessor
            api_chat_processor = APIChatProcessor()
            compact_messages = api_chat_processor.process_api_messages(chat_messages)
            
            # Step 3: Process board context using context processor
            context_data = await self.context_processor.process_context_request(
                client_id=validated_request['client_id'],
                scene_id=validated_request['scene_id'],
                include_chat_history=False,  # Already collected above
                message_count=message_count
            )
            
            # Override chat_history with properly collected and processed messages
            context_data['chat_history'] = compact_messages
            
            # DEBUG: Show raw context data being collected
            self.logger.info("=== RAW CONTEXT DATA COLLECTED (CONTEXT CHAT) ===")
            self.logger.info(f"Context Data Keys: {list(context_data.keys())}")
            self.logger.info(f"Board State: {context_data.get('board_state', {})}")
            self.logger.info(f"Chat History Length: {len(context_data.get('chat_history', []))}")
            self.logger.info(f"System Prompt: {context_data.get('system_prompt', 'No system prompt')}")
            self.logger.info("=== END RAW CONTEXT DATA (CONTEXT CHAT) ===")
            
            # Step 4: Prepare AI request with context
            ai_request = self._prepare_ai_request(validated_request, context_data)
            
            # Step 4: Send to AI service with universal settings
            ai_response = await self.ai_service.process_chat_request(ai_request, universal_settings)
            
            # Step 5: Format response
            response = self._format_response(ai_response, context_data)
            
            # Step 6: Send AI response to Foundry chat using AI processor (like api_chat endpoint)
            if response.get('status') == 'success':
                # Use client ID from universal settings (like api_chat endpoint)
                # Fall back to validated_request client_id if not in universal settings
                client_id_for_relay = universal_settings.get('relay client id') or validated_request['client_id']
                await self._send_ai_response_to_foundry_with_processor(response, client_id_for_relay)
            
            self.logger.info(f"Context chat response generated successfully")
            return response
            
        except HTTPException:
            raise
        except Exception as e:
            self.logger.error(f"Error in context chat endpoint: {e}")
            raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
    
    async def _send_ai_response_to_foundry_with_processor(self, response: Dict[str, Any], client_id: str):
        """
        Send AI response to Foundry chat via relay server using AI processor (like api_chat)
        
        Args:
            response: Formatted response from AI
            client_id: Foundry client ID
        """
        try:
            import requests
            from datetime import datetime
            
            # Get raw AI response content
            ai_response_text = response.get('response', 'AI response failed')
            
            # DEBUG: Show raw AI response before processing
            self.logger.info("=== RAW AI RESPONSE BEFORE PROCESSING (CONTEXT CHAT) ===")
            self.logger.info(f"Raw AI Response: {ai_response_text}")
            self.logger.info("=== END RAW AI RESPONSE (CONTEXT CHAT) ===")
            
            # Use AI chat processor to parse and format response (exact same as api_chat)
            from server.ai_chat_processor import AIChatProcessor
            
            # Create AI chat processor instance
            ai_chat_processor = AIChatProcessor()
            
            # Parse AI response using the same method as api_chat
            processed_response = ai_chat_processor.process_ai_response(ai_response_text)
            
            # Handle the response structure from AIChatProcessor
            if processed_response.get('type') == 'multi-message':
                parsed_messages = processed_response.get('messages', [])
            else:
                # Single message response
                parsed_messages = [{
                    'content': processed_response.get('content', ''),
                    'speaker': processed_response.get('author', {}).get('name', 'Gamemaster'),
                    'type': processed_response.get('type', 'chat-message')
                }]
            
            self.logger.info(f"Parsed {len(parsed_messages)} messages from AI response")
            
            # Send each parsed message to relay server (exact same logic as api_chat)
            success_count = 0
            total_messages = len(parsed_messages)
            
            for message_data in parsed_messages:
                try:
                    # Check if this is a dice roll message (exact same logic as api_chat)
                    if message_data.get("type") == "dice-roll" and "roll" in message_data:
                        # Send dice roll via /roll endpoint
                        success = await self._send_dice_roll_to_foundry(message_data, client_id)
                    else:
                        # Send regular chat message via /chat endpoint
                        success = await self._send_chat_message_to_foundry(message_data, client_id)
                    
                    if success:
                        success_count += 1
                        
                except Exception as e:
                    self.logger.error(f"Error sending individual message to Foundry: {e}")
            
            # Report overall success
            if success_count == total_messages and total_messages > 0:
                self.logger.info(f"Relay server transmission: {success_count}/{total_messages} messages sent successfully")
                return True
            elif success_count > 0:
                self.logger.warning(f"Partial success: {success_count}/{total_messages} messages sent")
                return True  # Consider partial success as success
            else:
                self.logger.error(f"Complete failure: {success_count}/{total_messages} messages sent")
                return False
                    
        except Exception as e:
            self.logger.error(f"Error in AI processor response handling: {e}")
            # Fallback to original method if AI processor fails
            self.logger.info("Falling back to original response method")
            return await self._send_ai_response_to_foundry(response, client_id)

    async def _send_dice_roll_to_foundry(self, message_data: Dict[str, Any], client_id: str):
        """Send dice roll to Foundry via /roll endpoint (exact same as api_chat)"""
        try:
            import requests
            import json
            
            roll_data = message_data.get("roll", {})
            
            # Prepare roll data for relay server (exact same as api_chat)
            post_data = {
                "formula": roll_data.get("formula", ""),
                "flavor": message_data.get("content", ""),
                "createChatMessage": True,  # Always create chat message for dice rolls
                "speaker": message_data.get("speaker", "The Gold Box AI")
            }
            
            # DEBUG: Show exactly what data is sent to POST /roll endpoint
            self.logger.info("=== DATA SENT TO POST /ROLL ENDPOINT (CONTEXT CHAT) ===")
            self.logger.info(f"POST URL: http://localhost:3010/roll?clientId={client_id}")
            self.logger.info(f"POST Data: {json.dumps(post_data, indent=2)}")
            self.logger.info("=== END POST /ROLL DATA (CONTEXT CHAT) ===")
            
            # Retry logic for relay server communication (exact same as api_chat)
            max_retries = 3
            retry_delay = 1  # seconds
            
            for attempt in range(max_retries):
                try:
                    response = requests.post(
                        f"http://localhost:3010/roll?clientId={client_id}",
                        json=post_data,
                        headers={"x-api-key": "local-dev"},
                        timeout=30
                    )
                    
                    if response.status_code == 200:
                        self.logger.info(f"Successfully sent dice roll to Foundry: {roll_data.get('formula', 'unknown')}")
                        return True  # Success, exit retry loop
                    else:
                        self.logger.warning(f"Roll attempt {attempt + 1} failed: {response.status_code} - {response.text}")
                        if attempt < max_retries - 1:
                            self.logger.info(f"Retrying in {retry_delay} seconds...")
                            await asyncio.sleep(retry_delay)
                            retry_delay *= 2  # Exponential backoff
                        else:
                            self.logger.error(f"All {max_retries} attempts failed for dice roll")
                            return False
                            
                except Exception as e:
                    self.logger.error(f"Roll attempt {attempt + 1} exception: {e}")
                    if attempt < max_retries - 1:
                        self.logger.info(f"Retrying in {retry_delay} seconds...")
                        await asyncio.sleep(retry_delay)
                        retry_delay *= 2  # Exponential backoff
                    else:
                        self.logger.error(f"All {max_retries} attempts failed for dice roll")
                        return False
            
            return False
                    
        except Exception as e:
            self.logger.error(f"Error sending dice roll to Foundry: {e}")
            return False

    async def _send_chat_message_to_foundry(self, message_data: Dict[str, Any], client_id: str):
        """Send chat message to Foundry via /chat endpoint (exact same as api_chat)"""
        try:
            import requests
            import json
            from datetime import datetime
            
            # Use correct relay server format - BOTH nested message object AND flat fields (exact same as api_chat)
            post_data = {
                "clientId": client_id,
                "message": {
                    "message": message_data.get('content', 'Test message'),
                    "speaker": message_data.get('speaker', 'The Gold Box AI'),
                    "type": message_data.get('type', 'ic'),  # ic = in-character
                    "timestamp": int(datetime.now().timestamp() * 1000)  # milliseconds as required
                },
                # Also provide flat fields (required by relay server validation)
                "message.message": message_data.get('content', 'Test message'),
                "message.speaker": message_data.get('speaker', 'The Gold Box AI'),
                "message.type": message_data.get('type', 'ic'),  # ic = in-character
                "message.timestamp": int(datetime.now().timestamp() * 1000)  # milliseconds as required
            }
            
            # DEBUG: Show exactly what data is sent to POST /chat endpoint
            self.logger.info("=== DATA SENT TO POST /CHAT ENDPOINT (CONTEXT CHAT) ===")
            self.logger.info(f"POST URL: http://localhost:3010/chat")
            self.logger.info(f"POST Data: {json.dumps(post_data, indent=2)}")
            self.logger.info("=== END POST /CHAT DATA (CONTEXT CHAT) ===")
            
            # Retry logic for relay server communication (exact same as api_chat)
            max_retries = 3
            retry_delay = 1  # seconds
            
            for attempt in range(max_retries):
                try:
                    response = requests.post(
                        f"http://localhost:3010/chat",
                        json=post_data,
                        headers={"x-api-key": "local-dev"},
                        timeout=30  # Increased timeout to 30 seconds as requested
                    )
                    
                    if response.status_code == 200:
                        self.logger.info(f"Successfully sent chat message to Foundry: {message_data.get('type', 'unknown')}")
                        return True  # Success, exit retry loop
                    else:
                        self.logger.warning(f"Chat attempt {attempt + 1} failed: {response.status_code} - {response.text}")
                        if attempt < max_retries - 1:
                            self.logger.info(f"Retrying in {retry_delay} seconds...")
                            await asyncio.sleep(retry_delay)
                            retry_delay *= 2  # Exponential backoff
                        else:
                            self.logger.error(f"All {max_retries} attempts failed for chat message")
                            return False
                            
                except Exception as e:
                    self.logger.error(f"Chat attempt {attempt + 1} exception: {e}")
                    if attempt < max_retries - 1:
                        self.logger.info(f"Retrying in {retry_delay} seconds...")
                        await asyncio.sleep(retry_delay)
                        retry_delay *= 2  # Exponential backoff
                    else:
                        self.logger.error(f"All {max_retries} attempts failed for chat message")
                        return False
            
            return False
                    
        except Exception as e:
            self.logger.error(f"Error sending chat message to Foundry: {e}")
            return False

    async def _send_ai_response_to_foundry(self, response: Dict[str, Any], client_id: str):
        """
        Send AI response to Foundry chat via relay server
        
        Args:
            response: Formatted response from AI
            client_id: Foundry client ID
        """
        try:
            import requests
            import json
            from datetime import datetime
            
            # Prepare message for relay server (matching api_chat format exactly)
            ai_response_text = response.get('response', 'AI response failed')
            post_data = {
                "clientId": client_id,
                "message": {
                    "message": ai_response_text,
                    "author": {"name": "The Gold Box AI"},
                    "type": "chat-message",  # Fixed: use chat-message instead of ic
                    "timestamp": int(datetime.now().timestamp() * 1000)  # milliseconds as required
                },
                # Also provide flat fields (required by relay server validation)
                "message.message": ai_response_text,
                "message.author": {"name": "The Gold Box AI"},
                "message.speaker": "The Gold Box AI",  # Keep for compatibility
                "message.type": "chat-message",  # Fixed: use chat-message instead of ic
                "message.timestamp": int(datetime.now().timestamp() * 1000)  # milliseconds as required
            }
            
            # DEBUG: Show exactly what data is sent to POST /chat endpoint
            self.logger.info("=== DATA SENT TO POST /CHAT ENDPOINT (CONTEXT CHAT) ===")
            self.logger.info(f"POST URL: http://localhost:3010/chat")
            self.logger.info(f"POST Data: {json.dumps(post_data, indent=2)}")
            self.logger.info("=== END POST /CHAT DATA (CONTEXT CHAT) ===")
            
            # Send to relay server with retry logic
            max_retries = 3
            retry_delay = 1  # seconds
            
            for attempt in range(max_retries):
                try:
                    api_response = requests.post(
                        f"http://localhost:3010/chat",
                        json=post_data,
                        headers={"x-api-key": "local-dev"},
                        timeout=30
                    )
                    
                    if api_response.status_code == 200:
                        self.logger.info(f"Successfully sent AI response to Foundry chat")
                        return True  # Success, exit retry loop
                    else:
                        self.logger.warning(f"Foundry chat attempt {attempt + 1} failed: {api_response.status_code} - {api_response.text}")
                        if attempt < max_retries - 1:
                            self.logger.info(f"Retrying in {retry_delay} seconds...")
                            await asyncio.sleep(retry_delay)
                            retry_delay *= 2  # Exponential backoff
                        else:
                            self.logger.error(f"All {max_retries} attempts failed for Foundry chat")
                            return False
                            
                except Exception as e:
                    self.logger.error(f"Foundry chat attempt {attempt + 1} exception: {e}")
                    if attempt < max_retries - 1:
                        self.logger.info(f"Retrying in {retry_delay} seconds...")
                        await asyncio.sleep(retry_delay)
                        retry_delay *= 2  # Exponential backoff
                    else:
                        self.logger.error(f"All {max_retries} attempts failed for Foundry chat")
                        return False
            
            return False
                    
        except Exception as e:
            self.logger.error(f"Error sending AI response to Foundry: {e}")
            return False
    
    def _validate_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate and sanitize request data
        
        Args:
            request_data: Raw request data
            
        Returns:
            Validated request with defaults applied
        """
        
        if not isinstance(request_data, dict):
            raise HTTPException(status_code=400, detail="Request must be a JSON object")
        
        # DEBUG: Log the raw request data to understand the structure
        self.logger.info(f"DEBUG: Raw request data keys: {list(request_data.keys())}")
        self.logger.info(f"DEBUG: Raw request data: {request_data}")
        
        # Required fields - check for both 'client_id' and look for client ID in settings
        required_fields = ['client_id', 'scene_id', 'message']
        
        # Try to get client_id from request data first
        client_id = request_data.get('client_id')
        
        # If no client_id in request data, try to get it from settings
        if not client_id:
            settings = request_data.get('settings', {})
            client_id = settings.get('relay client id')
            self.logger.info(f"DEBUG: Using client_id from settings: {client_id}")
        
        # If still no client_id, then we have a problem
        if not client_id:
            self.logger.error("DEBUG: No client_id found in request data or settings!")
            raise HTTPException(status_code=400, detail="Missing required field: client_id")
        
        # Validate other required fields
        for field in ['scene_id', 'message']:
            if field not in request_data:
                raise HTTPException(status_code=400, detail=f"Missing required field: {field}")
        
        self.logger.info(f"DEBUG: Validated client_id: {client_id}")
        
        # Apply defaults for context options
        context_options = request_data.get('context_options', {})
        default_context_options = {
            'include_chat_history': True,
            'message_count': 50,
            'include_scene_data': True,
            'include_tokens': True,
            'include_walls': True,
            'include_lighting': True,
            'include_map_notes': True,
            'include_templates': True
        }
        
        # Merge with defaults
        validated_context_options = {**default_context_options, **context_options}
        
        # Apply defaults for AI options
        ai_options = request_data.get('ai_options', {})
        default_ai_options = {
            'model': 'gpt-4',
            'temperature': 0.7,
            'max_tokens': 2000
        }
        
        # Merge with defaults
        validated_ai_options = {**default_ai_options, **ai_options}
        
        return {
            'client_id': client_id,
            'scene_id': request_data['scene_id'],
            'message': request_data['message'],
            'context_options': validated_context_options,
            'ai_options': validated_ai_options
        }
    
    def _prepare_ai_request(self, validated_request: Dict[str, Any], 
                           context_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Prepare AI request with enhanced context
        
        Args:
            validated_request: Validated request data
            context_data: Processed context data
            
        Returns:
            AI service request
        """
        
        # Build enhanced system prompt based on AI role
        ai_role = validated_request['ai_options'].get('ai_role', 'dm').lower()
        
        # Get AI role specific prompt content
        role_prompts = {
            'gm': 'You are assigned as a full gamemaster. Your role is to describe the scene, describe NPC actions, and create dice rolls whenever NPCs do anything that requires one. Keep generating descriptions, actions, and dice rolls until every NPC in the scene has gone, and then turn the action back over to the players.',
            'gm assistant': 'You are assigned as a GM\'s assistant. Your role is to aid the GM in whatever task they are currently doing, which they will usually prompt for you in the most recent message.',
            'player': 'You are assigned as a Player. Your role is to participate in the story via in-character chat and actions. Describe what your character is doing and roll dice as appropriate for your actions.'
        }
        
        role_specific_prompt = role_prompts.get(ai_role, role_prompts['gm'])
        
        # Generate context codes and abbreviations from board state
        context_codes = []
        context_abbreviations = []
        context_schemas = []
        
        # Add scene context codes
        if 'scn' in context_data.get('board_state', {}):
            context_codes.append('scn: scene_info')
            context_abbreviations.append('scn: scene dimensions, grid size')
            context_schemas.append('scn: {"w": width, "h": height, "gs": grid_size, "bg": background}')
        
        # Add wall context codes
        if 'wal' in context_data.get('board_state', {}):
            context_codes.append('wal: walls')
            context_abbreviations.append('wal: wall segments, boundaries')
            context_schemas.append('wal: [{"x1": x1, "y1": y1, "x2": x2, "y2": y2, "type": wall_type}]')
        
        # Add lighting context codes
        if 'lig' in context_data.get('board_state', {}):
            context_codes.append('lig: lighting')
            context_abbreviations.append('lig: light sources, illumination')
            context_schemas.append('lig: [{"x": x, "y": y, "r": radius, "t": light_type, "c": color}]')
        
        # Add token context codes and abbreviations
        if 'tkn' in context_data.get('board_state', {}):
            context_codes.append('tkn: tokens')
            context_abbreviations.extend(['tkn: character/creature tokens', 'hp: hit points', 'ac: armor class', 'str: strength', 'dex: dexterity', 'con: constitution', 'int: intelligence', 'wis: wisdom', 'cha: charisma'])
            context_schemas.append('tkn: [{"n": name, "x": x, "y": y, "at": {attribute_code: value}]')
        
        # Add template context codes
        if 'tpl' in context_data.get('board_state', {}):
            context_codes.append('tpl: templates')
            context_abbreviations.append('tpl: area templates, spell templates')
            context_schemas.append('tpl: [{"x": x, "y": y, "w": width, "h": height, "t": template_type}]')
        
        # Format scene context objects
        scene_context = []
        board_state = context_data.get('board_state', {})
        
        if 'scn' in board_state:
            scene = board_state['scn']
            scene_context.append(f"Scene: {scene.get('w', 0)}x{scene.get('h', 0)} grid, size {scene.get('gs', 0)}")
        
        if 'wal' in board_state and board_state['wal']:
            scene_context.append(f"Walls: {len(board_state['wal'])} wall segments")
        
        if 'lig' in board_state and board_state['lig']:
            scene_context.append(f"Lighting: {len(board_state['lig'])} light sources")
        
        if 'tkn' in board_state and board_state['tkn']:
            scene_context.append("Tokens:")
            for token in board_state['tkn']:
                token_info = f"  {token.get('n', 'Unknown')} at ({token.get('x', 0)}, {token.get('y', 0)})"
                if 'at' in token and token['at']:
                    attr_info = ", ".join([f"{code}={value}" for code, value in token['at'].items()])
                    token_info += f" [{attr_info}]"
                scene_context.append(token_info)
        
        if 'tpl' in board_state and board_state['tpl']:
            scene_context.append(f"Templates: {len(board_state['tpl'])} active templates")
        
        # Get message context - use compact JSON format like api_chat
        message_context = context_data.get('chat_history', [])
        
        # Convert to compact JSON for AI (same as api_chat)
        import json
        compact_json_context = json.dumps(message_context, indent=2)
        
        # Build system prompt
        system_prompt = f"""You are an AI assistant for tabletop RPG games, with the role {ai_role}. {role_specific_prompt}

Data from chat and environment is formatted as follows:

Type Codes:
- dr: dice_roll
- cm: chat_message
- cd: chat_card

Field Abbreviations:
- t: message type (dr, cm, cd)
- f: formula (dice roll formula)
- r: results (individual dice results array)
- tt: total (roll total result)
- s: speaker (character name who sent message)
- c: content (message text content)
- ft: flavor_text (roll context like "Intelligence (Investigation) Check")
- n: name (item/spell/condition name)
- d: description (card description text)
- a: actions (button actions array)

Message Schemas:
- Dice Roll: {{"t": "dr", "ft": "flavor_text", "f": "formula", "r": [results], "tt": total}}
- Chat Message: {{"t": "cm", "s": "speaker", "c": "content"}}
- Chat Card: {{"t": "cd", "n": "name", "d": "description", "a": ["actions"]}}

Context Codes:
{', '.join(context_codes)}

Context Abbreviations:
{', '.join(context_abbreviations)}

Context Schemas:
{'; '.join(context_schemas)}

Scene Context:
{'; '.join(scene_context)}"""
        
        # Add user message with context
        user_message = f"""Chat Context (Compact JSON Format):
{compact_json_context}

Please respond to this conversation as an AI assistant for tabletop RPGs. If you need to generate game mechanics, use compact JSON format specified in system prompt."""
        
        ai_request = {
            'system_prompt': system_prompt,
            'user_message': user_message,
            'options': validated_request['ai_options']
        }
        
        # DEBUG: Show final prompt being sent to AI
        self.logger.info("=== FINAL AI PROMPT CONSTRUCTED (CONTEXT CHAT) ===")
        self.logger.info(f"System Prompt Length: {len(system_prompt)} characters")
        self.logger.info(f"User Message Length: {len(user_message)} characters")
        self.logger.info("=== SYSTEM PROMPT (CONTEXT CHAT) ===")
        self.logger.info(system_prompt)
        self.logger.info("=== USER MESSAGE (CONTEXT CHAT) ===")
        self.logger.info(user_message)
        self.logger.info("=== END FINAL AI PROMPT (CONTEXT CHAT) ===")
        
        return ai_request
    
    def _format_board_context_for_ai(self, board_state: Dict[str, Any]) -> str:
        """
        Format board state data for AI consumption
        
        Args:
            board_state: Optimized board state
            
        Returns:
            Formatted board context string
        """
        
        context_lines = ["Board State:"]
        
        # Add scene info
        if 'scn' in board_state:
            scene = board_state['scn']
            context_lines.append(f"  Scene: {scene.get('w', 0)}x{scene.get('h', 0)} grid, size {scene.get('gs', 0)}")
        
        # Add walls
        if 'wal' in board_state and board_state['wal']:
            context_lines.append(f"  Walls: {len(board_state['wal'])} walls/segments found")
        
        # Add lighting
        if 'lig' in board_state and board_state['lig']:
            context_lines.append(f"  Lighting: {len(board_state['lig'])} light sources")
        
        # Add map notes
        if 'not' in board_state and board_state['not']:
            context_lines.append(f"  Map Notes: {len(board_state['not'])} notes")
        
        # Add tokens with attributes
        if 'tkn' in board_state and board_state['tkn']:
            context_lines.append("  Tokens:")
            for token in board_state['tkn']:
                token_info = f"    {token.get('n', 'Unknown')} at ({token.get('x', 0)}, {token.get('y', 0)})"
                if 'at' in token and token['at']:
                    attr_info = ", ".join([f"{code}={value}" for code, value in token['at'].items()])
                    token_info += f" [{attr_info}]"
                context_lines.append(token_info)
        
        # Add templates
        if 'tpl' in board_state and board_state['tpl']:
            context_lines.append(f"  Templates: {len(board_state['tpl'])} active templates")
        
        return "\n".join(context_lines)
    
    def _format_chat_history_for_ai(self, chat_history: list) -> str:
        """
        Format chat history for AI consumption
        
        Args:
            chat_history: List of chat messages
            
        Returns:
            Formatted chat history string
        """
        
        if not chat_history:
            return "  No recent chat history"
        
        context_lines = ["Recent Chat History:"]
        for msg in chat_history[-5:]:  # Show last 5 messages
            # Handle both chat messages and dice rolls
            if msg.get('_source') == 'roll':
                # Dice roll message
                formula = msg.get('formula', '')
                result = msg.get('result', 0)
                flavor = msg.get('flavor', '')
                context_lines.append(f"  Roll: {flavor} - {formula} = {result}")
            else:
                # Chat message
                speaker = msg.get('speaker', 'Unknown')
                content = msg.get('content', '')
                context_lines.append(f"  {speaker}: {content}")
        
        return "\n".join(context_lines)
    
    def _format_response(self, ai_response: Dict[str, Any], 
                       context_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Format: final response
        
        Args:
            ai_response: Response from AI service
            context_data: Context data used
            
        Returns:
            Formatted endpoint response
        """
        
        # Get the actual AI response content
        ai_content = ai_response.get('response', '')
        
        # Check if AI response indicates success
        if not ai_content or ai_response.get('error'):
            # Return error response
            return {
                'status': 'error',
                'error': ai_response.get('error', 'AI service failed to generate response'),
                'response': '',
                'metadata': {
                    'context_used': True,
                    'provider_used': ai_response.get('provider_used', 'unknown'),
                    'model_used': ai_response.get('model', 'unknown'),
                    'tokens_used': ai_response.get('tokens_used', 0)
                }
            }
        
        # Return success response with AI content
        return {
            'status': 'success',
            'response': ai_content,
            'metadata': {
                'context_used': True,
                'provider_used': ai_response.get('provider_used', 'unknown'),
                'model_used': ai_response.get('model', 'unknown'),
                'tokens_used': ai_response.get('tokens_used', 0),
                'processing_time': context_data.get('processed_at', 'unknown'),
                'scene_id': context_data.get('scene_id', 'unknown'),
                'board_elements': {
                    'scene': 'scn' in context_data.get('board_state', {}),
                    'walls': 'wal' in context_data.get('board_state', {}),
                    'lighting': 'lig' in context_data.get('board_state', {}),
                    'map_notes': 'not' in context_data.get('board_state', {}),
                    'tokens': 'tkn' in context_data.get('board_state', {}),
                    'templates': 'tpl' in context_data.get('board_state', {})
                }
            }
        }


# Real Foundry Client for production use
class RealFoundryClient:
    """Real Foundry client that integrates with relay server"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    async def get_chat_messages(self, client_id: str, count: int) -> List[Dict[str, Any]]:
        """Get chat messages from relay server"""
        try:
            import requests
            
            headers = {"x-api-key": "local-dev"}  # Works for local memory store
            
            response = requests.get(
                f"http://localhost:3010/messages",
                params={"clientId": client_id, "limit": count, "sort": "timestamp", "order": "desc"},
                headers=headers,
                timeout=3
            )
            
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, dict) and 'messages' in data:
                    return data['messages']
                elif isinstance(data, list):
                    return data
                else:
                    return []
            else:
                self.logger.warning(f"Failed to get chat messages: {response.status_code}")
                return []
                
        except Exception as e:
            self.logger.warning(f"Error getting chat messages: {e}")
            return []
    
    async def get_scene(self, scene_id: str) -> Dict[str, Any]:
        """Get scene data from relay server"""
        try:
            import requests
            
            headers = {"x-api-key": "local-dev"}
            
            response = requests.get(
                f"http://localhost:3010/scenes/{scene_id}",
                headers=headers,
                timeout=5
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                self.logger.warning(f"Failed to get scene {scene_id}: {response.status_code}")
                return {}
                
        except Exception as e:
            self.logger.warning(f"Error getting scene {scene_id}: {e}")
            return {}
    
    async def get_scene_walls(self, scene_id: str) -> List[Dict[str, Any]]:
        """Get scene walls from relay server"""
        try:
            import requests
            
            headers = {"x-api-key": "local-dev"}
            
            response = requests.get(
                f"http://localhost:3010/scenes/{scene_id}/walls",
                headers=headers,
                timeout=5
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                self.logger.warning(f"Failed to get scene walls {scene_id}: {response.status_code}")
                return []
                
        except Exception as e:
            self.logger.warning(f"Error getting scene walls {scene_id}: {e}")
            return []
    
    async def get_scene_notes(self, scene_id: str) -> List[Dict[str, Any]]:
        """Get scene notes from relay server"""
        try:
            import requests
            
            headers = {"x-api-key": "local-dev"}
            
            response = requests.get(
                f"http://localhost:3010/scenes/{scene_id}/notes",
                headers=headers,
                timeout=5
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                self.logger.warning(f"Failed to get scene notes {scene_id}: {response.status_code}")
                return []
                
        except Exception as e:
            self.logger.warning(f"Error getting scene notes {scene_id}: {e}")
            return []
    
    async def get_scene_tokens(self, scene_id: str) -> List[Dict[str, Any]]:
        """Get scene tokens from relay server"""
        try:
            import requests
            
            headers = {"x-api-key": "local-dev"}
            
            response = requests.get(
                f"http://localhost:3010/scenes/{scene_id}/tokens",
                headers=headers,
                timeout=5
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                self.logger.warning(f"Failed to get scene tokens {scene_id}: {response.status_code}")
                return []
                
        except Exception as e:
            self.logger.warning(f"Error getting scene tokens {scene_id}: {e}")
            return []
    
    async def get_scene_templates(self, scene_id: str) -> List[Dict[str, Any]]:
        """Get scene templates from relay server"""
        try:
            import requests
            
            headers = {"x-api-key": "local-dev"}
            
            response = requests.get(
                f"http://localhost:3010/scenes/{scene_id}/templates",
                headers=headers,
                timeout=5
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                self.logger.warning(f"Failed to get scene templates {scene_id}: {response.status_code}")
                return []
                
        except Exception as e:
            self.logger.warning(f"Error getting scene templates {scene_id}: {e}")
            return []
    
    async def get_actor(self, actor_id: str) -> Dict[str, Any]:
        """Get actor data from relay server"""
        try:
            import requests
            
            headers = {"x-api-key": "local-dev"}
            
            response = requests.get(
                f"http://localhost:3010/actors/{actor_id}",
                headers=headers,
                timeout=5
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                self.logger.warning(f"Failed to get actor {actor_id}: {response.status_code}")
                return {}
                
        except Exception as e:
            self.logger.warning(f"Error getting actor {actor_id}: {e}")
            return {}


# Real AI Service wrapper for context chat
class RealAIService:
    """Real AI service wrapper that uses actual AI service with universal settings"""
    
    def __init__(self, ai_service):
        self.ai_service = ai_service
        self.logger = logging.getLogger(__name__)
    
    async def process_chat_request(self, request: Dict[str, Any], settings: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Process chat request using real AI service with universal settings
        
        Args:
            request: AI request with system_prompt, user_message, and options
            settings: Validated universal settings (from backend storage)
            
        Returns:
            AI response with success/error info
        """
        try:
            system_prompt = request.get('system_prompt', '')
            user_message = request.get('user_message', '')
            options = request.get('options', {})
            
            # Use universal settings if provided, otherwise fall back to request options
            if settings:
                # Extract provider config from universal settings (same as api_chat)
                provider_config = get_provider_config(settings, use_tactical=False)
                
                provider_id = provider_config['provider']
                model = provider_config['model']
                base_url = provider_config['base_url']
                api_version = provider_config['api_version']
                timeout = provider_config['timeout']
                max_retries = provider_config['max_retries']
                custom_headers = provider_config.get('headers', {})
                
                self.logger.info(f"Using universal settings - provider: {provider_id}, model: {model}")
            else:
                # Fallback to request options (should not happen with proper integration)
                provider_id = 'openrouter'
                model = options.get('model', 'openai/gpt-4')
                base_url = options.get('base_url')
                api_version = 'v1'
                timeout = options.get('timeout', 30)
                max_retries = 3
                custom_headers = {}
                
                self.logger.warning(f"No universal settings provided, using fallback - provider: {provider_id}, model: {model}")
            
            # Build messages for AI service
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ]
            
            # Call real AI service with proper settings
            result = await self.ai_service.call_ai_provider(messages, {
                'provider': provider_id,
                'model': model,
                'api_key': None,  # Will be loaded by provider manager from stored keys
                'base_url': base_url,
                'timeout': timeout,
                'temperature': options.get('temperature', 0.7),
                'max_tokens': options.get('max_tokens', 2000),
                'api_version': api_version,
                'max_retries': max_retries,
                'custom_headers': custom_headers
            })
            
            if result.get('success'):
                return {
                    'response': result.get('response', ''),
                    'tokens_used': result.get('tokens_used', 0),
                    'model': result.get('metadata', {}).get('model', model),
                    'provider_used': provider_id
                }
            else:
                return {
                    'response': f'AI service error: {result.get("error", "Unknown error")}',
                    'tokens_used': 0,
                    'model': model,
                    'provider_used': provider_id,
                    'error': result.get('error')
                }
                
        except Exception as e:
            self.logger.error(f"Error in real AI service: {e}")
            return {
                'response': f'Service error: {str(e)}',
                'tokens_used': 0,
                'model': 'unknown',
                'provider_used': 'unknown',
                'error': str(e)
            }


# Mock dependencies for testing (keep for fallback)
class MockAIService:
    """Mock AI service for testing"""
    
    async def process_chat_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        await asyncio.sleep(0.1)  # Simulate processing time
        
        user_message = request.get('user_message', '')
        
        # Generate a contextual response based on the message
        if 'door' in user_message.lower():
            return {
                'response': 'Based on the door you found and the fighter\'s position, I recommend checking for traps before opening it. The door appears to be wooden with strange markings.',
                'tokens_used': 150,
                'model': request.get('options', {}).get('model', 'gpt-4')
            }
        elif 'move' in user_message.lower():
            return {
                'response': 'Considering your current position and the wall layout, moving forward seems safe. The fighter has good health and armor for any potential threats.',
                'tokens_used': 120,
                'model': request.get('options', {}).get('model', 'gpt-4')
            }
        else:
            return {
                'response': 'I see you\'re in a dungeon scene with a door, walls, and good lighting. The fighter appears ready for action. What would you like to do next?',
                'tokens_used': 100,
                'model': request.get('options', {}).get('model', 'gpt-4')
            }


class MockFoundryClient:
    """Mock Foundry client for testing"""
    
    async def get_chat_messages(self, client_id: str, count: int):
        return []  # Would return actual chat messages


# Test the implementation
if __name__ == "__main__":
    import asyncio
    import json
    
    async def test_context_chat_endpoint():
        # Create mocks
        ai_service = MockAIService()
        foundry_client = MockFoundryClient()
        
        # Create endpoint
        endpoint = ContextChatEndpoint(ai_service, foundry_client)
        
        # Test request
        test_request = {
            "client_id": "test_client_123",
            "scene_id": "dungeon_scene_456",
            "message": "I want to move forward and investigate the door I see.",
            "context_options": {
                "include_chat_history": True,
                "message_count": 10,
                "include_scene_data": True,
                "include_tokens": True,
                "include_walls": True
            },
            "ai_options": {
                "model": "gpt-4",
                "temperature": 0.7,
                "max_tokens": 1500
            }
        }
        
        # Process request
        response = await endpoint.handle_context_chat(test_request)
        
        print("=== CONTEXT CHAT RESPONSE ===")
        print(json.dumps(response, indent=2))
    
    asyncio.run(test_context_chat_endpoint())
