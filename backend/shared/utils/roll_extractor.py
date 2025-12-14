"""
Roll Data Extractor - Unified roll data extraction and normalization
Eliminates redundant roll processing logic across services
"""

import logging
from typing import Dict, Any, Optional, List, Union
from shared.exceptions import MessageValidationException
from shared.utils.message_type_detector import is_dice_message


class RollExtractor:
    """
    Unified roll data extraction and normalization
    Single source of truth for roll data processing
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Define standard roll field mappings
        self._field_mappings = {
            # Primary result fields
            'result': ['result', 'total', 'value', 'sum', 'outcome'],
            'formula': ['formula', 'roll', 'dice_formula', 'expression'],
            'flavor': ['flavor', 'description', 'note', 'text'],
            'user': ['user', 'player', 'character', 'name', 'sender'],
            'timestamp': ['timestamp', 'time', 'date', 'created_at'],
            
            # Dice-specific fields
            'dice': ['dice', 'dice_rolls', 'individual_rolls', 'results'],
            'critical': ['critical', 'crit', 'critical_success'],
            'fumble': ['fumble', 'critical_failure', 'botch', 'crit_fail'],
            'success': ['success', 'passed', 'success_flag'],
            'type': ['type', 'roll_type', 'category']
        }
    
    def extract_roll_data(self, message: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Extract and normalize roll data from a message
        
        Args:
            message: Message dictionary containing roll data
            
        Returns:
            Normalized roll data or None if not a roll message
            
        Raises:
            MessageValidationException: When message is invalid
        """
        if not message or not isinstance(message, dict):
            raise MessageValidationException("Message must be a non-empty dictionary")
        
        # Check if this is actually a roll message
        if not is_dice_message(message):
            return None
        
        try:
            # Extract normalized roll data
            roll_data = {
                'type': 'roll',
                'timestamp': self._extract_timestamp(message),
                'user': self._extract_user(message),
                'formula': self._extract_formula(message),
                'result': self._extract_result(message),
                'flavor': self._extract_flavor(message),
                'critical': self._extract_critical(message),
                'fumble': self._extract_fumble(message),
                'success': self._extract_success(message),
                'dice': self._extract_dice(message)
            }
            
            # Add original message for reference
            roll_data['_original'] = message
            
            # Validate essential fields
            if not roll_data.get('result') and not roll_data.get('dice'):
                self.logger.warning("Roll message missing both result and dice data")
                return None
            
            return roll_data
            
        except Exception as e:
            self.logger.error(f"Error extracting roll data: {e}")
            raise MessageValidationException(f"Failed to extract roll data: {e}")
    
    def normalize_roll_list(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Normalize a list of messages, extracting only roll data
        
        Args:
            messages: List of message dictionaries
            
        Returns:
            List of normalized roll data
            
        Raises:
            MessageValidationException: When any message is invalid
        """
        if not messages:
            return []
        
        normalized_rolls = []
        
        for i, message in enumerate(messages):
            if not message or not isinstance(message, dict):
                raise MessageValidationException(f"Message at index {i} must be a non-empty dictionary")
            
            try:
                roll_data = self.extract_roll_data(message)
                if roll_data:
                    normalized_rolls.append(roll_data)
            except MessageValidationException:
                # Skip invalid roll messages but continue processing
                continue
        
        return normalized_rolls
    
    def extract_roll_components(self, formula: str) -> Dict[str, Any]:
        """
        Extract components from a dice formula
        
        Args:
            formula: Dice formula string (e.g., "2d6+3", "1d20+5")
            
        Returns:
            Dictionary with parsed components
            
        Raises:
            MessageValidationException: When formula is invalid
        """
        if not formula or not isinstance(formula, str):
            return {'valid': False, 'error': 'Formula must be a non-empty string'}
        
        try:
            import re
            
            # Basic dice formula pattern: NdS(+/-M)
            pattern = r'^(\d+)?[dD](\d+)([+\-]\d+)?$'
            match = re.match(pattern, formula.strip())
            
            if not match:
                return {'valid': False, 'error': f'Invalid dice formula: {formula}'}
            
            groups = match.groups()
            
            components = {
                'valid': True,
                'formula': formula.strip(),
                'num_dice': int(groups[0]) if groups[0] else 1,
                'sides': int(groups[1]) if groups[1] else 6,
                'modifier': int(groups[2]) if groups[2] else 0
            }
            
            # Calculate min/max possible values
            components['min_possible'] = components['num_dice'] + components['modifier']
            components['max_possible'] = (components['num_dice'] * components['sides']) + components['modifier']
            components['average'] = ((components['min_possible'] + components['max_possible']) / 2)
            
            return components
            
        except Exception as e:
            return {'valid': False, 'error': f'Error parsing formula {formula}: {e}'}
    
    def calculate_roll_statistics(self, rolls: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Calculate statistics for a list of rolls
        
        Args:
            rolls: List of normalized roll data
            
        Returns:
            Dictionary with roll statistics
        """
        if not rolls:
            return {
                'count': 0,
                'success_rate': 0,
                'critical_rate': 0,
                'fumble_rate': 0
            }
        
        count = len(rolls)
        successes = sum(1 for roll in rolls if roll.get('success'))
        criticals = sum(1 for roll in rolls if roll.get('critical'))
        fumbles = sum(1 for roll in rolls if roll.get('fumble'))
        
        results = [roll.get('result', 0) for roll in rolls if roll.get('result') is not None]
        
        stats = {
            'count': count,
            'success_rate': (successes / count) * 100 if count > 0 else 0,
            'critical_rate': (criticals / count) * 100 if count > 0 else 0,
            'fumble_rate': (fumbles / count) * 100 if count > 0 else 0,
            'successes': successes,
            'criticals': criticals,
            'fumbles': fumbles
        }
        
        if results:
            stats.update({
                'result_min': min(results),
                'result_max': max(results),
                'result_avg': sum(results) / len(results),
                'result_count': len(results)
            })
        
        return stats
    
    def _extract_field_value(self, message: Dict[str, Any], field_name: str) -> Any:
        """
        Extract field value using mappings
        
        Args:
            message: Message dictionary
            field_name: Target field name
            
        Returns:
            Field value or None
        """
        if field_name not in self._field_mappings:
            return None
        
        for possible_field in self._field_mappings[field_name]:
            if possible_field in message:
                return message[possible_field]
        
        return None
    
    def _extract_timestamp(self, message: Dict[str, Any]) -> Optional[int]:
        """Extract timestamp from message"""
        timestamp = self._extract_field_value(message, 'timestamp')
        
        if timestamp is None:
            return None
        
        # Convert to int if needed
        if isinstance(timestamp, str):
            try:
                timestamp = int(timestamp)
            except ValueError:
                return None
        elif isinstance(timestamp, float):
            timestamp = int(timestamp)
        
        return timestamp if isinstance(timestamp, int) else None
    
    def _extract_user(self, message: Dict[str, Any]) -> str:
        """Extract user name from message"""
        user = self._extract_field_value(message, 'user')
        return str(user) if user is not None else 'Unknown'
    
    def _extract_formula(self, message: Dict[str, Any]) -> str:
        """Extract dice formula from message"""
        formula = self._extract_field_value(message, 'formula')
        return str(formula) if formula is not None else ''
    
    def _extract_result(self, message: Dict[str, Any]) -> Optional[Union[int, float]]:
        """Extract roll result from message"""
        result = self._extract_field_value(message, 'result')
        
        if result is None:
            return None
        
        try:
            if isinstance(result, str):
                # Try to extract number from string
                import re
                numbers = re.findall(r'-?\d+\.?\d*', result)
                if numbers:
                    return float(numbers[0]) if '.' in numbers[0] else int(numbers[0])
            return result
        except (ValueError, TypeError):
            return None
    
    def _extract_flavor(self, message: Dict[str, Any]) -> str:
        """Extract flavor text from message"""
        flavor = self._extract_field_value(message, 'flavor')
        return str(flavor) if flavor is not None else ''
    
    def _extract_critical(self, message: Dict[str, Any]) -> bool:
        """Extract critical flag from message"""
        critical = self._extract_field_value(message, 'critical')
        
        if critical is None:
            return False
        
        # Handle various boolean representations
        if isinstance(critical, bool):
            return critical
        elif isinstance(critical, str):
            return critical.lower() in ('true', '1', 'yes', 'crit', 'critical')
        elif isinstance(critical, (int, float)):
            return critical != 0
        
        return bool(critical)
    
    def _extract_fumble(self, message: Dict[str, Any]) -> bool:
        """Extract fumble flag from message"""
        fumble = self._extract_field_value(message, 'fumble')
        
        if fumble is None:
            return False
        
        # Handle various boolean representations
        if isinstance(fumble, bool):
            return fumble
        elif isinstance(fumble, str):
            return fumble.lower() in ('true', '1', 'yes', 'fumble', 'botch', 'crit_fail')
        elif isinstance(fumble, (int, float)):
            return fumble != 0
        
        return bool(fumble)
    
    def _extract_success(self, message: Dict[str, Any]) -> Optional[bool]:
        """Extract success flag from message"""
        success = self._extract_field_value(message, 'success')
        
        if success is None:
            return None
        
        # Handle various boolean representations
        if isinstance(success, bool):
            return success
        elif isinstance(success, str):
            success_lower = success.lower()
            if success_lower in ('true', '1', 'yes', 'pass', 'success'):
                return True
            elif success_lower in ('false', '0', 'no', 'fail', 'failure'):
                return False
        elif isinstance(success, (int, float)):
            return success != 0
        
        return bool(success)
    
    def _extract_dice(self, message: Dict[str, Any]) -> Optional[List[Any]]:
        """Extract individual dice results from message"""
        dice = self._extract_field_value(message, 'dice')
        
        if dice is None:
            return None
        
        if isinstance(dice, list):
            return dice
        elif isinstance(dice, str):
            # Try to parse dice results from string
            import re
            numbers = re.findall(r'\d+', dice)
            return [int(n) for n in numbers] if numbers else None
        
        return [dice] if isinstance(dice, (int, float)) else None
    
    def get_extraction_stats(self) -> Dict[str, Any]:
        """
        Get statistics about field mappings and extraction
        
        Returns:
            Dictionary with extraction configuration
        """
        return {
            'field_mappings': self._field_mappings,
            'total_fields': len(self._field_mappings),
            'supported_mappings': {k: len(v) for k, v in self._field_mappings.items()}
        }


# Global extractor instance for convenience
_extractor = RollExtractor()


def extract_roll_data(message: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Convenience function for roll data extraction
    
    Args:
        message: Message dictionary containing roll data
        
    Returns:
        Normalized roll data or None
    """
    return _extractor.extract_roll_data(message)


def normalize_roll_list(messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Convenience function to normalize roll list
    
    Args:
        messages: List of message dictionaries
        
    Returns:
        List of normalized roll data
    """
    return _extractor.normalize_roll_list(messages)


def extract_roll_components(formula: str) -> Dict[str, Any]:
    """
    Convenience function to extract formula components
    
    Args:
        formula: Dice formula string
        
    Returns:
        Dictionary with parsed components
    """
    return _extractor.extract_roll_components(formula)


def calculate_roll_statistics(rolls: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Convenience function to calculate roll statistics
    
    Args:
        rolls: List of normalized roll data
        
    Returns:
        Dictionary with roll statistics
    """
    return _extractor.calculate_roll_statistics(rolls)
