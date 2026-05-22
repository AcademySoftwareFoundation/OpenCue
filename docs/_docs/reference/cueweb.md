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
| `NEXT_PUBLIC_DOCS_URL` | Online User Guide link in the Help menu. | `https://www.opencue.io/docs/` |
| `NEXT_PUBLIC_SUGGESTIONS_URL` | Make a Suggestion link in the Help menu. | CueGUI default (GitHub issues, `enhancement` template) |
| `NEXT_PUBLIC_BUGS_URL` | Report a Bug link in the Help menu. | CueGUI default (GitHub issues, `bug_report` template) |
| `NEXT_PUBLIC_URL` | Base URL the client uses when calling the Next.js API routes. **Default empty** = the client builds same-origin relative URLs (`/api/job/getjobs`, ...) so CueWeb works from any host the browser reached it at (`http://localhost:3000` on the dev Mac, `http://<lan-ip>:3000` from a phone on the same network). Set to an absolute URL only if your deployment serves the API on a different origin than the UI. | (empty) |
| `NEXT_PUBLIC_LOG_EDITOR_URL` | URL template for the Frame context menu's **View Log on \<editor\>** item. The literal `{path}` is substituted with the absolute rqlog path at click time. Common values: `vscode://file{path}`, `vscode-insiders://file{path}`, `subl://open?url=file://{path}`, `txmt://open?url=file://{path}`, `idea://open?file={path}`. Empty hides the menu item entirely. The sandbox `docker-compose.yml` defaults to `vscode://file{path}`. | `vscode://file{path}` (sandbox) / empty (Dockerfile default) |

### Authentication Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `NEXT_PUBLIC_AUTH_PROVIDER` | Comma-separated auth providers. Supported values: `local`, `okta`, `google`, `github`, `ldap`. Empty = sandbox mode (no login). | `local,okta,google,github,ldap` |
| `NEXTAUTH_URL` | NextAuth callback URL | `http://localhost:3000` |
| `NEXTAUTH_SECRET` | NextAuth session secret | `random-secret` |

**Note:** Set `NEXT_PUBLIC_AUTH_PROVIDER=` (empty) for no authentication. With an empty value CueWeb runs unauthenticated and the RBAC enforcement layer short-circuits to "allow", which matches the pre-RBAC behavior. The value must match between build time (`--build-arg`) and runtime (`environment:`) - the build-arg value is what the client bundle sees.

### RBAC Variables

These take effect when `NEXT_PUBLIC_AUTH_PROVIDER` is non-empty.

| Variable | Description | Default |
|----------|-------------|---------|
| `CUEWEB_GROUPS_RESOLVER` | Active groups resolver. One of `okta`, `ldap`, or `none`. Selects how CueWeb maps an external identity to a list of groups on each sign-in. Google and GitHub sign-ins always land in the users table but do not sync groups; admins assign roles directly. | `none` |
| `CUEWEB_RBAC_DB` | Path to the SQLite policy store. Use `:memory:` in CI / tests. | `/data/cueweb-rbac.db` |
| `LDAP_SEARCH_USER_DN` | Optional service-account DN used by the LDAP groups resolver for the `memberOf` lookup. Falls back to anonymous bind if unset. | (empty) |
| `LDAP_SEARCH_USER_PASSWORD` | Companion to `LDAP_SEARCH_USER_DN`. | (empty) |

### Identity Provider Variables

#### Okta

| Variable | Description |
|----------|-------------|
| `NEXT_AUTH_OKTA_CLIENT_ID` | Okta application client ID |
| `NEXT_AUTH_OKTA_CLIENT_SECRET` | Okta application client secret |
| `NEXT_AUTH_OKTA_ISSUER` | Okta issuer URL (e.g., `https://company.okta.com`) |

When `CUEWEB_GROUPS_RESOLVER=okta`, the Okta application must be configured to include a `groups` claim in the ID token (Okta admin -> Applications -> _your app_ -> Sign On -> OpenID Connect ID Token -> Groups claim type: Filter, matching the group names you want to expose).

#### Google

| Variable | Description |
|----------|-------------|
| `GOOGLE_CLIENT_ID` | Google OAuth client ID |
| `GOOGLE_CLIENT_SECRET` | Google OAuth client secret |

Google sign-ins are written into the RBAC store as `source=imported` so admins can attach roles directly. Group sync is not available.

#### GitHub

| Variable | Description |
|----------|-------------|
| `GITHUB_ID` | GitHub OAuth application ID |
| `GITHUB_SECRET` | GitHub OAuth application secret |

GitHub sign-ins are written into the RBAC store as `source=imported` so admins can attach roles directly. Group / team sync is not available.

#### LDAP

| Variable | Description |
|----------|-------------|
| `LDAP_URI` | LDAP server URI (e.g., `ldaps://ldap.company.com:636`) |
| `LDAP_LOGIN_DN` | Login DN template with `{login}` placeholder |
| `LDAP_CERTIFICATE` | Path to CA certificate for TLS verification |

