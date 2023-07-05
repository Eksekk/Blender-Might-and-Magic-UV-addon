def trunc(x, d):
    if x < 0:
        return x + (-x % d)
    else:
        return x - x % d

def getUvDirections(normals, indoor=True):
    nx, ny, nz = map(lambda x: trunc(x * 0x10000, 1 / 0x10000), normals)
    if nz == 0: # wall
        ux, uy, uz = trunc(-ny / 0x10000, 1 / 0x10000), trunc(nx / 0x10000, 1 / 0x10000), 0
        vx, vy, vz = 0, 0, 1
    elif abs(nz) >= (0xB569 if indoor else 0xE6CA): # floor, ceil
        ux, uy, uz = 1, 0, 0
        vx, vy, vz = 0, -1, 0
    else:
        q = (nx * nx + ny * ny) ** -0.5
        ux, uy, uz = trunc(-ny * q, 1 / 0x10000), trunc(nx * q, 1 / 0x10000), 0
        vx, vy, vz = 0, 0, 1
    return ux, uy, uz, vx, vy, vz

class VertData:
    def __init__(self, vert, u, v, loopIndex):
        self.vert = vert
        self.u = u
        self.v = v
        self.loopIndex = loopIndex

def zeroUvCoordinates(uOffset=0, vOffset=0):
    bm = bmesh.from_edit_mesh(bpy.context.edit_object.data)
    uvmap = bm.loops.layers.uv.verify()
    faces = [f for f in bm.faces if f.select]
    for face in faces:
        i = 0
        verts = []
        for loop in face.loops:
            vert = VertData(loop.vert, *loop[uvmap].uv, i)
            verts.append(vert)
            i += 1
                
        ux, uy, uz, vx, vy, vz = getUvDirections(face.normal)
        
        bmpWidth = None
        t = bpy.context.edit_object.data.materials[face.material_index]
        if t.node_tree != None:
            for node in t.node_tree.nodes:
                if node.bl_static_type == "TEX_IMAGE":
                    bmpWidth, bmpHeight = tuple(node.image.size)
                    break
        
        assert bmpWidth != None, "Material's node tree needs to have \"image texture\" node"
        uOffset %= bmpWidth
        vOffset %= bmpHeight
        
        for vert in verts:
            coords = vert.vert.co
            vert.u = trunc(round(coords[0] * ux + coords[1] * uy + coords[2] * uz + uOffset) / float(bmpWidth), 1 / bmpWidth)
            vert.v = trunc(round(coords[0] * vx + coords[1] * vy + coords[2] * vz + vOffset) / float(bmpHeight), 1 / bmpHeight)
            # apply changed uv
            face.loops[vert.loopIndex][uvmap].uv = (vert.u, vert.v)
    
    bmesh.update_edit_mesh(bpy.context.edit_object.data)