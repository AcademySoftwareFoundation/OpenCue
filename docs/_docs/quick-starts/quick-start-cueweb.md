---
layout: default
title: CueWeb Quick Start
parent: Quick Starts
nav_order: 9
---

# CueWeb Quick Start
{: .no_toc }

Get up and running with CueWeb, the web-based interface for OpenCue.

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

CueWeb is a web-based application that brings the core functionality of CueGUI to your browser. It provides an intuitive interface for managing rendering jobs, monitoring frame status, and interacting with your OpenCue render farm from anywhere.

### What you'll learn

- How to set up and run CueWeb locally
- How to configure the REST Gateway dependency
- How to access and navigate the CueWeb interface
- Basic job management operations

### Prerequisites

Before you begin, ensure you have:

- **OpenCue stack running** (Cuebot, RQD, and PostgreSQL)
- **Docker** installed on your system
- **Node.js** (version 18 or later) for development mode
- **npm** package manager
- **Git** for cloning the repository

---

## Step 1: Set up the REST Gateway

CueWeb requires the OpenCue REST Gateway to communicate with Cuebot. The REST Gateway is **not included** in the main OpenCue Docker Compose stack and must be deployed separately.

### Build the REST Gateway

```bash
# From the OpenCue root directory
docker build -f rest_gateway/Dockerfile -t opencue-rest-gateway:latest .
```

### Run the REST Gateway

```bash
# Start the REST Gateway container
docker run -d --name opencue-rest-gateway \
  --network opencue_default \
  -p 8448:8448 \
  -e CUEBOT_ENDPOINT=cuebot:8443 \
  -e JWT_SECRET=your-secret-key \
  -e REST_PORT=8448 \
  opencue-rest-gateway:latest
```

### Verify the REST Gateway

```bash
# Check if the gateway is running (expects 401 - service is up)
curl -s -o /dev/null -w "%{http_code}" http://localhost:8448/
# Should return: 401 (Unauthorized - this is expected)
```

---

## Step 2: Configure CueWeb

Navigate to the CueWeb directory and set up the environment configuration.

```bash
cd cueweb
```

### Create Environment Configuration

Create a `.env` file with the following configuration:

```bash
# REST Gateway Configuration
NEXT_PUBLIC_OPENCUE_ENDPOINT=http://localhost:8448
NEXT_PUBLIC_URL=http://localhost:3000
NEXT_JWT_SECRET=your-secret-key

# Development Configuration
SENTRY_ENVIRONMENT='development'
NEXTAUTH_URL=http://localhost:3000
NEXTAUTH_SECRET=canbeanything

# Authentication (optional - can be commented out for local development)
# NEXT_PUBLIC_AUTH_PROVIDER=github,okta,google
```

**Important Notes:**
- The `NEXT_JWT_SECRET` must match the REST Gateway's `JWT_SECRET`
- Authentication is disabled by default for local development
- Sentry integration is optional and can be disabled

---

## Step 3: Install Dependencies and Run CueWeb

### Install Dependencies

```bash
npm install
```

### Start CueWeb in Development Mode

```bash
npm run dev
```

You should see output similar to:

```
▲ Next.js 14.2.32
- Local:        http://localhost:3000
- Environments: .env

✓ Ready in 1778ms
```

---

## Step 4: Access CueWeb

1. Open your web browser
2. Navigate to: **http://localhost:3000**
3. You should see the CueWeb interface

### Expected Interface

The CueWeb interface includes:

- **Global Header**: Persistent across every page. Shows the OpenCue logo (theme-aware: black in light mode, white in dark mode) + the **CueWeb** wordmark on the left, six dropdown menus mirroring the CueGUI menu bar — **File**, **Cuebot Facility**, **Cuetopia**, **CueCommander**, **Other** (Attributes, Show Shortcuts, Notify on Shortcut), **Help** (with a search box that finds commands across every menu) — a theme toggle on the right, and an always-visible **Sign out** button. With auth disabled (`NEXT_PUBLIC_AUTH_PROVIDER=`), the Sign out button still appears — clicking it just navigates to `/login`, which shows a **CueWeb Home** button.
- **Left Sidebar**: Same six groups as the header, organized as accordion sections. Click **Collapse** at the bottom to shrink to an icon-only rail.
- **Jobs Dashboard**: View and manage rendering jobs, with CueGUI-parity columns (Launched, Eligible, Finished, User Color, ...).
- **Layers / Frames panels**: Inline below the jobs table. Click a job row to reveal them; click a layer to filter the frames panel; double-click a frame row to open the log viewer.
- **Job Search**: Search for specific jobs by name or pattern.
- **Per-table Filter**: Small substring filter input on each table (Jobs, Layers, Frames) that narrows the rows already loaded.
- **Customizable + reorderable columns**: Every table has a **Columns** dropdown where each column has a visibility checkbox plus `←` / `→` reorder buttons, and a pinned **Reset to Default** button.
- **Frame Management**: Monitor frame status and logs (CueGUI-parity columns include LLU, Memory (RSS), Memory (PSS), Eligible Time, Submission Time, Last Line).
- **Layer Operations**: Manage job layers and dependencies (CueGUI-parity columns include Eligible and a stacked Progress bar).
- **Dark/Light Mode**: Toggle between themes via the sun/moon button in the header
- **Real-time Updates**: Automatic refresh of job status
- **Job-finished Notifications**: Per-row bell button to subscribe to a browser notification when a job reaches `FINISHED`
- **Disable Job Interaction**: Read-only safety toggle in File ▸ Disable Job Interaction (header or sidebar). When on, an amber banner appears under the header and destructive actions (Pause / Unpause / Retry / Eat / Kill) — in the toolbar and in the right-click menus — are dim and inert.
- **Attributes Panel**: Other ▸ Attributes opens a docked drawer with a collapsible key/value tree of the selected entity. Click a row in the jobs table to populate it; pick the dock position (right / bottom / left / top) from the panel's title bar.
- **Bottom Status Bar**: a fixed 24-pixel bar at the bottom of every page shows REST gateway status (a colored dot + Online/Offline + the last round-trip latency), the time since the jobs table last refreshed, and the CueWeb build version. The whole bar turns red when the gateway is unreachable.
- **Breadcrumb Navigation**: detail views (frame log page, per-job comments page) render a small "Home > Jobs > ..." breadcrumb above the content so you can navigate back to the index. Long labels truncate with an ellipsis and the full text appears in a tooltip on hover.
- **Keyboard shortcuts**: Press `?` anywhere (or use **Other ▸ Show Shortcuts**) to open the cheat-sheet. A small toast appears on every triggered shortcut so you know it registered; turn it off via **Other ▸ Notify on Shortcut** if you prefer silence.

