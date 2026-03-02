# WebCue Implementation Plan

## Overview

WebCue is a new modern web interface for OpenCue render management system. This plan details a hybrid architecture with a React SPA frontend (Material-UI, TypeScript) and a lightweight Node.js backend that handles OAuth authentication, JWT minting, and WebSocket hub. The backend proxies requests to the existing REST Gateway.

---

## 1. Directory Structure

```
/webcue/
├── package.json                    # Root package.json for monorepo management
├── README.md                       # Project documentation
├── docker-compose.yml              # Development environment setup
├── .env.example                    # Environment variable template
│
├── frontend/                       # React SPA
│   ├── package.json
│   ├── vite.config.ts
│   ├── tsconfig.json
│   ├── index.html
│   ├── .env.example
│   │
│   ├── public/
│   │   └── favicon.ico
│   │
│   └── src/
│       ├── main.tsx                # Application entry point
│       ├── App.tsx                 # Root component with routing
│       ├── vite-env.d.ts
│       │
│       ├── api/                    # API client layer
│       │   ├── client.ts           # Axios/fetch wrapper with auth
│       │   ├── jobs.ts             # Job-related API calls
│       │   ├── layers.ts           # Layer-related API calls
│       │   ├── frames.ts           # Frame-related API calls
│       │   └── types.ts            # API response types
│       │
│       ├── components/             # Reusable UI components
│       │   ├── layout/
│       │   │   ├── AppLayout.tsx   # Main app shell with header/sidebar
│       │   │   ├── Header.tsx      # Top navigation bar
│       │   │   └── Sidebar.tsx     # Optional sidebar navigation
│       │   │
│       │   ├── common/
│       │   │   ├── DataTable.tsx   # Generic sortable/filterable table
│       │   │   ├── ProgressBar.tsx # Job/frame progress visualization
│       │   │   ├── StatusBadge.tsx # State indicator (Paused, Failing, etc.)
│       │   │   ├── ContextMenu.tsx # Right-click context menu wrapper
│       │   │   ├── ConfirmDialog.tsx # Confirmation modal
│       │   │   └── LoadingSpinner.tsx
│       │   │
│       │   ├── jobs/
│       │   │   ├── JobMonitor.tsx  # Main job list view
│       │   │   ├── JobTable.tsx    # Job data table with columns
│       │   │   ├── JobRow.tsx      # Individual job row
│       │   │   ├── JobContextMenu.tsx # Job right-click actions
│       │   │   └── JobSearchBar.tsx # Job filtering/search
│       │   │
│       │   ├── layers/
│       │   │   ├── LayerMonitor.tsx # Layer list for selected job
│       │   │   ├── LayerTable.tsx   # Layer data table
│       │   │   ├── LayerRow.tsx     # Individual layer row
│       │   │   └── LayerContextMenu.tsx
│       │   │
│       │   └── frames/
│       │       ├── FrameMonitor.tsx # Frame list for selected job
│       │       ├── FrameTable.tsx   # Frame data table
│       │       ├── FrameRow.tsx     # Individual frame row
│       │       ├── FrameContextMenu.tsx
│       │       └── LogViewer.tsx    # Frame log display
│       │
│       ├── contexts/               # React contexts
│       │   ├── AuthContext.tsx     # Authentication state
│       │   ├── WebSocketContext.tsx # WebSocket connection
│       │   └── JobContext.tsx      # Selected job state
│       │
│       ├── hooks/                  # Custom React hooks
│       │   ├── useAuth.ts          # Authentication hook
│       │   ├── useWebSocket.ts     # WebSocket connection hook
│       │   ├── useJobs.ts          # Job data fetching
│       │   ├── useLayers.ts        # Layer data fetching
│       │   ├── useFrames.ts        # Frame data fetching
│       │   └── useContextMenu.ts   # Context menu state
│       │
│       ├── pages/                  # Route-level components
│       │   ├── LoginPage.tsx       # OAuth login page
│       │   ├── DashboardPage.tsx   # Main dashboard with monitors
│       │   └── NotFoundPage.tsx    # 404 page
│       │
│       ├── types/                  # TypeScript type definitions
│       │   ├── job.ts              # Job, JobStats types
│       │   ├── layer.ts            # Layer, LayerStats types
│       │   ├── frame.ts            # Frame type
│       │   └── websocket.ts        # WebSocket message types
│       │
│       ├── utils/                  # Utility functions
│       │   ├── formatters.ts       # Memory, time formatting
│       │   ├── constants.ts        # App constants
│       │   └── helpers.ts          # General helpers
│       │
│       └── theme/                  # MUI theme customization
│           └── theme.ts            # Custom MUI theme
│
└── backend/                        # Node.js backend
    ├── package.json
    ├── tsconfig.json
    ├── .env.example
    │
    └── src/
        ├── index.ts                # Server entry point
        ├── app.ts                  # Express app setup
        │
        ├── config/
        │   └── config.ts           # Environment configuration
        │
        ├── middleware/
        │   ├── auth.ts             # JWT validation middleware
        │   └── errorHandler.ts     # Global error handler
        │
        ├── routes/
        │   ├── auth.ts             # OAuth routes (/auth/*)
        │   └── api.ts              # API proxy routes (/api/*)
        │
        ├── services/
        │   ├── authService.ts      # OAuth + JWT logic
        │   ├── proxyService.ts     # REST Gateway proxy
        │   └── pollingService.ts   # Background data polling
        │
        ├── websocket/
        │   ├── wsServer.ts         # WebSocket server setup
        │   ├── handlers.ts         # Message handlers
        │   └── broadcaster.ts      # Client broadcast logic
        │
        └── types/
            └── index.ts            # Backend type definitions
```

