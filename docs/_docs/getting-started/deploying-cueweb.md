---
layout: default
title: Deploying CueWeb
parent: Getting Started
nav_order: 27
---

# Deploying CueWeb
{: .no_toc }

Deploy and configure CueWeb for production use in your OpenCue render farm.

<details open markdown="block">
  <summary>
    Table of contents
  </summary>
  {: .text-delta }
1. TOC
{:toc}
</details>

---

## Overview

CueWeb is a web-based interface for OpenCue that provides job management, monitoring, and control capabilities through a browser. This guide covers production deployment options for CueWeb.

### Prerequisites

Before deploying CueWeb, ensure you have:

- **OpenCue REST Gateway** deployed and accessible
- **Node.js** (version 18 or later) for building from source
- **Docker** (recommended for production deployment)
- **Web server** (Nginx, Apache) for reverse proxy (optional)
- **SSL certificates** for HTTPS (recommended)

---

## Quick Deployment with Docker

### Build CueWeb Image

```bash
# Navigate to CueWeb directory
cd cueweb

# Build Docker image
docker build -t cueweb:latest .
```

### Run CueWeb Container

```bash
# Run CueWeb with basic configuration
docker run -d \
  --name cueweb \
  -p 3000:3000 \
  -e NEXT_PUBLIC_OPENCUE_ENDPOINT=http://your-rest-gateway:8448 \
  -e NEXT_PUBLIC_URL=http://your-server:3000 \
  -e NEXT_JWT_SECRET=your-jwt-secret \
  cueweb:latest
```

### Verify Deployment

```bash
# Check container status
docker ps | grep cueweb

# View logs
docker logs cueweb

# Test accessibility
curl http://localhost:3000
```

---

## Production Deployment

### Environment Configuration

Create a production environment file:

```bash
# .env.production
NEXT_PUBLIC_OPENCUE_ENDPOINT=https://api.renderfarm.company.com
NEXT_PUBLIC_URL=https://cueweb.company.com
NEXT_JWT_SECRET=very-long-secure-jwt-secret-key

# Production settings
NODE_ENV=production
NEXT_TELEMETRY_DISABLED=1

# Authentication (optional)
NEXT_PUBLIC_AUTH_PROVIDER=okta,google
NEXTAUTH_URL=https://cueweb.company.com
NEXTAUTH_SECRET=nextauth-production-secret

# OAuth providers
OKTA_CLIENT_ID=your-okta-client-id
OKTA_CLIENT_SECRET=your-okta-client-secret
OKTA_ISSUER=https://company.okta.com

GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret

# Monitoring (optional)
SENTRY_DSN=https://your-sentry-dsn
SENTRY_ENVIRONMENT=production
```

### Docker Compose Deployment

```yaml
# docker-compose.yml
version: '3.8'

services:
  cueweb:
    build: .
    ports:
      - "3000:3000"
    env_file:
      - .env.production
    restart: unless-stopped
    depends_on:
      - rest-gateway
    networks:
      - opencue
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:3000/api/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  rest-gateway:
    image: opencue-rest-gateway:latest
    ports:
      - "8448:8448"
    environment:
      - CUEBOT_ENDPOINT=cuebot:8443
      - JWT_SECRET=${JWT_SECRET}
    networks:
      - opencue

networks:
  opencue:
    external: true
```

### Building from Source

For environments where Docker is not available:

```bash
# Install Node.js dependencies
npm install

# Build production bundle
npm run build

# Start production server
npm run start

# Or use PM2 for process management
npm install -g pm2
pm2 start npm --name "cueweb" -- start
pm2 save
pm2 startup
```

---

## Kubernetes Deployment

### Deployment Manifest

