---
layout: default
title: CueWeb User Guide
parent: User Guides
nav_order: 37
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
   - **Job actions**: Un-monitor, Pause/Unpause, Retry dead frames, Eat dead frames, Kill
   - **Layer actions**: Kill, Eat, Retry, Retry dead frames
   - **Frame actions**: Retry, Eat, Kill
   - Context-aware menu items (disabled for finished jobs)

8. **Auto-reloading Tables**
   - All tables (jobs, layers, frames) auto-reload at configurable intervals
   - Loading animations for better user experience

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

![CueWeb authentication page (light mode)](/assets/images/cueweb/figure1-auth-light.png)

![CueWeb authentication page (dark mode)](/assets/images/cueweb/figure2-auth-dark.png)

**Note**: If authentication is disabled for development, you'll see a "CueWeb Home" button to access the interface directly.

### First Time Setup

When you first access CueWeb, you'll see the main dashboard:

![CueWeb main page (light mode)](/assets/images/cueweb/figure3-main-light.png)

![CueWeb main page (dark mode)](/assets/images/cueweb/figure4-main-dark.png)

- **Jobs Dashboard**: Central paginated table populated with OpenCue jobs
- **Navigation Menu**: Access to different sections
- **Theme Toggle**: Switch between light and dark modes
- **User Menu**: Authentication and settings (if enabled)

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

| Column | Description |
|--------|-------------|
| **Select** | Checkbox for multi-job selection |
| **Name** | Job identifier with show-shot-user and job name on separate lines |
| **State** | Current job state (Failing, Finished, In Progress, Dependency, Paused) |
| **Done / Total** | Succeeded frames out of total frames (e.g., "150 of 200") |
| **Started** | Job start timestamp in human-readable format |
| **Finished** | Job completion timestamp (if finished) |
| **Running** | Number of currently running frames |
| **Dead** | Number of failed frames |
| **Eaten** | Number of frames marked as completed (skipped) |
| **Wait** | Number of frames waiting to run |
| **MaxRss** | Maximum resident set size (peak memory usage) |
| **Age** | Total time since job started (HHH:MM format) |
| **Progress** | Visual progress bar showing completion percentage |
| **Pop-up** | Button to open job details panel |

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

   ![Un-monitoring selected jobs (before)](/assets/images/cueweb/figure7-unmonitor-before.png)

   ![Un-monitoring selected jobs (after)](/assets/images/cueweb/figure8-unmonitor-after.png)

### Advanced Job Operations

#### Context Menu Actions

Right-click on jobs to access the context menu with the following actions:

- **Unmonitor**: Remove job from monitoring
- **Pause/Unpause**: Pause or resume job execution
- **Retry Dead Frames**: Restart only failed frames in the job
- **Eat Dead Frames**: Mark failed frames as completed (skip)
- **Kill**: Terminate the job

**Note**: Menu items are automatically disabled if the job has finished, and the context menu is always rendered on-screen.

   ![CueWeb with job context menu open](/assets/images/cueweb/figure14-job-context-menu.png)

   ![Pop-up showing successful kill job message](/assets/images/cueweb/figure15-kill-job-success.png)

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

   ![Job search functionality](/assets/images/cueweb/figure13-job-search.png)

---

## Frame and Layer Management

### Viewing Job Details

1. Use the `Job detail button` to view the job's layers and frames

![Job detail button to open the job layers and frames](/assets/images/cueweb/job-popup-detail-button.png)

2. The job details panel opens with tabs:
   - **Layers**: Show job layers information (top datatable)
   - **Frames**: Show frames information (bottom datatable)

   ![Pop-up window layers and frames (light mode)](/assets/images/cueweb/figure9-popup-light.png)

   ![Pop-up window layers and frames (dark mode)](/assets/images/cueweb/figure10-popup-dark.png)

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
| **Progress** | Completion percentage |
| **Timeout** | Frame timeout duration (HHH:MM) |
| **Timeout LLU** | Timeout for last layer update (HHH:MM) |

#### Layer Actions

- **Kill**: Kill/stop all frames in the layer
- **Eat**: Mark layer as completed (skip)
- **Retry**: Restart all frames in the layer
- **Retry Dead Frames**: Restart only failed frames

   ![CueWeb with layer context menu open](/assets/images/cueweb/figure16-layer-context-menu.png)

   ![Pop-up showing successful retry layer message](/assets/images/cueweb/figure17-retry-layer-success.png)

### Frame Operations

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
| **Memory** | Memory usage (used memory for running, max RSS for completed) |
| **GPU Memory** | GPU memory usage (used for running, max for completed) |
| **Start Time** | Frame start timestamp in human-readable format |
| **Stop Time** | Frame completion timestamp (if finished) |

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

   ![CueWeb with frame context menu open](/assets/images/cueweb/figure18-frame-context-menu.png)

   ![Pop-up showing successful eat frame message](/assets/images/cueweb/figure19-eat-frame-success.png)

#### Frame Log Viewer

1. **View Log**: Click on the link in the frame line to open the logs
2. **Log Selection**: Choose from available log versions
3. **Auto-refresh**: Automatically update running frame logs

   ![Frame information and logs visualization (light mode)](/assets/images/cueweb/figure11-frame-logs-light.png)

   ![Frame information and logs visualization (dark mode)](/assets/images/cueweb/figure12-frame-logs-dark.png)

---

## Table Customization

### Column Management

1. **Show/Hide Columns**: Click the columns button to toggle visibility

   ![Column visibility dropdown](/assets/images/cueweb/figure5-column-visibility.png)

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

---

## Mobile and Responsive Usage

### Mobile Interface

CueWeb adapts to smaller screens:

- **Simplified Navigation**: Collapsible menu for mobile
- **Touch-friendly**: Large buttons and touch targets
- **Swipe Gestures**: Navigate between sections
- **Essential Information**: Prioritized data display

### Responsive Features

- **Adaptive Layout**: Adjusts to any screen size
- **Progressive Enhancement**: Core features work on all devices

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
