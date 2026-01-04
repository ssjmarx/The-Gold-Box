#!/bin/bash
# Test combat operations with state verification loops

# Source helper functions
. ./test_helpers.sh

section_header "Test: Combat Operations"

echo "📝 NOTE: This test verifies combat operations with state verification"
echo "   • get_encounter → action → get_encounter (confirm state changes)"
echo ""

# Step 1: Start test session
start_session

# Step 2: Extract actor IDs from world state
extract_actor_ids

if [ "$ACTOR_IDS" = "null" ] || [ "$ACTOR_IDS" = "[]" ]; then
  echo "❌ ERROR: No actor IDs found in world state"
  echo "   Skipping combat tests"
  end_session true
  exit 1
fi

echo "✅ Found $(echo "$ACTOR_IDS" | jq 'length') actor IDs"
echo "   Actor IDs: $ACTOR_IDS"
echo ""

# Step 3: Get baseline encounter state (should be no combat)
test_command "Get Baseline Encounter" "get_encounter"
ACTIVE_COMBAT=$(get_value ".result.active_encounter // false")

if [ "$ACTIVE_COMBAT" = "false" ]; then
  echo "✅ VERIFICATION PASSED: No active combat (as expected)"
else
  echo "❌ VERIFICATION FAILED: Expected no active combat, but found active combat"
fi
echo ""

# Step 4: Create encounter with initiative
create_encounter "Create Encounter with Initiative" "$ACTOR_IDS" "$TEST_SESSION_ID" --roll_initiative

# Step 5: Verify combat was created
test_command "Verify Combat Created" "get_encounter"
ACTIVE_COMBAT=$(get_value ".result.active_encounter // false")
COMBATANTS_COUNT=$(get_value ".result.combatants | length // 0")

if [ "$ACTIVE_COMBAT" = "true" ]; then
  echo "✅ VERIFICATION PASSED: Combat is active"
else
  echo "❌ VERIFICATION FAILED: Combat should be active but is not"
fi

if [ $COMBATANTS_COUNT -gt 0 ]; then
  echo "✅ VERIFICATION PASSED: Combat has $COMBATANTS_COUNT combatants"
else
  echo "❌ VERIFICATION FAILED: Combat should have combatants but has none"
fi
echo ""

# Step 6: Try to create encounter while combat is active (should error)
create_encounter "Create Encounter (Already Active - Should Error)" "$ACTOR_IDS" "$TEST_SESSION_ID" --no_initiative
verify_error

# Step 7: Advance combat turn
test_command "Advance Combat Turn" "advance_combat_turn"

# Step 8: Verify turn advanced
test_command "Verify Turn Advanced" "get_encounter"
CURRENT_TURN=$(get_value ".result.current_turn // -1")
ROUND=$(get_value ".result.round // 0")

echo "📊 Current turn: $CURRENT_TURN, Round: $ROUND"
if [ $CURRENT_TURN -gt 0 ]; then
  echo "✅ VERIFICATION PASSED: Turn advanced successfully"
else
  echo "❌ VERIFICATION FAILED: Turn should have advanced"
fi
echo ""

# Step 9: Advance combat turn again
test_command "Advance Combat Turn (Second Time)" "advance_combat_turn"

# Step 10: Verify second turn advancement
test_command "Verify Second Turn Advancement" "get_encounter"
NEW_CURRENT_TURN=$(get_value ".result.current_turn // -1")
NEW_ROUND=$(get_value ".result.round // 0")

echo "📊 New turn: $NEW_CURRENT_TURN, Round: $NEW_ROUND"

# If turn wrapped back to 0, round should have increased
if [ $NEW_CURRENT_TURN -eq 0 ] && [ $NEW_ROUND -gt $ROUND ]; then
  echo "✅ VERIFICATION PASSED: Turn wrapped, round increased"
elif [ $NEW_CURRENT_TURN -gt $CURRENT_TURN ]; then
  echo "✅ VERIFICATION PASSED: Turn advanced successfully"
else
  echo "❌ VERIFICATION FAILED: Turn did not advance correctly"
fi
echo ""

# Step 11: Delete encounter
test_command "Delete Encounter" "delete_encounter"

# Step 12: Verify combat was deleted
test_command "Verify Combat Deleted" "get_encounter"
ACTIVE_COMBAT=$(get_value ".result.active_encounter // false")

if [ "$ACTIVE_COMBAT" = "false" ]; then
  echo "✅ VERIFICATION PASSED: Combat is no longer active"
else
  echo "❌ VERIFICATION FAILED: Combat should be deleted but is still active"
fi
echo ""

# Step 13: Try to delete encounter when no combat (should error)
test_command "Delete Encounter (No Combat - Should Error)" "delete_encounter"
verify_error

# Step 14: Try to advance turn when no combat (should error)
test_command "Advance Turn (No Combat - Should Error)" "advance_combat_turn"
verify_error

# Step 15: End session with WebSocket reset
end_session true

echo ""
echo "=========================================="
echo "✅ Combat operations test complete!"
echo "=========================================="
echo ""
echo "✅ Test Summary:"
echo "   • Encounter creation with initiative"
echo "   • Encounter creation error handling (already active)"
echo "   • Turn advancement (multiple times)"
echo "   • Turn advancement error handling (no combat)"
echo "   • Encounter deletion"
echo "   • Encounter deletion error handling (no combat)"
echo "   • State verification at each step"
echo ""
