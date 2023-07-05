import bpy, math, mathutils, bmesh
from decimal import Decimal
from sys import float_info
from re import sub
from json import dumps
# TODO: clean up imports, operator (for favorites menu), change all selected, specify offset, arrow keys to change uv (like in editor), absolute offset for all uvs as option (relative to 0/0/0)
class dotdict(dict):
    """dot.notation access to dictionary attributes"""
    __getattr__ = dict.get
    __setattr__ = dict.__setitem__
    __delattr__ = dict.__delitem__
    
invalidateCache = False
#invalidateCache = True
if not hasattr(bpy, "f") or not hasattr(bpy, "v") or invalidateCache:
    bpy.f = dotdict()
    bpy.v = dotdict()
    invalidateCache = True

def changeShaderNodeScale(s):
    for material in bpy.data.materials:
        if material.node_tree != None:
            for node in material.node_tree.nodes:
                if node.bl_static_type == "MAPPING":
                    node.inputs[3].default_value = (-200, -192.6, -7.0)
                    
bpy.f.changeShaderNodeScale = changeShaderNodeScale

#for obj in bpy.context.selected_objects:
#    obj.name = re.sub(r"\.\d{3}", "", obj.name)
#    obj.data.name = re.sub(r"\.\d{3}", "", obj.data.name)

#for vert in bpy.context.active_object.data.vertices:
#    c = vert.co
#    c2 = (math.floor(c[0]), math.floor(c[1]), math.floor(c[2]))
#    if c != c2:
#        a.a.a = 5
#    vert.co = c2

def find_area():
    try:
        for a in bpy.data.window_managers[0].windows[0].screen.areas:
            if a.type == "VIEW_3D":
                return a
        return None
    except:
        return None

bpy.f.find_area = find_area
area = find_area()

if area is None:
    print("area not find")
    def _():
        pass
    bpy.f.move = _
else:
    r3d = area.spaces[0].region_3d
    def move(x, y, z):
        r3d.view_location = (x, y, z)
    bpy.f.move = move

# load vertices from file in form:
# 1 2 3\n
# 2 3 4\n
# 5 6 7\n
# returns: list of tuples, each tuple is one vertex coords
def loadVertices(fileName):
    try:
        file = open(fileName, "r")
    except:
        print("Couldn't load file {}!" % (fileName))
        return []
    
    verts = file.read().split("\n")
    for i in range(0, len(verts)):
        verts[i] = tuple(map(float, verts[i].split()))
        
    return verts

def matchNewWithOld():
    m = bpy.context.object.matrix_world
    oldVertices = loadVertices("C:\\Users\\Eksekk\\Desktop\\test.txt")
    # old vertices positions are global

    # list of tuples of form (x, y, z, vertex_id)
    # @ is matrix multiplication (need to multiply with matrix_world
    # to get real coordinates)
    # * operator unpacks list/vector/tuple etc.
    newVertices = [tuple([*(m @ elem.co), elem.index]) for elem in bpy.context.object.data.vertices]

    # list of tuples of form (new vertex id, [old vertices ids])
    matches = [None] * len(newVertices)
    cmp = 5 # no sqrt, don't sqrt distance either for faster computation
    for oldId in range(0, len(oldVertices)):
        old = oldVertices[oldId]
        for newId in range(0, len(newVertices)):
            new = newVertices[newId]
            #if mathutils.Vector((old[0] - new[0], old[1] - new[1], old[2] - new[2])).length_squared <= cmp:
            if (old[0] - new[0]) ** 2 + (old[1] - new[1]) ** 2 + (old[2] - new[2]) ** 2 <= cmp:
                if matches[newId] is None:
                    matches[newId] = (newId, [oldId])
                else:
                    matches[newId][1].append(oldId)
    
    return (oldVertices, newVertices, matches)

if not hasattr(bpy, "f") or not hasattr(bpy, "v") or invalidateCache:
    #oldVertices, newVertices, matches = matchNewWithOld()
    #bpy.v.oldVertices = oldVertices
    #bpy.v.newVertices = newVertices
    #bpy.v.matches = matches
    #bpy.v.multimatches = [m for m in matches if m is not None and len(m[1]) > 1]
    pass
