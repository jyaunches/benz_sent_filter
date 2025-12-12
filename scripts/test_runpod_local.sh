#!/bin/bash
# Test RunPod handler locally
# Usage: ./scripts/test_runpod_local.sh

set -e

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

BASE_URL="${RUNPOD_LOCAL_URL:-http://localhost:8080}"

echo "Testing RunPod handler at $BASE_URL"
echo "======================================="

# Test 1: Classify single headline
echo -e "\n${GREEN}Test 1: Classify single headline${NC}"
curl -s -X POST "$BASE_URL/runsync" \
  -H "Content-Type: application/json" \
  -d '{
    "input": {
      "operation": "classify",
      "headline": "Apple announces new iPhone with revolutionary AI features"
    }
  }' | jq .

# Test 2: Classify with company
echo -e "\n${GREEN}Test 2: Classify with company relevance${NC}"
curl -s -X POST "$BASE_URL/runsync" \
  -H "Content-Type: application/json" \
  -d '{
    "input": {
      "operation": "classify",
      "headline": "Apple announces new iPhone with revolutionary AI features",
      "company": "Apple"
    }
  }' | jq .

# Test 3: Classify batch
echo -e "\n${GREEN}Test 3: Classify batch${NC}"
curl -s -X POST "$BASE_URL/runsync" \
  -H "Content-Type: application/json" \
  -d '{
    "input": {
      "operation": "classify_batch",
      "headlines": [
        "Tesla reports record Q3 earnings",
        "Opinion: Why crypto will fail"
      ]
    }
  }' | jq .

# Test 4: Routine operations
echo -e "\n${GREEN}Test 4: Routine operations multi-ticker${NC}"
curl -s -X POST "$BASE_URL/runsync" \
  -H "Content-Type: application/json" \
  -d '{
    "input": {
      "operation": "routine_operations",
      "headline": "Bank announces quarterly dividend payment",
      "ticker_symbols": ["BAC", "JPM"]
    }
  }' | jq .

# Test 5: Detect quantitative catalyst
echo -e "\n${GREEN}Test 5: Detect quantitative catalyst${NC}"
curl -s -X POST "$BASE_URL/runsync" \
  -H "Content-Type: application/json" \
  -d '{
    "input": {
      "operation": "detect_quantitative_catalyst",
      "headline": "Universal Security Instruments Increases Quarterly Dividend to $1 Per Share"
    }
  }' | jq .

# Test 6: Detect strategic catalyst
echo -e "\n${GREEN}Test 6: Detect strategic catalyst${NC}"
curl -s -X POST "$BASE_URL/runsync" \
  -H "Content-Type: application/json" \
  -d '{
    "input": {
      "operation": "detect_strategic_catalyst",
      "headline": "X4 Pharmaceuticals CEO and CFO Step Down"
    }
  }' | jq .

echo -e "\n${GREEN}All tests completed!${NC}"
