---
title: "DCC Integration Tutorial"
layout: default
parent: Tutorials
nav_order: 54
linkTitle: "DCC Integration Tutorial"
date: 2025-01-29
description: >
  Integrate OpenCue with Maya, Blender, and other DCC applications for seamless render submission
---

# DCC Integration Tutorial

This tutorial demonstrates how to integrate OpenCue with popular Digital Content Creation (DCC) applications like Maya, Blender, Nuke, and Houdini for seamless render submission and pipeline integration.

## What You'll Learn

- Setting up OpenCue integration in various DCC applications
- Creating custom submission interfaces
- Automating render job creation from DCC scenes
- Handling DCC-specific requirements and workflows
- Building production-ready pipeline tools

## Prerequisites

- Completed previous OpenCue tutorials
- Access to DCC applications (Maya, Blender, Nuke, or Houdini)
- Python scripting knowledge for your target DCC
- OpenCue PyOutline installed and configured

## Maya Integration

### Basic Maya Render Submission

#### Setup Maya Environment

```python
# maya_opencue_setup.py
import sys
import os

# Add OpenCue Python modules to Maya's path
opencue_path = "/shared/tools/opencue/python"
if opencue_path not in sys.path:
    sys.path.insert(0, opencue_path)

# Import OpenCue modules
import outline
import outline.modules.shell
import maya.cmds as cmds
import maya.mel as mel
```

#### Simple Maya Render Script

```python
# maya_render_submit.py
import maya.cmds as cmds
import outline
import outline.modules.shell
import os

def submit_maya_render():
    """Submit current Maya scene for rendering"""
    
    # Get scene information
    scene_file = cmds.file(query=True, sceneName=True)
    if not scene_file:
        cmds.error("Please save your scene first")
        return
    
    # Get render settings
    start_frame = int(cmds.getAttr("defaultRenderGlobals.startFrame"))
    end_frame = int(cmds.getAttr("defaultRenderGlobals.endFrame"))
    camera = cmds.getAttr("defaultRenderGlobals.renderable_camera")
    renderer = cmds.getAttr("defaultRenderGlobals.currentRenderer")
    
    # Create job
    scene_name = os.path.splitext(os.path.basename(scene_file))[0]
    job = outline.Outline(
        name=f"maya-{scene_name}-v001",
        shot=scene_name.split("_")[0] if "_" in scene_name else "default",
        show="maya-project",
        user=os.getenv("USER", "maya-user")
    )
    
    # Create render layer
    render_layer = outline.modules.shell.Shell(
        name="maya-render",
        command=[
            "maya", "-batch",
            "-file", scene_file,
            "-renderer", renderer,
            "-camera", camera,
            "-s", "#IFRAME#",
            "-e", "#IFRAME#"
        ],
        range=f"{start_frame}-{end_frame}"
    )
    
    # Set appropriate resources for Maya rendering
    render_layer.set_min_cores(4)
    render_layer.set_min_memory(8192)  # 8GB
    render_layer.set_service("maya2024")
    
    job.add_layer(render_layer)
    
    # Submit job
    outline.cuerun.launch(job, use_pycuerun=False)
    print(f"Submitted Maya render job: {job.get_name()}")

# Run from Maya script editor or shelf
submit_maya_render()
```

#### Advanced Maya Integration with UI

