bl_info = {
    "name": "MM UV coordinates tools",
    "description": "Makes changing face UV coordinates for Might and Magic maps much easier",
    "author": "Eksekk",
    "version": (1, 0),
    "blender": (3, 20, 20),
    "location": "View3D > UV (requires edit mode)",
    "warning": "", # used for warning icon and text in addons panel
    "doc_url": "",
    "tracker_url": "",
    "support": "COMMUNITY",
    "category": "UV",
}

import bpy, bmesh
#
# ACTUAL ADDON CODE
#

"""
TODO:
* grab settings from face
* preset UV coordinates (say, for cabinets or buttons)
* arrow keys to change uv (like in editor)
* relative UV coordinates mode (current, coords are affected by vertex positions) and
* absolute UV coordinates mode (no matter vertex coords, texture always has same UV offsets)
"""

# adapted from Grayface's editor code

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
    elif abs(nz) >= (0xB569 if indoor else 0xE6CA): # floor, ceil, TODO: outdoor map detection
        ux, uy, uz = 1, 0, 0
        vx, vy, vz = 0, 1, 0
    else:
        q = (nx * nx + ny * ny) ** -0.5
        ux, uy, uz = trunc(-ny * q, 1 / 0x10000), trunc(nx * q, 1 / 0x10000), 0
        vx, vy, vz = 0, 0, 1
    return ux, uy, uz, vx, vy, vz

# simple data container
class VertData:
    def __init__(self, vert, u, v, loopIndex):
        self.vert = vert
        self.u = u
        self.v = v
        self.loopIndex = loopIndex
    
# get vertex list, uv coordinates and bmp width/height
# argument is bmesh face and uv map for which to get uv values
def getFaceData(face, uvmap):
    i = 0
    verts = []
    for loop in face.loops:
        vert = VertData(loop.vert, *loop[uvmap].uv, i)
        verts.append(vert)
        i += 1
    
    ux, uy, uz, vx, vy, vz = getUvDirections(face.normal)
    
    bmpWidth, bmpHeight = None, None
    t = bpy.context.edit_object.data.materials[face.material_index]
    if t.node_tree != None:
        for node in t.node_tree.nodes:
            if node.bl_static_type == "TEX_IMAGE":
                bmpWidth, bmpHeight = tuple(node.image.size)
                break
            
    return (verts, (ux, uy, uz, vx, vy, vz), (bmpWidth, bmpHeight))

# returns current UV coords the face uses. If vertex UVs are inconsistent, result will be unpredictable
# arguments: bmesh face and uv map
def getUvSettingsFromFace(face, uvmap):
    data = getFaceData(face, uvmap)
    verts = data[0]
    ux, uy, uz, vx, vy, vz = data[1]
    bmpWidth, bmpHeight = data[2]
    
    assert bmpWidth != None, "Material's node tree needs to have \"image texture\" node"
    def getCoeffU(vert):
        # round is important!
        return round(ux * vert.co[0] + uy * vert.co[1] + uz * vert.co[2])
    def getCoeffV(vert):
        return round(vx * vert.co[0] + vy * vert.co[1] + vz * vert.co[2])
    
    u, v = None, None
    for i in range(0, len(verts)):
        vert = verts[i]
        # ADVANCED MATHS
        # vert.u = round(coeff1 + unk) / bmpWidth
        # vert.u * bmpWidth = round(coeff1 + unk)
        # unk = vert.u * bmpWidth - coeff1
        u2 = (vert.u * bmpWidth - getCoeffU(vert.vert))
        v2 = (vert.v * bmpHeight - getCoeffV(vert.vert))
        # wanted to make checking if uv was consistent, didn't work
        u, v = u2, v2
    return u, v

# operators such as box select don't add faces to selection history
# argument: bmesh instance
def getSelectedFaces(bm):
    faces = [elem for elem in bm.select_history if isinstance(elem, bmesh.types.BMFace)]
    indexes = {elem.index: True for elem in bm.select_history if isinstance(elem, bmesh.types.BMFace)}
    for face in bm.faces:
        if face.select and face.index not in indexes:
            indexes[face.index] = True
            faces.append(face)
    return faces

