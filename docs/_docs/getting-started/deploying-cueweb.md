---
layout: default
title: Deploying CueWeb
parent: Getting Started
nav_order: 31
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
# Leave empty if the UI and the API are served from the same origin
# (the common case): the client will build same-origin relative URLs
# and CueWeb works correctly when accessed from any host. Only set
# this to an absolute URL when the API really lives on a different
# origin than the UI.
NEXT_PUBLIC_URL=
NEXT_JWT_SECRET=very-long-secure-jwt-secret-key

# Production settings
NODE_ENV=production
NEXT_TELEMETRY_DISABLED=1

# Authentication (optional)
# Comma-separated list of providers to enable on the /login page.
# Supported values: local, okta, google, github, ldap.
# When empty, CueWeb runs unauthenticated (sandbox mode) and the
# RBAC enforcement layer short-circuits to "allow", matching the
# pre-RBAC behavior.
# IMPORTANT: NEXT_PUBLIC_* vars must match between build-arg and runtime.
NEXT_PUBLIC_AUTH_PROVIDER=local,okta,google,github,ldap
NEXTAUTH_URL=https://cueweb.company.com
NEXTAUTH_SECRET=nextauth-production-secret

# RBAC (optional, only relevant when auth is enabled)
# Active groups resolver. One of: okta | ldap | none.
# - okta: read the `groups` claim from the Okta ID token (requires the
#         Okta app to be configured to include the claim)
# - ldap: query memberOf on the user's DN via ldapjs after sign-in
# - none: no external sync; admins assign roles directly in /admin
CUEWEB_GROUPS_RESOLVER=okta

# Override the SQLite policy-store path (default: /data/cueweb-rbac.db).
# CUEWEB_RBAC_DB=/data/cueweb-rbac.db

# Optional LDAP service account for the memberOf lookup. If unset,
# the resolver tries an anonymous bind and silently skips the lookup
# if anonymous search is disallowed.
# LDAP_SEARCH_USER_DN=cn=cueweb-svc,ou=Services,dc=example,dc=com
# LDAP_SEARCH_USER_PASSWORD=...

# Cuebot Facility selector (optional)
# Comma-separated list of facilities exposed in the header / sidebar
# "Cuebot Facility" menu. Defaults to local,dev,cloud,external if unset.
# (The selected value is persisted client-side; per-facility gateway
# routing is implemented in a separate page-level change.)
# NEXT_PUBLIC_CUEBOT_FACILITIES=local,dev,cloud,external

# Help menu URLs (optional)
# Defaults mirror CueGUI's cuegui.yaml exactly. Override these to point
# internal docs / suggestions / bug trackers at your own systems.
# NEXT_PUBLIC_DOCS_URL=https://www.opencue.io/docs/
# NEXT_PUBLIC_SUGGESTIONS_URL=https://github.com/AcademySoftwareFoundation/OpenCue/issues/new?labels=enhancement&template=enhancement.md
# NEXT_PUBLIC_BUGS_URL=https://github.com/AcademySoftwareFoundation/OpenCue/issues/new?labels=bug&template=bug_report.md

# Build version shown in the bottom status bar (optional).
# Falls back to the `version` field in cueweb/package.json when unset.
# In CI you typically pass the short Git SHA or a release tag via
# `docker build --build-arg NEXT_PUBLIC_APP_VERSION=$(git rev-parse --short HEAD)`.
# NEXT_PUBLIC_APP_VERSION=1.19.1

# Optional deep-link template for the Frame context menu's
# "View Log on <editor>" item. The literal {path} is substituted at
# click time with the absolute rqlog path. Empty hides the menu item
# entirely. Browser sandboxing prevents reading $EDITOR / spawning
# subprocesses, so the custom URL scheme is the web-native equivalent
# of cuegui.Utils.popupView's editor launcher. Common values:
#   vscode://file{path}
#   vscode-insiders://file{path}
#   subl://open?url=file://{path}
#   txmt://open?url=file://{path}
#   idea://open?file={path}
# This MUST be passed as a Docker build arg (the value is inlined into
# the client bundle at build time):
#   docker build --build-arg NEXT_PUBLIC_LOG_EDITOR_URL='vscode://file{path}' ...
# NEXT_PUBLIC_LOG_EDITOR_URL=vscode://file{path}