#### Local

The built-in local Credentials provider needs no additional environment variables. On first launch CueWeb generates a random password for the bootstrap `admin` user, prints it once to the container log, and writes it to `/data/.cueweb-bootstrap` (mode 0600).

### Monitoring Variables

| Variable | Description |
|----------|-------------|
| `SENTRY_DSN` | Sentry Data Source Name for error tracking |
| `SENTRY_ENVIRONMENT` | Sentry environment name |
| `SENTRY_URL` | Sentry server URL |
| `SENTRY_ORG` | Sentry organization |
| `SENTRY_PROJECT` | Sentry project name |

---

## RBAC and Admin UI

CueWeb ships a Role-Based Access Control layer that activates whenever `NEXT_PUBLIC_AUTH_PROVIDER` is non-empty. The policy lives in a SQLite database (`/data/cueweb-rbac.db` by default) and is managed end-to-end from a web Admin UI at `/admin`.

### Bootstrap admin (first launch with `local` enabled)

When `local` is listed in `NEXT_PUBLIC_AUTH_PROVIDER` and the policy store has no admins yet, CueWeb runs a one-time bootstrap flow at server startup:

1. Generates a 24-character cryptographically random password.
2. Inserts a local user `admin` (source = local) and gives it the `site-admin` role plus admin-UI access.
3. Writes the credentials to `/data/.cueweb-bootstrap` with mode `0600` and prints them once in a banner to the container log.
4. Marks the user as `must_change_password=1` so the first sign-in lands on `/login/change-password` and forces a rotation before reaching the dashboard.

### Built-in roles

| Role | Permissions | Notes |
|------|-------------|-------|
| `site-admin` | `*` (wildcard) | Cannot be deleted. Holds admin-UI access. |
| `operator` | `jobs.view`, `jobs.kill`, `jobs.retry`, `jobs.pause`, `jobs.eat`, `jobs.set_max_retries`, `jobs.set_auto_eat`, `layers.view`, `layers.kill`, `layers.retry`, `frames.view`, `frames.eat`, `frames.retry`, `frames.kill`, `hosts.view`, `hosts.lock`, `hosts.unlock`, `shows.view`, `cuecommander.open` | Day-to-day production operator. |
| `viewer` | `jobs.view`, `layers.view`, `frames.view`, `hosts.view`, `shows.view` | Read-only. |

Custom roles can be added in the **Roles** tab; built-in rows are protected from deletion.

### Permission catalog

| Permission | Description |
|-------------|-------------|
| `*` | Wildcard. Held only by `site-admin`. |
| `jobs.view` / `jobs.kill` / `jobs.retry` / `jobs.pause` / `jobs.eat` | Per-action job verbs. |
| `jobs.set_max_retries` / `jobs.set_auto_eat` | Job-level configuration. |
| `layers.view` / `layers.kill` / `layers.retry` | Per-action layer verbs. |
| `frames.view` / `frames.eat` / `frames.retry` / `frames.kill` | Per-action frame verbs. |
| `hosts.view` / `hosts.lock` / `hosts.unlock` / `hosts.reboot` | Per-action host verbs. |
| `shows.view` / `shows.edit` | Show inspection / configuration. |
| `cuecommander.open` | Gates the CueCommander mega-menu and pages. |

### Admin UI tabs

| Tab | URL | Purpose |
|-----|-----|---------|
| Overview | `/admin` | Stat cards: total users, groups, roles, admins. |
| Users | `/admin/users` | List + search users, create local users, deactivate, reset password, attach/detach direct roles. |
| Groups | `/admin/groups` | List groups with their source badge (`local` / `okta` / `ldap` / `imported`), create local groups, attach/detach roles. Externally sourced groups cannot be deleted from the UI. |
| Roles | `/admin/roles` | Built-in + custom roles, edit permission sets, create / rename / delete custom roles. Built-ins are protected. |
| Permissions | `/admin/permissions` | Read-only catalog rendered from the same source the role editor reads. |
| Admins | `/admin/admins` | Users with admin-UI access. Add by username, email, or external ID (Okta `sub`, LDAP DN, etc.). Last admin cannot be removed. |
| Audit log | `/admin/audit` | Filterable, paginated history of every mutation, with before/after JSON. CSV export. |

### Audit log entries

Every mutation through `/api/admin/*` writes one row with these columns: `id`, `ts`, `actor_id`, `actor_label`, `action`, `target`, `before_json`, `after_json`. Action strings are namespaced (`user.create`, `user.role_attach`, `group.delete`, `role.update`, `admin.add`, `admin.remove`, `bootstrap.admin_created`, `user.self_password_change`, etc.).

### Bootstrap password recovery

If you lose `/data/.cueweb-bootstrap` and the password is not in the container log retention window:

```bash
docker compose down cueweb
docker volume rm opencue_cueweb-data
docker compose up -d cueweb && docker compose logs cueweb --tail 20
```

