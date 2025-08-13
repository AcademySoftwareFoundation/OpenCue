---
title: "Monitoring jobs"
nav_order: 24
parent: User Guides
layout: default
linkTitle: "Monitoring your jobs"
date: 2019-05-09
description: >
  Monitor your OpenCue rendering jobs from CueGUI
---

# Monitoring jobs

### Monitor your OpenCue rendering jobs from CueGUI

---

This guide describes how to monitor your OpenCue jobs from the CueGUI app
and configure plugins for viewing job details.

After you submit a job to OpenCue, you can monitor the progress of the
individual frames and layers in the job from the CueGUI app on your
workstation. CueGUI supports the following *views* to monitor and manage
job status:

*   *Cuetopia* includes plugins for monitoring jobs and individual job
    details.
*   *CueCommander* includes plugins for monitoring your OpenCue system.
    System administrators typically run CueCommander to monitor
    and manage OpenCue infrastructure, such as rendering hosts.
*   *Other* includes plugins for viewing logs and attributes.

This guide explains how to use the Cuetopia view to monitor jobs. To
learn more about the features available in CueGUI, see
[CueGUI reference](/docs/reference/cuegui-reference/).

## Before you begin

Make sure you are familiar with the steps for
[submitting jobs](/docs/user-guides/submitting-jobs/).

You also need to configure CueGUI.

### Configuring CueGUI

> **Note**
> {: .callout .callout-info}You can review the logs for a job,
either in the CueGUI app or in an external text editor. To view job logs
in an external text editor, set your `EDITOR` environment variable.
Alternatively, you can set the `Constants.DEFAULT_EDITOR` variable to
configure an external text editor.>

Before you start to monitor jobs in CueGUI, complete the following steps:
    
1.  Start CueGUI.

    The instructions for running
    Cuetopia vary depending on the installation method. To learn more, see
    [Installing CueGUI](/docs/getting-started/installing-cuegui/)
    or contact your OpenCue admin.
    
    After CueGUI loads for the first time, you can expect to find one or more
    windows. The following screenshot illustrates the default Cuetopia window
    you run to follow this guide:
    
    ![Cuetopia default view](/assets/images/cuetopia_default.png)

1.  Click **Window** > **Raise Window: CueCommander**.

    The following screenshot illustrates the default CueCommander window:
    
    ![CueCommander default view](/assets/images/cuecommander_default.png)
    
    You don't typically run CueCommander to monitor individual
	OpenCue jobs and you don't need it to follow this guide.

1.  If it's open, close the CueCommander window.

## Monitoring jobs

To monitor a job:

1.  Enter a username or [show](/docs/concepts/glossary/#show) name in the
    Monitor Jobs **Load** search field:
    
    ![Search for jobs by show name or username, or auto-load your
    jobs.](/assets/images/cuegui_search.png)
    
    To autoload your own jobs, check the **Autoload Mine** box.

1.  Click **Load:**.
    
    Cuetopia displays a list of jobs in the search results.
    
    ![Monitoring the status of OpenCue
    jobs](/assets/images/cuetopia_monitor_job.png)

1.  Double-click the name of a job to view the details of the job in the
    Monitor Job Details plugin.
    
    Cuetopia displays a list of the layers and frames associated with the job
    and their status. In the following example, Cuetopia is displaying the
    summary for a job consisting of a single layer called *render*, which
    contains 101 frames:
    
    ![Monitoring the status of individual job layers and
    frames](/assets/images/cuetopia_monitor_layer.png)

1.  Double-click a frame to view the associated logs.
    
    Cuetopia displays the logs for the frame in the LogView view:
    
    ![Viewing the logs associated with a
    frame](/assets/images/cuetopia_monitor_logs.png)

## Un-monitoring jobs

You can unmonitor all or some of the jobs in the Monitor Jobs plugin:

![Unmonitor all or some of the jobs listed in the Monitor Jobs
plugin](/assets/images/cuetopia_unmonitor_jobs.png)

*   To unmonitor all finished jobs, click **Finished**.
*   To unmonitor all jobs, click **All**.
*   To unmonitor all selected jobs:
    1.  Select the jobs you want to unmonitor in the Monitor Jobs plugin.
    1.  Click the following button:

        ![Unmonitor selected
        jobs](/assets/images/cuetopia_unmonitor_selected.png)

## Monitoring Hosts with CueCommander

System administrators can use CueCommander to monitor and manage rendering hosts in the OpenCue system. The **Monitor Hosts** plugin provides comprehensive host monitoring capabilities.

### Host Filtering Options

The Monitor Hosts interface includes several filtering options to help you find specific hosts:

- **Host Name Filter**: Search for hosts by name using regex patterns
- **Filter Allocation**: Filter hosts by their allocation assignments
- **Filter HardwareState**: Show hosts by hardware state (UP, DOWN, REBOOT, etc.)  
- **Filter LockState**: Filter by lock state (OPEN, LOCKED, NIMBY_LOCKED)
- **Filter OS**: Filter hosts by operating system

### Using the OS Filter

The OS filter allows you to filter hosts based on their operating system:

1. In the CueCommander Monitor Hosts view, click the **Filter OS** dropdown button
2. The filter initially shows "Not Loaded" until hosts are loaded into the view
3. Once hosts are loaded, select one or more operating systems from the dynamically populated list:
   - Linux
   - Windows  
   - macOS
   - Other OS values detected from your hosts
4. The host list updates to show only hosts matching the selected OS values
5. Use the **Clear** option to remove all OS filters

![Monitor Hosts with OS Filter](/assets/images/cuegui/cuecommander_monitor_os_filter.png)

The OS filter list dynamically updates based on the operating systems detected in your host environment. When you first open CueCommander, the filter displays "Not Loaded" to indicate that host data hasn't been retrieved yet. Once hosts are loaded, the filter automatically populates with the actual OS values found in your system.

### Host Management

From the Monitor Hosts view, you can:

- View detailed host information including CPU, memory, and GPU usage
- Monitor host states and connectivity
- Lock or unlock hosts for maintenance
- Reboot hosts when needed
- Manage host allocations and tags

## What's next?

-   [Troubleshooting rendering](/docs/other-guides/troubleshooting-rendering)

