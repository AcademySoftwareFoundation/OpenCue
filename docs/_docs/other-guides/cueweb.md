---
title: "CueWeb System"
layout: default
parent: Other Guides
nav_order: 57
linkTitle: "CueWeb system"
date: 2025-02-04
description: >
   CueWeb system: First web-based release of CueGUI with many features from Cuetopia
---

# CueWeb

### A web-based CueGUI alternative with job filtering, inspection, and interactive controls

---

This guide provides an introduction to the CueWeb system, the web-based version of CueGUI.

## Introduction

[OpenCue](https://www.opencue.io/) has facilitated efficient management of rendering jobs through its application, CueGUI, which includes Cuetopia and CueCommander. Previously, OpenCue's capabilities were somewhat restricted as it was primarily limited to desktops/workstations running Qt-based applications. Because of that, the CueWeb system was created. CueWeb is a transformative, web-based application that extends access across multiple platforms, ensuring users can manage their rendering tasks from virtually anywhere.

## A seamless transition to web accessibility 

CueWeb replicates the core functionality of [CueGUI](https://www.opencue.io/docs/reference/cuegui-app/) (Cuetopia and Cuecommander) in a web-accessible format, enhancing usability while maintaining the familiar interface that users appreciate. This adaptation supports essential operations such as:

1. **Persistent global header (every authenticated route):**
   - OpenCue logo (theme-aware: black in light mode, white in dark mode) + the **CueWeb** wordmark.
   - Six dropdown menus mirroring the CueGUI menu bar: **File** (Disable Job Interaction), **Cuebot Facility**, **Cuetopia** (Monitor Jobs), **CueCommander** (Allocations, Limits, Monitor Cue, Monitor Hosts, Redirect, Services, Shows, Stuck Frame, Subscription Graphs, Subscriptions), **Other** (Attributes, Show Shortcuts, Notify on Shortcut), and **Help** (search box across every menu command, plus Online User Guide / Make a Suggestion / Report a Bug). Routes that are not yet implemented 404 gracefully.
   - Theme toggle (light/dark).
   - Always-visible **Sign out** button that calls NextAuth's `signOut()` and routes to `/login` - the `/login` page itself shows either the **CueWeb Home** button (when `NEXT_PUBLIC_AUTH_PROVIDER` is empty) or the configured provider buttons.
2. **Collapsible left sidebar (every authenticated route):**
   - Same six groups as the header (**File**, **Cuebot Facility**, **Cuetopia**, **CueCommander**, **Other**, **Help**), organized as accordion sections; the group containing the active route auto-expands.
   - One click on the **Collapse** button shrinks the sidebar to an icon-only rail; overall and per-group state persist across reloads.
3. **Disable Job Interaction (read-only safety mode):**
   - File -> Disable Job Interaction (header or sidebar) toggles a global flag, persisted in `localStorage` and synced across tabs.
   - When on, an amber **Read-only mode** banner appears under the header (with a *Re-enable* button) and every destructive action (Eat / Retry / Pause / Unpause / Kill - both in the jobs toolbar and in the right-click menus on job/layer/frame rows) becomes inert.
4. **Attributes panel (Other -> Attributes):**
   - Docked drawer showing a collapsible key/value tree for the currently-selected entity (click a row in the jobs table to populate it).
   - Position picker in the title bar docks the panel on the **right** (default), **bottom**, **left**, or **top**. A filter input narrows the tree live.
5. **Bottom status bar (IDE-style):**
   - Fixed 24-pixel bar at the bottom of every authenticated route.
   - **Gateway** (left): dot + `Online` / `Offline` + last round-trip latency. Polled every 10s via `/api/health` (JWT-signed reachability probe with a 5s timeout). Whole bar turns red when the gateway is unreachable.
   - **Last refresh** (center): live "Ns ago" timer that updates whenever the jobs table fires a `cueweb:jobs-refreshed` event.
   - **Version** (right): `v<NEXT_PUBLIC_APP_VERSION>` (falls back to `package.json#version` at build time).
6. **Breadcrumb navigation on detail views:**
   - Above the frame log page and the per-job comments page, a "Home > Jobs > ..." trail lets you click back to the jobs index or any parent in the path.
   - Long segment labels truncate to `max-w-[40ch]` with the full text recoverable in a tooltip on hover.
   - Last segment renders as plain text with `aria-current="page"`; non-last segments are `next/link`s.
7. **Secure user authentication:**
   - Authentication through Github, Google, [Okta](https://www.okta.com/), LDAP, Apple, GitLab, Amazon, Microsoft Azure, LinkedIn, Atlassian, Auth0, etc. Other providers and login options can be easily configured and enabled in the CueWeb. LDAP authentication is particularly useful for intranet deployments using company directory credentials. See [NextAuth.js](https://next-auth.js.org/) authentication using email, credentials and providers: https://next-auth.js.org/providers/
8. **Customizable job / layer / frame tables (CueGUI parity):**
   - Each of the three data tables (Jobs, Layers, Frames) has a **Columns** dropdown with three controls per column: a checkbox to hide/show, and **`←` / `→`** arrows to nudge the column left / right within the user-reorderable subset. Non-hideable system columns (the row-select checkbox) stay anchored.
   - A **Reset to Default** button pinned at the top of the dropdown clears both visibility AND order in one click.
   - Both states persist per table in `localStorage` (Jobs uses the bare `columnVisibility` / `columnOrder` keys; Layers/Frames use `cueweb.layers.*` and `cueweb.frames.*`).
   - CueGUI-parity column sets:
     - **Jobs**: Name, **Comments** (sortable sticky-note column - pull jobs with comments to the top in one click), State, Done / Total, Running, Dead, Eaten, Wait, MaxRss, Age, Readable Age, **Launched**, **Eligible**, **Finished**, **User Color** (per-job color swatch persisted to `localStorage["cueweb.userColors"]` with cross-tab sync via the standard `storage` event), Progress, Notify.
     - **Layers**: Dispatch Order, Name, Services, Limits, Range, Cores, Memory, Gpus, Gpu Memory, MaxRss, Total, Done, Run, Depend, Wait, Eaten, Dead, Avg, Tags, **Progress** (stacked animated bar, same palette as the Jobs progress bar), Timeout, Timeout LLU, **Eligible**.
     - **Frames**: Order, Frame, Layer, Status, Cores, GPUs, Host, Retries, CheckP, Runtime, **LLU** (only populated for `RUNNING` frames - blank for WAITING / DEPEND / SUCCEEDED / DEAD, matching CueGUI), **Memory (RSS)**, **Memory (PSS)**, GPU Memory, **Remain** (placeholder until the ETA predictor is wired in), Start Time, Stop Time, **Eligible Time**, **Submission Time**, **Last Line** (placeholder until the per-frame log-tail fetch is wired in).
   - Each table also has a small client-side substring **Filter** input next to its Columns dropdown that narrows the rows already loaded; resets to page 1 on every keystroke and keeps sorting, visibility, reordering and pagination working over the filtered subset.
9. **Flexible monitoring controls:**
   - Easily un-monitor jobs across all statuses.
10. **Detailed job inspection (inline Layers + Frames panel):**
   - Clicking a row in the jobs table reveals the associated **Layers** and **Frames** tables stacked below the jobs grid (CueGUI Monitor Jobs + Monitor Job Details parity).
   - Clicking a layer row narrows the frames panel to that layer and pushes the layer's attributes into the docked Attributes panel; clicking the same layer again clears the filter and re-selects the job in Attributes.
   - Double-clicking any frame row opens the log viewer for that frame.
   - Inline panels refresh every 5 seconds with cancellation guards so stale responses can't overwrite a fresh selection.
11. **Frame navigation and logs access:**
   - Navigate frames using hyperlinks that lead to dedicated pages for frame data and logs.
12. **Advanced job search functionality:** 
   - Search for jobs by show name with dropdown suggestions for matching entries.
   - Search functionality requires `show-shot-` as the prefix to reduce the number of results returned.
13. **Dark mode toggle for user preference:** 
   - Switch between light and dark modes according to user preference.
14. **Enhanced search functionality:**
   - Users can enable regex searches by appending '!' to their queries, with tooltips provided for guidance.
   - Optimized loading times using virtualization and web workers, along with loading animations for a better user experience.
   - Users can add or remove multiple jobs directly from the search results, with existing jobs highlighted in green.
15. **Enhanced security using Opencue API:**
   - CueWeb uses JWT token generation for enhanced security in authorization headers.
16. **CueWeb actions and context menu (CueGUI parity):**
   - Right-clicking any row in the Jobs, Layers, or Frames tables opens a context menu that mirrors the CueGUI Monitor Jobs / Monitor Job Details menus.
   - On touch devices, every row has a small **`⋮` Actions** button as its leftmost cell. Tapping it opens the same menu the desktop right-click opens.
   - **Job actions** include: Unmonitor, View Job, **View Job Details** (opens the tabbed `/jobs/<jobName>` page with Overview / Layers / Frames / Comments / Dependencies), **Copy Job Name**, Email Artist, Request Cores, Subscribe to Job, Comments, View Dependencies, Dependency Wizard, Drop External / Internal Dependencies, Set / Clear User Color, Set Max Retries, Reorder / Stagger Frames, Pause / Unpause, Auto-Eat On / Off, Retry / Eat Dead Frames, Unbook, Kill, Show Progress Bar.
   - **Layer actions** include: View Layer, **Copy Layer Name**, dependency items, Reorder / Stagger Frames, Properties, Kill, Eat, Retry, Retry Dead Frames.
   - **Frame actions** include: **Tail Log / View Log** (in-browser viewer), **View Log on \<editor\>** (external editor - see item 23), **Copy Log Path**, **Copy Frame Name**, View Host, dependency items, Filter Selected Layers, Reorder, Preview All, Retry, Eat, Kill, Eat and Mark done, View Processes.
   - All copy actions work whether CueWeb is reached at `localhost` or at a LAN IP over plain HTTP.
   - Menus scroll instead of overflowing on small viewports. Items that depend on dialogs / backend integrations not yet implemented in CueWeb surface a friendly placeholder toast. Destructive items are auto-disabled when **Disable Job Interaction** is on.

17. **Auto-reloading of tables:**
   - All tables (jobs, layers, frames) are auto-reloaded at regular intervals to display the latest data.

18. **Animated progress bar on Jobs AND Layers:**
   - Both tables render a stacked bar with five colored segments (succeeded, running, waiting, depend, dead) using the shared `<ProgressBar/>` renderer. The Layers table consumes the same palette via `getLayerProgressSegments` in `cueweb/app/utils/layer_progress_utils.ts`.
   - Hovering the bar opens a tooltip with the exact frame count and percentage for each state.

19. **Frame state filter chips:**
   - Above the frames table, a chip is rendered for each supported state - `WAITING`, `RUNNING`, `SUCCEEDED`, `DEAD`, `EATEN`, `DEPEND` - annotated with the count of frames currently in that state.
   - Selections combine with OR semantics; the table pages back to the first page on selection change so the filtered results are immediately visible.
   - The current selection is mirrored to the `frameStates` URL query parameter (e.g. `?frameStates=WAITING,DEAD`), making filtered views bookmarkable and shareable.

20. **Per-job completion notifications:**
   - The Jobs table includes a **Notify** column with a bell button per row. Clicking it subscribes the browser to a notification when the job reaches `FINISHED`.
   - The bell has three visual states: outline (not subscribed), filled (subscribed/waiting), and filled with a green dot (notification has fired - click to clear).
   - The bell is disabled on rows whose job state is already `FINISHED` when first viewed.
   - Subscriptions always succeed; the OS-level notification permission is an optional upgrade for desktop popups. Clicking the bell branches the resulting toast on `granted` / `denied` / `default` so users know whether they got an in-app-only subscription or also a system popup.
   - An app-wide background poller checks each subscribed job every 15 seconds. When a job reaches `FINISHED` an in-app toast fires (always), and a desktop popup appears too if the OS-level notification permission was granted. When several CueWeb tabs poll the same job concurrently only one tab actually fires the toast, so you see exactly one notification per finished job.
   - Subscriptions are persisted in the browser and survive page reloads. Subscriptions to jobs that no longer exist in Cuebot are removed automatically on the next poll. Mutations are synced across tabs.

21. **Keyboard shortcuts overlay (+ menu access + per-shortcut toast):**
   - Press `?` anywhere to open the cheat-sheet overlay; press `Esc` to close it. Single-letter keys (`/`, `r`, `t`) are ignored while typing into editable elements so they don't collide with text input, and modifier-key combos (Ctrl / Cmd / Alt) are passed through to the browser.
   - The same overlay is reachable from **Other ▸ Show Shortcuts** in both the header and the sidebar. Both items dispatch a `cueweb:open-shortcuts` `CustomEvent` on `window` that the overlay listens for.
   - **Notify on Shortcut** (also under Other; default ON, persisted to `localStorage["cueweb.shortcutNotifications"]`) controls whether a toast naming the action fires every time a shortcut triggers (e.g. `Shortcut: r → Refresh table`). The pref is read imperatively at fire-time, so flipping the toggle takes effect on the very next keypress without a reload.

22. **Job comments:**
   - Per-job CRUD that mirrors the CueGUI **Comments** dialog (`cuegui/cuegui/Comments.py`): list / add / edit / delete.
   - Reached from the **Comments** entry in the job context menu, or from a sticky-note icon in the Jobs table's dedicated **Comments** column (sortable, sits right after Name) when the job has at least one comment.
   - Messages support markdown and are sanitized (`react-markdown` + `rehype-sanitize`).
   - Predefined-comment macros are stored per-browser in `localStorage` (`cueweb-comment-macros`), with the same `> Add / > Edit / > Delete predefined comment` workflow as CueGUI.

23. **External editor integration (View Log on \<editor\>):**
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
   - If the chosen editor isn't installed on the user's machine, CueWeb shows a warning toast after a short delay pointing the user at the alternatives.
   - When the frame hasn't started running yet (WAITING / DEPEND frames have no log file on disk), the menu item shows a friendly warning toast instead of handing a non-existent path to the editor.

24. **Mobile-friendly UI:**
   - Every authenticated route works on phone-sized viewports. The Jobs page stacks its filter / toolbar / table vertically on small screens instead of forcing a wide layout, and the data tables can be swiped horizontally to reach off-screen columns.
   - On phones the desktop sidebar is replaced by a hamburger button in the global header. Tapping it opens a side drawer mirroring every sidebar group: Dashboard, File, Cuebot Facility, Cuetopia, CueCommander, Other (Attributes / Show Shortcuts / Notify on Shortcut), and Help. The drawer is scrollable and auto-closes when you tap a navigation link.
   - Every Jobs / Layers / Frames row has a small **`⋮` Actions** button as its leftmost cell. Tapping it opens the same context menu the desktop right-click opens (see item 16), so touch users get the full action set without a right-click event.
   - The keyboard-shortcuts overlay (item 21) is itself touch-friendly: every key badge in the list is tappable, so `/` (focus search), `r` (refresh), and `t` (toggle theme) work on phones without a physical keyboard.

25. **LAN access (CueWeb usable from phones / tablets):**
   - The same image works whether the browser reaches CueWeb at `localhost` on the dev machine or at a LAN IP from another device on the same network - no rebuild needed when you want to test on a phone. The build-time `NEXT_PUBLIC_URL` setting defaults to empty for this reason; only set it to an absolute URL if your deployment serves the API on a different origin than the UI.
   - Copy actions (Copy Job / Layer / Frame Name, Copy Log Path) work even when CueWeb is reached over plain HTTP at a LAN IP, where the modern Clipboard API would otherwise be unavailable. Compatibility includes iOS Safari.

## CueWeb's user interface

Upon logging in through Okta/Google/GitHub/LDAP or another authentication method configured using [NextAuth.js](https://next-auth.js.org/) (Figures 1 or 2), users are welcomed by CueWeb's main dashboard, as shown in Figure 3 (light mode) or Figure 4 (dark mode).  The CueWeb main page contains a paginated table that is populated with the OpenCue jobs. 

#### Figure 1: CueWeb authentication page (light mode)
![CueWeb authentication page (light mode)](/assets/images/cueweb/figure1-auth-light.png)

#### Figure 2: CueWeb authentication page (dark mode)
![CueWeb authentication page (dark mode)](/assets/images/cueweb/figure2-auth-dark.png)

#### Figure 2b: CueWeb LDAP authentication button
![CueWeb LDAP authentication button](/assets/images/cueweb/cueweb-ldap-button.png)

#### Figure 2c: CueWeb LDAP login page
![CueWeb LDAP login page](/assets/images/cueweb/cueweb-ldap-login-password-page.png)

**Note:** If the CueWeb login is disabled, the image below displays the initial CueWeb page. This page includes a button labelled "CueWeb Home", which opens the main CueWeb interface. For instructions on how to disable the CueWeb login, refer to the [cueweb/README.md](https://github.com/AcademySoftwareFoundation/OpenCue/blob/master/cueweb/README.md) file.

![CueWeb home button page](/assets/images/cueweb/cueweb-home-button.png)

#### Figure 3: CueWeb main page (light mode)
![CueWeb main page (light mode)](/assets/images/cueweb/figure3-main-light.png)

#### Figure 4: CueWeb main page (dark mode)
![CueWeb main page (dark mode)](/assets/images/cueweb/figure4-main-dark.png)

## CueWeb dashboard (Jobs data table) - Similar to [CueGUI Cuetopia](https://www.opencue.io/docs/user-guides/monitoring-your-jobs/)'s functionalities

Here's what you can expect:

- **Visual modes:** Toggle between light and dark mode to suit your viewing preferences.

- **Customizable jobs tables:** Tailor your dashboard by selecting which columns to display, enhancing readability and focus on critical jobs metrics (see Figure 5)

#### Figure 5: Column visibility dropdown to choose display data table columns
![Column visibility dropdown](/assets/images/cueweb/figure5-column-visibility.png)

- **Efficient job filtering:** Filter jobs by state - `Finished`, `Failing`, `Dependency`, `In Progress`, `Paused` - to streamline management tasks  (see Figure 6).

#### Figure 6: Data table filtering based on job state
![Data table filtering based on job state](/assets/images/cueweb/figure6-job-filtering.png)

* **Advanced monitoring options:** Un-monitor jobs selectively or in bulk, providing flexibility in data visualization (see Figures 7 and 8).

#### Figure 7: Un-monitoring selected jobs (data table before un-monitor selection)
![Un-monitoring selected jobs (before)](/assets/images/cueweb/figure7-unmonitor-before.png)

#### Figure 8:  Un-monitoring selected jobs (data table after un-monitor selection)
![Un-monitoring selected jobs (after)](/assets/images/cueweb/figure8-unmonitor-after.png)

* **Detailed inspections:** A pop-up detail view for layers and frames associated with a selected job (see Figure 8 for light mode and Figure 10 for dark mode), offering deep dives into specific frame logs as shown in Figure 11 for light mode and Figure 12 for dark mode.

#### Figure 9: Pop-up window to view layers and frames information (light mode) 
![Pop-up window layers and frames (light mode)](/assets/images/cueweb/figure9-popup-light.png)

#### Figure 10: Pop-up window to view layers and frames information (dark mode) 
![Pop-up window layers and frames (dark mode)](/assets/images/cueweb/figure10-popup-dark.png)

#### Figure 11: Frame information and logs visualization (light mode) 
![Frame information and logs visualization (light mode)](/assets/images/cueweb/figure11-frame-logs-light.png)

#### Figure 12: Frame information and logs visualization (dark mode) 
![Frame information and logs visualization (dark mode)](/assets/images/cueweb/figure12-frame-logs-dark.png)

- **Job searching:** Search for a job by typing in a show name followed by a hyphen and then the shot followed by a hyphen (ex: "show-shot-") or by typing in a regex query followed by a "!" (ex: ".*character-name*!"). This will trigger a dropdown populated with jobs for that query (see Figure 13). Clicking jobs in this dropdown will add them to the jobs table. Jobs in the jobs table will be highlighted `green` in the dropdown.

#### Figure 13: Job search functionality 
![Job search functionality](/assets/images/cueweb/figure13-job-search.png)

### CueWeb Actions for Jobs / Layers / Frames

The CueWeb system includes actions like `eat dead frames`, `retry dead frames`, `pause`, `unpause`, and `kill` for selected jobs in the table. Also, the ability to right-click jobs, layers, and frames to get a context menu popup with actions for that object type. 

Figure 14 shows the `job` context menu with options to `un-monitor`, `comments`, `pause`, `retry dead frames`, `eat dead frames` and `kill` jobs and Figure 15 shows the successful message after selecting `kill` a job.

#### Figure 14: CueWeb with job context menu open
![CueWeb with job context menu open](/assets/images/cueweb/figure14-job-context-menu.png)

#### Figure 15: Pop-up showing a successful message after selecting `kill` a job
![Pop-up showing successful kill job message](/assets/images/cueweb/figure15-kill-job-success.png)

Figure 16 shows the `layer` context menu with options to `kill`, `eat`, `retry`, and `retry dead frames` and Figure 17 shows the successful message after selecting `retry` a layer.

#### Figure 16: CueWeb with layer context menu open
![CueWeb with layer context menu open](/assets/images/cueweb/figure16-layer-context-menu.png)

#### Figure 17: Pop-up showing a successful message after selecting `retry` a layer
![Pop-up showing successful retry layer message](/assets/images/cueweb/figure17-retry-layer-success.png)

Finally, Figure 18 shows the `frame` context menu with options to `kill`, `eat`, and `retry` and Figure 19 shows the successful message after selecting `eat` a frame.

#### Figure 18: CueWeb with frame context menu open
![CueWeb with frame context menu open](/assets/images/cueweb/figure18-frame-context-menu.png)

#### Figure 19: Pop-up showing a successful message after selecting `eat` a frame
![Pop-up showing successful eat frame message](/assets/images/cueweb/figure19-eat-frame-success.png)


## Conclusion

In conclusion, the CueWeb system marks a significant advancement in rendering job management by providing a powerful, web-based interface that simplifies and enhances user interaction with the OpenCue system. With features like customizable job tables, efficient job filtering, and detailed inspections, along with the ability to view comprehensive logs and switch visual modes, CueWeb ensures that managing rendering jobs is more accessible and adaptable to a variety of user needs.