```python
# maya_opencue_ui.py
import maya.cmds as cmds
import maya.OpenMayaUI as omui
from PySide2 import QtWidgets, QtCore
import shiboken2
import outline
import outline.modules.shell

class MayaOpenCueSubmitter(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super(MayaOpenCueSubmitter, self).__init__(parent)
        self.setWindowTitle("OpenCue Render Submitter")
        self.setFixedSize(400, 500)
        self.setup_ui()
        self.populate_defaults()
    
    def setup_ui(self):
        layout = QtWidgets.QVBoxLayout(self)
        
        # Job Information
        job_group = QtWidgets.QGroupBox("Job Information")
        job_layout = QtWidgets.QFormLayout(job_group)
        
        self.job_name_edit = QtWidgets.QLineEdit()
        self.show_edit = QtWidgets.QLineEdit()
        self.shot_edit = QtWidgets.QLineEdit()
        self.user_edit = QtWidgets.QLineEdit()
        
        job_layout.addRow("Job Name:", self.job_name_edit)
        job_layout.addRow("Show:", self.show_edit)
        job_layout.addRow("Shot:", self.shot_edit)
        job_layout.addRow("User:", self.user_edit)
        
        # Render Settings
        render_group = QtWidgets.QGroupBox("Render Settings")
        render_layout = QtWidgets.QFormLayout(render_group)
        
        self.start_frame_spin = QtWidgets.QSpinBox()
        self.start_frame_spin.setRange(1, 10000)
        self.end_frame_spin = QtWidgets.QSpinBox()
        self.end_frame_spin.setRange(1, 10000)
        
        self.camera_combo = QtWidgets.QComboBox()
        self.renderer_combo = QtWidgets.QComboBox()
        
        render_layout.addRow("Start Frame:", self.start_frame_spin)
        render_layout.addRow("End Frame:", self.end_frame_spin)
        render_layout.addRow("Camera:", self.camera_combo)
        render_layout.addRow("Renderer:", self.renderer_combo)
        
        # Resource Settings
        resource_group = QtWidgets.QGroupBox("Resource Requirements")
        resource_layout = QtWidgets.QFormLayout(resource_group)
        
        self.cores_spin = QtWidgets.QSpinBox()
        self.cores_spin.setRange(1, 32)
        self.cores_spin.setValue(4)
        
        self.memory_spin = QtWidgets.QSpinBox()
        self.memory_spin.setRange(1024, 65536)
        self.memory_spin.setValue(8192)
        self.memory_spin.setSuffix(" MB")
        
        self.priority_spin = QtWidgets.QSpinBox()
        self.priority_spin.setRange(1, 200)
        self.priority_spin.setValue(100)
        
        resource_layout.addRow("Min Cores:", self.cores_spin)
        resource_layout.addRow("Min Memory:", self.memory_spin)
        resource_layout.addRow("Priority:", self.priority_spin)
        
        # Buttons
        button_layout = QtWidgets.QHBoxLayout()
        submit_btn = QtWidgets.QPushButton("Submit Job")
        cancel_btn = QtWidgets.QPushButton("Cancel")
        
        submit_btn.clicked.connect(self.submit_job)
        cancel_btn.clicked.connect(self.reject)
        
        button_layout.addWidget(submit_btn)
        button_layout.addWidget(cancel_btn)
        
        # Add to main layout
        layout.addWidget(job_group)
        layout.addWidget(render_group)
        layout.addWidget(resource_group)
        layout.addLayout(button_layout)
    
    def populate_defaults(self):
        """Populate UI with current Maya scene settings"""
        import os
        
        # Scene information
        scene_file = cmds.file(query=True, sceneName=True)
        if scene_file:
            scene_name = os.path.splitext(os.path.basename(scene_file))[0]
            self.job_name_edit.setText(f"maya-{scene_name}-v001")
            
            # Try to extract show/shot from filename
            parts = scene_name.split("_")
            if len(parts) >= 2:
                self.show_edit.setText(parts[0])
                self.shot_edit.setText(parts[1])
        
        self.user_edit.setText(os.getenv("USER", "maya-user"))
        
        # Frame range
        start_frame = int(cmds.getAttr("defaultRenderGlobals.startFrame"))
        end_frame = int(cmds.getAttr("defaultRenderGlobals.endFrame"))
        self.start_frame_spin.setValue(start_frame)
        self.end_frame_spin.setValue(end_frame)
        
        # Cameras
        cameras = cmds.ls(type="camera")
        renderable_cameras = []
        for cam in cameras:
            if cmds.getAttr(f"{cam}.renderable"):
                renderable_cameras.append(cam)
        
        self.camera_combo.addItems(renderable_cameras)
        
        # Renderers
        renderers = cmds.renderer(query=True, namesOfAvailableRenderers=True)
        self.renderer_combo.addItems(renderers)
        current_renderer = cmds.getAttr("defaultRenderGlobals.currentRenderer")
        index = self.renderer_combo.findText(current_renderer)
        if index >= 0:
            self.renderer_combo.setCurrentIndex(index)
    
    def submit_job(self):
        """Submit the render job to OpenCue"""
        try:
            # Get scene file
            scene_file = cmds.file(query=True, sceneName=True)
            if not scene_file or not cmds.file(query=True, exists=True):
                QtWidgets.QMessageBox.warning(self, "Warning", "Please save your scene first")
                return
            
            # Create job
            job = outline.Outline(
                name=self.job_name_edit.text(),
                shot=self.shot_edit.text(),
                show=self.show_edit.text(),
                user=self.user_edit.text()
            )
            job.set_priority(self.priority_spin.value())
            
            # Create render layer
            render_layer = outline.modules.shell.Shell(
                name="maya-render",
                command=[
                    "maya", "-batch",
                    "-file", scene_file,
                    "-renderer", self.renderer_combo.currentText(),
                    "-camera", self.camera_combo.currentText(),
                    "-s", "#IFRAME#",
                    "-e", "#IFRAME#"
                ],
                range=f"{self.start_frame_spin.value()}-{self.end_frame_spin.value()}"
            )
            
            render_layer.set_min_cores(self.cores_spin.value())
            render_layer.set_min_memory(self.memory_spin.value())
            render_layer.set_service("maya2024")
            
            job.add_layer(render_layer)
            
            # Submit
            outline.cuerun.launch(job, use_pycuerun=False)
            
            QtWidgets.QMessageBox.information(
                self, "Success", 
                f"Successfully submitted job: {job.get_name()}"
            )
            self.accept()
            
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Error", f"Failed to submit job: {str(e)}")

def show_submitter():
    """Show the OpenCue submitter dialog"""
    app = QtWidgets.QApplication.instance()
    if not app:
        app = QtWidgets.QApplication([])
    
    # Get Maya main window as parent
    maya_main_window = None
    try:
        maya_main_window_ptr = omui.MQtUtil.mainWindow()
        maya_main_window = shiboken2.wrapInstance(int(maya_main_window_ptr), QtWidgets.QWidget)
    except:
        pass
    
    dialog = MayaOpenCueSubmitter(maya_main_window)
    dialog.show()
    return dialog

# Create shelf button or menu item to run:
# show_submitter()
```