# sets UV coordinates (relative to vertex coords). Params:
# uOffset, vOffset - uv to apply or add
# assignMaterial - if this is a number, all affected faces will get material with this index assigned
# absolute - set coordinates based on lowest v or u value, not based on coords
# addOffsets - if this is true, offsets are added to current face value, otherwise they completely replace original value
def changeUvCoordinates(uOffset=0, vOffset=0, assignMaterial=None, absolute=False, addOffsets=False):
    bm = bmesh.from_edit_mesh(bpy.context.edit_object.data)
    uvmap = bm.loops.layers.uv.verify()
    bm.select_history.validate()
    faces = getSelectedFaces(bm)
    if len(faces) == 0:
        return False
    for face in faces:
        if assignMaterial and face.material_index != assignMaterial:
            face.material_index = assignMaterial
        data = getFaceData(face, uvmap)
        verts = data[0]
        ux, uy, uz, vx, vy, vz = data[1]
        bmpWidth, bmpHeight = data[2]
        assert bmpWidth != None, "Material's node tree needs to have \"image texture\" node"

        modOffsetU = uOffset % bmpWidth
        modOffsetV = vOffset % bmpHeight
        
        if absolute:
            minU, minV = getFirstAbsoluteVertexUv(face, data)
        orig_uv = getUvSettingsFromFace(face, uvmap)
        for vert in verts:
            coords = vert.vert.co
            # UV offsets in mm notation (like 43 or 187)
            offU, offV = round(coords[0] * ux + coords[1] * uy + coords[2] * uz + modOffsetU), round(coords[0] * vx + coords[1] * vy + coords[2] * vz + modOffsetV)
            if addOffsets:
                offU = (offU + orig_uv[0] % bmpWidth)
                offV = (offV + orig_uv[1] % bmpHeight)

            if absolute:
                # UV offsets in blender notation (like 0.34 or 0.55)
                valU, valV = offU / bmpWidth, offV / bmpHeight
                vertU, vertV = valU - minU, valV - minV
            else:
                vertU = trunc(offU / float(bmpWidth), 1 / bmpWidth)
                vertV = trunc(offV / float(bmpHeight), 1 / bmpHeight)
            # apply changed uv
            face.loops[vert.loopIndex][uvmap].uv = (vertU, vertV)
    
    bmesh.update_edit_mesh(bpy.context.edit_object.data)
    return uOffset, vOffset

def matchUvToLastSelected(assignMaterial=False, absolute=False):
    bm = bmesh.from_edit_mesh(bpy.context.edit_object.data)
    bm.select_history.validate()
    faces = getSelectedFaces(bm)
    if len(faces) == 0:
        print("Nothing selected")
        return False
    last = bm.select_history.active or faces[len(faces) - 1]
    uvmap = bm.loops.layers.uv.verify()
    uv = getUvSettingsFromFace(last, uvmap)
    if uv == False:
        return False
    u, v = uv
    faces.remove(last)
    changeUvCoordinates(uOffset = u, vOffset = v, assignMaterial = last.material_index if assignMaterial else None, absolute = absolute)
    
    bmesh.update_edit_mesh(bpy.context.edit_object.data)
    return u, v

def getUvFromSelected():
    bm = bmesh.from_edit_mesh(bpy.context.edit_object.data)
    uvmap = bm.loops.layers.uv.verify()
    faces = getSelectedFaces(bm)
    if len(faces) == 0:
        return False
    return getUvSettingsFromFace(faces[len(faces) - 1], uvmap)

def getFirstAbsoluteVertexUv(face, faceData):
    minU, minV, minUVert, minVVert = None, None, [], []
    ux, uy, uz, vx, vy, vz = faceData[1]
    for vert in face.verts:
        valU = vert.co[0] * ux + vert.co[1] * uy + vert.co[2] * uz
        valV = vert.co[0] * vx + vert.co[1] * vy + vert.co[2] * vz
        
        if not minU or valU <= minU:
            minU = valU
        else:
            minUVert.clear()
        minUVert.append(vert)
        
        if not minV or valV <= minV:
            minV = valV
        else:
            minVVert.clear()
        minVVert.append(vert)

    vert = None
    for testVert in minUVert:
        if testVert in minVVert:
            vert = testVert
            break

    assert vert, "Two or more suitable vertices found"
    if vert:
        print("Single vert: {} {} {}, index: {}".format(*vert.co, vert.index))
    else:
        print("MinU vert: {} {} {}, index: {}\nMinV vert: {} {} {}, index: {}".format(*minUVert[0].co, minUVert[0].index, *minVVert[0].co, minVVert[0].index))
    bmpWidth, bmpHeight = faceData[2]
    minU = minU / bmpWidth
    minV = minV / bmpHeight
    return minU, minV

    
