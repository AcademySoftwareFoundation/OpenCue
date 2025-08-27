---
title: "Creating Multi-Layer Jobs"
layout: default
parent: Tutorials
nav_order: 51
linkTitle: "Creating Multi-Layer Jobs"
date: 2025-01-29
description: >
  Build complex rendering pipelines with multiple dependent layers using PyOutline
---

# Creating Multi-Layer Jobs

This tutorial teaches you how to create sophisticated multi-layer jobs in OpenCue, enabling complex rendering pipelines with dependencies, parallel processing, and efficient resource utilization.

## What You'll Learn

- Multi-layer job architecture and design patterns
- Layer dependency strategies and implementation
- Parallel and sequential processing workflows
- Resource optimization across layers
- Error handling and recovery in complex jobs
- Real-world pipeline examples

## Prerequisites

- Completed [Submitting Your First Job](/docs/tutorials/submitting-first-job/)
- Understanding of [Managing Jobs and Frames](/docs/tutorials/managing-jobs-frames/)
- PyOutline installed and configured
- Access to OpenCue environment

## Multi-Layer Job Architecture

### Understanding Layer Relationships

```
Complex Render Pipeline:
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Preprocess    │───▶│     Render      │───▶│   Composite     │
│   (Frames 1-N)  │    │   (Frames 1-N)  │    │  (Frames 1-N)   │ 
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  Cache Assets   │    │   FX Simulation │    │   QC Review     │
│   (Once only)   │    │  (Frames 1-N)   │    │  (Frames 1-N)   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### Layer Types and Patterns

1. **Preprocessing Layers**: Data preparation, asset processing
2. **Parallel Layers**: Independent processing (multiple render layers)
3. **Sequential Layers**: Frame-dependent processing
4. **Cleanup Layers**: Post-processing, delivery, archival

## Basic Multi-Layer Job

### Simple Sequential Pipeline

```python
#!/usr/bin/env python3

import outline
import outline.modules.shell

def create_basic_pipeline():
    """Create a simple 3-layer sequential pipeline"""
    
    job = outline.Outline(
        name="sequential-pipeline-v001",
        shot="shot010",
        show="demo-project", 
        user="artist01"
    )
    
    # Layer 1: Asset preparation
    prep_layer = outline.modules.shell.Shell(
        name="asset-prep",
        command=[
            "python", "/shared/scripts/prep_assets.py",
            "--shot", "shot010",
            "--frame", "#IFRAME#",
            "--output", "/shared/cache/shot010/"
        ],
        range="1-100"
    )
    prep_layer.set_min_cores(1)
    prep_layer.set_min_memory(2048)
    prep_layer.set_service("python")
    
    # Layer 2: Main render (depends on prep)
    render_layer = outline.modules.shell.Shell(
        name="beauty-render",
        command=[
            "/usr/local/blender/blender",
            "-b", "/shared/scenes/shot010.blend",
            "-o", "/shared/renders/shot010/beauty_####.exr",
            "-f", "#IFRAME#"
        ],
        range="1-100"
    )
    render_layer.set_min_cores(4)
    render_layer.set_min_memory(8192)
    render_layer.set_service("blender")
    render_layer.depend_on(prep_layer)  # Wait for asset prep
    
    # Layer 3: Composite (depends on render)
    comp_layer = outline.modules.shell.Shell(
        name="composite",
        command=[
            "nuke", "-x", "/shared/scripts/shot010_comp.nk",
            "--frame-range", "#IFRAME#-#IFRAME#"
        ], 
        range="1-100"
    )
    comp_layer.set_min_cores(2)
    comp_layer.set_min_memory(4096)
    comp_layer.set_service("nuke")
    comp_layer.depend_on(render_layer)  # Wait for render
    
    # Add layers to job
    job.add_layer(prep_layer)
    job.add_layer(render_layer)
    job.add_layer(comp_layer)
    
    return job

if __name__ == "__main__":
    job = create_basic_pipeline()
    outline.cuerun.launch(job, use_pycuerun=False)
    print(f"Submitted sequential pipeline: {job.get_name()}")