## Blender Integration

### Blender Command Line Rendering

```python
# blender_opencue_submit.py
import bpy
import outline
import outline.modules.shell
import os
import tempfile

class BlenderOpenCueSubmitter(bpy.types.Operator):
    """Submit Blender render to OpenCue"""
    bl_idname = "render.opencue_submit"
    bl_label = "Submit to OpenCue"
    bl_options = {'REGISTER', 'UNDO'}
    
    # Properties
    job_name: bpy.props.StringProperty(
        name="Job Name",
        description="Name for the render job",
        default="blender-render-v001"
    )
    
    show_name: bpy.props.StringProperty(
        name="Show",
        description="Show/Project name",
        default="blender-project"
    )
    
    shot_name: bpy.props.StringProperty(
        name="Shot", 
        description="Shot name",
        default="shot001"
    )
    
    priority: bpy.props.IntProperty(
        name="Priority",
        description="Job priority",
        default=100,
        min=1,
        max=200
    )
    
    def execute(self, context):
        try:
            # Save current file if needed
            if not bpy.data.filepath:
                self.report({'ERROR'}, "Please save your Blender file first")
                return {'CANCELLED'}
            
            # Get render settings
            scene = context.scene
            start_frame = scene.frame_start
            end_frame = scene.frame_end
            output_path = bpy.path.abspath(scene.render.filepath)
            
            # Create OpenCue job
            job = outline.Outline(
                name=self.job_name,
                shot=self.shot_name,
                show=self.show_name,
                user=os.getenv("USER", "blender-user")
            )
            job.set_priority(self.priority)
            
            # Create render layer
            render_layer = outline.modules.shell.Shell(
                name="blender-render",
                command=[
                    bpy.app.binary_path,  # Blender executable
                    "-b", bpy.data.filepath,  # Background mode with file
                    "-o", output_path,  # Output path
                    "-f", "#IFRAME#"  # Frame number
                ],
                range=f"{start_frame}-{end_frame}"
            )
            
            # Set resource requirements
            render_layer.set_min_cores(2)
            render_layer.set_min_memory(4096)
            render_layer.set_service("blender")
            
            job.add_layer(render_layer)
            
            # Submit job
            outline.cuerun.launch(job, use_pycuerun=False)
            
            self.report({'INFO'}, f"Submitted job: {job.get_name()}")
            return {'FINISHED'}
            
        except Exception as e:
            self.report({'ERROR'}, f"Failed to submit job: {str(e)}")
            return {'CANCELLED'}

class BlenderOpenCuePanel(bpy.types.Panel):
    """Panel for OpenCue submission in Blender"""
    bl_label = "OpenCue Render"
    bl_idname = "RENDER_PT_opencue"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "render"
    
    def draw(self, context):
        layout = self.layout
        scene = context.scene
        
        # Job settings
        col = layout.column()
        col.label(text="OpenCue Job Settings:")
        
        # Use scene properties to store settings
        if not hasattr(scene, "opencue_job_name"):
            scene.opencue_job_name = bpy.props.StringProperty(default="blender-render-v001")
            scene.opencue_show = bpy.props.StringProperty(default="blender-project")
            scene.opencue_shot = bpy.props.StringProperty(default="shot001")
            scene.opencue_priority = bpy.props.IntProperty(default=100)
        
        col.prop(scene, "opencue_job_name", text="Job Name")
        col.prop(scene, "opencue_show", text="Show")
        col.prop(scene, "opencue_shot", text="Shot")
        col.prop(scene, "opencue_priority", text="Priority")
        
        # Submit button
        col.separator()
        col.operator("render.opencue_submit", text="Submit to OpenCue", icon='RENDER_ANIMATION')

def register():
    bpy.utils.register_class(BlenderOpenCueSubmitter)
    bpy.utils.register_class(BlenderOpenCuePanel)

def unregister():
    bpy.utils.unregister_class(BlenderOpenCueSubmitter)
    bpy.utils.unregister_class(BlenderOpenCuePanel)

if __name__ == "__main__":
    register()
```

