#!/bin/bash
# Test script simulating benz_analyzer filter pipeline calls to benz_sent_filter
#
# This script replicates the exact sequence of API calls made by benz_analyzer
# during article processing, based on the filter pipeline order.
#
# Filter Pipeline Order (from benz_analyzer/src/analyzer_core/api.py):
# 1. published_date_filter (no API call)
# 2. ticker_filter (no API call)
# 3. ticker_type_filter (calls FMP API, not benz_sent_filter)
# 4. channel_filter (no API call)
# 5. tag_filter (no API call)
# 6. regex_filter (no API call)
# 7. news_institution_filter (no API call)
# 8. opinion_filter → /classify endpoint
# 9. routine_operation_filter → /routine-operations endpoint
# 10. catalyst_filter → /detect-quantitative-catalyst endpoint
# 11. strategic_catalyst_filter → /detect-strategic-catalyst endpoint
# 12. historical_filter (calls benz_researcher, not benz_sent_filter)
# 13. pattern_filter (no API call)
# 14. warning_threshold_filter (no API call)

set -e  # Exit on error

# Configuration
BASE_URL="${BENZ_SENT_FILTER_URL:-http://localhost:8002}"
TIMEOUT=5

# Test article data (from IMPL-025 test dataset - SATS example)
HEADLINE="EchoStar To Sell 3.45 GHz And 600 MHz Spectrum Licenses To AT&T For \$23B, Establishes Hybrid MNO Agreement With Boost Mobile To Address FCC Inquiries"
TICKERS='["SATS", "T"]'

echo "=========================================="
echo "benz_analyzer Filter Pipeline Simulation"
echo "=========================================="
echo ""
echo "Base URL: $BASE_URL"
echo "Test Article: $HEADLINE"
echo "Tickers: $TICKERS"
echo ""
echo "=========================================="
echo "Filter Sequence (only API calls shown)"
echo "=========================================="
echo ""

# Step 8: OpinionFilter calls /classify
echo "Step 8: OpinionFilter → POST /classify"
echo "----------------------------------------"
echo "Payload:"
cat <<EOF | jq '.'
{
  "headline": "$HEADLINE"
}
EOF
echo ""
echo "Making request..."
CLASSIFY_RESPONSE=$(curl -s -X POST "$BASE_URL/classify" \
  -H "Content-Type: application/json" \
  -d "{\"headline\": \"$HEADLINE\"}" \
  --max-time $TIMEOUT)

echo "Response:"
echo "$CLASSIFY_RESPONSE" | jq '.'
echo ""
echo "Key Fields:"
echo "  - is_opinion: $(echo "$CLASSIFY_RESPONSE" | jq -r '.is_opinion')"
echo "  - temporal_category: $(echo "$CLASSIFY_RESPONSE" | jq -r '.temporal_category')"
echo "  - far_future_forecast: $(echo "$CLASSIFY_RESPONSE" | jq -r '.far_future_forecast')"
echo "  - conditional_language: $(echo "$CLASSIFY_RESPONSE" | jq -r '.conditional_language // "null"')"
echo ""
echo "=========================================="
echo ""

# Step 9: RoutineOperationFilter calls /routine-operations
echo "Step 9: RoutineOperationFilter → POST /routine-operations"
echo "----------------------------------------"
echo "Payload:"
cat <<EOF | jq '.'
{
  "headline": "$HEADLINE",
  "ticker_symbols": $TICKERS
}
EOF
echo ""
echo "Making request..."
ROUTINE_RESPONSE=$(curl -s -X POST "$BASE_URL/routine-operations" \
  -H "Content-Type: application/json" \
  -d "{\"headline\": \"$HEADLINE\", \"ticker_symbols\": $TICKERS}" \
  --max-time $TIMEOUT)

echo "Response:"
echo "$ROUTINE_RESPONSE" | jq '.'
echo ""
echo "Per-Ticker Results:"
echo "$ROUTINE_RESPONSE" | jq -r '.routine_operations_by_ticker | to_entries[] | "  \(.key): routine_operation=\(.value.routine_operation // "null"), confidence=\(.value.routine_confidence // "null")"'
echo ""
echo "Material Tickers (routine_operation=false):"
echo "$ROUTINE_RESPONSE" | jq -r '.routine_operations_by_ticker | to_entries[] | select(.value.routine_operation == false or .value.routine_operation == null) | "  - \(.key)"'
echo ""
echo "=========================================="
echo ""

# Step 10: QuantitativeCatalystFilter calls /detect-quantitative-catalyst
echo "Step 10: QuantitativeCatalystFilter → POST /detect-quantitative-catalyst"
echo "----------------------------------------"
echo "Payload:"
cat <<EOF | jq '.'
{
  "headline": "$HEADLINE"
}
EOF
echo ""
echo "Making request..."
QUANT_CATALYST_RESPONSE=$(curl -s -X POST "$BASE_URL/detect-quantitative-catalyst" \
  -H "Content-Type: application/json" \
  -d "{\"headline\": \"$HEADLINE\"}" \
  --max-time $TIMEOUT)

echo "Response:"
echo "$QUANT_CATALYST_RESPONSE" | jq '.'
echo ""
echo "Key Fields:"
echo "  - has_quantitative_catalyst: $(echo "$QUANT_CATALYST_RESPONSE" | jq -r '.has_quantitative_catalyst')"
echo "  - catalyst_type: $(echo "$QUANT_CATALYST_RESPONSE" | jq -r '.catalyst_type // "null"')"
echo "  - catalyst_values: $(echo "$QUANT_CATALYST_RESPONSE" | jq -r '.catalyst_values // [] | join(", ")')"
echo "  - confidence: $(echo "$QUANT_CATALYST_RESPONSE" | jq -r '.confidence')"
echo ""
echo "=========================================="
echo ""

