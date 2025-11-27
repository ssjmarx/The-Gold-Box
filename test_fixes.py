#!/usr/bin/env python3
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

from server.api_chat_processor import APIChatProcessor
from server.ai_chat_processor import AIChatProcessor
import json

def test_fixes():
    api_processor = APIChatProcessor()
    ai_processor = AIChatProcessor()
    
    # Test 1: Card message with nested content
    card_msg = {
        "user": {"id": "I1xuWKewrC5fQH5U", "name": "Gamemaster"},
        "content": '<div class="chat-card activation-card"><span class="title">Dagger</span><span class="subtitle">Simple Melee</span><button data-action="rollAttack">Attack</button><button data-action="rollDamage">Damage</button><ul><li>Action</li><li>Proficient</li></ul></div>',
        "speaker": {"alias": "Snes"}
    }
    
    print("Test 1 - Fixed Card Processing (no nested content):")
    compact_card = api_processor._convert_to_compact(card_msg)
    print(json.dumps(compact_card, indent=2))
    print()
    
    # Test 2: AI response parsing (still needs fix)
    ai_response = '{"t": "dr", "ft": "Investigation Check (Searching for traps and locks)", "f": "1d20+3", "r": [16], "tt": 19} {"t": "gm", "c": "Your careful examination of the southwestern door reveals no signs of traps. The door appears to be a simple wooden door with a basic iron latch - no lock mechanism that you can detect. The door seems to open freely when you test the latch."}'
    
    print("Test 2 - AI Response (needs fix):")
    print("Test 2 - AI Response (needs fix):")
    print(f"Original: {ai_response}")
    processed = ai_processor.process_ai_response(ai_response)
    print(f"Processed: {json.dumps(processed, indent=2)}")
    print()
    
    print("✅ Card processing fix implemented!")
    print("❌ AI response still needs fixing (compact JSON issue)")

if __name__ == "__main__":