### Blender Animation Rendering

```python
# blender_animation_submit.py
import bpy
import outline
import outline.modules.shell
import os

def submit_blender_animation():
    """Submit Blender animation with multiple layers"""
    
    scene = bpy.context.scene
    blend_file = bpy.data.filepath
    
    if not blend_file:
        print("ERROR: Please save your Blender file first")
        return
    
    # Create job
    job = outline.Outline(
        name="blender-animation-v001",
        shot="animation_test",
        show="blender-feature",
        user=os.getenv("USER", "animator")
    )
    
    # Viewport preview layer (fast)
    preview_layer = outline.modules.shell.Shell(
        name="viewport-preview",
        command=[
            bpy.app.binary_path, "-b", blend_file,
            "--python-expr", 
            "import bpy; "
            "bpy.context.scene.render.engine = 'BLENDER_WORKBENCH'; "
            "bpy.context.scene.render.resolution_percentage = 50; "
            "bpy.ops.render.render(write_still=True)",
            "-o", "/shared/preview/viewport_####.png",
            "-f", "#IFRAME#"
        ],
        range=f"{scene.frame_start}-{scene.frame_end}"
    )
    preview_layer.set_min_cores(1)
    preview_layer.set_min_memory(2048)
    
    # Full quality render layer
    render_layer = outline.modules.shell.Shell(
        name="final-render",
        command=[
            bpy.app.binary_path, "-b", blend_file,
            "-o", "/shared/renders/final_####.exr",
            "-f", "#IFRAME#"
        ],
        range=f"{scene.frame_start}-{scene.frame_end}"
    )
    render_layer.set_min_cores(4)
    render_layer.set_min_memory(8192)
    render_layer.depend_on(preview_layer)  # Wait for preview approval
    
    # Video compilation
    video_layer = outline.modules.shell.Shell(
        name="create-video",
        command=[
            "ffmpeg", "-start_number", str(scene.frame_start),
            "-i", "/shared/renders/final_%04d.exr",
            "-c:v", "libx264", "-pix_fmt", "yuv420p",
            "/shared/output/animation_final.mp4"
        ],
        range="1-1"
    )
    video_layer.depend_on(render_layer)
    
    # Add layers to job
    job.add_layer(preview_layer)
    job.add_layer(render_layer)
    job.add_layer(video_layer)
    
    # Submit
    outline.cuerun.launch(job, use_pycuerun=False)
    print(f"Submitted Blender animation job: {job.get_name()}")

# Run from Blender's text editor
submit_blender_animation()
```

