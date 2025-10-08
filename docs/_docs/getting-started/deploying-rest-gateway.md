---
title: "Deploying OpenCue REST Gateway"
nav_order: 26
parent: Getting Started
layout: default
linkTitle: "Deploying REST Gateway"
date: 2025-09-15
description: >
  Deploy the OpenCue REST Gateway for HTTP/REST API access
---

# Deploying OpenCue REST Gateway

### Set up HTTP/REST API access to your OpenCue system

---

The OpenCue REST Gateway provides HTTP/REST endpoints for all OpenCue functionality, enabling web applications and HTTP clients to interact with your render farm without requiring gRPC clients.

## Before you begin

Make sure you have completed the following steps:

1. [Set up the database](/docs/getting-started/setting-up-the-database/)
2. [Deploy Cuebot](/docs/getting-started/deploying-cuebot/)
3. [Deploy RQD](/docs/getting-started/deploying-rqd/) (optional for basic setup)

You also need:
- Docker installed on your system
- Access to the Cuebot gRPC endpoint (typically port 8443)
- A secure JWT secret for authentication

## Quick Start with Docker (Recommended)

**Important:** The REST Gateway is not included in OpenCue's main `docker-compose.yml` and must be deployed separately.

### Step 1: Start OpenCue Stack

From the OpenCue repository root:

```bash
# Start core OpenCue services (database, cuebot, rqd)
docker compose up -d

# Check service status
docker compose ps
```

### Step 2: Deploy REST Gateway Separately

```bash
# Generate JWT secret for REST API authentication
export JWT_SECRET=$(openssl rand -base64 32)

# Build REST Gateway image
docker build -f rest_gateway/Dockerfile -t opencue-rest-gateway:latest .

# Run REST Gateway as separate container
docker run -d --name opencue-rest-gateway \
  --network opencue_default \
  -p 8448:8448 \
  -e CUEBOT_ENDPOINT=cuebot:8443 \
  -e JWT_SECRET="$JWT_SECRET" \
  -e LOG_LEVEL=info \
  opencue-rest-gateway:latest
```

The REST Gateway will be available at `http://localhost:8448` alongside the OpenCue stack.

### Step 3: Run Comprehensive Tests

OpenCue includes a comprehensive test script that validates all REST Gateway endpoints:

```bash
cd rest_gateway
./test_rest_gateway_docker_compose.sh
```

This script will:
- Automatically generate JWT tokens
- Test all OpenCue interfaces (Show, Job, Frame, Layer, Group, Host, Owner, Proc, Deed, Comment, Allocation, Facility, Filter, Action, Matcher, Depend, Subscription, Limit, Service, ServiceOverride, Task)
- Verify different endpoints
- Display results for each test

Example output:
```
Testing OpenCue REST Gateway with Docker Compose
=================================================

Checking Docker Compose services...
Generating JWT token...
JWT token generated (length: 124)

Testing REST Gateway endpoints...
================================

1. Testing GetShows...
GetShows: SUCCESS
{
  "shows": [
    {
      "name": "testing",
      "id": "abc-123"
    }
  ]
}
```

### Step 4: Manual Testing (Optional)

For individual endpoint testing, generate a token manually:

```bash
# Install PyJWT first
pip install PyJWT

# Generate a quick test token
export JWT_TOKEN=$(python3 -c "
import jwt, datetime, os
secret = os.getenv('JWT_SECRET', 'dev-secret-key-change-in-production')
payload = {'user': 'test', 'exp': datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=1)}
print(jwt.encode(payload, secret, algorithm='HS256'))
")

# Test API access to get shows
curl -H "Authorization: Bearer $JWT_TOKEN" \
     -H "Content-Type: application/json" \
     -X POST \
     "http://localhost:8448/show.ShowInterface/GetShows" \
     -d '{}'
```

## Manual Docker Setup

For advanced users who want to build manually:

### Step 1: Build the REST Gateway

From the OpenCue repository root:

```bash
cd rest_gateway
docker build -t opencue-rest-gateway .
```

### Step 2: Generate JWT Secret

Create a secure secret for JWT token signing:

```bash
export JWT_SECRET=$(openssl rand -base64 32)
echo "JWT_SECRET=$JWT_SECRET"
```