---

## 2. Component Hierarchy

```
App
├── AuthProvider (Context)
│   └── WebSocketProvider (Context)
│       └── Routes
│           ├── LoginPage
│           │   └── OAuthButtons (Okta, Google, GitHub, LDAP)
│           │
│           └── ProtectedRoute
│               └── AppLayout
│                   ├── Header
│                   │   ├── Logo
│                   │   ├── Navigation
│                   │   └── UserMenu (logout, settings)
│                   │
│                   └── DashboardPage
│                       ├── JobSearchBar
│                       │   ├── TextField (search input)
│                       │   ├── ShowFilter
│                       │   └── UserFilter
│                       │
│                       ├── JobMonitor (main panel)
│                       │   ├── JobTable
│                       │   │   ├── TableHeader (sortable columns)
│                       │   │   └── JobRow[] (virtualized)
│                       │   │       ├── Checkbox (selection)
│                       │   │       ├── JobName
│                       │   │       ├── StatusBadge
│                       │   │       ├── FrameStats (done/total/running/dead/eaten/wait)
│                       │   │       ├── MaxRss
│                       │   │       ├── Age
│                       │   │       └── ProgressBar
│                       │   │
│                       │   └── JobContextMenu
│                       │       ├── Pause/Resume
│                       │       ├── Kill
│                       │       ├── Retry Dead
│                       │       └── Eat Dead
│                       │
│                       ├── LayerMonitor (detail panel)
│                       │   ├── LayerTable
│                       │   │   ├── TableHeader
│                       │   │   └── LayerRow[]
│                       │   │       ├── Name, Services, Range
│                       │   │       ├── Cores, Memory
│                       │   │       ├── FrameStats
│                       │   │       ├── AvgTime
│                       │   │       └── ProgressBar
│                       │   │
│                       │   └── LayerContextMenu
│                       │       ├── Kill
│                       │       ├── Retry
│                       │       └── Eat
│                       │
│                       └── FrameMonitor (detail panel)
│                           ├── FrameTable
│                           │   ├── TableHeader
│                           │   └── FrameRow[]
│                           │       ├── Order, Frame#, Layer
│                           │       ├── Status
│                           │       ├── Host, Retries
│                           │       ├── Runtime, Memory
│                           │       └── StartTime, StopTime
│                           │
│                           ├── FrameContextMenu
│                           │   ├── Retry
│                           │   ├── Kill
│                           │   ├── Eat
│                           │   └── View Log
│                           │
│                           └── LogViewer (modal/drawer)
│                               ├── LogContent
│                               └── TailToggle
```