## Nuke Integration

### Nuke Render Submission

```python
# nuke_opencue_submit.py
import nuke
import outline
import outline.modules.shell
import os

def submit_nuke_render():
    """Submit Nuke script to OpenCue"""
    
    # Get current script
    script_path = nuke.scriptName()
    if not script_path:
        nuke.message("Please save your Nuke script first")
        return
    
    # Get frame range
    first_frame = int(nuke.root()['first_frame'].getValue())
    last_frame = int(nuke.root()['last_frame'].getValue())
    
    # Find Write nodes
    write_nodes = [node for node in nuke.allNodes() if node.Class() == "Write"]
    if not write_nodes:
        nuke.message("No Write nodes found in script")
        return
    
    # Create job
    script_name = os.path.splitext(os.path.basename(script_path))[0]
    job = outline.Outline(
        name=f"nuke-{script_name}-v001",
        shot=script_name.split("_")[0] if "_" in script_name else "comp",
        show="nuke-project",
        user=os.getenv("USER", "compositor")
    )
    
    # Create render layer for each Write node
    for write_node in write_nodes:
        layer_name = f"render-{write_node.name()}"
        
        render_layer = outline.modules.shell.Shell(
            name=layer_name,
            command=[
                "nuke", "-x", script_path,
                "-X", write_node.name(),  # Execute specific Write node
                "-F", f"#IFRAME#-#IFRAME#"
            ],
            range=f"{first_frame}-{last_frame}"
        )
        
        # Set resources based on script complexity
        render_layer.set_min_cores(2)
        render_layer.set_min_memory(4096)
        render_layer.set_service("nuke")
        
        job.add_layer(render_layer)
    
    # Submit job
    outline.cuerun.launch(job, use_pycuerun=False)
    nuke.message(f"Submitted Nuke job: {job.get_name()}")

# Create Nuke menu item
if __name__ == "__main__":
    # Add to Nuke menu
    toolbar = nuke.toolbar("Nodes")
    m = toolbar.addMenu("OpenCue")
    m.addCommand("Submit Render", "submit_nuke_render()")
```

### Advanced Nuke Integration