```

## Advanced Dependency Patterns

### Parallel Processing with Convergence

```python
def create_parallel_pipeline():
    """Multiple parallel layers converging to final composite"""
    
    job = outline.Outline(
        name="parallel-render-v001",
        shot="shot010", 
        show="demo-project",
        user="artist01"
    )
    
    # Shared preparation layer
    prep_layer = outline.modules.shell.Shell(
        name="scene-prep",
        command=["python", "/shared/scripts/scene_prep.py", "--shot", "shot010"],
        range="1-1"  # Single task
    )
    
    # Multiple parallel render layers
    beauty_layer = outline.modules.shell.Shell(
        name="beauty-pass",
        command=["/usr/local/blender/blender", "-b", "scene.blend", 
                "-o", "/shared/renders/beauty_####.exr", "-f", "#IFRAME#"],
        range="1-100"
    )
    beauty_layer.depend_on(prep_layer)
    
    shadow_layer = outline.modules.shell.Shell(
        name="shadow-pass", 
        command=["/usr/local/blender/blender", "-b", "scene.blend",
                "-o", "/shared/renders/shadow_####.exr", "-f", "#IFRAME#"],
        range="1-100"
    )
    shadow_layer.depend_on(prep_layer)
    
    reflection_layer = outline.modules.shell.Shell(
        name="reflection-pass",
        command=["/usr/local/blender/blender", "-b", "scene.blend",
                "-o", "/shared/renders/reflection_####.exr", "-f", "#IFRAME#"],
        range="1-100"
    )
    reflection_layer.depend_on(prep_layer)
    
    # Final composite waits for all render passes
    final_comp = outline.modules.shell.Shell(
        name="final-composite",
        command=["nuke", "-x", "/shared/scripts/final_comp.nk", 
                "--frame", "#IFRAME#"],
        range="1-100"
    )
    final_comp.depend_on(beauty_layer)
    final_comp.depend_on(shadow_layer) 
    final_comp.depend_on(reflection_layer)
    
    # Add all layers
    job.add_layer(prep_layer)
    job.add_layer(beauty_layer)
    job.add_layer(shadow_layer)
    job.add_layer(reflection_layer)
    job.add_layer(final_comp)
    
    return job
```

### Frame-by-Frame Dependencies

```python
def create_frame_dependent_pipeline():
    """Pipeline where each frame depends on previous frame completion"""
    
    job = outline.Outline(
        name="frame-dependent-v001",
        shot="shot010",
        show="demo-project",
        user="artist01"
    )
    
    # Simulation layer - each frame depends on previous
    simulation_layer = outline.modules.shell.Shell(
        name="fluid-simulation",
        command=[
            "houdini", "-c", 
            "python /shared/scripts/fluid_sim.py --frame #IFRAME# --input /shared/cache/"
        ],
        range="1-240"
    )
    
    # Cache layer - waits for simulation on frame-by-frame basis
    cache_layer = outline.modules.shell.Shell(
        name="sim-cache",
        command=[
            "python", "/shared/scripts/cache_sim.py",
            "--frame", "#IFRAME#",
            "--input", "/shared/sim/",
            "--output", "/shared/cache/"
        ],
        range="1-240"
    )
    cache_layer.depend_on(simulation_layer, 
                         depend_type=outline.depend.DependType.FRAME_BY_FRAME)
    
    # Render layer - can start as soon as cache frames are available
    render_layer = outline.modules.shell.Shell(
        name="render-with-sim",
        command=[
            "/usr/local/blender/blender", "-b", "scene.blend",
            "--python-expr", 
            "import bpy; bpy.context.scene.frame_set(#IFRAME#); bpy.ops.render.render()",
            "-o", "/shared/renders/final_####.exr"
        ],
        range="1-240"
    )
    render_layer.depend_on(cache_layer,
                          depend_type=outline.depend.DependType.FRAME_BY_FRAME)
    
    job.add_layer(simulation_layer)
    job.add_layer(cache_layer)
    job.add_layer(render_layer)
    
    return job
```

## Resource Optimization Strategies

### Layer-Specific Resource Allocation

```python
def optimize_layer_resources(job):
    """Apply resource optimization based on layer types"""
    
    for layer in job.get_layers():
        layer_name = layer.get_name().lower()
        
        if "prep" in layer_name or "cache" in layer_name:
            # I/O intensive tasks
            layer.set_min_cores(1)
            layer.set_max_cores(2)
            layer.set_min_memory(1024)
            
        elif "render" in layer_name:
            # CPU intensive tasks
            layer.set_min_cores(4)
            layer.set_max_cores(16)
            layer.set_min_memory(4096)
            
        elif "simulation" in layer_name:
            # Memory and CPU intensive
            layer.set_min_cores(8)
            layer.set_max_cores(32)
            layer.set_min_memory(16384)
            
        elif "composite" in layer_name:
            # Moderate resource needs
            layer.set_min_cores(2)
            layer.set_max_cores(8)
            layer.set_min_memory(2048)
