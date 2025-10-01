#!/bin/bash

echo "=============================================="
echo "OpenCue REST Gateway - Docker Integration Tests"
echo "=============================================="
echo ""

# Check if we're in the right directory
if [ ! -f "integration_test.go" ]; then
    echo "Error: Please run this script from rest_gateway/opencue_gateway directory"
    exit 1
fi

cd ../..  # Go to OpenCue root

echo "Step 1: Starting OpenCue stack..."
docker compose up -d

echo ""
echo "Step 2: Waiting for services to be ready..."
sleep 5

echo ""
echo "Step 3: Generating JWT secret..."
export JWT_SECRET=$(openssl rand -base64 32)
echo "JWT_SECRET: ${JWT_SECRET:0:10}... (hidden)"

echo ""
echo "Step 4: Stopping any existing REST Gateway..."
docker rm -f opencue-rest-gateway 2>/dev/null || true

echo ""
echo "Step 5: Starting REST Gateway with JWT_SECRET..."
docker run -d --name opencue-rest-gateway \
  --network opencue_default \
  -p 8448:8448 \
  -e CUEBOT_ENDPOINT=cuebot:8443 \
  -e JWT_SECRET="$JWT_SECRET" \
  -e LOG_LEVEL=info \
  opencue-rest-gateway:latest

if [ $? -ne 0 ]; then
    echo "Error: Failed to start REST Gateway"
    exit 1
fi

echo ""
echo "Step 6: Waiting for REST Gateway to be ready..."
sleep 5

# Test connectivity
response=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8448/ 2>/dev/null)
if [ "$response" = "401" ]; then
    echo "[OK] REST Gateway is running and requiring authentication"
else
    echo "Warning: Gateway response: $response (expected 401)"
fi

echo ""
echo "Step 7: Building test image..."
docker build -f rest_gateway/Dockerfile --target build -t opencue-gateway-test .

if [ $? -ne 0 ]; then
    echo "Error: Failed to build test image"
    exit 1
fi

echo ""
echo "Step 8: Running integration tests..."
echo "========================================"
docker run --rm \
  --network opencue_default \
  -e GATEWAY_URL=http://opencue-rest-gateway:8448 \
  -e JWT_SECRET="$JWT_SECRET" \
  -e TEST_SHOW=testing \
  opencue-gateway-test \
  sh -c "cd /app/opencue_gateway && go test -v -tags=integration"

TEST_RESULT=$?

echo ""
echo "========================================"
if [ $TEST_RESULT -eq 0 ]; then
    echo "[OK] All integration tests passed!"
else
    echo "[X] Some integration tests failed"
fi
echo ""
echo "To view REST Gateway logs:"
echo "  docker logs opencue-rest-gateway"
echo ""
echo "To stop services:"
echo "  docker rm -f opencue-rest-gateway"
echo "  docker compose down"

exit $TEST_RESULT