def test():
    bm = bmesh.mynew()
    faces = getSelectedFaces(bm)
    assert len(faces) == 1
    face = faces[0]
    uvmap = bm.loops.layers.uv.verify()
    data = getFaceData(face, uvmap)
    ux, uy, uz, vx, vy, vz = data[1]
        
    # get uv offsets needed to have texture's bottom left corner at found vertex
    minU, minV = getFirstAbsoluteVertexUv(face, data)
    
    width, height = data[2]
    # CHECK IF ROUNDING OR TRUNCATING IS NEEDED
    for changeVert in data[0]:
        valU = (changeVert.vert.co[0] * ux + changeVert.vert.co[1] * uy + changeVert.vert.co[2] * uz) / width
        valV = (changeVert.vert.co[0] * vx + changeVert.vert.co[1] * vy + changeVert.vert.co[2] * vz) / height
        face.loops[changeVert.loopIndex][uvmap].uv = (valU - minU, valV - minV)
            
    bmesh.update_edit_mesh(bpy.context.edit_object.data)

bpy.f.test = test
def getuv():
    bm = bmesh.mynew()
    return getUvDirections(getSelectedFaces(bm)[0].normal)
bpy.f.getuv = getuv
bpy.f.getUvDirections = getUvDirections
bpy.f.changeUvCoordinates = changeUvCoordinates

def genericPoll(context):
    obj = context.active_object
    return obj and obj.type == 'MESH' and obj.mode == 'EDIT' and len(getSelectedFaces(bmesh.from_edit_mesh(obj.data))) > 0

class MightAndMagicUvSet(bpy.types.Operator):
    """Set UV coordinates"""
    bl_idname = "mm.uv_set"
    bl_label = "Might and Magic UV set"
    bl_options = {'REGISTER', 'UNDO'}
    
    # GRAB TRAITS
    """
    1. always false when launching operator (setting different faces)
    2. when user checks, current coords are saved and coordinates turn to those of face before operator application (permanent, should persist between different launches)
    3. when is checked and coord settings are changed, checkbox is unchecked and coords are saved
    4. when unchecked by user, saved coords (or, if first uncheck, coordinates before application) are restored
    """
        
    # grab is false when launching new operator instance, idk why
    
    # both get and set required, otherwise won't work
    def getGrab(self):
        return False if "grabSettingsFromFace" not in self else self["grabSettingsFromFace"]
    def setGrab(self, value):
        self["grabSettingsFromFace"] = value
        print(value)
        if value:
            uv = getUvFromSelected()
            if not uv:
                print("fail")
                return
            self.prevUOffset, self.prevVOffset = self.uOffset, self.vOffset
            self.uOffset, self.vOffset = map(int, uv)
            self["grabSettingsFromFace"] = value
            print("new", self.uOffset, self.vOffset)
        else:
            self.uOffset, self.vOffset = self.prevUOffset, self.prevVOffset
        # square bracket notation is very important, otherwise property won't change!
    def updateUv(self, context):
        self["grabSettingsFromFace"] = False
    
    # current UV offsets
    uOffset: bpy.props.IntProperty(name="U offset", description="Like in editor", default=0,  update=updateUv)
    vOffset: bpy.props.IntProperty(name="V offset", description="Like in editor", default=0,  update=updateUv)
    
    # attempt to save offsets before grab settings is activated
    prevUOffset: bpy.props.IntProperty(default=0, options={'HIDDEN'})
    prevVOffset: bpy.props.IntProperty(default=0, options={'HIDDEN'})
    
    # Checkbox (maybe should really be a button) to grab current UV settings from face
    grabSettingsFromFace: bpy.props.BoolProperty(name="Grab settings from face", description="If disabled, simply sets coordinates. If enabled, gets original coords from face and then allows editing them", default=False, set=setGrab, get=getGrab)

    absolute: bpy.props.BoolProperty(name = "Absolute", default=False)

    @classmethod
    def poll(cls, context):
        return genericPoll(context)

    def execute(self, context):
        uv = map(int, changeUvCoordinates(uOffset = self.uOffset, vOffset = self.vOffset, absolute = self.absolute))
        if uv == False:
            return {'CANCELLED'}
        return {'FINISHED'}

    def invoke(self, context, event):
        return self.execute(context)
        