---

## 3. Backend API Routes

### Authentication Routes (`/auth/*`)

| Method | Route | Description |
|--------|-------|-------------|
| GET | `/auth/providers` | List available OAuth providers |
| GET | `/auth/login/:provider` | Initiate OAuth flow (okta/google/github/ldap) |
| GET | `/auth/callback/:provider` | OAuth callback handler |
| POST | `/auth/ldap` | LDAP username/password login |
| POST | `/auth/refresh` | Refresh JWT token |
| POST | `/auth/logout` | Invalidate session |
| GET | `/auth/me` | Get current user info |

### API Proxy Routes (`/api/*`)

These routes proxy requests to the REST Gateway, adding JWT authentication.

| Method | Route | Backend Action | REST Gateway Endpoint |
|--------|-------|----------------|----------------------|
| POST | `/api/jobs` | Get jobs list | `POST /job.JobInterface/GetJobs` |
| POST | `/api/jobs/:id` | Get single job | `POST /job.JobInterface/GetJob` |
| POST | `/api/jobs/:id/layers` | Get job layers | `POST /job.JobInterface/GetLayers` |
| POST | `/api/jobs/:id/frames` | Get job frames | `POST /job.JobInterface/GetFrames` |
| POST | `/api/jobs/:id/pause` | Pause job | `POST /job.JobInterface/Pause` |
| POST | `/api/jobs/:id/resume` | Resume job | `POST /job.JobInterface/Resume` |
| POST | `/api/jobs/:id/kill` | Kill job | `POST /job.JobInterface/Kill` |
| POST | `/api/jobs/:id/retry-dead` | Retry dead frames | `POST /job.JobInterface/RetryFrames` |
| POST | `/api/jobs/:id/eat-dead` | Eat dead frames | `POST /job.JobInterface/EatFrames` |
| POST | `/api/layers/:id/kill` | Kill layer | `POST /job.LayerInterface/Kill` |
| POST | `/api/layers/:id/retry` | Retry layer frames | `POST /job.LayerInterface/RetryFrames` |
| POST | `/api/layers/:id/eat` | Eat layer frames | `POST /job.LayerInterface/EatFrames` |
| POST | `/api/frames/:id/retry` | Retry frame | `POST /job.FrameInterface/Retry` |
| POST | `/api/frames/:id/kill` | Kill frame | `POST /job.FrameInterface/Kill` |
| POST | `/api/frames/:id/eat` | Eat frame | `POST /job.FrameInterface/Eat` |
| GET | `/api/frames/:id/log` | Get frame log path | Returns log file path |

---

## 4. WebSocket Message Protocol

### Connection

```
Client connects to: ws://backend:3001/ws
Headers: { Authorization: "Bearer <jwt_token>" }
```

### Message Format

All messages use JSON with this structure:

```typescript
interface WebSocketMessage {
  type: string;
  payload: any;
  timestamp: number;
}
```

### Client -> Server Messages

| Type | Payload | Description |
|------|---------|-------------|
| `subscribe:jobs` | `{ showFilter?: string, userFilter?: string }` | Subscribe to job updates |
| `unsubscribe:jobs` | `{}` | Unsubscribe from job updates |
| `subscribe:job` | `{ jobId: string }` | Subscribe to specific job (layers/frames) |
| `unsubscribe:job` | `{ jobId: string }` | Unsubscribe from specific job |
| `ping` | `{}` | Keep-alive ping |

### Server -> Client Messages

| Type | Payload | Description |
|------|---------|-------------|
| `jobs:update` | `{ jobs: Job[] }` | Full job list update |
| `jobs:delta` | `{ added: Job[], updated: Job[], removed: string[] }` | Incremental job changes |
| `job:layers` | `{ jobId: string, layers: Layer[] }` | Layer list for subscribed job |
| `job:frames` | `{ jobId: string, frames: Frame[] }` | Frame list for subscribed job |
| `job:updated` | `{ job: Job }` | Single job update |
| `error` | `{ code: string, message: string }` | Error notification |
| `pong` | `{}` | Keep-alive response |