---

## Step 5: Basic Operations

### View Jobs

1. The main dashboard displays all jobs from your OpenCue shows
2. Use the **Show** dropdown to filter jobs by show
3. Apply status filters (Active, Paused, Completed)

### Job Management

- **Pause/Resume**: Click the pause/play button for individual jobs
- **Kill Jobs**: Use the stop button to terminate jobs
- **Job Details**: Click on a job name to view detailed information
- **Job Comments**: Right-click a job and choose **Comments**, or click the sticky-note icon next to a job's name, to open the Comments page where you can list / add / edit / delete comments and manage predefined-comment macros

### Frame Operations

1. Click on a job to view its layers and frames
2. **Retry Frames**: Right-click failed frames to retry
3. **View Logs**: Click on frame numbers to view logs
4. **Frame States**: Monitor frame progress with color-coded status
5. **Frame State Filter Chips**: Use the chips above the frames table (`WAITING`, `RUNNING`, `SUCCEEDED`, `DEAD`, `EATEN`, `DEPEND`) — each shows a live count and toggles a filter. Multiple selections combine with OR and persist in the URL via `?frameStates=...`.
6. **Job Progress Tooltip**: Hover the stacked progress bar in the Jobs table to see exact frame counts and percentages for each state.
7. **Subscribe to Completion**: Click the bell in the **Notify** column of the Jobs table to subscribe to a notification when the job reaches `FINISHED`. The subscription always succeeds; the browser's notification permission is an optional upgrade (granted = in-app toast + desktop popup; denied = in-app toast only). Subscriptions persist across page reloads (stored in `localStorage`) and a background poller checks each subscribed job every 15 seconds. When the same job is polled by several tabs concurrently, only one tab actually fires the toast (cross-tab serialization via the Web Locks API).

### Search Functionality

- **Simple Search**: Type show name followed by hyphen (e.g., "myshow-")
- **Regex Search**: Prefix with `!` for advanced patterns (e.g., "!.*test.*")
- **Dropdown Suggestions**: Shows matching jobs as you type

---

## Troubleshooting

### CueWeb won't start

**Problem**: npm run dev fails
```bash
# Check Node.js version
node --version  # Should be 18+

# Clear cache and reinstall
rm -rf node_modules package-lock.json
npm install
```

### Can't connect to OpenCue

**Problem**: "Failed to fetch jobs" error

1. **Check REST Gateway status**:
   ```bash
   docker logs opencue-rest-gateway
   ```

2. **Verify Cuebot connection**:
   ```bash
   docker ps | grep cuebot
   ```

3. **Test REST Gateway**:
   ```bash
   # Generate test JWT
   JWT_TOKEN=$(python3 -c "
   import base64, hmac, hashlib, json, time
   header = {'alg': 'HS256', 'typ': 'JWT'}
   payload = {'sub': 'test', 'exp': int(time.time()) + 3600}
   h = base64.urlsafe_b64encode(json.dumps(header).encode()).decode().rstrip('=')
   p = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip('=')
   m = f'{h}.{p}'
   s = base64.urlsafe_b64encode(hmac.new(b'your-secret-key', m.encode(), hashlib.sha256).digest()).decode().rstrip('=')
   print(f'{m}.{s}')
   ")

   # Test endpoint
   curl -X POST http://localhost:8448/show.ShowInterface/GetShows \
     -H "Authorization: Bearer $JWT_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{}'
   ```

### Authentication Issues

**Problem**: Login loops or authentication errors

1. **Disable authentication** for local development:
   ```bash
   # In .env file, comment out:
   # NEXT_PUBLIC_AUTH_PROVIDER=github,okta,google
   ```

2. **Check JWT secret matching**:
   - Ensure `NEXT_JWT_SECRET` in `.env` matches REST Gateway's `JWT_SECRET`

---

## Production Deployment

For production deployment, see:
- [CueWeb User Guide](/docs/user-guides/cueweb-user-guide) - Complete user documentation
- [CueWeb Developer Guide](/docs/developer-guide/cueweb-development) - Development and deployment guide
- [REST API Reference](/docs/reference/rest-api-reference/) - API documentation

---

## Next Steps

Now that CueWeb is running:

1. **Explore the Interface**: Familiarize yourself with job management features
2. **Configure Authentication**: Set up OAuth providers for multi-user access
3. **Customize Settings**: Adjust table columns and refresh intervals
4. **Monitor Production**: Set up alerts and monitoring for your render farm

For detailed usage instructions, see the [CueWeb User Guide](/docs/user-guides/cueweb-user-guide).