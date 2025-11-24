# Patch 0.2.6 Plan - Complete Information Preservation

## Overview
Patch 0.2.6 focuses on fixing critical information loss in the processor module where rich Foundry VTT HTML content is being stripped when converted to compact JSON format for AI communication.

## Critical Issues Identified

### 1. Chat Content Loss (Highest Priority)
- **Problem**: All chat messages are being processed without their actual content (`"c"` field is empty)
- **Impact**: AI receives no conversational context, making responses ineffective
- **Root Cause**: Frontend preprocessing strips `.message-content` and only sends extracted content

### 2. Dice Roll Context Missing
- **Problem**: Dice roll flavor text (e.g., "Intelligence (Investigation) Check") is not being captured
- **Impact**: AI loses important context about what rolls represent
- **Root Cause**: Flavor text is in `.flavor-text` span in header, but processor only looks at dice content

### 3. Description Formatting Issues
- **Problem**: Text descriptions are concatenated without spaces (e.g., "castingBright Lightin a 20-foot radius")
- **Impact**: AI receives poorly formatted text that's harder to understand
- **Root Cause**: HTML-to-text conversion doesn't handle spacing properly

### 4. Input Validator Compatibility
- **Problem**: Input validator needs to be compatible with Foundry HTML while maintaining security
- **Impact**: Can't enable security validation without breaking functionality
- **Root Cause**: Current validator too restrictive for Foundry's HTML structure

## Solution Architecture

### Phase 1: Frontend Changes (Required)
**Goal**: Send complete HTML without preprocessing to maintain separation of concerns

#### 1.1 Modify Data Extraction
- **Current**: Extract only `.message-content` and create `FrontendMessage` objects
- **New**: Extract complete `<li class="chat-message">` elements
- **Files**: `scripts/gold-box.js`

#### 1.2 Remove Preprocessing Logic
- **Current**: Frontend creates `FrontendMessage(sender, content, timestamp)` objects
- **New**: Send raw HTML strings for backend processing
- **Benefits**: Cleaner separation, backend handles all parsing

#### 1.3 Maintain Message Metadata
- Preserve timestamps and any other metadata alongside HTML
- Update message sending format to include both

### Phase 2: Backend Processor Updates
**Goal**: Handle complete Foundry HTML structure and extract all available information

#### 2.1 Enhanced Chat Message Extraction
```python
def extract_complete_chat_data(self, soup: BeautifulSoup) -> Dict[str, Any]:
    """
    Extract data from complete chat-message li element
    Expected structure:
    <li class="chat-message">
        <header class="message-header">
            <h4 class="message-sender">Speaker Name</h4>
            <span class="flavor-text">Roll type/context</span>
        </header>
        <div class="message-content">Content</div>
    </li>
    """
```

#### 2.2 Enhanced Dice Roll Processing
```python
def extract_dice_roll_data(self, soup: BeautifulSoup) -> Dict[str, Any]:
    """
    Enhanced dice roll extraction with flavor text from header
    Extracts:
    - Flavor text from header (roll context)
    - Formula, results, total
    - Sender information
    """
```

#### 2.3 Fix Description Text Formatting
```python
# Proper spacing when extracting description text
desc_text = desc_elem.get_text(separator=' ', strip=True)
desc_text = re.sub(r'([a-z])([A-Z])', r'\1 \2', desc_text)  # Add space before capitals
desc_text = re.sub(r'\s+', ' ', desc_text)  # Normalize whitespace
```

#### 2.4 Update Compact JSON Schema
Add new field:
- `ft`: flavor_text (roll context like "Intelligence (Investigation) Check")

Updated schemas:
- Dice Roll: `{"t": "dr", "ft": "flavor_text", "f": "formula", "r": [results], "tt": total, "s": "speaker"}`
- Player Chat: `{"t": "pl", "s": "speaker", "c": "content"}` (no flavor text for plain chat)

### Phase 3: Input Validator Updates
**Goal**: Make "basic" level validation compatible with Foundry HTML while maintaining security

#### 3.1 Enhanced Foundry HTML Support
The current `_validate_foundry_html` method is well-designed but needs:

1. **Extended Allowed Tags**:
```python
FOUNDRY_ALLOWED_TAGS = {
    # Existing tags...
    'li', 'ol', 'dl', 'dt', 'dd',  # List structures
    'h1', 'h2', 'h3', 'h4', 'h5', 'h6',  # Headers
    'hr', 'br',  # Line breaks
    'i', 'b', 'u', 'strong', 'em',  # Text formatting
    'small', 'sub', 'sup',  # Additional formatting
    'blockquote', 'pre', 'code',  # Code blocks
    'table', 'thead', 'tbody', 'tr', 'th', 'td',  # Tables (if needed)
}
```

2. **Enhanced Data Attribute Support**:
```python
def _is_allowed_attr(self, attr_name: str) -> bool:
    attr_lower = attr_name.lower()
    
    # Allow all data-* attributes (Foundry uses many)
    if attr_lower.startswith('data-'):
        return True
    
    # Allow specific safe attributes
    allowed_attrs = {
        'class', 'id', 'style', 'alt', 'src', 'href', 'title', 
        'type', 'action', 'method', 'for', 'value', 'name',
        'disabled', 'checked', 'selected', 'readonly'
    }
    
    return attr_lower in allowed_attrs
```

