---
title: "CueWeb Tutorial"
nav_order: 85
parent: Tutorials
layout: default
linkTitle: "Getting Started with CueWeb"
date: 2024-09-17
description: >
  Step-by-step tutorial for using CueWeb to manage OpenCue render jobs
---

# CueWeb Tutorial
{: .no_toc }

Learn how to use CueWeb's web interface to monitor jobs, manage frames, and control your OpenCue render farm.

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

This tutorial will guide you through using CueWeb, OpenCue's web-based interface. You'll learn how to monitor jobs, manage frames, search for specific jobs, and perform common render farm operations through your browser.

### What you'll learn

- How to navigate the CueWeb interface
- Job monitoring and management techniques
- Frame-level operations and troubleshooting
- Search and filtering capabilities
- Team collaboration features

### Prerequisites

- CueWeb deployed and accessible
- OpenCue render farm with some test jobs
- Basic understanding of render farm concepts

---

## Getting Started

### Accessing CueWeb

1. Open your web browser
2. Navigate to your CueWeb URL (e.g., `http://cueweb.company.com:3000`)
3. If authentication is enabled, sign in with your credentials

You should see the main CueWeb dashboard with the jobs table.

### Interface Overview

The CueWeb interface consists of:

- **Global header (persistent across every authenticated route):**
  - OpenCue logo (theme-aware: black in light mode, white in dark mode) + the **CueWeb** wordmark on the left, clickable as a link back to the jobs dashboard.
  - Six dropdown menus mirroring the CueGUI menu bar:
    - **File** -> Disable Job Interaction (read-only safety toggle).
    - **Cuebot Facility** -> switch between the options (e.g.: `local` / `dev` / `cloud` / `external`); the active facility is shown as a chip on the trigger.
    - **Cuetopia** -> Monitor Jobs.
    - **CueCommander** -> Allocations, Limits, Monitor Cue, Monitor Hosts, Redirect, Services, Shows, Stuck Frame, Subscription Graphs, Subscriptions. Routes that are not yet implemented 404 gracefully.
    - **Other** -> Attributes (toggles the docked Attributes panel), Show Shortcuts (opens the same overlay as `?`), Notify on Shortcut (toggle for the per-shortcut toast).
    - **Help** -> a search box that finds commands across every menu, plus Online User Guide, Make a Suggestion, and Report a Bug.
  - Theme toggle and an always-visible **Sign out** button on the right. With an active session, Sign out clears it and returns you to `/login`. Without a session (or when auth is disabled), it simply navigates to `/login`.
- **Left sidebar (persistent, collapsible):** same six groups as the header, organized as accordion sections. The group containing the active route auto-expands; click **Collapse** at the bottom to shrink the sidebar to an icon rail (your choice persists).
- **Read-only banner:** appears only when *Disable Job Interaction* is on; describes the read-only state and offers a *Re-enable* button. Destructive toolbar buttons and right-click menu items are dim and inert in this state.
- **Attributes panel:** docked drawer toggled from Other ▸ Attributes. Click a row in the jobs table to populate it; use the title-bar position picker to dock it on the right, bottom, left, or top of the viewport.
- **Breadcrumb (detail pages only):** above the frame log and the per-job comments page, a small "Home > Jobs > ..." trail lets you click back to the jobs index or to any parent in the path. Long labels truncate with an ellipsis; hover any segment to see the full text.
- **Bottom status bar:** fixed 24-pixel bar at the bottom of every page. Shows REST gateway status (a dot + Online/Offline + round-trip latency), the time since the jobs table last refreshed, and the CueWeb build version. The whole bar turns red when the gateway is unreachable.
- **Filter Bar**: Show selection, status filters, and search
- **Jobs Table**: Main view of all jobs with sortable columns
- **Action Buttons**: Job control operations

---

## Monitoring Jobs

### Viewing Your Jobs

1. **Select Your Show**: Use the show dropdown to filter jobs for your project
2. **Apply Status Filters**: Click filter buttons to show only:
   - Active jobs (running or pending)
   - Paused jobs
   - Failed jobs
   - All jobs

3. **Sort Jobs**: Click column headers to sort by:
   - Priority (highest first)
   - Progress (completion percentage)
   - Start time (newest first)

4. **Inspect Per-state Progress**: Hover the progress bar in the **Progress** column to display a tooltip with the exact frame count and percentage for each state (succeeded, running, waiting, depend, dead).

5. **Subscribe to Job Completion**: Click the bell in the **Notify** column to subscribe to a notification when a job reaches `FINISHED`. The bell cycles through three visual states:
   - Outline bell &rarr; not subscribed
   - Filled bell &rarr; subscribed, waiting
   - Filled bell with green dot &rarr; notification has fired (click to clear)

   The subscription always succeeds; the OS-level notification permission is requested afterwards as an optional upgrade. A toast tells you the outcome - `granted` (in-app + desktop popup), `denied` (in-app only), or `default` (in-app only, user dismissed the prompt). Subscriptions persist across page reloads via `localStorage` and a background poller checks each subscribed job every 15 seconds. The bell is disabled on jobs that are already `FINISHED` when first viewed.