```yaml
# k8s/cueweb-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: cueweb
  namespace: opencue
  labels:
    app: cueweb
    version: v1
spec:
  replicas: 3
  selector:
    matchLabels:
      app: cueweb
  template:
    metadata:
      labels:
        app: cueweb
        version: v1
    spec:
      containers:
      - name: cueweb
        image: cueweb:latest
        ports:
        - containerPort: 3000
          name: http
        env:
        - name: NEXT_PUBLIC_OPENCUE_ENDPOINT
          value: "http://rest-gateway:8448"
        - name: NEXT_PUBLIC_URL
          value: "https://cueweb.company.com"
        - name: NEXT_JWT_SECRET
          valueFrom:
            secretKeyRef:
              name: cueweb-secrets
              key: jwt-secret
        - name: NEXTAUTH_SECRET
          valueFrom:
            secretKeyRef:
              name: cueweb-secrets
              key: nextauth-secret
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
        livenessProbe:
          httpGet:
            path: /api/health
            port: 3000
          initialDelaySeconds: 30
          periodSeconds: 10
          timeoutSeconds: 5
          failureThreshold: 3
        readinessProbe:
          httpGet:
            path: /api/health
            port: 3000
          initialDelaySeconds: 5
          periodSeconds: 5
          timeoutSeconds: 3
          failureThreshold: 3
        securityContext:
          runAsNonRoot: true
          runAsUser: 1001
          allowPrivilegeEscalation: false
          readOnlyRootFilesystem: true
        volumeMounts:
        - name: tmp
          mountPath: /tmp
        - name: nextjs-cache
          mountPath: /.next
      volumes:
      - name: tmp
        emptyDir: {}
      - name: nextjs-cache
        emptyDir: {}
      securityContext:
        fsGroup: 1001

---
apiVersion: v1
kind: Service
metadata:
  name: cueweb
  namespace: opencue
  labels:
    app: cueweb
spec:
  type: ClusterIP
  ports:
  - port: 3000
    targetPort: 3000
    protocol: TCP
    name: http
  selector:
    app: cueweb

---
apiVersion: v1
kind: Secret
metadata:
  name: cueweb-secrets
  namespace: opencue
type: Opaque
data:
  jwt-secret: <base64-encoded-jwt-secret>
  nextauth-secret: <base64-encoded-nextauth-secret>
  okta-client-secret: <base64-encoded-okta-secret>
  google-client-secret: <base64-encoded-google-secret>
```

### Ingress Configuration

```yaml
# k8s/cueweb-ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: cueweb
  namespace: opencue
  annotations:
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
    nginx.ingress.kubernetes.io/force-ssl-redirect: "true"
    cert-manager.io/cluster-issuer: "letsencrypt-prod"
spec:
  tls:
  - hosts:
    - cueweb.company.com
    secretName: cueweb-tls
  rules:
  - host: cueweb.company.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: cueweb
            port:
              number: 3000
```

---

## Authentication Setup

### OAuth Provider Configuration

#### Google OAuth Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create or select a project
3. Enable Google+ API
4. Create OAuth 2.0 credentials
5. Add authorized redirect URIs:
   - `https://cueweb.company.com/api/auth/callback/google`

#### Okta Setup

1. Log in to your Okta admin console
2. Go to Applications > Create App Integration
3. Select OIDC - OpenID Connect
4. Choose Web Application
5. Configure redirect URIs:
   - `https://cueweb.company.com/api/auth/callback/okta`

#### GitHub Setup (Optional)

1. Go to GitHub Settings > Developer settings > OAuth Apps
2. Create a new OAuth App
3. Set Authorization callback URL:
   - `https://cueweb.company.com/api/auth/callback/github`

### Disable Authentication (Development)

For development or internal deployments without authentication:

```bash
# In .env file, comment out or remove:
# NEXT_PUBLIC_AUTH_PROVIDER=okta,google

# CueWeb will run without authentication requirements
```

---

## Reverse Proxy Configuration

### Nginx Configuration

```nginx
# /etc/nginx/sites-available/cueweb
server {
    listen 80;
    server_name cueweb.company.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name cueweb.company.com;

    ssl_certificate /path/to/ssl/certificate.crt;
    ssl_certificate_key /path/to/ssl/private.key;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512;

    location / {
        proxy_pass http://localhost:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
    }

    # Static assets caching
    location /_next/static/ {
        proxy_pass http://localhost:3000;
        add_header Cache-Control "public, max-age=31536000, immutable";
    }

    # Health check endpoint
    location /api/health {
        proxy_pass http://localhost:3000;
        access_log off;
    }
}
```

### Apache Configuration

```apache
# /etc/apache2/sites-available/cueweb.conf
<VirtualHost *:80>
    ServerName cueweb.company.com
    Redirect permanent / https://cueweb.company.com/
</VirtualHost>

<VirtualHost *:443>
    ServerName cueweb.company.com

    SSLEngine on
    SSLCertificateFile /path/to/ssl/certificate.crt
    SSLCertificateKeyFile /path/to/ssl/private.key

    ProxyPreserveHost On
    ProxyRequests Off

    ProxyPass / http://localhost:3000/
    ProxyPassReverse / http://localhost:3000/

    # WebSocket support
    ProxyPass /api/ws ws://localhost:3000/api/ws
    ProxyPassReverse /api/ws ws://localhost:3000/api/ws

    # Headers for proper forwarding
    ProxyPassReverse / http://localhost:3000/
    ProxyPassReverseRewrite Off

    Header always set X-Frame-Options DENY
    Header always set X-Content-Type-Options nosniff
</VirtualHost>
```

---

## High Availability Setup

### Load Balancer Configuration