This resets the policy store; the first-launch flow runs again and prints a fresh password. The audit log is reset along with the policy store; if you want to preserve it, export it from the **Audit log** tab first.

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

### Inline JobDetails (Layers + Frames panel)

Clicking a row in the Jobs table populates `JobDetailsInline` (`cueweb/components/ui/job-details-inline.tsx`), which renders the **Layers** and **Frames** tables stacked below the jobs grid (CueGUI Monitor Jobs + Monitor Job Details parity).

| Behavior | Description |
|----------|-------------|
| **Layers panel** | Lists every layer in the selected job, including the Progress bar and Eligible time. |
| **Layer-click** | Toggles a frames-table filter to that layer (`frame.layerName === layer.name`) and pushes the layer's attributes into the docked Attributes panel. Clicking the same layer again clears the filter and re-selects the job in Attributes. |
| **Frames panel** | Lists every frame in the job (or the layer-filtered subset). Total count shows `X of Y` when filtered. |
| **Refresh** | Both panels poll every 5 seconds, with cancellation guards so a stale response cannot overwrite a fresh selection. |
| **Log viewer** | Double-clicking any frame row opens the log viewer (`/frames/<frameName>?frameId=...&frameLogDir=...`). |

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
| **Email Artist** | Compose an email to the job's owner. *(placeholder)* |
| **Request Cores** | Open the Request Cores dialog. *(placeholder)* |
| **Subscribe to Job** | Same as clicking the Notify bell. *(placeholder)* |
| **Comments** | Open the per-job Comments page (`/jobs/<jobName>/comments`). |
| **Use Local Cores** | Reserve local cores for this job. *(placeholder)* |
| **View Dependencies** | Open the dependency graph for the job. *(placeholder)* |
| **Dependency Wizard** | Open the dependency-creation wizard. *(placeholder)* |
| **Drop External Dependencies** | Drop external job-on-job dependencies. |
| **Drop Internal Dependencies** | Drop internal layer-on-layer dependencies. |
| **Set User Color** / **Clear User Color** | Drive the User Color column for this job. *(placeholder)* |
| **Set Max Retries** | Edit the per-frame retry budget. |
| **Reorder Frames** / **Stagger Frames** | Open the reorder / stagger dialogs. *(placeholder)* |
| **Pause** / **Unpause** | Pause or resume the job. |
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
| `job.JobInterface/GetComments` | List comments for a job |
| `job.JobInterface/AddComment` | Add a new comment to a job |
| `comment.CommentInterface/Save` | Update an existing comment's subject/message |
| `comment.CommentInterface/Delete` | Delete a comment |
| `layer.LayerInterface/GetLayer` | Get layer details |
| `layer.LayerInterface/GetFrames` | Get frames for layer |
| `frame.FrameInterface/Retry` | Retry frame |
| `frame.FrameInterface/Kill` | Kill frame |
| `frame.FrameInterface/Eat` | Eat frame |

### CueWeb Proxy Routes

The browser does not call REST Gateway directly; it goes through Next.js API proxies that attach the JWT. Comment-related routes:

| Route | Forwards to |
|-------|-------------|
| `POST /api/job/getcomments` | `job.JobInterface/GetComments` |
| `POST /api/job/action/addcomment` | `job.JobInterface/AddComment` |
| `POST /api/comment/action/save` | `comment.CommentInterface/Save` |
| `POST /api/comment/action/delete` | `comment.CommentInterface/Delete` |

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
  `public/opencue-icon-black.png` (light mode) and
  `public/opencue-icon-white.png` (dark mode). Clicking the logo returns
  to `/` (Monitor Jobs).
- **File** dropdown:
  - Disable Job Interaction - read-only safety toggle (see
    [Disable Job Interaction](#disable-job-interaction-safety-mode)).
- **Cuebot Facility** dropdown: one item per configured facility (default
  `local` / `dev` / `cloud` / `external`; overridable via
  `NEXT_PUBLIC_CUEBOT_FACILITIES`). A small chip on the menu trigger
  shows the currently-active facility.
- **Cuetopia** dropdown:
  - Monitor Jobs (`/`)
- **CueCommander** dropdown (mirrors the CueGUI Views/Plugins menu):
  - Allocations (`/allocations`)
  - Limits (`/limits`)
  - Monitor Cue (`/monitor-cue`)
  - Monitor Hosts (`/hosts`)
  - Redirect (`/redirect`)
  - Services (`/services`)
  - Shows (`/shows`)
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

---

## Left Sidebar

CueWeb also mounts a collapsible sidebar to the left of the content area.
Implemented in `components/ui/app-sidebar.tsx` and hidden on `/login*` and
on viewports smaller than the `md` breakpoint.

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
  dim every destructive item (Pause / Retry / Retry Dead Frames / Eat /
  Eat Dead Frames / Kill). *Unmonitor* and *Comments* on the job menu
  remain active.

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

Toggle via the sun/moon button in the global header.

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
