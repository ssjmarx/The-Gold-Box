"""
Dice Message Collector - Collects dice roll messages alongside chat messages
Uses existing API chat endpoint code for dice collection
"""

import logging
from typing import Dict, List, Any, Optional
import requests


class DiceMessageCollector:
    """
    Collects dice roll messages alongside chat messages
    Uses existing API chat endpoint code for dice collection
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.relay_base_url = "http://localhost:3010"
    
    async def collect_dice_messages(self, client_id: str, count: int) -> List[Dict[str, Any]]:
        """
        Gets dice rolls from relay server
        Combines with chat messages for complete context
        
        Args:
            client_id: Foundry client identifier
            count: Number of recent dice messages to collect
            
        Returns:
            List of dice roll messages with metadata
        """
        
        try:
            headers = {"x-api-key": "local-dev"}  # Works for local memory store
            
            # Get dice rolls from relay server with clear flag to force fresh data
            response = requests.get(
                f"{self.relay_base_url}/rolls",
                params={
                    "clientId": client_id, 
                    "limit": count, 
                    "sort": "timestamp", 
                    "order": "desc",
                    "clear": "true",  # Force clear cache to get fresh data
                    "refresh": "true"  # Also refresh from chat log
                },
                headers=headers,
                timeout=3
            )
            
            if response.status_code == 200:
                data = response.json()
                
                # Handle different response formats
                if isinstance(data, dict) and 'data' in data:
                    # Relay server puts rolls in 'data' field
                    dice_messages = data['data']
                elif isinstance(data, dict) and 'rolls' in data:
                    # Alternative format
                    dice_messages = data['rolls']
                elif isinstance(data, list):
                    # Direct list response
                    dice_messages = data
                else:
                    dice_messages = []
                
                # Process and format dice messages
                processed_messages = []
                for msg in dice_messages:
                    processed_msg = self._format_dice_message(msg)
                    if processed_msg:
                        processed_messages.append(processed_msg)
                
                self.logger.info(f"Collected {len(processed_messages)} dice messages for client {client_id}")
                return processed_messages
                
            else:
                self.logger.warning(f"Failed to get dice messages: {response.status_code}")
                return []
                
        except Exception as e:
            self.logger.warning(f"Error collecting dice messages: {e}")
            return []
    
    def _format_dice_message(self, raw_message: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Format dice message for consistent processing
        
        Args:
            raw_message: Raw dice message from relay server
            
        Returns:
            Formatted dice message or None if invalid
        """
        
        try:
            # Extract common dice message fields
            formatted = {
                'type': 'dice',
                'timestamp': raw_message.get('timestamp', 0),
                'user': raw_message.get('user', 'Unknown'),
                'roll': raw_message.get('roll', ''),
                'result': raw_message.get('result', 0),
                'formula': raw_message.get('formula', ''),
                'flavor': raw_message.get('flavor', ''),
                'critical': raw_message.get('critical', False),
                'fumble': raw_message.get('fumble', False),
                'details': raw_message.get('details', [])
            }
            
            # Add roll-specific data if available
            if 'dice' in raw_message:
                formatted['dice'] = raw_message['dice']  # Individual dice results
            
            if 'total' in raw_message:
                formatted['total'] = raw_message['total']  # Total roll result
            
            if 'success' in raw_message:
                formatted['success'] = raw_message['success']  # Success/failure indicator
            
            # Only return if we have meaningful content
            if formatted['roll'] or formatted['result'] is not None or formatted['formula']:
                return formatted
            else:
                return None
                
        except Exception as e:
            self.logger.warning(f"Error formatting dice message: {e}")
            return None
    
    async def collect_combined_context(self, client_id: str, count: int) -> Dict[str, Any]:
        """
        Collect both chat messages and dice rolls for complete context
        
        Args:
            client_id: Foundry client identifier  
            count: Number of recent messages to collect (each type)
            
        Returns:
            Dictionary with combined chat and dice context
        """
        
        try:
            # Import here to avoid circular imports
            from endpoints.api_chat import collect_chat_messages_api
            
            # Collect chat messages
            chat_messages = await collect_chat_messages_api(count, {'relayClientId': client_id})
            
            # Collect dice messages
            dice_messages = await self.collect_dice_messages(client_id, count)
            
            # Combine and sort by timestamp
            all_messages = []
            
            # Add chat messages with type marker
            for msg in chat_messages:
                msg['_source'] = 'chat'
                msg['_timestamp'] = msg.get('timestamp', 0)
                all_messages.append(msg)
            
            # Add dice messages with type marker
            for msg in dice_messages:
                msg['_source'] = 'dice'
                msg['_timestamp'] = msg.get('timestamp', 0)
                all_messages.append(msg)
            
            # Sort by timestamp (newest first, then reverse for chronological)
            all_messages.sort(key=lambda x: x.get('_timestamp', 0), reverse=True)
            combined_messages = list(reversed(all_messages[:count * 2]))  # Get 2x count to allow for both types
            
            self.logger.info(f"Combined context: {len(chat_messages)} chat + {len(dice_messages)} dice = {len(combined_messages)} total messages")
            
            return {
                'messages': combined_messages,
                'chat_count': len(chat_messages),
                'dice_count': len(dice_messages),
                'total_count': len(combined_messages)
            }
            
        except Exception as e:
            self.logger.error(f"Error collecting combined context: {e}")
            return {
                'messages': [],
                'chat_count': 0,
                'dice_count': 0,
                'total_count': 0
            }


# Mock implementation for testing
class MockDiceMessageCollector:
    """Mock dice collector for testing"""
    
    async def collect_dice_messages(self, client_id: str, count: int) -> List[Dict[str, Any]]:
        """Mock dice message collection"""
        
        # Return sample dice messages for testing
        mock_dice = [
            {
                'type': 'dice',
                'timestamp': 1635724800,
                'user': 'GM',
                'roll': 'Attack Roll',
                'result': 18,
                'formula': '1d20+5',
                'flavor': 'Longsword attack',
                'critical': True,
                'fumble': False
            },
            {
                'type': 'dice',
                'timestamp': 1635724790,
                'user': 'Player',
                'roll': 'Damage Roll',
                'result': 8,
                'formula': '1d8+3',
                'flavor': 'Slashing damage',
                'critical': False,
                'fumble': False
            }
        ]
        
        return mock_dice[:count]
    
    async def collect_combined_context(self, client_id: str, count: int) -> Dict[str, Any]:
        """Mock combined context collection"""
        return {
            'messages': [],
            'chat_count': 0,
            'dice_count': 2,
            'total_count': 2
        }


# Test implementation
if __name__ == "__main__":
    import asyncio
    
    async def test_dice_collector():
        # Test with real collector
        collector = DiceMessageCollector()
        
        # Test dice collection
        dice_messages = await collector.collect_dice_messages("test_client", 5)
        print("Dice Messages:")
        for msg in dice_messages:
            print(f"  {msg}")
        
        # Test combined context
        combined = await collector.collect_combined_context("test_client", 10)
        print(f"\nCombined Context: {combined}")
        
        # Test with mock
        print("\n--- Testing Mock Collector ---")
        mock_collector = MockDiceMessageCollector()
        mock_dice = await mock_collector.collect_dice_messages("mock_client", 3)
        print("Mock Dice Messages:")
        for msg in mock_dice:
            print(f"  {msg}")
    
    asyncio.run(test_dice_collector())
