#!/bin/bash
# Test dice rolling operations with circular verification

# Source helper functions
. ./test_helpers.sh

section_header "Test: Dice Rolling"

echo "📝 NOTE: This test verifies dice operations with circular verification"
echo "   • get_message_history → roll → get_message_history (confirm dice rolls added)"
echo ""

# Step 1: Start test session
start_session

# Step 2: Get baseline message count
test_command "Get Baseline Message History" "get_message_history 10"
BASELINE_COUNT=$(get_value ".result.messages_count // 0")
echo "📊 Baseline message count: $BASELINE_COUNT"
echo ""

# Step 3: Roll single dice with flavor
test_command "Single Dice Roll with Flavor" "roll_dice rolls=[{\"formula\":\"1d20+5\",\"flavor\":\"Attack roll\"}]"

# Step 4: Roll multiple dice in one command
test_command "Multiple Dice Rolls" "roll_dice rolls=[{\"formula\":\"2d6\",\"flavor\":\"Damage\"},{\"formula\":\"1d8+3\",\"flavor\":\"Bonus damage\"}]"

# Step 5: Roll dice without flavor
test_command "Dice Roll Without Flavor" "roll_dice rolls=[{\"formula\":\"1d20\"}]"

# CRITICAL FIX: Wait for dice rolls to be collected by frontend
# Frontend needs time to execute rolls in Foundry and send them back via WebSocket
echo "⏳ Waiting for dice rolls to be collected..."
sleep 2

# Step 6: Verify dice rolls were added
test_command "Verify Dice Rolls Added" "get_message_history 15"
# CRITICAL FIX: Check for actual dice rolls by filtering for type 'dr' (dice_roll)
# Use map to safely handle null content
ROLL_COUNT=$(get_value '.result.messages // [] | map(select(.t == "dr")) | length')

echo "📊 Dice rolls found in history: $ROLL_COUNT (expected: 3)"
echo ""

# Extract dice roll details for verification
ROLL_1_FORMULA=$(get_value '.result.messages // [] | map(select(.t == "dr")) | .[-1].f // empty')
ROLL_1_FLAVOR=$(get_value '.result.messages // [] | map(select(.t == "dr")) | .[-1].ft // empty')
ROLL_2_FORMULA=$(get_value '.result.messages // [] | map(select(.t == "dr")) | .[-2].f // empty')
ROLL_3_FORMULA=$(get_value '.result.messages // [] | map(select(.t == "dr")) | .[-3].f // empty')

echo "📊 Roll 1: Formula=$ROLL_1_FORMULA, Flavor=\"$ROLL_1_FLAVOR\""
echo "📊 Roll 2: Formula=$ROLL_2_FORMULA"
echo "📊 Roll 3: Formula=$ROLL_3_FORMULA"
echo ""

# Verify specific rolls were created
if [ "$ROLL_COUNT" -ge 3 ]; then
  # Check for expected formulas (note: rolls are in reverse chronological order)
  # ROLL_1 is most recent (1d20), ROLL_2 is second (1d8+3), ROLL_3 is third (2d6)
  # We expect to find: 1d20+5, 2d6, 1d8+3, 1d20 somewhere in the dice rolls
  HAS_1D20=$(echo "$ROLL_1_FORMULA" | grep -q "1d20$" && echo "yes" || echo "no")
  HAS_BONUS_ROLL=$(echo "$ROLL_2_FORMULA" | grep -q "1d8+3" && echo "yes" || echo "no")
  HAS_DAMAGE_ROLL=$(echo "$ROLL_3_FORMULA" | grep -q "2d6" && echo "yes" || echo "no")
  
  if [ "$HAS_1D20" = "yes" ] && [ "$HAS_BONUS_ROLL" = "yes" ] && [ "$HAS_DAMAGE_ROLL" = "yes" ]; then
    echo "✅ VERIFICATION PASSED: All 3 expected dice roll formulas found"
  else
    echo "❌ VERIFICATION FAILED: Found $ROLL_COUNT dice rolls but formulas don't match expected values"
    echo "   Expected: ROLL_1=1d20, ROLL_2=1d8+3, ROLL_3=2d6"
    echo "   Got: ROLL_1=$ROLL_1_FORMULA, ROLL_2=$ROLL_2_FORMULA, ROLL_3=$ROLL_3_FORMULA"
    track_failure
  fi
else
  echo "❌ VERIFICATION FAILED: Expected 3 dice rolls, got $ROLL_COUNT"
  track_failure
fi
echo ""

# Step 7: End session with WebSocket reset
end_session true

echo ""
echo "=========================================="
echo "✅ Dice rolling test complete!"
echo "=========================================="
echo ""
echo "Expected results in Foundry VTT chat:"
echo "   • Dice roll: '1d20+5 (Attack roll) = X'"
echo "   • Dice roll: '2d6 (Damage) = X'"
echo "   • Dice roll: '1d8+3 (Bonus damage) = X'"
echo "   • Dice roll: '1d20 = X'"
echo ""
