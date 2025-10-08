---
title: "CueWeb and REST Gateway"
nav_order: 15
parent: Concepts
layout: default
linkTitle: "CueWeb and REST Gateway"
date: 2024-09-17
description: >
  Understanding CueWeb and the OpenCue REST Gateway architecture
---

# CueWeb and REST Gateway
{: .no_toc }

Learn about CueWeb's web-based interface and the REST Gateway that enables HTTP communication with OpenCue.

<details open markdown="block">
  <summary>
    Table of contents
  </summary>
  {: .text-delta }
1. TOC
{:toc}
</details>

---

## What is CueWeb?

CueWeb is a web-based application that brings the core functionality of CueGUI to your browser. Built with Next.js and React, CueWeb provides a responsive, accessible interface for managing OpenCue render farms from anywhere on the network.

### Key Features

- **Job Management Dashboard**: View, filter, and manage rendering jobs
- **Real-time Updates**: Automatic refresh of job, layer, and frame status
- **Advanced Search**: Regex-enabled search with dropdown suggestions
- **Frame Navigation**: Detailed frame inspection with log viewing
- **Multi-job Operations**: Bulk operations on multiple jobs
- **Dark/Light Mode**: Theme switching for user preference
- **Responsive Design**: Works on desktop, tablet, and mobile devices
- **Authentication Support**: Optional OAuth integration (GitHub, Google, Okta)

### CueWeb vs CueGUI

| Feature | CueGUI | CueWeb |
|---------|---------|---------|
| **Platform** | Desktop application | Web browser |
| **Installation** | Requires Python/Qt setup | No client installation |
| **Access** | Local workstation only | Network accessible |
| **Updates** | Manual client updates | Automatic via web |
| **Mobile Support** | No | Yes (responsive design) |
| **Multi-user** | Individual instances | Shared web service |
| **Authentication** | System-based | OAuth providers |

---

## What is the OpenCue REST Gateway?

The OpenCue REST Gateway is a production-ready HTTP service that provides RESTful endpoints for OpenCue's gRPC API. It acts as a translation layer, converting HTTP requests to gRPC calls and responses back to JSON.

### Architecture Overview

<div class="mermaid">
graph LR
    A["Web Client<br/>- CueWeb<br/>- Mobile App<br/>- curl/Scripts<br/>- Third-party"]
    B["REST Gateway<br/>- Authentication<br/>- Request Trans.<br/>- Response Form.<br/>- Error Handling"]
    C["Cuebot<br/>- Job Mgmt<br/>- Scheduling<br/>- Resources<br/>- Monitoring"]

    A <-->|HTTP/JSON| B
    B <-->|gRPC| C
</div>

### Request Flow

1. **HTTP Request**: Client sends HTTP POST with JSON payload and JWT token
2. **Authentication**: Gateway validates JWT token signature and expiration
3. **gRPC Translation**: HTTP request converted to gRPC call
4. **Cuebot Communication**: Request forwarded to Cuebot service
5. **Response Translation**: gRPC response converted back to JSON
6. **HTTP Response**: Formatted JSON returned to client

---

## Authentication and Security

### JWT Token System

Both CueWeb and the REST Gateway use JSON Web Tokens (JWT) for secure authentication:

- **Algorithm**: HMAC SHA256 (HS256)
- **Header Format**: `Authorization: Bearer <token>`
- **Expiration**: Configurable token lifetime
- **Secret Sharing**: Same secret used by both CueWeb and REST Gateway

### Token Lifecycle

<div class="mermaid">
sequenceDiagram
    participant U as User
    participant C as CueWeb
    participant G as Gateway
    participant B as Cuebot

    U->>C: 1. Login/Access
    C->>G: 2. Generate JWT Token
    C->>G: 3. API Request + JWT
    G->>B: 4. Validate JWT
    G->>B: 5. gRPC Call
    B->>G: 6. gRPC Response
    G->>C: 7. JSON Response
    C->>U: 8. Updated UI
</div>

### Security Features

- **No API Keys**: JWT tokens eliminate need for permanent credentials
- **Token Expiration**: Automatic token expiry prevents unauthorized access
- **Request Validation**: All requests validated before processing
- **CORS Support**: Configurable cross-origin resource sharing
- **TLS Support**: Optional HTTPS encryption

