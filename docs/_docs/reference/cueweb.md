---
layout: default
title: CueWeb Reference
parent: Reference
nav_order: 71
---

# CueWeb Reference
{: .no_toc }

Complete reference documentation for CueWeb, the web-based interface for OpenCue.

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

CueWeb is a web-based application that provides browser access to OpenCue render farm management. Built with Next.js and React, it offers a responsive interface for monitoring jobs, managing frames, and controlling rendering operations.

### System Requirements

| Component | Requirement |
|-----------|-------------|
| **Node.js** | Version 18 or later |
| **Browser** | Chrome, Firefox, Safari, Edge (latest versions) |
| **Network** | Access to REST Gateway endpoint |
| **Memory** | 512MB minimum for container deployment |

---

## Architecture

### Component Stack

```
┌─────────────────────────────────────────────────────────┐
│                      CueWeb                              │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐  │
│  │   Next.js   │  │    React    │  │   Shadcn UI     │  │
│  │   Server    │  │  Components │  │   Components    │  │
│  └─────────────┘  └─────────────┘  └─────────────────┘  │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐  │
│  │  NextAuth   │  │  JWT Token  │  │   Web Workers   │  │
│  │    Auth     │  │  Generation │  │   (Filtering)   │  │
│  └─────────────┘  └─────────────┘  └─────────────────┘  │
└─────────────────────────────────────────────────────────┘
                           │
                           ▼ HTTP/JSON
┌─────────────────────────────────────────────────────────┐
│                    REST Gateway                          │
└─────────────────────────────────────────────────────────┘
                           │
                           ▼ gRPC
┌─────────────────────────────────────────────────────────┐
│                       Cuebot                             │
└─────────────────────────────────────────────────────────┘
```

### Data Flow

1. User interacts with CueWeb UI
2. CueWeb generates JWT token using shared secret
3. HTTP request sent to REST Gateway with JWT in Authorization header
4. REST Gateway validates JWT and forwards to Cuebot via gRPC
5. Response returned through the same path

---

## Environment Variables

### Required Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `NEXT_PUBLIC_OPENCUE_ENDPOINT` | REST Gateway URL | `http://localhost:8448` |
| `NEXT_PUBLIC_URL` | CueWeb public URL | `http://localhost:3000` |
| `NEXT_JWT_SECRET` | JWT signing secret (must match REST Gateway) | `your-secret-key` |

### Authentication Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `NEXT_PUBLIC_AUTH_PROVIDER` | Comma-separated auth providers | `google,okta,github,ldap` |
| `NEXTAUTH_URL` | NextAuth callback URL | `http://localhost:3000` |
| `NEXTAUTH_SECRET` | NextAuth session secret | `random-secret` |

**Note:** Set `NEXT_PUBLIC_AUTH_PROVIDER=` (empty) for no authentication.

### OAuth Provider Variables

#### Okta

| Variable | Description |
|----------|-------------|
| `NEXT_AUTH_OKTA_CLIENT_ID` | Okta application client ID |
| `NEXT_AUTH_OKTA_CLIENT_SECRET` | Okta application client secret |
| `NEXT_AUTH_OKTA_ISSUER` | Okta issuer URL (e.g., `https://company.okta.com`) |

#### Google

| Variable | Description |
|----------|-------------|
| `GOOGLE_CLIENT_ID` | Google OAuth client ID |
| `GOOGLE_CLIENT_SECRET` | Google OAuth client secret |

#### GitHub

| Variable | Description |
|----------|-------------|
| `GITHUB_ID` | GitHub OAuth application ID |
| `GITHUB_SECRET` | GitHub OAuth application secret |

#### LDAP

| Variable | Description |
|----------|-------------|
| `LDAP_URI` | LDAP server URI (e.g., `ldaps://ldap.company.com:636`) |
| `LDAP_LOGIN_DN` | Login DN template with `{login}` placeholder |
| `LDAP_CERTIFICATE` | Path to CA certificate for TLS verification |

### Monitoring Variables

| Variable | Description |
|----------|-------------|
| `SENTRY_DSN` | Sentry Data Source Name for error tracking |
| `SENTRY_ENVIRONMENT` | Sentry environment name |
| `SENTRY_URL` | Sentry server URL |
| `SENTRY_ORG` | Sentry organization |
| `SENTRY_PROJECT` | Sentry project name |

