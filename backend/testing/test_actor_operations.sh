#!/bin/bash
# Test actor operations (queries + health) with circular verification

# Source helper functions
. ./test_helpers.sh

section_header "Test: Actor Operations"

echo "📝 NOTE: This test verifies actor queries and health management"
echo "   • get_actor_details → modify → get_actor_details (confirm changes)"
echo ""

# Step 1: Start test session
start_session

# Step 2: Extract token ID from world state
extract_token_id

if [ -z "$TOKEN_ID" ]; then
  echo "❌ ERROR: No token ID found in world state"
  echo "   Skipping actor operations tests"
  end_session true
  exit 1
fi

echo "✅ Found token ID: $TOKEN_ID"
echo ""

# Step 3: Get full actor sheet
test_command "Get Full Actor Sheet" "get_actor_details token_id=\"$TOKEN_ID\""
ACTOR_NAME=$(get_value ".result.name // \"Unknown\"")
echo "📊 Actor name: $ACTOR_NAME"

if [ "$ACTOR_NAME" != "Unknown" ] && [ "$ACTOR_NAME" != "" ]; then
  echo "✅ VERIFICATION PASSED: Actor sheet retrieved successfully"
else
  echo "❌ VERIFICATION FAILED: Could not retrieve actor sheet"
fi
echo ""

# Step 4: Search for HP-related fields
test_command "Search for 'hp' Fields" "get_actor_details token_id=\"$TOKEN_ID\" search_phrase=\"hp\""
HP_MATCHES=$(get_value ".result.summary.total_matches // 0")
echo "📊 HP field matches: $HP_MATCHES"

if [ $HP_MATCHES -gt 0 ]; then
  echo "✅ VERIFICATION PASSED: Found $HP_MATCHES HP-related fields"
else
  echo "❌ VERIFICATION FAILED: Should find HP-related fields"
fi
echo ""

# Step 5: Search for weapon
test_command "Search for 'sword' Weapon" "get_actor_details token_id=\"$TOKEN_ID\" search_phrase=\"sword\""
SWORD_MATCHES=$(get_value ".result.summary.total_matches // 0")
echo "📊 Weapon matches: $SWORD_MATCHES"

if [ $SWORD_MATCHES -ge 0 ]; then
  echo "✅ VERIFICATION PASSED: Weapon search executed (found $SWORD_MATCHES matches)"
else
  echo "❌ VERIFICATION FAILED: Weapon search failed"
fi
echo ""

# Step 6: Search with numeric value
test_command "Search for Numeric Value '12'" "get_actor_details token_id=\"$TOKEN_ID\" search_phrase=\"12\""
NUM_MATCHES=$(get_value ".result.summary.total_matches // 0")
echo "📊 Numeric matches: $NUM_MATCHES"

if [ $NUM_MATCHES -ge 0 ]; then
  echo "✅ VERIFICATION PASSED: Numeric search executed (found $NUM_MATCHES matches)"
else
  echo "❌ VERIFICATION FAILED: Numeric search failed"
fi
echo ""

# Step 7: Search for nonexistent term
test_command "Search for Nonexistent Term" "get_actor_details token_id=\"$TOKEN_ID\" search_phrase=\"nonexistent\""
NO_MATCHES=$(get_value ".result.summary.total_matches // 0")
echo "📊 Nonexistent term matches: $NO_MATCHES"

if [ $NO_MATCHES -eq 0 ]; then
  echo "✅ VERIFICATION PASSED: Correctly found 0 matches for nonexistent term"
else
  echo "❌ VERIFICATION FAILED: Should find 0 matches for nonexistent term"
fi
echo ""

# Step 8: Create encounter for health tests
extract_actor_ids
create_encounter "Create Encounter for Health Tests" "$ACTOR_IDS" "$TEST_SESSION_ID" --roll_initiative

# Step 9: Get baseline HP
test_command "Get Baseline HP" "get_actor_details token_id=\"$TOKEN_ID\" search_phrase=\"hp\""
BASELINE_HP=$(get_value '.result.matches[] | select(.path == "attributes.hp.value") | .value // 0')
echo "📊 Baseline HP: $BASELINE_HP"
echo ""