else:
    #oldVertices, newVertices, matches = bpy.v.oldVertices, bpy.v.newVertices, bpy.v.matches
    pass


# t - tuple from above function's matches
def getDists(t):
    return [(mathutils.Vector(oldVertices[x]) - bpy.context.object.data.vertices[t[0] ].co).length for x in t[1] ]

def writeMultimatchDataToFile(fileName):
    try:
        file = open(fileName, "w")
    except:
        print("Couldn't open file {}!" % (fileName))
        return
    
    for mmatch in bpy.v.multimatches:
        new = bpy.context.object.data.vertices[mmatch[0] ].co
        file.write("Vertex {} (coords: {}, {}, {})\n".format(mmatch[0], *new))
        file.write("Matching vertices: " + ", ".join(map(str, mmatch[1])) + "\nTheir coords:\n")
        for vid in mmatch[1]:
            coords = map(lambda x: str(round(x, 2)), oldVertices[vid])
            length = (new - mathutils.Vector(oldVertices[vid])).length
            file.write("    {}: {} {} {}, distance: {}\n".format(str(vid), *coords, round(length, 2)))
        
        file.write("\n\n")
    
    file.close()
bpy.f.getDists = getDists
#writeMultimatchDataToFile("C:\\Users\\Eksekk\\Desktop\\test2.txt")

# launch while in object mode and object selected!
def restoreOldCoordinates():
    maxDistChange = -999
    
    maxCoordsDiff = [-5, -5, -5]
    mat = bpy.context.object.matrix_world.inverted()
    for new in newVertices:
        newId = new[3]
        if matches[newId] is None:
            continue
        
        matchVerts = [mathutils.Vector(oldVertices[oldId]) for oldId in matches[newId][1] ]
        new = mathutils.Vector(new[:-1]) # cut off vertex id
        minVal = 999
        minIndex = -1
        for i in range(0, len(matchVerts)):
            for j in range(0, 3):
                maxCoordsDiff[j] = max(maxCoordsDiff[j], abs(new[j] - oldVertices[matches[newId][1][i] ][j]))
            dist = (new - matchVerts[i]).length
            if dist < minVal:
                minVal = dist
                minIndex = i
        
        if maxDistChange < minVal:
            maxDistChange = minVal
            max1, max2 = new, matchVerts[minIndex]
        
        bpy.context.object.data.vertices[newId].co = mat @ matchVerts[minIndex]
    
    print("Maximum changed distance: {} (coords: ({}, {}, {}), ({}, {}, {}))\nMax coords differences: {}, {}, {}".format(round(maxDistChange, 3),
        *max1, *max2, *maxCoordsDiff))
    bpy.context.view_layer.update()
    
bpy.f.restoreOldCoordinates = restoreOldCoordinates

def approximatelyEqual(a: float, b: float, epsilon: float):
    return abs(a - b) <= max(abs(a), abs(b)) * epsilon

# round in new python rounds "half to even", and I want
# "half away from zero"
# returns tuple (rounded value, amount that was added to round value)
FLOAT_EPS = Decimal(2 ** -23)
def myround(n):
    if n is not Decimal:
        n = Decimal(n)
    #n += FLOAT_EPS * n
    n2 = n.quantize(1, rounding=decimal.ROUND_HALF_UP)
    return n2, n2 - n

def myceil(n):
    #n += FLOAT_EPS * n
    n2 = n.quantize(1, rounding=decimal.ROUND_UP)
    return n2, n2 - n

def myfloor(n):
    #n += FLOAT_EPS * n
    n2 = n.quantize(1, rounding=decimal.ROUND_DOWN)
    return n2, n2 - n

bpy.f.myround = myround
    
