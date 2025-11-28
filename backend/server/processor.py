#!/usr/bin/env python3
"""
The Gold Box v0.2.5 - Chat Context Processor
Bidirectional translation system for Foundry VTT chat messages

Converts Foundry HTML → Compact JSON → AI → Compact JSON → Foundry HTML

License: CC-BY-NC-SA 4.0
"""

import re
import json
import html as html_module
from typing import Dict, List, Any, Optional, Tuple
from bs4 import BeautifulSoup
import logging
 
# Configure logging
logger = logging.getLogger(__name__)

class ChatContextProcessor:
    """
    Core processor for bidirectional translation between Foundry HTML and Compact JSON
    """
    
    # Type codes for compact JSON format (system-agnostic Foundry VTT types)
    TYPE_CODES = {
        'dice-roll': 'dr',
        'chat-message': 'cm', 
        'chat-card': 'cd',  # Updated to "chat card" as requested
    }
    
    # Reverse mapping for JSON to HTML conversion
    REVERSE_TYPE_CODES = {v: k for k, v in TYPE_CODES.items()}
    
    # Priority-based classification patterns (system-agnostic Foundry VTT types)
    CLASSIFICATION_PATTERNS = [
        # Dice rolls (highest priority)
        ('dr', r'class=["\'].*dice-roll'),
        
        # Chat cards - more flexible patterns to match actual Foundry HTML
        ('cd', r'class=["\'].*chat-card|activation-card'),  # Generic chat card pattern
        
        # Message types
        ('cm', r'class=["\'].*chat-message(?![^"]*whisper)'),
    ]
    
    def __init__(self):
        """Initialize processor with compiled regex patterns"""
        self.compiled_patterns = [
            (type_code, re.compile(pattern, re.IGNORECASE))
            for type_code, pattern in self.CLASSIFICATION_PATTERNS
        ]
    
    def classify_message(self, html_content: str) -> str:
        """
        Classify message type using CSS class patterns with priority-based classification
        
        Args:
            html_content: HTML content to classify
            
        Returns:
            Type code string (e.g., 'dr', 'cm', 'cd')
        """
        for type_code, pattern in self.compiled_patterns:
            if pattern.search(html_content):
                logger.debug(f"Classified as {type_code}: {self.REVERSE_TYPE_CODES.get(type_code, 'unknown')}")
                return type_code
        
        # Default to chat message if no pattern matches
        logger.debug("No pattern matched, defaulting to chat message")
        return 'cm'
    
    def extract_dice_roll_data(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """
        Extract data from dice roll HTML with enhanced flavor text support
        
        Expected structure:
        <li class="chat-message">
            <header class="message-header">
                <h4 class="message-sender">Speaker Name</h4>
                <span class="flavor-text">Intelligence (Investigation) Check</span>
            </header>
            <div class="message-content">
                <div class="dice-roll">
                    <div class="dice-formula">1d20 + 3 + 2</div>
                    <div class="dice-tooltip">...</div>
                    <h4 class="dice-total">6</h4>
                </div>
            </div>
        </li>
        """
        data = {}
        
        # Extract flavor text from header (roll context like "Intelligence (Investigation) Check")
        flavor_elem = soup.select_one('.flavor-text')
        if flavor_elem:
            flavor_text = flavor_elem.get_text(strip=True)
            if flavor_text:
                data['ft'] = flavor_text
        
        # Extract formula
        formula_elem = soup.select_one('.dice-formula')
        if formula_elem:
            data['f'] = formula_elem.get_text(strip=True)
        
        # Extract total from dice-total h4
        total_elem = soup.select_one('.dice-total')
        if total_elem:
            total_text = total_elem.get_text(strip=True)
            # Extract first number from total text (may contain extra content like icons)
            total_match = re.search(r'(\d+)', total_text)
            if total_match:
                data['tt'] = int(total_match.group(1))
            else:
                data['tt'] = total_text
        
        # Extract individual dice results from tooltip - handle real Foundry structure
        tooltip_elem = soup.select_one('.dice-tooltip')
        if tooltip_elem:
            results = []
            
            # Try to find individual dice in different ways
            # Method 1: Look for .dice .roll elements
            dice_elements = tooltip_elem.select('.dice .roll')
            for dice_elem in dice_elements:
                dice_text = dice_elem.get_text(strip=True)
                # Extract numbers from dice text
                numbers = re.findall(r'\d+', dice_text)
                results.extend([int(n) for n in numbers])
            
            # Method 2: Look for .dice-rolls .roll elements (real Foundry structure)
            if not results:
                dice_rolls = tooltip_elem.select('.dice-rolls .roll')
                for roll_elem in dice_rolls:
                    roll_text = roll_elem.get_text(strip=True)
                    # Extract the actual number from the roll
                    number_match = re.search(r'\d+', roll_text)
                    if number_match:
                        results.append(int(number_match.group()))
            
            # Method 3: Look for .dice-rolls li elements (alternative structure)
            if not results:
                roll_lis = tooltip_elem.select('.dice-rolls li')
                for li_elem in roll_lis:
                    li_text = li_elem.get_text(strip=True)
                    # Extract the actual number from the li
                    number_match = re.search(r'\d+', li_text)
                    if number_match:
                        results.append(int(number_match.group()))
            
            if results:
                data['r'] = results
        
        # Extract sender from the chat message structure
        sender_elem = (soup.select_one('.message-sender .title') or
                       soup.select_one('.name-stacked .title') or
                       soup.select_one('.message-sender') or
                       soup.select_one('.sender'))
        
        if sender_elem:
            data['s'] = sender_elem.get_text(strip=True)
        
        return data
    
    def extract_chat_message_data(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """
        Extract data from complete chat-message li element
        Expected structure:
        <li class="chat-message">
            <header class="message-header">
                <h4 class="message-sender">Speaker Name</h4>
            </header>
            <div class="message-content">Content</div>
        </li>
        """
        data = {}
        
        # Extract sender from header with multiple fallback selectors
        sender_elem = (soup.select_one('.message-sender .title') or
                       soup.select_one('.name-stacked .title') or
                       soup.select_one('.message-sender') or
                       soup.select_one('.sender') or
                       soup.select_one('header h4'))
        
        if sender_elem:
            data['s'] = sender_elem.get_text(strip=True)
        
        # Extract content with multiple fallback selectors
        content_elem = (soup.select_one('.message-content') or
                       soup.select_one('.content') or
                       soup.select_one('div.message-text') or
                       soup)  # Fallback to full text
        
        if content_elem:
            # Get all text content, preserving structure
            content_text = content_elem.get_text(separator=' ', strip=True)
            # Remove duplicate chat card content that might be included
            # Look for the main paragraph content, not card descriptions
            if content_elem != soup:  # Only if we found a specific content element
                paragraphs = content_elem.find_all('p')
                if paragraphs:
                    # Use the first paragraph as the main content, exclude card content
                    main_content = paragraphs[0].get_text(separator=' ', strip=True)
                    if main_content and main_content.strip():
                        data['c'] = main_content.strip()
                    else:
                        data['c'] = content_text.strip()
                else:
                    data['c'] = content_text.strip()
            else:
                data['c'] = content_text.strip()
        
        return data
    
    def extract_chat_card_data(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """
        Extract data from chat card (items, spells, etc.)
        
        Expected structure:
        <li class="chat-message">
            <header class="message-header">
                <h4 class="message-sender">Speaker Name</h4>
            </header>
            <div class="message-content">
                <div class="chat-card activation-card">
                    <header class="card-header">
                        <img class="gold-icon" src="...">
                        <div class="name-stacked border">
                            <span class="title">Dagger</span>
                            <span class="subtitle">Simple Melee</span>
                        </div>
                    </header>
                    <section class="details">
                        <div class="wrapper">
                            <p>Attack description...</p>
                        </div>
                    </section>
                </div>
            </div>
        </li>
        """
        data = {}
        
        # Find chat card element within message structure
        card_element = soup.select_one('.chat-card') or soup.select_one('.activation-card')
        if not card_element:
            # Fallback: look for any div with activation-card class
            card_element = soup.find('div', class_=lambda x: x and 'activation-card' in str(x))
        
        # Extract speaker from message header (not card)
        speaker_elem = (soup.select_one('.message-sender .title') or
                       soup.select_one('.name-stacked .title') or
                       soup.select_one('.message-sender'))
        
        if speaker_elem:
            data['s'] = speaker_elem.get_text(strip=True)
        
        # Extract name from the card header, not message header
        # Look for the title within the card structure
        if card_element:
            name_elem = (card_element.select_one('.card-header .title') or
                        card_element.select_one('.name-stacked .title') or
                        card_element.select_one('.item-name') or
                        card_element.select_one('h3'))
        else:
            # Fallback to searching in the full soup but be more specific
            name_elem = (soup.select_one('.chat-card .card-header .title') or
                        soup.select_one('.activation-card .card-header .title') or
                        soup.select_one('.chat-card .name-stacked .title'))
        
        if name_elem:
            data['n'] = name_elem.get_text(strip=True)
        
        # Extract description - look for the actual description content, exclude roll links
        desc_elem = (soup.select_one('.details .wrapper p') or 
                    soup.select_one('.card-content p') or 
                    soup.select_one('.item-description'))
        
        if desc_elem:
            # Get text content with proper spacing
            desc_text = desc_elem.get_text(separator=' ', strip=True)
            # Fix spacing between words (especially around HTML links)
            desc_text = re.sub(r'([a-z])([A-Z])', r'\1 \2', desc_text)  # Add space before capitals
            desc_text = re.sub(r'([a-z])([A-Z])', r'\1 \2', desc_text)  # Add space before capitals (backup)
            desc_text = re.sub(r'\s+', ' ', desc_text)  # Normalize whitespace
            # Remove roll patterns while preserving spacing
            desc_text = re.sub(r'\s*\d+d\d*(?:\s*[-+]\s*\d+)?\s*', ' ', desc_text)  # 1d20+4, 1d4 + 2, etc.
            desc_text = re.sub(r'\s*\+[+\d]*\s*', ' ', desc_text)  # Remove stray +4, +2 patterns
            desc_text = re.sub(r'Roll:\s*,', 'Roll:', desc_text)  # Fix "Roll:" followed by comma
            desc_text = re.sub(r'\.\s*\(', '. (', desc_text)  # Fix period spacing before parenthesis
            desc_text = desc_text.strip()
            # Unescape HTML entities for better readability
            import html as html_module
            desc_text = html_module.unescape(desc_text)
            data['d'] = desc_text
        
        # Check if this is a mixed message (chat message + card) and extract main content
        # This handles cases where a player says something AND includes a card
        message_content_elem = soup.select_one('.message-content p')
        if message_content_elem:
            content_text = message_content_elem.get_text(separator=' ', strip=True)
            # Check if this is the main message content (not card description)
            # by ensuring it's not the same as the card description
            if 'd' in data and content_text != data['d']:
                # Also check if it contains card description by looking for key phrases
                if not any(phrase in content_text.lower() for phrase in ['description:', 'test item', 'test type']):
                    data['c'] = content_text.strip()
        
        # Extract actions from buttons
        button_elems = soup.select('.card-buttons button')
        actions = []
        for button in button_elems:
            action = button.get('data-action') or button.get_text(strip=True)
            if action:
                actions.append(action)
        
        if actions:
            data['a'] = actions  # No truncation - preserve all actions
        
        return data
    
    def html_to_compact_json(self, html_content: str) -> Dict[str, Any]:
        """
        Convert Foundry HTML to compact JSON format
        
        Args:
            html_content: HTML content from Foundry chat message
            
        Returns:
            Compact JSON dictionary with type code and extracted data
        """
        try:
            # Parse HTML
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Classify message type
            message_type = self.classify_message(html_content)
            
            # Extract data based on message type
            if message_type == 'dr':
                data = self.extract_dice_roll_data(soup)
            elif message_type == 'cm':
                data = self.extract_chat_message_data(soup)
            elif message_type == 'cd':
                data = self.extract_chat_card_data(soup)
            else:
                # Fallback to chat message extraction
                data = self.extract_chat_message_data(soup)
            
            # Add type code
            result = {'t': message_type}
            result.update(data)
            
            # Security sanitization
            result = self._sanitize_compact_json(result)
            
            logger.debug(f"HTML to JSON: {message_type} → {result}")
            return result
            
        except Exception as e:
            logger.error(f"Error converting HTML to compact JSON: {e}")
            # Return safe fallback
            return {
                't': 'cm',
                's': 'Unknown',
                'c': 'Error processing message'
            }
    
    def compact_json_to_html(self, compact_data: Dict[str, Any]) -> str:
        """
        Convert compact JSON back to Foundry HTML format
        
        Args:
            compact_data: Compact JSON dictionary
            
        Returns:
            Foundry HTML string
        """
        try:
            # Get message type
            message_type = compact_data.get('t', 'cm')
            full_type_name = self.REVERSE_TYPE_CODES.get(message_type, 'chat-message')
            
            # Generate HTML based on type
            if message_type == 'dr':
                html = self._generate_dice_roll_html(compact_data)
            elif message_type == 'cm':
                html = self._generate_chat_message_html(compact_data)
            elif message_type == 'cd':
                html = self._generate_chat_card_html(compact_data)
            else:
                # Fallback to chat message
                html = self._generate_chat_message_html(compact_data)
            
            logger.debug(f"JSON to HTML: {message_type} → HTML generated")
            return html
            
        except Exception as e:
            logger.error(f"Error converting compact JSON to HTML: {e}")
            # Return safe fallback
            return f'''<div class="chat-message">
    <div class="message-content">
        <p>Error generating response: {html_module.escape(str(e))}</p>
    </div>
</div>'''
    
    def _sanitize_compact_json(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sanitize compact JSON data for security (translation preserves full data)
        
        Args:
            data: Raw compact JSON data
            
        Returns:
            Sanitized data with readable text for AI
        """
        sanitized = {}
        
        for key, value in data.items():
            if isinstance(value, str):
                # Remove null bytes first
                clean_value = value.replace('\x00', '')
                # Unescape HTML entities for AI readability
                clean_value = html_module.unescape(clean_value)
                # Remove dangerous HTML tags but preserve readable text
                # This is safer than full HTML escaping for AI context
                dangerous_patterns = [
                    r'<script[^>]*>.*?</script>',  # Remove script tags
                    r'<iframe[^>]*>.*?</iframe>',  # Remove iframes
                    r'<object[^>]*>.*?</object>',  # Remove objects
                    r'<embed[^>]*>.*?</embed>',    # Remove embeds
                    r'<form[^>]*>.*?</form>',      # Remove forms
                    r'javascript:',                   # Remove javascript URLs
                    r'vbscript:',                    # Remove vbscript URLs
                    r'on\w+\s*=',                  # Remove event handlers
                ]
                for pattern in dangerous_patterns:
                    clean_value = re.sub(pattern, '', clean_value, flags=re.IGNORECASE | re.DOTALL)
                
                # Clean up any remaining HTML tag fragments that might result from pattern removal
                clean_value = re.sub(r'<[^>]*>', '', clean_value)  # Remove any remaining HTML tags
                clean_value = re.sub(r'>', '', clean_value)     # Remove stray closing brackets
                
                # Final cleanup: normalize whitespace and ensure readability
                clean_value = re.sub(r'\s+', ' ', clean_value).strip()
                
                sanitized[key] = clean_value
                # Note: No length truncation for translation - preserve full data
            elif isinstance(value, (int, float, bool)):
                sanitized[key] = value
            elif isinstance(value, list):
                # Sanitize list items without truncation
                sanitized[key] = []
                for item in value:
                    if isinstance(item, str):
                        clean_item = item.replace('\x00', '')
                        clean_item = html_module.unescape(clean_item)
                        # Apply same dangerous pattern removal
                        for pattern in dangerous_patterns:
                            clean_item = re.sub(pattern, '', clean_item, flags=re.IGNORECASE | re.DOTALL)
                        # Clean up HTML tag fragments
                        clean_item = re.sub(r'<[^>]*>', '', clean_item)
                        clean_item = re.sub(r'>', '', clean_item)
                        clean_item = re.sub(r'\s+', ' ', clean_item).strip()
                        sanitized[key].append(clean_item)
                    else:
                        sanitized[key].append(item)
            # Skip other types
        
        return sanitized
    
    def _generate_dice_roll_html(self, data: Dict[str, Any]) -> str:
        """Generate HTML for dice roll message"""
        formula = data.get('f', '1d20')
        total = data.get('tt', 0)
        results = data.get('r', [])
        
        # Build tooltip content
        tooltip_content = ''
        if results:
            dice_str = '+'.join(str(r) for r in results)
            tooltip_content = f'<div class="dice-tooltip"><section class="tooltip-part"><div class="dice">{dice_str}</div></section></div>'
        
        return f'''<div class="dice-roll">
    <div class="roll-formula">{html_module.escape(str(formula))}</div>
    {tooltip_content}
    <h4 class="roll-total">{total}</h4>
</div>'''
    
    def _generate_chat_message_html(self, data: Dict[str, Any]) -> str:
        """Generate HTML for chat message"""
        speaker = data.get('s', 'Unknown')
        content = data.get('c', '')
        
        return f'''<div class="chat-message">
    <header class="message-header">
        <h4 class="message-speaker">{html_module.escape(str(speaker))}</h4>
    </header>
    <div class="message-content">
        <p>{html_module.escape(str(content))}</p>
    </div>
</div>'''
    
    def _generate_chat_card_html(self, data: Dict[str, Any]) -> str:
        """Generate HTML for chat card"""
        name = data.get('n', 'Unknown')
        description = data.get('d', '')
        actions = data.get('a', [])
        
        buttons_html = ''
        if actions:
            buttons_html = '<div class="card-buttons">'
            for action in actions:  # No truncation - preserve all actions
                buttons_html += f'<button data-action="{html_module.escape(str(action))}">{html_module.escape(str(action))}</button>'
            buttons_html += '</div>'
        
        return f'''<div class="chat-card">
    <header class="card-header">
        <h3 class="item-name">{html_module.escape(str(name))}</h3>
    </header>
    <div class="card-content">
        <p>{html_module.escape(str(description))}</p>
    </div>
    {buttons_html}
</div>'''
    
    def process_message_list(self, messages: List[Any]) -> List[Dict[str, Any]]:
        """
        Process a list of messages to compact JSON
        
        Args:
            messages: List of HTML message strings or frontend message objects
            
        Returns:
            List of compact JSON message dictionaries
        """
        processed_messages = []
        
        for message in messages:
            try:
                # Extract HTML content based on message type
                if isinstance(message, str):
                    # Plain HTML string
                    html_content = message
                elif hasattr(message, 'content'):
                    # Frontend message object
                    html_content = message.content
                else:
                    # Unknown type, try to convert to string
                    html_content = str(message)
                
                compact_message = self.html_to_compact_json(html_content)
                
                # If we have sender info from frontend message, preserve it
                if hasattr(message, 'sender') and message.sender:
                    compact_message['s'] = message.sender
                
                processed_messages.append(compact_message)
                
            except Exception as e:
                logger.error(f"Error processing message: {e}")
                # Add safe fallback
                fallback_message = {
                    't': 'cm',
                    's': 'Unknown',
                    'c': 'Error processing message'
                }
                
                # Try to preserve sender from frontend message
                if hasattr(message, 'sender') and message.sender:
                    fallback_message['s'] = message.sender
                
                processed_messages.append(fallback_message)
        
        return processed_messages
    
    def generate_system_prompt(self, ai_role: str = "player") -> str:
        """
        Generate system prompt with type codes and schema definitions based on AI role
        
        Args:
            ai_role: The current AI role setting ("player", "gm assistant", or "gamemaster")
            
        Returns:
            System prompt string for AI API
        """
        type_codes_str = ', '.join([f"'{code}': '{name}'" for code, name in self.REVERSE_TYPE_CODES.items()])
        
        # Role-based prompt variations
        if ai_role == "player":
            base_prompt = """You are a player character in this tabletop RPG session. Respond naturally to the conversation as a player would, participating in the story and engaging with other characters. When you need to generate game mechanics like dice rolls or actions, use the compact JSON format specified below."""
        elif ai_role == "gm assistant":
            base_prompt = """You are a GM's assistant in this tabletop RPG session. Your role is to respond to specific commands, queries, or requests from the most recent chat message. Provide helpful guidance, rules clarifications, or execute specific actions as requested. Focus on being responsive to direct commands rather than driving the narrative forward. When you need to generate game mechanics, use the compact JSON format specified below."""
        elif ai_role == "gamemaster":
            base_prompt = """You are the Gamemaster for this tabletop RPG session. Your role is to drive the narrative continuously until it becomes the player's turn again. Control the story, describe scenes, manage NPCs, create challenges, and keep the game moving forward. Generate multiple actions, descriptions, and events as needed to advance the story before handing control back to players. During combat, roll all dice for non-player actions.  When you need to generate game mechanics, use the compact JSON format specified below."""
        else:
            # Default fallback
            base_prompt = """You are an AI assistant for tabletop RPG games. Respond naturally to the conversation as an AI assistant would. When you need to generate game mechanics, use the compact JSON format specified below."""
        
        system_prompt = f"""{base_prompt}

Chat messages use a compact JSON format with type codes and field abbreviations:

Type Codes (Generic Foundry VTT):
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

When generating game mechanics, use the compact JSON format above with field abbreviations. Be system-agnostic and work with any tabletop RPG system."""
        
        return system_prompt

# Test function
def test_processor():
    """Test the processor with sample HTML messages"""
    processor = ChatContextProcessor()
    
    # Test cases
    test_cases = [
        # Dice roll
        '''<div class="dice-roll">
            <div class="roll-formula">3d6</div>
            <div class="roll-tooltip"><div class="dice">2+4+2</div></div>
            <h4 class="roll-total">8</h4>
        </div>''',
        
        # Chat message
        '''<div class="chat-message">
            <header class="message-header">
                <h4 class="message-sender">Fighter</h4>
            </header>
            <div class="message-content">
                <p>I attack the goblin!</p>
            </div>
        </div>''',
        
        # Chat card
        '''<div class="chat-card">
            <header class="card-header">
                <h3 class="item-name">Dagger</h3>
            </header>
            <div class="card-content">
                <p>A simple melee weapon with a sharp blade.</p>
            </div>
            <div class="card-buttons">
                <button data-action="attack">Attack</button>
                <button data-action="throw">Throw</button>
            </div>
        </div>''',
    ]
    
    print("=" * 60)
    print("Chat Context Processor Test")
    print("=" * 60)
    
    for i, test_html in enumerate(test_cases, 1):
        print(f"\nTest Case {i}:")
        print("Input HTML:")
        print(test_html[:200] + "..." if len(test_html) > 200 else test_html)
        
        # Convert to compact JSON
        compact = processor.html_to_compact_json(test_html)
        print("\nCompact JSON:")
        print(json.dumps(compact, indent=2))
        
        # Convert back to HTML
        regenerated_html = processor.compact_json_to_html(compact)
        print("\nRegenerated HTML:")
        print(regenerated_html[:200] + "..." if len(regenerated_html) > 200 else regenerated_html)
        
        print("-" * 40)
    
    # Test system prompt generation with different roles
    print("\nSystem Prompt (Player Role):")
    print(processor.generate_system_prompt("player"))
    print("\nSystem Prompt (GM Assistant Role):")
    print(processor.generate_system_prompt("gm assistant"))
    print("\nSystem Prompt (Gamemaster Role):")
    print(processor.generate_system_prompt("gamemaster"))
    print("\nSystem Prompt (Default):")
    print(processor.generate_system_prompt("unknown"))
    
    print("=" * 60)

if __name__ == "__main__":
    test_processor()
