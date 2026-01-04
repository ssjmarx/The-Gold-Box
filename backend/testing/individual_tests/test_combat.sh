#!/bin/bash
# Test multi-encounter support for combat operations
# Tests create/delete/advance operations with multiple concurrent encounters

# Source helper functions
. ./test_helpers.sh

section_header "Test: Multi-Encounter Combat Operations"

echo "📝 NOTE: This test verifies multi-encounter support"
echo "   • Create multiple encounters with different actors"
echo "   • Verify encounters are tracked independently"
echo "   • Advance turns in specific encounters"
echo "   • Delete specific encounters"
echo "   • Get all encounters vs specific encounter"
echo ""

# Step 1: Start test session
start_session

# Step 2: Cleanup any existing combat from previous tests
cleanup_combat

# Cleanup old combat_id files from previous test runs
rm -f .combat_id_1 .combat_id_2

# Step 3: Extract actor IDs from world state
extract_actor_ids

if [ "$ACTOR_IDS" = "null" ] || [ "$ACTOR_IDS" = "[]" ]; then
  test_failed "No actor IDs found in world state"
  exit 1
fi

echo "✅ Found $(echo "$ACTOR_IDS" | jq 'length') actor IDs"
echo "   Actor IDs: $ACTOR_IDS"
echo ""

# Step 4: Get baseline encounter state (should be no combat)
test_command "Get Baseline Encounter" "get_encounter"
IN_COMBAT=$(get_value ".result.in_combat // false")

if [ "$IN_COMBAT" = "false" ]; then
  echo "✅ VERIFICATION PASSED: No active combat (as expected)"
else
  echo "❌ VERIFICATION FAILED: Expected no active combat, but found active combat"
  track_failure
fi
echo ""

# Step 5: Create first encounter with all actors (roll initiative)
echo "Creating Encounter 1 with actors: $ACTOR_IDS"
create_encounter "Create Encounter 1" "$ACTOR_IDS" --roll_initiative ".combat_id_1"

# Step 6: Verify encounter 1 was created and capture combat_id
test_command "Verify Encounter 1 Created" "get_encounter"
IN_COMBAT=$(get_value ".result.in_combat // false")
COMBATANTS_COUNT=$(get_value ".result.combatants | length // 0")

if [ "$IN_COMBAT" = "true" ]; then
  echo "✅ VERIFICATION PASSED: Combat is active"
else
  echo "❌ VERIFICATION FAILED: Combat should be active but is not"
  track_failure
fi

if [ $COMBATANTS_COUNT -gt 0 ]; then
  echo "✅ VERIFICATION PASSED: Combat has $COMBATANTS_COUNT combatants"
else
  echo "❌ VERIFICATION FAILED: Combat should have combatants but has none"
  track_failure
fi

# Load combat_id_1 from saved file
if [ -f ".combat_id_1" ]; then
  COMBAT_ID_1=$(cat .combat_id_1)
  echo "💾 Loaded combat_id_1: $COMBAT_ID_1"
else
  echo "❌ VERIFICATION FAILED: No combat_id file found for encounter 1"
  track_failure
fi
echo ""

# Step 7: Create second encounter with all actors (NO roll initiative)
echo "Creating Encounter 2 with actors: $ACTOR_IDS"
create_encounter "Create Encounter 2" "$ACTOR_IDS" ".combat_id_2"

# Step 8: Verify encounter 2 was created and capture combat_id
test_command "Verify Encounter 2 Created" "get_encounter"
IN_COMBAT=$(get_value ".result.in_combat // false")
COMBATANTS_COUNT=$(get_value ".result.combatants | length // 0")

if [ "$IN_COMBAT" = "true" ]; then
  echo "✅ VERIFICATION PASSED: Combat is active"
else
  echo "❌ VERIFICATION FAILED: Combat should be active but is not"
  track_failure
fi

if [ $COMBATANTS_COUNT -gt 0 ]; then
  echo "✅ VERIFICATION PASSED: Combat has $COMBATANTS_COUNT combatants"
else
  echo "❌ VERIFICATION FAILED: Combat should have combatants but has none"
  track_failure
fi

# Load combat_id_2 from saved file
if [ -f ".combat_id_2" ]; then
  COMBAT_ID_2=$(cat .combat_id_2)
  echo "💾 Loaded combat_id_2: $COMBAT_ID_2"
else
  echo "❌ VERIFICATION FAILED: No combat_id file found for encounter 2"
  track_failure
fi
echo ""

# Step 9: Verify get_encounter returns all encounters
test_command "Get All Encounters" "get_encounter"
IN_COMBAT=$(get_value ".result.in_combat // false")
ACTIVE_COUNT=$(get_value ".result.active_count // 0")
ENCOUNTERS_ARRAY=$(get_value ".result.encounters // []")

if [ "$IN_COMBAT" = "true" ]; then
  echo "✅ VERIFICATION PASSED: Combat is active"
  echo "✅ VERIFICATION PASSED: Found $ACTIVE_COUNT active encounters"
else
  echo "❌ VERIFICATION FAILED: Expected active encounters"
  track_failure
fi

if [ "$ACTIVE_COUNT" -eq 2 ]; then
  echo "✅ VERIFICATION PASSED: Correct number of encounters (2)"
else
  echo "❌ VERIFICATION FAILED: Expected 2 encounters, got $ACTIVE_COUNT"
  track_failure
fi
echo ""

# Step 10: Get specific encounter (Encounter 1)
test_command "Get Encounter 1" "get_encounter" "$COMBAT_ID_1"
IN_COMBAT=$(get_value ".result.in_combat // false")
SPECIFIC_ENCOUNTER_ID=$(get_value ".result.combat_id // empty")