def testMyround() -> bool:
    return True
    print("Testing myround function")
    tests = [(0.999999, 1), (0.9, 1), (0.6, 1), (0.500000001, 1), (0.5, 1), (0.4999999, 0), (0.4, 0), (0.2, 0), (0.0000000001, 0)]
    passed = True
    for sign in range(1, -2, -2):
        signCharacter = (sign == -1) and "-" or ""
        for i in range(0, len(tests)):
            test, exp, ansround, ansdiff = sign * tests[i][0], sign * tests[i][1], *myround(tests[i][0])
            ansround, ansdiff = sign * ansround, sign * ansdiff
            if not math.isclose(exp, ansround, rel_tol=sys.float_info.epsilon):
                passed = False
                print("Test {}{} failed (test: {}, expected: {}, received: {}, diff: {})".format(signCharacter, i, test, exp, ansround, ansdiff))
            else:
                print("Test {}{} passed (test: {}, expected: {}, received: {}, diff: {})".format(signCharacter, i, test, exp, ansround, ansdiff))
    
    if passed:
        print("All tests passed")
    return passed

# changes vertex coordinates so that rounded length of one-world-axis
# edges doesn't change or (very very rarely) changes by 1
# verts = list of lists of form [index, single coordinate]
def integerizeCoordinates(oldVerts, coord, file):
#   l = len(verts)
    verts = [ [t[0], Decimal(t[1])] for t in sorted(oldVerts, key=lambda t: t[1])]
#    if "dists" not in bpy.v:
#        bpy.v.dists = [ [], [], [] ]
#        if len(bpy.v.dists[coord]) == 0:
#            bpy.v.dists[coord] = [None] * l ** 2
#            dists = bpy.v.dists[coord]
#            for v1 in verts:
#                for v2 in verts:
#                    dists[v1[0] * l + v2[0] ] = myround(abs(v1[1] - v2[1]))[0]
#    
#    dists = bpy.v.dists[coord]
    distsByVertPair = [Decimal(verts[i][1] - verts[i - 1][1]) for i in range(1, len(verts))]
    fractionalDistsByVertPair = [x % Decimal(1) for x in distsByVertPair]
    print(fractionalDistsByVertPair)
    
    diff = Decimal(0)
    # 0.7 - 1
    # 0.5 - 1
    # 0.3 - 1
    #-0.3 - 0
    #-0.5 - -1
    #-0.7 - -1
    maxdiff = Decimal(0)
    def myprint(s):
        print(s)
        file.write(s)
    
    myprint("Coordinate {}".format(coord))
    dabs = decimal.getcontext().abs
    
    for i in range(len(verts)):
        old = verts[i][1]
        ansround, ansdiff = myround(verts[i][1])
        diff += ansdiff
        myprint(json.dumps({"old_distance": distsByVertPair[i - 1] if i > 0 else 0, "new_distance": abs(ansround - verts[i - 1][1]) if i > 0 else 0, "old_coord": old, "coord_with_diff": verts[i][1], "new_coord": ansround, "current_diff": ansdiff, "full_diff": diff}, indent=4, default=str))
        assert dabs(dabs(ansround - verts[i - 1][1]) - distsByVertPair[i - 1] if i > 0 else 0) <= 1, file.close()
        verts[i][1] = ansround
        maxdiff = maxdiff.max(dabs(diff))
    
    # don't do oldVerts = verts, because assignment doesn't propagate through function argument reference,
    # workaround is to modify it so that you don't reassign new list, but instead modify it
    print("Maxdiff: {}".format(maxdiff))
    oldVerts.clear()
    oldVerts += verts
    
def test():
    t = [ [0, 1.2], [1, 1.5], [2, 1.9], [3, 2.4], [4, 3.2], [5, 5.6] ]
    print("original", t)
    integerizeCoordinates(t, 0)
    print("modified", t)

bpy.f.test = test

