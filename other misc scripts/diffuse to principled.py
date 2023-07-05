import bpy

C = bpy.context
for mat in C.object.data.materials:
    if hasattr(mat, "node_tree"):
        out = mat.node_tree.nodes["Material Output"]
        if mat.node_tree.nodes.find("Diffuse BSDF") != -1:
            mat.node_tree.nodes.remove(mat.node_tree.nodes["Diffuse BSDF"])
            pr = mat.node_tree.nodes.new("ShaderNodeBsdfPrincipled")
            pr.location = (60, 300)
            tex = mat.node_tree.nodes["Image Texture"]
            mat.node_tree.links.new(out.inputs[0], pr.outputs[0])
            mat.node_tree.links.new(pr.inputs["Base Color"], tex.outputs["Color"])