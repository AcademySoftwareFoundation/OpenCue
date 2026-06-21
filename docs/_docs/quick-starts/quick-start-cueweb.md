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

# Leave empty so the client builds same-origin relative API URLs.
# That way CueWeb works from any host the browser reached it at:
# http://localhost:3000 on this machine, or http://<lan-ip>:3000
# from another device on the same network (useful for testing on a
# phone). Only set this to an absolute URL if the API is served on
# a different origin than the UI.
NEXT_PUBLIC_URL=

NEXT_JWT_SECRET=your-secret-key

# Development Configuration
SENTRY_ENVIRONMENT='development'
NEXTAUTH_URL=http://localhost:3000
NEXTAUTH_SECRET=canbeanything

# Authentication (optional - can be commented out for local development)
# NEXT_PUBLIC_AUTH_PROVIDER=github,okta,google

# Optional deep-link template for the Frame context menu's
# "View Log on <editor>" item. {path} is substituted with the
# absolute log path at click time. Empty hides the menu item.
# The OpenCue sandbox docker-compose defaults this to
# vscode://file{path}.
# NEXT_PUBLIC_LOG_EDITOR_URL=vscode://file{path}
```

**Important Notes:**
- The `NEXT_JWT_SECRET` must match the REST Gateway's `JWT_SECRET`
- Authentication is disabled by default for local development
- Sentry integration is optional and can be disabled
- `NEXT_PUBLIC_URL` is empty by default so the same image works from `localhost`, a LAN IP, or any reverse-proxy host without rebuilding. Override it only when the UI and API live on different origins.

### Restrict access by group (optional)

By default every signed-in user can use CueWeb. To limit access by **group membership**, opt in with these env vars (all off/empty by default):

```bash
# Turn the gate on (off by default — leave unset for an open deployment)
CUEWEB_AUTHZ_ENABLED=true
# Groups allowed to use CueWeb at all (empty = everyone signed in)
CUEWEB_ALLOWED_GROUPS=renderwranglers,supervisors
# Groups allowed on the CueCommander admin pages + job submission (empty = everyone)
CUEWEB_ADMIN_GROUPS=supervisors
# The token claim that carries the user's groups (default: groups)
CUEWEB_GROUPS_CLAIM=groups
```

The gate is enforced server-side: a user outside `CUEWEB_ALLOWED_GROUPS` sees an **Access denied** page (API routes get `403`), and non-admins are blocked from the admin pages but keep read-only monitoring. It only works when your authentication provider emits the user's groups in the token, so configure your identity provider's groups claim accordingly. For the sandbox (auth disabled) the gate stays inactive - you don't need any of these.

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
- **Job-finished Notifications**: Two channels - a per-row **Notify bell** for browser notifications (in-app toast + optional desktop popup) and a right-click **Subscribe to Job** entry for *email* notifications sent by Cuebot. Independent of each other.
- **Disable Job Interaction**: Read-only safety toggle in File ▸ Disable Job Interaction (header or sidebar). When on, an amber banner appears under the header and destructive actions (Pause / Unpause / Retry / Eat / Kill) — in the toolbar and in the right-click menus — are dim and inert.
- **Attributes Panel**: Other ▸ Attributes opens a docked drawer with a collapsible key/value tree of the selected entity. Click a row in the jobs table to populate it; pick the dock position (right / bottom / left / top) from the panel's title bar.
- **Bottom Status Bar**: a fixed 24-pixel bar at the bottom of every page shows REST gateway status (a colored dot + Online/Offline + the last round-trip latency), the time since the jobs table last refreshed, and the CueWeb build version. The whole bar turns red when the gateway is unreachable.
- **Breadcrumb Navigation**: detail views (frame log page, per-job comments page) render a small "Home > Jobs > ..." breadcrumb above the content so you can navigate back to the index. Long labels truncate with an ellipsis and the full text appears in a tooltip on hover.
- **Keyboard shortcuts**: Press `?` anywhere (or use **Other ▸ Show Shortcuts**) to open the cheat-sheet. A small toast appears on every triggered shortcut so you know it registered; turn it off via **Other ▸ Notify on Shortcut** if you prefer silence.

The login page (or the **CueWeb Home** button when authentication is disabled):

![CueWeb login page](/assets/images/cueweb/cueweb_cuetopia_monitor_jobs_login.png)


The Dashboard you land on after signing in:

![CueWeb dashboard](/assets/images/cueweb/cueweb_dashboard.png)


The Cuetopia Monitor Jobs view with the jobs table:

![CueWeb Monitor Jobs](/assets/images/cueweb/cueweb_cuetopia_monitor_jobs_mainpage.png)


---

## Step 5: Basic Operations

### View Jobs

1. The main dashboard displays all jobs from your OpenCue shows
2. Use the **Show** dropdown to filter jobs by show
3. Apply status filters (Active, Paused, Completed)

Click a job row to reveal the inline Layers and Frames panels below the jobs table:

![CueWeb inline layers and frames](/assets/images/cueweb/cueweb_cuetopia_monitor_jobs_layersframes.png)


### Job Management

- **Pause/Resume**: Right-click a job and pick **Pause** (or **Unpause** if the job is already paused). The same entry toggles between the two labels based on the job's current state, and is grayed out for Finished jobs.
- **Set Priority**: Right-click a job and pick **Set Priority...** to open a 1-100 slider + number input. Either control drives the value; both stay in sync. The Priority column updates immediately on Apply. Available on both Cuetopia Monitor Jobs and CueCommander Monitor Cue.
- **Manage Dependencies**: Right-click a job to access four dependency entries. **View Dependencies...** opens a read-only dialog listing every depend on the job (Type / Target / Active / OnJob / OnLayer / OnFrame). **Dependency Wizard...** walks you through creating a new depend across every CueGUI `depend.DependType` (Job On Job, Job On Layer / Frame, Hard Depend, Layer On Job / Layer / Frame, Frame By Frame, Frame On Job / Layer / Frame, Layer on Simulation Frame); every picker is multi-select and Done fires the full source x target cross-product. **Drop External Dependencies** and **Drop Internal Dependencies** clear those depend categories in one click; the Jobs table auto-refreshes after success.

  ![View Dependencies dialog](/assets/images/cueweb/cueweb_cuetopia_monitor_jobs_view_dependencies_window.png)

  ![Dependency Wizard type picker](/assets/images/cueweb/cueweb_cuetopia_monitor_jobs_dependency_wizard_menu_select_dependency_type_job_on_job_step1_select_type.png)
- **Kill Jobs**: Use the stop button to terminate jobs
- **Job Details (inline)**: Click on a job row to reveal the inline Layers + Frames panel below the Jobs table.
- **Job Details (tabbed page)**: Right-click a job and choose **View Job Details** to open the tabbed `/jobs/<jobName>` page with Overview / Layers / Frames / Comments / Dependencies tabs. The active tab is stored in the URL so the page is bookmarkable.
- **Job Dependency Graph**: Toggle **Cuetopia &rarr; View Job Graph**, then click a job to mount a read-only, interactive node graph of its dependency tree below the inline Layers + Frames panels. Nodes are color-coded by kind (JOB / LAYER / FRAME), the focus job is ringed, and clicking a node opens that job's detail page.

  ![Dependency graph panel below Layers and Frames](/assets/images/cueweb/cueweb_cuetopia_view_job_graph_monitor_jobs_dependency_graph_only.png)
- **Job Comments**: Right-click a job and choose **Comments**, or click the sticky-note icon in the Jobs table's **Comments** column (sortable, sits right after Name), to open the Comments page where you can list / add / edit / delete comments and manage predefined-comment macros.

The job right-click menu, and the tabbed Job Details page it can open:

![CueWeb job context menu](/assets/images/cueweb/cueweb_cuetopia_monitor_jobs_job_context_menu_open.png)


![CueWeb Job Details overview](/assets/images/cueweb/cueweb_cuetopia_monitor_jobs_view_job_details_page_overview.png)


### Frame Operations

1. Click on a job to view its layers and frames
2. **Retry Frames**: Right-click failed frames to retry (or tap the `⋮` Actions button on the left of the row, on phones)
3. **View Logs**: Double-click a frame row to open the in-browser log viewer. Right-click → **View Log** does the same. The sandbox deploy also ships a **View Log on VSCode** item that launches the rqlog directly in VSCode via the `vscode://file{path}` URL scheme (set `NEXT_PUBLIC_LOG_EDITOR_URL` at build time to target a different editor like Sublime / TextMate / IntelliJ, or to an empty string to hide the menu item).
4. **Frame States**: Monitor frame progress with color-coded status
5. **Frame State Filter Chips**: Use the chips above the frames table (`WAITING`, `RUNNING`, `SUCCEEDED`, `DEAD`, `EATEN`, `DEPEND`) — each shows a live count and toggles a filter. Multiple selections combine with OR and persist in the URL via `?frameStates=...`.
6. **Job Progress Tooltip**: Hover the stacked progress bar in the Jobs table to see exact frame counts and percentages for each state.
7. **Subscribe to Completion - in browser**: Click the bell in the **Notify** column of the Jobs table to subscribe to a notification when the job reaches `FINISHED`. The subscription always succeeds; the browser's notification permission is an optional upgrade (granted = in-app toast + desktop popup; denied = in-app toast only). Subscriptions are saved in your browser and survive page reloads, and a background check runs on each subscribed job every 15 seconds. When the same job is open in several tabs, only one tab shows the notification.
8. **Subscribe to Completion - by email**: For notifications that should survive a browser close, follow you between machines, or fan out to a team alias, right-click the job and pick **Subscribe to Job**. A dialog opens with the job name and an editable **To** address; Save registers the address with Cuebot so Cuebot emails the subscriber when the job finishes. Independent of the Notify bell.
9. **Copy actions**: every row's context menu has copy items - **Copy Job Name** / **Copy Layer Name** / **Copy Frame Name** / **Copy Log Path** - that push the value to the clipboard with a confirmation toast. Works on `http://localhost:3000` and also when accessing CueWeb at a LAN IP over plain HTTP.
10. **Mobile**: load CueWeb on a phone via `http://<lan-ip>:3000` from the same network (e.g. `ipconfig getifaddr en0` on the Mac shows the IP). The hamburger button at the top-left opens a nav drawer with every menu group; each row's leftmost `⋮` button replaces the right-click menu on touch.