### Backend Polling Behavior

```
1. Backend polls REST Gateway every 20 seconds for subscribed data
2. Compares with cached data to detect changes
3. Broadcasts delta updates to subscribed clients
4. For job detail (layers/frames), polls every 10 seconds when clients subscribed
```

---

## 5. Authentication Flow

### OAuth Flow (Okta/Google/GitHub)

```
1. User clicks "Login with [Provider]"
2. Frontend redirects to: GET /auth/login/:provider
3. Backend redirects to OAuth provider authorization URL
4. User authenticates with provider
5. Provider redirects to: GET /auth/callback/:provider?code=xxx
6. Backend exchanges code for tokens
7. Backend creates/updates user record
8. Backend mints JWT token with user info
9. Backend redirects to frontend with JWT in URL fragment
10. Frontend stores JWT in localStorage/memory
11. Frontend includes JWT in all API requests
12. WebSocket connection includes JWT in handshake
```

### LDAP Flow

```
1. User enters username/password on login page
2. Frontend POSTs to: POST /auth/ldap { username, password }
3. Backend binds to LDAP server with credentials
4. On success, backend mints JWT token
5. Backend returns JWT to frontend
6. Same storage/usage as OAuth flow
```

### JWT Token Structure

```typescript
{
  sub: string,        // User ID
  email: string,      // User email
  name: string,       // Display name
  role: string,       // User role (user/admin)
  iat: number,        // Issued at timestamp
  exp: number         // Expiration (1 hour)
}
```

### Environment Variables for Auth

```bash
# OAuth Providers (configure any/all)
OAUTH_OKTA_CLIENT_ID=
OAUTH_OKTA_CLIENT_SECRET=
OAUTH_OKTA_ISSUER=

OAUTH_GOOGLE_CLIENT_ID=
OAUTH_GOOGLE_CLIENT_SECRET=

OAUTH_GITHUB_CLIENT_ID=
OAUTH_GITHUB_CLIENT_SECRET=

# LDAP
LDAP_URL=ldaps://ldap.example.com:636
LDAP_BIND_DN=uid={username},ou=users,dc=example,dc=com
LDAP_CA_CERT_PATH=/path/to/ca.crt

# JWT
JWT_SECRET=your-secret-key-here
JWT_EXPIRY=3600
```

---

## 6. Step-by-Step Implementation Order

### Phase 1: Project Setup (Days 1-2)

1. **Create project structure**
   - Initialize `/webcue/` directory
   - Create `package.json` for monorepo with workspaces
   - Set up frontend with Vite + React + TypeScript
   - Set up backend with Express + TypeScript

2. **Configure development environment**
   - Set up ESLint, Prettier configurations
   - Create `.env.example` files
   - Create `docker-compose.yml` for local development
   - Set up hot-reload for both frontend and backend

### Phase 2: Backend Core (Days 3-5)

3. **Implement authentication service**
   - Set up Passport.js with OAuth strategies
   - Implement JWT minting and validation
   - Create auth middleware
   - Add LDAP authentication support

4. **Implement API proxy service**
   - Create proxy to REST Gateway
   - Add JWT token injection for gateway auth
   - Implement error handling and response transformation

5. **Implement WebSocket server**
   - Set up Socket.io server
   - Implement authentication handshake
   - Create subscription management
   - Build broadcaster for client updates

### Phase 3: Frontend Foundation (Days 6-8)

6. **Set up React application**
   - Configure MUI theme (dark/light mode)
   - Set up React Router
   - Create AuthContext and WebSocketContext
   - Implement protected routes

7. **Build login page**
   - Create OAuth button components
   - Implement LDAP login form
   - Handle auth callbacks and token storage