### Understanding Job Status

Jobs are color-coded for quick identification:

- **🟢 Green**: Jobs with running frames
- **🔵 Blue**: Paused jobs
- **🟠 Orange**: Pending jobs waiting for resources
- **🔴 Red**: Jobs with failed frames
- **⚫ Gray**: Completed jobs

### Find Problem Jobs

1. Click the "Failed" filter to show jobs with errors
2. Look for jobs with red status indicators
3. Note the frame counts in the Progress column
4. Sort by "Dead Frames" to prioritize the most problematic jobs

---

## Basic Job Management

### Pausing and Resuming Jobs

Sometimes you need to pause jobs to free up resources or fix issues.

#### Pause a Job

1. Find the job you want to pause
2. Click the **Pause** button in the Actions menu
3. The job status should change to "PAUSED" with a blue indicator

#### Resume a Job

1. Find a paused job (blue indicator)
2. Click the **Unpause** button in the Actions menu
3. The job should return to "PENDING" or "RUNNING"

### Pause and Resume Practice

1. Find an active job with running frames
2. Pause the job and watch the status change
3. Wait 30 seconds for the interface to refresh
4. Resume the job
5. Observe how the job returns to the queue

---

## Job Details and Frame Management

### Viewing Job Details

CueWeb has two ways to inspect a job:

1. **Inline panel (quick look)**: Click a job row in the Jobs table. The associated Layers and Frames tables appear stacked just below the Jobs grid - the CueGUI Monitor Jobs + Monitor Job Details dock layout.

