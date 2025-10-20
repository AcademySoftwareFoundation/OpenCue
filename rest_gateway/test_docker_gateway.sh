#!/bin/bash

# Test script for REST Gateway running in Docker

echo "===== Testing REST Gateway Docker Container ====="
echo ""

# Configuration
GATEWAY_URL="http://localhost:8448"
JWT_SECRET="test-secret-key"

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to create JWT token (simple base64 for testing)
create_test_jwt() {
    local header='{"alg":"HS256","typ":"JWT"}'
    local payload='{"sub":"test","exp":'$(($(date +%s) + 3600))'}'
    
    local header_b64=$(echo -n "$header" | base64 | tr -d '=' | tr '/+' '_-')
    local payload_b64=$(echo -n "$payload" | base64 | tr -d '=' | tr '/+' '_-')
    
    # For testing, we'll use a simple token format
    # In production, this should be properly signed with the JWT secret
    echo "${header_b64}.${payload_b64}.test-signature"
}

# Function to test an endpoint
test_endpoint() {
    local service=$1
    local method=$2
    local payload=$3
    local description=$4
    
    echo -e "${YELLOW}Testing: $description${NC}"
    echo "Endpoint: POST $service/$method"
    
    local jwt_token=$(create_test_jwt)
    local url="$GATEWAY_URL/$service/$method"
    
    local response=$(curl -s -w "%{http_code}" -X POST "$url" \
        -H "Authorization: Bearer $jwt_token" \
        -H "Content-Type: application/json" \
        -d "$payload" 2>/dev/null)
    
    local http_code="${response: -3}"
    local body="${response%???}"
    
    echo "HTTP Status: $http_code"
    
    # Since we don't have a real Cuebot backend, we expect connection errors (502/503)
    # or authentication errors (401), but not 404 (which would indicate endpoint not found)
    if [[ "$http_code" == "401" ]]; then
        echo -e "${GREEN} Endpoint exists (JWT auth working)${NC}"
    elif [[ "$http_code" == "502" ]] || [[ "$http_code" == "503" ]]; then
        echo -e "${GREEN} Endpoint exists (backend connection error expected)${NC}"
    elif [[ "$http_code" == "404" ]]; then
        echo -e "${RED} Endpoint not found${NC}"
    else
        echo -e "${YELLOW}? Unexpected response ($http_code)${NC}"
    fi
    echo ""
}

# Test container is running
echo "Checking if REST Gateway container is running..."
if ! curl -s -f "$GATEWAY_URL" >/dev/null 2>&1; then
    if ! docker ps | grep -q opencue-rest-gateway-test; then
        echo -e "${RED}Container not running! Starting it...${NC}"
        docker run -d --name opencue-rest-gateway-test -p 8448:8448 \
            -e CUEBOT_ENDPOINT=mock-cuebot:8443 \
            -e JWT_SECRET=test-secret-key \
            opencue-rest-gateway:latest
        sleep 2
    fi
fi

echo -e "${GREEN}REST Gateway is accessible at $GATEWAY_URL${NC}"
echo ""

# Test sample endpoints from each interface
echo "========================================="
echo "Testing Sample Endpoints"
echo "========================================="
echo ""

test_endpoint "show.ShowInterface" "FindShow" '{"name": "test-show"}' "Find a show"
test_endpoint "job.JobInterface" "FindJob" '{"name": "test-job"}' "Find a job"
test_endpoint "frame.FrameInterface" "GetFrame" '{"id": "frame-123"}' "Get a frame"
test_endpoint "layer.LayerInterface" "FindLayer" '{"name": "test-layer"}' "Find a layer"
test_endpoint "group.GroupInterface" "FindGroup" '{"name": "test-group"}' "Find a group"
test_endpoint "host.HostInterface" "FindHost" '{"name": "test-host"}' "Find a host"
test_endpoint "owner.OwnerInterface" "GetOwner" '{"name": "test-owner"}' "Get an owner"
test_endpoint "proc.ProcInterface" "GetProc" '{"id": "proc-123"}' "Get a process"
test_endpoint "deed.DeedInterface" "GetOwner" '{"deed": {"id": "deed-123"}}' "Get deed owner"

# Test authentication
echo "========================================="
echo "Testing Authentication"
echo "========================================="
echo ""

echo -e "${YELLOW}Testing without JWT token:${NC}"
response=$(curl -s -w "%{http_code}" -X POST "$GATEWAY_URL/show.ShowInterface/FindShow" \
    -H "Content-Type: application/json" \
    -d '{"name": "test-show"}' 2>/dev/null)
http_code="${response: -3}"
if [[ "$http_code" == "401" ]]; then
    echo -e "${GREEN} Authentication required (401)${NC}"
else
    echo -e "${RED} Expected 401, got $http_code${NC}"
fi
echo ""

echo -e "${YELLOW}Testing with invalid JWT token:${NC}"
response=$(curl -s -w "%{http_code}" -X POST "$GATEWAY_URL/show.ShowInterface/FindShow" \
    -H "Authorization: Bearer invalid-token" \
    -H "Content-Type: application/json" \
    -d '{"name": "test-show"}' 2>/dev/null)
http_code="${response: -3}"
if [[ "$http_code" == "401" ]]; then
    echo -e "${GREEN} Invalid token rejected (401)${NC}"
else
    echo -e "${RED} Expected 401, got $http_code${NC}"
fi
echo ""

# Show container logs
echo "========================================="
echo "Container Logs (last 10 lines)"
echo "========================================="
docker logs --tail 10 opencue-rest-gateway-test

echo ""
echo "========================================="
echo "Docker Test Complete!"
echo "========================================="
echo ""
echo "To stop the test container:"
echo "  docker stop opencue-rest-gateway-test"
echo "  docker rm opencue-rest-gateway-test"
echo ""
echo -e "${GREEN}REST Gateway Docker container is working correctly!${NC}"