**Important:** Save this secret securely - you'll need it for generating client tokens.

### Step 3: Run the Gateway

Start the REST Gateway container:

```bash
docker run -d \
  --name opencue-rest-gateway \
  --network host \
  -e CUEBOT_ENDPOINT=localhost:8443 \
  -e JWT_SECRET="$JWT_SECRET" \
  -e LOG_LEVEL=info \
  opencue-rest-gateway
```

For Docker Compose setups, adjust the network configuration:

```bash
docker run -d \
  --name opencue-rest-gateway \
  -p 8448:8448 \
  -e CUEBOT_ENDPOINT=cuebot:8443 \
  -e JWT_SECRET="$JWT_SECRET" \
  -e LOG_LEVEL=info \
  opencue-rest-gateway
```

### Step 4: Verify Installation

Check that the gateway is running:

```bash
# Test service connectivity (expects 401 - confirms service is running)
response=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8448/)
if [ "$response" = "401" ]; then
    echo "✓ Gateway is running and requiring authentication (as expected)"
else
    echo "✗ Gateway may not be running (got HTTP $response)"
fi
```

**Note:** All endpoints require JWT authentication - there are no public health endpoints.

For authenticated API testing:

```bash
# Install PyJWT if not already installed
pip install PyJWT

# Generate a test token using your JWT_SECRET
export JWT_TOKEN=$(python3 -c "
import jwt, datetime, os
secret = os.getenv('JWT_SECRET', 'dev-secret-key-change-in-production')
payload = {'user': 'test', 'exp': datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=1)}
print(jwt.encode(payload, secret, algorithm='HS256'))
")

# Test authenticated endpoint
curl -H "Authorization: Bearer $JWT_TOKEN" \
     -H "Content-Type: application/json" \
     -X POST "http://localhost:8448/show.ShowInterface/GetShows" \
     -d '{}'
```

Alternative using openssl for token generation (if Python/PyJWT not available):

```bash
# Create a simple test token using openssl (less secure but works for testing)
# Note: This creates a basic token structure, may not work with all JWT implementations
HEADER=$(echo -n '{"alg":"HS256","typ":"JWT"}' | base64 | tr -d '=' | tr '/+' '_-' | tr -d '\n')
PAYLOAD=$(echo -n '{"user":"test","exp":'$(date -d '+1 hour' +%s)'}' | base64 | tr -d '=' | tr '/+' '_-' | tr -d '\n')
SIGNATURE=$(echo -n "${HEADER}.${PAYLOAD}" | openssl dgst -sha256 -hmac "$JWT_SECRET" -binary | base64 | tr -d '=' | tr '/+' '_-' | tr -d '\n')
export JWT_TOKEN="${HEADER}.${PAYLOAD}.${SIGNATURE}"

# Test authenticated endpoint
curl -H "Authorization: Bearer $JWT_TOKEN" \
     -H "Content-Type: application/json" \
     -X POST "http://localhost:8448/show.ShowInterface/GetShows" \
     -d '{}'
```

## Authentication Setup

### Generate a Test Token

Create a JWT token for testing:

```python
# generate_token.py
import jwt
import datetime
import os

secret = os.getenv('JWT_SECRET')
if not secret:
    print("Please set JWT_SECRET environment variable")
    exit(1)

payload = {
    "user": "test-user",
    "exp": datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=24)
}

token = jwt.encode(payload, secret, algorithm="HS256")
print(f"export JWT_TOKEN='{token}'")
```

Run the script:

```bash
python3 generate_token.py
# Copy and paste the export command
```

### Test API Access

Test access to the OpenCue API:

```bash
curl -H "Authorization: Bearer $JWT_TOKEN" \
     -H "Content-Type: application/json" \
     -X POST \
     "http://localhost:8448/show.ShowInterface/GetShows" \
     -d '{}'
```

If successful, you'll see a JSON response with show information.

## Docker Compose Configuration (Separate File)

For production deployments, create a separate Docker Compose file for the REST Gateway:

```yaml
# rest-gateway-compose.yml
version: '3.8'
services:
  rest-gateway:
    build: ./rest_gateway
    ports:
      - "8448:8448"
    environment:
      - CUEBOT_ENDPOINT=cuebot:8443
      - JWT_SECRET=${JWT_SECRET}
      - LOG_LEVEL=info
      - CORS_ALLOWED_ORIGINS=*
      - REST_PORT=8448
    networks:
      - opencue_default
    restart: unless-stopped

networks:
  opencue_default:
    external: true
```

Deploy the services:

```bash
# Start OpenCue stack first
docker compose up -d

# Generate JWT secret
export JWT_SECRET=$(openssl rand -base64 32)

# Deploy REST Gateway separately
docker compose -f rest-gateway-compose.yml up -d
```

## Configuration Options

The REST Gateway supports these environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `CUEBOT_ENDPOINT` | `localhost:8443` | Cuebot gRPC server address |
| `REST_PORT` | `8448` | HTTP server port |
| `JWT_SECRET` | `dev-secret-key-change-in-production` | JWT signing secret (required) |
| `LOG_LEVEL` | `info` | Log level (debug, info, warn, error) |
| `CORS_ALLOWED_ORIGINS` | `*` | CORS allowed origins |

## Security Considerations

### Production Deployment

For production use:

1. **Use a strong JWT secret** (32+ random characters)
2. **Enable HTTPS** with a reverse proxy (nginx, HAProxy)
3. **Restrict CORS origins** to known domains
4. **Use secure networks** between gateway and Cuebot
5. **Monitor logs** for suspicious activity

### Network Security

Place the REST Gateway behind a reverse proxy:

```nginx
# nginx example
server {
    listen 443 ssl;
    server_name api.your-domain.com;
    
    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;
    
    location / {
        proxy_pass http://localhost:8448;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## Testing Your Deployment

### Comprehensive Testing

Use the included comprehensive test script:

```bash
cd rest_gateway
./test_rest_gateway_docker_compose.sh
```

This script tests all available endpoints across the OpenCue interfaces and provides detailed results.

### Basic Functionality Test

For a quick test, create a simple script:

```bash
#!/bin/bash
# test_gateway.sh

echo "Testing OpenCue REST Gateway..."

# Generate JWT token
export JWT_TOKEN=$(python3 -c "
import jwt, datetime
secret = 'dev-secret-key-change-in-production'
payload = {'user': 'test', 'exp': datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=1)}
print(jwt.encode(payload, secret, algorithm='HS256'))
")

# Test authentication
echo "Testing authentication..."
curl -s -H "Authorization: Bearer $JWT_TOKEN" \
     -H "Content-Type: application/json" \
     -X POST \
     "http://localhost:8448/show.ShowInterface/GetShows" \
     -d '{}' | jq .

echo "Test complete"
```

Run the test:

```bash
chmod +x test_gateway.sh
./test_gateway.sh
```

## Troubleshooting

### Common Issues

**Gateway won't start:**
- Check Docker logs: `docker logs opencue-rest-gateway`
- Verify port 8448 is available: `netstat -ln | grep 8448`

**Can't connect to Cuebot:**
- Test gRPC connectivity: `telnet localhost 8443`
- Check network configuration in Docker
- Verify Cuebot is running and accessible

**Authentication failures:**
- Verify JWT_SECRET is set correctly
- Check token expiration
- Ensure Authorization header format: `Bearer <token>`

**CORS errors in browser:**
- Set CORS_ALLOWED_ORIGINS to your domain
- Check browser developer console for specific errors

### Debug Mode

Enable debug logging for troubleshooting:

```bash
docker run -d \
  --name opencue-rest-gateway-debug \
  -p 8448:8448 \
  -e CUEBOT_ENDPOINT=localhost:8443 \
  -e JWT_SECRET="$JWT_SECRET" \
  -e LOG_LEVEL=debug \
  opencue-rest-gateway

# View logs
docker logs -f opencue-rest-gateway-debug
```

## What's next?

- [Using the REST API](/docs/user-guides/using-rest-api/) - Learn how to use the API
- [REST API Tutorial](/docs/tutorials/rest-api-tutorial/) - Step-by-step examples
- [Deploying REST Gateway](/docs/other-guides/deploying-rest-gateway/) - Production deployment patterns