```python
# nuke_opencue_advanced.py
import nuke
import nukescripts
import outline
import outline.modules.shell
import os

class NukeOpenCueSubmitter(nukescripts.PythonPanel):
    def __init__(self):
        nukescripts.PythonPanel.__init__(self, "OpenCue Submitter")
        
        # Job settings
        self.job_name = nuke.String_Knob('job_name', 'Job Name:', 'nuke-comp-v001')
        self.show_name = nuke.String_Knob('show_name', 'Show:', 'nuke-project')
        self.shot_name = nuke.String_Knob('shot_name', 'Shot:', 'shot001')
        self.priority = nuke.Int_Knob('priority', 'Priority:', 100)
        
        # Frame range
        self.frame_range = nuke.String_Knob('frame_range', 'Frame Range:', 
                                           f"{int(nuke.root()['first_frame'].getValue())}-{int(nuke.root()['last_frame'].getValue())}")
        
        # Write node selection
        write_nodes = [node.name() for node in nuke.allNodes() if node.Class() == "Write"]
        self.write_nodes = nuke.Enumeration_Knob('write_nodes', 'Write Nodes:', write_nodes)
        self.write_nodes.setFlag(nuke.STARTLINE)
        
        # Resource settings
        self.min_cores = nuke.Int_Knob('min_cores', 'Min Cores:', 2)
        self.min_memory = nuke.Int_Knob('min_memory', 'Min Memory (MB):', 4096)
        
        # Add knobs
        for knob in [self.job_name, self.show_name, self.shot_name, self.priority,
                     self.frame_range, self.write_nodes, self.min_cores, self.min_memory]:
            self.addKnob(knob)
        
        # Submit button
        self.submit_btn = nuke.PyScript_Knob('submit', 'Submit to OpenCue')
        self.addKnob(self.submit_btn)
    
    def knobChanged(self, knob):
        if knob == self.submit_btn:
            self.submit_job()
    
    def submit_job(self):
        try:
            script_path = nuke.scriptName()
            if not script_path:
                nuke.message("Please save your Nuke script first")
                return
            
            # Create job
            job = outline.Outline(
                name=self.job_name.getValue(),
                shot=self.shot_name.getValue(), 
                show=self.show_name.getValue(),
                user=os.getenv("USER", "compositor")
            )
            job.set_priority(int(self.priority.getValue()))
            
            # Parse frame range
            frame_range = self.frame_range.getValue()
            
            # Get selected Write nodes
            selected_writes = [self.write_nodes.enumName(i) for i in range(self.write_nodes.numValues())
                              if i == self.write_nodes.getValue()]
            
            if not selected_writes:
                selected_writes = [node.name() for node in nuke.allNodes() if node.Class() == "Write"]
            
            # Create render layers
            for write_name in selected_writes:
                layer_name = f"render-{write_name}"
                
                render_layer = outline.modules.shell.Shell(
                    name=layer_name,
                    command=[
                        "nuke", "-x", script_path,
                        "-X", write_name,
                        "-F", f"#IFRAME#-#IFRAME#"
                    ],
                    range=frame_range
                )
                
                render_layer.set_min_cores(int(self.min_cores.getValue()))
                render_layer.set_min_memory(int(self.min_memory.getValue()))
                render_layer.set_service("nuke")
                
                job.add_layer(render_layer)
            
            # Submit
            outline.cuerun.launch(job, use_pycuerun=False)
            nuke.message(f"Successfully submitted job: {job.get_name()}")
            
        except Exception as e:
            nuke.message(f"Failed to submit job: {str(e)}")

def show_opencue_submitter():
    """Show the OpenCue submitter panel"""
    panel = NukeOpenCueSubmitter()
    panel.show()

# Add to Nuke menu
if __name__ == "__main__":
    toolbar = nuke.toolbar("Nodes")
    m = toolbar.addMenu("OpenCue")
    m.addCommand("Submit Render", "show_opencue_submitter()")
```

## Houdini Integration

### Houdini Render Submission

