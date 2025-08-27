---
title: "CueWeb System"
layout: default
parent: Other Guides
nav_order: 36
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

1. **Secure user authentication:** 
   - Authentication through Github, Google, [Okta](https://www.okta.com/), Apple, GitLab, Amazon, Microsoft Azure, LinkedIn, Atlassian, Auth0, etc. Other providers and login options can be easily configured and enabled in the CueWeb. See [NextAuth.js](https://next-auth.js.org/) authentication using email, credentials and providers: https://next-auth.js.org/providers/
2. **Customizable job management dashboard:** 
   - Manage jobs with a customizable table where users can select visible columns and filter jobs based on their state (active, paused, completed).
3. **Flexible monitoring controls:** 
   - Easily un-monitor jobs across all statuses.
4. **Detailed job inspection:** 
   - View job details with pop-up windows showing layers and frames associated with each job.
5. **Frame navigation and logs access:** 
   - Navigate frames using hyperlinks that lead to dedicated pages for frame data and logs.
6. **Advanced job search functionality:** 
   - Search for jobs by show name with dropdown suggestions for matching entries.
   - Search functionality requires `show-shot-` as the prefix to reduce the number of results returned.
7. **Dark mode toggle for user preference:** 
   - Switch between light and dark modes according to user preference.
8. **Enhanced search functionality:**
   - Users can enable regex searches by appending '!' to their queries, with tooltips provided for guidance.
   - Optimized loading times using virtualization and web workers, along with loading animations for a better user experience.
   - Users can add or remove multiple jobs directly from the search results, with existing jobs highlighted in green.
9. **Enhanced security using Opencue API:**
   - CueWeb uses JWT token generation for enhanced security in authorization headers.
10. **CueWeb actions and context menu are available:**

Job actions: Unmonitor, Pause, Retry dead frames, Eat dead frames, Kill.
   - _Layer actions:_ `Kill`, `Eat`, `Retry`, `Retry dead frames`.
   - _Frame actions:_ `Retry`, `Eat`, `Kill`.
   - Menu items are disabled if the job has finished, and the context menu is always rendered on-screen.

11. **Auto-reloading of tables:**
   - All tables (jobs, layers, frames) are auto-reloaded at regular intervals to display the latest data.

## CueWeb's user interface

Upon logging in through Okta/Google/GitHub or another authentication method configured using [NextAuth.js](https://next-auth.js.org/) (Figures 1 or 2), users are welcomed by CueWeb's main dashboard, as shown in Figure 3 (light mode) or Figure 4 (dark mode).  The CueWeb main page contains a paginated table that is populated with the OpenCue jobs. 

#### Figure 1: CueWeb authentication page (light mode)
![CueWeb authentication page (light mode)](/assets/images/cueweb/figure1-auth-light.png)

#### Figure 2: CueWeb authentication page (dark mode)
![CueWeb authentication page (dark mode)](/assets/images/cueweb/figure2-auth-dark.png)

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

Figure 14 shows the `job` context menu with options to `un-monitor`, `pause`, `retry dead frames`, `eat dead frames` and `kill` jobs and Figure 15 shows the successful message after selecting `kill` a job.

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