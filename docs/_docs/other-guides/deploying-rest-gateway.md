---
title: "Deploying REST Gateway"
nav_order: 49
parent: Other Guides
layout: default
linkTitle: "Deploying the OpenCue REST Gateway"
date: 2025-09-15
description: >
  Deploy and configure the OpenCue REST Gateway for production use
---

# Deploying REST Gateway

### Production deployment and configuration of the OpenCue REST Gateway

---

The OpenCue REST Gateway provides HTTP/REST endpoints for OpenCue's gRPC API, enabling web applications and HTTP clients to interact with your render farm. This guide covers production deployment patterns and configuration.

## Architecture Overview

<div class="mermaid">
graph LR
    A["Web Client<br/>- Browser<br/>- Mobile App<br/>- curl/Scripts<br/>- Third-party"]
    B["REST Gateway<br/>- Authentication<br/>- Request Trans.<br/>- Response Form.<br/>- Error Handling"]
    C["Cuebot<br/>- Job Mgmt<br/>- Scheduling<br/>- Resources<br/>- Monitoring"]

    A <-->|HTTP/JSON| B
    B <-->|gRPC| C
</div>

## Prerequisites

- Go 1.19 or later
- Access to OpenCue Cuebot gRPC endpoint
- JWT secret for authentication
- Docker (optional, for containerized deployment)

## Installation Methods

### Method 1: Standalone Docker Deployment (Recommended)

**Important:** The REST Gateway is not included in OpenCue's main docker-compose.yml and must be deployed separately.

**Step 1: Start OpenCue Stack**

From the OpenCue repository root:

```bash
# Start core OpenCue services (database, cuebot, rqd)
docker compose up -d

# Check service status
docker compose ps
```

**Step 2: Deploy REST Gateway Separately**

```bash
# Generate JWT secret for REST API authentication
export JWT_SECRET=$(openssl rand -base64 32)

# Build REST Gateway image
cd rest_gateway
docker build -t opencue-rest-gateway .

# Run REST Gateway as separate container
docker run -d --name opencue-rest-gateway \
  --network opencue_default \
  -p 8448:8448 \
  -e CUEBOT_ENDPOINT=cuebot:8443 \
  -e JWT_SECRET="$JWT_SECRET" \
  -e LOG_LEVEL=info \
  opencue-rest-gateway
```

The REST Gateway will be available at `http://localhost:8448` alongside the OpenCue infrastructure.

**Test the deployment:**

```bash
# Install PyJWT for token generation
pip install PyJWT

# Generate a test JWT token
export JWT_TOKEN=$(python3 -c "
import jwt, datetime, os
secret = os.getenv('JWT_SECRET')
payload = {'user': 'test', 'exp': datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=1)}
print(jwt.encode(payload, secret, algorithm='HS256'))
")

# Test service connectivity (expects 401 - confirms service is running)
response=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8448/)
if [ "$response" = "401" ]; then
    echo "Gateway is running and requiring authentication (as expected)"
else
    echo "Gateway may not be running (got HTTP $response)"
fi

# Test API access
curl -H "Authorization: Bearer $JWT_TOKEN" \
     -H "Content-Type: application/json" \
     -X POST \
     "http://localhost:8448/show.ShowInterface/GetShows" \
     -d '{}'
```

### Method 2: Custom Docker Compose File

For production deployments, create a separate Docker Compose file:

Create a REST Gateway compose file:

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
      - CORS_ALLOWED_ORIGINS=https://your-domain.com
      - REST_PORT=8448
    networks:
      - opencue_default
    restart: unless-stopped

networks:
  opencue_default:
    external: true
```

Deploy separately:

```bash
# Start OpenCue stack first
docker compose up -d

# Deploy REST Gateway with separate compose file
export JWT_SECRET=$(openssl rand -base64 32)
docker compose -f rest-gateway-compose.yml up -d
```

Run with Docker:

```bash
docker run -d \
  --name opencue-rest-gateway \
  -p 8448:8448 \
  -e CUEBOT_ENDPOINT=cuebot:8443 \
  -e JWT_SECRET=your-secret-key \
  -e LOG_LEVEL=info \
  opencue-rest-gateway
