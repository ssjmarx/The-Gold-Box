#!/bin/bash
# Master Test Runner - Runs all Gold Box tests and logs results

LOG_FILE="test_results.log"
TIMESTAMP=$(date "+%Y-%m-%d %H:%M:%S")
INDIVIDUAL_TESTS_DIR="individual_tests"
LOG_FILE_PATH="../shared/server_files/goldbox.log"

echo ""
echo "=========================================="
echo "The Gold Box Master Test Suite"
echo "=========================================="
echo "Started: $TIMESTAMP"
echo ""

# Prompt for admin password (once for all tests)
read -s -p "Enter admin password: " ADMIN_PASSWORD
echo ""
export ADMIN_PASSWORD

# Verify connection before starting tests
echo ""
. ./test_helpers.sh

if ! verify_connection; then
  echo ""
  echo "❌ ERROR: Cannot verify connection to admin API"
  echo "   Please ensure the backend server is running"
  echo "   and the admin password is correct."
  exit 1
fi

echo ""

# Clear old log file if it exists
if [ -f "$LOG_FILE" ]; then
  rm "$LOG_FILE"
fi

# Create log header
{
  echo "=========================================="
  echo "The Gold Box Test Results"
  echo "=========================================="
  echo "Started: $TIMESTAMP"
  echo ""
  echo "Test Summary:"
  echo "=========================================="
  echo ""
} > "$LOG_FILE"

# Track test results
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0

# Function to run a test and log results
run_test() {
  local test_name="$1"
  local test_script="$2"
  
  TOTAL_TESTS=$((TOTAL_TESTS + 1))
  
  echo "━━━ Running: $test_name ━━━"
  echo ""
  
  # Run test and capture both stdout and exit code
  # Set AUTO_MODE=true for non-interactive execution
  AUTO_MODE=true bash "$test_script" >> "$LOG_FILE" 2>&1
  EXIT_CODE=$?
  
  if [ $EXIT_CODE -eq 0 ]; then
    PASSED_TESTS=$((PASSED_TESTS + 1))
    echo "✅ $test_name: PASSED" >> "$LOG_FILE"
    echo "   Status: All checks passed"
  else
    FAILED_TESTS=$((FAILED_TESTS + 1))
    echo "❌ $test_name: FAILED (exit code: $EXIT_CODE)" >> "$LOG_FILE"
    echo "   Status: Some checks failed"
  fi
  
  # Wait for WebSocket reconnection before next test
  echo ""
  wait_for_websocket_reconnect 10 "$LOG_FILE_PATH"
  
  # Add separator to log
  echo "" >> "$LOG_FILE"
}

# Check if individual_tests directory exists, if not create it
if [ ! -d "$INDIVIDUAL_TESTS_DIR" ]; then
  echo "Creating individual_tests/ directory..."
  mkdir -p "$INDIVIDUAL_TESTS_DIR"
fi

# Run individual test scripts
# Source test_helpers first
. ./test_helpers.sh

# Check if individual test scripts exist in individual_tests directory
if [ -f "$INDIVIDUAL_TESTS_DIR/test_actor_operations.sh" ]; then
  run_test "Actor Operations Test" "./$INDIVIDUAL_TESTS_DIR/test_actor_operations.sh"
else
  echo "⚠️  WARNING: test_actor_operations.sh not found in $INDIVIDUAL_TESTS_DIR"
  echo "   Skipping actor operations test"
  echo ""
fi

if [ -f "$INDIVIDUAL_TESTS_DIR/test_combat.sh" ]; then
  run_test "Combat Operations Test" "./$INDIVIDUAL_TESTS_DIR/test_combat.sh"
else
  echo "⚠️  WARNING: test_combat.sh not found in $INDIVIDUAL_TESTS_DIR"
  echo "   Skipping combat test"
  echo ""
fi

if [ -f "$INDIVIDUAL_TESTS_DIR/test_dice_rolling.sh" ]; then
  run_test "Dice Rolling Test" "./$INDIVIDUAL_TESTS_DIR/test_dice_rolling.sh"
else
  echo "⚠️  WARNING: test_dice_rolling.sh not found in $INDIVIDUAL_TESTS_DIR"
  echo "   Skipping dice rolling test"
  echo ""
fi

if [ -f "$INDIVIDUAL_TESTS_DIR/test_messaging.sh" ]; then
  run_test "Messaging Test" "./$INDIVIDUAL_TESTS_DIR/test_messaging.sh"
else
  echo "⚠️  WARNING: test_messaging.sh not found in $INDIVIDUAL_TESTS_DIR"
  echo "   Skipping messaging test"
  echo ""
fi

if [ -f "$INDIVIDUAL_TESTS_DIR/test_multi_command_and_deltas.sh" ]; then
  run_test "Multi-Command & Delta Tracking Test" "./$INDIVIDUAL_TESTS_DIR/test_multi_command_and_deltas.sh"
else
  echo "⚠️  WARNING: test_multi_command_and_deltas.sh not found in $INDIVIDUAL_TESTS_DIR"
  echo "   Skipping multi-command test"
  echo ""
fi

# Write summary to log
END_TIME=$(date "+%Y-%m-%d %H:%M:%S")
{
  echo "=========================================="
  echo "Test Summary"
  echo "=========================================="
  echo "Started:  $TIMESTAMP"
  echo "Completed: $END_TIME"
  echo ""
  echo "Total Tests:  $TOTAL_TESTS"
  echo "Passed:       $PASSED_TESTS"
  echo "Failed:       $FAILED_TESTS"
  
  if [ $TOTAL_TESTS -gt 0 ]; then
    PASS_RATE=$((PASSED_TESTS * 100 / TOTAL_TESTS))
    echo "Pass Rate:    ${PASS_RATE}%"
  fi
  echo ""
  echo "Full test results logged in: $LOG_FILE"
  echo "=========================================="
} >> "$LOG_FILE"

# Print summary to console
echo ""
echo "=========================================="
echo "Test Summary"
echo "=========================================="
echo "Total Tests:  $TOTAL_TESTS"
echo "Passed:       $PASSED_TESTS"
echo "Failed:       $FAILED_TESTS"

if [ $TOTAL_TESTS -gt 0 ]; then
  PASS_RATE=$((PASSED_TESTS * 100 / TOTAL_TESTS))
  echo "Pass Rate:    ${PASS_RATE}%"
fi

echo ""
echo "Full test results logged in: $LOG_FILE"
echo "=========================================="
echo ""

if [ $FAILED_TESTS -eq 0 ]; then
  echo "🎉 All tests passed!"
else
  echo "⚠️  Some tests failed - check $LOG_FILE for details"
fi