# OAuth providers
OKTA_CLIENT_ID=your-okta-client-id
OKTA_CLIENT_SECRET=your-okta-client-secret
OKTA_ISSUER=https://company.okta.com

GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret

# LDAP Configuration (optional)
LDAP_URI=ldaps://ldap.company.com:636
LDAP_LOGIN_DN=uid={login},cn=users,cn=accounts,dc=company,dc=com
LDAP_CERTIFICATE=/etc/ssl/certs/ldap-ca.crt

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
    volumes:
      # Persist the RBAC SQLite store across container restarts so the
      # bootstrap admin and all later user/group/role rows survive.
      - cueweb-data:/data
    restart: unless-stopped
    depends_on:
      - rest-gateway
    networks:
      - opencue
    healthcheck:
      test: ["CMD", "wget", "--spider", "-q", "http://localhost:3000"]
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

volumes:
  cueweb-data:
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
        # RBAC SQLite store. Use a PersistentVolumeClaim so the policy
        # store survives pod restarts and rescheduling.
        - name: cueweb-data
          mountPath: /data
      volumes:
      - name: tmp
        emptyDir: {}
      - name: nextjs-cache
        emptyDir: {}
      - name: cueweb-data
        persistentVolumeClaim:
          claimName: cueweb-data
      securityContext:
        fsGroup: 1001

---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: cueweb-data
  namespace: opencue
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 1Gi

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

#### LDAP Setup (Optional)

LDAP authentication allows users to authenticate using their company directory credentials. This is useful for intranet deployments where OAuth providers may not be available.

![CueWeb LDAP login button](/assets/images/cueweb/cueweb-ldap-button.png)

![CueWeb LDAP login page](/assets/images/cueweb/cueweb-ldap-login-password-page.png)

1. Configure the LDAP environment variables:
   ```bash
   # LDAP server URI (use ldaps:// for TLS)
   LDAP_URI=ldaps://ldap.company.com:636

   # Distinguished Name template ({login} will be replaced with username)
   LDAP_LOGIN_DN=uid={login},cn=users,cn=accounts,dc=company,dc=com

   # Path to CA certificate for TLS verification (optional)
   LDAP_CERTIFICATE=/etc/ssl/certs/ldap-ca.crt
   ```

2. Add `ldap` to `NEXT_PUBLIC_AUTH_PROVIDER`:
   ```bash
   NEXT_PUBLIC_AUTH_PROVIDER=google,okta,ldap
   ```

3. For Docker deployments, mount the CA certificate:
   ```bash
   docker run -v /path/to/ca.crt:/etc/ssl/certs/ldap-ca.crt:ro ...
   ```

**Security Notes:**
- Always use `ldaps://` (LDAP over TLS) in production
- Provide a CA certificate for proper TLS verification
- The `{login}` placeholder in `LDAP_LOGIN_DN` is replaced with the username at authentication time

### Local credentials provider (built-in)

The `local` provider is built into CueWeb - no external IdP needed. Useful for air-gapped or single-operator deployments.

1. Set `NEXT_PUBLIC_AUTH_PROVIDER=local` (or combine with `okta` / `google` / `github` / `ldap`).
2. Mount a persistent volume at `/data` (e.g. `cueweb-data:/data` in `docker-compose.yml`). The SQLite policy store lives there.
3. Start CueWeb. On first launch with `local` in the provider list, the container log prints a one-time bootstrap admin banner. Capture it with `docker compose logs cueweb --tail 20`.
4. Sign in at `/login` as `admin` with that password. CueWeb forces a password change before the dashboard.

To reset the bootstrap password (e.g. lost the original):

```bash
docker compose down cueweb
docker volume rm <stack>_cueweb-data
docker compose up -d cueweb && docker compose logs cueweb --tail 20
```

This regenerates the whole policy store - **all users, groups, roles, and the audit log are erased**. Export the audit log to CSV from the Admin UI's **Audit log** tab beforehand if you need to keep it.