8. **Create base layout**
   - Build AppLayout with header
   - Create navigation components
   - Implement user menu with logout

### Phase 4: Core Components (Days 9-14)

9. **Build Job Monitor**
   - Create JobTable with all columns from cuegui
   - Implement sorting and filtering
   - Add row selection with checkboxes
   - Create JobContextMenu with all actions

10. **Build Layer Monitor**
    - Create LayerTable with columns
    - Connect to selected job
    - Implement LayerContextMenu

11. **Build Frame Monitor**
    - Create FrameTable with columns
    - Connect to selected job
    - Implement FrameContextMenu
    - Create LogViewer component

### Phase 5: Real-time Updates (Days 15-17)

12. **Implement polling service**
    - Create background polling in backend
    - Implement change detection
    - Build delta update logic

13. **Connect WebSocket to UI**
    - Wire up useWebSocket hook
    - Update tables on WebSocket messages
    - Handle reconnection logic

### Phase 6: Polish and Testing (Days 18-20)

14. **Add remaining features**
    - Implement job search/filter
    - Add keyboard shortcuts
    - Create confirmation dialogs for destructive actions

15. **Testing and documentation**
    - Write unit tests for critical components
    - Create integration tests
    - Write deployment documentation

---

## 7. Key Files to Create

### Frontend Files

| File | Description |
|------|-------------|
| `frontend/src/main.tsx` | React app entry with providers |
| `frontend/src/App.tsx` | Root component with Router |
| `frontend/src/api/client.ts` | Axios client with JWT interceptor |
| `frontend/src/contexts/AuthContext.tsx` | Auth state management |
| `frontend/src/contexts/WebSocketContext.tsx` | WebSocket connection management |
| `frontend/src/components/jobs/JobMonitor.tsx` | Main job list component |
| `frontend/src/components/jobs/JobTable.tsx` | Job data table |
| `frontend/src/components/jobs/JobContextMenu.tsx` | Job right-click menu |
| `frontend/src/components/layers/LayerMonitor.tsx` | Layer list component |
| `frontend/src/components/frames/FrameMonitor.tsx` | Frame list component |
| `frontend/src/components/frames/LogViewer.tsx` | Frame log viewer |
| `frontend/src/types/job.ts` | Job TypeScript types |
| `frontend/src/utils/formatters.ts` | Memory/time formatters |
| `frontend/src/theme/theme.ts` | MUI theme config |

### Backend Files

| File | Description |
|------|-------------|
| `backend/src/index.ts` | Server entry point |
| `backend/src/app.ts` | Express app with middleware |
| `backend/src/config/config.ts` | Environment configuration |
| `backend/src/routes/auth.ts` | OAuth/LDAP auth routes |
| `backend/src/routes/api.ts` | API proxy routes |
| `backend/src/services/authService.ts` | Auth logic with Passport |
| `backend/src/services/proxyService.ts` | REST Gateway proxy |
| `backend/src/services/pollingService.ts` | Background data polling |
| `backend/src/websocket/wsServer.ts` | Socket.io setup |
| `backend/src/websocket/broadcaster.ts` | WebSocket broadcast logic |
| `backend/src/middleware/auth.ts` | JWT validation middleware |

---

## 8. Dependencies

### Frontend (`frontend/package.json`)

```json
{
  "dependencies": {
    "@emotion/react": "^11.11.0",
    "@emotion/styled": "^11.11.0",
    "@mui/material": "^5.15.0",
    "@mui/icons-material": "^5.15.0",
    "@tanstack/react-table": "^8.11.0",
    "axios": "^1.6.0",
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "react-router-dom": "^6.21.0",
    "socket.io-client": "^4.7.0",
    "date-fns": "^3.0.0",
    "react-virtualized": "^9.22.0"
  },
  "devDependencies": {
    "@types/react": "^18.2.0",
    "@types/react-dom": "^18.2.0",
    "@vitejs/plugin-react": "^4.2.0",
    "typescript": "^5.3.0",
    "vite": "^5.0.0",
    "eslint": "^8.56.0",
    "prettier": "^3.1.0",
    "@testing-library/react": "^14.1.0",
    "vitest": "^1.1.0"
  }
}
```