2. **Tabbed detail page (full inspection)**: Right-click a job and choose **View Job Details** (or tap the row's `⋮` Actions button on a phone). This opens `/jobs/<jobName>` with five tabs:
   - **Overview**: identity, frame and resource summary.
   - **Layers**: full Layers table.
   - **Frames**: full Frames table with the same filter chips and column controls.
   - **Comments**: preview of the job's comments with a link out to the full Comments editor.
   - **Dependencies**: placeholder for the dependency graph view.
   The active tab is stored in the URL as `?tab=<key>`, so the page is bookmarkable and the browser back / forward buttons walk between tabs.

3. To view notes attached to a job, open **Comments**:
   - Right-click the job row and choose **Comments**, or click the sticky-note icon in the Jobs table's dedicated **Comments** column (right after Name) when the job already has comments.
   - The Jobs table's Comments column is sortable - click the column header to pull jobs with comments to the top.
   - The Comments page mirrors the CueGUI Comments dialog: comment list (Subject / User / Date), a markdown-rendered preview, an editor for the selected comment, and `New` / `Save changes` / `Delete` buttons.
   - A **Use a predefined comment…** dropdown applies, adds, edits, or deletes per-browser comment macros (`localStorage` key `cueweb-comment-macros`).
   - Only a comment's author may edit or delete it; other users see it read-only.

### Understanding Layers

Each job contains one or more layers representing different render passes:

1. **Layer Information**:
   - Layer name and type
   - Frame range (start-end frames)
   - Core and memory requirements
   - Progress statistics

2. **Layer Actions**:
   - Kill all frames in layer
   - Retry failed frames
   - View frame details

### Working with Frames

Frames are the individual rendering tasks within each layer.

#### Frame Status Colors

- **🟢 Green**: Successfully completed
- **🟡 Yellow**: Currently running
- **🔴 Red**: Failed frames
- **⚫ Gray**: Waiting/pending
- **🔵 Blue**: Being retried

#### Frame Operations

1. **View Frame Logs**:
   - Double-click anywhere on the frame row to open the in-browser Monaco log viewer.
   - Or right-click → **View Log** / **Tail Log** for the same in-browser viewer.
   - On touch devices, tap the row's `⋮` Actions button (leftmost cell) → **View Log**.
   - Select log version from the dropdown inside the viewer.
   - The viewer shows an empty-state message when the frame hasn't started running yet (no log file on disk).

2. **Open Logs in an External Editor** *(optional)*:
   - If the deployment has `NEXT_PUBLIC_LOG_EDITOR_URL` configured, the Frame right-click menu also offers **View Log on \<editor\>** below **View Log**.
   - The sandbox `docker-compose.yml` ships with `vscode://file{path}` as the default → **View Log on VSCode**. Override the build arg to target Sublime / TextMate / IntelliJ instead (or set it empty to hide the item).
   - Tapping it launches the rqlog file directly in your desktop editor via the custom URL scheme - the same approach GitHub's "Open in VSCode" button uses. No need to copy the path and paste it into a terminal.
   - If the editor isn't installed (no app registered for `vscode://`, `subl://`, etc.), CueWeb shows a warning toast after a short timeout pointing you at the alternatives.

3. **Retry Failed Frames**:
   - Right-click on red (failed) frames
   - Select "Retry Frame"
   - Monitor the frame as it re-enters the queue

4. **Kill Running Frames**:
   - Right-click on yellow (running) frames
   - Select "Kill Frame"
   - Use when frames are stuck or consuming too many resources

5. **Copy frame metadata**:
   - **Copy Frame Name** copies just the frame name (e.g. `0001-test_layer`).
   - **Copy Log Path** copies the absolute rqlog path so you can paste it into a terminal or another viewer.
   - Both work on plain-HTTP LAN deployments (e.g. accessing CueWeb on your phone via the Mac's LAN IP), not just `localhost`.

6. **Filter by Frame State**:
   - The chips above the frames table — `WAITING`, `RUNNING`, `SUCCEEDED`, `DEAD`, `EATEN`, `DEPEND` — show the count for each state and act as toggles.
   - Click one or more chips to filter; multiple selections are combined with **OR**.
   - The current selection is mirrored to the URL as `?frameStates=...`, so the filtered view can be bookmarked or shared.
   - Counts on each chip always reflect the full unfiltered data set.

### Frame Troubleshooting

1. Open job details for a job with failed frames
2. Click on the "Frames" tab
3. Find a red (failed) frame
4. Click on the frame number to view logs
5. Look for error messages in the log output
6. Right-click the frame and select "Retry"
7. Watch the frame change from red to gray (pending)

---

## Advanced Search and Filtering

### Basic Search

The search bar supports multiple search patterns:

#### Simple Text Search
```
# Find jobs containing "comp"
comp

# Find jobs starting with show name
myshow-

# Find specific shot
shot_010
```

#### Show-Shot Search
```
# Find jobs by show-shot pattern
show-shot-

# Find specific shots
myshow-shot_010-
```

### Advanced Regex Search

Prefix searches with `!` to enable regex patterns:

#### Regex Examples
```
# Find jobs matching pattern
!^myshow-.*comp.*$

# Find jobs with specific frame ranges
!.*_[0-9]{3}-[0-9]{3}_.*

# Find jobs by multiple criteria
!(lighting|comp).*shot_[0-9]+
```

### Search Results Management

1. **View Suggestions**: Type to see dropdown suggestions
2. **Add to Monitor**: Click to add jobs to your dashboard
3. **Green Indicators**: Shows jobs already in your monitor
4. **Batch Selection**: Use checkboxes for multiple jobs

### Search Practice

1. **Basic Search**:
   - Type your show name followed by a hyphen
   - Note the dropdown suggestions
   - Select a job to add to monitoring

2. **Show-Shot Search**:
   - Search using `show-shot-` pattern for show-based filtering
   - Try `myshow-` to find jobs from a specific show

3. **Regex Search**:
   - Use `!.*lighting.*` to find lighting jobs
   - Try `!^[a-z]+_shot_[0-9]+` for pattern matching

---

## Table Customization

### Column Management

Each of the three data tables (Jobs, Layers, Frames) has its own **Columns** dropdown in the per-table toolbar.

1. **Show / Hide columns**:
   - Open the **Columns** dropdown.
   - Toggle the checkbox next to any column to hide / show it.

2. **Reorder columns left / right**:
   - In the same dropdown, each row has a `←` button (move column one slot left) and a `→` button (move it one slot right). Non-hideable system columns (the row-select checkbox) stay anchored, so swaps never reach across them.

3. **Reset to default**:
   - The pinned **Reset to Default** button at the top clears both column visibility AND order in one click.

4. **Filter the loaded rows**:
   - The **Filter ...** input next to the Columns dropdown performs a case-insensitive substring search across every visible column and narrows the rows already loaded. The table snaps back to page 1 on every keystroke; click the `×` button to clear the filter.

5. **Sort**:
   - Click any sortable column header to toggle ascending / descending.

Both visibility and ordering choices persist per table in `localStorage` and survive reloads, navigations, and Docker rebuilds.

## Real-time Monitoring

### Auto-refresh Settings

* **Refresh Interval**: CueWeb uses a fixed 5-second update interval for all tables.
* **Job-finished Notifications**: Subscribe to specific jobs via the bell in the **Notify** column. A background poller checks each subscribed job every 15 seconds. When the job reaches `FINISHED` an in-app toast fires (always), and a desktop popup is layered on top when you have granted the browser's notification permission. Subscriptions are stored in `localStorage` and survive page reloads; when several tabs poll the same job concurrently, only one tab actually fires the toast (cross-tab serialization via the Web Locks API).

### Monitoring Best Practices

#### Active Job Monitoring
1. **Filter to Active Jobs**: Hide completed jobs for focus
2. **Sort by Priority**: High-priority jobs at the top
3. **Watch Progress**: Monitor completion percentages
4. **Check Failed Counts**: Red numbers indicate problems

#### Problem Job Identification
1. **Failed Frame Alerts**: Look for red indicators
2. **Stuck Jobs**: Jobs with no progress over time
3. **Resource Hogs**: Jobs using excessive memory/cores
4. **Long-running Frames**: Individual frames taking too long

---

## Mobile and Remote Monitoring

CueWeb is responsive down to phone-sized viewports. Every action available on desktop has a mobile-equivalent path.

### Reaching CueWeb from a phone on the same network

1. On the machine running CueWeb, find the LAN IP: `ipconfig getifaddr en0` on macOS, `ip a` on Linux.
2. On the phone (same Wi-Fi), open `http://<lan-ip>:3000` in your browser (e.g. Safari or Google Chrome).
3. The same UI loads. The client builds same-origin relative URLs for every API call, so it works correctly from any host (no rebuild needed). This requires `NEXT_PUBLIC_URL=` (empty, the default).

### Mobile-specific UI affordances

1. **Hamburger nav drawer**:
   - The desktop sidebar is hidden below the `md` breakpoint (768px).
   - A hamburger button appears on the LEFT of the global header. Tap it to open a side drawer with every group: Dashboard, File, Cuebot Facility, Cuetopia, CueCommander, Other (Attributes / Show Shortcuts / Notify on Shortcut), Help.
   - The drawer auto-closes when you tap a navigation link.

2. **Per-row Actions menu (replaces right-click)**:
   - Every Jobs / Layers / Frames row has a small `⋮` button as its leftmost cell.
   - Tap it to open the same context menu the desktop right-click opens: Copy Job / Layer / Frame Name, View Log, View Log on \<editor\>, Pause / Kill / Eat / Retry, etc.

3. **Horizontally swipeable tables**:
   - The Jobs / Layers / Frames grids have 15-25 columns each. Phones can't fit all of them.
   - Swipe left/right inside the table to reach off-screen columns.
   - Use the **Columns** dropdown to hide columns you don't need on small screens (the choice is remembered for next time).

4. **Tap-to-trigger keyboard shortcuts**:
   - Open **Other ▸ Show Shortcuts** from the hamburger drawer.
   - Every key badge in the overlay is a real button. Tapping `/` focuses the Jobs search box, `r` refreshes the table, `t` toggles theme, `Esc` closes the overlay - no physical keyboard needed.

### Clipboard, notifications, and external editor on LAN HTTP

- **Clipboard works** on plain-HTTP LAN access. The browser's modern clipboard API is restricted to secure contexts (HTTPS / `localhost`), but CueWeb automatically uses a legacy copy path when the modern one isn't available.
- **Subscribe to Job** still works - the in-app toast always fires. The optional desktop popup is skipped on LAN HTTP because the Web Notifications API also requires a secure context; serve CueWeb over HTTPS (self-signed cert is enough) to enable that path.
- **View Log on \<editor\>** depends on the user's device having the URL scheme registered. iOS Safari doesn't route arbitrary custom schemes to apps the way macOS does, so the in-browser **View Log** is the reliable path on phones - CueWeb falls back to a warning toast when the scheme isn't handled.

---

## Troubleshooting Common Issues

### Frame Failures

When frames fail repeatedly:

1. **Check Frame Logs**:
   - Click failed frame numbers
   - Look for error patterns
   - Note resource usage

2. **Common Issues**:
   - **Memory errors**: Frames running out of RAM
   - **File not found**: Missing assets or incorrect paths
   - **License errors**: Software license unavailable
   - **Timeout errors**: Frames taking too long

3. **Resolution Steps**:
   - Retry individual frames
   - Adjust memory requirements
   - Check asset availability
   - Contact technical support

### Performance Issues

When jobs run slowly:

1. **Check Resource Allocation**:
   - Verify core and memory settings
   - Look for resource conflicts
   - Monitor host utilization

2. **Optimization Strategies**:
   - Increase priority for urgent jobs
   - Pause non-critical jobs
   - Adjust core allocations
   - Balance workload across hosts

---

### Additional Resources

- **[CueWeb User Guide](/docs/user-guides/cueweb-user-guide)** - Complete reference manual
- **[CueWeb Developer Guide](/docs/developer-guide/cueweb-development)** - For customization and development
- **[REST API Reference](/docs/reference/rest-api-reference/)** - For automation and integration
- **[OpenCue Community](/docs/concepts/opencue-overview#contact-us)** - Support and discussion
