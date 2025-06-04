---
title: "CueGUI app"
linkTitle: "CueGUI app"
date: 2019-02-22
weight: 1
description: >
  Interact with CueGUI
---

This page describes the main functions of CueGUI, the OpenCue graphical user
interface for artists.

Within the *Monitor Jobs* view, there are two main sections. The top section
shows loaded jobs. Double-clicking on a job populates the bottom section with
the job details. These details are broken out by layers and frames. Hovering
over any of the column headers displays an explanation for the column.

The following screenshot displays the CueGUI *Monitor Jobs* view:

![CueGUI Monitor Jobs view](/docs/images/cuegui_monitor_jobs.png)

## Booking to your local workstation

Booking to your local machine is a useful way to fast-track a render or run
quick tests. You can book to your local machine from the *Assign Local Cores*
dialog. To launch the dialog, right-click on a job in the *Monitor Jobs* view
and select **Use local cores...**.

The following screenshot displays the CueGUI *Assign Local Cores* dialog:

![CueGUI Assign Local Cores dialog](/docs/images/cuegui_use_local.png)

## Viewing logs

To view the log for a frame, double-click on the frame.

To open the log in an external text editor, right-click on the frame and select
**View Log**.

To configure the external text editor, update the value of your `EDITOR`
environment variable. `cuegui/Constants.py` also defines a default editor if the
value of the `EDITOR` variable isn't set.

## Managing frames

To manage frames, select one of the following:

*   **Retry** - Retrying a frame stops rendering and retries the frame on
    another proc.
*   **Eat** - Eating a frame stops rendering and doesn't try to continue
    processing the frame.
*   **Kill** - Killing a frame stops rendering and books to another proc.

## Rendering and staggering frames

To reorder the way frames are rendered, right-click on either the job or the
layer and select **Reorder Frames**:

1.  Select the frame range to be reordered.
1.  Select the order: First, Last, Reverse.

To stagger frames, right-click on either the job or the layer and select
**Stagger Frames**:

1.  Select the frame range to be staggered.
1.  Select the increment to be staggered.

## Previewing frames

To preview the output of a running frame, right-click on the frame and select
either **Preview Main** or **Preview All**:

*   Preview Main - Previews the primary output of an Arnold render.
*   Preview All - Previews all the Arbitrary Output Variables (AOV) of an Arnold
    render.

## Leaving comments on jobs

You can add and manage comments for individual jobs from the *Comments* dialog.
To open the dialog right-click on a job in the *Monitor Jobs* view and select
**Comments...**.

The following screenshot displays the CueGUI *Comments* dialog:

![CueGUI Comments dialog](/docs/images/cuegui_comments.png)

## Searching for jobs

In the top-left there is a search box to load jobs:

![CueGUI search box](/docs/images/cuegui_search.png)

You can perform the following tasks from the search box:

*   To display a list of all the running jobs for a shot, type in the shot name.
*   To display a list of all of a user's jobs, type in a username.
*   To autoload your own jobs, check the **Autoload Mine** box.

## Managing hosts

To view and manage available render machines, click ***Views/Plugins** >
**Cuecommander** and select the **Monitor Host** plugin. This view displays a
list of render *Hosts* and a list of active *Procs*.

To manage a render host, right-click on the host name and select one of the
available actions. Some of the common actions include:

*   Restarting the host
*   Changing the tags on the host
*   Changing the allocation associated with the host
*   Locking/Unlocking the host

## Managing services

To edit and add services to OpenCue:

1.  Click **Views/Plugins** > **Services** and select the **Services** plugin.

    From this view, you can add or select a service to edit.

1.  Select a service from the list on the left.

    You can modify the CPU, memory, and GPU requirements. You can also define
    the *tags* associated with this service.

1.  Click **Save** to push your changes to Cuebot.