### Backend (`backend/package.json`)

```json
{
  "dependencies": {
    "express": "^4.18.0",
    "socket.io": "^4.7.0",
    "passport": "^0.7.0",
    "passport-oauth2": "^1.8.0",
    "passport-google-oauth20": "^2.0.0",
    "passport-github2": "^0.1.0",
    "ldapjs": "^3.0.0",
    "jsonwebtoken": "^9.0.0",
    "axios": "^1.6.0",
    "cors": "^2.8.0",
    "helmet": "^7.1.0",
    "dotenv": "^16.3.0",
    "winston": "^3.11.0"
  },
  "devDependencies": {
    "@types/express": "^4.17.0",
    "@types/passport": "^1.0.0",
    "@types/jsonwebtoken": "^9.0.0",
    "@types/ldapjs": "^3.0.0",
    "@types/cors": "^2.8.0",
    "typescript": "^5.3.0",
    "ts-node-dev": "^2.0.0",
    "eslint": "^8.56.0",
    "jest": "^29.7.0",
    "@types/jest": "^29.5.0"
  }
}
```

---

## 9. Data Types (from cueweb/cuegui analysis)

### Job Type

```typescript
interface Job {
  id: string;
  name: string;
  state: 'PENDING' | 'FINISHED';
  isPaused: boolean;
  autoEat: boolean;
  hasComment: boolean;
  show: string;
  shot: string;
  user: string;
  facility: string;
  group: string;
  logDir: string;
  priority: number;
  minCores: number;
  maxCores: number;
  minGpus: number;
  maxGpus: number;
  startTime: number;
  stopTime: number;
  uid: number;
  os: string;
  jobStats: JobStats;
}

interface JobStats {
  totalFrames: number;
  succeededFrames: number;
  runningFrames: number;
  deadFrames: number;
  eatenFrames: number;
  waitingFrames: number;
  dependFrames: number;
  pendingFrames: number;
  maxRss: string;
  avgFrameSec: number;
  reservedCores: number;
  reservedGpus: number;
}
```

### Layer Type

```typescript
interface Layer {
  id: string;
  name: string;
  parentId: string;  // Job ID
  range: string;
  chunkSize: number;
  dispatchOrder: number;
  type: string;
  services: string[];
  limits: string[];
  tags: string[];
  minCores: number;
  maxCores: number;
  minGpus: number;
  maxGpus: number;
  minMemory: string;
  minGpuMemory: string;
  isThreadable: boolean;
  timeout: number;
  timeoutLlu: number;
  memoryOptimizerEnabled: boolean;
  layerStats: LayerStats;
}

interface LayerStats {
  totalFrames: number;
  succeededFrames: number;
  runningFrames: number;
  deadFrames: number;
  eatenFrames: number;
  waitingFrames: number;
  dependFrames: number;
  avgFrameSec: number;
  maxRss: string;
}
```

### Frame Type

```typescript
interface Frame {
  id: string;
  name: string;
  layerName: string;
  number: number;
  state: 'WAITING' | 'RUNNING' | 'DEAD' | 'EATEN' | 'DEPEND' | 'SUCCEEDED' | 'CHECKPOINT';
  retryCount: number;
  exitStatus: number;
  dispatchOrder: number;
  startTime: number;
  stopTime: number;
  maxRss: string;
  usedMemory: string;
  reservedMemory: string;
  usedGpuMemory: string;
  maxGpuMemory: string;
  reservedGpuMemory: string;
  lastResource: string;  // "hostname/cores/gpus" format
  checkpointState: string;
  checkpointCount: number;
  totalCoreTime: number;
  lluTime: number;
  totalGpuTime: number;
}
```

---

## 10. Critical Files for Implementation

### Critical Files for Implementation