```

### Dynamic Chunking Strategy

```python
def apply_smart_chunking(layer, total_frames):
    """Apply chunking based on layer type and frame count"""
    
    layer_name = layer.get_name().lower()
    
    if "simulation" in layer_name:
        # Simulations usually can't be chunked
        layer.set_chunk(1)
        
    elif "render" in layer_name:
        # Renders work well with small chunks
        if total_frames > 100:
            layer.set_chunk(1)
        else:
            layer.set_chunk(5)
            
    elif "composite" in layer_name:
        # Composites can handle larger chunks
        chunk_size = max(1, min(10, total_frames // 20))
        layer.set_chunk(chunk_size)
```

## Error Handling and Recovery

### Robust Pipeline Design

```python
def create_fault_tolerant_pipeline():
    """Pipeline with error handling and recovery mechanisms"""
    
    job = outline.Outline(
        name="fault-tolerant-v001",
        shot="shot010",
        show="demo-project",
        user="artist01"
    )
    
    # Validation layer - checks prerequisites
    validation_layer = outline.modules.shell.Shell(
        name="validate-inputs",
        command=[
            "python", "/shared/scripts/validate_inputs.py",
            "--shot", "shot010",
            "--check-assets", "--check-scene", "--check-textures"
        ],
        range="1-1"
    )
    
    # Main processing with error handling
    main_layer = outline.modules.shell.Shell(
        name="main-render",
        command=[
            "timeout", "3600",  # 1 hour timeout
            "python", "/shared/scripts/robust_render.py",
            "--frame", "#IFRAME#",
            "--max-retries", "3",
            "--fallback-quality", "draft"
        ],
        range="1-100"
    )
    main_layer.depend_on(validation_layer)
    main_layer.set_retry_count(3)  # Automatic retries
    
    # Verification layer - checks outputs
    verify_layer = outline.modules.shell.Shell(
        name="verify-outputs",
        command=[
            "python", "/shared/scripts/verify_frames.py",
            "--frame", "#IFRAME#",
            "--input", "/shared/renders/",
            "--report", "/shared/reports/frame_#IFRAME#_report.json"
        ],
        range="1-100"
    )
    verify_layer.depend_on(main_layer, 
                          depend_type=outline.depend.DependType.FRAME_BY_FRAME)
    
    # Cleanup layer - runs regardless of main success/failure
    cleanup_layer = outline.modules.shell.Shell(
        name="cleanup-temp",
        command=[
            "python", "/shared/scripts/cleanup_temp.py",
            "--shot", "shot010",
            "--keep-days", "7"
        ],
        range="1-1"
    )
    # Cleanup runs when main layer finishes (success or failure)
    cleanup_layer.depend_on(main_layer,
                           depend_type=outline.depend.DependType.LAYER_ON_LAYER)
    
    job.add_layer(validation_layer)
    job.add_layer(main_layer)
    job.add_layer(verify_layer)
    job.add_layer(cleanup_layer)
    
    return job
```

## Real-World Pipeline Examples

### VFX Shot Pipeline

```python
def create_vfx_shot_pipeline(shot_name, frame_range):
    """Complete VFX shot pipeline with all departments"""
    
    job = outline.Outline(
        name=f"vfx-{shot_name}-v001",
        shot=shot_name,
        show="big-movie",
        user="vfx-supervisor"
    )
    
    # Asset preparation
    asset_prep = outline.modules.shell.Shell(
        name="asset-preparation",
        command=[
            "python", "/shared/pipeline/prep_shot_assets.py",
            "--shot", shot_name,
            "--publish-version", "latest"
        ],
        range="1-1"
    )
    
    # Layout department
    layout_layer = outline.modules.shell.Shell(
        name="layout-render",
        command=[
            "maya", "-batch", "-file", f"/shared/scenes/{shot_name}_layout.ma",
            "-command", f"python(\"renderFrame({frame_range})\")"
        ],
        range=frame_range
    )
    layout_layer.depend_on(asset_prep)
    layout_layer.set_service("maya2024")
    
    # Animation department
    animation_layer = outline.modules.shell.Shell(
        name="animation-render",
        command=[
            "maya", "-batch", "-file", f"/shared/scenes/{shot_name}_anim.ma",
            "-command", "python(\"renderAnimationFrame()\")"
        ],
        range=frame_range
    )
    animation_layer.depend_on(layout_layer)
    animation_layer.set_service("maya2024")
    
    # FX simulation (parallel with animation review)
    fx_sim_layer = outline.modules.shell.Shell(
        name="fx-simulation",
        command=[
            "houdini", "-c",
            f"python /shared/fx/scripts/run_sim.py --shot {shot_name} --frame #IFRAME#"
        ],
        range=frame_range
    )
    fx_sim_layer.depend_on(animation_layer)
    fx_sim_layer.set_service("houdini")
    fx_sim_layer.set_min_cores(16)
    fx_sim_layer.set_min_memory(32768)
    
    # Lighting (waits for animation and fx)
    lighting_layer = outline.modules.shell.Shell(
        name="lighting-render",
        command=[
            "maya", "-batch", "-file", f"/shared/scenes/{shot_name}_lighting.ma",
            "-command", "python(\"renderLightingFrame()\")"
        ],
        range=frame_range
    )
    lighting_layer.depend_on(animation_layer)
    lighting_layer.depend_on(fx_sim_layer)
    lighting_layer.set_service("maya2024,arnold")
    lighting_layer.set_min_cores(8)
    lighting_layer.set_min_memory(16384)
    
    # Compositing
    comp_layer = outline.modules.shell.Shell(
        name="compositing",
        command=[
            "nuke", "-x", f"/shared/comp/{shot_name}_comp.nk",
            "--frame-range", "#IFRAME#-#IFRAME#"
        ],
        range=frame_range
    )
    comp_layer.depend_on(lighting_layer)
    comp_layer.set_service("nuke")
    comp_layer.set_min_cores(4)
    comp_layer.set_min_memory(8192)
    
    # Review/QC
    review_layer = outline.modules.shell.Shell(
        name="create-review",
        command=[
            "python", "/shared/pipeline/create_review.py",
            "--shot", shot_name,
            "--input", f"/shared/comp/{shot_name}/",
            "--output", f"/shared/review/{shot_name}_v001.mov"
        ],
        range="1-1"
    )
    review_layer.depend_on(comp_layer)
    
    # Add all layers
    for layer in [asset_prep, layout_layer, animation_layer, fx_sim_layer, 
                  lighting_layer, comp_layer, review_layer]:
        job.add_layer(layer)
    
    return job
```

### Animation Feature Pipeline

```python
def create_animation_feature_pipeline(sequence_name):
    """Animation feature film pipeline"""
    
    job = outline.Outline(
        name=f"anim-feature-{sequence_name}-v001",
        shot=sequence_name,
        show="animated-feature",
        user="animation-supervisor"
    )
    
    # Storyboard validation
    storyboard_layer = outline.modules.shell.Shell(
        name="validate-storyboard",
        command=[
            "python", "/shared/editorial/validate_boards.py",
            "--sequence", sequence_name
        ],
        range="1-1"
    )
    
    # Layout pass
    layout_layer = outline.modules.shell.Shell(
        name="layout-pass",
        command=[
            "maya", "-batch", 
            "-file", f"/shared/layout/{sequence_name}_layout.ma",
            "-command", "python(\"renderLayoutFrame(#IFRAME#)\")"
        ],
        range="1-480"  # 20 seconds at 24fps
    )
    layout_layer.depend_on(storyboard_layer)
    
    # Animation blocking
    blocking_layer = outline.modules.shell.Shell(
        name="animation-blocking",
        command=[
            "maya", "-batch",
            "-file", f"/shared/animation/{sequence_name}_blocking.ma", 
            "-command", "python(\"renderBlockingFrame(#IFRAME#)\")"
        ],
        range="1-480"
    )
    blocking_layer.depend_on(layout_layer)
    
    # Final animation
    final_anim_layer = outline.modules.shell.Shell(
        name="final-animation",
        command=[
            "maya", "-batch",
            "-file", f"/shared/animation/{sequence_name}_final.ma",
            "-command", "python(\"renderFinalFrame(#IFRAME#)\")"
        ],
        range="1-480"
    )
    final_anim_layer.depend_on(blocking_layer)
    
    # Character rendering (multiple passes)
    char_beauty_layer = outline.modules.shell.Shell(
        name="character-beauty",
        command=[
            "maya", "-batch", "-renderer", "arnold",
            "-file", f"/shared/scenes/{sequence_name}_chars.ma",
            "-rl", "beauty", "-s", "#IFRAME#", "-e", "#IFRAME#"
        ],
        range="1-480"
    )
    char_beauty_layer.depend_on(final_anim_layer)
    char_beauty_layer.set_service("maya2024,arnold")
    
    # Environment rendering
    env_layer = outline.modules.shell.Shell(
        name="environment-render",
        command=[
            "maya", "-batch", "-renderer", "arnold",
            "-file", f"/shared/scenes/{sequence_name}_env.ma", 
            "-rl", "environment", "-s", "#IFRAME#", "-e", "#IFRAME#"
        ],
        range="1-480"
    )
    env_layer.depend_on(final_anim_layer)
    env_layer.set_service("maya2024,arnold")
    
    # Composite characters and environment
    comp_layer = outline.modules.shell.Shell(
        name="sequence-composite",
        command=[
            "nuke", "-x", f"/shared/comp/{sequence_name}_comp.nk",
            "--frame", "#IFRAME#"
        ],
        range="1-480"
    )
    comp_layer.depend_on(char_beauty_layer)
    comp_layer.depend_on(env_layer)
    
    # Create sequence playblast
    playblast_layer = outline.modules.shell.Shell(
        name="create-playblast",
        command=[
            "ffmpeg", "-start_number", "1", "-i", 
            f"/shared/comp/{sequence_name}/comp_%04d.exr",
            "-c:v", "libx264", "-pix_fmt", "yuv420p",
            f"/shared/review/{sequence_name}_v001.mp4"
        ],
        range="1-1"
    )
    playblast_layer.depend_on(comp_layer)
    
    # Add all layers
    layers = [storyboard_layer, layout_layer, blocking_layer, final_anim_layer,
              char_beauty_layer, env_layer, comp_layer, playblast_layer]
    
    for layer in layers:
        job.add_layer(layer)
    
    return job
```

## Performance Monitoring and Optimization

### Pipeline Analytics

```python
def analyze_pipeline_performance(job_name):
    """Analyze performance of multi-layer pipeline"""
    
    import opencue
    import time
    
    job = opencue.api.findJob(job_name)
    layers = job.getLayers()
    
    print(f"Pipeline Analysis for: {job_name}")
    print("=" * 50)
    
    for layer in layers:
        frames = layer.getFrames()
        if not frames:
            continue
            
        total_runtime = sum(f.runTime() for f in frames if f.runTime() > 0)
        avg_runtime = total_runtime / len(frames) if frames else 0
        failed_count = len([f for f in frames 
                           if f.state() == opencue.compiled_proto.job_pb2.DEAD])
        
        print(f"\nLayer: {layer.name()}")
        print(f"  Total Frames: {len(frames)}")
        print(f"  Average Runtime: {avg_runtime/60:.2f} minutes")
        print(f"  Failed Frames: {failed_count}")
        print(f"  Success Rate: {((len(frames)-failed_count)/len(frames)*100):.1f}%")
        
        # Resource utilization
        if frames:
            avg_cores = sum(f.usedCores() for f in frames) / len(frames)
            avg_memory = sum(f.usedMemory() for f in frames) / len(frames)
            print(f"  Avg Cores Used: {avg_cores:.1f}")
            print(f"  Avg Memory Used: {avg_memory:.0f} MB")
```

## Next Steps

You've mastered complex multi-layer job creation:
- Multi-layer architecture and dependency patterns
- Parallel and sequential processing workflows  
- Resource optimization strategies
- Error handling and fault tolerance
- Real-world pipeline examples

**Complete your learning with**:
- [DCC Integration Tutorial](/docs/tutorials/dcc-integration/) - Integrate with Maya, Blender, etc.
- Explore the [Other Guides](/docs/other-guides/) for advanced configuration
- Check the [Reference](/docs/reference/) for detailed API documentation

## Troubleshooting Multi-Layer Jobs

### Common Issues

1. **Dependency Deadlocks**:
   ```bash
   # Check for circular dependencies
   cueadmin -lji job-name | grep -A5 "Dependencies"
   ```

2. **Resource Starvation**:
   ```python
   # Monitor resource allocation across layers
   layers = job.getLayers()
   for layer in layers:
       print(f"{layer.name()}: {layer.minimumCores()} cores, {layer.minimumMemory()} MB")
   ```

3. **Failed Dependencies**:
   ```bash
   # Clear failed dependencies to allow continuation
   cueadmin -satisfy-dependency job-name layer-name
   ```