---

## Deployment Patterns

### Standalone Deployment

CueWeb and REST Gateway run as separate services:

<div class="mermaid">
graph LR
    A["CueWeb<br/>Port: 3000"] --> B["REST Gateway<br/>Port: 8448"]
    B --> C["Cuebot<br/>Port: 8443"]
</div>

### Container Deployment

Using Docker containers for isolation and scalability:

```yaml
services:
  cueweb:
    image: cueweb:latest
    ports: ["3000:3000"]
    environment:
      - NEXT_PUBLIC_OPENCUE_ENDPOINT=http://rest-gateway:8448

  rest-gateway:
    image: opencue-rest-gateway:latest
    ports: ["8448:8448"]
    environment:
      - CUEBOT_ENDPOINT=cuebot:8443
      - JWT_SECRET=${JWT_SECRET}
```

### High Availability Setup

Load-balanced deployment for production environments:

<div class="mermaid">
graph TD
    LB["Load Balancer"]

    LB --> CW1["CueWeb #1"]
    LB --> CW2["CueWeb #2"]
    LB --> CW3["CueWeb #3"]

    CW1 --> RG["REST Gateway<br/>(Clustered)"]
    CW2 --> RG
    CW3 --> RG

    RG --> CB["Cuebot<br/>(Clustered)"]
</div>

---

## Data Flow and API Coverage

### Supported Interfaces

The REST Gateway exposes all OpenCue gRPC interfaces:

#### Core Interfaces

| Interface | Description | Example Endpoints |
|-----------|-------------|-------------------|
| **ShowInterface** | Project management | `GetShows`, `FindShow`, `CreateShow` |
| **JobInterface** | Job lifecycle | `GetJobs`, `Kill`, `Pause`, `Resume` |
| **FrameInterface** | Frame operations | `GetFrame`, `Retry`, `Kill`, `Eat` |
| **LayerInterface** | Layer management | `GetLayer`, `GetFrames`, `Kill` |
| **GroupInterface** | Resource groups | `GetGroup`, `SetMinCores`, `SetMaxCores` |
| **HostInterface** | Host management | `GetHosts`, `Lock`, `Unlock`, `AddTags` |
| **OwnerInterface** | Resource ownership | `GetOwner`, `TakeOwnership` |
| **ProcInterface** | Process control | `GetProc`, `Kill`, `Unbook` |
| **DeedInterface** | Resource deeds | `GetOwner`, `GetHost` |

#### Management Interfaces

| Interface | Description | Example Endpoints |
|-----------|-------------|-------------------|
| **AllocationInterface** | Resource allocation | `GetAll`, `Find`, `SetBillable` |
| **FacilityInterface** | Multi-site facilities | `Get`, `Create`, `GetAllocations` |
| **FilterInterface** | Job filtering | `FindFilter`, `GetActions`, `SetEnabled` |
| **ActionInterface** | Filter actions | `Delete`, `Commit` |
| **MatcherInterface** | Filter matchers | `Delete`, `Commit` |
| **DependInterface** | Dependencies | `GetDepend`, `Satisfy`, `Unsatisfy` |
| **SubscriptionInterface** | Show subscriptions | `Get`, `Find`, `SetSize`, `SetBurst` |
| **LimitInterface** | Resource limits | `GetAll`, `Create`, `SetMaxValue` |
| **ServiceInterface** | Service definitions | `GetService`, `CreateService`, `Update` |
| **ServiceOverrideInterface** | Service overrides | `Update`, `Delete` |
| **TaskInterface** | Task management | `Delete`, `SetMinCores` |

### Real-time Updates

CueWeb implements automatic updates through:

- **Polling Strategy**: Regular API calls to refresh data
- **Configurable Intervals**: Adjustable refresh rates per table
- **Intelligent Updates**: Only update changed data to minimize load
- **Background Workers**: Web workers for filtering and processing

---

## Configuration and Environment Variables

### CueWeb Configuration

Key environment variables for CueWeb:

```bash
# Required
NEXT_PUBLIC_OPENCUE_ENDPOINT=http://localhost:8448  # REST Gateway URL
NEXT_PUBLIC_URL=http://localhost:3000               # CueWeb URL
NEXT_JWT_SECRET=your-secret-key                     # JWT signing secret

# Authentication (optional)
NEXT_PUBLIC_AUTH_PROVIDER=github,okta,google        # OAuth providers
NEXTAUTH_URL=http://localhost:3000                  # Auth callback URL
NEXTAUTH_SECRET=random-secret                       # NextAuth secret

# Third-party integrations (optional)
SENTRY_DSN=your-sentry-dsn                          # Error tracking
GOOGLE_CLIENT_ID=your-google-client-id              # Google OAuth
GITHUB_ID=your-github-app-id                        # GitHub OAuth
```

### REST Gateway Configuration

Key environment variables for the REST Gateway:

```bash
# Required
CUEBOT_ENDPOINT=localhost:8443                      # Cuebot gRPC address
REST_PORT=8448                                      # HTTP server port
JWT_SECRET=your-secret-key                          # JWT validation secret

# Optional
LOG_LEVEL=info                                      # Logging verbosity
GRPC_TIMEOUT=30s                                    # gRPC call timeout
CORS_ORIGINS=https://cueweb.example.com             # CORS configuration
RATE_LIMIT_RPS=100                                  # Rate limiting
```

---

## Performance and Scalability

### CueWeb Performance

- **Server-Side Rendering**: Fast initial page loads with Next.js SSR
- **Code Splitting**: Automatic bundle optimization
- **Virtual Scrolling**: Efficient rendering of large job lists
- **Web Workers**: Background processing for data filtering
- **Caching**: Browser and server-side caching strategies

### REST Gateway Performance

- **Connection Pooling**: Efficient gRPC connection reuse
- **Concurrent Handling**: Multiple simultaneous requests
- **Memory Efficiency**: Minimal overhead HTTP-to-gRPC translation
- **Rate Limiting**: Configurable request throttling
- **Health Monitoring**: Built-in health checks and metrics

### Scaling Considerations

- **Horizontal Scaling**: Multiple CueWeb instances behind load balancer
- **Gateway Clustering**: Multiple REST Gateway instances for redundancy
- **Database Optimization**: Efficient Cuebot database queries
- **CDN Integration**: Static asset delivery optimization
- **Monitoring**: Application performance monitoring (APM) integration

---

## Best Practices

### Development

1. **Environment Separation**: Use different configurations for dev/staging/prod
2. **Secret Management**: Use secure secret storage for JWT keys
3. **Testing**: Implement unit and integration tests
4. **Code Quality**: Follow TypeScript and React best practices
5. **Documentation**: Maintain API and component documentation

### Deployment

1. **Container Security**: Use minimal base images and security scanning
2. **Network Security**: Implement proper firewall rules and TLS
3. **Monitoring**: Set up logging, metrics, and alerting
4. **Backup Strategy**: Regular configuration and data backups
5. **Update Procedures**: Establish rolling update procedures

### Operations

1. **Performance Monitoring**: Track response times and error rates
2. **Capacity Planning**: Monitor resource usage and plan scaling
3. **User Training**: Provide documentation and training materials
4. **Incident Response**: Establish procedures for troubleshooting
5. **Regular Maintenance**: Schedule updates and maintenance windows

---

## Troubleshooting Common Issues

### Connection Problems

- **502 Bad Gateway**: Check REST Gateway status and Cuebot connectivity
- **CORS Errors**: Verify CORS configuration in REST Gateway
- **Timeout Issues**: Adjust GRPC_TIMEOUT and HTTP_TIMEOUT settings

### Authentication Issues

- **JWT Validation Failed**: Ensure JWT_SECRET matches between services
- **Token Expired**: Check token expiration times and refresh logic
- **OAuth Failures**: Verify OAuth provider configuration and callbacks

### Performance Issues

- **Slow Page Loads**: Enable caching and optimize bundle sizes
- **High Memory Usage**: Review data fetching patterns and implement pagination
- **API Rate Limits**: Implement request throttling and caching strategies

For detailed troubleshooting guides, see:
- [CueWeb User Guide](/docs/user-guides/cueweb-user-guide)
- [REST API Reference](/docs/reference/rest-api-reference/)
- [Developer Guide](/docs/developer-guide/cueweb-development)