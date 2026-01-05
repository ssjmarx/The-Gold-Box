"""
AI Prompt Builder Utility
Shared utility for building initial messages with delta injection
Used by both production API and testing harness to ensure consistency
"""

import logging
import json
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

# Import log truncation utility
from shared.utils.log_utils import truncate_for_log


def build_initial_messages_with_delta(
    universal_settings: Dict[str, Any],
    system_prompt: str,
    is_first_turn: bool = True
) -> List[Dict[str, Any]]:
    """
    Build initial messages for AI with delta or full context injection
    
    This function is used by both production API endpoint and testing harness
    to ensure consistent delta handling across codebase. This provides a single
    source of truth for delta injection logic.
    
    Args:
        universal_settings: Settings dictionary containing 'message_delta', 'ai role', and 'client_id'
        system_prompt: Base system prompt (without delta information)
        is_first_turn: Whether this is the first turn for the session (default: True)
        
    Returns:
        List of messages in OpenAI format:
        [
            {"role": "system", "content": system_prompt + delta_display or full_context},
            {"role": "user", "content": user_message}
        ]
    """
    try:
        if is_first_turn:
            # FIRST TURN: Build full initial context
            logger.info(f"Building initial context for first turn")
            
            # Build initial world context
            try:
                from services.message_services.context_builder import get_context_builder
                context_builder = get_context_builder()
                client_id = universal_settings.get('relay_client_id', '')
                initial_context = context_builder.build_initial_context(client_id)
                
                # Inject full context into system prompt
                context_display = f"""

World State Overview:
{json.dumps(initial_context, indent=2)}
"""
                logger.info(f"Full initial context injected for first turn: {truncate_for_log(initial_context)}")
                system_prompt_with_context = system_prompt + context_display
            except Exception as e:
                logger.warning(f"Failed to build initial context: {e}")
                system_prompt_with_context = system_prompt
        else:
            # SUCCESSIVE TURN: Use deltas only
            logger.info(f"Building delta context for successive turn")
            
            # Get delta from settings (use PascalCase as specified in ROADMAP)
            message_delta = universal_settings.get('message_delta', {})
            has_changes = message_delta.get('hasChanges', False)
            
            # Build delta display based on whether there are changes
            if has_changes:
                # Include full delta data with all details (dice rolls, combat events, etc.)
                delta_display = f"""

Recent changes to the game:
{json.dumps(message_delta, indent=2)}
"""
                logger.info(f"Delta hasChanges: True - including full delta JSON: {truncate_for_log(message_delta)}")
            else:
                # No changes - show clear message
                delta_display = """

No changes to game state since last AI turn
"""
                logger.info(f"Delta hasChanges: False - no changes to report")
            
            # Append delta to system_prompt
            system_prompt_with_context = system_prompt + delta_display
        
        # Get AI role from settings to make message role-aware
        ai_role = universal_settings.get('ai role', 'gm').lower()
        
        # Map role to appropriate user message
        role_messages = {
            'gm': 'Take your turn as Game Master.',
            "gm's assistant": 'Take your turn as GM\'s Assistant.',
            'player': 'Take your turn as Player.'
        }
        
        user_message = role_messages.get(ai_role, 'Take your turn as Game Master.')
        
        # Return OpenAI format messages
        return [
            {"role": "system", "content": system_prompt_with_context},
            {"role": "user", "content": user_message}
        ]
        
    except Exception as e:
        logger.error(f"Error building initial messages with delta: {e}")
        # Fallback: return system prompt without delta
        ai_role = universal_settings.get('ai role', 'gm').lower()
        role_messages = {
            'gm': 'Take your turn as Game Master.',
            "gm's assistant": 'Take your turn as GM\'s Assistant.',
            'player': 'Take your turn as Player.'
        }
        user_message = role_messages.get(ai_role, 'Take your turn as Game Master.')
        
        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ]