3. **Improved Pattern Matching**:
```python
# More specific dangerous patterns to avoid false positives
DANGEROUS_PATTERNS = [
    r'<script[^>]*>.*?</script>',
    r'javascript:',
    r'vbscript:',
    r'on\w+\s*=',  # All event handlers
    r'<iframe[^>]*>',
    r'<object[^>]*>',
    r'<embed[^>]*>',
    # More specific SQL patterns (avoid "D&D" false positives)
    r'\b(UNION|SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC)\s+\w+',
    # More specific command patterns
    r'[;&|`$]\s*(rm|del|format|shutdown|reboot|cat|wget|curl)',
]
```

4. **Size Limit Adjustments**:
```python
SIZE_LIMITS = {
    'prompt': 10000,    # AI prompts can be longer
    'text': 50000,      # General text (Foundry HTML can be large)
    'html_content': 75000,  # Specifically for Foundry HTML messages
    'api_key': 500,     # API keys
    'config': 1000,      # Configuration values
}
```

#### 3.2 Validation Level Configuration
Update security_config.ini to enable basic validation:
```ini
[process_chat]
input_validation = basic
```

#### 3.3 Enhanced Structured Data Validation
Improve handling of message lists with HTML content:
```python
def _validate_structured_data(self, data, input_type, field_name, validation_level):
    if isinstance(data, list):
        sanitized_list = []
        for i, item in enumerate(data):
            # Check if this is a Foundry HTML message
            if isinstance(item, dict) and 'content' in item:
                validation_type = 'html_content'  # Use larger limit for HTML
            else:
                validation_type = 'prompt'
            
            is_valid, error, sanitized_value = self.validate_input(
                item, validation_type, f"{field_name}[{i}}", 
                validation_level=validation_level
            )
            if not is_valid:
                return False, error, None
            sanitized_list.append(sanitized_value)
        return True, "", sanitized_list
```

### Phase 4: Testing and Validation
**Goal**: Ensure complete information preservation and security

#### 4.1 Comprehensive Test Cases
Create test cases using real Foundry HTML output:
- Plain chat messages
- Dice rolls with flavor text
- Item cards with descriptions
- Spell cards with actions
- Mixed content messages

#### 4.2 Round-trip Testing
Test HTML → JSON → HTML conversion:
1. Verify all content is preserved
2. Check spacing and formatting
3. Validate flavor text extraction
4. Ensure security patterns work

#### 4.3 Security Validation
1. Test dangerous patterns are still blocked
2. Verify Foundry HTML passes validation
3. Test edge cases and malformed HTML

## Implementation Order

### Priority 1 (Critical - Backend)
1. Update `extract_dice_roll_data()` to handle flavor text from headers
2. Fix `extract_chat_card_data()` description spacing issues
3. Update compact JSON schema with `ft` field
4. Update system prompt with new schema

### Priority 2 (Required - Frontend)
1. Modify data extraction to send complete `<li class="chat-message">` HTML
2. Remove preprocessing logic that creates `FrontendMessage` objects
3. Update message format to include metadata

### Priority 3 (Security)
1. Extend input validator for Foundry HTML compatibility
2. Add new HTML tags and attributes to allow list
3. Update size limits and validation patterns
4. Enable basic validation in security config

### Priority 4 (Testing)
1. Create comprehensive test suite
2. Validate round-trip conversion
3. Test security validation with real Foundry HTML
4. Performance testing and optimization

## Expected Outcomes

### Information Preservation
- **Chat Content**: 100% of conversational context preserved
- **Dice Context**: All flavor text and roll types captured
- **Card Information**: Properly formatted descriptions and metadata
- **Overall**: >95% of critical information preserved in compact format

### Security
- **Basic Validation**: Compatible with Foundry HTML while blocking dangerous content
- **Performance**: Maintains current processing efficiency
- **Flexibility**: Supports Foundry's rich HTML structure

### Token Efficiency
- **Maintain**: Current 85-90% token reduction vs raw HTML
- **Improve**: Better structured data for AI understanding
- **Balance**: Optimal trade-off between information preservation and efficiency

## Files to Modify

### Backend Files
1. `backend/server/processor.py` - Core extraction and conversion logic
2. `backend/security/input_validator.py` - Foundry HTML compatibility
3. `backend/security_config.ini` - Enable basic validation
4. `backend/endpoints/process_chat.py` - Handle new message format

### Frontend Files
1. `scripts/gold-box.js` - Data extraction and message sending logic

### Documentation
1. `README.md` - Update with new capabilities
2. `CHANGELOG.md` - Document changes and improvements

## Success Criteria

1. **No Information Loss**: All chat content, roll context, and descriptions preserved
2. **Security Enabled**: Basic validation working with Foundry HTML
3. **Better AI Context**: Richer structured data improves AI responses
4. **Backward Compatibility**: Existing functionality remains intact
5. **Performance Maintained**: No significant performance degradation

This patch will fundamentally improve the quality of AI responses by ensuring complete conversational context and game information is preserved throughout the processing pipeline.