### Search Functionality

- **Simple Search**: Type show name followed by hyphen (e.g., "myshow-")
- **Regex Search**: Prefix with `!` for advanced patterns (e.g., "!.*test.*")
- **Dropdown Suggestions**: Shows matching jobs as you type

![CueWeb job search](/assets/images/cueweb/cueweb_cuetopia_monitor_jobs_search_jobs.png)


---

## Step 6 (optional): Submit a job from the browser (CueSubmit)

CueWeb ships a browser-based equivalent of the standalone CueSubmit CLI tool so you don't need a separate desktop install just to launch a test job:

![CueSubmit menu options](/assets/images/cueweb/cueweb_cuesubmit_menu_options.png)

![CueSubmit Submit Job page](/assets/images/cueweb/cueweb_cuesubmit_submit_job.png)

1. Click **CueSubmit > Submit Job** in the top header (or the matching entry in the sidebar / mobile drawer).
2. In **Job Info** fill in a Job Name (e.g. `quickstart_test`), pick `testing` for Show, type a Shot like `test_shot`, leave Facility as `[Default]`, and confirm Username.
3. In **Layer Info** fill in a Layer Name (e.g. `layer1`), set Frame Spec to `1-3`, leave Chunk Size at `1` and Memory at the `256m` default, and keep Job Type set to **Shell**.
4. In **Shell options** type `sleep 5` for Command To Run. Watch the **Final command** field at the bottom update per-keystroke.
5. Click **Submit**. CueWeb redirects you to the job's detail page where the three frames will go WAITING -> RUNNING -> SUCCEEDED in a few seconds.
6. Click **View in Monitor Jobs** in the detail-page header to open Cuetopia with the new job already loaded.

The form keeps an autocomplete history (per browser) for Job Name, Shot, and Layer Name across submissions, and auto-saves a draft on every keystroke so an accidental refresh never wipes a multi-layer setup. Click **Reset** to clear the form back to a blank canvas.

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