```

### Method 3: Custom Docker Compose

For custom Docker Compose setups, you can reference the integrated configuration or create your own:

```yaml
version: '3.8'
services:
  rest-gateway:
    build: ./rest_gateway
    ports:
      - "8448:8448"
    environment:
      - CUEBOT_ENDPOINT=cuebot:8443
      - JWT_SECRET=${JWT_SECRET:-dev-secret-key-change-in-production}
      - LOG_LEVEL=${LOG_LEVEL:-info}
      - CORS_ALLOWED_ORIGINS=${CORS_ALLOWED_ORIGINS:-*}
      - REST_PORT=8448
    depends_on:
      - cuebot
    restart: unless-stopped

  cuebot:
    image: opencue/cuebot:latest
    ports:
      - "8443:8443"
    # Add your cuebot configuration
```

Deploy with:

```bash
export JWT_SECRET=$(openssl rand -base64 32)
docker-compose up -d
```

### Method 3: Binary Deployment

Build from source:

```bash
cd rest_gateway/opencue_gateway
go build -o opencue-rest-gateway
```

Create systemd service `/etc/systemd/system/opencue-rest-gateway.service`:

```ini
[Unit]
Description=OpenCue REST Gateway
After=network.target

[Service]
Type=simple
User=opencue
WorkingDirectory=/opt/opencue
ExecStart=/opt/opencue/opencue-rest-gateway
Environment=CUEBOT_ENDPOINT=localhost:8443
Environment=JWT_SECRET=your-secret-key
Environment=LOG_LEVEL=info
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl enable opencue-rest-gateway
sudo systemctl start opencue-rest-gateway
```

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `CUEBOT_ENDPOINT` | `localhost:8443` | Cuebot gRPC endpoint |
| `REST_PORT` | `8448` | HTTP server port |
| `JWT_SECRET` | `dev-secret-key-change-in-production` | JWT signing secret |
| `LOG_LEVEL` | `info` | Logging level (debug, info, warn, error) |
| `CORS_ALLOWED_ORIGINS` | `*` | CORS allowed origins |
| `GRPC_MAX_MESSAGE_SIZE` | `4194304` | Max gRPC message size (4MB) |
| `REQUEST_TIMEOUT` | `30s` | Request timeout duration |
| `SHUTDOWN_TIMEOUT` | `30s` | Graceful shutdown timeout |

### Production Configuration

For production deployments, create a configuration file:

```bash
# /etc/opencue/rest-gateway.env
CUEBOT_ENDPOINT=cuebot.internal:8443
REST_PORT=8448
JWT_SECRET=your-production-secret-key-here
LOG_LEVEL=warn
CORS_ALLOWED_ORIGINS=https://your-domain.com,https://cueweb.internal
GRPC_MAX_MESSAGE_SIZE=8388608
REQUEST_TIMEOUT=60s
SHUTDOWN_TIMEOUT=30s
```

## Security Configuration

### JWT Authentication

Generate a secure JWT secret:

```bash
openssl rand -base64 32
```

Create JWT tokens for clients:

```python
import jwt
import datetime