seams = {}
# launch from object mode
def integerizeCoordinatesFull(dry=True):
    if not testMyround():
        return
    O = bpy.context.object
    V = O.data.vertices
    originalEdgeLengths = [Decimal((V[edge.vertices[0] ].co - V[edge.vertices[1] ].co).length) for edge in O.data.edges]
    
    # list of form:
    # [ [list of [vertex index, x coordinate] ], list of [vertex index, y coordinate], list of [vertex index, z coordinate] ]
    vertsByCoord = [ [ [vert.index, Decimal(vert.co[i]) ] for vert in O.data.vertices] for i in range(0, 3)]
    
    file = open(r"C:\Users\Eksekk\Desktop\output blender.txt", "w+")
    integerizeCoordinates(vertsByCoord[0], 0, file)
    integerizeCoordinates(vertsByCoord[1], 1, file)
    integerizeCoordinates(vertsByCoord[2], 2, file)
    
    # list of same form as previous, just sorted by vertex index
    vertCoords = [sorted(vertsByCoord[coord], key=lambda v: v[0]) for coord in range(0, 3)]
    for i in range(len(V)):
        assert vertCoords[0][i][0] == i and vertCoords[1][i][0] == i and vertCoords[2][i][0] == i
        assert isinstance(vertCoords[0][i][1], Decimal) and isinstance(vertCoords[1][i][1], Decimal) and isinstance(vertCoords[2][i][1], Decimal)
    assert vertCoords[0][457][0] == 457, vertCoords[0][457][0]
    #print(vertCoords[0])
    
    coordnames = ("X", "Y", "Z")
    dabs = decimal.getcontext().abs
    lmaxdiff, lmindiff, lavgdiff = Decimal(-10), Decimal(10), Decimal(0)
    lendiffs = []
    lens = []
    lens2 = []
    oneaxnum = Decimal(0)
    diffs = []
    for edge in O.data.edges:
        EV = edge.vertices
        len1 = originalEdgeLengths[edge.index]
        lens.append(len1)
        len2 = Decimal(0)
        oneax = True
        diffnum = 0
        newlen = Decimal(0)
        sqrt3 = Decimal(3).sqrt() + Decimal("0.1")
        for coord in range(3):
            newlen += decimal.getcontext().power(myround(vertCoords[coord][EV[0] ][1] - vertCoords[coord][EV[1] ][1])[0], Decimal(2))
            if dabs(myround(vertCoords[coord][EV[0] ][1] - vertCoords[coord][EV[1] ][1])[0]) > sqrt3 * Decimal(2):
                diffnum += 1
                #print(dabs(myround(dabs(vertCoords[coord2][EV[0] ][1] - vertCoords[coord2][EV[1] ][1]))[0]), EV[0], EV[1], vertCoords[coord2][EV[0] ], vertCoords[coord2][EV[1] ], coord, coord2)
        
        newlen = newlen.sqrt()
        oneax = diffnum <= 1
        diff = myround(dabs(originalEdgeLengths[edge.index] - newlen))[0]
        assert diff <= Decimal(2), json.dumps({"diff": diff, "edge_index": edge.index, "orig_len": originalEdgeLengths[edge.index], "new_len": newlen, "old_coords": [[*map(int, V[EV[0] ].co)], [*map(int, V[EV[1] ].co)]], "new_coords": [ [vertCoords[coord][EV[i] ][1] for coord in range(3)] for i in range(2)], }, indent=4, default=str)
        if diff >= Decimal(1):
            seams[edge.index] = True
            pass
        if oneax:
            oneaxnum += Decimal(1)
        diffs.append(diff)
        
        """
        assert isinstance(vertCoords[coord][EV[0] ][1], Decimal) and isinstance(vertCoords[coord][EV[1] ][1], Decimal)
        len2 += decimal.getcontext().power(vertCoords[coord][EV[0] ][1] - vertCoords[coord][EV[1] ][1], Decimal(2))
        len2 = len2.sqrt()
        lens2.append(len2)
        #if abs(len1 - len2) > 50:
        #    print([[*map(int, V[EV[0] ].co)], [*map(int, V[EV[1] ].co)]])
        #    print([ [vertCoords[coord][EV[i] ][1] for coord in range(3)] for i in range(2)])
        #    print(len1, len2)
        lendiffs.append(decimal.getcontext().abs(len1 - len2))
        lmaxdiff = lmaxdiff.max(decimal.getcontext().abs(len1 - len2))
        lavgdiff += decimal.getcontext().abs(len1 - len2)
        lmindiff = lmindiff.min(decimal.getcontext().abs(len1 - len2))
        """
    """
    lendiffs.sort(reverse=True)
    print("Coordinates XYZ")
    print("Edge length differences: {} (max) {} (min), {} (avg)\n".format(lmaxdiff, lmindiff,
    (lavgdiff / Decimal(len(bpy.context.object.data.edges))).quantize(Decimal("0.0001"), rounding=decimal.ROUND_HALF_UP)))
    print("Top 30 greatest edge length differences:")
    print("\n".join(map(lambda x: decimal.getcontext().to_sci_string(x.quantize(Decimal("0.1"), rounding=decimal.ROUND_HALF_UP)), lendiffs)))
    """
    print("One axis edges: {}".format(oneaxnum))
    diffs.sort()
    file.write("\n" + "\n".join(map(str, diffs)))
    file.close()
    """
    print("Another max: {}".format(max(lendiffs)))
    print(sorted(lens[-5:]))
    print(sorted(lens2[-5:]))
    coords = [(x[1], y[1], z[1]) for x, y, z in zip(*vertCoords)]
    output = []
    for edge in bpy.context.object.data.edges:
        l = []
        for i in range(3):
            l += [V[edge.vertices[0] ].co[i], V[edge.vertices[1] ].co[i] ]
        for i in range(3):
            l += [vertCoords[i][edge.vertices[0] ][1], vertCoords[i][edge.vertices[1] ][1] ]
        output.append("sqrt(({} - {})^2 + ({} - {})^2 + ({} - {})^2) - sqrt(({} - {})^2 + ({} - {})^2 + ({} - {})^2)".format(*map(lambda num: str(Decimal(num).quantize(Decimal("0.01"), rounding=decimal.ROUND_HALF_UP)), l)))
    print("\n\n".join(output[-5:]))"""
    if not dry:
        for vert in V:
            i = vert.index
            vert.co[0], vert.co[1], vert.co[2] = float(vertCoords[0][i][1]), float(vertCoords[1][i][1]), float(vertCoords[2][i][1])
    