---

## User Interface Components

### Jobs Table

The main jobs table displays rendering jobs with the following columns:

| Column | Description | Sortable |
|--------|-------------|----------|
| **Name** | Job name (clickable for details) | Yes |
| **Show** | Parent show name | Yes |
| **Shot** | Shot identifier | Yes |
| **User** | Job owner | Yes |
| **State** | Current job state | Yes |
| **Progress** | Frame completion progress | Yes |
| **Priority** | Job priority value | Yes |
| **Pending** | Pending frame count | Yes |
| **Running** | Running frame count | Yes |
| **Dead** | Failed frame count | Yes |
| **Cores** | Reserved cores | Yes |
| **Start Time** | Job start timestamp | Yes |

### Job States

| State | Color | Description |
|-------|-------|-------------|
| `PENDING` | Orange | Job waiting for resources |
| `RUNNING` | Green | Job has running frames |
| `PAUSED` | Blue | Job manually paused |
| `FINISHED` | Gray | Job completed |
| `DEAD` | Red | Job has failed frames |

### Frame States

| State | Color | Description |
|-------|-------|-------------|
| `WAITING` | Gray | Frame pending dispatch |
| `RUNNING` | Yellow | Frame currently rendering |
| `SUCCEEDED` | Green | Frame completed successfully |
| `DEAD` | Red | Frame failed |
| `EATEN` | Purple | Frame marked as eaten |
| `DEPEND` | Cyan | Frame waiting on dependency |

---

## Search Functionality

### Basic Search

Type directly in the search box to find jobs:

```
# Search by show name
myshow-

# Search by job name pattern
myshow-shot_010

# Search by partial match
comp
```

### Regex Search

Prefix with `!` for regex patterns:

```
# Match pattern
!^myshow-.*lighting.*$

# Match frame range
!.*_[0-9]{3}-[0-9]{3}_.*

# Match multiple criteria
!(lighting|comp).*shot_[0-9]+
```

### Search Result Actions

- **Click job**: Add to monitored jobs table
- **Green indicator**: Job already in table
- **Multiple selection**: Use checkboxes for batch operations

---

## Context Menu Actions

### Job Actions

| Action | Description |
|--------|-------------|
| **Pause** | Pause job rendering |
| **Unpause** | Resume paused job |
| **Kill** | Terminate job |
| **Eat Dead Frames** | Mark dead frames as eaten |
| **Retry Dead Frames** | Retry all failed frames |
| **Unmonitor** | Remove from monitored jobs |

### Layer Actions

| Action | Description |
|--------|-------------|
| **Kill** | Kill all frames in layer |
| **Eat** | Eat all frames in layer |
| **Retry** | Retry failed frames in layer |
| **View Frames** | Show frame list for layer |

### Frame Actions

| Action | Description |
|--------|-------------|
| **Retry** | Retry specific frame |
| **Kill** | Kill running frame |
| **Eat** | Mark frame as eaten |
| **View Log** | Open frame log viewer |

---

## API Integration

### JWT Token Generation

CueWeb generates JWT tokens for REST Gateway authentication:

```javascript
// Token structure
{
  "header": {
    "alg": "HS256",
    "typ": "JWT"
  },
  "payload": {
    "sub": "user-id",
    "exp": 1234567890  // Unix timestamp
  }
}
```

### API Endpoints Used

CueWeb communicates with these REST Gateway endpoints:

| Endpoint | Purpose |
|----------|---------|
| `show.ShowInterface/GetShows` | List available shows |
| `show.ShowInterface/FindShow` | Get specific show |
| `job.JobInterface/GetJobs` | List jobs for show |
| `job.JobInterface/FindJob` | Get specific job |
| `job.JobInterface/GetFrames` | Get frames for job |
| `job.JobInterface/Pause` | Pause job |
| `job.JobInterface/Resume` | Resume job |
| `job.JobInterface/Kill` | Kill job |
| `layer.LayerInterface/GetLayer` | Get layer details |
| `layer.LayerInterface/GetFrames` | Get frames for layer |
| `frame.FrameInterface/Retry` | Retry frame |
| `frame.FrameInterface/Kill` | Kill frame |
| `frame.FrameInterface/Eat` | Eat frame |

