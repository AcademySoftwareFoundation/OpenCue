---
title: "Getting Started with OpenCue"
layout: default
parent: Tutorials
nav_order: 47
linkTitle: "Getting Started with OpenCue"
date: 2025-01-29
description: >
  Learn the basics of OpenCue by setting up your first render job and monitoring its progress
---

# Getting Started with OpenCue

This tutorial will guide you through your first experience with OpenCue, from understanding the basic concepts to submitting and monitoring a simple render job.

## What You'll Learn

- Basic OpenCue concepts and terminology
- How to access the OpenCue web interface
- How to submit a simple test job
- How to monitor job progress and view results
- Basic troubleshooting techniques

## Prerequisites

- OpenCue sandbox environment running (see [Quick starts](/docs/quick-starts/))
- Basic understanding of command-line operations
- Python 3.6+ installed

## Step 1: Understanding OpenCue Components

OpenCue consists of several key components:

- **Cuebot**: The central server that manages all jobs and distributes work
- **RQD**: The daemon running on render nodes that executes jobs
- **CueGUI/CueWeb**: User interfaces for monitoring and managing jobs
- **CueSubmit**: Tool for submitting jobs to the render queue

## Step 2: Accessing the OpenCue Interface

If you're using the sandbox environment, you can access OpenCue through:

### Web Interface (CueWeb)
1. Open your browser and navigate to `http://localhost:8080`
2. You should see the OpenCue web interface with an empty job list

### Desktop Application (CueGUI)
1. If you have CueGUI installed, launch it from your terminal:
   ```bash
   cuegui
   ```

## Step 3: Your First Job Submission

Let's create a simple test job that demonstrates basic OpenCue functionality.

### Using PyOutline (Recommended for Learning)

Create a Python script called `first_job.py`:

```python
#!/usr/bin/env python3

import outline
import outline.modules.shell

# Create a new job
job = outline.Outline(
    name="my-first-job",
    shot="tutorial", 
    show="learning",
    user="student"
)

# Add a simple layer that prints frame numbers
test_layer = outline.modules.shell.Shell(
    name="test-layer",
    command=["echo", "Processing frame #IFRAME#", "&&", "sleep", "5"],
    range="1-10"
)

# Add the layer to the job
job.add_layer(test_layer)

# Submit the job
print("Submitting job:", job.get_name())
outline.cuerun.launch(job, use_pycuerun=False)
print("Job submitted successfully!")
```

Run the script:
```bash
python first_job.py
```

### Using CueSubmit GUI

1. Launch CueSubmit:
   ```bash
   cuesubmit
   ```

2. Fill in the job details:
   - **Job Name**: `my-first-job`
   - **Shot**: `tutorial`
   - **Show**: `learning` 
   - **Frame Range**: `1-10`
   - **Command**: `echo "Processing frame #IFRAME#" && sleep 5`

3. Click **Submit** to send the job to the queue

## Step 4: Monitoring Your Job

### In the Web Interface

1. Refresh the job list - you should see your job appear
2. Click on the job name to view details
3. Observe the job state changing from "Pending" to "Running" to "Finished"
4. Click on individual frames to see their status and logs

### In CueGUI

1. Your job should appear in the main job list
2. Double-click the job to see layer and frame details
3. Right-click on frames to access logs and management options

## Step 5: Understanding Job States

As your job runs, you'll see it progress through different states:

- **Pending**: Job is queued but not yet running
- **Running**: Frames are actively being processed
- **Finished**: All frames completed successfully
- **Dead**: Job encountered errors and stopped

## Step 6: Viewing Frame Logs

To see what happened during frame execution:

1. In the job details view, find a completed frame
2. Double-click the frame or right-click and select "View Log"
3. You should see the output: "Processing frame [number]"

## Step 7: Basic Troubleshooting

If your job doesn't appear or has issues:

### Check Job Submission
```bash
# List recent jobs
cueadmin -lj

# Check job details
cueadmin -lji your-job-name
```

### Check RQD Status
```bash
# List available hosts
cueadmin -lh

# Check if RQD is running
ps aux | grep rqd
```

### Common Issues

1. **Job not appearing**: Check that Cuebot is running and accessible
2. **Frames stuck in "Waiting"**: Verify RQD hosts are available
3. **Frames failing**: Check frame logs for error messages

## Next Steps

Congratulations! You've successfully:
- Submitted your first OpenCue job
- Monitored job progress through the interface
- Viewed frame logs and results

**Ready for more?** Continue with:
- [Submitting Your First Job](/docs/tutorials/submitting-first-job/) - Learn advanced submission techniques
- [Using CueGUI for Job Monitoring](/docs/tutorials/using-cuegui/) - Master the monitoring interface
- [Creating Multi-Layer Jobs](/docs/tutorials/multi-layer-jobs/) - Build complex render pipelines

## Troubleshooting Tips

- Always check the Cuebot logs if jobs aren't submitting: `tail -f /path/to/cuebot/logs/cuebot.log`
- Ensure your show exists in the database before submitting jobs
- Verify that RQD hosts are properly registered with Cuebot
- Use `cueadmin -ls` to list available shows in your system