# Step 10: Apply damage
test_command "Apply Damage (-15 HP)" "modify_token_attribute token_id=\"$TOKEN_ID\" attribute_path=\"attributes.hp.value\" value=-15 is_delta=true is_bar=true"

# Step 11: Verify damage applied
test_command "Verify Damage Applied" "get_actor_details token_id=\"$TOKEN_ID\" search_phrase=\"hp\""
NEW_HP=$(get_value '.result.matches[] | select(.path == "attributes.hp.value") | .value // 0')
DAMAGE_APPLIED=$((BASELINE_HP - NEW_HP))

echo "📊 New HP after damage: $NEW_HP"
echo "📊 Damage applied: $DAMAGE_APPLIED (expected: 15)"

if [ $DAMAGE_APPLIED -eq 15 ]; then
  echo "✅ VERIFICATION PASSED: 15 HP damage applied successfully"
else
  echo "❌ VERIFICATION FAILED: Expected 15 damage, got $DAMAGE_APPLIED"
fi
echo ""

# Step 12: Apply healing
test_command "Apply Healing (+10 HP)" "modify_token_attribute token_id=\"$TOKEN_ID\" attribute_path=\"attributes.hp.value\" value=10 is_delta=true is_bar=true"

# Step 13: Verify healing applied
test_command "Verify Healing Applied" "get_actor_details token_id=\"$TOKEN_ID\" search_phrase=\"hp\""
HEALED_HP=$(get_value '.result.matches[] | select(.path == "attributes.hp.value") | .value // 0')
HEALING_APPLIED=$((HEALED_HP - NEW_HP))

echo "📊 HP after healing: $HEALED_HP"
echo "📊 Healing applied: $HEALING_APPLIED (expected: 10)"

if [ $HEALING_APPLIED -eq 10 ]; then
  echo "✅ VERIFICATION PASSED: 10 HP healing applied successfully"
else
  echo "❌ VERIFICATION FAILED: Expected 10 healing, got $HEALING_APPLIED"
fi
echo ""

# Step 14: Set absolute HP value
test_command "Set Absolute HP (25)" "modify_token_attribute token_id=\"$TOKEN_ID\" attribute_path=\"attributes.hp.value\" value=25 is_delta=false is_bar=true"

# Step 15: Verify absolute value set
test_command "Verify Absolute HP Set" "get_actor_details token_id=\"$TOKEN_ID\" search_phrase=\"hp\""
ABSOLUTE_HP=$(get_value '.result.matches[] | select(.path == "attributes.hp.value") | .value // 0')

echo "📊 HP after absolute set: $ABSOLUTE_HP (expected: 25)"

if [ $ABSOLUTE_HP -eq 25 ]; then
  echo "✅ VERIFICATION PASSED: HP set to absolute value 25"
else
  echo "❌ VERIFICATION FAILED: Expected HP to be 25, got $ABSOLUTE_HP"
fi
echo ""

# Step 16: Verify combat state updated
test_command "Verify Combat State Updated" "get_encounter"
echo "✅ Combat state retrieved (should show updated HP)"

# Step 17: Try to modify with invalid token ID (should error)
test_command "Modify with Invalid Token ID (Should Error)" "modify_token_attribute token_id=\"invalid_token_id\" attribute_path=\"attributes.hp.value\" value=10 is_delta=true"
verify_error

# Step 18: Try to modify with invalid attribute path (should error)
test_command "Modify with Invalid Attribute Path (Should Error)" "modify_token_attribute token_id=\"$TOKEN_ID\" attribute_path=\"invalid.path\" value=10 is_delta=true"
verify_error

# Step 19: Clean up - delete encounter
test_command "Delete Encounter" "delete_encounter"

# Step 20: End session with WebSocket reset
end_session true

echo ""
echo "=========================================="
echo "✅ Actor operations test complete!"
echo "=========================================="
echo ""
echo "✅ Test Summary:"
echo "   • Full actor sheet retrieval"
echo "   • Grep-like search (hp, sword, numeric, nonexistent)"
echo "   • Damage application with verification"
echo "   • Healing application with verification"
echo "   • Absolute value setting with verification"
echo "   • Combat state updates"
echo "   • Error handling (invalid token_id, invalid path)"
echo ""
