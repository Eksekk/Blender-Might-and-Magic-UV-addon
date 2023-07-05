import bpy, re

C = bpy.context
for mat in C.object.data.materials:
    newName = re.sub(".bmp", "", mat.name)
    if newName not in C.object.data.materials:
        mat.name = newName