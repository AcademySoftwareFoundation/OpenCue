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
import pip

import outline
import outline.cuerun

class SubmitJob(bpy.types.Operator):
    bl_idname = "object.submit_job"
    bl_label = "My Operator"

    def execute(self, context):
        jobName = context.scene.job_name
        usrName = context.scene.usr_name
        layerName = context.scene.layer_name
        self.report({'INFO'}, jobName)  # Custom method to run when button is clicked
        return {'FINISHED'}


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
        col.operator("object.submit_job", text="Submit")


def register():
    # bpy.utils.register_class(OpenCuePanel)

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

    bpy.utils.register_class(OpenCuePanel)
    bpy.utils.register_class(SubmitJob)


def unregister():
    bpy.utils.unregister_class(OpenCuePanel)
    bpy.utils.unregister_class(SubmitJob)
    del bpy.types.Scene.job_name
    del bpy.types.Scene.usr_name
    del bpy.types.Scene.layer_name


if __name__ == "__main__":
    register()