> **Warning:** `docker volume rm <stack>_cueweb-data` is **destructive and irreversible**. It removes every persisted RBAC row - local users, groups, custom roles, group/role attachments, the admin whitelist, and the entire audit log. Externally sourced identities (Okta / LDAP / Google / GitHub) reappear on the next sign-in but any direct role grants on them are lost, which can lock out admins who relied on direct grants. **Do not run this in production unless you have a tested backup-and-restore plan** - see the "Persistent volumes" section below for a `tar` recipe.

### Disable Authentication (Development)

For development or internal deployments without authentication:

```bash
# In .env file, set the var to an empty string:
NEXT_PUBLIC_AUTH_PROVIDER=
```

CueWeb runs unauthenticated and the RBAC enforcement short-circuits to "allow" so the new code paths don't add anything visible. The `/admin` link in the header is hidden in this mode.

---

## RBAC and Admin UI

When any provider is enabled, CueWeb activates a Role-Based Access Control layer. Highlights for operators:

- **Storage**: SQLite at `/data/cueweb-rbac.db` (override with `CUEWEB_RBAC_DB`). Mount a persistent volume to survive restarts.
- **First-launch flow**: with `local` enabled, CueWeb auto-creates an `admin` user, generates a 24-char random password, prints it once to the container log, and writes it to `/data/.cueweb-bootstrap` (mode `0600`).
- **Admin UI**: reachable at `/admin` to anyone in the `admins` whitelist. Tabs cover Users, Groups, Roles, Permissions, Admins, and an Audit log (with CSV export).
- **Groups resolver**: optional - set `CUEWEB_GROUPS_RESOLVER=okta` or `=ldap` to sync external group membership into CueWeb on every sign-in. Default `none`.
- **Built-in roles**: `site-admin` (wildcard, undeletable), `operator` (day-to-day verbs + CueCommander), `viewer` (read-only). Add custom roles in the Admin UI.

See the [CueWeb reference doc](/docs/reference/cueweb/#rbac-and-admin-ui) for the full permission catalog and the [user guide](/docs/user-guides/cueweb-user-guide/#admin-ui) for the per-tab tour.

---

## CueSubmit (browser-based job submission)

The `/cuesubmit` route is a TypeScript port of the standalone CueSubmit CLI tool. It reuses the same REST gateway + cuebot path as the rest of CueWeb, so no extra services or env vars are needed.

**Submit path**:
1. Browser POSTs the form payload to `/api/job/submit` (the Next.js Node route).
2. The route validates with zod, builds the OpenCue cjsl XML job spec server-side (same format pyoutline emits), and forwards it to `job.JobInterface/LaunchSpecAndWait` on the REST gateway.
3. Cuebot creates the job and returns the resolved `JobSeq`. CueWeb redirects the browser to `/jobs/<name>` so the user can watch frames dispatch live.

**Sandbox-tuned defaults**: the form chooses values that produce a runnable job against the seeded sandbox out of the box:

- **Memory** default `256m`. The seeded `default` service has a 3.2 GB minimum which most sandbox RQDs can't satisfy; without a smaller request, trivial test jobs sit in WAITING forever.
- **Facility** default `local` (when the user picks `[Default]` in the form). Cuebot's internal fallback is `cloud`, which doesn't match the seeded sandbox RQD's `local.general` allocation.
- **Per-user deterministic UID** in the range 1000-65000. Cuebot rejects `uid=0` with `Cannot launch jobs as root`, so CueWeb never emits zero.

**Production deployments**: change Memory to whatever the real services expect, override Facility from the dropdown if your deployment has more than one, and confirm `NEXT_PUBLIC_CUEBOT_FACILITIES` enumerates every facility the user should be able to pick.

The form auto-saves a draft to `localStorage` on every keystroke and keeps per-field autocomplete history (Job Name / Shot / Layer Name) - these are browser-local and don't require any server-side persistence.

### Persistent volumes

The Docker image declares `/data` as a volume; pair it with a named volume so the policy store survives container restarts and `docker compose down`:

```yaml
# docker-compose.yml (excerpt)
services:
  cueweb:
    # ...
    volumes:
      - cueweb-data:/data
volumes:
  cueweb-data:
```

Backups: `docker run --rm -v <stack>_cueweb-data:/data -v $(pwd):/backup alpine tar czf /backup/cueweb-data-$(date +%F).tgz -C /data .` copies the SQLite store and the bootstrap credentials file to a tarball. Restore with the inverse.

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