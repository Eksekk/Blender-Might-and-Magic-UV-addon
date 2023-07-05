import bpy

for mat in bpy.data.materials:
    mat.preview_render_type = "FLAT"