1. **`/Users/dtavares/dev/OpenCue/cueweb/app/utils/api_utils.ts`**
   - Pattern to follow: Shows how to create JWT tokens, fetch from REST Gateway, and handle responses
   - Key functions: `fetchObjectFromRestGateway`, `createJwtToken`, `handleRoute`

2. **`/Users/dtavares/dev/OpenCue/cueweb/app/jobs/columns.tsx`**
   - Pattern to follow: Job type definition and column structure using TanStack Table
   - Key patterns: `getState()` function for determining job display state, column definitions

3. **`/Users/dtavares/dev/OpenCue/cueweb/lib/auth.ts`**
   - Pattern to follow: OAuth provider configuration using NextAuth
   - Key patterns: Provider setup for Okta, Google, GitHub, LDAP

4. **`/Users/dtavares/dev/OpenCue/rest_gateway/opencue_gateway/main.go`**
   - Pattern to follow: REST Gateway endpoint structure and JWT validation
   - Key insight: All endpoints use POST, JWT middleware pattern

5. **`/Users/dtavares/dev/OpenCue/cuegui/cuegui/MenuActions.py`**
   - Pattern to follow: Complete list of context menu actions and their API calls
   - Key actions: JobActions (pause, resume, kill, retryDead, eatDead), LayerActions, FrameActions

---

## 11. Environment Variables

### Backend `.env`

```bash
# Server
PORT=3001
NODE_ENV=development

# REST Gateway
REST_GATEWAY_URL=http://localhost:8448
JWT_SECRET=your-jwt-secret-for-gateway

# Session
SESSION_SECRET=your-session-secret

# OAuth: Okta
OAUTH_OKTA_ENABLED=true
OAUTH_OKTA_CLIENT_ID=xxx
OAUTH_OKTA_CLIENT_SECRET=xxx
OAUTH_OKTA_ISSUER=https://your-org.okta.com

# OAuth: Google
OAUTH_GOOGLE_ENABLED=true
OAUTH_GOOGLE_CLIENT_ID=xxx
OAUTH_GOOGLE_CLIENT_SECRET=xxx

# OAuth: GitHub
OAUTH_GITHUB_ENABLED=true
OAUTH_GITHUB_CLIENT_ID=xxx
OAUTH_GITHUB_CLIENT_SECRET=xxx

# LDAP
LDAP_ENABLED=true
LDAP_URL=ldaps://ldap.example.com:636
LDAP_BIND_DN=uid={username},ou=users,dc=example,dc=com
LDAP_CA_CERT_PATH=/path/to/ca.crt

# Polling
POLL_INTERVAL_JOBS=20000
POLL_INTERVAL_JOB_DETAIL=10000

# Frontend URL (for OAuth callbacks)
FRONTEND_URL=http://localhost:5173
```

### Frontend `.env`

```bash
VITE_API_URL=http://localhost:3001
VITE_WS_URL=ws://localhost:3001
```

---

## 12. Docker Compose for Development

```yaml
version: '3.8'

services:
  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile.dev
    ports:
      - "5173:5173"
    volumes:
      - ./frontend:/app
      - /app/node_modules
    environment:
      - VITE_API_URL=http://localhost:3001
      - VITE_WS_URL=ws://localhost:3001

  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile.dev
    ports:
      - "3001:3001"
    volumes:
      - ./backend:/app
      - /app/node_modules
    env_file:
      - ./backend/.env
    depends_on:
      - rest-gateway

  rest-gateway:
    image: opencue/rest-gateway:latest
    ports:
      - "8448:8448"
    environment:
      - CUEBOT_ENDPOINT=cuebot:8443
      - REST_PORT=8448
      - JWT_SECRET=${JWT_SECRET}
    depends_on:
      - cuebot

  cuebot:
    image: opencue/cuebot:latest
    ports:
      - "8443:8443"
    environment:
      - CUE_FRAME_LOG_DIR=/tmp/rqd/logs
```

---

This implementation plan provides a comprehensive blueprint for building WebCue. The architecture follows patterns established in the existing cueweb codebase while using a more lightweight backend approach suitable for the specific requirements (OAuth + WebSocket hub + API proxy).