```python
# houdini_opencue_submit.py
import hou
import outline
import outline.modules.shell
import os

def submit_houdini_render():
    """Submit Houdini render to OpenCue"""
    
    # Get current hip file
    hip_file = hou.hipFile.path()
    if hip_file == "untitled.hip":
        hou.ui.displayMessage("Please save your Houdini file first")
        return
    
    # Find ROP nodes
    rop_nodes = []
    for node in hou.node("/out").children():
        if node.type().category().name() == "Driver":
            rop_nodes.append(node)
    
    if not rop_nodes:
        hou.ui.displayMessage("No render nodes found in /out")
        return
    
    # Get frame range from global settings
    frame_range = hou.playbar.frameRange()
    start_frame = int(frame_range[0])
    end_frame = int(frame_range[1])
    
    # Create job
    hip_name = os.path.splitext(os.path.basename(hip_file))[0]
    job = outline.Outline(
        name=f"houdini-{hip_name}-v001",
        shot=hip_name.split("_")[0] if "_" in hip_name else "fx",
        show="houdini-project",
        user=os.getenv("USER", "fx-artist")
    )
    
    # Create layers for each ROP
    for rop in rop_nodes:
        layer_name = f"render-{rop.name()}"
        
        # Determine if this is a simulation or render
        is_simulation = rop.type().name() in ["dopnet", "filecache", "rop_alembic"]
        
        render_layer = outline.modules.shell.Shell(
            name=layer_name,
            command=[
                "hython",  # Houdini's Python
                "-c",
                f"import hou; "
                f"hou.hipFile.load('{hip_file}'); "
                f"rop = hou.node('/out/{rop.name()}'); "
                f"rop.render(frame_range=({start_frame}, {end_frame}), verbose=True)"
            ],
            range=f"{start_frame}-{end_frame}"
        )
        
        # Set resources based on node type
        if is_simulation:
            render_layer.set_min_cores(8)
            render_layer.set_min_memory(16384)  # 16GB for simulations
            render_layer.set_service("houdini,simulation")
        else:
            render_layer.set_min_cores(4)
            render_layer.set_min_memory(8192)   # 8GB for rendering
            render_layer.set_service("houdini")
        
        job.add_layer(render_layer)
    
    # Submit job
    outline.cuerun.launch(job, use_pycuerun=False)
    hou.ui.displayMessage(f"Submitted Houdini job: {job.get_name()}")

# Create shelf tool
def create_shelf_tool():
    """Create OpenCue shelf tool in Houdini"""
    
    # Get or create custom shelf
    shelf_set = hou.shelves.shelves()
    custom_shelf = None
    
    for shelf in shelf_set.values():
        if shelf.name() == "opencue_tools":
            custom_shelf = shelf
            break
    
    if not custom_shelf:
        custom_shelf = hou.shelves.newShelf(name="opencue_tools", label="OpenCue Tools")
    
    # Create submit tool
    tool = hou.shelves.newTool(
        name="submit_opencue",
        label="Submit to OpenCue",
        script="submit_houdini_render()",
        language=hou.scriptLanguage.Python,
        icon="ROP_geometry",
        help="Submit current Houdini scene to OpenCue render farm"
    )
    
    custom_shelf.setTools(list(custom_shelf.tools()) + [tool])

if __name__ == "__main__":
    create_shelf_tool()
```

## Production Pipeline Integration

### Universal DCC Submitter

