---
title: "Submitting Your First Job"
layout: default
parent: Tutorials
nav_order: 48
linkTitle: "Submitting Your First Job"
date: 2025-01-29
description: >
  A detailed walkthrough of creating and submitting render jobs using both CueSubmit GUI and PyOutline scripts
---

# Submitting Your First Job

This tutorial provides a comprehensive guide to job submission in OpenCue, covering both GUI and programmatic approaches. You'll learn the anatomy of OpenCue jobs and master different submission methods.

## What You'll Learn

- Understanding job structure (jobs, layers, frames)
- Using CueSubmit GUI for job submission
- Writing PyOutline scripts for automated submission
- Job configuration and parameter management
- Frame range and chunking strategies
- Job dependencies and priorities

## Prerequisites

- Completed [Getting Started with OpenCue](/docs/tutorials/getting-started-tutorial/)
- OpenCue environment running with at least one RQD host
- Python 3.6+ with OpenCue libraries installed

## Understanding Job Structure

### OpenCue Job Hierarchy

```
Job
├── Layer 1 (e.g., Render)
│   ├── Frame 1
│   ├── Frame 2
│   └── Frame N
├── Layer 2 (e.g., Composite)
│   ├── Frame 1
│   └── Frame N
└── Layer N
```

### Key Concepts

- **Job**: Top-level container with metadata (show, shot, user)
- **Layer**: A specific task within a job (render, composite, etc.)
- **Frame**: Individual work units within a layer
- **Frame Range**: Specification of which frames to process (e.g., "1-100")

## Method 1: Using CueSubmit GUI

### Basic Job Submission

1. **Launch CueSubmit**:
   ```bash
   cuesubmit
   ```

2. **Fill in Job Information**:
   - **Job Name**: `render-tutorial-v001`
   - **Shot**: `shot010`
   - **Show**: `demo-project`
   - **User**: Your username
   - **Frame Range**: `1-24`

3. **Configure the Render Command**:
   ```bash
   echo "Rendering frame #IFRAME# for shot010" && sleep 3
   ```

4. **Set Resource Requirements**:
   - **Min Cores**: 1
   - **Memory**: 1GB
   - **Services**: Leave default

5. **Submit the Job**:
   Click the **Submit** button

### Advanced CueSubmit Configuration

#### Creating Custom Job Types

CueSubmit uses YAML configuration files to define job types. Create a custom config:

```yaml
# ~/.config/opencue/cuesubmit.yaml
JOB_TYPES:
  BLENDER:
    RENDER_CMD: "/usr/local/blender/blender"
    PARAMETERS:
      - name: "blend_file"
        type: "file"
        label: "Blend File"
        required: true
      - name: "output_path"
        type: "directory" 
        label: "Output Directory"
        required: true
```

#### Using Environment Variables

Set up environment variables for your render:

```yaml
ENVIRONMENT:
  BLENDER_USER_SCRIPTS: "/shared/scripts"
  RENDER_ROOT: "/shared/renders"
  PYTHONPATH: "/shared/tools/python"
```

## Method 2: PyOutline Scripting

### Basic PyOutline Job

Create `render_job.py`:

```python
#!/usr/bin/env python3

import outline
import outline.modules.shell
import os

def create_render_job():
    # Create the job outline
    job = outline.Outline(
        name="blender-render-v001",
        shot="shot010",
        show="demo-project", 
        user=os.getenv("USER", "student")
    )
    
    # Set job-level properties
    job.set_frame_range("1-24")
    job.set_min_cores(1)
    job.set_max_cores(4)
    
    # Create a render layer
    render_layer = outline.modules.shell.Shell(
        name="render",
        command=[
            "/usr/local/blender/blender",
            "-b", "/shared/scenes/demo.blend",
            "-o", "/shared/output/shot010/frame_####.png",
            "-f", "#IFRAME#"
        ],
        range="1-24"
    )
    
    # Set layer-specific resources
    render_layer.set_min_cores(1)
    render_layer.set_min_memory(2048)  # 2GB
    render_layer.set_service("blender")
    
    # Add layer to job
    job.add_layer(render_layer)
    
    return job

if __name__ == "__main__":
    job = create_render_job()
    print(f"Submitting job: {job.get_name()}")
    
    # Submit the job
    outline.cuerun.launch(job, use_pycuerun=False)
    print("Job submitted successfully!")
```

### Multi-Layer Job with Dependencies

Create `complex_job.py`:

```python
#!/usr/bin/env python3

import outline
import outline.modules.shell

def create_complex_job():
    job = outline.Outline(
        name="complex-pipeline-v001",
        shot="shot010",
        show="demo-project",
        user="student"
    )
    
    # Pre-processing layer
    preprocess = outline.modules.shell.Shell(
        name="preprocess",
        command=[
            "python", "/shared/scripts/preprocess.py",
            "--input", "/shared/input/shot010",
            "--output", "/shared/cache/shot010",
            "--frame", "#IFRAME#"
        ],
        range="1-24"
    )
    
    # Main render layer (depends on preprocess)
    render = outline.modules.shell.Shell(
        name="render", 
        command=[
            "/usr/local/blender/blender",
            "-b", "/shared/scenes/shot010.blend",
            "-o", "/shared/output/shot010/render_####.exr",
            "-f", "#IFRAME#"
        ],
        range="1-24"
    )
    
    # Composite layer (depends on render)
    composite = outline.modules.shell.Shell(
        name="composite",
        command=[
            "nuke", "-x", "/shared/scripts/comp.nk",
            "--frame", "#IFRAME#"
        ],
        range="1-24"
    )
    
    # Set up dependencies
    render.depend_on(preprocess)
    composite.depend_on(render)
    
    # Add all layers to job
    job.add_layer(preprocess)
    job.add_layer(render) 
    job.add_layer(composite)
    
    return job

if __name__ == "__main__":
    job = create_complex_job()
    outline.cuerun.launch(job, use_pycuerun=False)
```

