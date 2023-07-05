import bpy

C = bpy.context
for mat in C.object.data.materials:
    if hasattr(mat, "node_tree") and "Image Texture" in mat.node_tree.nodes:
        mat.node_tree.nodes["Image Texture"].projection = "FLAT"