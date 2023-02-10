bl_info = {
    "name": "OpenCue",
    "author": "Nuwan Jayawardene",
    "version": (0, 0, 0, 1),
    "blender": (3, 3, 1)    
}

import bpy

class OpenCuePanel(bpy.types.Panel):
    """A custom panel in the 3D View Properties region"""
    bl_label = "OpenCue"
    bl_idname = "VIEW_3D_opencue_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Properties"

    def draw(self, context):
        layout = self.layout

        row = layout.row()
        row.operator("mesh.primitive_cube_add", text="Add Cube")
        row = layout.row()
        row.operator("object.delete", text="Delete Object")

def register():
    bpy.utils.register_class(OpenCuePanel)

def unregister():
    bpy.utils.unregister_class(OpenCuePanel)

if __name__ == "__main__":
    register()