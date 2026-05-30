---
layout: default
title: CueWeb User Guide
parent: User Guides
nav_order: 43
---

# CueWeb User Guide
{: .no_toc }

Complete guide to using CueWeb for OpenCue render farm management.

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

CueWeb is a web-based interface for managing OpenCue render farms, replicating the core functionality of CueGUI (Cuetopia and CueCommander) in a web-accessible format. It extends OpenCue access across multiple platforms, ensuring users can manage their rendering tasks from virtually anywhere.

### Key Benefits

- **Browser-based Access**: No client software installation required
- **Cross-platform**: Works on Windows, macOS, Linux, tablets, and mobile devices
- **Real-time Updates**: Automatic refresh of job status and frame progress with configurable intervals
- **Collaborative**: Multiple users can access the same interface simultaneously
- **Modern UI**: Dark/light themes, responsive design, and intuitive navigation
- **Enhanced Security**: JWT token generation for secure API communication
- **Advanced Search**: Regex-enabled search with dropdown suggestions

### Core Features

1. **Secure User Authentication**
   - Multiple OAuth providers (GitHub, Google, Okta, Apple, GitLab, Amazon, Microsoft Azure, LinkedIn, Atlassian, Auth0)
   - Email and credential-based authentication options
   - Configurable authentication through NextAuth.js

2. **Customizable Job Management Dashboard**
   - Paginated table with sortable columns
   - Column visibility controls for personalized views
   - Filter jobs by state (active, paused, completed, failing, dependency)

3. **Flexible Monitoring Controls**
   - Add/remove jobs from monitoring
   - Bulk operations on multiple selected jobs
   - Un-monitor jobs across all statuses

4. **Detailed Job Inspection**
   - Pop-up windows showing layers and frames
   - Resource allocation information
   - Job statistics and performance metrics
   - Stacked job progress bar with hover tooltip showing per-state frame counts and percentages (succeeded / running / waiting / depend / dead)
   - Frame state filter chips above the frames table (WAITING / RUNNING / SUCCEEDED / DEAD / EATEN / DEPEND) with per-state counts, OR-combined selection, and URL-persisted state

5. **Frame Navigation and Logs Access**
   - Hyperlinked frames leading to dedicated pages
   - Comprehensive log viewing with version selection
   - Real-time log updates for running frames

6. **Advanced Job Search Functionality**
   - Search by show name with "show-shot-" prefix
   - Regex search with "!" prefix
   - Dropdown suggestions with green highlighting for monitored jobs
   - Optimized loading with virtualization and web workers

7. **Context Menu Actions**
   - **Job actions**: Un-monitor, Comments, Pause/Unpause, Retry dead frames, Eat dead frames, Kill
   - **Layer actions**: Kill, Eat, Retry, Retry dead frames
   - **Frame actions**: Retry, Eat, Kill
   - Context-aware menu items (disabled for finished jobs)

8. **Auto-reloading Tables**
   - All tables (jobs, layers, frames) auto-reload at configurable intervals
   - Loading animations for better user experience

9. **Job Comments**
   - View, add, edit, and delete per-job comments (markdown-supported, sanitized)
   - Sticky-note indicator on the jobs table for jobs that already have comments
   - Predefined comment macros stored per browser for repeated text

---

## Getting Started

### Accessing CueWeb

1. Open your web browser
2. Navigate to your CueWeb URL (typically `http://your-server:3000`)
3. If authentication is enabled, sign in with your credentials

### Authentication

CueWeb supports secure authentication through multiple providers:

- **OAuth Providers**: GitHub, Google, Okta, Apple, GitLab, Amazon, Microsoft Azure, LinkedIn, Atlassian, Auth0
- **Email Authentication**: Email-based login
- **Custom Credentials**: Username/password authentication
- **Other Providers**: Additional providers can be configured using [NextAuth.js](https://next-auth.js.org/)

![CueWeb authentication page](/assets/images/cueweb/cueweb_cuetopia_monitor_jobs_login.png)


**Note**: If authentication is disabled for development, you'll see a "CueWeb Home" button to access the interface directly.

### First Time Setup

When you first access CueWeb, you'll see the main dashboard:

![CueWeb main page](/assets/images/cueweb/cueweb_cuetopia_monitor_jobs_mainpage.png)

CueWeb ships light and dark themes; use the sun/moon toggle in the header to switch (your choice persists across sessions). The rest of this guide uses light-mode screenshots, but every view has a dark equivalent - here is the same Monitor Jobs view in dark mode:

![CueWeb main page in dark mode](/assets/images/cueweb/cueweb_cuetopia_monitor_jobs_mainpage_dark.png)

The screen is composed of:

- **Global header** (persistent across every authenticated route):
  - **Logo and wordmark**: OpenCue icon (black in light mode, white in dark mode) followed by **CueWeb**. Clicking the logo returns you to the jobs dashboard (`/`).
  - **Menus** (mirror the CueGUI menu bar):
    - **File** -> *Disable Job Interaction* (read-only safety toggle, see below).
    - **Cuebot Facility** -> switch between `local` · `dev` · `cloud` · `external` (the active facility is shown as a small chip on the menu trigger).
    - **Cuetopia** -> Monitor Jobs.
    - **CueCommander** -> Allocations, Limits, Monitor Cue, Monitor Hosts, Redirect, Services, Shows, Stuck Frame, Subscription Graphs, Subscriptions. Unimplemented routes 404 gracefully - they are placeholders for upcoming features.
    - **Other** -> *Attributes* (toggles the docked Attributes panel, see below).
    - **Help** -> a search box that finds commands across **every** menu in CueWeb (CueGUI parity), plus Online User Guide, Make a Suggestion, and Report a Bug.
  - **Theme toggle**: Switch between light and dark modes (your choice persists across sessions).
  - **Sign out**: Always visible. When you are signed in, it shows your name or email next to the button and clicking it ends the session and returns you to `/login`. When you are not signed in (or when authentication is disabled in the deployment), clicking it just navigates to `/login` - the `/login` page itself shows the **CueWeb Home** button if no auth provider is configured, or the provider buttons otherwise.
- **Left sidebar** (persistent across every authenticated route):
  - Same six groups as the header (**File**, **Cuebot Facility**, **Cuetopia**, **CueCommander**, **Other**, **Help**), organized as accordion sections. The group containing the active route auto-expands; the others remember their open/closed state per browser.
  - Click the **Collapse** button at the bottom to shrink the sidebar to an icon-only rail (your choice persists across reloads). Hover an icon to see its label.
  - Hidden on `/login` and on mobile viewports.
- **Read-only banner** (only when *Disable Job Interaction* is on): an amber strip just under the header explains that destructive actions (Pause / Unpause / Retry Dead Frames / Eat Dead Frames / Kill - both in the jobs toolbar and in the right-click menus on job / layer / frame rows) are temporarily disabled. Click **Re-enable** to clear it.
- **Attributes panel** (toggled from Other ▸ Attributes): a docked drawer that displays a collapsible key/value tree for the currently-selected entity. Click any row in the jobs table to populate it. The title bar's position picker lets you dock the panel on the **right** (default), **bottom**, **left**, or **top** of the viewport - the choice persists across reloads. A filter input narrows the tree live.
- **Breadcrumb** (only on detail pages such as the frame log and the per-job comments page): a small "Home > Jobs > ..." trail above the content lets you click back to the jobs index or to any parent in the path. Long labels truncate with an ellipsis and the full text is recoverable by hovering over the segment.
- **Bottom status bar** (IDE-style, always visible): 24-pixel-tall fixed bar at the bottom of the viewport. Three metrics with tooltips:
  - **Gateway**: a colored dot plus `Online` / `Offline` plus the last round-trip latency. Polled every 10 seconds; the bar's surface turns red whenever the REST gateway is unreachable.
  - **Last refresh**: a live "just now" / "Ns ago" timer that updates every time the jobs table re-fetches.
  - **Version**: the CueWeb build version (`v<x.y.z>`) baked in at build time.
- **Jobs Dashboard**: Central paginated table populated with OpenCue jobs (below the header).

### Navigation menus

The left sidebar and the header menus give you the same set of groups. Use the sidebar's accordion sections to jump between pages, and collapse it to an icon-only rail when you want more room for the tables.

![CueWeb left sidebar](/assets/images/cueweb/cueweb_left_side_menu.png)


The **Cuetopia** menu opens Monitor Jobs.

![Cuetopia menu](/assets/images/cueweb/cueweb_cuetopia_monitor_jobs_menu.png)


The **Cuebot Facility** menu lets you switch the active facility.

![Cuebot Facility menu](/assets/images/cueweb/cueweb_cuebot_facility_menu.png)


The **CueCommander** menu lists the farm-administration pages.

![CueCommander menu](/assets/images/cueweb/cueweb_cuecommander_menu_options.png)


The **File** menu holds the *Disable Job Interaction* safety toggle.

![File menu with Disable Job Interaction](/assets/images/cueweb/cueweb_file_disable_job_interaction_menu.png)


When the toggle is on, a read-only banner appears under the header and destructive actions are disabled until you click **Re-enable**.

![Read-only banner shown when job interaction is disabled](/assets/images/cueweb/cueweb_file_disable_job_interaction_enabled.png)


The **Other** menu collects the Attributes panel toggle, the shortcuts overlay, and the shortcut-toast preference.

![Other menu](/assets/images/cueweb/cueweb_other_menu_options.png)


The **Help** menu provides a search box that finds commands across every menu, plus links to the online guide and feedback forms.

![Help menu with search](/assets/images/cueweb/cueweb_help_menu.png)


The bottom status bar shows the gateway connection, the last refresh time, and the build version.

![Bottom status bar indicators](/assets/images/cueweb/cueweb_status_indicators.png)


---

## Dashboard

The **Dashboard** is a dedicated statistics page, separate from the Jobs table below. It summarizes farm activity at a glance.

![CueWeb Dashboard](/assets/images/cueweb/cueweb_dashboard.png)


Open it from the **Dashboard** entry in the navigation.

![Dashboard menu entry](/assets/images/cueweb/cueweb_dashboard_menu.png)


---

## Jobs Dashboard

The Jobs Dashboard is the main interface for monitoring and managing rendering jobs.

### Dashboard Layout

The dashboard consists of:

- **Filter Bar**: Show selection, status filters, and search
- **Jobs Table**: Sortable table with job information
- **Action Buttons**: Job control operations
- **Status Indicators**: Visual job state representation

### Job Information Columns

The Jobs table ships every CueGUI-parity column visible by default. You can hide / show any of them or reorder them left/right via the **Columns** dropdown (see [Customizing the column set](#customizing-the-column-set) below).

| Column | Description |
|--------|-------------|
| **Select** | Checkbox for multi-job selection. Anchored at the leftmost position - column reorder skips over it. |
| **Name** | Job identifier with show-shot-user and job name on separate lines. |
| **Comments** | Sticky-note icon when the job has one or more comments; empty otherwise. The column is **sortable**, so you can pull jobs with comments to the top in one click on the header. Clicking the icon itself opens the per-job Comments page in a new tab. |
| **State** | Current job state (Failing, Finished, In Progress, Dependency, Paused). |
| **Done / Total** | Succeeded frames out of total frames (e.g., "150 of 200"). |
| **Running** | Number of currently running frames. |
| **Dead** | Number of failed frames. |
| **Eaten** | Number of frames marked as completed (skipped). |
| **Wait** | Number of frames waiting to run. |
| **MaxRss** | Maximum resident set size (peak memory usage). |
| **Age** | Total time since job started (HHH:MM format). |
| **Readable Age** | Same value as Age, formatted as `2h 14m` or `3d 4h`. |
| **Launched** | Job start timestamp in human-readable format (`YYYY-MM-DD HH:MM`). Mirrors CueGUI's "Launched" column. |
| **Eligible** | Timestamp when the job became eligible to dispatch. Blank when the field is zero / unset. |
| **Finished** | Job completion timestamp. Blank while the job is still running. |
| **User Color** | Per-job color swatch. Click the swatch to open the native color picker; right-click or click the `×` to clear. Color is yours alone - saved in your browser and synced across your open tabs. |
| **Progress** | Stacked progress bar with five colored segments - green (succeeded), yellow (running), light blue (waiting), purple (depend), and red (dead). Hover the bar to display a tooltip with the exact frame count and percentage for each state. |
| **Notify** | Bell button to subscribe to a notification when the job reaches `FINISHED` (see [Job-finished notifications](#job-finished-notifications)). |

### Customizing the column set

Each of the three tables (Jobs, Layers, Frames) has its own **Columns** dropdown in the per-table toolbar (just left of the table). The dropdown contains, top to bottom:

- A pinned **Reset to Default** button that clears both column visibility and order, restoring the table to the layout shipped by CueWeb.
- One row per hideable column with three controls:
  - A checkbox to hide / show the column.
  - A `←` button to nudge the column one slot left in the table.
  - A `→` button to nudge it one slot right.

The dropdown stays open between clicks so you can chain several adjustments without reopening it.

Your visibility and ordering choices are saved in your browser per table and survive reloads, navigations, and redeployments. If you ever need to start over, click **Reset to Default**.

### Filtering the loaded rows

Each of the three tables (Jobs, Layers, Frames) also has a small **Filter ...** input next to its Columns dropdown. The filter performs a case-insensitive substring match across every visible column and narrows the rows already loaded; sorting, column visibility, column ordering and pagination all keep working over the filtered subset.

The filter snaps you back to page 1 on every keystroke so you never sit on an empty page. A small `×` button appears inside the input once you've typed something - click it to clear the filter in one go.

> **Tip:** The Filter input narrows what's *already loaded* into the table. On the Jobs page, the separate **Search jobs - Enter to load** box at the top of the page is what tells Cuebot to load new jobs.

![Filtering the rows loaded into the jobs table](/assets/images/cueweb/cueweb_cuetopia_monitor_jobs_job_data_table_filtering.png)


### Job Status Indicators

Jobs are color-coded by status:

- **Green**: Successfully completed or finished jobs (`SUCCEEDED`, `FINISHED`)
- **Yellow**: Currently running jobs with active frames (`RUNNING`)
- **Blue**: Paused jobs or jobs waiting for resources (`PAUSED`, `WAITING`)
- **Purple**: Jobs with dependencies (`DEPEND`, `DEPENDENCY`)
- **Red**: Failed or failing jobs (`DEAD`, `FAILING`)
- **Gray**: Default/other statuses

---

## Job Management Operations

### Basic Job Controls

#### Pause/Resume Jobs

1. **Single Job**: Click the `Pause`/`Unpause` button in the Actions menu
2. **Multiple Jobs**: Select jobs using checkboxes, then use the `Pause`/`Unpause` button

#### Kill Jobs

1. **Single Job**: Click the `Kill` button in the Actions menu
2. **Multiple Jobs**: Select jobs and click `Kill`

#### Monitor/Unmonitor Jobs

Jobs can be added or removed from monitoring:

1. **Add to Monitor**: Search for jobs and select them to monitor (selected jobs are green)
2. **Remove from Monitor**: Select the job and use the "Unmonitor" option
3. **Bulk Operations**: Select multiple jobs using checkboxes for batch operations

   ![Un-monitoring selected jobs (before)](/assets/images/cueweb/cueweb_cuetopia_monitor_jobs_un-monitoring_selected_jobs-before.png)

   ![Un-monitoring selected jobs (after)](/assets/images/cueweb/cueweb_cuetopia_monitor_jobs_un-monitoring_selected_jobs-after.png)

### Advanced Job Operations

#### Context Menu Actions

Right-click on a job, layer, or frame row to open a CueGUI-parity context menu. The full menu structure for each type is listed in the reference doc; common entries:

- **Job menu**: Unmonitor, **View Job Details** (tabbed detail page with Overview / Layers / Frames / Comments / Dependencies), **Copy Job Name**, Comments, Pause / Unpause, Retry / Eat Dead Frames, Kill, Set Max Retries, Auto-Eat On / Off, Drop External / Internal Dependencies.
- **Layer menu**: View Layer, **Copy Layer Name**, Kill, Eat, Retry, Retry Dead Frames.
- **Frame menu**: **Tail Log** / **View Log** (in-browser viewer), **View Log on <editor>** (external editor - see below), **Copy Log Path**, **Copy Frame Name**, Retry, Eat, Kill.

#### Tapping the actions menu on touch devices

On phones / tablets without a `contextmenu` event, every Jobs / Layers / Frames row has a small `⋮` button as its leftmost cell. Tapping it opens the same menu the desktop right-click opens. Use this on iPhone / iPad / Android to reach every action.

#### Opening the log in an external editor

The Frame menu shows an additional **View Log on \<editor\>** item when the deployment has `NEXT_PUBLIC_LOG_EDITOR_URL` configured (the sandbox `docker-compose.yml` defaults it to **VSCode**). Selecting that item launches the rqlog file in your desktop editor via a custom URL scheme - the same approach GitHub's "Open in VSCode" button uses.

Important notes:

- The log file only exists on disk once **RQD has started running the frame**. Right-clicking a WAITING / DEPEND frame produces a warning toast instead of handing a non-existent path to your editor.
- If the configured editor isn't installed (no app registered for `vscode://`, `subl://`, etc.), CueWeb shows a warning toast after a short timeout pointing you at the alternatives.
- Double-clicking the row (or choosing **View Log** / **Tail Log**) opens the in-browser Monaco log viewer instead - always available, no editor install required.

**Note**: Destructive items (Pause / Unpause / Retry / Eat / Kill) are automatically disabled when the global **Disable Job Interaction** safety toggle is on, and the context menu always stays on-screen even on small viewports (it scrolls internally if it would overflow).

   ![CueWeb with job context menu open](/assets/images/cueweb/cueweb_cuetopia_monitor_jobs_job_context_menu_open.png)

   ![Pop-up showing successful kill job message](/assets/images/cueweb/cueweb_cuetopia_monitor_jobs_job_context_menu_open_and_success_notification.png)

---

## Job Comments

CueWeb provides full per-job comments, equivalent to the **Comments** dialog in CueGUI.

### Opening the Comments page

You can reach a job's Comments page in two ways:

- **Context menu**: Right-click a job row and choose **Comments**.
- **Indicator icon**: The Jobs table has a dedicated **Comments** column (right after Name). A sticky-note icon appears there when the job has at least one comment; the column is sortable so you can pull jobs with comments to the top. Clicking the icon opens the Comments page in a new tab.

![Comments item in the job context menu](/assets/images/cueweb/cueweb_cuetopia_monitor_jobs_comments_menu.png)


The Comments page opens in a new tab.

![Job Comments page](/assets/images/cueweb/cueweb_cuetopia_monitor_jobs_comments_page.png)


Both open the job's Comments page in a new browser tab. CueWeb identifies you from your signed-in session; only the author of a comment can edit or delete it, and everyone else sees it read-only.

### Page layout

The page replicates the CueGUI Comments dialog:

| Region | Purpose                                                                                                                                                                                                                                                    |
|--------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **Comment list** | Table of existing comments showing **Subject**, **User**, and **Date**. Click a row to load it into the editor below.                                                                                                                                      |
| **Preview** | Sanitized markdown preview of the currently selected message.                                                                                                                                                                                              |
| **Edit Comment** | Subject + Message fields. Editable only when the comment's author matches the session-derived signed-in user; otherwise the form is read-only. Server-side ownership enforcement is authoritative, the client UI just mirrors what the server will accept. |
| **Action bar** | The predefined-comment dropdown on the left, then `New`, `Save changes` / `Save new comment`, and `Delete` buttons on the right.                                                                                                                           |

### Creating, editing, deleting

| Operation | How to perform it |
|-----------|-------------------|
| **Add a new comment** | Click **New** (or land on the page with no comment selected), enter a Subject and Message, then click **Save new comment**. The Subject field cannot be empty. |
| **Edit an existing comment** | Click the comment in the list. The form switches to **Save changes**. Make edits and save. Only the comment's author can edit. |
| **Delete a comment** | Select a comment and click **Delete**. A confirmation prompt appears. Only the author can delete. |

Comments support markdown in the message body. Content is sanitized before rendering, so embedded HTML or scripts are stripped.

Selecting a comment in the list loads it into the editor and shows its preview.

![Viewing a selected comment](/assets/images/cueweb/cueweb_cuetopia_monitor_jobs_comments_page_view_comment.png)

To create a comment, fill in the Subject and Message fields.

![Adding a new comment](/assets/images/cueweb/cueweb_cuetopia_monitor_jobs_comments_page_adding_comment.png)

After saving, the new comment appears in the list.

![Newly added comment in the list](/assets/images/cueweb/cueweb_cuetopia_monitor_jobs_comments_page_added_comment.png)

Deleting a comment prompts for confirmation first.

![Delete comment confirmation prompt](/assets/images/cueweb/cueweb_cuetopia_monitor_jobs_comments_page_delete_selected_comment_confirmation.png)

A notification confirms the comment was deleted.

![Comment deleted notification](/assets/images/cueweb/cueweb_cuetopia_monitor_jobs_comments_page_deleted_selected_comment_notification.png)

### Predefined comment macros

The **Use a predefined comment…** dropdown mirrors CueGUI's macro list and is stored **per browser**. Macros are not shared across users or browsers.

- **Apply a macro**: Pick its name from the dropdown. The Subject and Message are loaded into the form for editing; saving creates a new comment.
- **Add a macro**: Choose `> Add predefined comment`. A dialog prompts for Name, Subject, and Message. Names must be unique.
- **Edit a macro**: Choose `> Edit predefined comment`, then enter the macro name when prompted. The Add/Edit dialog opens with the existing values.
- **Delete a macro**: Choose `> Delete predefined comment`, then enter the macro name. Confirm to remove.

Open the **Use a predefined comment...** dropdown to apply or manage macros.

![Use a predefined comment dropdown](/assets/images/cueweb/cueweb_cuetopia_monitor_jobs_comments_page_use_a_predefined_comment.png)

Choose to add a new predefined comment.

![Add predefined comment option](/assets/images/cueweb/cueweb_cuetopia_monitor_jobs_comments_page_use_a_predefined_comment_add_predefined_comment.png)

Fill in the macro's name, subject, and message.

![Adding a predefined comment](/assets/images/cueweb/cueweb_cuetopia_monitor_jobs_comments_page_use_a_predefined_comment_adding_predefined_comment.png)

The new macro is saved to the dropdown.

![Added predefined comment](/assets/images/cueweb/cueweb_cuetopia_monitor_jobs_comments_page_use_a_predefined_comment_added_predefined_comment.png)

To change a macro, edit its values.

![Editing a predefined comment](/assets/images/cueweb/cueweb_cuetopia_monitor_jobs_comments_page_use_a_predefined_comment_editing_predefined_comment.png)

The edited macro is updated in the dropdown.

![Edited predefined comment](/assets/images/cueweb/cueweb_cuetopia_monitor_jobs_comments_page_use_a_predefined_comment_edited_predefined_comment.png)

To remove a macro, choose to delete it.

![Deleting a predefined comment](/assets/images/cueweb/cueweb_cuetopia_monitor_jobs_comments_page_use_a_predefined_comment_deleting_predefined_comment.png)

Confirm the deletion to remove the macro.

![Delete predefined comment confirmation](/assets/images/cueweb/cueweb_cuetopia_monitor_jobs_comments_page_use_a_predefined_comment_delete_predefined_comment_confirmation.png)

### Comment indicator on the jobs table

When a job has at least one comment, the Jobs table's dedicated **Comments** column (right after Name) shows a sticky-note icon for that row. The indicator is refreshed on the regular jobs-table polling cycle (every 5 seconds by default), so a freshly added comment may take one tick to surface on the table. Click the column header to sort jobs with comments to the top.

![Sticky-note comment indicator in the jobs table](/assets/images/cueweb/cueweb_cuetopia_monitor_jobs_comments_has_comments_icon.png)


---

## Job Search and Filtering

### Basic Search

1. **Show Filter**: Select specific shows from the dropdown
2. **Status Filter**: Filter by job state (Active, Paused, Completed)
3. **User Filter**: Show jobs for specific users
4. **Quick Search**: Type in the search box for name matching

### Advanced Search Features

#### Pattern Matching

- **Simple Search**: Type show name followed by hyphen and shot (e.g., "show-shot-") to trigger dropdown suggestions
- **Wildcard Search**: Use `*` for any characters (e.g., "test*job")
- **Regex Search**: Prefix with `!` for regex patterns (e.g., "!.*character-name.*")
- **Tooltip Guidance**: Tooltips are provided to guide search functionality

### Search Results

- **Dropdown Suggestions**: Shows matching jobs as you type with optimized loading using virtualization and web workers
- **Add to Monitor**: Click to add jobs to your monitoring dashboard
- **Green Indicators**: Jobs already in your monitor list are highlighted in green
- **Multiple Job Selection**: Add or remove multiple jobs directly from search results

   ![Job search functionality](/assets/images/cueweb/cueweb_cuetopia_monitor_jobs_job_search_functionality.png)

Type into the **Search jobs** box to find jobs to load.

![Searching for jobs to load](/assets/images/cueweb/cueweb_cuetopia_monitor_jobs_search_jobs.png)


Pick matching jobs from the dropdown suggestions to add them to your monitor list.

![Picking jobs from the search dropdown](/assets/images/cueweb/cueweb_cuetopia_monitor_jobs_search_jobs_pick_from_list.png)


---

## Frame and Layer Management

### Viewing Job Details

1. **Click a row** in the Jobs table. The inline **Layers** and **Frames** panels appear stacked below the Jobs grid (CueGUI Monitor Jobs + Monitor Job Details parity).

   ![Pop-up window layers and frames](/assets/images/cueweb/cueweb_cuetopia_monitor_jobs_layersframes.png)


2. **Click a layer** in the Layers panel to:
   - Narrow the Frames panel to that layer (the Frames title shows `X of Y`).
   - Push the layer's attributes into the docked Attributes panel.
   - Clicking the same layer again clears the filter and re-selects the job in Attributes.

3. **Double-click a frame** in the Frames panel to open the log viewer for that frame.

Both inline panels refresh every 5 seconds while a job is selected; switching to a different job clears the panels and reloads.

#### Job Details page

For a fuller view, right-click a job row and choose **View Job Details** to open a tabbed detail page.

![View Job Details menu item](/assets/images/cueweb/cueweb_cuetopia_monitor_jobs_view_job_details_menu.png)


The **Overview** tab summarizes the job's status and statistics.

![Job Details Overview tab](/assets/images/cueweb/cueweb_cuetopia_monitor_jobs_view_job_details_page_overview.png)


The **Layers** tab lists every layer in the job.

![Job Details Layers tab](/assets/images/cueweb/cueweb_cuetopia_monitor_jobs_view_job_details_page_layers.png)


The **Frames** tab lists the job's frames.

![Job Details Frames tab](/assets/images/cueweb/cueweb_cuetopia_monitor_jobs_view_job_details_page_frames.png)


The **Comments** tab shows the job's comments.

![Job Details Comments tab](/assets/images/cueweb/cueweb_cuetopia_monitor_jobs_view_job_details_page_comments.png)


The **Dependencies** tab shows the job's dependency relationships.

![Job Details Dependencies tab](/assets/images/cueweb/cueweb_cuetopia_monitor_jobs_view_job_details_page_dependencies.png)


2. **Click a layer** in the Layers panel to:
   - Narrow the Frames panel to that layer (the Frames title shows `X of Y`).
   - Push the layer's attributes into the docked Attributes panel.
   - Clicking the same layer again clears the filter and re-selects the job in Attributes.

3. **Double-click a frame** in the Frames panel to open the log viewer for that frame.

Both inline panels refresh every 5 seconds while a job is selected; switching to a different job clears the panels and reloads.

### Layer Operations

#### Layer Information Columns

| Column | Description |
|--------|-------------|
| **Dispatch Order** | Processing order for the layer |
| **Name** | Layer identifier/name |
| **Services** | Associated render services |
| **Limits** | Resource limits applied |
| **Range** | Frame range (start-end frames) |
| **Cores** | Minimum CPU cores required (minCores) |
| **Memory** | Minimum RAM required |
| **Gpus** | Minimum GPU count required |
| **Gpu Memory** | Minimum GPU memory required |
| **MaxRss** | Maximum resident set size (memory usage) |
| **Total** | Total number of frames |
| **Done** | Successfully completed frames (succeeded) |
| **Run** | Currently running frames |
| **Depend** | Frames waiting on dependencies |
| **Wait** | Frames waiting to run |
| **Eaten** | Skipped/marked complete frames |
| **Dead** | Failed frames |
| **Avg** | Average frame render time (HH:MM:SS) |
| **Tags** | Associated tags/labels |
| **Progress** | Stacked progress bar with the same five-state palette as the Jobs progress bar (green / yellow / light blue / purple / red), with a hover tooltip showing per-state counts and percentages. |
| **Timeout** | Frame timeout duration (HHH:MM) |
| **Timeout LLU** | Timeout for last layer update (HHH:MM) |
| **Eligible** | Timestamp when the layer became eligible to dispatch. |

#### Layer Actions

- **Kill**: Kill/stop all frames in the layer
- **Eat**: Mark layer as completed (skip)
- **Retry**: Restart all frames in the layer
- **Retry Dead Frames**: Restart only failed frames

   ![CueWeb with layer context menu open](/assets/images/cueweb/cueweb_cuetopia_monitor_jobs_layer_context_menu_open.png)

   ![Pop-up showing successful retry layer message](/assets/images/cueweb/cueweb_cuetopia_monitor_jobs_layer_context_menu_open_and_success_notification.png)

### Frame Operations

#### Frame State Filter Chips

Above the frames table, CueWeb renders one filter chip per supported frame state - `WAITING`, `RUNNING`, `SUCCEEDED`, `DEAD`, `EATEN`, `DEPEND` - each annotated with the current count of frames in that state.

- **Toggle**: Click a chip to add or remove its state from the filter. Selected chips switch to a solid (filled) style.
- **OR semantics**: When multiple chips are selected, frames matching **any** of the selected states are shown.
- **No selection**: When no chip is selected, every frame is displayed.
- **URL-mirrored**: Selected states are written to the `frameStates` query parameter (e.g., `?frameStates=WAITING,DEAD`), so a filtered view can be bookmarked or shared. Whitespace and duplicates in the URL are tolerated.
- **Pagination reset**: Toggling a chip resets the table to page 1 so the filtered results are immediately visible. Background data refreshes preserve the current page.
- **Counts**: Counts shown on each chip always reflect the full unfiltered data set, so you can see how many frames each state has even after applying a filter.

#### Frame Information Columns

| Column | Description |
|--------|-------------|
| **Order** | Dispatch order for frame processing |
| **Frame** | Frame number identifier |
| **Layer** | Layer name the frame belongs to |
| **Status** | Current frame state (RUNNING, SUCCEEDED, DEAD, etc.) |
| **Cores** | Number of CPU cores assigned to the frame |
| **GPUs** | Number of GPUs assigned to the frame |
| **Host** | Host machine where the frame is/was processed |
| **Retries** | Number of retry attempts for this frame |
| **CheckP** | Checkpoint count for the frame |
| **Runtime** | Frame execution time (HH:MM:SS format) |
| **LLU** | Elapsed time since the frame's log was last updated (HH:MM:SS). Only populated for `RUNNING` frames - blank for everything else, matching CueGUI. |
| **Memory (RSS)** | Resident-set memory usage (used memory for running, max RSS for completed). |
| **Memory (PSS)** | Proportional-set-size memory usage (used PSS for running, max PSS for completed). |
| **GPU Memory** | GPU memory usage (used for running, max for completed). |
| **Remain** | CueGUI's ETA estimate. Hidden by default; the value is a placeholder (an em-dash) until the underlying predictor is wired into CueWeb. |
| **Start Time** | Frame start timestamp in human-readable format. |
| **Stop Time** | Frame completion timestamp (if finished). |
| **Eligible Time** | Timestamp when the frame became eligible to dispatch. |
| **Submission Time** | Timestamp when the frame was first submitted. |
| **Last Line** | Last line of the frame log. Placeholder (an em-dash) until the per-frame log-tail fetch is wired in. |

#### Frame Status Colors

Frames are color-coded by status:
- **Green**: Successfully completed frames (`SUCCEEDED`)
- **Yellow**: Currently running frames (`RUNNING`)
- **Red**: Failed/dead frames (`DEAD`)
- **Blue**: Waiting frames (`WAITING`)
- **Gray**: Default/other statuses

#### Frame Actions

1. **Right-click on frame** for context menu:
   - **Retry**: Restart failed frame
   - **Eat**: Mark frame as completed (skip)
   - **Kill**: Stop running frame

   ![CueWeb with frame context menu open](/assets/images/cueweb/cueweb_cuetopia_monitor_jobs_frame_context_menu_open.png)

   ![Pop-up showing successful eat frame message](/assets/images/cueweb/cueweb_cuetopia_monitor_jobs_frame_context_menu_open_and_success_notification.png)

#### Frame Log Viewer

1. **View Log**: Click on the link in the frame line to open the logs
2. **Log Selection**: Choose from available log versions
3. **Auto-refresh**: Automatically update running frame logs

   ![Frame information and logs visualization](/assets/images/cueweb/cueweb_cuetopia_monitor_jobs_frame.png)


---

## Attributes panel

The Attributes panel is a docked drawer that shows a collapsible key/value tree for the currently-selected entity. Toggle it from the **Other** menu, then click a row in the jobs table to populate it.

Selecting a job shows that job's attributes.

![Attributes panel for a selected job](/assets/images/cueweb/cueweb_other_menu_attributes_job.png)


Selecting a layer shows that layer's attributes.

![Attributes panel for a selected layer](/assets/images/cueweb/cueweb_other_menu_attributes_layer.png)


The title bar's position picker lets you dock the panel on any edge of the viewport, and your choice persists across reloads.

Docked on the right (the default).

![Attributes panel docked on the right](/assets/images/cueweb/cueweb_other_menu_attributes_dock_right.png)


Docked on the bottom.

![Attributes panel docked on the bottom](/assets/images/cueweb/cueweb_other_menu_attributes_dock_bottom.png)


Docked on the left.

![Attributes panel docked on the left](/assets/images/cueweb/cueweb_other_menu_attributes_dock_left.png)


Docked on the top.

![Attributes panel docked on the top](/assets/images/cueweb/cueweb_other_menu_attributes_dock_top.png)


---

## Table Customization

### Column Management

1. **Show/Hide Columns**: Click the columns button to toggle visibility

   ![Column visibility dropdown](/assets/images/cueweb/cueweb_cuetopia_monitor_jobs_column%20_visibility_dropdown.png)

2. **Sort Data**: Click column headers to sort (ascending/descending)
3. **Resize Columns**: Drag column borders to adjust width

---

## Real-time Updates and Monitoring

### Auto-refresh Settings

CueWeb provides automatic real-time updates:

1. **Fixed Refresh Interval**: All tables automatically update every 5 seconds
2. **All Tables**: Jobs, layers, and frames tables are auto-reloaded at regular intervals to display the latest data
3. **Background Updates**: Continue updates when tab is not active
4. **Performance Optimization**: Loading animations and virtualization optimize performance on slow connections

### Job-finished notifications

Each row in the jobs table has a bell button (the **Notify** column) that lets you subscribe to a browser notification when the job reaches `FINISHED`. The bell has three visual states:

- **Outline bell**: not subscribed &rarr; click to subscribe
- **Filled bell**: subscribed, waiting for `FINISHED` &rarr; click to cancel
- **Filled bell + green dot**: notification has fired &rarr; click to clear

Behavior:

- The bell is disabled (faded, with tooltip) on jobs that are already `FINISHED` when first viewed; there is nothing to notify on.
- The subscription always succeeds. After saving it, the browser's notification permission is requested as an optional upgrade for system-level popups. A toast tells you what you got:
  - **granted** &mdash; in-app toast plus a desktop popup when the job finishes.
  - **denied** &mdash; in-app toast only. To also receive desktop popups, enable notifications for the CueWeb origin in your browser site settings.
  - **default** &mdash; you dismissed the prompt without choosing. In-app toast only, same as `denied`.
- A background poller checks each subscribed job every 15 seconds. When a job reaches `FINISHED` an in-app `toast.success("Job finished: <jobName>")` always fires; a desktop `Notification` popup is layered on top when the permission was granted at fire-time. The bell switches to filled with a green dot, and the entry is marked as notified.
- When several CueWeb tabs are open for the same job, only one of them shows the notification, so you see exactly one notification per finished job per browser profile.
- Subscriptions are saved in your browser and survive page reloads. They are scoped to the browser and profile; clearing site data removes them.
- If a subscribed job is deleted from Cuebot (the API returns null), the subscription is removed automatically on the next poll.

---

## Keyboard Shortcuts

CueWeb registers a small set of global keyboard shortcuts. Single-letter keys are ignored while typing into a text field, and modifier-key combos (Ctrl / Cmd / Alt) are passed through to the browser, so they will not collide with native shortcuts such as Ctrl+R.

| Key | Action | Where it works |
|-----|--------|----------------|
| `?` | Open the keyboard-shortcuts overlay | Anywhere |
| `Esc` | Close the overlay | Inside the overlay |
| `/` | Focus the jobs search box | On the jobs page |
| `r` | Refresh the jobs table | On the jobs page |
| `t` | Toggle the light / dark theme | Anywhere |

### Opening shortcuts from the menu

The same overlay is reachable from the menu if you prefer mouse navigation:

- Header **Other ▸ Show Shortcuts**
- Sidebar **Other ▸ Show Shortcuts** (in both expanded and collapsed sidebar modes)

![Keyboard shortcuts overlay](/assets/images/cueweb/cueweb_other_menu_show_shortcuts.png)


### Toast on shortcut

A small toast appears every time you trigger a shortcut so you know it registered (e.g. pressing `r` toasts `Shortcut: r → Refresh table`). The toast can be turned off via **Other ▸ Notify on Shortcut** in the header or sidebar. The preference persists across reloads and across browser tabs.

---

## Submitting Jobs (CueSubmit)

CueWeb has a browser-based equivalent of the standalone CueSubmit CLI tool. Open it from the **CueSubmit > Submit Job** menu in the header (or from the matching entry in the sidebar / mobile drawer) to reach the `/cuesubmit` form.

### Filling in a job

1. **Job Info** at the top of the page:
   - **Job Name** - free text. The actual cuebot job name will be `<show>-<shot>-<user>_<jobname>`.
   - **Show** - pick one from the dropdown (populated from the shows registered in cuebot).
   - **Shot** - free text. Letters, numbers, `.`, `-`, `_`.
   - **Facility** - leave as `[Default]` to use the sandbox's local facility, or pick another if your deployment runs multiple.
   - **Username** - pre-filled with your signed-in identity when CueWeb is deployed with authentication. Tick the **Edit** checkbox next to the field to submit as someone else; unticking snaps it back to you.

2. **Layer Info** describes the first (and possibly only) layer:
   - **Layer Name** - free text.
   - **Frame Spec** - the frames to render. `1-10` means frames 1 through 10. `1-100x2` means every other frame. Click the **?** badge next to the field for more examples.
   - **Chunk Size** - how many frames cuebot bundles into one dispatched frame.
   - **Memory** - per-frame request, e.g. `256m`, `1g`. Leave empty to inherit the service default.
   - **Job Type** - Shell, Maya, Nuke, or Blender. The panel below changes to ask for the inputs that type needs (Shell asks for a command, Maya asks for a scene file + camera, etc.).
   - **Services** - pick the cuebot service that should run this layer.
   - **Limits** - optional cuebot limits to apply.
   - **Override Cores** - tick to pin the per-frame core count (otherwise the service default is used).
   - **Dependency Type** - for second-and-later layers only: `Layer` means the whole previous layer must finish first; `Frame` means just the matching frame number.

3. **Per-type options panel** is the white box below Layer Info:
   - **Shell** asks for the command to run. Use `#IFRAME#` for the current frame number and other cuebot tokens (click the **?** for the cheatsheet).
   - **Maya / Nuke / Blender** ask for a scene file path plus the type-specific inputs (Maya camera, Nuke write nodes, Blender output path / format).

4. **Final command** is a read-only preview of exactly what cuebot will execute. It updates per-keystroke as you fill the form.

5. **Submission Details** is the layers table at the bottom. Use the `+` button to add a second layer (or third, etc.); use `−` to remove the selected layer; the `↑ / ↓` buttons reorder. Clicking a row loads it back into the Layer Info section above for editing.

6. Click **Submit**. CueWeb sends the job to cuebot and redirects you to its detail page so you can watch the frames cycle through WAITING -> RUNNING -> SUCCEEDED.

### Convenience features

- **Autocomplete history**: Job Name, Shot, and Layer Name remember everything you've submitted (per browser). Start typing to see previous values. Mirrors the on-disk cache the standalone CueSubmit keeps.
- **Auto-saved draft**: the form saves to your browser on every change and restores on next page load, so an accidental refresh never wipes a 10-layer setup. Submitting or Resetting clears the draft.
- **Reset button**: between Cancel and Submit. Opens a themed confirmation dialog before clearing every field; autocomplete history is kept.
- **View in Monitor Jobs**: after the page redirects to the new job's detail view, the **View in Monitor Jobs** button in its header opens Cuetopia with the job auto-searched, so you can act on it alongside the rest of your monitored set.

### Sandbox defaults

The form ships with defaults tuned for the OpenCue sandbox so a fresh `sleep 5` test job runs end-to-end without further setup: Memory `256m` (the seeded default service requires 3.2 GB which the sandbox RQD usually can't satisfy), Facility `local` (matches the sandbox RQD's allocation), and a per-user UID that cuebot will accept. Adjust Memory and Facility for production deployments.

---

## Mobile and Responsive Usage

CueWeb works on phone-sized viewports, not just desktops.

### Hamburger nav drawer

On phones the desktop sidebar is replaced by a **hamburger** button on the LEFT of the global header. Tap it to open a side drawer containing every group: **Dashboard**, **File**, **Cuebot Facility**, **Cuetopia**, **CueCommander**, **Other** (Attributes / Show Shortcuts / Notify on Shortcut), **Help**. The drawer auto-closes when you tap a navigation link.

### Row actions via a tap

Touch devices don't have a right-click. Every Jobs / Layers / Frames row therefore has a small `⋮` Actions button as its leftmost cell. Tapping it opens the same context menu that desktop users get from right-clicking the row - Copy Job / Layer / Frame Name, View Log, Pause / Kill / Eat actions, etc.

### Horizontally swipeable tables

The Jobs / Layers / Frames grids carry 15-25 columns each. Phones can't fit all of those at once, so the tables can be swiped left / right to reach off-screen columns. Use the **Columns** dropdown to hide columns you don't need on small screens (the choice is remembered for next time).

### Clickable shortcuts overlay

The keyboard-shortcuts overlay (**Other ▸ Show Shortcuts** in the hamburger drawer) makes each of its key badges tappable on phones, so you can trigger:

- `/` -> focus the Jobs search box.
- `r` -> refresh the Jobs table.
- `t` -> toggle light / dark theme.
- `Esc` -> close the overlay.

without needing a physical keyboard.

### LAN access

CueWeb works correctly when you load it from a LAN IP (e.g. `http://XXX.XXX.XXX.XXX:3000` from a phone reaching your sandbox) - not just from `localhost`. API requests follow whichever host served the page, so the same image works from any address without rebuilding.

Two caveats on plain-HTTP LAN access:

- **Clipboard**: the modern browser clipboard API is restricted to secure contexts (HTTPS / `localhost`). CueWeb automatically falls back to a legacy copy path outside secure contexts, so **Copy Job Name** / **Copy Layer Name** / **Copy Frame Name** / **Copy Log Path** still work on LAN HTTP.
- **Desktop notification popups** (the optional upgrade for **Subscribe to Job**) require a secure context. On LAN HTTP, the subscription itself still works and the **in-app toast** still fires when the job finishes; you just don't get the OS-level notification banner. Serve the app over HTTPS (self-signed cert is enough for LAN testing) to enable that path.

---

## Troubleshooting and Support

### Common Issues

#### Connection Problems

**Symptoms**: "Cannot connect to OpenCue" error
**Solutions**:
1. Check if REST Gateway is running
2. Verify network connectivity
3. Check browser console for detailed errors
4. Confirm JWT token is valid

#### Performance Issues

**Symptoms**: Slow loading, high memory usage
**Solutions**:
1. Reduce auto-refresh frequency
2. Limit number of monitored jobs
3. Use status filters to reduce data load
4. Clear browser cache and cookies

#### Authentication Problems

**Symptoms**: Login loops, permission errors
**Solutions**:
1. Clear browser cookies and local storage
2. Check OAuth configuration
3. Verify user permissions
4. Contact administrator for account issues

---

## Advanced Features

### API Integration

For advanced users and developers:

- **REST API Access**: Direct API calls using JWT tokens
- **Custom Scripts**: Automate operations with curl or scripts
- **Integration Tools**: Connect with external monitoring systems
- **Webhook Support**: Real-time notifications to external services

For advanced configuration and development, see the [CueWeb Developer Guide](/docs/developer-guide/cueweb-development).
