---
title: "Monitoring your jobs"
linkTitle: "Monitoring your jobs"
date: 2019-05-09
weight: 2
description: >
  Monitor your OpenCue rendering jobs from CueGUI
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

{{% alert title="Note" color="info"%}}You can review the logs for a job,
either in the CueGUI app or in an external text editor. To view job logs
in an external text editor, set your `EDITOR` environment variable.
Alternatively, you can set the `Constants.DEFAULT_EDITOR` variable to
configure an external text editor.{{% /alert %}}

Before you start to monitor jobs in CueGUI, complete the following steps:
    
1.  Start CueGUI.

    The instructions for running
    Cuetopia vary depending on the installation method. To learn more, see
    [Installing CueGUI](/docs/getting-started/installing-cuegui/)
    or contact your OpenCue admin.
    
    After CueGUI loads for the first time, you can expect to find one or more
    windows. The following screenshot illustrates the default Cuetopia window
    you run to follow this guide:
    
    ![Cuetopia default view](/docs/images/cuetopia_default.png)

1.  Click **Window** > **Raise Window: CueCommander**.

    The following screenshot illustrates the default CueCommander window:
    
    ![CueCommander default view](/docs/images/cuecommander_default.png)
    
    You don't typically run CueCommander to monitor individual
	OpenCue jobs and you don't need it to follow this guide.

1.  If it's open, close the CueCommander window.

## Monitoring jobs

To monitor a job:

1.  Enter a username or [show](/docs/concepts/glossary/#show) name in the
    Monitor Jobs **Load** search field:
    
    ![Search for jobs by show name or username, or auto-load your
    jobs.](/docs/images/cuegui_search.png)
    
    To autoload your own jobs, check the **Autoload Mine** box.

1.  Click **Load:**.
    
    Cuetopia displays a list of jobs in the search results.
    
    ![Monitoring the status of OpenCue
    jobs](/docs/images/cuetopia_monitor_job.png)

1.  Double-click the name of a job to view the details of the job in the
    Monitor Job Details plugin.
    
    Cuetopia displays a list of the layers and frames associated with the job
    and their status. In the following example, Cuetopia is displaying the
    summary for a job consisting of a single layer called *render*, which
    contains 101 frames:
    
    ![Monitoring the status of individual job layers and
    frames](/docs/images/cuetopia_monitor_layer.png)

1.  Double-click a frame to view the associated logs.
    
    Cuetopia displays the logs for the frame in the LogView view:
    
    ![Viewing the logs associated with a
    frame](/docs/images/cuetopia_monitor_logs.png)

## Un-monitoring jobs

You can unmonitor all or some of the jobs in the Monitor Jobs plugin:

![Unmonitor all or some of the jobs listed in the Monitor Jobs
plugin](/docs/images/cuetopia_unmonitor_jobs.png)

*   To unmonitor all finished jobs, click **Finished**.
*   To unmonitor all jobs, click **All**.
*   To unmonitor all selected jobs:
    1.  Select the jobs you want to unmonitor in the Monitor Jobs plugin.
    1.  Click the following button:

        ![Unmonitor selected
        jobs](/docs/images/cuetopia_unmonitor_selected.png)

## What's next?

-   [Troubleshooting rendering](/docs/other-guides/troubleshooting-rendering)

