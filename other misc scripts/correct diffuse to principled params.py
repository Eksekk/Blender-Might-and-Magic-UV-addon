import bpy

C = bpy.context
for mat in C.object.data.materials:
    if hasattr(mat, "node_tree") and "Image Texture" in mat.node_tree.nodes:
        pr = mat.node_tree.nodes["Principled BSDF"]
        pr.inputs[9].default_value = 1
        tex = mat.node_tree.nodes["Image Texture"]
        tex.interpolation = "Linear"