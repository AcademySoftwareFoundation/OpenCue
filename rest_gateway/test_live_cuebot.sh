#!/bin/bash

# Test REST Gateway connected to live Cuebot instance

echo "===== Testing REST Gateway with Live Cuebot ====="
echo ""

GATEWAY_URL="http://localhost:8448"
JWT_SECRET="production-secret-key"

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Create properly signed JWT token
create_jwt_token() {
    python3 -c "
import base64
import hmac
import hashlib
import json
import time

header = {'alg': 'HS256', 'typ': 'JWT'}
payload = {'sub': 'test-user', 'exp': int(time.time()) + 3600}

header_b64 = base64.urlsafe_b64encode(json.dumps(header).encode()).decode().rstrip('=')
payload_b64 = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip('=')

message = f'{header_b64}.{payload_b64}'
signature = base64.urlsafe_b64encode(
    hmac.new('$JWT_SECRET'.encode(), message.encode(), hashlib.sha256).digest()
).decode().rstrip('=')

print(f'{message}.{signature}')
"
}

# Test function with better error handling
test_live_endpoint() {
    local service=$1
    local method=$2
    local payload=$3
    local description=$4
    
    echo -e "${YELLOW}Testing: $description${NC}"
    echo "Endpoint: POST $service/$method"
    
    local jwt_token=$(create_jwt_token)
    local url="$GATEWAY_URL/$service/$method"
    
    echo "Making request..."
    local response=$(curl -s -w "\n---HTTP_CODE:%{http_code}---" -X POST "$url" \
        -H "Authorization: Bearer $jwt_token" \
        -H "Content-Type: application/json" \
        -d "$payload" 2>/dev/null)
    
    local http_code=$(echo "$response" | grep "HTTP_CODE:" | cut -d':' -f2)
    local body=$(echo "$response" | sed '/---HTTP_CODE:/d')
    
    echo "HTTP Status: $http_code"
    
    if [[ "$http_code" == "200" ]]; then
        echo -e "${GREEN} SUCCESS - Got valid response${NC}"
        echo "Response: $body" | head -c 200
        [[ ${#body} -gt 200 ]] && echo "... (truncated)"
    elif [[ "$http_code" == "401" ]]; then
        echo -e "${RED} Authentication failed${NC}"
    elif [[ "$http_code" == "404" ]]; then
        echo -e "${RED} Endpoint not found${NC}"
    elif [[ "$http_code" == "502" ]] || [[ "$http_code" == "503" ]]; then
        echo -e "${YELLOW} Backend connection issue${NC}"
        echo "Response: $body"
    else
        echo -e "${YELLOW}? Unexpected response ($http_code)${NC}"
        echo "Response: $body"
    fi
    echo ""
}

# Check if Cuebot is accessible (gRPC service on 8443)
echo "Checking if Cuebot container is running..."
if docker ps | grep -q cuebot; then
    echo -e "${GREEN} Cuebot container is running${NC}"
else
    echo -e "${RED} Cuebot container not found${NC}"
    echo "Make sure Cuebot is running with 'docker compose up'"
    exit 1
fi

# Check if REST Gateway is accessible  
echo "Checking REST Gateway connectivity..."
if curl -s http://localhost:8448 >/dev/null 2>&1; then
    echo -e "${GREEN} REST Gateway is accessible on localhost:8448${NC}"
else
    echo -e "${RED} REST Gateway not accessible on localhost:8448${NC}"
    exit 1
fi

echo ""
echo "========================================="
echo "Testing Core Endpoints with Live Data"
echo "========================================="
echo ""

# Test endpoints that should work with a fresh Cuebot instance
test_live_endpoint "show.ShowInterface" "GetShows" '{}' "Get all shows"

# Try to find default show (many Cuebot instances have a 'testing' show)
test_live_endpoint "show.ShowInterface" "FindShow" '{"name": "testing"}' "Find 'testing' show"

# Test job endpoints
test_live_endpoint "job.JobInterface" "GetJobs" '{"r": {"show": {"name": "testing"}}}' "Get jobs for testing show"

# Test other interfaces
test_live_endpoint "host.HostInterface" "GetHosts" '{}' "Get all hosts"

echo "========================================="
echo "Testing Authentication"
echo "========================================="
echo ""

echo -e "${YELLOW}Testing without JWT token:${NC}"
response=$(curl -s -w "%{http_code}" -X POST "$GATEWAY_URL/show.ShowInterface/GetShows" \
    -H "Content-Type: application/json" \
    -d '{}' 2>/dev/null)
http_code="${response: -3}"
if [[ "$http_code" == "401" ]]; then
    echo -e "${GREEN} Authentication properly required${NC}"
else
    echo -e "${RED} Expected 401, got $http_code${NC}"
fi
echo ""

# Show recent container logs
echo "========================================="
echo "REST Gateway Logs (last 10 lines)"
echo "========================================="
docker logs --tail 10 opencue-rest-gateway-live

echo ""
echo "========================================="
echo "Live Cuebot Test Complete!"
echo "========================================="
echo ""
echo "REST Gateway is now connected to your live Cuebot instance!"
echo "You can test any endpoint using:"
echo ""
echo "JWT_TOKEN=\$(python3 -c \"
import base64, hmac, hashlib, json, time
header = {'alg': 'HS256', 'typ': 'JWT'}
payload = {'sub': 'user', 'exp': int(time.time()) + 3600}
h = base64.urlsafe_b64encode(json.dumps(header).encode()).decode().rstrip('=')
p = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip('=')
m = f'{h}.{p}'
s = base64.urlsafe_b64encode(hmac.new(b'$JWT_SECRET', m.encode(), hashlib.sha256).digest()).decode().rstrip('=')
print(f'{m}.{s}')
\")"
echo ""
echo "curl -X POST http://localhost:8448/show.ShowInterface/GetShows \\"
echo "  -H \"Authorization: Bearer \$JWT_TOKEN\" \\"
echo "  -H \"Content-Type: application/json\" \\"
echo "  -d '{}'"
echo ""
echo "To stop: docker stop opencue-rest-gateway-live"
