"""
Log Utilities for The Gold Box
Provides intelligent JSON truncation for logging large objects

This utility helps keep logs readable by truncating large JSON objects
while preserving the actual data sent to AI systems.
"""

import json
import logging
from typing import Any

logger = logging.getLogger(__name__)

# Default threshold for truncation (in characters)
# Objects larger than this will be truncated in logs
DEFAULT_TRUNCATION_THRESHOLD = 1000  # 1KB


def truncate_for_log(
    data: Any,
    threshold: int = DEFAULT_TRUNCATION_THRESHOLD
) -> str:
    """
    Intelligently truncate data for logging purposes.
    
    This function detects large JSON objects and replaces them with a single-line summary
    showing the length of the object. The actual data is NOT truncated - only
    the log output is affected.
    
    Args:
        data: Any Python object (typically dict, list, or string)
        threshold: Character count threshold for truncation (default: 1000)
        
    Returns:
        str: Either the original data (if small) or a truncation summary
        
    Examples:
        >>> truncate_for_log({"small": "data"})
        '{"small": "data"}'
        
        >>> truncate_for_log(large_dict_with_5000_chars)
        '[Large JSON object truncated: 5243 characters]'
    """
    try:
        # Convert data to string for length check
        if isinstance(data, str):
            data_str = data
        else:
            data_str = json.dumps(data, ensure_ascii=False)
        
        data_length = len(data_str)
        
        # If data is small enough, return it as-is
        if data_length <= threshold:
            return data_str
        
        # Data is too large - return truncation summary
        return f"[Large JSON object truncated: {data_length} characters]"
        
    except Exception as e:
        # If we can't serialize or measure the data, return a fallback message
        logger.warning(f"Error truncating log data: {e}")
        return "[Error: Could not truncate log data]"


def truncate_dict_for_log(
    data: dict,
    threshold: int = DEFAULT_TRUNCATION_THRESHOLD,
    keys_to_show: list = None
) -> str:
    """
    Truncate dictionary for logging with optional key filtering.
    
    This is useful when you want to show certain keys but truncate the entire
    dictionary if it's too large.
    
    Args:
        data: Dictionary to truncate
        threshold: Character count threshold (default: 1000)
        keys_to_show: List of keys to always show (if present)
        
    Returns:
        str: Truncated or filtered dictionary string
        
    Examples:
        >>> truncate_dict_for_log({"name": "Bob", "large_data": [...]}, 
        ...                          keys_to_show=["name"])
        '{"name": "Bob"} [Large JSON object truncated: 5000 characters]'
    """
    try:
        if keys_to_show:
            # Extract specified keys
            filtered = {k: v for k, v in data.items() if k in keys_to_show}
            filtered_str = json.dumps(filtered, ensure_ascii=False)
            
            if len(filtered_str) > 0:
                # Show filtered keys plus truncation note
                full_str = json.dumps(data, ensure_ascii=False)
                return f"{filtered_str} [Large JSON object truncated: {len(full_str)} characters]"
        
        # Default to simple truncation
        return truncate_for_log(data, threshold)
        
    except Exception as e:
        logger.warning(f"Error truncating dictionary for log: {e}")
        return "[Error: Could not truncate log data]"


def set_truncation_threshold(threshold: int) -> None:
    """
    Set a custom truncation threshold for log_utils module.
    
    This allows configuration of the truncation size without modifying code.
    
    Args:
        threshold: New threshold in characters
    """
    global DEFAULT_TRUNCATION_THRESHOLD
    DEFAULT_TRUNCATION_THRESHOLD = threshold
    logger.info(f"Log truncation threshold set to {threshold} characters")


def get_truncation_threshold() -> int:
    """
    Get the current truncation threshold.
    
    Returns:
        int: Current threshold in characters
    """
    return DEFAULT_TRUNCATION_THRESHOLD