```python
# universal_dcc_submitter.py
import os
import sys
import outline
import outline.modules.shell

class DCCSubmitter:
    """Universal submitter for different DCC applications"""
    
    def __init__(self):
        self.dcc_type = self.detect_dcc()
        self.dcc_handlers = {
            'maya': self.handle_maya,
            'blender': self.handle_blender,
            'nuke': self.handle_nuke,
            'houdini': self.handle_houdini
        }
    
    def detect_dcc(self):
        """Detect which DCC application is running"""
        if 'maya' in sys.modules:
            return 'maya'
        elif 'bpy' in sys.modules:
            return 'blender'
        elif 'nuke' in sys.modules:
            return 'nuke'
        elif 'hou' in sys.modules:
            return 'houdini'
        else:
            return 'standalone'
    
    def submit_job(self, job_settings):
        """Submit job using appropriate DCC handler"""
        if self.dcc_type in self.dcc_handlers:
            return self.dcc_handlers[self.dcc_type](job_settings)
        else:
            raise ValueError(f"Unsupported DCC: {self.dcc_type}")
    
    def handle_maya(self, settings):
        """Handle Maya-specific submission"""
        import maya.cmds as cmds
        
        scene_file = cmds.file(query=True, sceneName=True)
        if not scene_file:
            raise ValueError("No Maya scene file saved")
        
        job = outline.Outline(
            name=settings['job_name'],
            shot=settings['shot'],
            show=settings['show'], 
            user=settings['user']
        )
        
        render_layer = outline.modules.shell.Shell(
            name="maya-render",
            command=[
                "maya", "-batch", "-file", scene_file,
                "-renderer", settings.get('renderer', 'arnold'),
                "-s", "#IFRAME#", "-e", "#IFRAME#"
            ],
            range=settings['frame_range']
        )
        
        self.apply_resources(render_layer, settings)
        render_layer.set_service("maya2024")
        job.add_layer(render_layer)
        
        return job
    
    def handle_blender(self, settings):
        """Handle Blender-specific submission"""
        import bpy
        
        blend_file = bpy.data.filepath
        if not blend_file:
            raise ValueError("No Blender file saved")
        
        job = outline.Outline(
            name=settings['job_name'],
            shot=settings['shot'],
            show=settings['show'],
            user=settings['user']
        )
        
        render_layer = outline.modules.shell.Shell(
            name="blender-render",
            command=[
                bpy.app.binary_path, "-b", blend_file,
                "-o", settings.get('output_path', '/shared/renders/####'),
                "-f", "#IFRAME#"
            ],
            range=settings['frame_range']
        )
        
        self.apply_resources(render_layer, settings)
        render_layer.set_service("blender")
        job.add_layer(render_layer)
        
        return job
    
    def handle_nuke(self, settings):
        """Handle Nuke-specific submission"""
        import nuke
        
        script_path = nuke.scriptName()
        if not script_path:
            raise ValueError("No Nuke script saved")
        
        job = outline.Outline(
            name=settings['job_name'],
            shot=settings['shot'],
            show=settings['show'],
            user=settings['user']
        )
        
        render_layer = outline.modules.shell.Shell(
            name="nuke-render",
            command=[
                "nuke", "-x", script_path,
                "-F", f"#IFRAME#-#IFRAME#"
            ],
            range=settings['frame_range']
        )
        
        self.apply_resources(render_layer, settings)
        render_layer.set_service("nuke")
        job.add_layer(render_layer)
        
        return job
    
    def handle_houdini(self, settings):
        """Handle Houdini-specific submission"""
        import hou
        
        hip_file = hou.hipFile.path()
        if hip_file == "untitled.hip":
            raise ValueError("No Houdini file saved")
        
        job = outline.Outline(
            name=settings['job_name'],
            shot=settings['shot'],
            show=settings['show'],
            user=settings['user']
        )
        
        render_layer = outline.modules.shell.Shell(
            name="houdini-render",
            command=[
                "hython", "-c",
                f"import hou; hou.hipFile.load('{hip_file}'); "
                f"hou.node('/out/{settings.get('rop_node', 'mantra1')}').render()"
            ],
            range=settings['frame_range']
        )
        
        self.apply_resources(render_layer, settings)
        render_layer.set_service("houdini")
        job.add_layer(render_layer)
        
        return job
    
    def apply_resources(self, layer, settings):
        """Apply resource settings to layer"""
        layer.set_min_cores(settings.get('min_cores', 4))
        layer.set_min_memory(settings.get('min_memory', 4096))
        layer.set_priority(settings.get('priority', 100))

# Usage example
def submit_from_any_dcc():
    """Submit render from any supported DCC"""
    
    submitter = DCCSubmitter()
    
    settings = {
        'job_name': 'universal-render-v001',
        'shot': 'shot010',
        'show': 'multi-dcc-project',
        'user': os.getenv('USER', 'artist'),
        'frame_range': '1-100',
        'min_cores': 4,
        'min_memory': 8192,
        'priority': 100
    }
    
    try:
        job = submitter.submit_job(settings)
        outline.cuerun.launch(job, use_pycuerun=False)
        print(f"Successfully submitted {submitter.dcc_type} job: {job.get_name()}")
        
    except Exception as e:
        print(f"Failed to submit job: {str(e)}")

if __name__ == "__main__":
    submit_from_any_dcc()
```

## Next Steps

You've mastered DCC integration with OpenCue:
- Maya integration with custom UI and batch rendering
- Blender integration with operators and panels
- Nuke integration with Write node management
- Houdini integration with ROP node handling
- Universal submitter for multi-DCC pipelines

**You've completed all OpenCue tutorials!** 

**Continue exploring**:
- [Other Guides](/docs/other-guides/) for advanced configuration and troubleshooting
- [Reference](/docs/reference/) for detailed API documentation
- [User Guides](/docs/user-guides/) for additional workflow techniques

## Best Practices Summary

1. **Always validate scene files** before submission
2. **Set appropriate resource requirements** based on job complexity
3. **Use descriptive job names** with version numbers
4. **Test locally** before submitting to the farm
5. **Monitor resource usage** and adjust settings accordingly
6. **Create user-friendly interfaces** for artists
7. **Handle errors gracefully** with informative messages
8. **Integrate with studio pipeline** tools and conventions