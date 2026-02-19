#!/bin/bash

# Test the fund endpoint

# First, get an auth token
echo "[1] Getting auth token..."
TOKEN=$(curl -s -X POST "http://localhost:8000/auth/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin@finanza.com&password=AdminPass123!" | grep -o '"access_token":"[^"]*' | cut -d'"' -f4)

if [ -z "$TOKEN" ]; then
  echo "❌ Failed to get auth token"
  exit 1
fi

echo "✅ Auth token: ${TOKEN:0:20}..."

# Now try to fund an account
echo ""
echo "[2] Testing fund transfer endpoint..."
curl -s -X POST "http://localhost:8000/api/admin/fund/transfer" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": 2,
    "amount": 100.0,
    "account_type": "CHECKING",
    "fund_source": "admin",
    "notes": "Test fund transfer"
  }' | jq .

echo ""
echo "Done!"