```yaml
# k8s/cueweb-hpa.yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: cueweb-hpa
  namespace: opencue
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: cueweb
  minReplicas: 3
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
  behavior:
    scaleDown:
      stabilizationWindowSeconds: 300
      policies:
      - type: Percent
        value: 50
        periodSeconds: 60
    scaleUp:
      stabilizationWindowSeconds: 0
      policies:
      - type: Percent
        value: 100
        periodSeconds: 15
```

### Session Affinity (if needed)

```yaml
# Add to service configuration
apiVersion: v1
kind: Service
metadata:
  name: cueweb
spec:
  sessionAffinity: ClientIP
  sessionAffinityConfig:
    clientIP:
      timeoutSeconds: 10800  # 3 hours
```

---

## Monitoring and Logging

### Health Checks

CueWeb provides health check endpoints:

```bash
# Basic health check
curl https://cueweb.company.com/api/health

# Detailed health status
curl https://cueweb.company.com/api/health/detailed
```

### Prometheus Metrics

Enable metrics collection:

```javascript
// next.config.js
module.exports = {
  experimental: {
    instrumentationHook: true,
  },
  // Other config...
}
```

### Sentry Integration

Configure error tracking:

```bash
# Environment variables
SENTRY_DSN=https://your-sentry-dsn
SENTRY_ENVIRONMENT=production
SENTRY_RELEASE=1.0.0
```

### Log Aggregation

```yaml
# k8s/cueweb-logging.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: fluent-bit-config
data:
  fluent-bit.conf: |
    [INPUT]
        Name tail
        Path /var/log/containers/*cueweb*.log
        Tag cueweb.*

    [OUTPUT]
        Name es
        Match cueweb.*
        Host elasticsearch
        Port 9200
        Index cueweb-logs
```

---

## Security Considerations

### Security Headers

```javascript
// next.config.js
module.exports = {
  async headers() {
    return [
      {
        source: '/(.*)',
        headers: [
          {
            key: 'X-Frame-Options',
            value: 'DENY'
          },
          {
            key: 'X-Content-Type-Options',
            value: 'nosniff'
          },
          {
            key: 'Referrer-Policy',
            value: 'strict-origin-when-cross-origin'
          },
          {
            key: 'Strict-Transport-Security',
            value: 'max-age=31536000; includeSubDomains'
          }
        ]
      }
    ]
  }
}
```

### Secret Management

Use secure secret storage:

```bash
# Kubernetes secrets
kubectl create secret generic cueweb-secrets \
  --from-literal=jwt-secret=your-jwt-secret \
  --from-literal=nextauth-secret=your-nextauth-secret

# Docker secrets
echo "your-jwt-secret" | docker secret create jwt_secret -
```

### Network Security

- Use HTTPS/TLS for all connections
- Implement proper firewall rules
- Restrict access to management ports
- Use network policies in Kubernetes

---

## Troubleshooting

### Common Issues

#### 502 Bad Gateway
- Check if CueWeb container is running
- Verify port configuration
- Check REST Gateway connectivity

#### Authentication Loops
- Verify OAuth configuration
- Check NEXTAUTH_URL setting
- Confirm callback URLs match

#### Performance Issues
- Monitor memory usage
- Check CPU utilization
- Review database connection pool
- Implement caching strategies

### Debug Mode

```bash
# Enable debug logging
DEBUG=cueweb:* npm start

# Docker debug mode
docker run -e DEBUG=cueweb:* cueweb:latest
```

### Log Analysis

```bash
# Container logs
docker logs cueweb

# Kubernetes logs
kubectl logs -f deployment/cueweb -n opencue

# Follow logs with specific labels
kubectl logs -f -l app=cueweb -n opencue
```

---

## Maintenance

### Updates

```bash
# Update CueWeb
git pull origin master
npm install
npm run build
docker build -t cueweb:latest .

# Rolling update in Kubernetes
kubectl set image deployment/cueweb cueweb=cueweb:latest -n opencue
```

### Backup

Important data to backup:
- Environment configuration files
- SSL certificates
- OAuth application settings
- Custom configuration files

### Performance Monitoring

Monitor these metrics:
- Response times
- Memory usage
- CPU utilization
- Active connections
- Error rates

---

## Next Steps

After deploying CueWeb:

1. **Configure Authentication**: Set up OAuth providers for user access
2. **Train Users**: Provide training on the web interface
3. **Monitor Performance**: Set up monitoring and alerting
4. **Customize Interface**: Adapt UI for your workflow needs
5. **Integration**: Connect with existing pipeline tools

For detailed usage instructions, see the [CueWeb User Guide](/docs/user-guides/cueweb-user-guide).

For development and customization, see the [CueWeb Developer Guide](/docs/developer-guide/cueweb-development).