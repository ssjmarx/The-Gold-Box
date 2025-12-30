#!/usr/bin/env python3
"""
AI Prompt Data Validator Module
Validates data quality before sending to AI to prevent corrupted prompts
"""

import logging
import json
import re
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple, Union

logger = logging.getLogger(__name__)

class DataValidationError(Exception):
    """Custom exception for data validation failures"""
    pass

class AIPromptValidator:
    """Validates and ensures data quality for AI prompts"""
    
    def __init__(self, strict_mode: bool = False):
        self.strict_mode = strict_mode
        self.validation_results = {
            'is_valid': True,
            'errors': [],
            'warnings': [],
            'data_quality_score': 100,
            'context_completeness': 100,
            'data_freshness': 100
        }
    
    def validate_roll_data(self, roll: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """Validate individual roll data structure"""
        required_fields = ['t', 'f', 'r', 'tt', 's', 'ts']
        
        # Check required fields
        for field in required_fields:
            if field not in roll or roll[field] is None:
                return False, f"Missing required field: {field}"
        
        # Validate roll type
        if roll['t'] != 'dr':
            return False, f"Invalid roll type: {roll['t']} (expected 'dr')"
        
        # Validate formula
        formula = roll.get('f', '').strip()
        if not formula:
            return False, "Empty roll formula"
        
        # Basic formula validation
        if not self._is_valid_dice_formula(formula):
            return False, f"Invalid dice formula: {formula}"
        
        # Validate roll total
        try:
            total = int(roll['tt'])
            if total < 0:
                return False, f"Negative roll total: {total}"
        except (ValueError, TypeError):
            return False, f"Invalid roll total: {roll['tt']}"
        
        # Validate dice array
        dice = roll.get('r', [])
        if not isinstance(dice, list):
            return False, "Roll results must be an array"
        
        # Validate timestamp
        try:
            timestamp = int(roll['ts'])
            # Check if timestamp is reasonable (not too old or future)
            now = datetime.now().timestamp() * 1000  # Convert to milliseconds
            one_hour_ago = now - (60 * 60 * 1000)  # 1 hour in milliseconds
            if timestamp > now + (5 * 60 * 1000):  # 5 minutes future allowed
                return False, f"Future timestamp: {timestamp}"
            if timestamp < one_hour_ago:
                if self.strict_mode:
                    return False, f"Old timestamp: {timestamp}"
                else:
                    self.validation_results['warnings'].append(f"Old roll timestamp: {timestamp}")
        except (ValueError, TypeError):
            return False, f"Invalid timestamp: {roll['ts']}"
        
        return True, None
    
    def validate_chat_data(self, chat: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """Validate individual chat message data structure"""
        required_fields = ['t', 'c', 's', 'ts']
        
        # Check required fields
        for field in required_fields:
            if field not in chat or chat[field] is None:
                return False, f"Missing required field: {field}"
        
        # Validate chat type
        if chat['t'] != 'cm':
            return False, f"Invalid chat type: {chat['t']} (expected 'cm')"
        
        # Validate content
        content = chat.get('c', '').strip()
        if not content or len(content) < 3:
            return False, f"Empty or too short chat content: '{content}'"
        
        # Check for HTML/structural corruption
        if self._is_corrupted_html(content):
            return False, "Chat content appears corrupted (excessive HTML fragments)"
        
        # Validate speaker
        speaker = chat.get('s', '').strip()
        if not speaker:
            return False, "Empty speaker name"
        
        # Validate timestamp
        try:
            timestamp = int(chat['ts'])
            now = datetime.now().timestamp() * 1000
            if timestamp > now + (5 * 60 * 1000):
                return False, f"Future timestamp: {timestamp}"
            if timestamp < now - (2 * 60 * 60 * 1000):  # 2 hours ago
                if self.strict_mode:
                    return False, f"Old timestamp: {timestamp}"
                else:
                    self.validation_results['warnings'].append(f"Old chat message: {timestamp}")
        except (ValueError, TypeError):
            return False, f"Invalid timestamp: {chat['ts']}"
        
        return True, None
    
    def validate_context_completeness(self, messages: List[Dict[str, Any]], rolls: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Validate overall context completeness"""
        total_messages = len(messages)
        total_rolls = len(rolls)
        total_items = total_messages + total_rolls
        
        # Minimum context requirements
        if total_items == 0:
            return {
                'completeness_score': 0,
                'assessment': 'NO_DATA',
                'message': 'No chat or roll data available'
            }
        
        # More lenient completeness scoring - focus on having any valid data
        if total_items >= 2:
            completeness_score = 70  # Base score for having some data
        elif total_items >= 1:
            completeness_score = 50  # Lower score for minimal data
        else:
            completeness_score = 0
        
        # Context diversity check
        has_chat = total_messages > 0
        has_rolls = total_rolls > 0
        diversity_bonus = 20 if (has_chat and has_rolls) else (10 if has_chat else 0)
        
        completeness_score = min(100, completeness_score + diversity_bonus)
        
        assessment = 'EXCELLENT' if completeness_score >= 80 else \
                    'GOOD' if completeness_score >= 60 else \
                    'FAIR' if completeness_score >= 40 else \
                    'POOR' if completeness_score >= 20 else 'INADEQUATE'
        
        return {
            'completeness_score': completeness_score,
            'assessment': assessment,
            'message_count': total_messages,
            'roll_count': total_rolls,
            'has_chat': has_chat,
            'has_rolls': has_rolls,
            'diversity_bonus': diversity_bonus
        }
    
    def validate_data_freshness(self, messages: List[Dict[str, Any]], rolls: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Validate data recency and freshness"""
        if not messages and not rolls:
            return {
                'freshness_score': 0,
                'assessment': 'STALE',
                'message': 'No data to evaluate freshness'
            }
        
        now = datetime.now().timestamp() * 1000  # Convert to milliseconds
        
        # Get timestamps from all items
        all_timestamps = []
        for msg in messages:
            if 'ts' in msg:
                try:
                    all_timestamps.append(int(msg['ts']))
                except (ValueError, TypeError):
                    continue
        
        for roll in rolls:
            if 'ts' in roll:
                try:
                    all_timestamps.append(int(roll['ts']))
                except (ValueError, TypeError):
                    continue
        
        if not all_timestamps:
            return {
                'freshness_score': 0,
                'assessment': 'NO_TIMESTAMPS',
                'message': 'No valid timestamps found in data'
            }
        
        # Calculate freshness based on most recent data
        most_recent = max(all_timestamps)
        age_minutes = (now - most_recent) / (60 * 1000)  # Convert to minutes
        
        if age_minutes <= 5:
            freshness_score = 100
            assessment = 'FRESH'
        elif age_minutes <= 15:
            freshness_score = 80
            assessment = 'RECENT'
        elif age_minutes <= 60:
            freshness_score = 60
            assessment = 'MODERATELY_FRESH'
        else:
            freshness_score = 30
            assessment = 'STALE'
            self.validation_results['warnings'].append(f"Data is {age_minutes:.0f} minutes old")
        
        return {
            'freshness_score': freshness_score,
            'assessment': assessment,
            'age_minutes': age_minutes,
            'most_recent_timestamp': most_recent
        }
    
    def validate_overall_quality(self, messages: List[Dict[str, Any]], rolls: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate overall data quality score"""
        # Individual item validation
        valid_messages = 0
        valid_rolls = 0
        total_corruption_issues = 0
        
        for msg in messages:
            is_valid, error = self.validate_chat_data(msg)
            if is_valid:
                valid_messages += 1
            else:
                total_corruption_issues += 1
                self.validation_results['errors'].append(f"Chat data invalid: {error}")
        
        for roll in rolls:
            is_valid, error = self.validate_roll_data(roll)
            if is_valid:
                valid_rolls += 1
            else:
                total_corruption_issues += 1
                self.validation_results['errors'].append(f"Roll data invalid: {error}")
        
        total_items = len(messages) + len(rolls)
        if total_items == 0:
            return {
                'quality_score': 0,
                'assessment': 'NO_DATA',
                'valid_messages': 0,
                'valid_rolls': 0,
                'corruption_rate': 0
            }
        
        # Calculate quality metrics
        valid_items = valid_messages + valid_rolls
        quality_score = (valid_items / total_items) * 100
        corruption_rate = (total_corruption_issues / total_items) * 100
        
        assessment = 'EXCELLENT' if quality_score >= 95 else \
                    'GOOD' if quality_score >= 85 else \
                    'FAIR' if quality_score >= 70 else \
                    'POOR' if quality_score >= 50 else 'UNACCEPTABLE'
        
        return {
            'quality_score': quality_score,
            'assessment': assessment,
            'valid_messages': valid_messages,
            'valid_rolls': valid_rolls,
            'total_items': total_items,
            'corruption_rate': corruption_rate
        }
    
    def validate_prompt_context(self, messages: List[Dict[str, Any]], rolls: List[Dict[str, Any]], 
                           scene_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Main validation function for complete prompt context"""
        self.validation_results = {
            'is_valid': True,
            'errors': [],
            'warnings': [],
            'data_quality_score': 100,
            'context_completeness': 100,
            'data_freshness': 100,
            'validation_timestamp': datetime.now().isoformat(),
            'recommendations': []
        }
        
        try:
            # Validate individual items
            for i, msg in enumerate(messages):
                is_valid, error = self.validate_chat_data(msg)
                if not is_valid:
                    self.validation_results['is_valid'] = False
                    self.validation_results['errors'].append(f"Chat message {i}: {error}")
            
            for i, roll in enumerate(rolls):
                is_valid, error = self.validate_roll_data(roll)
                if not is_valid:
                    self.validation_results['is_valid'] = False
                    self.validation_results['errors'].append(f"Roll data {i}: {error}")
            
            # Calculate comprehensive metrics
            completeness = self.validate_context_completeness(messages, rolls)
            freshness = self.validate_data_freshness(messages, rolls)
            quality = self.validate_overall_quality(messages, rolls)
            
            # Update validation results
            self.validation_results.update({
                'data_quality_score': quality['quality_score'],
                'context_completeness': completeness['completeness_score'],
                'data_freshness': freshness['freshness_score'],
                'message_count': len(messages),
                'roll_count': len(rolls),
                'scene_data_available': scene_data is not None
            })
            
            # Generate recommendations
            recommendations = []
            
            if completeness['completeness_score'] < 50:
                recommendations.append("Consider requesting more chat history for better context")
            
            if freshness['freshness_score'] < 60:
                recommendations.append("Data appears stale - consider refreshing with force flag")
            
            if quality['corruption_rate'] > 10:
                recommendations.append("High data corruption detected - check data sources")
            
            if len(messages) > 0 and len(rolls) == 0:
                recommendations.append("No roll data available - some game mechanics may be limited")
            
            self.validation_results['recommendations'] = recommendations
            
            # Log detailed results
            logger.info(f"=== AI PROMPT VALIDATION RESULTS ===")
            logger.info(f"Valid: {self.validation_results['is_valid']}")
            logger.info(f"Quality Score: {self.validation_results['data_quality_score']:.1f}%")
            logger.info(f"Completeness: {self.validation_results['context_completeness']:.1f}%")
            logger.info(f"Freshness: {self.validation_results['data_freshness']:.1f}%")
            logger.info(f"Messages: {len(messages)}, Rolls: {len(rolls)}")
            logger.info(f"Errors: {len(self.validation_results['errors'])}")
            logger.info(f"Warnings: {len(self.validation_results['warnings'])}")
            
            return self.validation_results
            
        except Exception as e:
            error_msg = f"Validation error: {str(e)}"
            self.validation_results['is_valid'] = False
            self.validation_results['errors'].append(error_msg)
            logger.error(f"AI Prompt validation failed: {error_msg}")
            return self.validation_results
    
    def should_block_prompt(self, min_quality_threshold: float = 70.0) -> bool:
        """Determine if prompt should be blocked based on validation results"""
        if not self.validation_results['is_valid']:
            return True  # Always block if validation failed
        
        if self.validation_results['data_quality_score'] < min_quality_threshold:
            return True
        
        # Block if no reasonable context
        if (self.validation_results.get('message_count', 0) + 
            self.validation_results.get('roll_count', 0)) < 2:
            return True
        
        return False
    
    def get_block_message(self) -> str:
        """Generate user-friendly block message"""
        if not self.validation_results['errors']:
            return None
        
        errors = self.validation_results['errors'][:3]  # Show first 3 errors
        warnings = self.validation_results['warnings'][:2]  # Show first 2 warnings
        
        message_parts = ["**AI Prompt Blocked - Data Quality Issues**\n"]
        
        if errors:
            message_parts.append("**Errors:**\n")
            for error in errors:
                message_parts.append(f"• {error}\n")
        
        if warnings:
            message_parts.append("**Warnings:**\n")
            for warning in warnings:
                message_parts.append(f"• {warning}\n")
        
        message_parts.append(f"\n**Quality Score:** {self.validation_results['data_quality_score']:.1f}%")
        message_parts.append(f"**Context:** {self.validation_results['message_count']} messages, {self.validation_results['roll_count']} rolls")
        
        if self.validation_results['recommendations']:
            message_parts.append("\n**Recommendations:**\n")
            for rec in self.validation_results['recommendations']:
                message_parts.append(f"• {rec}\n")
        
        return ''.join(message_parts)
    
    def _is_valid_dice_formula(self, formula: str) -> bool:
        """Basic dice formula validation"""
        if not formula:
            return False
        
        # Common dice patterns
        dice_patterns = [
            r'^\d+d$',           # 1d6
            r'^\d+d\+\d+$',       # 1d6+2
            r'^\d+d-\d+$',       # 1d6-2
            r'^\d+d\d+\+\d+$',    # 2d6+3
            r'^\d+kh\d+$',        # 4d6kh3
            r'^\d+kl\d+$',        # 4d6kl1
        ]
        
        formula = formula.strip().lower()
        return any(re.match(pattern, formula) for pattern in dice_patterns)
    
    def _is_corrupted_html(self, content: str) -> bool:
        """Check if content appears to be corrupted HTML"""
        if not content:
            return False
        
        # Check for excessive HTML fragments
        html_tags = content.count('<')
        if html_tags > 10:  # Too many HTML tags suggests corruption
            return True
        
        # Check for repeated class names (common in corrupted Foundry data)
        class_pattern = r'class="[^"]*"\s+class="'
        if len(re.findall(class_pattern, content)) > 3:
            return True
        
        # Check for excessive attributes
        attr_pattern = r'data-[^=]+="[^"]*"'
        if len(re.findall(attr_pattern, content)) > 15:
            return True
        
        return False
    
    def get_validation_summary(self) -> str:
        """Get concise validation summary for logging"""
        if not self.validation_results:
            return "No validation performed"
        
        status = "VALID" if self.validation_results['is_valid'] else "INVALID"
        return (f"{status} | Quality: {self.validation_results['data_quality_score']:.1f}% | "
                f"Context: {self.validation_results['context_completeness']:.1f}% | "
                f"Fresh: {self.validation_results['data_freshness']:.1f}% | "
                f"Messages: {self.validation_results.get('message_count', 0)} | "
                f"Rolls: {self.validation_results.get('roll_count', 0)}")


def validate_ai_prompt_context(messages: List[Dict[str, Any]], rolls: List[Dict[str, Any]], 
                           scene_data: Optional[Dict[str, Any]] = None, 
                           strict_mode: bool = False) -> Dict[str, Any]:
    """
    Convenience function for validating AI prompt context
    
    Args:
        messages: List of chat message dictionaries
        rolls: List of roll data dictionaries  
        scene_data: Optional scene/game state data
        strict_mode: Whether to apply strict validation rules
    
    Returns:
        Validation results dictionary with comprehensive quality metrics
    """
    validator = AIPromptValidator(strict_mode=strict_mode)
    return validator.validate_prompt_context(messages, rolls, scene_data)


if __name__ == "__main__":
    # Test the validator
    test_messages = [
        {"t": "cm", "c": "Hello world", "s": "Test", "ts": 1700000000000},
        {"t": "dr", "f": "1d20", "r": [15], "tt": 15, "s": "Test", "ts": 1700000001000}
    ]
    
    test_rolls = [
        {"t": "dr", "f": "2d6", "r": [3, 4], "tt": 7, "s": "Test", "ts": 1700000002000, "fl": "Attack"}
    ]
    
    result = validate_ai_prompt_context(test_messages, test_rolls)
    print(json.dumps(result, indent=2))
