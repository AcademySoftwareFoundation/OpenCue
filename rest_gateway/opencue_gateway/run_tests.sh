#!/bin/bash

echo "===================================="
echo "OpenCue REST Gateway - Test Runner"
echo "===================================="
echo ""

# Check if we're in the right directory
if [ ! -f "main.go" ] || [ ! -f "main_test.go" ]; then
    echo "Error: Please run this script from rest_gateway/opencue_gateway directory"
    exit 1
fi

echo "Testing requires protobuf-generated code."
echo "Choose your testing method:"
echo ""
echo "1. DOCKER BUILD (Recommended)"
echo "   Full test with protobuf generation"
echo ""
echo "2. LOCAL TEST (requires protoc setup)"
echo "   Faster but needs protoc and plugins installed"
echo ""
echo "Select option [1-2]: "
read -r option

case $option in
    1)
        echo ""
        echo "Building Docker image with tests..."
        cd ../..
        docker build -f rest_gateway/Dockerfile \
            --target build \
            -t opencue-gateway-test:latest .
        
        echo ""
        echo "Running tests in container..."
        docker run --rm opencue-gateway-test:latest \
            sh -c "cd /app/opencue_gateway && go test -v ."
        ;;
    2)
        echo ""
        echo "Checking prerequisites..."
        
        # Check Go
        if ! command -v go &> /dev/null; then
            echo "Error: Go not found. Install Go 1.21+"
            exit 1
        fi
        echo "[OK] Go found: $(go version)"
        
        # Check protoc
        if ! command -v protoc &> /dev/null; then
            echo "Error: protoc not found. Install Protocol Buffers compiler"
            exit 1
        fi
        echo "[OK] protoc found: $(protoc --version)"
        
        echo ""
        echo "Generating protobuf code..."
        
        # Create gen directory
        mkdir -p gen/go
        
        # Generate code
        protoc -I ../../proto/src/ \
            --go_out ./gen/go/ \
            --go_opt paths=source_relative \
            --go-grpc_out ./gen/go/ \
            --go-grpc_opt paths=source_relative \
            ../../proto/src/*.proto
        
        protoc -I ../../proto/src/ \
            --grpc-gateway_out ./gen/go \
            --grpc-gateway_opt paths=source_relative \
            --grpc-gateway_opt generate_unbound_methods=true \
            ../../proto/src/*.proto
        
        echo ""
        echo "Running tests..."
        go test -v .
        ;;
    *)
        echo "Invalid option"
        exit 1
        ;;
esac