### Frame Chunking Strategy

For jobs with many small frames, use chunking:

```python
# Process 10 frames per task
chunked_layer = outline.modules.shell.Shell(
    name="batch-render",
    command=[
        "python", "/shared/scripts/batch_render.py",
        "--start", "#IFRAME#",
        "--end", "#IFRAME_END#",
        "--output", "/shared/output/"
    ],
    range="1-1000",
    chunk=10  # Process 10 frames per task
)
```

## Method 3: CueAdmin Command Line

### Direct Job Submission

You can also submit jobs using cueadmin:

```bash
# Submit a simple shell job
cueadmin -create-job \
  --name "cli-test-job" \
  --show "demo-project" \
  --shot "shot010" \
  --user "$USER" \
  --command "echo Processing frame #IFRAME#" \
  --range "1-10"
```

## Job Configuration Best Practices

### Resource Management

```python
# Set appropriate resource requirements
layer.set_min_cores(1)           # Minimum cores needed
layer.set_max_cores(8)           # Maximum cores to use
layer.set_min_memory(2048)       # Minimum RAM in MB
layer.set_service("maya")        # Required service tag
```

### Environment Variables

```python
# Set environment variables for the job
job.set_env("MAYA_LOCATION", "/usr/autodesk/maya2024")
job.set_env("ARNOLD_LICENSE", "/shared/licenses/arnold")
job.set_env("PYTHONPATH", "/shared/tools/python:$PYTHONPATH")
```

### Job Priorities

```python
# Set job priority (higher number = higher priority)
job.set_priority(100)  # Default is 50
```

## Testing Your Jobs

### Dry Run Testing

Before submitting to the full farm:

```python
# Test with a single frame first
test_layer = outline.modules.shell.Shell(
    name="test-render",
    command=your_render_command,
    range="1-1"  # Just one frame
)
```

### Local Testing

Test your commands locally before submission:

```bash
# Test the exact command that will run
/usr/local/blender/blender -b scene.blend -o output_####.png -f 1
```

## Common Job Submission Patterns

### Maya Batch Render

```python
maya_render = outline.modules.shell.Shell(
    name="maya-render",
    command=[
        "maya", "-batch", 
        "-file", "/shared/scenes/shot010.ma",
        "-command", "python(\"import maya.mel as mel; mel.eval('render -s #IFRAME# -e #IFRAME#')\")"
    ],
    range="1-120"
)
```

### Nuke Render

```python
nuke_render = outline.modules.shell.Shell(
    name="nuke-render", 
    command=[
        "nuke", "-x", "/shared/scripts/shot010.nk",
        "-F", "#IFRAME#-#IFRAME#"
    ],
    range="1001-1120"
)
```

### Custom Python Script

```python
python_task = outline.modules.shell.Shell(
    name="python-processing",
    command=[
        "python", "/shared/scripts/process_frame.py",
        "--frame", "#IFRAME#",
        "--input", "/shared/input/",
        "--output", "/shared/output/"
    ],
    range="1-100"
)
```

## Troubleshooting Job Submission

### Common Issues

1. **Job doesn't appear in queue**:
   ```bash
   # Check if job was submitted
   cueadmin -lj | grep your-job-name
   ```

2. **Frames stuck in "Waiting" state**:
   ```bash
   # Check available hosts
   cueadmin -lh
   
   # Check host services
   cueadmin -lh -alloc your-allocation
   ```

3. **Permission errors**:
   ```bash
   # Verify file permissions
   ls -la /path/to/your/files
   
   # Check OpenCue configuration
   cat ~/.config/opencue/opencue.yaml
   ```

### Debugging Commands

```bash
# List recent jobs
cueadmin -lj

# Show job details
cueadmin -lji your-job-name

# List running processes
cueadmin -lp

# Check frame logs
cueadmin -ll your-job-name
```

## Next Steps

You've now learned multiple ways to submit jobs to OpenCue:
- GUI submission with CueSubmit
- Programmatic submission with PyOutline
- Command-line submission with CueAdmin
- Job configuration and resource management
- Multi-layer jobs with dependencies

**Continue learning with**:
- [Using CueGUI for Job Monitoring](/docs/tutorials/using-cuegui/) - Master job monitoring
- [Managing Jobs and Frames](/docs/tutorials/managing-jobs-frames/) - Advanced job management
- [Creating Multi-Layer Jobs](/docs/tutorials/multi-layer-jobs/) - Complex pipeline workflows