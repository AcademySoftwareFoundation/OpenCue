---
title: "REST Gateway Development"
nav_order: 83
parent: Developer Guide
layout: default
linkTitle: "Developing the OpenCue REST Gateway"
date: 2025-09-15
description: >
  Guide for developers working on the OpenCue REST Gateway
---

# REST Gateway Development

### Development guide for the OpenCue REST Gateway

---

This guide covers development workflows, architecture, and best practices for contributors working on the OpenCue REST Gateway. The gateway provides HTTP/REST endpoints for OpenCue's gRPC API using the grpc-gateway framework.

## Architecture Overview

The REST Gateway is built with:

- **Go 1.19+** - Primary programming language
- **grpc-gateway** - Automatic REST endpoint generation from protobuf definitions
- **Protocol Buffers** - Interface definitions and code generation
- **JWT authentication** - HMAC SHA256 token-based security
- **Docker** - Containerized deployment

### Project Structure

```
rest_gateway/
├── opencue_gateway/         # Main gateway application
│   ├── main.go              # Entry point and server setup
│   ├── main_test.go         # Unit tests
│   ├── go.mod               # Go module definition
│   └── go.sum               # Dependency checksums
├── gen/                     # Generated protobuf code
│   └── go/                  # Go-specific generated files
├── Dockerfile               # Container build definition
├── README.md                # Basic usage documentation
└── docs/                    # Detailed documentation
```

## Development Environment Setup

### Prerequisites

- Go 1.19 or later
- Protocol Buffers compiler (`protoc`)
- Docker and Docker Compose
- Git
- Make (optional, for automation)

### Initial Setup

- **Clone the repository:**

```bash
git clone https://github.com/AcademySoftwareFoundation/OpenCue.git
cd OpenCue
```

- **Quick Development Start with Docker:**

**Note:** The REST Gateway is not included in OpenCue's main docker-compose.yml and must be deployed separately.

```bash
# Start the OpenCue stack first
docker compose up -d

# Build and start REST Gateway separately
cd rest_gateway
docker build -f Dockerfile -t opencue-rest-gateway-dev .
docker run -d --name opencue-gateway-dev \
  --network opencue_default \
  -p 8448:8448 \
  -e CUEBOT_ENDPOINT=cuebot:8443 \
  -e JWT_SECRET=dev-secret-key \
  opencue-rest-gateway-dev

# The REST Gateway will be available at http://localhost:8448
# Cuebot gRPC will be available at localhost:8443
```

- **Install Go dependencies (for local development):**

```bash
cd rest_gateway/opencue_gateway
go mod download
```

- **Install protobuf dependencies:**

```bash
# On Ubuntu/Debian
sudo apt-get install protobuf-compiler

# On macOS with Homebrew
brew install protobuf

# On Rocky Linux/CentOS
sudo dnf install protobuf protobuf-devel protobuf-compiler
```

- **Install Go protobuf plugins:**

```bash
go install google.golang.org/protobuf/cmd/protoc-gen-go@latest
go install google.golang.org/grpc/cmd/protoc-gen-go-grpc@latest
go install github.com/grpc-ecosystem/grpc-gateway/v2/protoc-gen-grpc-gateway@latest
```

### Environment Configuration

Create a development environment file:

```bash
# .env.dev
GRPC_ENDPOINT=localhost:8443
HTTP_PORT=8448
JWT_SECRET=dev-secret-key-change-in-production
LOG_LEVEL=debug
CORS_ALLOWED_ORIGINS=*
```

## Building and Running

### Local Development

Build and run the gateway locally:

```bash
cd opencue_gateway

# Build the binary
go build -o opencue-rest-gateway

# Run with development settings
source ../.env.dev
./opencue-rest-gateway
```

### Using Docker

Build and run with Docker:

```bash
# Build Docker image
docker build -t opencue-rest-gateway-dev .

# Run container
docker run -d \
  --name opencue-gateway-dev \
  -p 8448:8448 \
  -e GRPC_ENDPOINT=host.docker.internal:8443 \
  -e JWT_SECRET=dev-secret-key \
  -e LOG_LEVEL=debug \
  opencue-rest-gateway-dev
```

### Integration Testing

Test with a running Cuebot instance:

```bash
# Start OpenCue stack using Docker Compose (from OpenCue root)
docker compose up -d

# In another terminal, start the gateway
cd rest_gateway/opencue_gateway
go run main.go

# Test service connectivity (expects 401 - confirms service is running)
response=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8448/)
if [ "$response" = "401" ]; then
    echo "Gateway is running and requiring authentication (as expected)"
else
    echo "Gateway may not be running (got HTTP $response)"
fi

# Test with JWT authentication (all endpoints require authentication)
export JWT_TOKEN=$(python3 -c "
import jwt, datetime
payload = {'user': 'dev', 'exp': datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=1)}
print(jwt.encode(payload, 'dev-secret-key', algorithm='HS256'))
")
curl -H "Authorization: Bearer $JWT_TOKEN" \
     -H "Content-Type: application/json" \
     -X POST \
     "http://localhost:8448/show.ShowInterface/GetShows" \
     -d '{}'
```

## Code Generation

### Protocol Buffer Compilation

The gateway relies on generated code from OpenCue's protobuf definitions. When protobuf files change, regenerate the code:

```bash
# From the OpenCue root directory
# This generates both gRPC and grpc-gateway code
protoc \
  --proto_path=proto \
  --go_out=rest_gateway/gen/go \
  --go_opt=paths=source_relative \
  --go-grpc_out=rest_gateway/gen/go \
  --go-grpc_opt=paths=source_relative \
  --grpc-gateway_out=rest_gateway/gen/go \
  --grpc-gateway_opt=paths=source_relative \
  proto/*.proto
```

### Automation Script

Create a script to automate code generation:

```bash
#!/bin/bash
# scripts/generate_code.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

echo "Generating protobuf code..."

# Clean existing generated code
rm -rf rest_gateway/gen/go/*

# Generate new code
protoc \
  --proto_path=proto \
  --go_out=rest_gateway/gen/go \
  --go_opt=paths=source_relative \
  --go-grpc_out=rest_gateway/gen/go \
  --go-grpc_opt=paths=source_relative \
  --grpc-gateway_out=rest_gateway/gen/go \
  --grpc-gateway_opt=paths=source_relative \
  proto/*.proto

echo "Code generation complete"
```

## Testing

### Unit Tests

Run the test suite:

```bash
cd rest_gateway/opencue_gateway

# Run all tests
go test .

# Run tests with coverage
go test -cover .

# Run tests with detailed output
go test -v .

# Generate coverage report
go test -coverprofile=coverage.out .
go tool cover -html=coverage.out -o coverage.html
```

### Integration Tests

The gateway includes comprehensive integration tests that verify all OpenCue interfaces:

```bash
# Automated Docker-based integration tests (recommended)
cd rest_gateway/opencue_gateway
./run_docker_integration_tests.sh

# Manual: Run integration tests (requires running Cuebot and REST Gateway)
go test -tags=integration -v

# Run specific test function
go test -tags=integration -run TestIntegration_ShowInterface

# Run tests with race detection
go test -race .

# Run benchmarks
go test -bench=. -tags=integration
```

The automated script (`run_docker_integration_tests.sh`) handles:
- Starting the OpenCue stack
- Generating JWT secrets
- Building and starting the REST Gateway
- Running all integration tests
- Cleanup

### Load Testing

Test gateway performance:

```bash
# Install Apache Bench
sudo apt-get install apache2-utils  # Ubuntu/Debian
brew install httpie                  # macOS

# Create test payload
echo '{}' > test_payload.json

# Run load test
ab -n 1000 -c 10 -T application/json -p test_payload.json \
   -H "Authorization: Bearer $JWT_TOKEN" \
   http://localhost:8448/show.ShowInterface/GetShows
```

## Code Style and Standards

### Go Code Standards

Follow standard Go conventions:

- Use `gofmt` for formatting
- Use `golint` for style checking
- Use `go vet` for static analysis
- Follow the [Effective Go](https://golang.org/doc/effective_go.html) guidelines

```bash
cd rest_gateway/opencue_gateway

# Format code
go fmt .

# Lint code
golint .

# Static analysis
go vet .

# Run all checks
go fmt . && golint . && go vet . && go test .
```

### Pre-commit Hooks

Set up pre-commit hooks for code quality:

```bash
# .git/hooks/pre-commit
#!/bin/bash

cd rest_gateway/opencue_gateway

echo "Running Go formatter..."
go fmt .

echo "Running linter..."
golint .

echo "Running static analysis..."
go vet .

echo "Running tests..."
go test .

if [ $? -ne 0 ]; then
    echo "Tests failed. Commit aborted."
    exit 1
fi
```

## Adding New Endpoints

### Step 1: Update Protobuf Definitions

When adding new OpenCue functionality:

1. Define the gRPC service in `proto/` directory
2. Add appropriate HTTP annotations for REST mapping
3. Regenerate code using the generation script

Example protobuf service:
```protobuf
service MyNewInterface {
  rpc GetSomething(GetSomethingRequest) returns (GetSomethingResponse) {
    option (google.api.http) = {
      post: "/my.MyNewInterface/GetSomething"
      body: "*"
    };
  }
}
```

### Step 2: Register Handler

Add the new handler registration in `main.go`:

```go
// Register new interface handler
err = myNewPb.RegisterMyNewInterfaceHandlerFromEndpoint(
    ctx, mux, grpcEndpoint, grpcDialOpts)
if err != nil {
    log.Fatalf("Failed to register MyNew interface handler: %v", err)
}
```

### Step 3: Add Tests

Create tests for the new endpoints:

```go
func TestMyNewEndpoints(t *testing.T) {
    tests := []EndpointTest{
        {
            name:     "GetSomething",
            endpoint: "/my.MyNewInterface/GetSomething",
            payload:  `{}`,
        },
    }
    
    for _, test := range tests {
        t.Run(test.name, func(t *testing.T) {
            testEndpoint(t, test)
        })
    }
}
```

## Debugging

### Enable Debug Logging

Set log level to debug for detailed output:

```bash
export LOG_LEVEL=debug
go run main.go
```

### Using Delve Debugger

Debug with Go's delve debugger:

```bash
# Install delve
go install github.com/go-delve/delve/cmd/dlv@latest

# Start debugging session
dlv debug main.go

# Set breakpoints and run
(dlv) break main.main
(dlv) continue
```

### Memory and CPU Profiling

Profile the application:

```go
// Add to main.go for development
import _ "net/http/pprof"

// In main function
go func() {
    log.Println(http.ListenAndServe("localhost:6060", nil))
}()
```

Access profiling endpoints:
- CPU: `http://localhost:6060/debug/pprof/profile`
- Memory: `http://localhost:6060/debug/pprof/heap`
- Goroutines: `http://localhost:6060/debug/pprof/goroutine`

## Security Considerations

### JWT Token Handling

- Never log JWT tokens
- Use secure random secrets in production
- Implement token rotation
- Validate expiration times

```go
// Example secure token validation
func validateJWT(tokenString, secret string) (*jwt.Token, error) {
    token, err := jwt.Parse(tokenString, func(token *jwt.Token) (interface{}, error) {
        if _, ok := token.Method.(*jwt.SigningMethodHMAC); !ok {
            return nil, fmt.Errorf("unexpected signing method: %v", token.Header["alg"])
        }
        return []byte(secret), nil
    })
    
    if err != nil {
        return nil, err
    }
    
    if !token.Valid {
        return nil, fmt.Errorf("invalid token")
    }
    
    return token, nil
}
```

### Input Validation

Validate all input data:

```go
func validateRequest(req *SomeRequest) error {
    if req == nil {
        return fmt.Errorf("request cannot be nil")
    }
    
    if req.Id == "" {
        return fmt.Errorf("id field is required")
    }
    
    // Additional validation...
    return nil
}
```

## Performance Optimization

### Connection Pooling

Optimize gRPC connections:

```go
// Configure connection pool
grpcDialOpts := []grpc.DialOption{
    grpc.WithTransportCredentials(insecure.NewCredentials()),
    grpc.WithKeepaliveParams(keepalive.ClientParameters{
        Time:                10 * time.Second,
        Timeout:             time.Second,
        PermitWithoutStream: true,
    }),
}
```

### Response Caching

Implement caching for expensive operations:

```go
type CacheEntry struct {
    Data      interface{}
    ExpiresAt time.Time
}

var cache = make(map[string]CacheEntry)
var cacheMutex sync.RWMutex

func getCachedResponse(key string) (interface{}, bool) {
    cacheMutex.RLock()
    defer cacheMutex.RUnlock()
    
    entry, exists := cache[key]
    if !exists || time.Now().After(entry.ExpiresAt) {
        return nil, false
    }
    
    return entry.Data, true
}
```

## Contributing Guidelines

### Pull Request Process

1. **Fork and branch**: Create a feature branch from `master`
2. **Develop**: Implement your changes with tests
3. **Test**: Run full test suite and integration tests
4. **Document**: Update relevant documentation
5. **Review**: Submit pull request for code review

### Commit Message Format

Use conventional commit format:

```
feat: add new endpoint for layer management
fix: resolve JWT token validation issue
docs: update REST API documentation
test: add integration tests for job operations
```

### Code Review Checklist

- [ ] Code follows Go conventions
- [ ] All tests pass
- [ ] Security considerations addressed
- [ ] Performance impact assessed
- [ ] Documentation updated
- [ ] Backward compatibility maintained

## Deployment for Development

### Local Kubernetes

Deploy to local Kubernetes for testing:

```yaml
# k8s-dev.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: opencue-rest-gateway-dev
spec:
  replicas: 1
  selector:
    matchLabels:
      app: opencue-rest-gateway-dev
  template:
    metadata:
      labels:
        app: opencue-rest-gateway-dev
    spec:
      containers:
      - name: gateway
        image: opencue-rest-gateway-dev:latest
        ports:
        - containerPort: 8448
        env:
        - name: GRPC_ENDPOINT
          value: "cuebot-service:8443"
        - name: JWT_SECRET
          value: "dev-secret-key"
        - name: LOG_LEVEL
          value: "debug"
```

### Docker Compose Development

Create development compose file (separate from main OpenCue stack):

```yaml
# rest-gateway-dev-compose.yml
version: '3.8'
services:
  rest-gateway-dev:
    build: 
      context: .
      dockerfile: Dockerfile
    ports:
      - "8448:8448"
    environment:
      - CUEBOT_ENDPOINT=cuebot:8443
      - JWT_SECRET=dev-secret-key
      - LOG_LEVEL=debug
    volumes:
      - ./opencue_gateway:/app/opencue_gateway
    networks:
      - opencue_default
    command: go run main.go

networks:
  opencue_default:
    external: true
```

```bash
# Deploy REST Gateway with separate compose file
docker compose -f rest-gateway-dev-compose.yml up -d
```

## Troubleshooting Development Issues

### Common Build Errors

**Missing protobuf compiler:**
```bash
# Install protobuf compiler
sudo apt-get install protobuf-compiler  # Ubuntu/Debian
brew install protobuf                    # macOS
sudo dnf install protobuf-compiler       # Rocky Linux/CentOS
```

**Go module issues:**
```bash
# Clean module cache
go clean -modcache

# Re-download dependencies
go mod download

# Verify dependencies
go mod verify
```

**Generated code out of date:**
```bash
# Regenerate protobuf code
./scripts/generate_code.sh

# Or manually
protoc --proto_path=proto --go_out=rest_gateway/gen/go proto/*.proto
```

### Runtime Issues

**Connection refused to Cuebot:**
```bash
# Check Cuebot is running
docker ps | grep cuebot

# Test connectivity
telnet localhost 8443

# Check logs
docker logs cuebot-container
```

**JWT authentication fails:**
```bash
# Verify token format
echo $JWT_TOKEN | cut -d. -f2 | base64 -d

# Check secret matches
echo $JWT_SECRET
```

## Resources

### Documentation
- [gRPC-Gateway Documentation](https://github.com/grpc-ecosystem/grpc-gateway)
- [Protocol Buffers Guide](https://developers.google.com/protocol-buffers)
- [Go Testing Documentation](https://golang.org/pkg/testing/)

### Community
- [OpenCue GitHub](https://github.com/AcademySoftwareFoundation/OpenCue)
- [Academy Software Foundation Slack](https://academysoftwarefdn.slack.com/archives/CMFPXV39Q)

## What's next?

- [Contributing to OpenCue](/docs/developer-guide/contributing/) - General contribution guidelines
- [Sandbox Testing](/docs/developer-guide/sandbox-testing/) - Test environment setup
- [REST API Reference](/docs/reference/rest-api-reference/) - Complete API documentation