---

## Configuration Files

### next.config.js

Key configuration options:

```javascript
module.exports = {
  // Enable React strict mode
  reactStrictMode: true,

  // Output standalone build
  output: 'standalone',

  // Image optimization
  images: {
    unoptimized: true
  },

  // Security headers
  async headers() {
    return [
      {
        source: '/(.*)',
        headers: [
          { key: 'X-Frame-Options', value: 'DENY' },
          { key: 'X-Content-Type-Options', value: 'nosniff' }
        ]
      }
    ]
  }
}
```

### Docker Configuration

Default Dockerfile exposes:

| Port | Service |
|------|---------|
| 3000 | CueWeb HTTP |

Required volume mounts for log viewing:

```bash
# Mount frame log directory
-v /path/to/logs:/tmp/rqd/logs:ro
```

---

## Theming

### Theme Toggle

CueWeb supports light and dark themes:

- **Light Mode**: Default theme with light backgrounds
- **Dark Mode**: Dark theme for reduced eye strain

Toggle via the theme button in the header.

### CSS Variables

Key theme variables (defined in Tailwind config):

```css
/* Light theme */
--background: 0 0% 100%;
--foreground: 222.2 84% 4.9%;

/* Dark theme */
--background: 222.2 84% 4.9%;
--foreground: 210 40% 98%;
```

---

## Performance Optimization

### Auto-refresh

- Default refresh interval: 5 seconds
- Tables auto-update without full page reload
- Configurable per-table refresh rates

### Virtualization

- Large job lists use virtual scrolling
- Only visible rows are rendered
- Improves performance with 1000+ jobs

### Web Workers

- Filtering operations run in background threads
- Main thread remains responsive during searches
- Reduces UI blocking

---

## Troubleshooting

### Common Issues

#### "Failed to fetch jobs"

**Cause**: Cannot connect to REST Gateway

**Solution**:
1. Verify REST Gateway is running
2. Check `NEXT_PUBLIC_OPENCUE_ENDPOINT` is correct
3. Verify network connectivity
4. Check browser console for CORS errors

#### Authentication Loop

**Cause**: OAuth configuration mismatch

**Solution**:
1. Verify `NEXTAUTH_URL` matches actual URL
2. Check OAuth provider callback URLs
3. Ensure `NEXTAUTH_SECRET` is set

#### JWT Token Errors

**Cause**: Secret mismatch between CueWeb and REST Gateway

**Solution**:
1. Ensure `NEXT_JWT_SECRET` matches REST Gateway's `JWT_SECRET`
2. Check token expiration settings

#### Blank Page on Load

**Cause**: Build-time environment variables not set

**Solution**:
1. Rebuild with correct environment variables
2. Check `NEXT_PUBLIC_*` variables are set during build

### Debug Mode

Enable verbose logging:

```bash
# Set in environment
DEBUG=cueweb:* npm run dev
```

### Browser Console

Check browser developer tools for:
- Network request failures
- JavaScript errors
- WebSocket connection issues

---

## File Structure

```
cueweb/
├── app/                   # Next.js app directory
│   ├── api/               # API routes
│   ├── login/             # Login page
│   ├── jobs/              # Jobs pages
│   └── page.tsx           # Main page
├── components/            # React components
│   └── ui/                # Shadcn UI components
├── lib/                   # Utility libraries
│   ├── auth.ts            # Authentication config
│   └── api.ts             # API client functions
├── public/                # Static assets
├── Dockerfile             # Container configuration
├── next.config.js         # Next.js configuration
├── package.json           # Dependencies
└── tailwind.config.js     # Tailwind CSS config
```

---

## Related Documentation

- [CueWeb Quick Start](/docs/quick-starts/quick-start-cueweb/) - Getting started guide
- [CueWeb User Guide](/docs/user-guides/cueweb-user-guide/) - Complete usage guide
- [CueWeb Tutorial](/docs/tutorials/cueweb-tutorial/) - Step-by-step tutorial
- [CueWeb Developer Guide](/docs/developer-guide/cueweb-development/) - Development reference
- [REST API Reference](/docs/reference/rest-api-reference/) - API documentation
- [Deploying CueWeb](/docs/getting-started/deploying-cueweb/) - Deployment guide
