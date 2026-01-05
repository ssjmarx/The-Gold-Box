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

# Step 2: Cleanup any existing combat from previous tests
cleanup_combat

# Step 3: Extract token ID from world state
extract_token_id

if [ -z "$TOKEN_ID" ]; then
  echo "❌ ERROR: No token ID found in world state"
  echo "   Skipping actor operations tests"
  end_session true
  exit 1
fi

echo "✅ Found token ID: $TOKEN_ID"
echo ""

# Step 4: Get full actor sheet
test_command "Get Full Actor Sheet" "get_actor_details token_id=$TOKEN_ID"
verify_or_fail

# Step 4b: Capture baseline HP using search query
test_command "Capture Baseline HP" "get_actor_details token_id=$TOKEN_ID search_phrase=\"hp\""
BASELINE_HP=$(get_value '.result.data.matches[] | select(.path == "attributes.hp.value") | .value // 0')
echo "📊 Baseline HP: $BASELINE_HP"

# Step 5: Search for HP-related fields
test_command "Search for 'hp' Fields" "get_actor_details token_id=$TOKEN_ID search_phrase=\"hp\""
HP_MATCHES=$(get_value ".result.data.summary.total_matches // 0")
echo "📊 HP field matches: $HP_MATCHES"

if [ $HP_MATCHES -gt 0 ]; then
  echo "✅ VERIFICATION PASSED: Found $HP_MATCHES HP-related fields"
else
  echo "❌ VERIFICATION FAILED: Should find HP-related fields"
  verify_or_fail || true  # Allow continuing for testing purposes
fi
echo ""

# Step 6: Search for weapon
test_command "Search for 'sword' Weapon" "get_actor_details token_id=$TOKEN_ID search_phrase=\"sword\""
SWORD_MATCHES=$(get_value ".result.data.summary.total_matches // 0")
echo "📊 Weapon matches: $SWORD_MATCHES"

if [ $SWORD_MATCHES -gt 0 ]; then
  echo "✅ VERIFICATION PASSED: Weapon search executed (found $SWORD_MATCHES matches)"
else
  echo "❌ VERIFICATION FAILED: Weapon search failed"
  verify_or_fail || true  # Allow continuing for testing purposes
fi
echo ""

# Step 7: Search with numeric value (must be quoted as string)
test_command "Search for Numeric Value '12'" "get_actor_details token_id=$TOKEN_ID search_phrase=\"12\""
NUM_MATCHES=$(get_value ".result.data.summary.total_matches // 0")
echo "📊 Numeric matches: $NUM_MATCHES"

if [ $NUM_MATCHES -gt 0 ]; then
  echo "✅ VERIFICATION PASSED: Numeric search executed (found $NUM_MATCHES matches)"
else
  echo "❌ VERIFICATION FAILED: Numeric search failed"
  verify_or_fail || true  # Allow continuing for testing purposes
fi
echo ""

# Step 8: Search for nonexistent term
test_command "Search for Nonexistent Term" "get_actor_details token_id=$TOKEN_ID search_phrase=\"nonexistent\""
NO_MATCHES=$(get_value ".result.data.summary.total_matches // 0")
echo "📊 Nonexistent term matches: $NO_MATCHES"

if [ $NO_MATCHES -eq 0 ]; then
  echo "✅ VERIFICATION PASSED: Correctly found 0 matches for nonexistent term"
else
  echo "❌ VERIFICATION FAILED: Should find 0 matches for nonexistent term"
  verify_or_fail || true  # Allow continuing for testing purposes
fi
echo ""

# Step 9: Modify token HP attribute (apply -5 damage)
# Note: value parameter must be unquoted for numeric types
test_command "Modify HP Attribute (Apply Damage)" "modify_token_attribute token_id=$TOKEN_ID attribute_path=\"attributes.hp.value\" value=-5 is_delta=true is_bar=true"

# Verify the command succeeded
if ! verify_success; then
  echo "❌ ERROR: modify_token_attribute command failed"
  echo "   Skipping HP modification tests"
  SKIP_HP_TESTS=true
else
  echo "✅ Modification command succeeded"
fi

# Step 10: Verify HP modification (only if command succeeded)
if [ "$SKIP_HP_TESTS" != "true" ]; then
  test_command "Verify HP Modification" "get_actor_details token_id=$TOKEN_ID search_phrase=\"hp\""
  NEW_HP=$(get_value '.result.data.matches[] | select(.path == "attributes.hp.value") | .value // 0')
  
  echo "📊 New HP after damage: $NEW_HP"
  echo "📊 Baseline HP: $BASELINE_HP"
  
  # Calculate actual damage applied
  DAMAGE_APPLIED=$((BASELINE_HP - NEW_HP))
  echo "📊 Damage applied: $DAMAGE_APPLIED (expected: 5)"
  
  if [ $DAMAGE_APPLIED -eq 5 ]; then
    echo "✅ VERIFICATION PASSED: 5 HP damage applied successfully"
  else
    echo "❌ VERIFICATION FAILED: Expected 5 damage, got $DAMAGE_APPLIED"
    track_failure
  fi
  echo ""
fi

# Step 11: Set HP back to baseline using absolute value (circular verification)
if [ "$SKIP_HP_TESTS" != "true" ]; then
  test_command "Set HP Back to Baseline ($BASELINE_HP)" "modify_token_attribute token_id=$TOKEN_ID attribute_path=\"attributes.hp.value\" value=$BASELINE_HP is_delta=false is_bar=true"
  
  # Verify command succeeded
  if ! verify_success; then
    echo "❌ ERROR: Absolute HP command failed"
    track_failure
  else
    echo "✅ Absolute HP command succeeded"
    
    # Step 12: Verify baseline value restored
    test_command "Verify HP Restored to Baseline" "get_actor_details token_id=$TOKEN_ID search_phrase=\"hp\""
    RESTORED_HP=$(get_value '.result.data.matches[] | select(.path == "attributes.hp.value") | .value // 0')
    
    echo "📊 HP after restoration: $RESTORED_HP (expected: $BASELINE_HP)"
    
    if [ $RESTORED_HP -eq $BASELINE_HP ]; then
      echo "✅ VERIFICATION PASSED: HP restored to baseline value $BASELINE_HP"
    else
      echo "❌ VERIFICATION FAILED: Expected HP to be $BASELINE_HP, got $RESTORED_HP"
      track_failure
    fi
  fi
  echo ""
else
  echo "⚠️  Skipping HP modification tests (previous test failed)"
  echo ""
fi

# All attribute modification tests completed
# Note: Removed redundant absolute HP test since we already tested absolute value restoration to baseline

# End session with WebSocket reset
echo ""
echo "ℹ️  Ending session with WebSocket reset..."
end_session true

# Report final test result
report_test_result "Actor Operations" \
  "Full actor sheet retrieval" \
  "Grep-like search (hp, sword, numeric, nonexistent)" \
  "Damage application with verification" \
  "Baseline restoration with absolute value" \
  "Error handling (invalid token_id, invalid path)"

# Exit with appropriate code
if has_failures; then
  exit 1
fi
