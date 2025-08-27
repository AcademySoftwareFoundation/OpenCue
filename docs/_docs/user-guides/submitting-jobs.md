---
title: "Submitting jobs"
nav_order: 23
parent: User Guides
layout: default
linkTitle: "Submitting jobs"
date: 2019-03-15
description: >
  Submit rendering and shell jobs to OpenCue from CueSubmit
---

# Submitting jobs

### Submit rendering and shell jobs to OpenCue from CueSubmit

---

This guide describes how to submit jobs to OpenCue using the stand-alone
version of CueSubmit and configure relevant rendering settings. A job is a
collection of layers, which is sent as a script to the queue to be processed
on remote cores. Each job can contain one or more layers, which are sub-jobs
in an outline script job. Each layer contains a frame range and a command to
execute.

You can select from the following pre-configured job types:

*   Blender
*   Maya
*   Nuke

Alternatively, you can submit shell commands to OpenCue for
processing on RQD rendering nodes. Your RQD rendering nodes must support
the necessary software to complete the job you are submitting otherwise
the job will fail.

## Before you begin

This guide describes submitting jobs using the OpenCue sandbox environment
running Blender. The steps for submitting jobs in a production environment
are very similar but will vary depending on the configuration choices
your OpenCue admin has made.

To learn how to install Blender and similar software in the OpenCue sandbox
environment, see
[Customizing RQD rendering hosts](/docs/other-guides/customizing-rqd/).

If you're working in a production environment, make sure your OpenCue admin
has [installed CueSubmit](/docs/getting-started/installing-cuesubmit/).

## Submitting a render job

This section of the guide uses a Blender job to illustrate submitting
a rendering job. The process for submitting Maya and Nuke jobs is very
similar.

To submit a Blender job to OpenCue:

1.  Start CueSubmit.

    > **Note**
> {: .callout .callout-info}The instructions for running
    CueSubmit vary depending on the installation method. To learn more, see
    [Installing CueSubmit](/docs/getting-started/installing-cuesubmit)
    or contact your OpenCue admin.>

1.  Enter a **Job Name**.

    The job name is an arbitrary value that you choose when creating the
    job.
    
    > **Note**
> {: .callout .callout-info}You can follow the naming convention
    for your rendering facility, as long as the job name is unique, contains
    more than 3 characters, and contains no spaces.>

1.  Select a **Show**.

    A show is a group of related jobs for OpenCue to process. Jobs you submit
    to OpenCue exist within the context of a show.

1.  Enter the name for the **Shot** to send to OpenCue.

    A shot is a series of uninterrupted frames you need to render. Choose a
    shot name that describes the shot that this job relates to.
    
    The following screenshot illustrates a completed job info form:
    
    ![CueSubmit job info form](/assets/images/cuesubmit_job_info.png)

1.  For **Job Type**, select **Blender**.

    The CueSubmit layer info dialogue updates the submission form.

1.  Enter a **Layer Name** to name the first layer in your job.

    > **Note**
> {: .callout .callout-info}Layer names must contain more than
    3 characters and contain no spaces.>
    
    Choose a layer name that describes the task the layer is performing,
    such as 'rendering' or 'compositing'.

1.  In **Blender File**, enter the location of a Blender project file
    with the `.blend` extension, such as `/tmp/rqd/shots/myproject.blend`.

1.  In **Output Path**, enter the location that your RQD rendering nodes
    can write the output of the jobs, such as `/tmp/rqd/shots/`

1.  For **Output Format**, select your desired output format, such as
    **JPEG**.

1.  In **Frame Spec**, enter the range of frames you want to process, such as
    `1-10`.

    A frame spec consists of a start time, an optional end time, a step,
    and an interleave. To add multiple ranges together, separate them
    by commas. For detailed examples of the frame spec syntax, click **?**.

1.  Optionally, select the required **Services** from the available list for
    your job. OpenCue matches jobs with machines, based on the selected
    service.
    
    The following screenshot illustrates a completed layer info form:

    ![CueSubmit Blender layer info](/assets/images/cuesubmit_blender_layer_info.png)

1.  Review the summary information in **Submission Details** to verify your
    settings, as illustrated by the following screenshot:
    
    ![CueSubmit submission details summary](/assets/images/cuesubmit_blender_submission_details.png)

1.  Optionally, to add more layers to this job, click **+**.

1.  When you're ready to submit your job, click **Submit**.

## Submitting a shell job

This section of the guide describes submitting a Blender file for rendering
as a shell job. You can submit a variety of shell jobs to OpenCue as long as
the necessary software is installed on your RQD rendering nodes.

To submit a shell job to OpenCue:

1.  Start CueSubmit.

    > **Note**
> {: .callout .callout-info}The instructions for running
    CueSubmit vary depending on the installation method. To learn more, see
    [Installing CueSubmit](/docs/getting-started/installing-cuesubmit)
    or contact your OpenCue admin.>

1.  Enter a **Job Name**.

    The job name is an arbitrary value that you choose when creating the
    job.
    
    > **Note**
> {: .callout .callout-info}You can follow the naming convention
    for your rendering facility, as long as the job name is unique, contains
    more than 3 characters, and contains no spaces.>

1.  Select a **Show**.

    A show is a group of related jobs for OpenCue to process. Jobs you submit
    to OpenCue exist within the context of a show.

1.  Enter the name for the **Shot** to send to OpenCue.

    A shot is a series of uninterrupted frames you need to render. Choose a
    shot name that describes the shot that this job relates to.
    
    The following screenshot illustrates a completed job info form:
    
    ![CueSubmit job info form](/assets/images/cuesubmit_job_info.png)

1.  Set **Job Type** to **Shell**.

1.  Enter a **Layer Name** to name the first layer in your job.

    > **Note**
> {: .callout .callout-info}Layer names must contain more than
    3 characters and contain no spaces.>
    
    Choose a layer name that describes the task the layer is performing,
    such as 'rendering' or 'compositing'.

1.  In **Command to Run**, enter the shell command you want to run to render
    the layer.

    The command depends on the rendering software you're running. You can
    specify the frame number in the command to run at render time by
    specifying the `#IFRAME#` variable. For example, to render a range of
    frames using the 3D creation suite Blender, you can specify a command
    to run similar to the following:
    
    ```bash
    /usr/local/blender/blender -b -noaudio /tmp/rqd/shots/<your-blender-file>.blend -o /tmp/rqd/shots/test-shot.##### -F JPEG -f #IFRAME#
    ```

    In this example, based on the frame padding `#####`, OpenCue writes the
    output for frame 5 on disk, as file `test-shot.00005.jpg`.

1.  In **Frame Spec**, enter the range of frames you want to process, such as
    `1-10`.

    A frame spec consists of a start time, an optional end time, a step,
    and an interleave. To add multiple ranges together, separate them
    by commas. For detailed examples of the frame spec syntax, click **?**.

1.  Optionally, select the required **Services** from the available list for
    your job. OpenCue matches jobs with machines, based on the selected
    service.
    
    The following screenshot illustrates a completed layer info form:

    ![CueSubmit shell layer info](/assets/images/cuesubmit_shell_layer_info.png)

1.  Review the summary information in **Submission Details** to verify your
    settings, as illustrated by the following screenshot:
    
    ![CueSubmit shell submission details summary](/assets/images/cuesubmit_shell_submission_details.png)

1.  Optionally, to add more layers to this job, click **+**.

1.  When you're ready to submit your job, click **Submit**.

## What's next?

-   [Monitoring your jobs](/docs/user-guides/monitoring-your-jobs/)
 