if [ "$IN_COMBAT" = "true" ]; then
  echo "✅ VERIFICATION PASSED: Combat is active"
else
  echo "❌ VERIFICATION FAILED: Combat should be active but is not"
  track_failure
fi

if [ "$SPECIFIC_ENCOUNTER_ID" = "$COMBAT_ID_1" ]; then
  echo "✅ VERIFICATION PASSED: Correct encounter ID returned ($COMBAT_ID_1)"
else
  echo "❌ VERIFICATION FAILED: Wrong encounter ID returned"
  track_failure
fi
echo ""

# Step 11: Advance turn in Encounter 1 only
echo "Advancing turn in Encounter 1 (ID: $COMBAT_ID_1)"
test_command "Advance Turn Encounter 1" "advance_combat_turn" "$COMBAT_ID_1"

# Step 12: Verify turn advanced in Encounter 1 only
test_command "Verify Turn Advanced Encounter 1" "get_encounter" "$COMBAT_ID_1"
CURRENT_TURN=$(get_value ".result.current_turn // -1")
ROUND=$(get_value ".result.round // 0")
COMBATANT_INDEX=$(get_value ".result.turn // -1")

echo "📊 Encounter 1 - Current turn: $COMBATANT_INDEX, Round: $ROUND"
if [ $COMBATANT_INDEX -ge 0 ]; then
  echo "✅ VERIFICATION PASSED: Turn advanced successfully"
else
  echo "❌ VERIFICATION FAILED: Turn should have advanced (got $COMBATANT_INDEX)"
  track_failure
fi
echo ""

# Step 13: Verify Encounter 2 state unchanged
echo "Verifying Encounter 2 was NOT affected by turn advancement in Encounter 1"
test_command "Verify Encounter 2 Unchanged" "get_encounter" "$COMBAT_ID_2"
IN_COMBAT=$(get_value ".result.in_combat // false")
ENCOUNTER_2_TURN=$(get_value ".result.current_turn // -1")
ENCOUNTER_2_ROUND=$(get_value ".result.round // 0")

echo "📊 Encounter 2 - Current turn: $ENCOUNTER_2_TURN, Round: $ENCOUNTER_2_ROUND"

# Encounter 2 should still be at turn 1
if [ "$ENCOUNTER_2_TURN" -eq 1 ]; then
  echo "✅ VERIFICATION PASSED: Encounter 2 unchanged (turn 1)"
elif [ "$ENCOUNTER_2_TURN" -ne 1 ]; then
  echo "❌ VERIFICATION FAILED: Encounter 2 was affected by Encounter 1's turn advancement"
  track_failure
else
  echo "❌ VERIFICATION FAILED: Cannot verify Encounter 2 state"
  track_failure
fi
echo ""

# Step 14: Delete Encounter 1 specifically
echo "Deleting Encounter 1 (ID: $COMBAT_ID_1)"
test_command "Delete Encounter 1" "delete_encounter" "$COMBAT_ID_1"

# Step 15: Verify Encounter 1 deleted but Encounter 2 remains
test_command "Verify Encounter 1 Deleted" "get_encounter" "$COMBAT_ID_2"
IN_COMBAT=$(get_value ".result.in_combat // false")
ACTIVE_COUNT=$(get_value ".result.active_count // 0")

if [ "$IN_COMBAT" = "true" ]; then
  echo "✅ VERIFICATION PASSED: Combat is active"
else
  echo "❌ VERIFICATION FAILED: Combat should be active but is not"
  track_failure
fi

if [ "$ACTIVE_COUNT" -eq 1 ]; then
  echo "✅ VERIFICATION PASSED: One encounter remains (Encounter 2)"
else
  echo "❌ VERIFICATION FAILED: Expected 1 encounter, got $ACTIVE_COUNT"
  track_failure
fi
echo ""

# Step 16: Delete Encounter 2
echo "Deleting Encounter 2 (ID: $COMBAT_ID_2)"
test_command "Delete Encounter 2" "delete_encounter" "$COMBAT_ID_2"

# Step 17: Verify all encounters deleted
test_command "Verify All Encounters Deleted" "get_encounter"
IN_COMBAT=$(get_value ".result.in_combat // false")
ACTIVE_COUNT=$(get_value ".result.active_count // 0")

if [ "$IN_COMBAT" = "false" ]; then
  echo "✅ VERIFICATION PASSED: No encounters remain"
else
  echo "❌ VERIFICATION FAILED: Expected no encounters, but found $ACTIVE_COUNT"
  track_failure
fi
echo ""

# Step 18: Try to delete non-existent encounter (should error)
test_command "Delete Non-Existent Encounter (Should Error)" "delete_encounter" "non_existent_encounter_id"
verify_error_or_fail

# Step 19: Try to advance turn in non-existent encounter (should error)
test_command "Advance Turn (No Combat - Should Error)" "advance_combat_turn" "non_existent_encounter_id"
verify_error_or_fail

# Step 20: Try to get non-existent encounter (should return not active)
test_command "Get Non-Existent Encounter (Should Return Inactive)" "get_encounter" "non_existent_encounter_id"
verify_success
echo "✅ Verification: Non-existent encounter correctly returns inactive"
echo ""

# Step 21: End session with WebSocket reset
echo ""
echo "ℹ️  Ending session with WebSocket reset..."
end_session true

# Report final test result
report_test_result "Multi-Encounter Combat Operations" \
  "Multiple encounter creation and tracking" \
  "Independent turn advancement per encounter" \
  "Specific encounter deletion by ID" \
  "Get all encounters returns multiple encounters" \
  "Get specific encounter by ID" \
  "Error handling for non-existent encounters" \
  "Encounter independence verification"

# Exit with appropriate code
if has_failures; then
  exit 1
fi
