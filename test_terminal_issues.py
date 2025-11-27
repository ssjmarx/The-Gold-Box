#!/usr/bin/env python3
"""
Test specific issues seen in terminal output
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

from backend.server.api_chat_processor import APIChatProcessor

def test_terminal_dice_roll_issues():
    """Test the specific dice roll issues from terminal output"""
    print("🎲 Testing Terminal Output Issues")
    print("=" * 50)
    
    processor = APIChatProcessor()
    
    # Test case 1: Dagger card with roll indicators (should be dice-roll)
    dagger_card = {
        "id": "V0xQFuAWUF7iC4uG",
        "user": {"id": "5eFiujIoRS6TK61q", "name": "snes"},
        "content": '''<div class="chat-card activation-card">
    <section class="card-header description collapsible">
        <header class="summary">
            <img class="gold-icon" src="https://cdn.5e.tools/2024/img/items/XPHB/Dagger.webp" alt="Dagger" />
            <div class="name-stacked border">
                <span class="title">Dagger</span>
                <span class="subtitle">Simple Melee</span>
            </div>
            <i class="fa-solid fa-chevron-down fa-fw" inert></i>
        </header>
        <section class="details collapsible-content card-content">
            <div class="wrapper"><div class="rd__b  rd__b--2"><div data-roll-name-ancestor="Mastery: Nick" data-source="XPHB" class="rd__b  rd__b--3"><p><span class="rd__h rd__h--3" data-title-index="1"> <span class="entry-title-inner help-subtle" title="Source: Player's Handbook (2024), p214">Mastery: Nick.</span></span> When you make the extra attack of the Light property, you can make it as part of the <a class="content-link" draggable="true" data-plut-hover-page="actions.html" data-plut-hover-source="XPHB" data-plut-hover-hash="attack_xphb" data-plut-hover-tag="action" data-plut-hover-hash-pre-encoded="true" data-plut-hover-is-allow-redirect="false" data-plut-rich-link="true" data-plut-rich-link-entity-type="Item" data-plut-rich-link-original-text="action[Attack|XPHB]" data-plut-rich-link-tag-tag="action" data-plut-rich-link-tag-text="Attack|XPHB"><i class="fas fa-solid fa-suitcase"></i> Attack</a> action instead of as a <a class="content-link" draggable="true" data-plut-hover-page="variantrules.html" data-plut-hover-source="XPHB" data-plut-hover-hash="bonus%20action_xphb" data-plut-hover-tag="variantrule" data-plut-hover-hash-pre-encoded="true" data-plut-hover-is-allow-redirect="false" data-plut-rich-link="true" data-plut-rich-link-entity-type="JournalEntry" data-plut-rich-link-original-text="variantrule[Bonus Action|XPHB]" data-plut-rich-link-tag-tag="variantrule" data-plut-rich-link-tag-text="Bonus Action|XPHB]"><i class="fas fa-solid fa-book-open"></i> Bonus Action</a>. You can make this extra attack only once per turn.</p></div></div></div>
        </section>
    </section>

    <div class="card-buttons">
        <button type="button" data-action="rollAttack">
            <i class="dnd5e-icon" data-src="systems/dnd5e/icons/svg/trait-weapon-proficiencies.svg" inert></i> <span>Attack</span>
        </button>
        <button type="button" data-action="rollDamage">
            <i class="fa-solid fa-burst" inert></i> <span>Damage</span>
        </button>
    </div>


    <ul class="card-footer pills unlist">
        <li class="pill transparent">
            <span class="label">Action</span>
        </li>
        <li class="pill transparent">
            <span class="label">Instantaneous</span>
        </li>
        <li class="pill transparent">
            <span class="label">20/60 ft</span>
        </li>
        <li class="pill transparent">
            <span class="label">Equipped</span>
        </li>
        <li class="pill transparent">
            <span class="label">Proficient</span>
        </li>
    </ul>
</div>''',
        "flavor": "",
        "type": "base",
        "timestamp": 1763960419066,
        "speaker": {"scene": "5UAyjW90W6gW7UtW", "actor": "RSnHDAZZRrq8zZP8", "token": "1mqIWya772AYoukw", "alias": "Snes"},
        "whisper": [],
        "blind": False
    }
    
    # Test case 2: Bite card with actual roll data
    bite_card = {
        "id": "BlhulmrAylbBQZiZ",
        "user": {"id": "I1xuWKewrC5fQH5U", "name": "Gamemaster"},
        "content": '''<div class="chat-card activation-card">
    <section class="card-header description collapsible">
        <header class="summary">
            <img class="gold-icon" src="icons/creatures/abilities/mouth-teeth-long-red.webp" alt="Bite" />
            <div class="name-stacked border">
                <span class="title">Bite</span>
                <span class="subtitle">Natural</span>
            </div>
            <i class="fa-solid fa-chevron-down fa-fw" inert></i>
        </header>
        <section class="details collapsible-content card-content">
            <div class="wrapper"><div class="rd__b  rd__b--3"><p><i>Melee Attack Roll:</i> <a class="inline-roll roll" data-mode="roll" data-flavor="+5" data-formula="1d20+5" data-tooltip-text="1d20+5"><i class="fa-solid fa-dice-d20" inert></i>+5</a>, reach 5 feet. <i>Hit:</i> 5 (<a class="roll-link-group" data-type="damage" data-formulas="1d4 + 3" data-damage-types="piercing" data-roll-type="damage"><span class="roll-link"><i class="fa-solid fa-dice-d20" inert></i>1d4 + 3</span> Piercing</a>) damage.</p></div></div>
        </section>
    </section>

    <div class="card-buttons">
        <button type="button" data-action="rollAttack">
            <i class="dnd5e-icon" data-src="systems/dnd5e/icons/svg/trait-weapon-proficiencies.svg" inert></i> <span>Attack</span>
        </button>
        <button type="button" data-action="rollDamage">
            <i class="fa-solid fa-burst" inert></i> <span>Damage</span>
        </button>
    </div>


    <ul class="card-footer pills unlist">
        <li class="pill transparent">
            <span class="label">Action</span>
        </li>
        <li class="pill transparent">
            <span class="label">Instantaneous</span>
        </li>
        <li class="pill transparent">
            <span class="label">Self</span>
        </li>
        <li class="pill transparent">
            <span class="label">Equipped</span>
        </li>
        <li class="pill transparent">
            <span class="label">Proficient</span>
        </li>
    </ul>
</div>''',
        "flavor": "",
        "type": "base",
        "timestamp": 1763960520923,
        "speaker": {"scene": "5UAyjW90W6gW7UtW", "actor": "JCh3dNCvN4AgyKmY", "token": "338MXiHO9tGikQZ0", "alias": "Giant Rat"},
        "whisper": [],
        "blind": False
    }
    
    test_cases = [
        ("Dagger Card (should be card)", dagger_card),
        ("Bite Card with Roll Data (should be card)", bite_card),
    ]
    
    for name, test_msg in test_cases:
        print(f"\n📋 Testing: {name}")
        try:
            result = processor._convert_to_compact(test_msg)
            if result:
                print(f"  ✅ Type: {result.get('t')}")
                print(f"  ✅ Speaker: {result.get('s')}")
                
                # Check for problematic raw HTML in content
                if 'c' in result and len(result['c']) > 200:
                    print(f"  ⚠️  Raw HTML content detected ({len(result['c'])} chars)")
                    if '<div' in result['c']:
                        print(f"  ❌ ISSUE: Contains raw HTML divs")
                else:
                    print(f"  ✅ No problematic raw HTML")
                
                # Check for proper structured data extraction
                if result.get('t') == 'cd':
                    if result.get('tt') and result.get('st'):
                        print(f"  ✅ Card data extracted: {result.get('tt')} - {result.get('st')}")
                    else:
                        print(f"  ⚠️  Missing card data: tt={result.get('tt')}, st={result.get('st')}")
                
                # Check for roll data extraction
                if result.get('t') == 'dr':
                    roll_fields = [k for k in ['f', 'r', 'tt'] if k in result]
                    if roll_fields:
                        print(f"  ✅ Roll data extracted: {roll_fields}")
                    else:
                        print(f"  ⚠️  No roll data extracted")
            else:
                print("  ❌ No result returned")
        except Exception as e:
            print(f"  ❌ Error: {e}")

if __name__ == "__main__":
    test_terminal_dice_roll_issues()
