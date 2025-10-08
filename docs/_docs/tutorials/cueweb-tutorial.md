---
title: "CueWeb Tutorial"
nav_order: 74
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

- **Header**: Navigation, theme toggle, and user menu
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

1. Click on any job name in the table
2. This opens the job details panel with tabs:
   - **Layers**: Shows render layers and their status
   - **Frames**: Individual frame information
   - **Comments**: Job notes and updates

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
   - Click on a frame number
   - Select log version from dropdown
   - View error messages or progress

2. **Retry Failed Frames**:
   - Right-click on red (failed) frames
   - Select "Retry Frame"
   - Monitor the frame as it re-enters the queue

3. **Kill Running Frames**:
   - Right-click on yellow (running) frames
   - Select "Kill Frame"
   - Use when frames are stuck or consuming too many resources

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

Customize the jobs table to show relevant information:

1. **Show/Hide Columns**:
   - Click on the "Columns" dropdown
   - Toggle checkboxes for desired columns
   
2. **Sort and Filter**:
   - Click headers to sort ascending/descending

## Real-time Monitoring

### Auto-refresh Settings

* **Refresh Interval**: CueWeb uses a fixed 5-second update interval for all tables

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

### Mobile Interface

CueWeb has basic responsive design for mobile devices:

1. **Access on Mobile**:
   - Open CueWeb URL in mobile browser
   - Interface automatically adapts to smaller screen
   - Core functionality available

2. **Mobile Best Practices**:
   - Use simplified column views
   - Focus on status and progress columns
   - Note that mobile interface is basic compared to desktop

3. **Mobile Limitations**:
   - Limited responsive design implementation
   - Detailed log viewing may be difficult
   - Complex frame operations better on desktop
   - Primarily designed for desktop use

### Mobile Monitoring

If you have a mobile device available:

1. **Access Mobile Interface**:
   - Open CueWeb on your phone/tablet
   - Note the responsive layout
   - Test basic navigation

2. **Monitor Jobs**:
   - Check job status
   - View progress indicators
   - Try pausing/resuming a job

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
