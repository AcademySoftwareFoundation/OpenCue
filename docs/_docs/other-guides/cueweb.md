---
title: "OpenCueWeb System"
layout: default
parent: Other Guides
nav_order: 57
linkTitle: "OpenCueWeb system"
date: 2025-02-04
description: >
   OpenCueWeb system: First web-based release of CueGUI with many features from Cuetopia
---

# OpenCueWeb

### A web-based CueGUI alternative with job filtering, inspection, and interactive controls

---

This guide provides an introduction to the OpenCueWeb system, the web-based version of CueGUI.

## Introduction

[OpenCue](https://www.opencue.io/) has facilitated efficient management of rendering jobs through its application, CueGUI, which includes Cuetopia and CueCommander. Previously, OpenCue's capabilities were somewhat restricted as it was primarily limited to desktops/workstations running Qt-based applications. Because of that, the OpenCueWeb system was created. OpenCueWeb is a transformative, web-based application that extends access across multiple platforms, ensuring users can manage their rendering tasks from virtually anywhere.

## A seamless transition to web accessibility 

OpenCueWeb replicates the core functionality of [CueGUI](https://www.opencue.io/docs/reference/cuegui-app/) (Cuetopia and Cuecommander) in a web-accessible format, enhancing usability while maintaining the familiar interface that users appreciate. This adaptation supports essential operations such as:

1. **Persistent global header (every authenticated route):**
   - OpenCue logo (theme-aware: black in light mode, white in dark mode) + the **OpenCueWeb** wordmark.
   - Six dropdown menus mirroring the CueGUI menu bar: **File** (Disable Job Interaction), **Cuebot Facility**, **Cuetopia** (Monitor Jobs), **CueCommander** (Allocations, Limits, Monitor Cue, Monitor Hosts, Redirect, Services, Shows, Stuck Frame, Subscription Graphs, Subscriptions), **Other** (Attributes, Immersive (full-screen), Split view, Show Shortcuts, Notify on Shortcut), and **Help** (search box across every menu command, plus Online User Guide / Make a Suggestion / Report a Bug / About OpenCueWeb). Routes that are not yet implemented 404 gracefully.
   - Theme toggle (light/dark).
   - Always-visible **Sign out** button that calls NextAuth's `signOut()` and routes to `/login` - the `/login` page itself shows either the **OpenCueWeb Home** button (when `NEXT_PUBLIC_AUTH_PROVIDER` is empty) or the configured provider buttons.
2. **Collapsible left sidebar (every authenticated route):**
   - Same six groups as the header (**File**, **Cuebot Facility**, **Cuetopia**, **CueCommander**, **Other**, **Help**), organized as accordion sections; the group containing the active route auto-expands.
   - One click on the **Collapse** button shrinks the sidebar to an icon-only rail; overall and per-group state persist across reloads.
3. **Disable Job Interaction (read-only safety mode):**
   - File -> Disable Job Interaction (header or sidebar) toggles a read-only safety mode that is saved in your browser and synced across your open tabs.
   - When on, an amber **Read-only mode** banner appears under the header (with a *Re-enable* button) and every destructive action (Eat / Retry / Pause / Unpause / Kill - both in the jobs toolbar and in the right-click menus on job/layer/frame rows) becomes inert.
4. **Attributes panel (Other -> Attributes):**
   - Docked drawer showing a collapsible key/value tree for the currently-selected entity (click a row in the jobs table to populate it).
   - Position picker in the title bar docks the panel on the **right** (default), **bottom**, **left**, or **top**. A filter input narrows the tree live.
5. **Bottom status bar (IDE-style):**
   - Fixed 24-pixel bar at the bottom of every authenticated route.
   - **Gateway** (left): a dot + `Online` / `Offline` + the last round-trip latency, refreshed every few seconds. The whole bar turns red when the gateway is unreachable.
   - **Last refresh** (center): a live "Ns ago" timer that updates whenever the jobs table refreshes.
   - **Version** (right): the OpenCueWeb build version.
6. **Breadcrumb navigation on detail views:**
   - Above the frame log page and the per-job comments page, a "Home > Jobs > ..." trail lets you click back to the jobs index or any parent in the path.
   - Long segment labels are truncated, with the full text shown in a tooltip on hover.
   - The last segment is the current page; the earlier segments are clickable links back to the index or any parent.
7. **Secure user authentication:**
   - Authentication through Github, Google, [Okta](https://www.okta.com/), LDAP, Apple, GitLab, Amazon, Microsoft Azure, LinkedIn, Atlassian, Auth0, etc. Other providers and login options can be easily configured and enabled in the OpenCueWeb. LDAP authentication is particularly useful for intranet deployments using company directory credentials. See [NextAuth.js](https://next-auth.js.org/) authentication using email, credentials and providers: https://next-auth.js.org/providers/
8. **Browser-based job submission (CueSubmit CLI parity):**
   - A dedicated `/cuesubmit` route reachable from the **CueSubmit** top-level dropdown in the header, the matching **CueSubmit > Submit Job** group in the left sidebar (and the mobile nav drawer) mirrors the standalone CueSubmit CLI tool with Job Info / Layer Info / per-type option panels for Shell / Maya / Nuke / Blender, a live read-only Final command preview, and a multi-layer Submission Details table with `+ / - / down / up` controls.
   - Browser-only improvements over the CLI: per-keystroke command preview, per-field autocomplete history (Job Name / Shot / Layer Name) saved in your browser, draft auto-save so an accidental refresh doesn't wipe a multi-layer setup, themed `?` help popovers for frame-spec patterns and cuebot tokens, themed confirmation dialogs, and a **Reset** button next to Cancel and Submit.
   - The Username field auto-populates from the signed-in user when authentication is enabled and stays read-only until an explicit **Edit** override toggle is ticked; sandbox mode (no auth) leaves it always editable.
   - On successful submit the page redirects to the tabbed `/jobs/<name>` detail view; that view's header now has a **View in Monitor Jobs** deep-link button that opens Cuetopia with the job auto-searched.
   - Defaults tuned for the OpenCue sandbox so a `sleep 5` test job runs end-to-end out of the box: Memory `256m`, Facility `local`, and a deterministic per-user UID so cuebot never rejects the launch as root.
9. **Customizable job / layer / frame tables (CueGUI parity):**
   - Each of the three data tables (Jobs, Layers, Frames) has a **Columns** dropdown with three controls per column: a checkbox to hide/show, and **`←` / `→`** arrows to nudge the column left / right within the user-reorderable subset. Non-hideable system columns (the row-select checkbox) stay anchored.
   - A **Reset to Default** button pinned at the top of the dropdown clears both visibility AND order in one click.
   - Both states are saved per table in your browser and persist across reloads.
   - CueGUI-parity column sets:
     - **Jobs**: Name, **Comments** (sortable sticky-note column - pull jobs with comments to the top in one click), State, Done / Total, Running, Dead, Eaten, Wait, MaxRss, Age, Readable Age, **Launched**, **Eligible**, **Finished**, **User Color** (per-job color swatch saved in your browser and synced across your open tabs), Progress, Notify.
     - **Layers**: Dispatch Order, Name, Services, Limits, Range, Cores, Memory, Gpus, Gpu Memory, MaxRss, Total, Done, Run, Depend, Wait, Eaten, Dead, Avg, Tags, **Progress** (stacked animated bar, same palette as the Jobs progress bar), Timeout, Timeout LLU, **Eligible**.
     - **Frames**: Order, Frame, Layer, Status, Cores, GPUs, Host, Retries, CheckP, Runtime, **LLU** (only populated for `RUNNING` frames - blank for WAITING / DEPEND / SUCCEEDED / DEAD, matching CueGUI), **Memory (RSS)**, **Memory (PSS)**, GPU Memory, **Remain** (placeholder until the ETA predictor is wired in), Start Time, Stop Time, **Eligible Time**, **Submission Time**, **Last Line** (placeholder until the per-frame log-tail fetch is wired in).
   - Each table also has a small client-side substring **Filter** input next to its Columns dropdown that narrows the rows already loaded; resets to page 1 on every keystroke and keeps sorting, visibility, reordering and pagination working over the filtered subset.
10. **Flexible monitoring controls:**
   - Easily un-monitor jobs across all statuses.
11. **Detailed job inspection (inline Layers + Frames panel):**
   - Clicking a row in the jobs table reveals the associated **Layers** and **Frames** tables stacked below the jobs grid (CueGUI Monitor Jobs + Monitor Job Details parity).
   - Clicking a layer row narrows the frames panel to that layer and pushes the layer's attributes into the docked Attributes panel; clicking the same layer again clears the filter and re-selects the job in Attributes.
   - Double-clicking any frame row opens the log viewer for that frame.
   - Inline panels refresh every 5 seconds.
12. **Frame navigation and logs access:**
   - Navigate frames using hyperlinks that lead to dedicated pages for frame data and logs.
13. **Advanced job search functionality:** 
   - Search for jobs by show name with dropdown suggestions for matching entries.
   - Search functionality requires `show-shot-` as the prefix to reduce the number of results returned.
14. **Dark mode toggle for user preference:** 
   - Switch between light and dark modes according to user preference.
15. **Enhanced search functionality:**
   - Users can enable regex searches by appending '!' to their queries, with tooltips provided for guidance.
   - Optimized loading times, along with loading animations for a better user experience.
   - Users can add or remove multiple jobs directly from the search results, with existing jobs highlighted in green.
16. **Enhanced security using Opencue API:**
   - OpenCueWeb authorizes its requests to the OpenCue REST API with signed security tokens.
17. **OpenCueWeb actions and context menu (CueGUI parity):**
   - Right-clicking any row in the Jobs, Layers, or Frames tables opens a context menu that mirrors the CueGUI Monitor Jobs / Monitor Job Details menus.
   - On touch devices, every row has a small **`⋮` Actions** button as its leftmost cell. Tapping it opens the same menu the desktop right-click opens.
   - **Job actions** include: Unmonitor, View Job, **View Job Details** (opens the tabbed `/jobs/<jobName>` page with Overview / Layers / Frames / Comments / Dependencies), **Copy Job Name**, Email Artist, Request Cores, Subscribe to Job, Comments, **View Dependencies...** (themed dialog rendering the job's depends), **Dependency Wizard...** (multi-step dialog covering every CueGUI `depend.DependType`, multi-select on every picker, cross-product fan-out on Done), **Drop External / Internal Dependencies** (one click, table auto-refreshes), Set / Clear User Color, **Set Priority...** (themed 1-100 slider + number input), Set Max Retries, Reorder / Stagger Frames, **Pause / Unpause** (single toggle - the label and icon flip with the job's paused state, and the entry is grayed out for Finished jobs), Auto-Eat On / Off, Retry / Eat Dead Frames, Unbook, Kill, Show Progress Bar.

   ![View Dependencies dialog](/assets/images/cueweb/cueweb_cuetopia_monitor_jobs_view_dependencies_window.png)

   ![Dependency Wizard - type picker](/assets/images/cueweb/cueweb_cuetopia_monitor_jobs_dependency_wizard_menu_select_dependency_type_job_on_job_step1_select_type.png)
   - **Layer actions** include: View Layer, **Copy Layer Name**, dependency items, Reorder / Stagger Frames, Properties, Kill, Eat, Retry, Retry Dead Frames.
   - **Frame actions** include: **Tail Log / View Log** (in-browser viewer), **View Log on \<editor\>** (external editor - see item 23), **Copy Log Path**, **Copy Frame Name**, View Host, dependency items (View / Drop / **Dependency Wizard**), **Mark as waiting**, Filter Selected Layers, Reorder, **Preview All** (external image viewer; command configurable via `NEXT_PUBLIC_PREVIEW_COMMAND` / `NEXT_PUBLIC_PREVIEW_URL`), Retry, Eat, Kill, **Mark done** / Eat and Mark done, View Processes. You can also drag (or shift-click) to select a contiguous **frame range** and Retry / Eat / Kill it at once. The job menu's **Show Progress Bar** shows a configurable CueProgBar launch command (`NEXT_PUBLIC_CUEPROGBAR_COMMAND`).
   - **Frame log viewer** also offers in-log **search** (highlight + match counter, case/regex toggles), **follow/tail** mode (auto-scroll, pause-on-scroll-up, jump-to-bottom; **Tail Log** opens it following by default), absolute **line numbers**, **per-line copy**, raw-log **download**, and a **frame preview thumbnail** panel.
   - All copy actions work whether OpenCueWeb is reached at `localhost` or at a LAN IP over plain HTTP.
   - Menus scroll instead of overflowing on small viewports. Items that depend on dialogs / backend integrations not yet implemented in OpenCueWeb surface a friendly placeholder toast. Destructive items are auto-disabled when **Disable Job Interaction** is on.

18. **Auto-reloading of tables:**
   - All tables (jobs, layers, frames) are auto-reloaded at regular intervals to display the latest data.

19. **Animated progress bar on Jobs AND Layers:**
   - Both tables render a stacked bar with five colored segments (succeeded, running, waiting, depend, dead), using the same color palette.
   - Hovering the bar opens a tooltip with the exact frame count and percentage for each state.

20. **Frame state filter chips:**
   - Above the frames table, a chip is rendered for each supported state - `WAITING`, `RUNNING`, `SUCCEEDED`, `DEAD`, `EATEN`, `DEPEND` - annotated with the count of frames currently in that state.
   - Selections combine with OR semantics; the table pages back to the first page on selection change so the filtered results are immediately visible.
   - The current selection is mirrored to the `frameStates` URL query parameter (e.g. `?frameStates=WAITING,DEAD`), making filtered views bookmarkable and shareable.

21. **Per-job completion notifications (two channels):**
   - **Notify bell** (Jobs table **Notify** column): clicking the bell subscribes the *browser* to an in-app toast (and an optional desktop popup) when the job reaches `FINISHED`. Three visual states - outline (not subscribed), filled (subscribed/waiting), filled with a green dot (notification fired). The bell is disabled on rows whose job state is already `FINISHED` when first viewed. Subscriptions always succeed; the OS-level notification permission is an optional upgrade. An app-wide background poller checks each subscribed job every 15 seconds; when several tabs poll the same job concurrently only one actually fires the toast. Subscriptions are persisted in the browser, survive page reloads, sync across tabs, and self-prune when the job is deleted from Cuebot.
   - **Subscribe to Job** (right-click menu on a job row): opens a themed dialog mirroring CueGUI's `SubscribeToJobDialog`. The address you save is registered on Cuebot via the `AddSubscriber` RPC, so Cuebot **emails** the subscriber when the job finishes. Use this when you want notifications to survive closing the browser, going to a different machine, or to alert a team alias instead of yourself. Independent of the Notify bell; you can use one, the other, or both.

22. **Keyboard shortcuts overlay (+ menu access + per-shortcut toast):**
   - Press `?` anywhere to open the cheat-sheet overlay; press `Esc` to close it. The overlay lists `/` (focus jobs search), `r` (refresh table), `t` (toggle theme), and `F` / `Cmd/Ctrl+Shift+F` (toggle immersive - hide header / sidebar / status bar). Single-letter keys are ignored while typing into editable elements, and modifier-key combos (Ctrl / Cmd / Alt) are passed through to the browser - except the immersive chord `Cmd/Ctrl+Shift+F`, which is captured even from inside a search field.
   - The same overlay is reachable from **Other ▸ Show Shortcuts** in both the header and the sidebar.
   - **Notify on Shortcut** (also under Other; default ON) controls whether a toast naming the action fires every time a shortcut triggers (e.g. `Shortcut: r → Refresh table`). Flipping the toggle takes effect on the very next keypress.

23. **Job comments:**
   - Per-job comments that mirror the CueGUI **Comments** dialog: list, add, edit, and delete.
   - Reached from the **Comments** entry in the job context menu, or from a sticky-note icon in the Jobs table's dedicated **Comments** column (sortable, sits right after Name) when the job has at least one comment.
   - Messages support markdown and are sanitized before display.
   - Predefined-comment macros are stored per browser, with the same Add / Edit / Delete predefined-comment workflow as CueGUI.

24. **External editor integration (View Log on \<editor\>):**
   - Optional Frame context-menu item that launches the frame's log file directly in a desktop editor.
   - Configured at build time via the `NEXT_PUBLIC_LOG_EDITOR_URL` environment variable. The literal `{path}` is replaced with the absolute log path when the menu item is clicked.
   - The sandbox deployment ships with VSCode as the default (**View Log on VSCode**). Override with another value to target a different editor:
     - `vscode://file{path}` -> View Log on VSCode
     - `vscode-insiders://file{path}` -> View Log on VSCode Insiders
     - `subl://open?url=file://{path}` -> View Log on Sublime Text
     - `txmt://open?url=file://{path}` -> View Log on TextMate
     - `idea://open?file={path}` -> View Log on IntelliJ
     - Empty value -> the menu item is hidden entirely.
   - The menu label is derived automatically from the URL. Unrecognized schemes fall back to "View Log in external editor".
   - Web browsers can't read the user's shell `$EDITOR` variable or launch arbitrary local programs the way CueGUI does. The URL-scheme approach is the web equivalent: the same trick GitHub's "Open in VSCode" button uses.
   - If the chosen editor isn't installed on the user's machine, OpenCueWeb shows a warning toast after a short delay pointing the user at the alternatives.
   - When the frame hasn't started running yet (WAITING / DEPEND frames have no log file on disk), the menu item shows a friendly warning toast instead of handing a non-existent path to the editor.

25. **Mobile-friendly UI:**
   - Every authenticated route works on phone-sized viewports. The Jobs page stacks its filter / toolbar / table vertically on small screens instead of forcing a wide layout, and the data tables can be swiped horizontally to reach off-screen columns.
   - On phones the desktop sidebar is replaced by a hamburger button in the global header. Tapping it opens a side drawer mirroring every sidebar group: Dashboard, File, Cuebot Facility, Cuetopia, CueCommander, Other (Attributes / Immersive (full-screen) / Split view / Show Shortcuts / Notify on Shortcut), and Help. The drawer is scrollable and auto-closes when you tap a navigation link.
   - Every Jobs / Layers / Frames row has a small **`⋮` Actions** button as its leftmost cell. Tapping it opens the same context menu the desktop right-click opens (see item 16), so touch users get the full action set without a right-click event.
   - The keyboard-shortcuts overlay (item 21) is itself touch-friendly: every key badge in the list is tappable, so `/` (focus search), `r` (refresh), and `t` (toggle theme) work on phones without a physical keyboard.

26. **LAN access (OpenCueWeb usable from phones / tablets):**
   - The same image works whether the browser reaches OpenCueWeb at `localhost` on the dev machine or at a LAN IP from another device on the same network - no rebuild needed when you want to test on a phone. The build-time `NEXT_PUBLIC_URL` setting defaults to empty for this reason; only set it to an absolute URL if your deployment serves the API on a different origin than the UI.
   - Copy actions (Copy Job / Layer / Frame Name, Copy Log Path) work even when OpenCueWeb is reached over plain HTTP at a LAN IP, including on iOS Safari.

27. **Job dependency graph (Cuetopia &rarr; View Job Graph):**
   - A read-only, interactive node graph of a job's dependency tree, mirroring CueGUI's Monitor-Jobs dependency-graph dock.
   - Toggled from the checkable **Cuetopia &rarr; View Job Graph** entry (header dropdown and sidebar); the choice is persisted and synced across tabs.
   - When on, selecting a job in Monitor Jobs mounts the graph as a third panel under the inline Layers and Frames panels. It shows the focus job with its **layers** (so a job with no cross-job dependencies still renders its structure) and walks cross-job depends in both directions, color-codes nodes by kind (JOB / LAYER / FRAME), rings the focus job, and truncates long names with a full-name tooltip. Pan / zoom / fit controls are included.
   - **Double-click** a node to open that job's detail page (a single click only selects it). **Right-click a layer node** for the CueGUI Job-Graph layer menu: **Auto Layout Nodes**; **Dependencies** (View Dependencies… / Dependency Wizard… / Mark done); **Reorder Frames…**; **Stagger Frames…**; **Properties…**; **Kill / Eat / Retry / Retry Dead Frames** - the same actions as the Layers table.

28. **Monitor Cue (CueCommander &rarr; Monitor Cue):**
   - A show-grouped job tree at `/monitor-cue`, the OpenCueWeb equivalent of CueGUI's CueCommander Monitor Cue window (previously a dead sidebar link). Pick one or more shows from the **Shows** menu (All Shows / Clear / per-show, persisted) to load every job for those shows, grouped under their show and groups.
   - **Full CueGUI column set**: Comment + Auto-eat icons, Job, Run, Cores, Gpus, Wait, Depend, Total, **Booking** (a running/waiting bar with cyan min-core and red max-core markers, mirroring CueGUI's booking bar), Min, Max, Min G, Max G, Pri, ETA, MaxRss, MaxGpuMem, Age, Readable Age, and Progress. Columns sort with header arrows; a Columns dropdown (show/hide + reorder) and a **Filter jobs...** box sit at the top-right (persisted). Rows are tinted by condition: blue = paused, red = dead, yellow = high peak memory, green = waiting, purple = all-depend.
   - **Toolbar**: Eat / Retry / Pause / Unpause / Kill (with icons; Kill confirms) on the selected jobs, Refresh + Auto-refresh (5s), Expand / Collapse All, and a **Select:** name/regex box that live-selects matching jobs (plus a select-mine button). A select-all header checkbox and Shift+click range selection pick rows in bulk.
   - **Job menu** reuses the Monitor Jobs right-click menu plus Monitor-Cue-only entries: **View Job**, **Send To Group...** (reparent the job into another group of its show), the resource/priority setters (Set Min/Max Cores, Set Minimum/Maximum Cores, Set Minimum/Maximum Gpus, Set Priority), Use Local Cores, Unbook Frames..., and Set / Clear User Color. Auto-eat is a single **Enable / Disable auto eating** toggle.

29. **Monitor Hosts (CueCommander &rarr; Monitor Hosts) - full CueGUI parity:**
   - A host registry at `/hosts`, the OpenCueWeb equivalent of CueGUI's CueCommander Monitor Hosts plugin. Reached from the CueCommander menu / sidebar entry or the dashboard hosts widget's **View hosts** link.
   - **Full CueGUI column set**: Name, a Comments icon column, Load %, Swap, Physical, GPU Memory, Total Memory, Idle Memory, Temp, Temp Free, Temp Free %, Cores, Idle Cores, GPUs, Idle GPUs, GPU Mem, GPU Mem Idle, Ping, Boot Time, Hardware, Locked, ThreadMode, OS, Tags. Swap / Physical / GPU Memory / Temp render as red/green used-vs-free bars. Rows are tinted by condition: red for a non-`UP` hardware state, amber for `REBOOT_WHEN_IDLE`, yellow for an `UP` but `LOCKED` host. Column show/hide/reorder and saveable **Views** presets mirror the other tables.
   - **Filter bar**: name/regex box plus Allocation / HardwareState / LockState / OS multi-selects, with Auto-refresh / Refresh / Clear. Filtering is client-side and the active filters are mirrored in the URL so a filtered view is shareable. Auto-refreshes every 30 seconds.
   - **Host actions** via the row's right-click menu (CueGUI parity): **Comments…** (with reusable predefined-comment macros), **View Procs**, **Lock / Unlock / Take Ownership** (Take Ownership enabled only for a `NIMBY_LOCKED` host, with a confirmation dialog), **Edit Tags… / Rename Tag… / Change Allocation…**, **Reboot** (confirms - running frames are killed) **/ Reboot when idle / Delete Host**, and **Set / Clear Repair State**. Inapplicable items are greyed out by host state; the affected row updates immediately on success.
   - **Proc monitor panel** below the table: list the procs on one or more hosts (left-click a host row, choose **View Procs**, or type host names), then right-click a proc for **View Job**, **Unbook**, **Kill**, or **Unbook and Kill**. Auto-refreshes every 30 seconds.
   - **Host detail page**: click a host's name to open a per-host page with Overview, Procs, Comments, and Tags tabs. The Procs tab lists the frames running on the host (auto-refreshing every 15 seconds); clicking a proc opens that frame's log.

30. **Allocations (CueCommander &rarr; Allocations):**
   - An allocations table at `/allocations`, the OpenCueWeb equivalent of CueGUI's CueCommander Allocations window. Reached from the CueCommander menu / sidebar entry.
   - Columns mirror CueGUI: Name, Tag, a cores group (Cores, Idle, Locked, Down, Repair) and a hosts group (Hosts, Locked, Down, Repair). Numeric columns sort by their underlying value; column show/hide and the substring filter mirror the other tables. Auto-refreshes every 30 seconds.
   - Clicking an allocation's name navigates to the hosts list scoped to that allocation (`/hosts?allocation=<name>`).

31. **Shows (CueCommander &rarr; Shows):**
   - A shows registry at `/shows`, the OpenCueWeb equivalent of CueGUI's CueCommander Shows window. Reached from the CueCommander menu / sidebar entry.
   - Sortable, filterable stats table with columns Show Name, Cores Run, Frames Run, Frames Pending, and Jobs (from `GetActiveShows`), auto-refreshing every 30 seconds. Click a show name to open its detail page.
   - **Create Show** dialog: enter a unique alphanumeric name and optionally subscribe the new show to one or more allocations (checkbox + Size + Burst per allocation).
   - **Show actions** via the row's right-click menu: **Show Properties** (a four-tab dialog - Settings with default max/min cores and comment email, Booking with enable booking / enable dispatch, read-only Statistics, and Raw Show Data) and **Create Subscription...** (subscribe a show to an allocation with Size and Burst).

32. **Stuck Frames (CueCommander &rarr; Stuck Frame):**
   - A stuck-frame finder at `/stuck-frames`, the OpenCueWeb equivalent of CueGUI's CueCommander Stuck Frame window. Reached from the CueCommander menu / sidebar entry.
   - Scans every running frame across active jobs and flags the ones that look hung (the log has gone silent relative to runtime), grouped under their job. Columns: Name, Frame, Host, LLU, Runtime, % Stuck, Average, Last Line. Auto-refreshes on a timer, with **Refresh** / **Clear** controls.
   - **Detection filters** (saved per browser): % of Run Since LLU, Min LLU, % Avg Completion, Total Runtime, and Exclude Keywords. The **+** button adds a per-service filter row (catch-all "All Other Types" plus one row per render service, so e.g. Arnold can use looser thresholds than quicker services).
   - **Frame actions** via the row's right-click menu: Tail/View/View Last Log, Retry / Eat / Kill, Log Stuck Frame (and Log and Retry / Eat / Kill), Frame Not Stuck, Add Job to Excludes / Exclude and Remove Job, **Core Up** (raise the layer's minimum cores), and View Host.
   - **Job actions** via the job header's right-click menu: View Comments, Job Not Stuck, Add Job to Excludes / Exclude and Remove Job, and **Core Up** across the job's stuck layers.

33. **Facility Service Defaults (CueCommander &rarr; Services):**
   - A facility-wide service-defaults editor at `/services`, the OpenCueWeb equivalent of CueGUI's Facility Service Defaults tab. Reached from the CueCommander menu / sidebar entry. It edits the default resource requirements applied to a layer when it runs a given service (for example `arnold`, `maya`, `nuke`, or `shell`).
   - Two panes: a left list of services (with **New** / **Del**) and a right edit form with Name, Threadable, Min/Max Threads (100 = 1 thread), Min Memory MB, Min Gpu Memory MB, Timeout, Timeout LLU, OOM Increase MB, and Tags (predefined checkboxes or a Custom Tags free-text toggle).
   - Because these are facility-wide defaults, **Save** asks for a confirmation before creating or updating, and **Del** confirms before removing a service; a toast reports the result.

34. **Subscriptions (CueCommander &rarr; Subscriptions):**
   - A per-show subscriptions table at `/subscriptions`, the OpenCueWeb equivalent of CueGUI's CueCommander Subscriptions window. Pick a show from the dropdown to list its subscriptions, one row per allocation, with columns Alloc, Usage, Size, Burst, and Used. A subscription is a show's reservation against an allocation: **Size** is the guaranteed cores, **Burst** the maximum it may temporarily use.
   - **Add Subscription** subscribes the show to another allocation (Size + Burst); **Show Properties** opens the same four-tab dialog as the Shows page.
   - **Row actions** via the right-click menu: **Edit Subscription Size...** (with a billing confirmation), **Edit Subscription Burst...**, and **Delete Subscription**.

35. **Subscription Graphs (CueCommander &rarr; Subscription Graphs):**
   - A visual view at `/subscription-graphs`, the OpenCueWeb equivalent of CueGUI's CueCommander Subscription Graphs window. A **Shows** multi-select (All Shows / Clear / per-show) chooses which shows to graph; each gets one horizontal bar per subscription.
   - Each bar is scaled to the allocation's total cores and color-coded like CueGUI (legend at the top): sky-blue allocation capacity, yellow-green in-use cores, a blue size marker and a red burst marker. Hovering shows the exact values.
   - **Row actions** via the right-click menu match the Subscriptions table plus **Add new subscription**; right-clicking a show with no subscriptions offers **Add new subscription** to create the first one.

36. **Limits (CueCommander &rarr; Limits):**
   - A limits table at `/limits`, the OpenCueWeb equivalent of CueGUI's CueCommander Limits window. Reached from the CueCommander menu / sidebar entry.
   - Columns: Limit Name, Max Value, Current Running. Auto-refreshes every 30 seconds, with a **Refresh** button for an immediate reload.
   - **Add Limit** dialog creates a new limit (max value starts at 0).
   - **Limit actions** via the row's right-click menu: **Edit Max Value** (validates a non-negative integer), **Rename**, and **Delete Limit** (with a confirmation).

37. **Redirect (CueCommander &rarr; Redirect):**
   - An administrator tool at `/redirect`, the OpenCueWeb equivalent of CueGUI's CueCommander Redirect window. Reached from the CueCommander menu / sidebar entry. It moves cores to a job that needs them by reassigning busy procs to a target job - the frames running on those procs are killed and the freed cores are booked onto the target.
   - **Target + auto-detect**: typing a target job name auto-fills the Show and minimum cores/memory from the job's layers (CueGUI `detect()`), so the search looks for procs large enough to help.
   - **Job filters** (Show, Include Groups, Require Services, Exclude Regex) and **resource filters** (Allocations, Minimum/Max Cores, Minimum Memory, Result Limit, Proc Hour Cutoff) scope the search. **Search** lists the matching hosts (Cores, Memory, PrcTime, Group, Service, Job Cores, Waiting Frames, LLU), expandable to their individual procs.
   - **Redirect** the selected hosts (or **Select All**): OpenCueWeb refuses if the target is gone / has no waiting frames / is at max cores, and asks for confirmation when the target is paused or a selected proc belongs to a different show (a cross-show redirect kills that show's frame).

38. **Group-based authorization (optional, opt-in):**
   - An optional, environment-driven authorization gate enforced server-side in a single middleware chokepoint. **Off by default** - when disabled (or when no auth provider is configured) it is a pure pass-through and every signed-in user is treated as an admin.
   - **`CUEWEB_ALLOWED_GROUPS`** restricts who may use OpenCueWeb at all; **`CUEWEB_ADMIN_GROUPS`** restricts the entire CueCommander section (all pages, including Monitor Cue, Monitor Hosts and Stuck Frame), job submission (CueSubmit), and the Manage facilities… screen. A blocked user sees an **Access denied** page (`/unauthorized`); API routes return `403`, and those menus are hidden from non-admins. Cuetopia Monitor Jobs and the Dashboard stay available to non-admins.
   - The user's groups are resolved **once at sign-in** (from the OIDC claim named by `CUEWEB_GROUPS_CLAIM`, default `groups`, or a credentials/LDAP `groups` field) and stamped on the session token; the Edge middleware only reads them, so there is no per-request directory lookup. Requires an identity provider whose token carries group memberships.

39. **Plugin system (extensible add-ons):**
   - A minimal plugin architecture, the browser counterpart of the CueGUI plugin system. A plugin is a **manifest** (name, title, version, route, optional description) plus a **lazily-loaded React component** that mounts on its own route under `/plugins/<name>`; a static `PLUGIN_REGISTRY` is the discovery mechanism and each plugin is code-split into its own chunk, fetched only when its route is visited.
   - **Plugins page** (`/plugins`): a searchable, paginated index of registered plugins. Checkboxes choose which plugins appear in the **Plugins** menu (header + sidebar, to the right of CueSubmit); the selection persists per browser (`cueweb.plugin-menu.enabled`), syncs across tabs, and seeds from each manifest's `defaultEnabled`.
   - **Per-plugin settings**: plugins register settings (`key`, `label`, `kind`, `default`) that persist to `localStorage` (`cueweb.plugin-settings.<key>`); a shared, plugin-scoped settings dialog (mounted once in the layout, opened via an event) edits them.
   - **Bundled samples**: **Hello OpenCue** (minimal contract example with greeting/shout/emoji settings, off by default) and **Cue Progress Bar** (a port of CueGUI's `cueprogbar` - a live color-coded frame-state bar with done/total/running labels and pause / unpause / kill / retry-dead controls, on by default).

40. **Workspace layout (view presets, immersive, split view):**
   - Three web-native replacements for CueGUI window/layout affordances, all stored client-side (`localStorage`) and synced across tabs.
   - **Saveable view presets** (CueGUI *Save Window Settings*): a **Views** dropdown on every major table (Jobs, Hosts, Allocations, Shows, Layers, Frames) to **Save as… / Apply / Rename / Delete** named presets capturing column order/visibility, sort, filters, and page size. Persists per page under `cueweb.views.<page>` (active under `cueweb.views.<page>.active`); a built-in **Default** restores documented defaults. Table-agnostic - it operates on the TanStack table instance.
   - **Immersive (full-screen) mode** (CueGUI *Toggle Full-Screen*): hides the header, sidebar, and status bar so the active table fills the viewport. Toggled with **`F`** / **Cmd/Ctrl+Shift+F**, the **Other** menu, or a floating **Exit immersive** button; persists under `cueweb.layout.immersive`.
   - **Multi-pane split view** (CueGUI *Add new window*): the `/split?left=…&right=…` route opens two pages side-by-side in resizable, same-origin iframe panes, each with its own URL so the whole workspace is bookmarkable and reload-safe; drag/keyboard divider resize (ratio under `cueweb.split.ratio`), per-pane page picker, Swap, and Reset 50/50. Opened from **Other &rarr; Split view**.

41. **Optional Loki log backend (CueGUI Loki log viewer parity):**
   - The frame log viewer has two interchangeable backends. By default it reads the on-disk `.rqlog` file; when `NEXT_PUBLIC_LOKI_URL` points at a [Grafana Loki](https://grafana.com/oss/loki/) server it queries Loki for the frame's lines instead (the OpenCueWeb counterpart of CueGUI's `LokiViewPlugin`), falling back to the file-based viewer when unset.
   - Both backends share the same read-only editor, **Log versions** dropdown, and empty/loading states. With Loki, each "log version" is a separate **frame attempt** (`session_start_time`), newest first, with a **Refresh** button. The backend is chosen by the deployment, not in the UI.


## OpenCueWeb's user interface

Upon logging in through Okta/Google/GitHub/LDAP or another authentication method configured using [NextAuth.js](https://next-auth.js.org/) (Figure 1), users are welcomed by OpenCueWeb's main dashboard, as shown in Figure 2.  The OpenCueWeb main page contains a paginated table that is populated with the OpenCue jobs. 

**Figure 1: OpenCueWeb authentication page**
![OpenCueWeb authentication page](/assets/images/cueweb/cueweb_cuetopia_monitor_jobs_login.png)


**Figure 1a: OpenCueWeb LDAP authentication button**
![OpenCueWeb LDAP authentication button](/assets/images/cueweb/cueweb-ldap-button.png)

**Figure 1b: OpenCueWeb LDAP login page**
![OpenCueWeb LDAP login page](/assets/images/cueweb/cueweb-ldap-login-password-page.png)

**Note:** If the OpenCueWeb login is disabled, the image below displays the initial OpenCueWeb page. This page includes a button labelled "OpenCueWeb Home", which opens the main OpenCueWeb interface. For instructions on how to disable the OpenCueWeb login, refer to the [cueweb/README.md](https://github.com/AcademySoftwareFoundation/OpenCue/blob/master/cueweb/README.md) file.

![OpenCueWeb home button page](/assets/images/cueweb/cueweb-home-button.png)

**Figure 2: OpenCueWeb main page**
![OpenCueWeb main page](/assets/images/cueweb/cueweb_cuetopia_monitor_jobs_mainpage.png)


### Navigation and global controls

Every authenticated page shares a global header and a collapsible left sidebar. The sidebar groups the same menus found in the header, with the group for the current page expanded by default (Figure 3).

**Figure 3: OpenCueWeb collapsible left sidebar menu**
![OpenCueWeb collapsible left sidebar menu](/assets/images/cueweb/cueweb_left_side_menu.png)


The **Cuetopia** menu opens the Monitor Jobs view (Figure 4).

**Figure 4: Cuetopia (Monitor Jobs) menu**
![Cuetopia (Monitor Jobs) menu](/assets/images/cueweb/cueweb_cuetopia_monitor_jobs_menu.png)


The **Cuebot Facility** menu lets you choose which facility to connect to (Figure 5).
Selecting a facility switches the active Cuebot: OpenCueWeb re-fetches all data from
that facility's gateway, the active facility is shown both on the menu chip and in
the bottom status bar, and your choice persists for the session. This mirrors
CueGUI's "Cuebot Facility" menu, which connects to a single facility at a time.
A deployment can point each facility at its own Cuebot/gateway; when only one
gateway is configured, every facility uses it.

Each facility in the menu shows a small status dot — green when its gateway is
reachable, red when it is unreachable — refreshed periodically; a facility whose
gateway is down cannot be selected. The menu also has a **Manage facilities…**
item that opens an admin screen for editing each facility's gateway URL and
credentials at runtime, without redeploying (Figure 5b).

**Figure 5: Cuebot Facility menu**
![Cuebot Facility menu](/assets/images/cueweb/cueweb_cuebot_facility_with_manage_facilities_menu.png)

**Figure 5b: Manage Facilities screen**
![Manage Facilities screen](/assets/images/cueweb/cueweb_cuebot_facility_manage_facilities.png)


The **CueCommander** menu lists the administration views such as Allocations, Limits, Monitor Cue, Monitor Hosts, Services, Shows, and Subscriptions (Figure 6).

**Figure 6: CueCommander menu options**
![CueCommander menu options](/assets/images/cueweb/cueweb_cuecommander_menu_options.png)


The **File** menu includes **Disable Job Interaction**, a read-only safety mode (Figure 7). When it is enabled, a banner appears under the header and every destructive action is turned off (Figure 8).

**Figure 7: File menu with Disable Job Interaction**
![File menu with Disable Job Interaction](/assets/images/cueweb/cueweb_file_disable_job_interaction_menu.png)


**Figure 8: Read-only mode banner when Disable Job Interaction is enabled**
![Read-only mode banner](/assets/images/cueweb/cueweb_file_disable_job_interaction_enabled.png)


The **Other** menu provides Attributes, Show Shortcuts, and Notify on Shortcut (Figure 9), while the **Help** menu offers a searchable list of menu commands and links to the user guide (Figure 10).

**Figure 9: Other menu options**
![Other menu options](/assets/images/cueweb/cueweb_other_menu_options.png)


**Figure 10: Help menu**
![Help menu](/assets/images/cueweb/cueweb_help_about_cueweb_menu.png)

The Help menu also includes **About OpenCueWeb**, which opens a dialog showing the
OpenCueWeb version and build SHA, the active Cuebot facility, the REST gateway URL
(masked), the Apache-2.0 license, and credits. A **Copy diagnostics** button
copies all of these as JSON for bug reports (Figure 10b).

**Figure 10b: About OpenCueWeb dialog**
![About OpenCueWeb dialog](/assets/images/cueweb/cueweb_help_about_cueweb.png)


A fixed status bar at the bottom of every page shows the gateway connection state, the time since the last refresh, and the application version (Figure 11).

**Figure 11: Bottom status bar indicators**
![Bottom status bar indicators](/assets/images/cueweb/cueweb_status_indicators.png)


### OpenCueWeb Audit

OpenCueWeb keeps a built-in audit trail of everything that changes state, surfaced
under **Admin -> OpenCueWeb Audit** and reachable from both the top menu and the
left sidebar (Figure 11a). Every record captures who performed an action, when
it happened, which target it acted on, the Cuebot facility it ran against, and
whether it succeeded or failed - alongside sign-in and sign-out events.
Read-only browsing (opening tables, viewing logs, paging through results) is not
recorded; only the actions that actually mutate state are.

Because every mutating action in OpenCueWeb is proxied through a single gateway
chokepoint, the audit captures all of those actions uniformly - no individual
button or context-menu entry has to opt in. It records actions taken **through
OpenCueWeb specifically**, so changes made from CueGUI, `cueman`, or `pycue` do not
appear here; this is a record of what was done in the web interface.

The audit is presented as a filterable, paginated table (Figure 11b). A search
box and actor / category / result filters narrow the rows, a time-window control
restricts the range, each row expands to show its full details, and the current
view can be exported to CSV. Each record carries a timestamp, actor, category,
action, target, facility, result, any error, sanitized details, and the endpoint
and HTTP method that were called. Records are written to an append-only JSONL
store configured by `CUEWEB_AUDIT_STORE` (mount a volume there to persist the
trail) and bounded in size by `CUEWEB_AUDIT_MAX_RECORDS`.

Access to the audit page is admin-gated and reuses OpenCueWeb's optional
group-authorization (see item 38). When no group authorization is configured the
page is visible to everyone; otherwise it is restricted to the groups listed in
`CUEWEB_ADMIN_GROUPS`.

**Figure 11a: Admin -> OpenCueWeb Audit menu**
![OpenCueWeb Audit menu](/assets/images/cueweb/cueweb_admin_cueweb_audit_menu.png)

**Figure 11b: OpenCueWeb Audit page**
![OpenCueWeb Audit page](/assets/images/cueweb/cueweb_admin_cueweb_audit.png)


### Dashboard page

The Dashboard page provides an at-a-glance overview, reachable from its own entry in the navigation (Figures 12 and 13).

**Figure 12: OpenCueWeb Dashboard page**
![OpenCueWeb Dashboard page](/assets/images/cueweb/cueweb_dashboard.png)


**Figure 13: OpenCueWeb Dashboard menu**
![OpenCueWeb Dashboard menu](/assets/images/cueweb/cueweb_dashboard_menu.png)


## OpenCueWeb dashboard (Jobs data table) - Similar to [CueGUI Cuetopia](https://www.opencue.io/docs/user-guides/monitoring-your-jobs/)'s functionalities

Here's what you can expect:

- **Visual modes:** Toggle between light and dark mode to suit your viewing preferences.

- **Customizable jobs tables:** Tailor your dashboard by selecting which columns to display, enhancing readability and focus on critical jobs metrics (see Figure 14)

**Figure 14: Column visibility dropdown to choose display data table columns**
![Column visibility dropdown](/assets/images/cueweb/cueweb_cuetopia_monitor_jobs_column%20_visibility_dropdown.png)

- **Efficient job filtering:** Filter jobs by state - `Finished`, `Failing`, `Dependency`, `In Progress`, `Paused` - to streamline management tasks  (see Figure 15).

**Figure 15: Data table filtering based on job state**
![Data table filtering based on job state](/assets/images/cueweb/cueweb_cuetopia_monitor_jobs_job_data_table_filtering.png)

* **Advanced monitoring options:** Un-monitor jobs selectively or in bulk, providing flexibility in data visualization (see Figures 16 and 17).

**Figure 16: Un-monitoring selected jobs (data table before un-monitor selection)**
![Un-monitoring selected jobs (before)](/assets/images/cueweb/cueweb_cuetopia_monitor_jobs_un-monitoring_selected_jobs-before.png)

**Figure 17: Un-monitoring selected jobs (data table after un-monitor selection)**
![Un-monitoring selected jobs (after)](/assets/images/cueweb/cueweb_cuetopia_monitor_jobs_un-monitoring_selected_jobs-after.png)

* **Detailed inspections:** An inline details panel for layers and frames associated with a selected job (see Figure 18), offering deep dives into specific frame logs as shown in Figure 19.

**Figure 18: Inline panel to view layers and frames information**
![Inline layers and frames panels](/assets/images/cueweb/cueweb_cuetopia_monitor_jobs_layersframes.png)


**Figure 19: Frame information and logs visualization**
![Frame information and logs visualization](/assets/images/cueweb/cueweb_cuetopia_monitor_jobs_frame.png)


- **Job searching:** Search for a job by typing in a show name followed by a hyphen and then the shot followed by a hyphen (ex: "show-shot-") or by typing in a regex query followed by a "!" (ex: ".*character-name*!"). This will trigger a dropdown populated with jobs for that query (see Figure 20). Clicking jobs in this dropdown will add them to the jobs table. Jobs in the jobs table will be highlighted `green` in the dropdown.

**Figure 20: Job search functionality**
![Job search functionality](/assets/images/cueweb/cueweb_cuetopia_monitor_jobs_job_search_functionality.png)

The search box returns matching jobs in a dropdown, and you can pick one or more entries from the list to add them to the table (Figures 21 and 22).

**Figure 21: Searching for jobs**
![Searching for jobs](/assets/images/cueweb/cueweb_cuetopia_monitor_jobs_search_jobs.png)


**Figure 22: Picking jobs from the search results list**
![Picking jobs from the search results list](/assets/images/cueweb/cueweb_cuetopia_monitor_jobs_search_jobs_pick_from_list.png)


### Viewing job details

Selecting **View Job Details** from a job's context menu (Figure 23) opens a dedicated page with tabs for Overview, Layers, Frames, Comments, and Dependencies.

**Figure 23: View Job Details menu entry**
![View Job Details menu entry](/assets/images/cueweb/cueweb_cuetopia_monitor_jobs_view_job_details_menu.png)


The **Overview** tab summarizes the job (Figure 24).

**Figure 24: Job details - Overview tab**
![Job details Overview tab](/assets/images/cueweb/cueweb_cuetopia_monitor_jobs_view_job_details_page_overview.png)


The **Layers** tab lists the job's layers (Figure 25).

**Figure 25: Job details - Layers tab**
![Job details Layers tab](/assets/images/cueweb/cueweb_cuetopia_monitor_jobs_view_job_details_page_layers.png)


The **Frames** tab lists the job's frames (Figure 26).

**Figure 26: Job details - Frames tab**
![Job details Frames tab](/assets/images/cueweb/cueweb_cuetopia_monitor_jobs_view_job_details_page_frames.png)


The **Comments** tab shows the comments attached to the job (Figure 27).

**Figure 27: Job details - Comments tab**
![Job details Comments tab](/assets/images/cueweb/cueweb_cuetopia_monitor_jobs_view_job_details_page_comments.png)


The **Dependencies** tab lists the job's dependencies (Figure 28).

**Figure 28: Job details - Dependencies tab**
![Job details Dependencies tab](/assets/images/cueweb/cueweb_cuetopia_monitor_jobs_view_job_details_page_dependencies.png)


### Job comments

You can open the comments for a job from the **Comments** entry in the job context menu (Figure 29). When a job already has at least one comment, a sticky-note icon appears in the Comments column of the Jobs table (Figure 30).

**Figure 29: Comments menu entry**
![Comments menu entry](/assets/images/cueweb/cueweb_cuetopia_monitor_jobs_comments_menu.png)


**Figure 30: Comments column icon for jobs that have comments**
![Comments column icon](/assets/images/cueweb/cueweb_cuetopia_monitor_jobs_comments_has_comments_icon.png)


The comments page lets you list, add, edit, and delete comments for the selected job (Figure 31).

**Figure 31: Job comments page**
![Job comments page](/assets/images/cueweb/cueweb_cuetopia_monitor_jobs_comments_page.png)


You can view an existing comment, then add a new comment by typing the message and saving it (Figures 32 to 34).

**Figure 32: Viewing a comment**
![Viewing a comment](/assets/images/cueweb/cueweb_cuetopia_monitor_jobs_comments_page_view_comment.png)

**Figure 33: Adding a comment**
![Adding a comment](/assets/images/cueweb/cueweb_cuetopia_monitor_jobs_comments_page_adding_comment.png)

**Figure 34: Comment added**
![Comment added](/assets/images/cueweb/cueweb_cuetopia_monitor_jobs_comments_page_added_comment.png)

To remove a comment, select it and confirm the deletion; a notification confirms the comment was removed (Figures 35 and 36).

**Figure 35: Confirming deletion of a selected comment**
![Confirming deletion of a selected comment](/assets/images/cueweb/cueweb_cuetopia_monitor_jobs_comments_page_delete_selected_comment_confirmation.png)

**Figure 36: Notification confirming the comment was deleted**
![Notification confirming the comment was deleted](/assets/images/cueweb/cueweb_cuetopia_monitor_jobs_comments_page_deleted_selected_comment_notification.png)

OpenCueWeb also supports predefined comments (saved macros) that you can reuse, add, edit, and delete (Figures 37 to 44).

**Figure 37: Using a predefined comment**
![Using a predefined comment](/assets/images/cueweb/cueweb_cuetopia_monitor_jobs_comments_page_use_a_predefined_comment.png)

**Figure 38: Adding a predefined comment macro**
![Adding a predefined comment macro](/assets/images/cueweb/cueweb_cuetopia_monitor_jobs_comments_page_use_a_predefined_comment_add_predefined_comment.png)

**Figure 39: Entering the predefined comment details**
![Entering the predefined comment details](/assets/images/cueweb/cueweb_cuetopia_monitor_jobs_comments_page_use_a_predefined_comment_adding_predefined_comment.png)

**Figure 40: Predefined comment added**
![Predefined comment added](/assets/images/cueweb/cueweb_cuetopia_monitor_jobs_comments_page_use_a_predefined_comment_added_predefined_comment.png)

**Figure 41: Editing a predefined comment**
![Editing a predefined comment](/assets/images/cueweb/cueweb_cuetopia_monitor_jobs_comments_page_use_a_predefined_comment_editing_predefined_comment.png)

**Figure 42: Predefined comment edited**
![Predefined comment edited](/assets/images/cueweb/cueweb_cuetopia_monitor_jobs_comments_page_use_a_predefined_comment_edited_predefined_comment.png)

**Figure 43: Deleting a predefined comment**
![Deleting a predefined comment](/assets/images/cueweb/cueweb_cuetopia_monitor_jobs_comments_page_use_a_predefined_comment_deleting_predefined_comment.png)

**Figure 44: Confirming deletion of a predefined comment**
![Confirming deletion of a predefined comment](/assets/images/cueweb/cueweb_cuetopia_monitor_jobs_comments_page_use_a_predefined_comment_delete_predefined_comment_confirmation.png)

### Attributes panel

The **Other -> Attributes** panel shows a key/value tree for the currently selected entity. Selecting a job populates it with the job's attributes (Figure 45), and selecting a layer shows that layer's attributes (Figure 46).

**Figure 45: Attributes panel for a selected job**
![Attributes panel for a selected job](/assets/images/cueweb/cueweb_other_menu_attributes_job.png)


**Figure 46: Attributes panel for a selected layer**
![Attributes panel for a selected layer](/assets/images/cueweb/cueweb_other_menu_attributes_layer.png)


The Attributes panel can be docked on the right, bottom, left, or top of the page (Figures 47 to 50).

**Figure 47: Attributes panel docked right**
![Attributes panel docked right](/assets/images/cueweb/cueweb_other_menu_attributes_dock_right.png)


**Figure 48: Attributes panel docked bottom**
![Attributes panel docked bottom](/assets/images/cueweb/cueweb_other_menu_attributes_dock_bottom.png)


**Figure 49: Attributes panel docked left**
![Attributes panel docked left](/assets/images/cueweb/cueweb_other_menu_attributes_dock_left.png)


**Figure 50: Attributes panel docked top**
![Attributes panel docked top](/assets/images/cueweb/cueweb_other_menu_attributes_dock_top.png)


### Keyboard shortcuts

Selecting **Other -> Show Shortcuts** opens an overlay listing the available keyboard shortcuts (Figure 51).

**Figure 51: Keyboard shortcuts overlay**
![Keyboard shortcuts overlay](/assets/images/cueweb/cueweb_other_menu_show_shortcuts.png)


### OpenCueWeb Actions for Jobs / Layers / Frames

The OpenCueWeb system includes actions like `eat dead frames`, `retry dead frames`, `pause`, `unpause`, and `kill` for selected jobs in the table. Also, the ability to right-click jobs, layers, and frames to get a context menu popup with actions for that object type.

The Pause / Unpause entry in the job context menu is a single toggle: it reads **Pause** when the job is running (In Progress, Failing, Dependency), **Unpause** when the job is already paused, and is shown disabled (grayed) when the job is Finished.

Figure 52 shows the `job` context menu with options to `un-monitor`, `comments`, `pause`, `retry dead frames`, `eat dead frames` and `kill` jobs and Figure 53 shows the successful message after selecting `kill` a job.

**Figure 52: OpenCueWeb with job context menu open**
![OpenCueWeb with job context menu open](/assets/images/cueweb/cueweb_cuetopia_monitor_jobs_job_context_menu_open.png)

**Figure 53: Pop-up showing a successful message after selecting `kill` a job**
![Pop-up showing successful kill job message](/assets/images/cueweb/cueweb_cuetopia_monitor_jobs_job_context_menu_open_and_success_notification.png)

Figure 54 shows the `layer` context menu with options to `kill`, `eat`, `retry`, and `retry dead frames` and Figure 55 shows the successful message after selecting `retry` a layer.

**Figure 54: OpenCueWeb with layer context menu open**
![OpenCueWeb with layer context menu open](/assets/images/cueweb/cueweb_cuetopia_monitor_jobs_layer_context_menu_open.png)

**Figure 55: Pop-up showing a successful message after selecting `retry` a layer**
![Pop-up showing successful retry layer message](/assets/images/cueweb/cueweb_cuetopia_monitor_jobs_layer_context_menu_open_and_success_notification.png)

Finally, Figure 56 shows the `frame` context menu with options to `kill`, `eat`, and `retry` and Figure 57 shows the successful message after selecting `eat` a frame.

**Figure 56: OpenCueWeb with frame context menu open**
![OpenCueWeb with frame context menu open](/assets/images/cueweb/cueweb_cuetopia_monitor_jobs_frame_context_menu_open.png)

**Figure 57: Pop-up showing a successful message after selecting `eat` a frame**
![Pop-up showing successful eat frame message](/assets/images/cueweb/cueweb_cuetopia_monitor_jobs_frame_context_menu_open_and_success_notification.png)

### Browser-based job submission (CueSubmit)

The **CueSubmit** top-level menu (header / sidebar / mobile drawer) opens the browser-based job submission form at `/cuesubmit`, a one-for-one equivalent of the standalone CueSubmit CLI tool (Figures 58 and 59).

**Figure 58: CueSubmit menu options**
![CueSubmit menu options](/assets/images/cueweb/cueweb_cuesubmit_menu_options.png)

**Figure 59: CueSubmit Submit Job page**
![CueSubmit Submit Job page](/assets/images/cueweb/cueweb_cuesubmit_submit_job.png)

### Email the artist about a job

The job context menu's **Email Artist...** entry mirrors CueGUI's Email dialog (Figures 60 and 61). It opens a themed dialog pre-filled with From, To (the job's owner), CC, Subject (`cuemail: please check <jobName>`), and a Body that greets the artist by name. Every field is editable. **Send** hands the result to your default mail client via a `mailto:` URL.

**Figure 60: Email Artist entry in the job context menu**
![Email Artist entry in the job context menu](/assets/images/cueweb/cueweb_cuetopia_monitor_jobs_email_artist_menu.png)

**Figure 61: Email Artist dialog pre-filled from the selected job**
![Email Artist dialog pre-filled from the selected job](/assets/images/cueweb/cueweb_cuetopia_monitor_jobs_email_artist_window.png)

### Request cores from the support team

The job context menu's **Request Cores...** entry mirrors CueGUI's `RequestCoresDialog` (Figures 62 and 63). It opens an email composer pre-filled with **From** (your signed-in session), **CC** (`<show>-support@<domain>`), **Subject** (`Requesting Cores for <jobName>`), and an auto-populated body listing the job's still-active layers (Layer Name / Minimum Memory / Min Cores). Two extra fields let you add the **Date/Time by which completion is needed** and any **additional notes**. **Send** hands the result to your default mail client via a `mailto:` URL.

**Figure 62: Request Cores entry in the job context menu**
![Request Cores entry in the job context menu](/assets/images/cueweb/cueweb_cuetopia_monitor_jobs_request_cores_menu.png)

**Figure 63: Request Cores dialog pre-filled from the selected job**
![Request Cores dialog pre-filled from the selected job](/assets/images/cueweb/cueweb_cuetopia_monitor_jobs_request_cores_window.png)


### Subscribe to a job by email

The job context menu's **Subscribe to Job** entry mirrors CueGUI's `SubscribeToJobDialog` (Figures 64 to 66). Unlike the **Notify bell** in the Jobs table - which is a *browser-side* subscription that fires an in-app toast (and optional desktop popup) - this entry registers a *server-side, email* subscriber on Cuebot. When the job reaches `FINISHED`, Cuebot sends an email to the saved address.

The dialog shows the job name, an informational **From** address (deployment default), and an editable **To** address pre-filled with your account email (or `<user>@<domain>` if your session doesn't expose one). Edit the **To** field if you want notifications sent somewhere else - a team alias, a personal address, etc. - and click **Save**. A toast confirms the subscription is registered.

The two subscription mechanisms are independent; you can use one, the other, or both.

**Figure 64: Subscribe to Job entry in the job context menu**
![Subscribe to Job entry in the job context menu](/assets/images/cueweb/cueweb_cuetopia_monitor_jobs_subscribe_to_job_menu.png)

**Figure 65: Subscribe to Job dialog pre-filled from the selected job**
![Subscribe to Job dialog pre-filled from the selected job](/assets/images/cueweb/cueweb_cuetopia_monitor_jobs_subscribe_to_job_window.png)

**Figure 66: Toast confirming the subscription is registered**
![Toast confirming the subscription is registered](/assets/images/cueweb/cueweb_cuetopia_monitor_jobs_subscribe_to_job_confirmation.png)


### Adjust a job's dispatch priority

The job context menu's **Set Priority...** entry opens a themed dialog with a 1-100 range slider and a matching number input - either control drives the value, and both stay in sync. The current priority is pre-filled (cuebot's default is 100); higher numbers dispatch first. **Set Priority...** is available everywhere the job context menu appears: both **Cuetopia &rarr; Monitor Jobs** (the default landing page) and **CueCommander &rarr; Monitor Cue**. The dialog and behavior are identical on either page (Figures 67 to 69).

After **Apply**, a toast confirms the new value and the **Priority** column in the Jobs table updates immediately - no need to wait for the regular 5-second refresh tick.

**Figure 67: Set Priority entry in the job context menu (Cuetopia Monitor Jobs)**
![Set Priority entry in the job context menu](/assets/images/cueweb/cueweb_cuetopia_monitor_jobs_set_priority_menu.png)

**Figure 68: Set Priority dialog with slider and number input**
![Set Priority dialog with slider and number input](/assets/images/cueweb/cueweb_cuetopia_monitor_jobs_set_priority_window.png)

**Figure 69: Toast confirming the priority change and immediate column update**
![Toast confirming the priority change](/assets/images/cueweb/cueweb_cuetopia_monitor_jobs_set_priority_confirmation.png)

The checkable **Cuetopia &rarr; View Job Graph** entry (Figure 70) toggles a read-only dependency-graph panel. With it on, selecting a job in Monitor Jobs mounts an interactive node graph as a third panel under the inline Layers and Frames panels (Figure 71). The graph shows the focus job with its **layers** (so a job with no cross-job dependencies still renders its structure) and walks cross-job depends in both directions, color-codes nodes by kind (JOB / LAYER / FRAME), and rings the focus job (Figure 72). **Double-click** a node to open that job's detail page; **right-click a layer node** for the CueGUI Job-Graph layer menu (Auto Layout Nodes; Dependencies: View Dependencies… / Dependency Wizard… / Mark done; Reorder Frames…; Stagger Frames…; Properties…; Kill / Eat / Retry / Retry Dead Frames), shown in Figure 73.

**Figure 70: View Job Graph entry in the Cuetopia menu**
![View Job Graph entry in the Cuetopia menu](/assets/images/cueweb/cueweb_cuetopia_view_job_graph_menu.png)

**Figure 71: Dependency graph panel below the inline Layers and Frames panels**
![Dependency graph panel below Layers and Frames](/assets/images/cueweb/cueweb_cuetopia_view_job_graph_monitor_jobs_dependency_graph.png)

**Figure 72: The dependency graph panel showing the focus job and its layer**
![The Job Dependency Graph showing the focus job and its layer](/assets/images/cueweb/cueweb_dependency_graph.png)

**Figure 73: Right-click layer-node menu in the Job Dependency Graph**
![Right-click layer-node menu in the Job Dependency Graph](/assets/images/cueweb/cueweb_dependency_graph_menu_options.png)


## Conclusion

In conclusion, the OpenCueWeb system marks a significant advancement in rendering job management by providing a powerful, web-based interface that simplifies and enhances user interaction with the OpenCue system. With features like customizable job tables, efficient job filtering, and detailed inspections, along with the ability to view comprehensive logs and switch visual modes, OpenCueWeb ensures that managing rendering jobs is more accessible and adaptable to a variety of user needs.
