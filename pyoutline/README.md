# OpenCue PyOutline

PyOutline is a Python library for building and managing OpenCue job definitions. It provides an API to create outlines that describe jobs, layers, and tasks, making it easier to construct repeatable workflows for rendering pipelines. 

This library serves as a Python layer over OpenCue's XML job descriptions, allowing the construction of complex jobs without having to edit XML directly. PyOutline is used by CueSubmit to construct job submissions.

## Example Usage
Here is a simple example of how to submit a job to cuebot using the API
```python
import outline.modules.shell

# Create a job for submission
job = outline.Outline("test-job", shot='test', show='testing', user='jimmy')

# Create a layer that can later be associated with a job. The command can use internal variables that are  
# replaced at runtime (eg. #IFRAME# which is the current frame rendering)
layer1 = outline.modules.shell.Shell("layer1", type="Render", command=["echo #IFRAME#"], range="1-100")

# Adds the layer to the job
job.add_layer(layer1)

# Create a new layer that will run after the first layer is done. The frame size is the same, but the chunk
# size is set to the full range, which means that it will only result in a single task instead of 1 per frame
layer2 = outline.modules.shell.Shell("layer2", type="Util", command=["echo Collecting frames"], range="1-100", chunk=100, tags="ffmpeg")

# Set the layer to depend on layer1
layer2.depend_on(layer1)

# Add the layer to the job
job.add_layer(layer2)

# Submit the job to cuebot. It will not use the cuerun wrapper and mail notification is disabled.
outline.cuerun.launch(job, use_pycuerun=False, os="Linux", nomail=True)
```