class MightAndMagicUvChangeModal(bpy.types.Operator):
    """Change UV coordinates"""
    bl_idname = "mm.uv_change_modal"
    bl_label = "Might and Magic UV change modal"
    bl_options = {'REGISTER', 'UNDO'}

    # sum of UV offsets which were applied to selected faces during operator run (to restore original ones later; properties don't auto revert upon cancel as with non-modal operators)
    uOffsetShift: bpy.props.IntProperty(options = {"HIDDEN"})
    vOffsetShift: bpy.props.IntProperty(options = {"HIDDEN"})
    
    # can set coords with mouse or keyboard
    mode: bpy.props.EnumProperty(items = [("MOUSE", "Mouse", "Use mouse to set UV coords instead of keyboard"),
                                          ("KEYBOARD", "Keyboard", "Use keyboard to set UV coords instead of mouse")],
                                 name = "Mode", description = "Determines whether coords are set by mouse or keyboard", default = "KEYBOARD", options = {"HIDDEN"})
    
    # if mode is mouse, allows "locking" movement to one UV axis
    uOnly: bpy.props.BoolProperty(options = {"HIDDEN"})
    vOnly: bpy.props.BoolProperty(options = {"HIDDEN"})
    
    # Used to "pass data" between modal and execute methods
    addOffsets: bpy.props.CollectionProperty(options = {"HIDDEN"})

    absolute: bpy.props.BoolProperty(name = "Absolute", default=False, options = {"HIDDEN"})

    @classmethod
    def poll(cls, context):
        return genericPoll(context)
    
    def setStatusText(self, context):
        text = "current mode: {} | M: switch mode | Ctrl (hold): bigger change | Alt (hold): smaller change".format(self.mode)
        if self.mode == "MOUSE":
            lock = "U" if self.uOnly else ("V" if self.vOnly else "NONE")
            text += " | Current lock: {} | U: change only U coord | V: change only V coord | C: clear constraints".format(lock)
        elif self.mode == "KEYBOARD":
            text += u" | \u2190 \u2192 \u2191 \u2193 change coords"
        context.workspace.status_text_set(text)

    def execute(self, context):
        self.uOffsetShift += self.addOffsets[0]
        self.vOffsetShift += self.addOffsets[1]
        uv = map(int, changeUvCoordinates(uOffset = self.addOffsets[0], vOffset = self.addOffsets[1], addOffsets=True))
        if uv == False:
            return {'CANCELLED'}
        self.addOffsets = [0, 0]
        context.area.header_text_set("U offset: {}\t\tV offset: {}".format(self.uOffsetShift, self.vOffsetShift))
        self.setStatusText(context)
        return {'FINISHED'}

    def clearTexts(self, context):
        context.area.header_text_set(None)
        context.workspace.status_text_set(None)
    
    def doCancel(self, context):
        self.addOffsets = [-self.uOffsetShift, -self.vOffsetShift]
        if self.mode == "KEYBOARD":
            self.uOnly = False
            self.vOnly = False
        self.execute(context)
        self.clearTexts(context)
    
    def modal(self, context, event):
        if event.type == "M" and "PRESS" in event.value:
            self.mode = "KEYBOARD" if self.mode == "MOUSE" else "MOUSE"
            self.setStatusText(context)
            return {"RUNNING_MODAL"}
        if event.type == "A" and event.value == "PRESS":
            self.absolute = not self.absolute
        
        if self.mode == "MOUSE":
            if event.type == 'MOUSEMOVE':
                delta_x = event.mouse_prev_x - event.mouse_x
                delta_y = event.mouse_prev_y - event.mouse_y
                divisor = 4
                if event.alt:
                    divisor *= 4
                elif event.ctrl:
                    divisor //= 4
                self.addOffsets = [0, 0]
                if not self.vOnly:
                    self.addOffsets[0] = delta_x // divisor
                if not self.uOnly:
                    self.addOffsets[1] = delta_y // divisor
                self.execute(context)
            elif event.type == "U":
                self.uOnly = True
                self.vOnly = False
            elif event.type == "V":
                self.uOnly = False
                self.vOnly = True
            elif event.type == "C":
                self.uOnly = False
                self.vOnly = False
            elif event.type == 'LEFTMOUSE':
                self.clearTexts(context)
                return {'FINISHED'}
            elif event.type in {'RIGHTMOUSE', 'ESC'}:
                self.doCancel(context)
                return {'CANCELLED'}
        elif self.mode == "KEYBOARD":
            add = 8
            if event.alt:
                add //= 8
            elif event.ctrl:
                add *= 8
            addWhat = [0, 0]
            if "PRESS" in event.value: # don't execute twice
                if event.type == "LEFT_ARROW":
                    addWhat[0] = add
                elif event.type == "RIGHT_ARROW":
                    addWhat[0] = -add
                elif event.type == "UP_ARROW":
                    addWhat[1] = -add
                elif event.type == "DOWN_ARROW":
                    addWhat[1] = add
                elif event.type == "RET": # enter key
                    self.clearTexts(context)
                    return {'FINISHED'}
            elif event.type == 'LEFTMOUSE':
                self.clearTexts(context)
                return {'FINISHED'}
            elif event.type in {'RIGHTMOUSE', 'ESC'}:
                self.doCancel(context)
                return {'CANCELLED'}
            self.addOffsets = addWhat
            self.execute(context)

        return {'RUNNING_MODAL'}

    def invoke(self, context, event):
        if context.object:
            self.uOffsetShift, self.vOffsetShift = 0, 0
            context.window_manager.modal_handler_add(self)
            return {'RUNNING_MODAL'}
        else:
            self.report({'WARNING'}, "No active object, could not finish")
            return {'CANCELLED'}

