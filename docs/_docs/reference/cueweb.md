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

### Optional Build-Time Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `NEXT_PUBLIC_APP_VERSION` | Build version shown in the bottom status bar. Falls back to `cueweb/package.json#version` when unset. CI typically passes the Git SHA via `--build-arg`. | (package.json version) |
| `NEXT_PUBLIC_CUEBOT_FACILITIES` | Comma-separated facility list shown in the Cuebot Facility menu. | `local,dev,cloud,external` |
| `CUEBOT_<NAME>_REST_GATEWAY_URL` | Per-facility REST gateway base URL (server-only; `<NAME>` is the uppercased facility name). Falls back to `NEXT_PUBLIC_OPENCUE_ENDPOINT`. | (unset &rarr; default gateway) |
| `CUEBOT_<NAME>_JWT_SECRET` | Per-facility JWT secret the target gateway trusts (server-only). Falls back to `NEXT_JWT_SECRET`. | (unset &rarr; default secret) |
| `NEXT_PUBLIC_DOCS_URL` | Online User Guide link in the Help menu. | `https://www.opencue.io/docs/` |
| `NEXT_PUBLIC_SUGGESTIONS_URL` | Make a Suggestion link in the Help menu. | CueGUI default (GitHub issues, `enhancement` template) |
| `NEXT_PUBLIC_BUGS_URL` | Report a Bug link in the Help menu. | CueGUI default (GitHub issues, `bug_report` template) |
| `NEXT_PUBLIC_URL` | Base URL the client uses when calling the Next.js API routes. **Default empty** = the client builds same-origin relative URLs (`/api/job/getjobs`, ...) so CueWeb works from any host the browser reached it at (`http://localhost:3000` on the dev Mac, `http://<lan-ip>:3000` from a phone on the same network). Set to an absolute URL only if your deployment serves the API on a different origin than the UI. | (empty) |
| `NEXT_PUBLIC_LOG_EDITOR_URL` | URL template for the Frame context menu's **View Log on \<editor\>** item. The literal `{path}` is substituted with the absolute rqlog path at click time. Common values: `vscode://file{path}`, `vscode-insiders://file{path}`, `subl://open?url=file://{path}`, `txmt://open?url=file://{path}`, `idea://open?file={path}`. Empty hides the menu item entirely. The sandbox `docker-compose.yml` defaults to `vscode://file{path}`. | `vscode://file{path}` (sandbox) / empty (Dockerfile default) |
| `NEXT_PUBLIC_EMAIL_DOMAIN` | Email domain used to derive the **Email Artist...** dialog defaults: `<user>@<domain>` for **To**, `<show>-<suffix>@<domain>` for **From** and **CC**. See [Email Artist dialog](#email-artist-dialog). | `your.domain.com` |
| `NEXT_PUBLIC_EMAIL_SUPPORT_SUFFIX` | Per-show support alias suffix used in the **Email Artist...** dialog's From / CC defaults (`<show>-<suffix>@<domain>`). Matches CueGUI's "production support team" alias convention. | `pst` |
| `NEXT_PUBLIC_EMAIL_REQUEST_CORES_SUFFIX` | Per-show support alias suffix used in the **Request Cores...** dialog's CC default (`<show>-<suffix>@<domain>`). Distinct from the Email Artist `pst` alias because CueGUI's `RequestCoresDialog` traditionally targets a different team queue. | `support` |
| `NEXT_PUBLIC_SUBSCRIBE_FROM_EMAIL` | Informational **From** label shown by the **Subscribe to Job** dialog. The actual email sender is whatever Cuebot is configured with - this is purely a UI hint. See [Subscribe to Job dialog](#subscribe-to-job-dialog). | `opencue-noreply@<NEXT_PUBLIC_EMAIL_DOMAIN>` |

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

The main jobs table (`cueweb/app/jobs/columns.tsx` + `cueweb/app/jobs/data-table.tsx`) displays rendering jobs with the following columns, in their default order:

| Column | Description | Sortable |
|--------|-------------|----------|
| **(select)** | Row checkbox. Anchored at the leftmost position - column reorder skips over it. | No |
| **Name** | Two-line cell: `<show>-<shot>-<user>` on top, rest of the job name underneath. | Yes |
| **Comments** | Sticky-note icon when the job has one or more comments; empty otherwise. Sortable so users can pull jobs-with-comments to the top (CueGUI parity: `JobMonitorTree`'s note-icon column). Clicking the icon opens the per-job Comments page in a new tab. | Yes |
| **State** | Current job state badge (see [Job States](#job-states)). | Yes |
| **Done / Total** | `<succeededFrames> of <totalFrames>`. | Yes |
| **Running** | Running frame count. | Yes |
| **Dead** | Failed frame count. | Yes |
| **Eaten** | Eaten frame count. | Yes |
| **Wait** | Waiting frame count. | Yes |
| **MaxRss** | Max RSS observed across the job's frames (human-readable, e.g. `512M`). | Yes |
| **Age** | Wall-clock job age formatted `HHH:MM`. | Yes |
| **Readable Age** | Same age in human-friendly form (e.g. `2h 14m`). | Yes |
| **Launched** | `job.startTime` formatted `YYYY-MM-DD HH:MM`. Mirrors CueGUI's "Launched" column. | Yes |
| **Eligible** | `job.eligibleTime` formatted the same way. Blank when the field is zero / unset. | Yes |
| **Finished** | `job.stopTime`. Blank while the job is still running. | Yes |
| **User Color** | Per-job color swatch backed by `localStorage["cueweb.userColors"]` (map of `jobId -> #rrggbb`). Click the swatch to pick a color from the native picker; right-click or click the `×` button to clear. Cross-tab sync via the standard `storage` event plus an internal `cueweb:user-colors` `CustomEvent` for same-tab listeners. | No |
| **Progress** | Stacked frame-state progress bar with a hover tooltip showing exact frame counts and percentages for `SUCCEEDED`, `RUNNING`, `WAITING`, `DEPEND`, and `DEAD` states. | No |
| **Notify** | Per-row bell button to subscribe to a notification when the job reaches `FINISHED`. See [Job-finished notifications](#job-finished-notifications). | No |

### Layers Table

The inline Layers table (`cueweb/app/layers/layer-columns.tsx`, rendered by `SimpleDataTable` inside `JobDetailsInline`) ships these columns in default order:

| Column | Description |
|--------|-------------|
| **Dispatch Order** | Per-layer dispatch order assigned by Cuebot. |
| **Name** | Layer name (clickable to filter the Frames panel and populate the Attributes panel). |
| **Services** | Render services declared on the layer. |
| **Limits** | Resource-limit names. |
| **Range** | Frame range (e.g. `1-100x2`). |
| **Cores** | Minimum reserved cores. |
| **Memory** | Minimum reserved memory (human-readable). |
| **Gpus** | Minimum reserved GPUs. |
| **Gpu Memory** | Minimum reserved GPU memory. |
| **MaxRss** | High-water RSS observed on the layer. |
| **Total** | Total frame count on this layer. |
| **Done** | Succeeded frames. |
| **Run** | Running frames. |
| **Depend** | Frames in DEPEND state. |
| **Wait** | Waiting frames. |
| **Eaten** | Eaten frames. |
| **Dead** | Dead frames. |
| **Avg** | Average frame seconds, formatted `HH:MM:SS`. |
| **Tags** | Layer tags. |
| **Progress** | Same stacked animated bar as the Jobs table, fed by `getLayerProgressSegments` (`cueweb/app/utils/layer_progress_utils.ts`). Hover tooltip shows per-state counts. |
| **Timeout** | Layer timeout (`HHH:MM`). |
| **Timeout LLU** | Last-log-update timeout (`HHH:MM`). |
| **Eligible** | `layer.eligibleTime` formatted `YYYY-MM-DD HH:MM`. |

### Frames Table

The Frames table (`cueweb/app/frames/frame-columns.tsx`, rendered by `SimpleDataTable`) ships these columns:

| Column | Description |
|--------|-------------|
| **Order** | Dispatch order assigned by Cuebot. |
| **Frame** | Frame number. |
| **Layer** | Layer name (clickable link into the frame log viewer). |
| **Status** | Frame state badge (see [Frame States](#frame-states)). |
| **Cores** | Cores assigned to the running frame (parsed from `lastResource`). |
| **GPUs** | GPUs assigned. |
| **Host** | `lastResource` string (`host/cores/gpus`). |
| **Retries** | Retry count. |
| **CheckP** | Checkpoint count. |
| **Runtime** | `(stop - start)` if stopped, else `(now - start)`, formatted `HH:MM:SS`. |
| **LLU** | Elapsed time since the frame's log was last updated (`now - lluTime`, formatted `HH:MM:SS`). Only populated for `RUNNING` frames; blank for `WAITING` / `DEPEND` / `SUCCEEDED` / `DEAD` to match CueGUI. |
| **Memory (RSS)** | `used_memory` while RUNNING, `max_rss` after stop. |
| **Memory (PSS)** | `used_pss` while RUNNING, `max_pss` after stop. |
| **GPU Memory** | `used_gpu_memory` while RUNNING, `max_gpu_memory` after stop. |
| **Remain** | Placeholder column for CueGUI's ETA buffer; renders an em-dash until the predictor is wired into CueWeb. Hidden by default in the inline panel. |
| **Start Time** | `frame.startTime` formatted `YYYY-MM-DD HH:MM`. |
| **Stop Time** | `frame.stopTime` formatted `YYYY-MM-DD HH:MM`. |
| **Eligible Time** | `frame.eligibleTime` formatted `YYYY-MM-DD HH:MM`. |
| **Submission Time** | `frame.submissionTime` formatted `YYYY-MM-DD HH:MM`. |
| **Last Line** | Placeholder column for the per-frame log-tail fetch; renders an em-dash until that fetch is wired in. |

### Columns dropdown (visibility + ordering)

Every data table (Jobs, Layers, Frames) renders a **Columns** dropdown in its per-table toolbar.

| Control | Behavior |
|---------|----------|
| **Reset to Default** | Pinned at the top of the dropdown as a `secondary` button. Clears both column-visibility and column-order back to whatever the column definitions declare. |
| **Checkbox** (per row) | Toggle the column's visibility. The menu stays open after every click so the user can chain several toggles without reopening it. |
| **`←` / `→`** (per row) | Nudge the column one slot left / right within the user-reorderable subset. Non-hideable system columns (the row-select checkbox) stay anchored - swaps never reach across them. Buttons are disabled at the bounds of the reorderable set. |

Persistence keys:

| Table | Visibility key | Order key |
|-------|---------------|-----------|
| Jobs | `columnVisibility` | `columnOrder` |
| Layers | `cueweb.layers.columnVisibility` | `cueweb.layers.columnOrder` |
| Frames | `cueweb.frames.columnVisibility` | `cueweb.frames.columnOrder` |

Implementation: each table wires TanStack's `state.columnOrder` + `onColumnOrderChange` and reads/writes the matching `localStorage` key. The reorder helper (`moveColumn`) operates on the hideable subset of `columnOrder` so non-hideable columns stay in their original positions.

### Per-table substring filter

Each data table renders a small **Filter jobs / layers / frames...** `<input type="search">` next to its Columns dropdown.

| Aspect | Description |
|--------|-------------|
| **Source** | TanStack's built-in `globalFilter` state + `getFilteredRowModel()`. |
| **Match** | Case-insensitive substring against every visible column's accessor value (status badge text, runtime strings, etc. - everything that lands in the table's flat representation). |
| **Pagination** | Auto-resets to page 1 on every keystroke so the user never sits on an empty page after narrowing. |
| **Clear** | An `×` button appears inside the input once it has a value; clears the filter in one click. Pressing `Esc` while focused also clears the native `<input type="search">`. |
| **Scope** | Client-side only - distinct from the top-of-page "Search jobs - Enter to load" box on the Jobs page which hits Cuebot to load matching jobs. |

### Group By (Jobs table)

The Jobs table toolbar has a **Group By** dropdown that mirrors CueGUI's `MonitorJobsPlugin` grouping modes:

| Mode | Layout | Notes |
|------|--------|-------|
| **Clear** | Flat list (default). | No grouping. |
| **Dependent** | Parent / child dependency **tree**. | The Name column renders a chevron + depth-based indent in front of each row. A job that other monitored jobs depend on becomes a parent; the dependents nest under it. Click the chevron to collapse / expand a subtree. |
| **Show** | One collapsible header per show. | Header text is the show name (`(no show)` when missing); count in parentheses. |
| **Show-Shot** | `<show> - <shot>` headers. | Same collapse behavior. |
| **Show-Shot-Username** | `<show> - <shot> - <user>` headers. | Same. |

**Dependent tree details:**

- On entry, the dialog fires `/job.JobInterface/GetWhatDependsOnThis` for every monitored job in parallel and caches the result in component state, keyed by `jobId`. Adding a new monitored job fires one extra RPC; unmonitoring a job drops the cache entry. The cache is cleared when the page reloads.
- The tree builder walks the cached graph: a job's children are the *monitored* jobs whose `depend_er_job` field appears in the parent's depend list (active depends only, matching CueGUI). Jobs that appear as a child of any other monitored job are pulled under that parent; everyone else is a root.
- The Name column reads `table.options.meta.dependencyTree` (a `Map<jobId, { depth, hasChildren }>` plus a `toggle(jobId)` callback) and renders the chevron + indent. Empty `dependencyTree` falls back to the default centered layout.
- Filtering, sorting, and pagination all still apply on top of the tree: an orphaned child (parent filtered out) is re-rooted at depth 0 so the row never disappears silently.

### Inline JobDetails (Layers + Frames panel)

Clicking a row in the Jobs table populates `JobDetailsInline` (`cueweb/components/ui/job-details-inline.tsx`), which renders the **Layers** and **Frames** tables stacked below the jobs grid (CueGUI Monitor Jobs + Monitor Job Details parity).

| Behavior | Description |
|----------|-------------|
| **Layers panel** | Lists every layer in the selected job, including the Progress bar and Eligible time. |
| **Layer-click** | Toggles a frames-table filter to that layer (`frame.layerName === layer.name`) and pushes the layer's attributes into the docked Attributes panel. Clicking the same layer again clears the filter and re-selects the job in Attributes. |
| **Frames panel** | Lists every frame in the job (or the layer-filtered subset). Total count shows `X of Y` when filtered. |
| **Refresh** | Both panels poll every 5 seconds, with cancellation guards so a stale response cannot overwrite a fresh selection. |
| **Log viewer** | Double-clicking any frame row opens the log viewer (`/frames/<frameName>?frameId=...&frameLogDir=...`). |

### Job dependency graph panel

A read-only, interactive node graph of a job's dependency tree, rendered with [React Flow](https://reactflow.dev/) (`@xyflow/react`) and laid out with [dagre](https://github.com/dagrejs/dagre). It mirrors CueGUI's `JobMonitorGraph` Monitor-Jobs dock. Lives in `JobDependencyGraph` (`cueweb/components/ui/job-dependency-graph.tsx`).

**Toggle.** The checkable **Cuetopia &rarr; View Job Graph** entry (header dropdown in `app-header.tsx`, sidebar in `app-sidebar.tsx`, both expanded and collapsed) drives a shared `useShowDependencyGraph()` hook. The hook persists to `localStorage["cueweb.jobs.showDependencyGraph"]` and syncs in-tab via the `cueweb:show-dependency-graph-changed` CustomEvent and cross-tab via the `storage` event, so the menu items, the panel header toggle, and the panel itself stay in lockstep without prop drilling.

![View Job Graph entry in the Cuetopia menu](/assets/images/cueweb/cueweb_cuetopia_view_job_graph_menu.png)

**Mounting.** When the toggle is on, `JobDetailsInline` (`cueweb/components/ui/job-details-inline.tsx`) renders the graph as a third stacked panel (`id="job-dependency-graph-panel"`) under Layers and Frames, with a header naming the focus job and a close button.

![Dependency graph panel below the inline Layers and Frames panels](/assets/images/cueweb/cueweb_cuetopia_view_job_graph_monitor_jobs_dependency_graph.png)

![Dependency graph panel below the inline Layers and Frames panels (dark mode)](/assets/images/cueweb/cueweb_cuetopia_view_job_graph_monitor_jobs_dependency_graph_dark.png)

| Behavior | Description |
|----------|-------------|
| **Tree walk** | Breadth-first search from the focus job over both directions - `GetDepends` (downstream) and `GetWhatDependsOnThis` (upstream, active depends only) - bounded by `maxDepth` (default 4) and a visited-job set to break cycles. Mirrors CueGUI's `JobMonitorGraph.getRecursiveDependentJobs`. |
| **Name resolution** | Each BFS hop first resolves a job name to its UUID via `/api/job/getjobs` with an anchored `^name$` regex (Cuebot rejects name-only depend lookups). Resolved IDs are memoized in a `Map`, so a 12-job chain costs ~12 lookups across the whole walk, not 12 per hop. |
| **Silent fetches** | All BFS requests go through a `silentPost` helper that bypasses `accessGetApi`. Partial failures (jobs in other shows, unmonitored/finished + pruned) return `null` instead of cascading red "Resource not found" toasts. |
| **Nodes** | Custom `DependencyNode` renderer: monospace, truncated label with the full name in a `title` tooltip, a kind label and color-coded left border (JOB = blue, LAYER = amber, FRAME = emerald), and a stronger ring on the focus job. Layer / frame nodes carry a hierarchical label so their parent job/layer is visible. |
| **Edges** | Directed upstream &rarr; downstream (top-to-bottom); animated when the depend is active. |
| **Navigation** | Clicking a node calls `onNodeNavigate(jobName)` if supplied, else `router.push("/jobs/<jobName>?tab=overview")`. |
| **Theme-aware** | dagre lays out fresh per call (no module-level singleton); the data fetch is keyed on `job.id` so toggling dark/light does not re-walk the tree. The crosshair-cursor SVG is scoped per instance via a `data-graph-id` attribute so two graphs on a page do not collide. |
| **Empty / loading states** | `Loading dependency graph...` while walking; `No dependencies found for this job.` when only the focus node remains. |

![The dependency graph panel on its own](/assets/images/cueweb/cueweb_cuetopia_view_job_graph_monitor_jobs_dependency_graph_only.png)

### Monitor Hosts

A host registry at `/hosts` (`cueweb/app/hosts/page.tsx`), the CueWeb equivalent of CueGUI's `MonitorHostsPlugin` / `HostMonitorTree`. Reached from **CueCommander &rarr; Monitor Hosts** (header dropdown and sidebar) or the dashboard hosts widget's **View hosts** link.

![Monitor Hosts entry in the CueCommander menu](/assets/images/cueweb/cueweb_cuecommander_monitor_hosts_menu.png)

![CueWeb Monitor Hosts page](/assets/images/cueweb/cueweb_cuecommander_monitor_hosts.png)

| Behavior | Description |
|----------|-------------|
| **Data source** | Loads via `getHosts()` (`app/utils/get_utils.ts`), which posts to the `/api/host/gethosts` proxy &rarr; `host.HostInterface/GetHosts`. `getHosts()` returns an array on success and throws on a failed request so the page can tell a real failure from an empty registry. |
| **Columns** | Name, State, Locked, NIMBY, Cores (Idle/Total), Memory (Idle/Total), Free /mcp (`app/hosts/columns.tsx`). State and Locked reuse the shared `Status` badge. |
| **Sorting** | Resource columns sort by their underlying numeric value, not the formatted string: Cores and Memory by idle ratio (`idleRatio`), Free /mcp by byte count. Memory / mcp arrive from the gateway as KB-in-string and are parsed/formatted by `app/hosts/host_format_utils.ts` (`kbStringToNumber`, `kbStringToHuman`). |
| **Table** | Rendered by the shared `SimpleDataTable` with the `isHostsTable` flag - host-specific filter placeholder and empty-state copy, and the host row context menu. Column show/hide persists to `localStorage["cueweb.hosts.columnVisibility"]`. |
| **Refresh** | Auto-refreshes every 30s. A failed poll keeps previously loaded rows; a failed first load renders an inline error with a **Retry** button. |
| **Row actions** | A right-click `HostContextMenu` (`components/ui/context_menus/action-context-menu.tsx`) exposes Lock / Unlock, Reboot / Reboot When Idle, and Edit Tags. The action helpers (`lockHosts`, `unlockHosts`, `rebootHosts`, `rebootHostsWhenIdle`, `addHostTags`, `removeHostTags` in `app/utils/action_utils.ts`) post to the `/api/host/action/*` proxies and return a success boolean from `performAction`. Lock/Reboot/Edit-Tags open confirmation dialogs (`host-lock-dialog.tsx`, `host-reboot-dialog.tsx`, `edit-host-tags-dialog.tsx`); on success they fire a `cueweb:hosts-changed` event (`host-action-events.ts`) so the page optimistically patches the affected row and reconciles on the next fetch. The Edit Tags dialog autocompletes from existing registry tags via the shared `command.tsx` (cmdk) primitive. |
| **Gating** | Unlock is disabled for `NIMBY_LOCKED` hosts; Reboot is disabled while `REBOOTING`; Reboot When Idle is disabled while `REBOOTING` or `REBOOT_WHEN_IDLE`. |
| **Server-side filtering** | Not yet implemented; filtering is client-side over the loaded rows. |

### Host detail page

A per-host page at `/hosts/[host-name]` (`cueweb/app/hosts/[host-name]/page.tsx`) reached by clicking a host's Name in the Monitor Hosts table.

![Host detail page - Overview tab](/assets/images/cueweb/cueweb_cuecommander_monitor_hosts_host_detail_page_overview.png)

| Behavior | Description |
|----------|-------------|
| **Resolution** | Resolves the host by name via `findHostByName()` (`app/utils/get_utils.ts`) &rarr; `/api/host/findhost` &rarr; `host.HostInterface/FindHost`. |
| **Tabs** | Overview / Procs / Comments / Tags, with the active tab synced to the `?tab=` query (same pattern as the job detail page). |
| **Procs** | Loads via `getHostProcs()` &rarr; `/api/host/getprocs` &rarr; `host.HostInterface/GetProcs`, rendered by `SimpleDataTable` with the read-only `isProcsTable` flag (no row context menu) and `proc-columns.tsx`. Auto-refreshes every 15s; an `onRowClick` opens the proc's frame log using the proc's `logPath` as the `frameLogDir`. |
| **Comments** | Loads via `getHostComments()` &rarr; `/api/host/getcomments` &rarr; `host.HostInterface/GetComments` (read-only list). |
| **Tags** | Renders `host.tags`; an **Edit tags** button dispatches the same `cueweb:open-host-tags` event as the table menu. The page listens for `cueweb:hosts-changed` to patch and silently reconcile its host. |

### Allocations

An allocations table at `/allocations` (`cueweb/app/allocations/page.tsx`), the CueWeb equivalent of CueGUI's CueCommander Allocations window. Reached from **CueCommander &rarr; Allocations** (header dropdown and sidebar).

![CueWeb Allocations page](/assets/images/cueweb/cueweb_cuecommander_allocation.png)

| Behavior | Description |
|----------|-------------|
| **Data source** | Loads via `getAllocations()` (`app/utils/get_utils.ts`) &rarr; `/api/allocation/getall` &rarr; `facility.AllocationInterface/GetAll`. Auto-refreshes every 30s. |
| **Columns** | Name (links to `/hosts?allocation=<name>`), Tag, then a cores group (Cores, Idle, Locked, Down, Repair) and a hosts group (Hosts, Locked, Down, Repair) - `app/allocations/allocation-columns.tsx`. Numeric columns sort by their underlying value; cores render as integers. |
| **Derived columns** | `AllocationStats` does not expose Down cores, Repair cores, or Repair hosts, so the page fetches the host list once (`getHosts()`) and aggregates it on `allocName` via `computeAllocationHostStats` / `buildAllocationRows` (`app/allocations/allocation-utils.ts`). The host fetch is best-effort - those columns fall back to 0 if it fails. |
| **Table** | Rendered by the shared `SimpleDataTable` with the read-only `isAllocationsTable` flag - allocation-specific filter/empty-state copy and no row context menu. Column show/hide persists to `localStorage["cueweb.allocations.columnVisibility"]`. |

### Shows

A shows registry at `/shows` (`cueweb/app/shows/page.tsx` + `shows-client.tsx`), the CueWeb equivalent of CueGUI's CueCommander Shows window. Reached from **CueCommander &rarr; Shows** (header dropdown and sidebar).

![CueWeb Shows page](/assets/images/cueweb/cueweb_cuecommander_shows.png)

| Behavior | Description |
|----------|-------------|
| **Data source** | Loads via `getActiveShows()` (`app/utils/get_utils.ts`) &rarr; `/api/show/getactiveshows` &rarr; `show.ShowInterface/GetActiveShows`. Auto-refreshes every 30s and re-fetches on the `cueweb:shows-changed` event. |
| **Columns** | Show Name (links to the [show detail page](#show-detail-page-group-tree)), Cores Run (`reserved_cores`), Frames Run (`running_frames`), Frames Pending (`pending_frames`), Jobs (`pending_jobs`) - `app/shows/show-columns.tsx`. Numeric columns sort by their underlying value. |
| **Table** | Rendered by the shared `SimpleDataTable` with the `isShowsTable` flag - show-specific filter placeholder and empty-state copy, and the `ShowContextMenu`. Column show/hide persists to `localStorage["cueweb.shows.columnVisibility"]`. |
| **Create Show** | The `Create Show` button opens `create-show-dialog.tsx`: a unique alphanumeric name (duplicate-checked via `FindShow`) plus an optional per-allocation Subscriptions section (checkbox + Size + Burst, allocations from `getAllocations()`). Creates the show then a subscription on each checked allocation. |
| **Row actions** | A right-click `ShowContextMenu` (`components/ui/context_menus/action-context-menu.tsx`) exposes **Show Properties** and **Create Subscription...**, opened via the `cueweb:open-show-properties` / `cueweb:open-create-subscription` events (`components/ui/show-action-events.ts`). |

#### Show Properties dialog

`show-properties-dialog.tsx` (CueGUI `ShowDialog` parity), four tabs:

| Tab | Contents / RPCs |
|-----|-----------------|
| **Settings** | Default max cores (`SetDefaultMaxCores`), default min cores (`SetDefaultMinCores`), comment notification email (`SetCommentEmail`). Inputs are validated (non-negative, min &le; max) before save. |
| **Booking** | Enable booking (`EnableBooking`), enable dispatch (`EnableDispatching`). |
| **Statistics** | Read-only `show_stats` counts. |
| **Raw Show Data** | Read-only JSON dump of the show. |

Save calls only the setters whose value changed (via the `action_utils` helpers `setShowDefaultMaxCores` / `setShowDefaultMinCores` / `setShowCommentEmail` / `enableShowBooking` / `enableShowDispatching`), then fires `cueweb:shows-changed`.

#### Create Subscription dialog

`create-subscription-dialog.tsx` (CueGUI `SubscriptionCreator` parity): Show + Alloc dropdowns (`getShows()` / `getAllocations()`), Size (default 100), Burst (default 110). On **OK** it calls `createShowSubscription()` &rarr; `/api/show/action/createsubscription` &rarr; `show.ShowInterface/CreateSubscription`. A show has at most one subscription per allocation; the route maps Cuebot's duplicate-key error to a short, user-facing message.

#### Show detail page (group tree)

Clicking a show name opens `/shows/[showName]` (`cueweb/app/shows/[showName]/page.tsx`), a client page that resolves the show via `findShow()` (`app/utils/show_utils.ts` &rarr; `/api/show/findshow` &rarr; `show.ShowInterface/FindShow`) and renders its **group tree** (`components/group-tree/`).

![CueWeb show detail page with the group tree](/assets/images/cueweb/cueweb_cuecommander_shows_group_tree_page.png)

| Behavior | Description |
|----------|-------------|
| **Data source** | Groups load via `getShowGroups()` &rarr; `/api/show/getgroups` &rarr; `show.ShowInterface/GetGroups`; a group's jobs load lazily on first expand via `getGroupJobs()` &rarr; `/api/group/getjobs` &rarr; `job.GroupInterface/GetJobs` (each group fetched at most once). |
| **Expand state** | The set of expanded group ids is mirrored to the `?expanded=` query param, so a given view is deep-linkable. |
| **Reparent** | Dragging a group onto another calls `reparentGroups()` &rarr; `/api/group/action/reparentgroups` &rarr; `job.GroupInterface/ReparentGroups`; dragging a job onto a group calls `reparentJobs()` &rarr; `/api/group/action/reparentjobs` &rarr; `job.GroupInterface/ReparentJobs`. Drop targets are validated client-side (no self/descendant cycles, no same-parent no-ops), and reparents are serialized one at a time and rolled back on a failed RPC. |
| **Refresh** | The header **Refresh** button remounts the tree to reload groups and jobs. |

### Job-finished notifications

| Behavior | Description |
|----------|-------------|
| **Trigger** | Click the bell in the **Notify** column. The bell always subscribes immediately; OS notification permission is requested afterwards as an optional upgrade. |
| **Toast wording** | Branches on the prompt result: `granted` (in-app + desktop popup), `denied` (in-app only, instruction to enable in browser settings), `default` (in-app only, user dismissed the prompt). |
| **Polling** | An app-wide `JobSubscriptionPoller` provider polls each subscribed job's state every 15 seconds via the REST gateway. |
| **Notification** | When a subscribed job becomes `FINISHED`, `fireCompletionNotice(entry)` fires an in-app `toast.success("Job finished: <jobName>")` (always) and a desktop `new Notification(jobName, { body: "Job finished" })` (when `Notification.permission === "granted"` at fire-time). |
| **Cross-tab serialization** | The re-read + fire + mark sequence runs inside `navigator.locks.request("cueweb:notify-<jobId>", ...)` so only one tab toasts when several poll the same job concurrently. Falls back to a direct call when `navigator.locks` is unavailable. |
| **Persistence** | Subscriptions are stored in `localStorage` under `cueweb:job-subscriptions` and survive page reloads; cleared when the browser site data is cleared. |
| **Auto-cleanup** | If a subscribed job no longer exists in Cuebot (the lookup returns null), the subscription is removed on the next poll. |
| **Cross-component sync** | Mutations dispatch a `cueweb:subscriptions-changed` window event so the bell and poller stay in sync within the tab; the `storage` event syncs across tabs. |

### Keyboard shortcuts overlay (+ menu access)

| Aspect | Description |
|--------|-------------|
| **Component** | `KeyboardShortcuts` in `cueweb/components/ui/shortcuts-overlay.tsx`, mounted once from `cueweb/app/layout.tsx`. |
| **Keys** | `?` open overlay; `Esc` close overlay; `/` focus jobs search (`cueweb:focus-search`); `r` refresh jobs table (`cueweb:refresh-now`); `t` toggle light/dark theme. |
| **Suppression** | Single-letter keys are ignored while typing into `<input>`, `<textarea>`, `<select>`, or any `contenteditable` element. Modifier-key combos (Ctrl / Cmd / Alt) are passed through to the browser. |
| **Menu access** | Header **Other ▸ Show Shortcuts** and Sidebar **Other ▸ Show Shortcuts** both dispatch a `cueweb:open-shortcuts` `CustomEvent` on `window` that the overlay listens for. |
| **Toast on shortcut** | When **Other ▸ Notify on Shortcut** is checked (default ON), every triggered shortcut also fires a small toast naming the action (e.g. `Shortcut: r → Refresh table`). |
| **Pref storage** | `localStorage["cueweb.shortcutNotifications"]`. Cross-tab sync via the standard `storage` event plus an internal `cueweb:shortcut-notifications-changed` `CustomEvent`. Read imperatively at fire-time so toggling the pref takes effect on the very next keypress. |

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

### Frame State Filter Chips

Above the frames table, one filter chip is rendered per supported state. Each chip shows the current frame count for that state and toggles the filter on click.

| Behavior | Description |
|----------|-------------|
| **States** | `WAITING`, `RUNNING`, `SUCCEEDED`, `DEAD`, `EATEN`, `DEPEND` |
| **Combination** | OR semantics - frames matching any selected state are shown |
| **Empty selection** | All frames are shown when no chip is selected |
| **URL parameter** | `frameStates` (comma-separated, e.g., `?frameStates=WAITING,DEAD`); whitespace is trimmed and duplicates are removed |
| **Counts** | Always computed against the unfiltered data set |
| **Pagination** | The table jumps to page 1 when the selection changes (polling-driven data refreshes do not reset the page) |

### Job Comments Page

CueWeb mirrors the CueGUI **Comments** dialog (`cuegui/cuegui/Comments.py`) at `/jobs/<job-name>/comments`.

| Aspect | Description |
|--------|-------------|
| **Required query params** | `jobId` (job UUID). The page calls `getJob(jobId)` to populate the comment list. |
| **Viewer identity** | Derived client-side from the authenticated NextAuth session (`/api/auth/session`), never from URL parameters. Used only to drive UI state. |
| **Comment fields** | `id`, `timestamp` (unix seconds), `user`, `subject`, `message`. Mirrors `comment.Comment` in `proto/src/comment.proto`. |
| **Markdown** | Messages are rendered with `react-markdown` + `rehype-sanitize` to strip embedded HTML/scripts. |
| **Edit / delete authorization** | Server-side ownership enforcement in Cuebot is authoritative. The client adds a convenience gate that enables the editor/delete only when `comment.user === currentUser` (the session-derived identity); the URL is never used as an auth signal. |
| **Predefined macros** | Stored in `localStorage` under `cueweb-comment-macros`. Scope is per-browser; not synced. |
| **Indicator icon** | The Jobs table has a dedicated **Comments** column (right after Name) showing a sticky-note icon when `Job.hasComment` is true. The column is sortable so users can pull jobs-with-comments to the top. Updated on the regular jobs-table polling cycle. |

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

All three context menus (`JobContextMenu`, `LayerContextMenu`, `FrameContextMenu`) live in `cueweb/components/ui/context_menus/action-context-menu.tsx` and follow the CueGUI Monitor Jobs / Monitor Job Details structure. Items that depend on dialogs / backend integrations not yet implemented in CueWeb route through a `notYetImplemented(label)` placeholder. Destructive items are auto-disabled when **Disable Job Interaction** is on. Menus scroll instead of overflowing on small viewports.

### Job Actions

| Action | Description |
|--------|-------------|
| **Unmonitor** | Remove the job from the monitored list. |
| **View Job** | Navigate to the job detail page. *(placeholder)* |
| **View Job Details** | Open the tabbed job detail page at `/jobs/<jobName>?tab=overview`. The page exposes five tabs (Overview, Layers, Frames, Comments, Dependencies) with the active tab synced into the URL so it's bookmarkable and back-button friendly. |
| **Copy Job Name** | Copy the full job name to the clipboard. |
| **Email Artist...** | Open a themed dialog mirroring CueGUI's Email dialog. Fields (From, To, CC, BCC, Subject, Body) are pre-filled from the job and editable; see [Email Artist dialog](#email-artist-dialog). |
| **Request Cores...** | Open a themed dialog mirroring CueGUI's `RequestCoresDialog`. From / To / CC / BCC / Subject inputs are pre-filled; the body is auto-populated with the job's still-active layers (Layer Name / Minimum Memory / Min Cores) and two editable Date/Time + Notes sections. **Send** hands the result to the user's default mail client via a `mailto:` URL. See [Request Cores dialog](#request-cores-dialog). |
| **Subscribe to Job** | Open a themed dialog mirroring CueGUI's `SubscribeToJobDialog`. The address you save is registered with Cuebot via the `AddSubscriber` RPC, so Cuebot emails the subscriber when the job finishes. This is the *server-side, email* subscription - different from the [Notify bell](#job-finished-notifications) (browser-side, in-app + optional desktop popup). See [Subscribe to Job dialog](#subscribe-to-job-dialog). |
| **Comments** | Open the per-job Comments page (`/jobs/<jobName>/comments`). |
| **Use Local Cores** | Reserve local cores for this job. *(placeholder)* |
| **View Dependencies...** | Open a themed dialog mirroring CueGUI's `DependDialog`. On open, the dialog calls the `GetDepends` RPC via `/api/job/action/getdepends` and renders the job's `depend.DependSeq` as a table with columns Type / Target / Active / OnJob / OnLayer / OnFrame. **Refresh** re-fetches the list. See [View Dependencies dialog](#view-dependencies-dialog). |
| **Dependency Wizard...** | Open a themed three-step dialog mirroring CueGUI's `DependWizard`. Step 1 picks the dependency type (the three Job-On-X types are supported; the other CueGUI types are listed as `CueGUI only` to set expectations). Step 2 prompts for the target object's identifiers (job name, plus layer / frame names as needed). Step 3 confirms and dispatches to `CreateDependencyOnJob` / `CreateDependencyOnLayer` / `CreateDependencyOnFrame` via the matching `/api/job/action/createdependon*` proxy route. See [Dependency Wizard dialog](#dependency-wizard-dialog). |
| **Drop External Dependencies** | Drop external job-on-job dependencies via the `DropDepends` RPC with `target = EXTERNAL`. |
| **Drop Internal Dependencies** | Drop internal layer-on-layer dependencies via the `DropDepends` RPC with `target = INTERNAL`. |
| **Set User Color** / **Clear User Color** | Drive the User Color column for this job. *(placeholder)* |
| **Set Priority...** | Open a themed dialog with a 1-100 slider + number input to adjust the job's dispatch priority. Higher numbers dispatch first; default is 100. After Apply the Jobs table updates the Priority column optimistically (no wait for the 5s poll). Available everywhere the job context menu appears - both **Cuetopia &rarr; Monitor Jobs** (`/`) and **CueCommander &rarr; Monitor Cue** (`/monitor-cue`); the entry is *not* gated by `usePathname()`. See [Set Priority dialog](#set-priority-dialog). |
| **Set Max Retries** | Edit the per-frame retry budget. |
| **Reorder Frames** / **Stagger Frames** | Open the reorder / stagger dialogs. *(placeholder)* |
| **Pause** / **Unpause** | Single toggle entry: shows **Pause** when the job is running and **Unpause** when the job is already paused. The label, icon (`TbPlayerPause` / `TbPlayerPlay`) and dispatched action all flip on the row's `isPaused` flag. The entry is shown disabled (grayed) when the job's `state === "FINISHED"` (a terminal state can't be paused), and when the global *Disable Job Interaction* safety flag is on. Active in all other states (In Progress, Failing, Dependency). |
| **Auto-Eat On** / **Auto-Eat Off** | Toggle Auto-Eat. |
| **Retry Dead Frames** | Retry every dead frame. |
| **Eat Dead Frames** | Mark every dead frame as eaten. |
| **Unbook** | Unbook running frames. *(placeholder)* |
| **Kill** | Terminate the job. |
| **Show Progress Bar** | Surface the stacked progress bar for the job. *(placeholder)* |

### Layer Actions

| Action | Description |
|--------|-------------|
| **View Layer** | Navigate to the layer detail page. |
| **Copy Layer Name** | Copy the full layer name to the clipboard. |
| **Drop / View / Wizard dependency items** | Manage layer-level dependencies. *(placeholders)* |
| **Reorder Frames** / **Stagger Frames** | Open the reorder / stagger dialogs. *(placeholder)* |
| **Properties** | Open the layer properties dialog. *(placeholder)* |
| **Kill** | Kill every frame in the layer. |
| **Eat** | Eat every frame in the layer. |
| **Retry** | Retry every frame in the layer. |
| **Retry Dead Frames** | Retry only the dead frames. |

### Frame Actions

| Action | Description |
|--------|-------------|
| **Tail Log** / **View Log** | Open the in-browser log viewer at `/frames/<frameName>`. Same target as the row's double-click handler. Surfaces a friendly toast when the frame has not been dispatched yet (no log file on disk). |
| **View Log on \<editor\>** | Launches the log file in a desktop editor. Only rendered when `NEXT_PUBLIC_LOG_EDITOR_URL` is set. The menu label is derived from the configured value (`vscode://...` -> "View Log on VSCode", `subl://...` -> "View Log on Sublime Text", `txmt://...` -> "View Log on TextMate", `idea://...` -> "View Log on IntelliJ", unrecognized -> "View Log in external editor"). See [External editor integration](#external-editor-integration) below. |
| **Copy Log Path** | Copy the absolute log path to the clipboard. |
| **Copy Frame Name** | Copy the full frame name. |
| **View Host** | Navigate to the host detail page. *(placeholder)* |
| **Drop / View dependency items** | Manage frame-level dependencies. *(placeholders)* |
| **Filter Selected Layers** | Narrow the frames table to the frame's layer (same as clicking the layer row). |
| **Reorder** | Open the reorder dialog. *(placeholder)* |
| **Preview All** | Sequence-preview integration. *(placeholder)* |
| **Retry** | Retry the frame. |
| **Eat** | Mark the frame as eaten. |
| **Kill** | Kill the running frame. |
| **Eat and Mark done** | Eat the frame and treat it as succeeded. *(placeholder)* |
| **View Processes** | Show RQD processes attached to the frame. *(placeholder)* |

### External editor integration

The Frame context menu's **View Log on \<editor\>** item launches the log file in a desktop editor.

| Aspect | Description |
|--------|-------------|
| **Env var** | `NEXT_PUBLIC_LOG_EDITOR_URL` (build-time). Default in the sandbox deployment is `vscode://file{path}`; the Dockerfile-level default is empty (item hidden). |
| **Template** | The literal `{path}` is replaced with the absolute log path when the item is clicked. Common values: `vscode://file{path}`, `vscode-insiders://file{path}`, `subl://open?url=file://{path}`, `txmt://open?url=file://{path}`, `idea://open?file={path}`. |
| **Why not `$EDITOR`?** | Web browsers can't read the user's shell environment or launch arbitrary local programs the way CueGUI does. The URL-scheme approach is the web equivalent: the same trick GitHub's "Open in VSCode" button uses. |
| **Missing-handler detection** | If the chosen editor isn't installed on the user's machine, CueWeb shows a warning toast after a short delay pointing the user at the alternatives. |
| **Frame-state guard** | When the frame hasn't been dispatched yet by RQD (no log file on disk), the handler shows a friendly warning toast instead of handing a non-existent path to the editor. |

---

### Set Priority dialog

The job context menu's **Set Priority...** entry opens a themed dialog with a 1-100 range slider and a matching number input - either control drives the value, and both stay in sync. The number input is pre-filled with the job's current priority. Higher numbers dispatch first; cuebot's default is 100. Available everywhere the job context menu appears - both **Cuetopia &rarr; Monitor Jobs** (`/`) and **CueCommander &rarr; Monitor Cue** (`/monitor-cue`). The dialog and the dispatched action are identical on either page; only the **View Job** entry above it remains gated to `/monitor-cue`.

Mounted once via `<SetPriorityDialog />` in `cueweb/app/jobs/data-table.tsx`; opens in response to a `cueweb:open-set-priority` CustomEvent that `setPriorityGivenRow(row)` in `cueweb/app/utils/action_utils.ts` dispatches with `{ job }`. Lives in `cueweb/components/ui/set-priority-dialog.tsx`.

![Set Priority entry in the job context menu on Cuetopia Monitor Jobs](/assets/images/cueweb/cueweb_cuetopia_monitor_jobs_set_priority_menu.png)

![Set Priority dialog with 1-100 slider + matching number input](/assets/images/cueweb/cueweb_cuetopia_monitor_jobs_set_priority_window.png)

After **Apply**:

- `setJobPriority(job, value)` from `action_utils.ts` posts `{ job, val }` to `/api/job/action/setpriority`, which forwards to `/job.JobInterface/SetPriority` on the REST gateway.
- A success toast confirms the new value.
- The dialog dispatches a `cueweb:priority-changed` CustomEvent that the Jobs table consumes to update the row's **Priority** column optimistically, so the change is visible without waiting for the regular 5-second poll.

![Set Priority success confirmation toast](/assets/images/cueweb/cueweb_cuetopia_monitor_jobs_set_priority_confirmation.png)

---

### Email Artist dialog

The job context menu's **Email Artist...** entry mirrors CueGUI's `EmailDialog`. Mounted once via `<EmailArtistDialog />` in `cueweb/app/jobs/data-table.tsx`; opens in response to a `cueweb:open-email-artist` CustomEvent that `emailArtistGivenRow(row)` in `cueweb/app/utils/action_utils.ts` dispatches with `{ job }`. Lives in `cueweb/components/ui/email-artist-dialog.tsx`.

![Email Artist entry in the job context menu](/assets/images/cueweb/cueweb_cuetopia_monitor_jobs_email_artist_menu.png)

![Email Artist dialog pre-filled from the selected job](/assets/images/cueweb/cueweb_cuetopia_monitor_jobs_email_artist_window.png)

Defaults derived from the row:

| Field | Default value |
|-------|---------------|
| **From** | `<show>-<NEXT_PUBLIC_EMAIL_SUPPORT_SUFFIX>@<NEXT_PUBLIC_EMAIL_DOMAIN>` (informational - see below) |
| **To** | `<user>@<NEXT_PUBLIC_EMAIL_DOMAIN>` (the job's owner) |
| **CC** | same as From |
| **BCC** | empty |
| **Subject** | `cuemail: please check <jobName>` |
| **Body** | `Your Support Team requests that you check <jobName>` followed by `Hi <user>,` |

Send mechanism: the **Send** button builds a `mailto:` URL with the dialog's `to`, `cc`, `bcc`, `subject`, and `body` and assigns it to `window.location.href`. The OS hands the URL to the user's default mail client (Mail.app, Outlook, Thunderbird, etc.).

Browsers don't let `mailto:` override the user's account's `From:` header, so the **From** field in the dialog is informational only - it surfaces the support alias the team typically uses. CueGUI's `EmailDialog` can spoof From because it sends through CueGUI's own SMTP relay; CueWeb's mailto-based equivalent uses whatever account the user's mail client is configured with.

Configurable at build time via two env vars (see [Environment Variables](#environment-variables)):

- `NEXT_PUBLIC_EMAIL_DOMAIN` (default `your.domain.com`).
- `NEXT_PUBLIC_EMAIL_SUPPORT_SUFFIX` (default `pst`, matching CueGUI's "production support team" alias convention).

---

### Request Cores dialog

The job context menu's **Request Cores...** entry mirrors CueGUI's `RequestCoresDialog`. Mounted once via `<RequestCoresDialog />` in `cueweb/app/jobs/data-table.tsx`; opens in response to a `cueweb:open-request-cores` CustomEvent that `requestCoresGivenRow(row)` in `cueweb/app/utils/action_utils.ts` dispatches with `{ job }`. Lives in `cueweb/components/ui/request-cores-dialog.tsx`.

![Request Cores entry in the job context menu](/assets/images/cueweb/cueweb_cuetopia_monitor_jobs_request_cores_menu.png)

![Request Cores dialog pre-filled from the selected job](/assets/images/cueweb/cueweb_cuetopia_monitor_jobs_request_cores_window.png)

Defaults derived from the row:

| Field | Default value |
|-------|---------------|
| **From** | The signed-in user's email (`session.user.email`, falling back to `<sessionName>@<NEXT_PUBLIC_EMAIL_DOMAIN>` and then to empty). |
| **To** | Empty - the user fills in the recipient (team lead, support queue, etc.). |
| **CC** | `<show>-<NEXT_PUBLIC_EMAIL_REQUEST_CORES_SUFFIX>@<NEXT_PUBLIC_EMAIL_DOMAIN>`. |
| **BCC** | Empty. |
| **Subject** | `Requesting Cores for <jobName>`. |
| **Body (auto-populated)** | `Requesting more cores for:` header, `Job Name:` + `Group (Folder):`, then a fixed-width table of layers with `waitingFrames + runningFrames > 0` (`Layer Name / Minimum Memory / Min Cores`). |
| **Date/Time by which completion is needed** | Editable textarea, appended to the body on Send. |
| **Additional notes (flag priority frames etc.)** | Editable textarea, appended to the body on Send. |

Layer breakdown is fetched asynchronously on dialog open via `getLayersForJob(job)`; the body shows `Loading layers...` until the response lands, then re-renders with the filtered table.

Send mechanism: the **Send** button stitches the auto-populated prelude together with the Date/Time and Notes sections, builds a `mailto:` URL with `to`, `cc`, `bcc`, `subject`, and `body`, and assigns it to `window.location.href`. Same `From:`-is-informational caveat as the [Email Artist dialog](#email-artist-dialog). The button is disabled while **To** is empty.

Configurable at build time:

- `NEXT_PUBLIC_EMAIL_DOMAIN` (default `your.domain.com`, shared with Email Artist).
- `NEXT_PUBLIC_EMAIL_REQUEST_CORES_SUFFIX` (default `support`, matching CueGUI's `<show>-support@<domain>` convention - distinct from Email Artist's `pst`).

### Subscribe to Job dialog

The job context menu's **Subscribe to Job** entry mirrors CueGUI's `SubscribeToJobDialog`. Unlike the [Notify bell](#job-finished-notifications) - which is a *browser-side* subscription that fires an in-app toast (and optional desktop popup) - this entry registers a *server-side, email* subscriber on Cuebot. When the job reaches `FINISHED`, Cuebot sends an email to the saved address.

Mounted once via `<SubscribeToJobDialog />` in `cueweb/app/jobs/data-table.tsx`; opens in response to a `cueweb:open-subscribe-to-job` CustomEvent that `subscribeToJobGivenRow(row)` in `cueweb/app/utils/action_utils.ts` dispatches with `{ job }`. Lives in `cueweb/components/ui/subscribe-to-job-dialog.tsx`.

![Subscribe to Job entry in the job context menu](/assets/images/cueweb/cueweb_cuetopia_monitor_jobs_subscribe_to_job_menu.png)

![Subscribe to Job dialog pre-filled from the selected job](/assets/images/cueweb/cueweb_cuetopia_monitor_jobs_subscribe_to_job_window.png)

Defaults derived from the row:

| Field | Default value |
|-------|---------------|
| **Job name** | Read-only, taken from the row. |
| **From** | Read-only label - `NEXT_PUBLIC_SUBSCRIBE_FROM_EMAIL` if set, otherwise `opencue-noreply@<NEXT_PUBLIC_EMAIL_DOMAIN>`. Informational only - the actual sender is whatever Cuebot is configured with. |
| **To** | Editable; the signed-in user's `session.user.email`, falling back to `<sessionName-or-jobUser>@<NEXT_PUBLIC_EMAIL_DOMAIN>`. |

Save mechanism: the **Save** button trims and validates the **To** address with a permissive `^\S+@\S+\.\S+$` check (Cuebot does its own validation server-side), then calls `addJobSubscriber(job, subscriber)` from `action_utils.ts`. That posts `{ job, subscriber }` to `/api/job/action/addsubscriber`, which forwards to `/job.JobInterface/AddSubscriber` via the REST gateway. A success toast confirms the subscription:

![Subscribe to Job success confirmation](/assets/images/cueweb/cueweb_cuetopia_monitor_jobs_subscribe_to_job_confirmation.png)

The **Save** button is disabled while the **To** field is empty or while a save is in flight. **Cancel** closes the dialog without contacting Cuebot.

Configurable at build time:

- `NEXT_PUBLIC_EMAIL_DOMAIN` (default `your.domain.com`, shared with the other email dialogs).
- `NEXT_PUBLIC_SUBSCRIBE_FROM_EMAIL` (default `opencue-noreply@<EMAIL_DOMAIN>`). Use this to surface a deployment-specific informational From label without touching the code.

---

### Drop External / Internal Dependencies

Two one-click context-menu entries clear the matching depend bucket without opening a dialog. The action posts `{ job, target }` to `/api/job/action/dropdepends`, which validates `target` against `{ INTERNAL, EXTERNAL, ANY_TARGET }` server-side and forwards to `/job.JobInterface/DropDepends`. On success the helper dispatches `cueweb:refresh-now` (an immediate poll of the Jobs table) and `cueweb:depends-changed` (clears the Group-By Dependent tree cache and bumps its fetch token), so the Jobs row state, the chevrons in the dependency tree, and any open View Dependencies dialog all reconverge without waiting for the 5s autoload tick.

| Entry | Action |
|-------|--------|
| **Drop External Dependencies** | `DropDepends` with `target = EXTERNAL` - removes every cross-job depend. |
| **Drop Internal Dependencies** | `DropDepends` with `target = INTERNAL` - removes every within-job (layer-on-layer / frame-on-X) depend. |

![Drop External Dependencies entry in the job context menu](/assets/images/cueweb/cueweb_cuetopia_monitor_jobs_drop_external_dependencies_menu.png)

![Drop External Dependencies success toast](/assets/images/cueweb/cueweb_cuetopia_monitor_jobs_drop_external_dependencies_confirmation.png)

![Drop Internal Dependencies entry in the job context menu](/assets/images/cueweb/cueweb_cuetopia_monitor_jobs_drop_internal_dependencies_menu.png)

![Drop Internal Dependencies success toast](/assets/images/cueweb/cueweb_cuetopia_monitor_jobs_drop_internal_dependencies_confirmation.png)

---

### View Dependencies dialog

The job context menu's **View Dependencies...** entry mirrors CueGUI's `DependDialog`: a read-only table of the job's `depend.DependSeq` so the user can audit which depends are still blocking the job.

![View Dependencies entry in the job context menu](/assets/images/cueweb/cueweb_cuetopia_monitor_jobs_view_dependencies_menu.png)

Mounted once via `<ViewDependenciesDialog />` in `cueweb/app/jobs/data-table.tsx`; opens in response to a `cueweb:open-view-dependencies` CustomEvent that `viewDependenciesGivenRow(row)` in `cueweb/app/utils/action_utils.ts` dispatches with `{ job }`. Lives in `cueweb/components/ui/view-dependencies-dialog.tsx`.

On open, the dialog calls `fetchJobDepends(job)` from `action_utils.ts`, which posts `{ job }` to `/api/job/action/getdepends`. The proxy route forwards to `/job.JobInterface/GetDepends` via the REST gateway, and the dialog renders the returned `DependSeq` as a table.

![View Dependencies dialog showing the depend.DependSeq table](/assets/images/cueweb/cueweb_cuetopia_monitor_jobs_view_dependencies_window.png)

Columns mirror CueGUI's `DependDialog` table:

| Column | Source field |
|--------|--------------|
| **Type** | `depend.type` (e.g. `JOB_ON_JOB`, `LAYER_ON_FRAME`). |
| **Target** | `depend.target` (`INTERNAL` or `EXTERNAL`). |
| **Active** | `depend.active` boolean - `true` while the depend still blocks the dependent. |
| **OnJob** | `depend.depend_on_job` - the job this depend waits on. |
| **OnLayer** | `depend.depend_on_layer` - the layer (empty for job-level depends). |
| **OnFrame** | `depend.depend_on_frame` - the frame (empty for job / layer-level depends). |

The **Refresh** button re-issues the `GetDepends` RPC so the user can verify that a freshly created depend appears in the table without re-opening the dialog. **Close** dismisses the dialog.

---

### Dependency Wizard dialog

The job context menu's **Dependency Wizard...** entry mirrors CueGUI's `DependWizard`: a multi-step dialog that walks the user through creating a new depend on the current job.

![Dependency Wizard entry in the job context menu](/assets/images/cueweb/cueweb_cuetopia_monitor_jobs_dependency_wizard_menu.png)

Mounted once via `<DependencyWizardDialog />` in `cueweb/app/jobs/data-table.tsx`; opens in response to a `cueweb:open-dependency-wizard` CustomEvent that `dependencyWizardGivenRow(row)` in `cueweb/app/utils/action_utils.ts` dispatches with `{ job }`. Lives in `cueweb/components/ui/dependency-wizard-dialog.tsx`.

The wizard implements every CueGUI `depend.DependType`, including the UI-only Hard Depend variant. Every picker is multi-select (matching CueGUI's `QListWidget(ExtendedSelection)` behavior) and **Done** fires the full cross-product of source x target picks. The table below summarizes the step list and underlying RPC per type:

| Type | Steps | Underlying RPC(s) |
|------|-------|-------------------|
| `JOB_ON_JOB` | Type &rarr; Job &rarr; Confirm | `/job.JobInterface/CreateDependencyOnJob` |
| `JOB_ON_LAYER` | Type &rarr; Job &rarr; Layer &rarr; Confirm | `/job.JobInterface/CreateDependencyOnLayer` |
| `JOB_ON_FRAME` | Type &rarr; Job &rarr; Layer &rarr; Frame &rarr; Confirm | `/job.JobInterface/CreateDependencyOnFrame` |
| `JFBF` (Hard Depend - "Frame By Frame for all layers") | Type &rarr; Job &rarr; Confirm | `/layer.LayerInterface/CreateFrameByFrameDependency` per matched-type layer pair, across every picked target job |
| `LAYER_ON_JOB` | Type &rarr; Source Layer &rarr; Job &rarr; Confirm | `/layer.LayerInterface/CreateDependencyOnJob` |
| `LAYER_ON_LAYER` | Type &rarr; Source Layer &rarr; Job &rarr; Layer &rarr; Confirm | `/layer.LayerInterface/CreateDependencyOnLayer` |
| `LAYER_ON_FRAME` | Type &rarr; Source Layer &rarr; Job &rarr; Layer &rarr; Frame &rarr; Confirm | `/layer.LayerInterface/CreateDependencyOnFrame` |
| `FRAME_BY_FRAME` | Type &rarr; Source Layer &rarr; Job &rarr; Layer &rarr; Confirm | `/layer.LayerInterface/CreateFrameByFrameDependency` |
| `FRAME_ON_JOB` | Type &rarr; Source Layer &rarr; Source Frame &rarr; Job &rarr; Confirm | `/frame.FrameInterface/CreateDependencyOnJob` |
| `FRAME_ON_LAYER` | Type &rarr; Source Layer &rarr; Source Frame &rarr; Job &rarr; Layer &rarr; Confirm | `/frame.FrameInterface/CreateDependencyOnLayer` |
| `FRAME_ON_FRAME` | Type &rarr; Source Layer &rarr; Source Frame &rarr; Job &rarr; Layer &rarr; Frame &rarr; Confirm | `/frame.FrameInterface/CreateDependencyOnFrame` |
| `LAYER_ON_SIM_FRAME` | Type &rarr; Source Layer &rarr; Job &rarr; Sim Layer &rarr; Frame &rarr; Confirm | `/frame.FrameInterface/CreateDependencyOnFrame` per source frame x picked sim frame |

Fan-out semantics: **Done** issues `len(sources) * len(targets)` parallel RPCs through one `performAction` call so the user gets a single summary toast. Picking M source layers and N target layers under `LAYER_ON_LAYER`, for example, fires M*N `CreateDependencyOnLayer` RPCs.

1. **Select Dependency Type.** A radio-group lists every `depend.DependType` CueGUI offers, including the UI-only Hard Depend variant. All twelve are now wired.
2. **Source pickers (Layer / Frame in THIS job).** Layer-On-X, Frame-By-Frame, Frame-On-X, and Layer-On-Sim-Frame all need source object(s) in this job before targeting another job. The wizard fetches `getLayersForJob(thisJob)` to populate the source-layer picker; the source-frame picker then fetches `getFramesForJob(thisJob)` once and filters client-side to *every* picked source layer (so the user can multi-select layers and still pick frames across them).
3. **Target Job picker.** A regex search box drives a scrollable list of matching jobs (debounced 250ms, capped at 200 rows). The query is forwarded to `getJobsForRegex(regex, include_finished=true)`, which posts to `/api/job/getjobs`. An empty query falls back to `.*`. Multi-select - pick as many target jobs as you want.
4. **Target Layer picker.** Layers are fetched in parallel from every picked target job via `getLayersForJob` and concatenated. Each row carries its `parentJobName`; when multiple target jobs are picked the parent is rendered as a `[parentJob]` annotation so duplicates can be told apart. For `LAYER_ON_SIM_FRAME` the list is filtered client-side to layers whose `services` array contains a token matching `/sim/i`.
5. **Target Frame picker.** Frames are fetched in parallel from every parent job of the picked target layers, then filtered to the picked layer names. Each row shows `(state) [layerName] <parentJobName>` annotations where useful for disambiguation.
6. **Confirmation.** A read-only summary of the dependency type, this job, picked source object(s), and picked target object(s). **Done** dispatches to the matching wrapper in `action_utils.ts`, which expands the full source x target cross-product into one `performAction` call (parallel RPCs, single summary toast).

The Hard Depend (`JFBF`) case is handled client-side: on **Done** the wizard fetches the layer list for this job and for every picked target job in parallel, pairs each target job's layers with this job's layers by `layer.type`, and bulk-fires `/layer.LayerInterface/CreateFrameByFrameDependency` for every matched pair across every target job. The success toast notes how many target jobs and layer pairs were created (`<this-job> -> <N> jobs (<M> layer pairs)`). If no types match, the wizard surfaces a warning toast instead of opening empty RPCs against Cuebot.

Each step has **Go Back** / **Continue** (or **Done**) buttons; **Cancel** on step 1 dismisses the wizard. The dialog is locked while a Done request is in flight, and **Go Back** rewinds one step at a time so a wrong choice can be corrected without restarting the wizard.

#### Wizard walk-throughs

The screenshots below show the screen flow for each dependency type. Every picker is multi-select; **Done** fires the full source x target cross-product (see the table above for which RPC each type calls).

**Job On Job (3 steps)** - the shortest path. Pick the target job(s) the current job should wait on.

![Job On Job step 1 - select the dependency type](/assets/images/cueweb/cueweb_cuetopia_monitor_jobs_dependency_wizard_menu_select_dependency_type_job_on_job_step1_select_type.png)
![Job On Job step 2 - pick the target job(s)](/assets/images/cueweb/cueweb_cuetopia_monitor_jobs_dependency_wizard_menu_select_dependency_type_job_on_job_step2_select_jobs_to_depend.png)
![Job On Job step 3 - confirmation](/assets/images/cueweb/cueweb_cuetopia_monitor_jobs_dependency_wizard_menu_select_dependency_type_job_on_job_step3_confirmation.png)

**Job On Layer (4 steps)** - one extra target-layer picker.

![Job On Layer step 1 - select the dependency type](/assets/images/cueweb/cueweb_cuetopia_monitor_jobs_dependency_wizard_menu_select_dependency_type_job_on_layer_step1_select_type.png)
![Job On Layer step 2 - pick the target job(s)](/assets/images/cueweb/cueweb_cuetopia_monitor_jobs_dependency_wizard_menu_select_dependency_type_job_on_layer_step2_select_jobs_to_depend_on.png)
![Job On Layer step 3 - pick the target layer(s)](/assets/images/cueweb/cueweb_cuetopia_monitor_jobs_dependency_wizard_menu_select_dependency_type_job_on_layer_step3_select_target_layers_to_depend_on.png)
![Job On Layer step 4 - confirmation](/assets/images/cueweb/cueweb_cuetopia_monitor_jobs_dependency_wizard_menu_select_dependency_type_job_on_layer_step4_confirmation.png)

**Job On Frame (5 steps)** - drill all the way down to specific target frames.

![Job On Frame step 1 - select the dependency type](/assets/images/cueweb/cueweb_cuetopia_monitor_jobs_dependency_wizard_menu_select_dependency_type_job_on_frame_step1_select_type.png)
![Job On Frame step 2 - pick the target job(s)](/assets/images/cueweb/cueweb_cuetopia_monitor_jobs_dependency_wizard_menu_select_dependency_type_job_on_frame_step2_select_jobs_to_depend_on.png)
![Job On Frame step 3 - pick the target layer(s)](/assets/images/cueweb/cueweb_cuetopia_monitor_jobs_dependency_wizard_menu_select_dependency_type_job_on_frame_step3_select_target_layers_to_depend_on.png)
![Job On Frame step 4 - pick the target frame(s)](/assets/images/cueweb/cueweb_cuetopia_monitor_jobs_dependency_wizard_menu_select_dependency_type_job_on_frame_step4_select_target_frames_to_depend_on.png)
![Job On Frame step 5 - confirmation](/assets/images/cueweb/cueweb_cuetopia_monitor_jobs_dependency_wizard_menu_select_dependency_type_job_on_frame_step5_confirmation.png)

**Frame By Frame for all layers (Hard Depend, 3 steps)** - the wizard pairs source/target layers by `layer.type` and bulk-fires one Frame-By-Frame depend per matched pair on Done.

![Hard Depend step 1 - select the dependency type](/assets/images/cueweb/cueweb_cuetopia_monitor_jobs_dependency_wizard_menu_select_dependency_type_frame_by_frame_for_all_layers_step1_select_type.png)
![Hard Depend step 2 - pick the target job(s)](/assets/images/cueweb/cueweb_cuetopia_monitor_jobs_dependency_wizard_menu_select_dependency_type_frame_by_frame_for_all_layers_step2_select_jobs_to_depend_on.png)
![Hard Depend step 3 - confirmation](/assets/images/cueweb/cueweb_cuetopia_monitor_jobs_dependency_wizard_menu_select_dependency_type_frame_by_frame_for_all_layers_step3_confirmation.png)

**Layer On Job (4 steps)** - first source-side type. Pick layer(s) in THIS job, then the target job(s).

![Layer On Job step 1 - select the dependency type](/assets/images/cueweb/cueweb_cuetopia_monitor_jobs_dependency_wizard_menu_select_dependency_type_layer_on_job_step1_select_job.png)
![Layer On Job step 2 - pick the source layer(s) in this job](/assets/images/cueweb/cueweb_cuetopia_monitor_jobs_dependency_wizard_menu_select_dependency_type_layer_on_job_step2_select_source_layers_in_this_job.png)
![Layer On Job step 3 - pick the target job(s)](/assets/images/cueweb/cueweb_cuetopia_monitor_jobs_dependency_wizard_menu_select_dependency_type_layer_on_job_step3_select_jobs_to_depend_on.png)
![Layer On Job step 4 - confirmation](/assets/images/cueweb/cueweb_cuetopia_monitor_jobs_dependency_wizard_menu_select_dependency_type_layer_on_job_step4_confirmation.png)

**Layer On Layer (5 steps).**

![Layer On Layer step 1 - select the dependency type](/assets/images/cueweb/cueweb_cuetopia_monitor_jobs_dependency_wizard_menu_select_dependency_type_layer_on_layer_step1_select_type.png)
![Layer On Layer step 2 - pick the source layer(s) in this job](/assets/images/cueweb/cueweb_cuetopia_monitor_jobs_dependency_wizard_menu_select_dependency_type_layer_on_layer_step2_select_source_layers_in_this_job.png)
![Layer On Layer step 3 - pick the target job(s)](/assets/images/cueweb/cueweb_cuetopia_monitor_jobs_dependency_wizard_menu_select_dependency_type_layer_on_layer_step3_select_jobs_to_depend_on.png)
![Layer On Layer step 4 - pick the target layer(s)](/assets/images/cueweb/cueweb_cuetopia_monitor_jobs_dependency_wizard_menu_select_dependency_type_layer_on_layer_step4_select_target_layers_to_depend_on.png)
![Layer On Layer step 5 - confirmation](/assets/images/cueweb/cueweb_cuetopia_monitor_jobs_dependency_wizard_menu_select_dependency_type_layer_on_layer_step5_confirmation.png)

**Layer On Frame (6 steps).**

![Layer On Frame step 1 - select the dependency type](/assets/images/cueweb/cueweb_cuetopia_monitor_jobs_dependency_wizard_menu_select_dependency_type_layer_on_frame_step1_select_type.png)
![Layer On Frame step 2 - pick the source layer(s) in this job](/assets/images/cueweb/cueweb_cuetopia_monitor_jobs_dependency_wizard_menu_select_dependency_type_layer_on_frame_step2_select_source_layers_in_this_job.png)
![Layer On Frame step 3 - pick the target job(s)](/assets/images/cueweb/cueweb_cuetopia_monitor_jobs_dependency_wizard_menu_select_dependency_type_layer_on_frame_step3_select_jobs_to_depend_on.png)
![Layer On Frame step 4 - pick the target layer(s)](/assets/images/cueweb/cueweb_cuetopia_monitor_jobs_dependency_wizard_menu_select_dependency_type_layer_on_frame_step4_select_target_layers_to_depend_on.png)
![Layer On Frame step 5 - pick the target frame(s)](/assets/images/cueweb/cueweb_cuetopia_monitor_jobs_dependency_wizard_menu_select_dependency_type_layer_on_frame_step5_select_target_frames_to_depend_on.png)
![Layer On Frame step 6 - confirmation](/assets/images/cueweb/cueweb_cuetopia_monitor_jobs_dependency_wizard_menu_select_dependency_type_layer_on_frame_step6_confirmation.png)

**Frame By Frame (5 steps).** Single source layer x single target layer, frame-by-frame.

![Frame By Frame step 1 - select the dependency type](/assets/images/cueweb/cueweb_cuetopia_monitor_jobs_dependency_wizard_menu_select_dependency_type_frame_by_frame_step1_select_type.png)
![Frame By Frame step 2 - pick the source layer(s) in this job](/assets/images/cueweb/cueweb_cuetopia_monitor_jobs_dependency_wizard_menu_select_dependency_type_frame_by_frame_step2_select_source_layers_in_this_job.png)
![Frame By Frame step 3 - pick the target job(s)](/assets/images/cueweb/cueweb_cuetopia_monitor_jobs_dependency_wizard_menu_select_dependency_type_frame_by_frame_step3_select_jobs_to_depend_on.png)
![Frame By Frame step 4 - pick the target layer(s)](/assets/images/cueweb/cueweb_cuetopia_monitor_jobs_dependency_wizard_menu_select_dependency_type_frame_by_frame_step4_select_target_layers_to_depend_on.png)
![Frame By Frame step 5 - confirmation](/assets/images/cueweb/cueweb_cuetopia_monitor_jobs_dependency_wizard_menu_select_dependency_type_frame_by_frame_step5_confirmation.png)

**Frame On Job (5 steps).** Drill into source frames, then pick target job(s).

![Frame On Job step 1 - select the dependency type](/assets/images/cueweb/cueweb_cuetopia_monitor_jobs_dependency_wizard_menu_select_dependency_type_frame_on_job_step1_select_type.png)
![Frame On Job step 2 - pick the source layer(s)](/assets/images/cueweb/cueweb_cuetopia_monitor_jobs_dependency_wizard_menu_select_dependency_type_frame_on_job_step2_select_source_layers_in_this_job.png)
![Frame On Job step 3 - pick the source frame(s)](/assets/images/cueweb/cueweb_cuetopia_monitor_jobs_dependency_wizard_menu_select_dependency_type_frame_on_job_step3_select_source_frames_in_this_job.png)
![Frame On Job step 4 - pick the target job(s)](/assets/images/cueweb/cueweb_cuetopia_monitor_jobs_dependency_wizard_menu_select_dependency_type_frame_on_job_step4_select_jobs_to_depend_on.png)
![Frame On Job step 5 - confirmation](/assets/images/cueweb/cueweb_cuetopia_monitor_jobs_dependency_wizard_menu_select_dependency_type_frame_on_job_step5_confirmation.png)

**Frame On Layer (6 steps).**

![Frame On Layer step 1 - select the dependency type](/assets/images/cueweb/cueweb_cuetopia_monitor_jobs_dependency_wizard_menu_select_dependency_type_frame_on_layer_step1_select_type.png)
![Frame On Layer step 2 - pick the source layer(s)](/assets/images/cueweb/cueweb_cuetopia_monitor_jobs_dependency_wizard_menu_select_dependency_type_frame_on_layer_step2_select_source_layers_in_this_job.png)
![Frame On Layer step 3 - pick the source frame(s)](/assets/images/cueweb/cueweb_cuetopia_monitor_jobs_dependency_wizard_menu_select_dependency_type_frame_on_layer_step3_select_source_frames_in_this_job.png)
![Frame On Layer step 4 - pick the target job(s)](/assets/images/cueweb/cueweb_cuetopia_monitor_jobs_dependency_wizard_menu_select_dependency_type_frame_on_layer_step4_select_jobs_to_depend_on.png)
![Frame On Layer step 5 - pick the target layer(s)](/assets/images/cueweb/cueweb_cuetopia_monitor_jobs_dependency_wizard_menu_select_dependency_type_frame_on_layer_step5_select_target_layers_to_depend_on.png)
![Frame On Layer step 6 - confirmation](/assets/images/cueweb/cueweb_cuetopia_monitor_jobs_dependency_wizard_menu_select_dependency_type_frame_on_layer_step6_confirmation.png)

**Frame On Frame (7 steps)** - the longest path. Drill into a source frame and a target frame.

![Frame On Frame step 1 - select the dependency type](/assets/images/cueweb/cueweb_cuetopia_monitor_jobs_dependency_wizard_menu_select_dependency_type_frame_on_frame_step1_select_type.png)
![Frame On Frame step 2 - pick the source layer(s)](/assets/images/cueweb/cueweb_cuetopia_monitor_jobs_dependency_wizard_menu_select_dependency_type_frame_on_frame_step2_select_source_layers_in_this_job.png)
![Frame On Frame step 3 - pick the source frame(s)](/assets/images/cueweb/cueweb_cuetopia_monitor_jobs_dependency_wizard_menu_select_dependency_type_frame_on_frame_step3_select_source_frames_in_this_job.png)
![Frame On Frame step 4 - pick the target job(s)](/assets/images/cueweb/cueweb_cuetopia_monitor_jobs_dependency_wizard_menu_select_dependency_type_frame_on_frame_step4_select_jobs_to_depend_on.png)
![Frame On Frame step 5 - pick the target layer(s)](/assets/images/cueweb/cueweb_cuetopia_monitor_jobs_dependency_wizard_menu_select_dependency_type_frame_on_frame_step5_select_target_layers_to_depend_on.png)
![Frame On Frame step 6 - pick the target frame(s)](/assets/images/cueweb/cueweb_cuetopia_monitor_jobs_dependency_wizard_menu_select_dependency_type_frame_on_frame_step6_select_target_frames_to_depend_on.png)
![Frame On Frame step 7 - confirmation](/assets/images/cueweb/cueweb_cuetopia_monitor_jobs_dependency_wizard_menu_select_dependency_type_frame_on_frame_step7_confirmation.png)

**Layer On Simulation Frame.** Similar to Layer On Frame, but the target layer picker is filtered to layers whose `services` array matches `/sim/i`.

![Layer On Simulation Frame step 1 - select the dependency type](/assets/images/cueweb/cueweb_cuetopia_monitor_jobs_dependency_wizard_menu_select_dependency_type_layer_on_simulation_frame_step1_select_type.png)
![Layer On Simulation Frame step 2 - pick the source layer(s)](/assets/images/cueweb/cueweb_cuetopia_monitor_jobs_dependency_wizard_menu_select_dependency_type_layer_on_simulation_frame_step2_select_source_layers_in_this_job.png)
![Layer On Simulation Frame step 3 - pick the target job(s)](/assets/images/cueweb/cueweb_cuetopia_monitor_jobs_dependency_wizard_menu_select_dependency_type_layer_on_simulation_frame_step3_select_jobs_to_depend_on.png)
![Layer On Simulation Frame step 4 - pick the target sim layer(s)](/assets/images/cueweb/cueweb_cuetopia_monitor_jobs_dependency_wizard_menu_select_dependency_type_layer_on_simulation_frame_step4_select_target_layers_to_depend_on.png)

---

## CueSubmit (Job Submission UI)

CueWeb ships a browser-based equivalent of the standalone CueSubmit CLI tool at the `/cuesubmit` route, reachable from the **CueSubmit** top-level dropdown in the header (and the matching entry in the sidebar / mobile nav drawer). It mirrors the CueSubmit dialog layout one-for-one with a few quality-of-life improvements made possible by running in the browser.

![CueSubmit menu options](/assets/images/cueweb/cueweb_cuesubmit_menu_options.png)

![CueSubmit Submit Job page](/assets/images/cueweb/cueweb_cuesubmit_submit_job.png)

### Sections

| Section | Fields |
|---------|--------|
| **Job Info** | Job Name, Show (dropdown populated from `/api/show/getshows`), Shot, Facility (dropdown from `NEXT_PUBLIC_CUEBOT_FACILITIES`), Username |
| **Layer Info** | Layer Name, Dependency Type (none / Layer / Frame), Frame Spec, Chunk Size, Memory, Job Type, Services, Limits, Override Cores |
| **Per-type options** | Shell: Command To Run. Maya: Maya File + Camera. Nuke: Nuke File + Write Nodes. Blender: Blender File + Output Path + Output Format. |
| **Final command** | Read-only preview that updates per-keystroke. Mirrors the same text cuebot will see. |
| **Submission Details** | Multi-layer table (Layer Name / Job Type / Frames / Depend Type) with `+ / − / ↓ / ↑` buttons. Clicking a row loads it into the Layer Info editor. |
| **Action row** | Cancel · Reset · Submit. |

### Validation rules

| Field | Rule |
|-------|------|
| Job Name, Layer Name, Shot | Letters, numbers, `.`, `-`, `_` only. No spaces (cuebot uses the name in the log path). |
| Frame Spec | Must match cuebot frame-spec syntax: `1-10`, `1-100x2`, `1-100y3`, `1-100:2`, comma-separated segments. Reverse ranges (e.g. `10-1`) are rejected. |
| Memory | Number with optional unit suffix (`256m`, `1g`, `3.2G`). Empty inherits the service's `int_mem_min`. |
| Chunk Size | Positive integer. |
| At least one layer | Submit is disabled with a validation error when zero layers are configured. |

### Username and the Edit override

When CueWeb is deployed with `NEXT_PUBLIC_AUTH_PROVIDER` non-empty, the Username field is pre-populated from the signed-in session and rendered read-only. A small **Edit** checkbox to the right of the field toggles it editable. Unticking the box snaps the value back to the signed-in user. In sandbox mode (no auth) the field is always editable and the Edit checkbox is hidden.

### Defaults tuned for the OpenCue sandbox

The form chooses defaults that produce a runnable submission against the seeded sandbox out of the box:

- **Memory**: `256m`. The seeded `default` service has a 3.2 GB minimum, which the sandbox RQD usually can't satisfy. The 256 MB default keeps trivial jobs dispatchable.
- **Facility**: `local` when the user picks `[Default]`. The seeded sandbox's RQD belongs to the `local.general` allocation; cuebot's internal fallback (`cloud`) does not match.
- **UID**: derived deterministically from the username (1000-65000). Cuebot rejects `uid=0` with `Cannot launch jobs as root`, so CueWeb never emits zero.

These three defaults match what the standalone CueSubmit CLI tool produces against the same sandbox.

### Autocomplete history

Job Name, Shot, and Layer Name are wired to native `<datalist>` dropdowns populated from `localStorage` (per-field, deduped case-insensitively, capped at 25 entries). The Python CueSubmit CLI keeps an on-disk cache for the same reason - so a user's previous values are one keystroke away. On every successful submit the relevant values are recorded automatically.

### Draft auto-save

The whole form auto-saves to `localStorage` on every change and restores on mount, so an accidental refresh doesn't wipe a multi-layer setup. The draft is cleared on Cancel, on Reset (after the confirm dialog), and on a successful submit.

### Reset

Between Cancel and Submit, a Reset button clears every field and brings the form back to the blank-canvas state. A themed confirmation dialog (Radix-based, light/dark aware) replaces the native browser `confirm()` so the prompt doesn't look like an OS pop-up. Autocomplete history is **not** cleared on Reset.

### Submit flow

| Step | Detail |
|------|--------|
| 1. Validate | The form payload is parsed against the zod schema before any network call. Inline error messages render under each field on blur. |
| 2. Build spec | The server-side route builds the OpenCue cjsl XML spec - direct port of pyoutline's `outline.backend.cue.serialize` (cores / threadable heuristic, depend element shape, service defaulting, XML escaping). |
| 3. Launch | `POST /api/job/submit` proxies to `job.JobInterface/LaunchSpecAndWait` on the REST gateway, which returns the resolved job(s). |
| 4. Persist history | Job Name, Shot, and all Layer Names are appended to the autocomplete histories; the draft is cleared. |
| 5. Redirect | The page navigates to the tabbed `/jobs/<name>` job-detail view so the user can watch the new job's frames go WAITING -> RUNNING -> SUCCEEDED. |

### "View in Monitor Jobs" deep link

The tabbed job-detail page has a **View in Monitor Jobs** button in its header (next to the title). Clicking it navigates to `/?search=<jobname>`. Cuetopia's Jobs table reads the `search` URL param on mount, runs the same search the toolbar input would (regex-escaped so the literal job name matches), and then strips the param so a refresh doesn't re-fire.

### Help popovers

The `?` buttons next to Frame Spec and Command To Run open small themed popovers with:

- **Frame Spec** examples: `1-10`, `1-100x2`, `1-100y2`, `1-100:2`, `1,3,5,7`, `1-50,75-100`.
- **Command tokens** substituted by cuebot at dispatch: `#IFRAME#`, `#ZFRAME#`, `#FRAME_START#`, `#FRAME_END#`, `#FRAME_CHUNK#`, `#FRAMESPEC#`, `#LAYER#`, `#JOB#`, `#FRAME#`.

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
| `show.ShowInterface/GetActiveShows` | List active shows for the Shows page |
| `show.ShowInterface/FindShow` | Get specific show |
| `show.ShowInterface/CreateShow` | Create a show |
| `show.ShowInterface/EnableBooking` / `EnableDispatching` | Toggle a show's booking / dispatch |
| `show.ShowInterface/SetDefaultMaxCores` / `SetDefaultMinCores` | Set a show's default cores |
| `show.ShowInterface/SetCommentEmail` | Set a show's comment notification email |
| `show.ShowInterface/CreateSubscription` | Subscribe a show to an allocation |
| `show.ShowInterface/GetGroups` | List a show's groups for the group-tree detail page |
| `job.GroupInterface/GetJobs` | List a group's jobs (group tree, lazy-loaded per group) |
| `job.GroupInterface/ReparentGroups` | Move groups under a new parent group (group-tree drag) |
| `job.GroupInterface/ReparentJobs` | Move jobs into a group (group-tree drag) |
| `job.JobInterface/GetJobs` | List jobs for show |
| `job.JobInterface/FindJob` | Get specific job |
| `job.JobInterface/GetFrames` | Get frames for job |
| `job.JobInterface/Pause` | Pause job |
| `job.JobInterface/Resume` | Resume job |
| `job.JobInterface/Kill` | Kill job |
| `job.JobInterface/GetComments` | List comments for a job |
| `job.JobInterface/AddComment` | Add a new comment to a job |
| `comment.CommentInterface/Save` | Update an existing comment's subject/message |
| `comment.CommentInterface/Delete` | Delete a comment |
| `layer.LayerInterface/GetLayer` | Get layer details |
| `layer.LayerInterface/GetFrames` | Get frames for layer |
| `frame.FrameInterface/Retry` | Retry frame |
| `frame.FrameInterface/Kill` | Kill frame |
| `frame.FrameInterface/Eat` | Eat frame |
| `host.HostInterface/GetHosts` | List hosts for the Monitor Hosts page |
| `facility.AllocationInterface/GetAll` | List allocations (Allocations page + subscription dropdowns) |
| `host.HostInterface/FindHost` | Resolve a single host by name for the host detail page |
| `host.HostInterface/GetProcs` | List the procs running on a host (detail page Procs tab) |
| `host.HostInterface/GetComments` | List a host's comments (detail page Comments tab) |
| `host.HostInterface/Lock` / `Unlock` | Lock / unlock a host |
| `host.HostInterface/Reboot` / `RebootWhenIdle` | Reboot a host immediately / when idle |
| `host.HostInterface/AddTags` / `RemoveTags` | Add / remove host tags |

### CueWeb Proxy Routes

The browser does not call REST Gateway directly; it goes through Next.js API proxies that attach the JWT. Comment- and host-related routes:

| Route | Forwards to |
|-------|-------------|
| `POST /api/job/getcomments` | `job.JobInterface/GetComments` |
| `POST /api/job/action/addcomment` | `job.JobInterface/AddComment` |
| `POST /api/job/action/addsubscriber` | `job.JobInterface/AddSubscriber` |
| `POST /api/comment/action/save` | `comment.CommentInterface/Save` |
| `POST /api/comment/action/delete` | `comment.CommentInterface/Delete` |
| `POST /api/host/gethosts` | `host.HostInterface/GetHosts` (unwraps the gateway's double-nested `{hosts:{hosts:[...]}}` to a flat array) |
| `POST /api/host/findhost` | `host.HostInterface/FindHost` (unwraps to the bare host, or `null`) |
| `POST /api/host/getprocs` | `host.HostInterface/GetProcs` (unwraps `{procs:{procs:[...]}}` to a flat array) |
| `POST /api/host/getcomments` | `host.HostInterface/GetComments` (unwraps `{comments:{comments:[...]}}` to a flat array) |
| `POST /api/host/action/lock` | `host.HostInterface/Lock` |
| `POST /api/host/action/unlock` | `host.HostInterface/Unlock` |
| `POST /api/host/action/reboot` | `host.HostInterface/Reboot` |
| `POST /api/host/action/rebootwhenidle` | `host.HostInterface/RebootWhenIdle` |
| `POST /api/host/action/addtags` | `host.HostInterface/AddTags` (body `{ host, tags }`) |
| `POST /api/host/action/removetags` | `host.HostInterface/RemoveTags` (body `{ host, tags }`) |
| `POST /api/show/getactiveshows` | `show.ShowInterface/GetActiveShows` (unwraps `{shows:{shows:[...]}}` to a flat array) |
| `POST /api/allocation/getall` | `facility.AllocationInterface/GetAll` (unwraps `{allocations:{allocations:[...]}}` to a flat array) |
| `POST /api/show/action/enablebooking` | `show.ShowInterface/EnableBooking` (body `{ show, enabled }`) |
| `POST /api/show/action/enabledispatching` | `show.ShowInterface/EnableDispatching` (body `{ show, enabled }`) |
| `POST /api/show/action/setdefaultmaxcores` | `show.ShowInterface/SetDefaultMaxCores` (body `{ show, max_cores }`) |
| `POST /api/show/action/setdefaultmincores` | `show.ShowInterface/SetDefaultMinCores` (body `{ show, min_cores }`) |
| `POST /api/show/action/setcommentemail` | `show.ShowInterface/SetCommentEmail` (body `{ show, email }`) |
| `POST /api/show/action/createsubscription` | `show.ShowInterface/CreateSubscription` (body `{ show, allocation_id, size, burst }`) |
| `POST /api/show/getgroups` | `show.ShowInterface/GetGroups` (group-tree detail page; body `{ show: { id } }`) |
| `POST /api/group/getjobs` | `job.GroupInterface/GetJobs` (a group's jobs; body `{ group: { id } }`) |
| `POST /api/group/action/reparentgroups` | `job.GroupInterface/ReparentGroups` (body `{ group: { id }, groups: { groups: [...] } }`) |
| `POST /api/group/action/reparentjobs` | `job.GroupInterface/ReparentJobs` (body `{ group: { id }, jobs: { jobs: [...] } }`) |

The `/api/host/action/*` routes validate the request body (`400` on malformed JSON or a missing `host`; `addtags` / `removetags` additionally require a `tags` array), forward through `handleRoute`, and propagate the gateway's real HTTP status (a failed RPC returns its `4xx`/`5xx`, not `200`).

The `/api/show/action/*` routes likewise validate their bodies (`400` on malformed JSON or a missing/mistyped field: `enabled` must be boolean, `max_cores`/`min_cores` must be numeric, `allocation_id` a non-empty string) and propagate the real HTTP status. `createsubscription` maps Cuebot's duplicate-key error to a short "show already has a subscription on that allocation" message.

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

## Global Application Header

CueWeb mounts a persistent header at the top of every authenticated route
via `app/layout.tsx`. The header is implemented in
`components/ui/app-header.tsx` and is hidden on `/login*` routes only.

Layout, left to right:

- **OpenCue logo + "CueWeb" wordmark**: The logo swaps between
  `public/opencue-icon-black.png` and
  `public/opencue-icon-white.png` (dark mode). Clicking the logo returns
  to `/` (Monitor Jobs).
- **File** dropdown:
  - Disable Job Interaction - read-only safety toggle (see
    [Disable Job Interaction](#disable-job-interaction-safety-mode)).
- **Cuebot Facility** dropdown: one item per configured facility (default
  `local` / `dev` / `cloud` / `external`; overridable via
  `NEXT_PUBLIC_CUEBOT_FACILITIES`). A small chip on the menu trigger
  shows the currently-active facility. Selecting a facility writes the choice
  to the `cueweb.facility` cookie and reloads the page; every server-side API
  route then resolves that request's gateway via `lib/facility.ts`
  (`getRequestFacilityTarget`), so all data is fetched from the selected
  facility's REST gateway. The gateway URL + JWT secret per facility come from
  `CUEBOT_<NAME>_REST_GATEWAY_URL` / `CUEBOT_<NAME>_JWT_SECRET`, falling back to
  `NEXT_PUBLIC_OPENCUE_ENDPOINT` / `NEXT_JWT_SECRET`. The bottom status bar
  shows the active facility and pings that facility's gateway.
- **Cuetopia** dropdown:
  - Monitor Jobs (`/`)
- **CueCommander** dropdown (mirrors the CueGUI Views/Plugins menu):
  - Allocations (`/allocations`) - implemented; allocations table with
    cores/hosts stats (see [Allocations](#allocations)).
  - Limits (`/limits`)
  - Monitor Cue (`/monitor-cue`)
  - Monitor Hosts (`/hosts`) - implemented; host registry with row actions
    (lock/unlock, reboot, edit tags) and a per-host detail page (see
    [Monitor Hosts](#monitor-hosts)).
  - Redirect (`/redirect`)
  - Services (`/services`)
  - Shows (`/shows`) - implemented; shows stats table with Create Show, Show
    Properties, and Create Subscription, plus a per-show group-tree detail page
    at `/shows/[showName]` (see [Shows](#shows)).
  - Stuck Frame (`/stuck-frames`)
  - Subscription Graphs (`/subscription-graphs`)
  - Subscriptions (`/subscriptions`)

  Routes that have not been implemented yet 404 gracefully.
- **Other** dropdown:
  - **Attributes** - toggles the docked Attributes panel (see
    [Attributes Panel](#attributes-panel)).
  - **Show Shortcuts** - opens the keyboard-shortcuts overlay (same as
    pressing `?`). Dispatches a `cueweb:open-shortcuts` `CustomEvent`
    on `window` that the `KeyboardShortcuts` component listens for.
  - **Notify on Shortcut** - toggle that controls whether every
    triggered shortcut also fires a small toast naming the action.
    Default ON. Persisted under
    `localStorage["cueweb.shortcutNotifications"]` with cross-tab sync
    via the `storage` event plus a `cueweb:shortcut-notifications-changed`
    `CustomEvent`. See
    [Keyboard shortcuts overlay (+ menu access)](#keyboard-shortcuts-overlay--menu-access).
- **Help** dropdown - CueGUI parity:
  - A search input at the top that searches across **every** menu command
    in CueWeb via the `useMenuRegistry` hook
    (`app/utils/use_menu_registry.ts`). Matches render as `Group > Label`.
  - Online User Guide - `NEXT_PUBLIC_DOCS_URL`
    (default `https://www.opencue.io/docs/`).
  - Make a Suggestion - `NEXT_PUBLIC_SUGGESTIONS_URL`
    (default `https://github.com/AcademySoftwareFoundation/OpenCue/issues/new?labels=enhancement&template=enhancement.md`).
  - Report a Bug - `NEXT_PUBLIC_BUGS_URL`
    (default `https://github.com/AcademySoftwareFoundation/OpenCue/issues/new?labels=bug&template=bug_report.md`).
- **Theme toggle**: Switches between light and dark mode (see
  [Theming](#theming) below).
- **Sign out**: Always rendered. With a session, `signOut()` clears it and
  redirects to `/login`; without a session, the click just navigates to
  `/login`. When a session is present, the session's name or email is
  shown to the left of the button (truncated, hidden on mobile).

The `/login` page handles both auth configurations:

- `NEXT_PUBLIC_AUTH_PROVIDER=` (empty) renders only the **CueWeb Home**
  button - useful for sandbox deployments without authentication.
- `NEXT_PUBLIC_AUTH_PROVIDER=github,okta,google,ldap` (or any subset)
  renders one sign-in button per configured provider.

The header dropdown menus:

![CueWeb File menu](/assets/images/cueweb/cueweb_file_disable_job_interaction_menu.png)


![CueWeb Cuebot Facility menu](/assets/images/cueweb/cueweb_cuebot_facility_menu.png)


![CueWeb Cuetopia menu](/assets/images/cueweb/cueweb_cuetopia_monitor_jobs_menu.png)


![CueWeb CueCommander menu](/assets/images/cueweb/cueweb_cuecommander_menu_options.png)


![CueWeb Other menu](/assets/images/cueweb/cueweb_other_menu_options.png)


![CueWeb Help menu](/assets/images/cueweb/cueweb_help_menu.png)


The bottom status bar:

![CueWeb status bar](/assets/images/cueweb/cueweb_status_indicators.png)


---

## Left Sidebar

CueWeb also mounts a collapsible sidebar to the left of the content area.
Implemented in `components/ui/app-sidebar.tsx` and hidden on `/login*` and
on viewports smaller than the `md` breakpoint.

![CueWeb left sidebar](/assets/images/cueweb/cueweb_left_side_menu.png)


- Same six groups as the header (**File**, **Cuebot Facility**,
  **Cuetopia**, **CueCommander**, **Other**, **Help**), organized as
  accordion sections built on the `Collapsible` primitive.
- The group containing the currently-active route auto-expands on
  navigation.
- A **Collapse** button at the bottom toggles between expanded
  (`w-60`) and icon-only (`w-16`).
- The **Other** group mirrors the header's Other menu and ships three
  controls in both expanded and collapsed modes:
  - **Attributes** (toggle, with check icon when the panel is open).
  - **Show Shortcuts** (opens the keyboard-shortcuts overlay; same as
    pressing `?` or the header's Other ▸ Show Shortcuts item).
  - **Notify on Shortcut** (toggle, with check icon when on; controls
    the per-shortcut toast).
- Persisted state:
  - `cueweb.sidebar.collapsed` - overall expanded vs icon-only.
  - `cueweb.sidebar.openGroups` - per-group open/closed map.

---

## Mobile Navigation

On phone-sized viewports the desktop sidebar is hidden entirely. A **hamburger** button appears on the LEFT of the global header instead; tapping it opens a side drawer mirroring every sidebar group.

| Aspect | Description |
|--------|-------------|
| **Trigger** | Tap the hamburger button in the global header. |
| **Groups** | Dashboard, File (Disable Job Interaction), Cuebot Facility, Cuetopia, CueCommander, Other (Attributes / Show Shortcuts / Notify on Shortcut), Help. |
| **Scrolling** | The drawer itself scrolls when the menu list is taller than the viewport. |
| **Auto-close** | Tapping any navigation link closes the drawer automatically. |
| **Hidden on** | `/login*`. |

The drawer toggles share state with the desktop sidebar - flipping **Attributes** or **Disable Job Interaction** in the drawer is reflected in the desktop sidebar when the viewport is widened again.

### Per-row Actions button

To replace right-click on touch devices, every Jobs / Layers / Frames row has a small `⋮` Actions button as its leftmost cell. Tapping it opens the row's full context menu - the same action set you'd get from desktop right-click, including Copy Job / Layer / Frame Name, View Log, View Log on \<editor\>, Pause / Kill / Eat / Retry, etc. The column is always visible (it can't be hidden through the Columns dropdown).

### Responsive Jobs page

| Adaptation | What changes on small screens |
|------------|------------------------------|
| Search column + action toolbar | Stack vertically on small viewports instead of sitting side-by-side. |
| Monitor Jobs toolbar groups | Unmonitor and Job Actions groups stack with each label taking its own line above its buttons. The vertical divider between groups is hidden. |
| Data table containers | Horizontally swipeable so the wide grids can be navigated without forcing page-level scroll. |
| Shortcuts overlay | Caps its width and height so the dialog never bleeds past the viewport, and scrolls internally if the contents overflow. |

### LAN access

By default the client builds same-origin relative URLs for every API call, so the same image works whether the browser reaches it at `localhost` on the dev machine or at a LAN IP from a phone on the same network. The build-time `NEXT_PUBLIC_URL` env var defaults to an empty string for this reason.

| Caveat | Workaround |
|--------|-----------|
| The modern browser clipboard API is restricted to secure contexts (HTTPS / `localhost`). On plain-HTTP LAN access it's either unavailable or rejected. | CueWeb automatically falls back to a legacy copy path outside secure contexts, including iOS Safari. **Copy Job Name** / **Copy Layer Name** / **Copy Frame Name** / **Copy Log Path** still work. |
| Desktop notification popups also require a secure context. **Subscribe to Job** still works on LAN HTTP - the in-app toast always fires - but the optional OS-level notification banner is skipped. | Serve CueWeb over HTTPS (self-signed cert is enough for LAN testing) to enable the desktop popup. |

---

## Disable Job Interaction (safety mode)

Header File ▸ Disable Job Interaction (and the sidebar's File group)
toggle a single global flag persisted under
`localStorage["cueweb.safety.disable-job-interaction"]`. The
`useDisableJobInteraction` hook
(`app/utils/use_disable_job_interaction.ts`) keeps every consumer in sync
via a `cueweb:disable-job-interaction-changed` CustomEvent (same tab) and
the browser's `storage` event (cross-tab).

When the flag is on:

- A **`ReadOnlyBanner`** (`components/ui/read-only-banner.tsx`) renders an
  amber strip just under the header with a *Re-enable* button.
- The jobs toolbar action buttons (Eat Dead Frames, Retry Dead Frames,
  Pause, Unpause, Kill) disable themselves visually and ignore clicks.
  *Unmonitor* is non-destructive and remains active.
- The right-click context menus on **job**, **layer**, and **frame** rows
  dim every destructive item (Pause / Unpause / Retry / Retry Dead Frames
  / Eat / Eat Dead Frames / Kill). The Pause/Unpause entry is a single
  toggle whose label flips on `isPaused` - both flavors are dimmed the
  same way. *Unmonitor* and *Comments* on the job menu remain active.

![CueWeb read-only banner when job interaction is disabled](/assets/images/cueweb/cueweb_file_disable_job_interaction_enabled.png)


---

## Attributes Panel

Other ▸ Attributes (header or sidebar) toggles a docked drawer
implemented in `components/ui/attributes-panel.tsx`.

- **Selection**: clicking any row in the jobs table fires
  `setAttributeSelection({...})` from
  `app/utils/use_attribute_selection.ts`. The panel listens via the
  `useAttributeSelection` hook and re-renders for the new entity.
- **Position**: a dock-position picker in the title bar lets users place
  the panel on the **right** (default), **bottom**, **left**, or **top**
  of the viewport. Persisted under `cueweb.attributes.position`.
- **Open state**: persisted under `cueweb.attributes.open` (and synced
  across consumers via `cueweb:attributes-panel-changed`).
- **Filter input**: narrows the key/value tree live; parent groups stay
  visible whenever any descendant matches.

The Attributes panel for a selected job and for a selected layer:

![CueWeb attributes panel for a job](/assets/images/cueweb/cueweb_other_menu_attributes_job.png)


![CueWeb attributes panel for a layer](/assets/images/cueweb/cueweb_other_menu_attributes_layer.png)


The panel docked on each edge of the viewport - right, bottom, left, and top:

![CueWeb attributes panel docked right](/assets/images/cueweb/cueweb_other_menu_attributes_dock_right.png)


![CueWeb attributes panel docked bottom](/assets/images/cueweb/cueweb_other_menu_attributes_dock_bottom.png)


![CueWeb attributes panel docked left](/assets/images/cueweb/cueweb_other_menu_attributes_dock_left.png)


![CueWeb attributes panel docked top](/assets/images/cueweb/cueweb_other_menu_attributes_dock_top.png)


---

## Breadcrumbs

Reusable primitive at `components/ui/breadcrumbs.tsx`, accepting
`Array<{ label, href?, title? }>`. Renders a Home icon segment (`/`) by
default, separates segments with `ChevronRight`, and gives the last
segment `aria-current="page"`. Labels are wrapped in a Radix Tooltip
with `max-w-[40ch] truncate`, so over-long names collapse with an
ellipsis and the full text is recoverable on hover.

Currently mounted on every detail view (non-last segments are
`next/link`s; segments without an `href` render as plain text):

- `/frames/[frame-name]` -> `Home > Jobs > <jobName> > <layerName> > <frameName>`
  - The job name is parsed from the `frameLogDir` query parameter
    (RQD logs are named `<jobName>.<frameName>.rqlog`).
  - The layer name and frame name come from the loaded `Frame` payload,
    falling back to the route param while the fetch is pending.
- `/jobs/[job-name]/comments` -> `Home > Jobs > <jobName> > Comments`

Per-job and per-layer detail pages do not exist yet, so those segments
currently render as plain text; once those routes land they can be
upgraded to clickable links by setting the `href` field on the
corresponding `BreadcrumbItem`.

---

## Status Bar

CueWeb mounts an IDE-style fixed status bar at the bottom of every
authenticated route. Implemented in `components/ui/status-bar.tsx` and
hidden on `/login*`. Three metrics, each with a tooltip:

- **Gateway** (left): a colored dot, the literal `Online` / `Offline`,
  and the last round-trip latency in milliseconds when online.
  - Polled every 10s by `fetch('/api/health')`. The probe POSTs `{}` to
    `show.ShowInterface/GetActiveShows` with a 5s `AbortController`
    timeout and reports `{ gatewayOnline, status, latencyMs, checkedAt,
    error? }`.
  - When the gateway is unreachable, the whole bar's surface turns red
    so the failure is visible at a glance.
- **Last refresh** (center): live relative timestamp ("just now",
  "Ns ago", ...). Updated whenever the jobs table fires a
  `cueweb:jobs-refreshed` CustomEvent (every 5s while the table is
  mounted). Re-renders once per second so the timestamp stays accurate
  between events.
- **Version** (right): `v<NEXT_PUBLIC_APP_VERSION>`. Resolved at build
  time in `next.config.js`:
  1. If `NEXT_PUBLIC_APP_VERSION` is set, that value wins.
  2. Otherwise it falls back to the `version` field in
     `cueweb/package.json`.
  - The Dockerfile exposes a matching `ARG NEXT_PUBLIC_APP_VERSION`, so
    CI can pass a Git SHA or build tag via `--build-arg`.

### `GET /api/health`

Cheap reachability check used by the status bar. Returns a 200 with the
following body in both the healthy and unhealthy cases (so the UI can
render the offline state without surfacing a network-tab error):

```json
{
  "gatewayOnline": true,
  "status": 200,
  "latencyMs": 30,
  "checkedAt": "2026-05-20T07:58:51.098Z"
}
```

When `gatewayOnline` is `false`, the response additionally includes an
`error` field with a short human-readable hint.

---

## Theming

### Theme Toggle

CueWeb supports light and dark themes:

- **Light Mode**: Default theme with light backgrounds
- **Dark Mode**: Dark theme for reduced eye strain

Toggle via the sun/moon button in the global header (or press `t`). The choice persists across sessions. Every view has a dark equivalent; for example, the Monitor Jobs page in dark mode:

![CueWeb Monitor Jobs in dark mode](/assets/images/cueweb/cueweb_cuetopia_monitor_jobs_mainpage_dark.png)

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
├── app/                              # Next.js app directory
│   ├── api/                          # API proxy routes
│   │   ├── comment/action/save/      # CommentInterface/Save
│   │   ├── comment/action/delete/    # CommentInterface/Delete
│   │   └── job/
│   │       ├── action/addcomment/    # JobInterface/AddComment
│   │       └── getcomments/          # JobInterface/GetComments
│   ├── jobs/                         # Jobs pages
│   │   └── [job-name]/comments/      # Per-job Comments page
│   ├── utils/                        # Client helpers
│   │   ├── action_utils.ts           # add/save/delete comment helpers
│   │   ├── get_utils.ts              # getJobComments
│   │   └── comment_macros.ts         # Predefined-macro localStorage CRUD
│   ├── login/                        # Login page
│   └── page.tsx                      # Main page
├── components/                       # React components
│   └── ui/                           # Shadcn UI components
├── lib/                              # Utility libraries
│   └── auth.ts                       # Authentication config
├── public/                           # Static assets
├── Dockerfile                        # Container configuration
├── next.config.js                    # Next.js configuration
├── package.json                      # Dependencies (incl. react-markdown, rehype-sanitize)
└── tailwind.config.js                # Tailwind CSS config
```

---

## Related Documentation

- [CueWeb Quick Start](/docs/quick-starts/quick-start-cueweb/) - Getting started guide
- [CueWeb User Guide](/docs/user-guides/cueweb-user-guide/) - Complete usage guide
- [CueWeb Tutorial](/docs/tutorials/cueweb-tutorial/) - Step-by-step tutorial
- [CueWeb Developer Guide](/docs/developer-guide/cueweb-development/) - Development reference
- [REST API Reference](/docs/reference/rest-api-reference/) - API documentation
- [Deploying CueWeb](/docs/getting-started/deploying-cueweb/) - Deployment guide