bpy.f.integerizeCoordinatesFull = integerizeCoordinatesFull

def toggleSeams():
    for edge in bpy.context.object.data.edges:
        if edge.index in seams:
            edge.use_seam = not edge.use_seam

bpy.f.toggleSeams = toggleSeams

def selectConcave():
    obj = bpy.context.edit_object
    if obj is None:
        return
    me = obj.data

    bm = bmesh.from_edit_mesh(me)
    bm.faces.active = None

    for face in bm.faces:
        face.select_set(False)
        for loop in face.loops:
            if not loop.is_convex:
                face.select_set(True)
                break

    bmesh.update_edit_mesh(me, destructive=False)
    
bpy.f.selectConcave = selectConcave

bpy.f.dir = lambda x: print("\n".join(dir(x)))

#works correctly only in object mode
#D.meshes["zddb04"].uv_layers[0].data.__len__()

# print(bm.faces.active)
#x = bm.loops.layers.uv["UVMap"]
#bm = bmesh.from_edit_mesh(C.edit_object.data)

################
# bm.faces.active.loops[3][x]

def loops():
    bm = bmesh.from_edit_mesh(bpy.context.edit_object.data)
    uvmap = bm.loops.layers.uv["UVMap"]
    for loop in bm.faces.active.loops:
        index, x, y, z = loop.vert.index, *loop.vert.co
        print("Vert {}, coords: {} {} {}".format(*(map(lambda x: x, (index, x, y, z)))))
        print("U: {}, V: {}".format(*(map(lambda x: x, loop[uvmap].uv))))
        
bpy.f.loops = loops

def editVertUv(index, u, v):
    bm = bmesh.from_edit_mesh(bpy.context.edit_object.data)
    uvmap = bm.loops.layers.uv["UVMap"]
    for loop in bm.faces.active.loops:
        if loop.vert.index == index:
            loop[uvmap].uv = (u, v)
            break
        
    bmesh.update_edit_mesh(bpy.context.edit_object.data, destructive=False)
    
bpy.f.editVertUv = editVertUv

bpy.f.dirp = print