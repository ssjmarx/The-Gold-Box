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
    
    # Type codes for compact JSON format
    TYPE_CODES = {
        'dice-roll': 'dr',
        'player-chat': 'pl', 
        'attack-roll': 'ar',
        'saving-throw': 'sv',
        'gm-message': 'gm',
        'whisper': 'wp',
        'chat-card': 'cc',
        'condition-card': 'cd',
        'table-result': 'tr'
    }
    
    # Reverse mapping for JSON to HTML conversion
    REVERSE_TYPE_CODES = {v: k for k, v in TYPE_CODES.items()}
    
    # Priority-based classification patterns (highest priority first)
    CLASSIFICATION_PATTERNS = [
        # Dice rolls (highest priority)
        ('dr', r'class=["\'].*dice-roll'),
        ('ar', r'class=["\'].*attack-card'),  # More flexible - match attack-card
        ('sv', r'class=["\'].*save-card'),   # More flexible - match save-card
        
        # Chat cards - more flexible patterns to match actual Foundry HTML
        ('cc', r'class=["\'].*activation-card'),  # Specific activation-card pattern (higher priority)
        ('cc', r'class=["\'].*chat-card'),
        ('cd', r'class=["\'].*condition-card'),
        ('tr', r'class=["\'].*roll-table-result|table-result'),
        
        # Message types
        ('wp', r'class=["\'].*whisper'),
        ('gm', r'class=["\'].*gm-message'),
        ('pl', r'class=["\'].*chat-message(?![^"]*whisper)'),
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
            Type code string (e.g., 'dr', 'pl', 'ar')
        """
        for type_code, pattern in self.compiled_patterns:
            if pattern.search(html_content):
                logger.debug(f"Classified as {type_code}: {self.REVERSE_TYPE_CODES.get(type_code, 'unknown')}")
                return type_code
        
        # Default to player chat if no pattern matches
        logger.debug("No pattern matched, defaulting to player chat")
        return 'pl'
    
    def extract_dice_roll_data(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """
        Extract data from dice roll HTML
        
        Expected structure:
        <div class="dice-roll">
            <div class="dice-formula">1d20 + 3 + 2</div>
            <div class="dice-tooltip">...</div>
            <h4 class="dice-total">6</h4>
        </div>
        """
        data = {}
        
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
        
        return data
    
    def extract_player_chat_data(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """
        Extract data from player chat message
        
        Expected structure:
        <div class="chat-message">
            <header class="message-header">
                <h4 class="message-speaker">Character Name</h4>
            </header>
            <div class="message-content">Message content</div>
        </div>
        """
        data = {}
        
        # Extract speaker name
        speaker_elem = soup.select_one('.message-speaker')
        if speaker_elem:
            data['s'] = speaker_elem.get_text(strip=True)
        
        # Extract content
        content_elem = soup.select_one('.message-content')
        if content_elem:
            # Clean HTML and get text content
            content_text = content_elem.get_text(strip=True)
            data['c'] = content_text
        
        return data
    
    def extract_attack_roll_data(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """
        Extract data from attack roll HTML
        
        Expected structure:
        <div class="chat-card attack-card">
            <div class="attack-roll">...</div>
            <div class="damage-roll">...</div>
        </div>
        """
        data = {}
        
        # Extract speaker
        speaker_elem = soup.select_one('.message-speaker, .actor-name')
        if speaker_elem:
            data['s'] = speaker_elem.get_text(strip=True)
        
        # Extract attack roll data
        attack_elem = soup.select_one('.attack-roll .roll-formula')
        if attack_elem:
            data['af'] = attack_elem.get_text(strip=True)
        
        attack_total_elem = soup.select_one('.attack-roll .roll-total')
        if attack_total_elem:
            attack_text = attack_total_elem.get_text(strip=True)
            try:
                data['at'] = int(re.search(r'\d+', attack_text).group())
            except (AttributeError, ValueError):
                data['at'] = attack_text
        
        # Extract damage roll data
        damage_elem = soup.select_one('.damage-roll .roll-formula')
        if damage_elem:
            data['df'] = damage_elem.get_text(strip=True)
        
        damage_total_elem = soup.select_one('.damage-roll .roll-total')
        if damage_total_elem:
            damage_text = damage_total_elem.get_text(strip=True)
            try:
                data['dt'] = int(re.search(r'\d+', damage_text).group())
            except (AttributeError, ValueError):
                data['dt'] = damage_text
        
        return data
    
    def extract_saving_throw_data(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """
        Extract data from saving throw HTML
        
        Expected structure:
        <div class="chat-card save-card">
            <h3 class="save-title">Dexterity Saving Throw</h3>
            <div class="dice-roll">...</div>
        </div>
        """
        data = {}
        
        # Extract speaker
        speaker_elem = soup.select_one('.message-speaker, .actor-name')
        if speaker_elem:
            data['s'] = speaker_elem.get_text(strip=True)
        
        # Extract save type
        save_title_elem = soup.select_one('.save-title')
        if save_title_elem:
            title_text = save_title_elem.get_text(strip=True)
            # Extract ability score from title
            ability_match = re.search(r'(Strength|Dexterity|Constitution|Intelligence|Wisdom|Charisma)', title_text)
            if ability_match:
                data['st'] = ability_match.group(1)
        
        # Extract roll formula
        formula_elem = soup.select_one('.roll-formula')
        if formula_elem:
            data['f'] = formula_elem.get_text(strip=True)
        
        # Extract roll total
        total_elem = soup.select_one('.roll-total')
        if total_elem:
            total_text = total_elem.get_text(strip=True)
            try:
                data['tt'] = int(re.search(r'\d+', total_text).group())
            except (AttributeError, ValueError):
                data['tt'] = total_text
        
        # Extract DC and success/failure
        total_class = total_elem.get('class', '') if total_elem else ''
        if 'success' in total_class:
            data['succ'] = True
        elif 'failure' in total_class:
            data['succ'] = False
        
        # Look for DC in text
        dc_match = re.search(r'vs\s+DC\s+(\d+)', soup.get_text())
        if dc_match:
            data['dc'] = int(dc_match.group(1))
        
        return data
    
    def extract_whisper_data(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """
        Extract data from whisper message
        
        Expected structure:
        <div class="chat-message whisper" data-whisper-to="user1,user2">
            <h4 class="message-speaker">Speaker → Target1, Target2</h4>
            <div class="message-content">Message content</div>
        </div>
        """
        data = {}
        
        # Extract speaker and targets
        speaker_elem = soup.select_one('.message-speaker')
        if speaker_elem:
            speaker_text = speaker_elem.get_text(strip=True)
            # Parse "Speaker → Target1, Target2"
            if '→' in speaker_text:
                parts = speaker_text.split('→', 1)
                data['s'] = parts[0].strip()
                targets = [t.strip() for t in parts[1].split(',')]
                data['tg'] = targets
            else:
                data['s'] = speaker_text
        
        # Extract content
        content_elem = soup.select_one('.message-content')
        if content_elem:
            data['c'] = content_elem.get_text(strip=True)
        
        return data
    
    def extract_gm_message_data(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """
        Extract data from GM message
        
        Expected structure:
        <div class="chat-message gm-message">
            <div class="message-content">GM message content</div>
        </div>
        """
        data = {}
        
        # Extract content
        content_elem = soup.select_one('.message-content')
        if content_elem:
            data['c'] = content_elem.get_text(strip=True)
        
        return data
    
    def extract_chat_card_data(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """
        Extract data from chat card (items, spells, etc.)
        
        Expected structure:
        <div class="chat-card activation-card">
            <header class="card-header">
                <img class="gold-icon" src="...">
                <div class="name-stacked">
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
        """
        data = {}
        
        # Find the main chat card element (might be soup itself or a child)
        card_element = soup
        if soup.name == '[document]':  # If soup is the whole document
            card_element = soup.find('div') or soup.find('section') or soup
        
        # Determine card type from classes
        classes = card_element.get('class', [])
        if 'spell-card' in classes:
            data['ct'] = 'spell'
        elif 'activation-card' in classes:
            data['ct'] = 'item'
        else:
            data['ct'] = 'generic'
        
        # Extract name - try multiple selectors for actual Foundry structure
        name_elem = (soup.select_one('.title') or 
                     soup.select_one('.item-name') or 
                     soup.select_one('.card-header h3') or 
                     soup.select_one('h3'))
        
        if name_elem:
            data['n'] = name_elem.get_text(strip=True)
        
        # Extract description - look for the actual description content, exclude roll links
        desc_elem = (soup.select_one('.details .wrapper p') or 
                    soup.select_one('.card-content p') or 
                    soup.select_one('.item-description'))
        
        if desc_elem:
            # Get text content and clean up roll links
            desc_text = desc_elem.get_text(strip=True)
            # Remove more comprehensive roll patterns from description
            desc_text = re.sub(r'\d+d\d*(?:\s*[-+]\s*\d+)?', '', desc_text)  # 1d20+4, 1d4 + 2, etc.
            desc_text = re.sub(r'\+[+\d]*', '', desc_text)  # Remove stray +4, +2 patterns
            # Clean up extra spaces and punctuation
            desc_text = re.sub(r'\s+', ' ', desc_text)
            desc_text = re.sub(r'Roll:\s*,', 'Roll:', desc_text)  # Fix "Roll:" followed by comma
            desc_text = re.sub(r'\.\s*\(', '. (', desc_text)  # Fix period spacing before parenthesis
            desc_text = desc_text.strip()
            data['d'] = desc_text
        
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
    
    def extract_condition_card_data(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """
        Extract data from condition card
        
        Expected structure:
        <div class="chat-card condition-card">
            <h3 class="condition-name">Prone</h3>
            <div class="condition-description">Description...</div>
        </div>
        """
        data = {}
        
        # Extract condition name
        name_elem = soup.select_one('.condition-name, .card-header h3, h3')
        if name_elem:
            data['cn'] = name_elem.get_text(strip=True)
        
        # Extract description
        desc_elem = soup.select_one('.condition-description, .card-content')
        if desc_elem:
            desc_text = desc_elem.get_text(strip=True)
            data['d'] = desc_text
        
        return data
    
    def extract_table_result_data(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """
        Extract data from table result
        
        Expected structure:
        <div class="roll-table-result">
            <div class="table-result">
                <div class="table-roll">42</div>
                <div class="table-text">You find a treasure chest</div>
            </div>
        </div>
        """
        data = {}
        
        # Extract roll result
        roll_elem = soup.select_one('.table-roll')
        if roll_elem:
            roll_text = roll_elem.get_text(strip=True)
            try:
                data['r'] = int(re.search(r'\d+', roll_text).group())
            except (AttributeError, ValueError):
                data['r'] = roll_text
        
        # Extract table text
        text_elem = soup.select_one('.table-text')
        if text_elem:
            data['res'] = text_elem.get_text(strip=True)
        
        # Extract table name if available
        # Look for parent elements or headers that might contain table name
        table_name_elem = soup.select_one('[data-table], .table-name')
        if table_name_elem:
            data['tn'] = table_name_elem.get_text(strip=True)
        
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
            elif message_type == 'pl':
                data = self.extract_player_chat_data(soup)
            elif message_type == 'ar':
                data = self.extract_attack_roll_data(soup)
            elif message_type == 'sv':
                data = self.extract_saving_throw_data(soup)
            elif message_type == 'wp':
                data = self.extract_whisper_data(soup)
            elif message_type == 'gm':
                data = self.extract_gm_message_data(soup)
            elif message_type == 'cc':
                data = self.extract_chat_card_data(soup)
            elif message_type == 'cd':
                data = self.extract_condition_card_data(soup)
            elif message_type == 'tr':
                data = self.extract_table_result_data(soup)
            else:
                # Fallback to player chat extraction
                data = self.extract_player_chat_data(soup)
            
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
                't': 'pl',
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
            message_type = compact_data.get('t', 'pl')
            full_type_name = self.REVERSE_TYPE_CODES.get(message_type, 'player-chat')
            
            # Generate HTML based on type
            if message_type == 'dr':
                html = self._generate_dice_roll_html(compact_data)
            elif message_type == 'pl':
                html = self._generate_player_chat_html(compact_data)
            elif message_type == 'ar':
                html = self._generate_attack_roll_html(compact_data)
            elif message_type == 'sv':
                html = self._generate_saving_throw_html(compact_data)
            elif message_type == 'wp':
                html = self._generate_whisper_html(compact_data)
            elif message_type == 'gm':
                html = self._generate_gm_message_html(compact_data)
            elif message_type == 'cc':
                html = self._generate_chat_card_html(compact_data)
            elif message_type == 'cd':
                html = self._generate_condition_card_html(compact_data)
            elif message_type == 'tr':
                html = self._generate_table_result_html(compact_data)
            else:
                # Fallback to player chat
                html = self._generate_player_chat_html(compact_data)
            
            logger.debug(f"JSON to HTML: {message_type} → HTML generated")
            return html
            
        except Exception as e:
            logger.error(f"Error converting compact JSON to HTML: {e}")
            # Return safe fallback
            return f'''<div class="chat-message player-chat">
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
            Sanitized data
        """
        sanitized = {}
        
        for key, value in data.items():
            if isinstance(value, str):
                # Escape HTML characters
                sanitized[key] = html_module.escape(value)
                # Remove null bytes
                sanitized[key] = sanitized[key].replace('\x00', '')
                # Note: No length truncation for translation - preserve full data
            elif isinstance(value, (int, float, bool)):
                sanitized[key] = value
            elif isinstance(value, list):
                # Sanitize list items without truncation
                sanitized[key] = [
                    html_module.escape(str(item)) if isinstance(item, str) else item
                    for item in value
                ]
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
    
    def _generate_player_chat_html(self, data: Dict[str, Any]) -> str:
        """Generate HTML for player chat message"""
        speaker = data.get('s', 'Unknown')
        content = data.get('c', '')
        
        return f'''<div class="chat-message player-chat">
    <header class="message-header">
        <h4 class="message-speaker">{html_module.escape(str(speaker))}</h4>
    </header>
    <div class="message-content">
        <p>{html_module.escape(str(content))}</p>
    </div>
</div>'''
    
    def _generate_attack_roll_html(self, data: Dict[str, Any]) -> str:
        """Generate HTML for attack roll message"""
        speaker = data.get('s', 'Unknown')
        attack_formula = data.get('af', '1d20')
        attack_total = data.get('at', 0)
        damage_formula = data.get('df', '')
        damage_total = data.get('dt', 0)
        
        html = f'''<div class="dnd5e chat-card attack-card">
    <header class="card-header">
        <h3 class="item-name">Attack</h3>
    </header>
    <div class="card-content">'''
        
        if attack_formula:
            html += f'''
        <div class="attack-roll">
            <div class="roll-formula">{html_module.escape(str(attack_formula))}</div>
            <h4 class="roll-total">{attack_total}</h4>
        </div>'''
        
        if damage_formula:
            html += f'''
        <div class="damage-roll">
            <div class="roll-formula">{html_module.escape(str(damage_formula))}</div>
            <h4 class="roll-total">{damage_total}</h4>
        </div>'''
        
        html += '''
    </div>
</div>'''
        
        return html
    
    def _generate_saving_throw_html(self, data: Dict[str, Any]) -> str:
        """Generate HTML for saving throw message"""
        speaker = data.get('s', 'Unknown')
        save_type = data.get('st', 'Unknown')
        formula = data.get('f', '1d20')
        total = data.get('tt', 0)
        dc = data.get('dc', 0)
        success = data.get('succ')
        
        success_class = 'success' if success is True else 'failure' if success is False else ''
        vs_text = f" vs DC {dc}" if dc else ""
        
        return f'''<div class="dnd5e chat-card save-card" data-actor-id="">
    <header class="card-header">
        <h3 class="save-title">{html_module.escape(str(save_type))} Saving Throw</h3>
    </header>
    <div class="card-content">
        <div class="dice-roll">
            <div class="roll-formula">{html_module.escape(str(formula))}</div>
            <h4 class="roll-total {success_class}">{total}{vs_text}</h4>
        </div>
    </div>
</div>'''
    
    def _generate_whisper_html(self, data: Dict[str, Any]) -> str:
        """Generate HTML for whisper message"""
        speaker = data.get('s', 'Unknown')
        targets = data.get('tg', [])
        content = data.get('c', '')
        
        targets_str = ', '.join(str(t) for t in targets) if targets else 'GM'
        speaker_text = f"{speaker} → {targets_str}"
        
        return f'''<div class="chat-message whisper">
    <header class="message-header">
        <i class="fas fa-eye-slash"></i>
        <h4 class="message-speaker">{html_module.escape(str(speaker_text))}</h4>
    </header>
    <div class="message-content">
        <p>{html_module.escape(str(content))}</p>
    </div>
</div>'''
    
    def _generate_gm_message_html(self, data: Dict[str, Any]) -> str:
        """Generate HTML for GM message"""
        content = data.get('c', '')
        
        return f'''<div class="chat-message gm-message">
    <div class="message-content">
        <p>{html_module.escape(str(content))}</p>
    </div>
</div>'''
    
    def _generate_chat_card_html(self, data: Dict[str, Any]) -> str:
        """Generate HTML for chat card"""
        card_type = data.get('ct', 'generic')
        name = data.get('n', 'Unknown')
        description = data.get('d', '')
        actions = data.get('a', [])
        
        buttons_html = ''
        if actions:
            buttons_html = '<div class="card-buttons">'
            for action in actions:  # No truncation - preserve all actions
                buttons_html += f'<button data-action="{html_module.escape(str(action))}">{html_module.escape(str(action))}</button>'
            buttons_html += '</div>'
        
        return f'''<div class="dnd5e chat-card item-card">
    <header class="card-header">
        <h3 class="item-name">{html_module.escape(str(name))}</h3>
    </header>
    <div class="card-content">
        <p>{html_module.escape(str(description))}</p>
    </div>
    {buttons_html}
</div>'''
    
    def _generate_condition_card_html(self, data: Dict[str, Any]) -> str:
        """Generate HTML for condition card"""
        condition_name = data.get('cn', 'Unknown')
        description = data.get('d', '')
        
        return f'''<div class="dnd5e chat-card condition-card">
    <header class="card-header">
        <h3 class="condition-name">{html_module.escape(str(condition_name))}</h3>
    </header>
    <div class="card-content">
        <p>{html_module.escape(str(description))}</p>
    </div>
</div>'''
    
    def _generate_table_result_html(self, data: Dict[str, Any]) -> str:
        """Generate HTML for table result"""
        roll = data.get('r', 0)
        result = data.get('res', '')
        table_name = data.get('tn', 'Random Table')
        
        return f'''<div class="roll-table-result">
    <div class="table-result">
        <div class="table-roll">{html_module.escape(str(roll))}</div>
        <div class="table-text">{html_module.escape(str(result))}</div>
    </div>
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
                    't': 'pl',
                    's': 'Unknown',
                    'c': 'Error processing message'
                }
                
                # Try to preserve sender from frontend message
                if hasattr(message, 'sender') and message.sender:
                    fallback_message['s'] = message.sender
                
                processed_messages.append(fallback_message)
        
        return processed_messages
    
    def generate_system_prompt(self) -> str:
        """
        Generate system prompt with type codes and schema definitions
        
        Returns:
            System prompt string for AI API
        """
        type_codes_str = ', '.join([f"'{code}': '{name}'" for code, name in self.REVERSE_TYPE_CODES.items()])
        
        system_prompt = f"""You are an AI assistant for tabletop RPG games. Chat messages use a compact JSON format with type codes and field abbreviations:

Type Codes (Abbreviations):
- dr: dice_roll
- pl: player_chat  
- ar: attack_roll
- sv: saving_throw
- gm: gm_message
- wp: whisper
- cc: chat_card
- cd: condition_card
- tr: table_result

Field Abbreviations:
- t: message type (dr, pl, ar, sv, gm, wp, cc, cd, tr)
- f: formula (dice roll formula)
- r: results (individual dice results array)
- tt: total (roll total result)
- s: speaker (character name who sent message)
- c: content (message text content)
- af: attack_formula (attack roll formula)
- at: attack_total (attack roll total)
- df: damage_formula (damage roll formula)
- dt: damage_total (damage roll total)
- st: save_type (saving throw ability type)
- dc: dc (difficulty class for saves)
- succ: success (true/false for save success)
- tg: targets (whisper target list)
- ct: card_type (item/spell/generic for chat cards)
- n: name (item/spell/condition name)
- d: description (card description text)
- a: actions (button actions array)
- cn: condition_name (condition card name)
- res: result (table result text)
- tn: table_name (table name)

Message Schemas:
- Dice Roll: {{"t": "dr", "f": "formula", "r": [results], "tt": total}}
- Player Chat: {{"t": "pl", "s": "speaker", "c": "content"}}
- Attack Roll: {{"t": "ar", "af": "attack_formula", "at": "attack_total", "df": "damage_formula", "dt": "damage_total", "s": "speaker"}}
- Saving Throw: {{"t": "sv", "st": "save_type", "f": "formula", "tt": "total", "dc": "dc", "succ": true/false, "s": "speaker"}}
- Whisper: {{"t": "wp", "s": "speaker", "c": "content", "tg": ["targets"]}}
- GM Message: {{"t": "gm", "c": "content"}}
- Chat Card: {{"t": "cc", "ct": "card_type", "n": "name", "d": "description", "a": ["actions"]}}
- Condition Card: {{"t": "cd", "cn": "condition_name", "d": "description"}}
- Table Result: {{"t": "tr", "r": roll, "res": "result", "tn": "table_name"}}

Respond naturally to the conversation as an AI assistant for tabletop RPGs. When you need to generate game mechanics, use the compact JSON format above with the field abbreviations."""
        
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
        
        # Player chat
        '''<div class="chat-message player-chat">
            <header class="message-header">
                <h4 class="message-speaker">Fighter</h4>
            </header>
            <div class="message-content">
                <p>I attack goblin!</p>
            </div>
        </div>''',
        
        # Attack roll
        '''<div class="dnd5e chat-card attack-card">
            <header class="card-header">
                <h3 class="item-name">Longsword</h3>
            </header>
            <div class="card-content">
                <div class="attack-roll">
                    <div class="roll-formula">1d20+5</div>
                    <h4 class="roll-total">15</h4>
                </div>
                <div class="damage-roll">
                    <div class="roll-formula">2d6+3</div>
                    <h4 class="roll-total">10</h4>
                </div>
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
    
    # Test system prompt generation
    print("\nSystem Prompt:")
    print(processor.generate_system_prompt())
    
    print("=" * 60)

if __name__ == "__main__":
    test_processor()
