#!/bin/bash

# Simple script to test REST Gateway endpoints

GATEWAY_URL="${GATEWAY_URL:-http://localhost:8448}"
JWT_TOKEN="${JWT_TOKEN:-your-jwt-token-here}"

echo "Testing endpoint: $1"
echo "Payload: $2"
echo ""

curl -X POST "$GATEWAY_URL$1" \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d "$2" \
  -w "\nHTTP Status: %{http_code}\n"
