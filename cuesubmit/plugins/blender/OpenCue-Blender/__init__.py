#  Copyright Contributors to the OpenCue Project
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.

from __future__ import print_function
from __future__ import division
from __future__ import absolute_import

bl_info = {
    "name": "OpenCue",
    "author": "Nuwan Jayawardene",
    "version": (0, 0, 0, 1),
    "blender": (3, 3, 1),
    "description": "OpenCue client for Blender.",
    "location": "Output Properties > OpenCue",
    "category": "System",
}

import bpy

from . import Setup


class SubmitJob(bpy.types.Operator):
    """Compiles and submits job on button press"""
    bl_idname = "object.submit_job"
    bl_label = "My Operator"

    def execute(self, context):
        layerData = {
            'name': context.scene.layer_name,
            'layerType': 'Blender',
            'cmd': {
                'blenderFile': bpy.data.filepath,
                'outputPath': context.scene.output_path,
                'outputFormat': 'PNG'
            },
            'layerRange': context.scene.frame_spec,
            'chunk': context.scene.chunk_size,
            'cores': '0',
            'env': {},
            'services': [],
            'limits': [],
            'dependType': '',
            'dependsOne': None
        }

        jobData = {
            'name': context.scene.job_name,
            'username': context.scene.usr_name,
            'show': "testing",
            'shot': context.scene.shot_name,
            'layers': layerData
        }

        from . import Submission
        Submission.submit(jobData)


class OpenCuePanel(bpy.types.Panel):
    """A custom panel in the 3D View Properties region"""
    bl_label = "OpenCue"
    bl_idname = "SCENE_PT_layout"  # VIEW_3D_opencue_panel
    bl_space_type = 'PROPERTIES'  # VIEW_3D
    bl_region_type = 'WINDOW'  # UI
    bl_context = "output"  # Properties

    def draw(self, context):
        layout = self.layout

        col = layout.column()
        col.prop(context.scene, "job_name")

        col = layout.column()
        col.prop(context.scene, "usr_name")

        col = layout.column()
        col.prop(context.scene, "layer_name")

        col = layout.column()
        col.prop(context.scene, "shot_name")

        col = layout.column()
        col.prop(context.scene, "output_path")

        col = layout.column()
        col.prop(context.scene, "frame_spec")

        col = layout.column()
        col.prop(context.scene, "chunk_size")

        col = layout.column()
        col.operator("object.submit_job", text="Submit")


class OpenCueAddonPreferences(bpy.types.AddonPreferences):
    """Generates addon settings in preferences view"""
    bl_idname = __name__

    is_dependency_install: bpy.props.BoolProperty(
        name="Dependency Install",
        default=False,
        description="Flag to indicate if dependencies have been installed during first install",
    )

    use_gpu: bpy.props.BoolProperty(
        name="Use GPU for rendering",
        default=False,
        description="Enable to utilize GPU rendering for jobs",
    )

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "use_gpu")


def register():
    """Registers addon to Blender"""
    bpy.utils.register_class(OpenCueAddonPreferences)

    bpy.types.Scene.job_name = bpy.props.StringProperty(
        name="Job name",
        description="Name of job submission",
        default=""
    )

    bpy.types.Scene.usr_name = bpy.props.StringProperty(
        name="User name",
        description="Name of user performing job submission",
        default=""
    )

    bpy.types.Scene.layer_name = bpy.props.StringProperty(
        name="Layer name",
        description="Job submission layer name",
        default=""
    )

    bpy.types.Scene.shot_name = bpy.props.StringProperty(
        name="Shot name",
        description="Shot name",
        default=""
    )

    bpy.types.Scene.frame_spec = bpy.props.StringProperty(
        name="Frame spec",
        description="Enter frame spec",
        default=""
    )

    bpy.types.Scene.chunk_size = bpy.props.StringProperty(
        name="Chunk size",
        description="Enter chunk size",
        default=""
    )

    bpy.types.Scene.output_path = bpy.props.StringProperty(
        name="Output path",
        description="Enter output path for rendered frames",
        default=""
    )

    bpy.utils.register_class(OpenCuePanel)

    # Check if dependencies are not installed
    addon_pref = bpy.context.preferences.addons[__name__].preferences
    if not addon_pref.is_dependency_install:
        Setup.installModule()
        bpy.context.preferences.addons[__name__].preferences.is_dependency_install = True
        bpy.utils.register_class(SubmitJob)
    else:
        Setup.installOpencueModules()
        bpy.utils.register_class(SubmitJob)


def unregister():
    """Unregisters addon from Blender"""
    bpy.utils.unregister_class(OpenCuePanel)
    bpy.utils.unregister_class(SubmitJob)
    bpy.utils.unregister_class(OpenCueAddonPreferences)
    del bpy.types.Scene.job_name
    del bpy.types.Scene.usr_name
    del bpy.types.Scene.layer_name

    Setup.removeOpencueModules()


if __name__ == "__main__":
    register()