class MightAndMagicUvMatch(bpy.types.Operator):
    """Match UV coordinates to those of last selected face"""
    bl_idname = "mm.uv_match"
    bl_label = "Might and Magic UV match"
    bl_options = {'REGISTER', 'UNDO'}
    
    assignMaterial: bpy.props.BoolProperty(name="Assign material", description="If enabled, material of last selected face is assigned", default=True)
    absolute: bpy.props.BoolProperty(name="Absolute", description="If disabled, UV coords are affected by vertex coords, which means same texture matched on two faces might look different.", default=False)

    @classmethod
    def poll(cls, context):
        return genericPoll(context)

    def execute(self, context):
        u, v = matchUvToLastSelected(assignMaterial=self.assignMaterial, absolute=self.absolute)
        return {'FINISHED'}

    def invoke(self, context, event):
        return self.execute(context)

def menu_func_set(self, context):
    self.layout.operator(MightAndMagicUvSet.bl_idname, text=MightAndMagicUvSet.bl_label)

def menu_func_change_modal(self, context):
    self.layout.operator(MightAndMagicUvChangeModal.bl_idname, text=MightAndMagicUvChangeModal.bl_label)
    
def menu_func_match(self, context):
    self.layout.operator(MightAndMagicUvMatch.bl_idname, text=MightAndMagicUvMatch.bl_label)

# Register and add to the "uv" menu
addon_keymaps = []
def register():
    bpy.utils.register_class(MightAndMagicUvSet)
    bpy.types.VIEW3D_MT_uv_map.append(menu_func_set)

    bpy.utils.register_class(MightAndMagicUvChangeModal)
    bpy.types.VIEW3D_MT_uv_map.append(menu_func_change_modal)
    
    bpy.utils.register_class(MightAndMagicUvMatch)
    bpy.types.VIEW3D_MT_uv_map.append(menu_func_match)

def unregister():
    bpy.utils.unregister_class(MightAndMagicUvSet)
    bpy.types.VIEW3D_MT_uv_map.remove(menu_func_set)
    
    bpy.utils.unregister_class(MightAndMagicUvChangeModal)
    bpy.types.VIEW3D_MT_uv_map.remove(menu_func_change_modal)
    
    bpy.utils.unregister_class(MightAndMagicUvMatch)
    bpy.types.VIEW3D_MT_uv_map.remove(menu_func_match)

if __name__ == "__main__":
    register()