# Step 11: StrategicCatalystFilter calls /detect-strategic-catalyst
echo "Step 11: StrategicCatalystFilter → POST /detect-strategic-catalyst"
echo "----------------------------------------"
echo "Payload:"
cat <<EOF | jq '.'
{
  "headline": "$HEADLINE"
}
EOF
echo ""
echo "Making request..."
STRAT_CATALYST_RESPONSE=$(curl -s -X POST "$BASE_URL/detect-strategic-catalyst" \
  -H "Content-Type: application/json" \
  -d "{\"headline\": \"$HEADLINE\"}" \
  --max-time $TIMEOUT)

echo "Response:"
echo "$STRAT_CATALYST_RESPONSE" | jq '.'
echo ""
echo "Key Fields:"
echo "  - has_strategic_catalyst: $(echo "$STRAT_CATALYST_RESPONSE" | jq -r '.has_strategic_catalyst')"
echo "  - catalyst_subtype: $(echo "$STRAT_CATALYST_RESPONSE" | jq -r '.catalyst_subtype // "null"')"
echo "  - confidence: $(echo "$STRAT_CATALYST_RESPONSE" | jq -r '.confidence')"
echo ""
echo "=========================================="
echo ""

# Summary
echo "=========================================="
echo "Summary of Filter Results"
echo "=========================================="
echo ""
echo "OpinionFilter (/classify):"
echo "  - Article rejected: $([ "$(echo "$CLASSIFY_RESPONSE" | jq -r '.is_opinion')" == "true" ] && echo "YES (OPINION_CONTENT)" || echo "NO")"
echo "  - Far-future forecast: $([ "$(echo "$CLASSIFY_RESPONSE" | jq -r '.far_future_forecast')" == "true" ] && echo "YES (would reject)" || echo "NO")"
echo "  - Temporal category: $(echo "$CLASSIFY_RESPONSE" | jq -r '.temporal_category')"
echo ""
echo "RoutineOperationFilter (/routine-operations):"
MATERIAL_COUNT=$(echo "$ROUTINE_RESPONSE" | jq '[.routine_operations_by_ticker | to_entries[] | select(.value.routine_operation == false or .value.routine_operation == null)] | length')
TOTAL_COUNT=$(echo "$ROUTINE_RESPONSE" | jq '.routine_operations_by_ticker | length')
echo "  - Material tickers: $MATERIAL_COUNT / $TOTAL_COUNT"
echo "  - Article rejected: $([ "$MATERIAL_COUNT" == "0" ] && echo "YES (ROUTINE_OPERATION - all tickers routine)" || echo "NO")"
echo ""
echo "QuantitativeCatalystFilter (/detect-quantitative-catalyst):"
echo "  - Catalyst detected: $(echo "$QUANT_CATALYST_RESPONSE" | jq -r '.has_quantitative_catalyst')"
echo "  - Type: $(echo "$QUANT_CATALYST_RESPONSE" | jq -r '.catalyst_type // "none"')"
echo "  - Values: $(echo "$QUANT_CATALYST_RESPONSE" | jq -r '.catalyst_values // [] | join(", ") | if . == "" then "none" else . end')"
echo ""
echo "StrategicCatalystFilter (/detect-strategic-catalyst):"
echo "  - Catalyst detected: $(echo "$STRAT_CATALYST_RESPONSE" | jq -r '.has_strategic_catalyst')"
echo "  - Subtype: $(echo "$STRAT_CATALYST_RESPONSE" | jq -r '.catalyst_subtype // "none"')"
echo ""
echo "Pipeline Decision:"
if [ "$(echo "$CLASSIFY_RESPONSE" | jq -r '.is_opinion')" == "true" ]; then
  echo "  ❌ REJECTED at OpinionFilter (OPINION_CONTENT)"
elif [ "$(echo "$CLASSIFY_RESPONSE" | jq -r '.far_future_forecast')" == "true" ]; then
  echo "  ❌ REJECTED at OpinionFilter (FAR_FUTURE_FORECAST)"
elif [ "$MATERIAL_COUNT" == "0" ]; then
  echo "  ❌ REJECTED at RoutineOperationFilter (ROUTINE_OPERATION)"
else
  echo "  ✅ PASSED all filters - would proceed to LLM analysis"
  echo "  📊 Material tickers for LLM: $(echo "$ROUTINE_RESPONSE" | jq -r '.routine_operations_by_ticker | to_entries[] | select(.value.routine_operation == false or .value.routine_operation == null) | .key' | tr '\n' ', ' | sed 's/,$//')"

  # Show recipe selection hints
  if [ "$(echo "$QUANT_CATALYST_RESPONSE" | jq -r '.has_quantitative_catalyst')" == "true" ]; then
    echo "  🎯 Recipe hint: QUANTITATIVE_CATALYST (priority 1)"
  elif [ "$(echo "$STRAT_CATALYST_RESPONSE" | jq -r '.has_strategic_catalyst')" == "true" ]; then
    echo "  🎯 Recipe hint: STRATEGIC_CATALYST (priority 2)"
  else
    echo "  🎯 Recipe hint: Pattern-based recipe (priority 3+)"
  fi
fi
echo ""
echo "=========================================="
echo "Test Complete!"
echo "=========================================="
