from __future__ import print_function
from __future__ import division
from __future__ import absolute_import

from builtins import str

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
    bl_idname = "object.submit_job"
    bl_label = "My Operator"

    def execute(self, context):
        layerData = {
            'name': context.scene.layer_name,
            'layerType': 'Blender',
            'cmd': {
                'blenderFile': '/home/nuwan/Documents/Projects/OpenCue/blender-demos/test/test.blend',
                'outputPath': '',
                'outputFormat': 'PNG'
            },
            'layerRange': '1',
            'chunk': '1',
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

        # self.report({'INFO'}, jobName)  # Custom method to run when button is clicked
        # return {'FINISHED'}

        from . import Submission
        Submission.submit(jobData)


class OpenCuePanel(bpy.types.Panel):
    """A custom panel in the 3D View Properties region"""
    bl_label = "OpenCue"
    bl_idname = "SCENE_PT_layout"  # VIEW_3D_opencue_panel
    bl_space_type = 'PROPERTIES'  # VIEW_3D
    bl_region_type = 'WINDOW'  # UI
    bl_category = "render"  # Properties

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
        col.operator("object.submit_job", text="Submit")


class OpenCueAddonPreferences(bpy.types.AddonPreferences):
    bl_idname = __name__

    is_dependency_install: bpy.props.BoolProperty(
        name="Dependency Install",
        default=False,
        description="Flag to indicate if dependencies have been installed during first install",
    )

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "is_dependency_install")

def get_opencue_home():
    return bpy.context.preferences.addons[__name__].preferences.opencue_home

def register():
    bpy.utils.register_class(OpenCueAddonPreferences)

    bpy.types.Scene.job_name = bpy.props.StringProperty(
        name="Job name",
        description="Enter some text",
        default=""
    )

    bpy.types.Scene.usr_name = bpy.props.StringProperty(
        name="User name",
        description="Enter some text",
        default=""
    )

    bpy.types.Scene.layer_name = bpy.props.StringProperty(
        name="Layer name",
        description="Enter some text",
        default=""
    )

    bpy.types.Scene.shot_name = bpy.props.StringProperty(
        name="Shot name",
        description="Enter some text",
        default=""
    )

    bpy.utils.register_class(OpenCuePanel)

    addon_pref = bpy.context.preferences.addons[__name__].preferences
    if not addon_pref.is_dependency_install:
        Setup.installModule()
        bpy.context.preferences.addons[__name__].preferences.is_dependency_install = True

        bpy.utils.register_class(SubmitJob)


def unregister():
    bpy.utils.unregister_class(OpenCuePanel)
    bpy.utils.unregister_class(SubmitJob)
    bpy.utils.unregister_class(OpenCueAddonPreferences)
    del bpy.types.Scene.job_name
    del bpy.types.Scene.usr_name
    del bpy.types.Scene.layer_name

    Setup.removeModule()


if __name__ == "__main__":
    register()