secret = "your-production-secret-key-here"
payload = {
    "user": "api-client",
    "exp": datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=24)
}
token = jwt.encode(payload, secret, algorithm="HS256")
print(token)
```

### TLS/HTTPS Setup

For production, use a reverse proxy like NGINX:

```nginx
server {
    listen 443 ssl http2;
    server_name api.your-domain.com;
    
    ssl_certificate /path/to/certificate.crt;
    ssl_certificate_key /path/to/private.key;
    
    location / {
        proxy_pass http://localhost:8448;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### CORS Configuration

Configure CORS for web applications:

```bash
export CORS_ALLOWED_ORIGINS="https://cueweb.your-domain.com,https://your-app.com"
```

## High Availability Deployment

### Load Balancer Setup

Use HAProxy for load balancing multiple gateway instances:

```
backend opencue_rest_gateways
    mode http
    balance roundrobin
    option httpchk GET /
    # Note: Expects 401 response - this confirms service is running
    server gateway1 10.0.1.10:8448 check
    server gateway2 10.0.1.11:8448 check
    server gateway3 10.0.1.12:8448 check

frontend opencue_api
    bind *:443 ssl crt /path/to/certificate.pem
    default_backend opencue_rest_gateways
```

### Kubernetes Deployment

Create Kubernetes manifests:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: opencue-rest-gateway
spec:
  replicas: 3
  selector:
    matchLabels:
      app: opencue-rest-gateway
  template:
    metadata:
      labels:
        app: opencue-rest-gateway
    spec:
      containers:
      - name: rest-gateway
        image: opencue-rest-gateway:latest
        ports:
        - containerPort: 8448
        env:
        - name: CUEBOT_ENDPOINT
          value: "cuebot-service:8443"
        - name: JWT_SECRET
          valueFrom:
            secretKeyRef:
              name: opencue-secrets
              key: jwt-secret
        resources:
          requests:
            memory: "64Mi"
            cpu: "100m"
          limits:
            memory: "256Mi"
            cpu: "500m"
---
apiVersion: v1
kind: Service
metadata:
  name: opencue-rest-gateway
spec:
  selector:
    app: opencue-rest-gateway
  ports:
  - port: 8448
    targetPort: 8448
  type: ClusterIP
```

## Monitoring and Health Checks

### Service Health Monitoring

**Important:** The OpenCue REST Gateway requires JWT authentication for ALL endpoints - there are no public health endpoints.

For health monitoring, use these approaches:

```bash
# TCP connectivity check (recommended for load balancers)
timeout 5 bash -c '</dev/tcp/localhost/8448' && echo "Service is up"

# HTTP status check (expects 401 - confirms service is running)
response=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8448/)
if [ "$response" = "401" ]; then
    echo "✓ Gateway is running and requiring authentication (as expected)"
else
    echo "✗ Gateway may not be running (got HTTP $response)"
fi
```

### Monitoring with Prometheus

Add monitoring labels to your Kubernetes deployment:

```yaml
metadata:
  annotations:
    prometheus.io/scrape: "true"
    prometheus.io/port: "8448"
    prometheus.io/path: "/metrics"
```

### Log Aggregation

Configure log collection with Fluentd or similar:

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: fluentd-config
data:
  fluent.conf: |
    <source>
      @type tail
      path /var/log/containers/opencue-rest-gateway*.log
      pos_file /var/log/fluentd-opencue-gateway.log.pos
      tag kubernetes.opencue.gateway
      format json
    </source>
```

## Performance Tuning

### Connection Pool Settings

Optimize gRPC connection settings:

```bash
export GRPC_MAX_MESSAGE_SIZE=8388608  # 8MB
export GRPC_KEEPALIVE_TIME=30s
export GRPC_KEEPALIVE_TIMEOUT=5s
```

### Resource Limits

Set appropriate resource limits:

```yaml
resources:
  requests:
    memory: "128Mi"
    cpu: "200m"
  limits:
    memory: "512Mi"
    cpu: "1000m"
```

## Testing Deployment

### Basic Connectivity Test

```bash
# Test service connectivity (expects 401 - confirms service is running)
response=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8448/)
if [ "$response" = "401" ]; then
    echo "✓ Gateway is running and requiring authentication (as expected)"
else
    echo "✗ Gateway may not be running (got HTTP $response)"
fi

# Test with JWT authentication
export JWT_TOKEN="your-jwt-token-here"
curl -H "Authorization: Bearer $JWT_TOKEN" \
     -H "Content-Type: application/json" \
     -X POST \
     "http://localhost:8448/show.ShowInterface/GetShows" \
     -d '{}'
```

### Load Testing

Use Apache Bench for load testing:

```bash
# Create test request file
echo '{}' > test_request.json

# Run load test
ab -n 1000 -c 10 -T application/json -p test_request.json \
   -H "Authorization: Bearer $JWT_TOKEN" \
   http://localhost:8448/show.ShowInterface/GetShows
```

## Troubleshooting

### Common Issues

**Connection refused to Cuebot:**
```bash
# Check Cuebot connectivity
telnet cuebot-host 8443

# Verify gRPC endpoint
grpc_health_probe -addr=cuebot-host:8443
```

**JWT authentication failures:**
```bash
# Verify JWT secret matches
echo $JWT_SECRET

# Test token generation
python3 -c "import jwt; print(jwt.encode({'user': 'test'}, 'your-secret', algorithm='HS256'))"
```

**High memory usage:**
```bash
# Monitor memory usage
docker stats opencue-rest-gateway

# Check for memory leaks
go tool pprof http://localhost:8448/debug/pprof/heap
```

### Debug Mode

Enable debug logging:

```bash
export LOG_LEVEL=debug
```

## Security Best Practices

1. **Use strong JWT secrets** (32+ random characters)
2. **Enable HTTPS** in production
3. **Restrict CORS origins** to known domains
4. **Implement rate limiting** at the load balancer
5. **Regular security updates** for base images
6. **Network segmentation** between gateway and Cuebot
7. **Monitor for suspicious activity**

## What's next?

- [Using the REST API](/docs/user-guides/using-rest-api/) - Client usage examples
- [REST API Reference](/docs/reference/rest-api-reference/) - Complete API documentation
- [Monitoring with Prometheus](/docs/other-guides/monitoring-with-prometheus-loki-and-grafana/) - Add gateway metrics
