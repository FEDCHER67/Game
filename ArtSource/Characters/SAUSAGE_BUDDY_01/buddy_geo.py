"""Geometry helpers for the Sausage Buddy builder (Blender 5.2). Z up, -Y forward, metres."""
import math
import bpy, bmesh
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree
from mathutils.geometry import delaunay_2d_cdt

COLLECTION = None
MATS = {}
PART_TRIS = {}      # part object name -> triangles, recorded by join() for the per-part report
RANGES = {}         # joined object name -> [(part name, first vertex, vertex count)], for drop()

# Resolution per procedural part. 'full' = the v03 geometry (every builder default); 'crowd' (v04+) replaces the
# Catmull-Clark pass with denser exact rings where the silhouette needs them and drops hidden detail.
LODS = {
    'full': {},
    'crowd': {
        'head': dict(seg=32, subdiv=0, dome=8), 'nose': dict(seg=16, rings=10), 'ear': dict(seg=12, rings=8),
        'ear_inner': dict(seg=10, rings=6), 'torso': dict(seg=16, subdiv=0), 'arm': dict(seg=12, subdiv=0),
        'palm': dict(seg=20, subdiv=0), 'finger': dict(seg=12, subdiv=0), 'leg': dict(seg=16, subdiv=0),
        'eye': dict(seg=16, rings=10), 'pupil': dict(seg=12, rings=8), 'shine': dict(seg=8, rings=6),
        'brow': dict(seg=6), 'mouth': dict(seg=6),
        'top': dict(n=32, subdiv=0), 'hood': dict(seg=16, subdiv=0), 'hood_pouch': dict(seg=16, rings=10),
        'cord': dict(seg=6), 'bottoms': dict(n=24, subdiv=0, crotch=0.95), 'socks': dict(seg=12),
        'sole': dict(seg=12, subdiv=0, round_ends=True), 'upper': dict(seg=14, subdiv=0, round_ends=True), 'lace': dict(seg=4),
        'cap_crown': dict(seg=32, rows=8), 'cap_peak': dict(u=10, v=4), 'cap_button': dict(seg=10, rings=6),
        'tongue': dict(seg=12, rings=8), 'big_decal': dict(step=0.020),
    },
    # v05: ~6-7.5k tris. The face (eyes, rims, pupils, shines, brows, mouth) keeps the 'crowd' resolution; the head ring is
    # dense only across the face (front +-56 deg); hands, clothes and shoes get far fewer rings; skin hidden under the
    # clothes is built (the clothes take their weights from it) and then dropped ('drop', per variant).
    'low': {
        'head': dict(seg=24, subdiv=0, dome=7, front=(56.25, 10),
                     rows=((1.10, 0.66), (1.17, 0.88), (1.215, 0.99), (1.25, 1.0), (1.608, 1.0))),
        'nose': dict(seg=14, rings=9), 'ear': dict(seg=10, rings=6), 'ear_inner': dict(seg=8, rings=5),
        'torso': dict(seg=12, subdiv=0),
        'arm': dict(seg=10, subdiv=0, rows=((.10, .046), (.21, .046), (.32, .044), (.40, .042), (.46, .040), (.54, .037),
                                             (.62, .033), (.645, .031))),
        'palm': dict(seg=12, subdiv=0, rows=((.625, .032, .029), (.645, .045, .030), (.668, .054, .030), (.705, .058, .028), (.744, .052, .024),
                                             (.754, .044, .021))),
        'finger': dict(seg=8, subdiv=0, shaft=3, tip=3),
        'leg': dict(seg=10, subdiv=0, cap_start=False, cap_end=False,
                    rows=((.72, .055), (.60, .051), (.52, .048), (.44, .046), (.36, .044), (.28, .043), (.20, .041))),
        'eye': dict(seg=16, rings=10), 'pupil': dict(seg=12, rings=8), 'shine': dict(seg=8, rings=6),
        'brow': dict(seg=6), 'mouth': dict(seg=6),
        'top': dict(n=16, subdiv=0),
        'hoodie': dict(arm_row=5, cuff_from=6,
                       rows=((.735, .184, .126, -.012), (.750, .192, .132, -.012), (.770, .204, .140, -.014), (.86, .211, .147, -.016),
                             (.98, .212, .149, -.012), (1.10, .218, .152, 0.0), (1.17, .218, .156, .002), (1.235, .206, .158, .002),
                             (1.255, .174, .165, .002), (1.266, .162, .160, .002), (1.246, .157, .152, .002)),
                       sleeve=((.22, .080), (.30, .076), (.38, .073), (.44, .070), (.50, .068), (.575, .064),
                               (.586, .056), (.622, .054), (.630, .049), (.620, .045))),
        'tee': dict(arm_row=4,
                    rows=((.795, .188, .126, -.010), (.806, .192, .128, -.010), (.90, .194, .130, -.012), (1.02, .194, .130, -.008),
                          (1.10, .200, .140, 0.0), (1.17, .198, .146, .002), (1.235, .186, .150, .002), (1.253, .158, .154, .001),
                          (1.259, .151, .146, 0), (1.250, .149, .142, 0)),
                    sleeve=((.212, .074), (.27, .068), (.325, .064), (.338, .062), (.332, .057))),
        'hood': dict(seg=12, subdiv=0, rings=13), 'hood_pouch': dict(seg=10, rings=6),
        'cord': dict(seg=4), 'pocket': dict(step=0.045, edge=0.045),
        'bottoms': dict(n=16, subdiv=0, crotch=0.95),
        'shorts_a': dict(legs=((.66, .082), (.600, .077), (.606, .071))),
        'cargo_b': dict(legs=((.62, .092), (.505, .088), (.492, .083), (.499, .078))),
        'socks': dict(seg=10, base=(0.120,), lip=False),
        'shoe': dict(ys=(0.096, 0.060, 0.022, -0.020, -0.075, -0.130, -0.184, -0.218, -0.231), bottom=2),
        'sole': dict(seg=8, subdiv=0, round_ends=True), 'upper': dict(seg=9, subdiv=0, round_ends=True),
        'lace': dict(seg=3, pts=3, caps=False), 'shoe_stripe': dict(step=0.05, edge=0.02), 'toe_cap': dict(n=7, step=0.03),
        'cap_crown': dict(seg=16, rows=5), 'cap_peak': dict(u=8, v=2), 'cap_button': dict(seg=6, rings=4),
        'print': dict(n=12, grill=6, shine=8, step=0.02), 'text': dict(resolution=2),
        'cargo_pocket': dict(step=0.026, edge=0.026), 'cargo_flap': dict(step=0.03, edge=0.028),
        'tongue': dict(seg=12, rings=8),
        # hidden skin, removed after the clothes copied its weights: (part, test, value); test on the rest-pose position
        'drop': {'A': (('Skin_Torso', None, 0), ('Skin_Arm', 'absx<', 0.55)),
                 'B': (('Skin_Torso', None, 0), ('Skin_Arm', 'absx<', 0.15), ('Skin_Head', 'z>', 1.69))},
    },
}
LOD = LODS['full']


def res(part, **defaults):
    """Resolution of a procedural part: the builder's v03 defaults unless the active LOD overrides them."""
    out = dict(defaults)
    out.update(LOD.get(part, {}))
    return out


def srgb(c):
    return tuple(((v / 255) / 12.92 if v / 255 <= 0.04045 else ((v / 255 + 0.055) / 1.055) ** 2.4) for v in c) + (1.0,)


def mat(name, rgb, rough=0.6, sss=0.0):
    if name in MATS:
        return MATS[name]
    m = bpy.data.materials.new(name)
    try:
        m.use_nodes = True
    except Exception:
        pass
    b = next(n for n in m.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
    b.inputs['Base Color'].default_value = srgb(rgb)
    b.inputs['Roughness'].default_value = rough
    if 'Specular IOR Level' in b.inputs:
        b.inputs['Specular IOR Level'].default_value = 0.35
    if sss and 'Subsurface Weight' in b.inputs:
        b.inputs['Subsurface Weight'].default_value = sss
        b.inputs['Subsurface Radius'].default_value = (0.9, 0.45, 0.3)
        if 'Subsurface Scale' in b.inputs:
            b.inputs['Subsurface Scale'].default_value = 0.03
    m.diffuse_color = srgb(rgb)
    MATS[name] = m
    return m


def link(ob):
    COLLECTION.objects.link(ob)
    return ob


def from_bm(name, bm, material, smooth=True, extra=()):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me); bm.free()
    me.materials.append(material)
    for m in extra:
        me.materials.append(m)
    ob = link(bpy.data.objects.new(name, me))
    for p in me.polygons:
        p.use_smooth = smooth
    return ob


def from_data(name, vs, fs, material, smooth=True, mat_index=None, extra=(), subdiv=0, fix_normals=True):
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(v) for v in vs], [], [tuple(f) for f in fs])
    me.update()
    me.materials.append(material)
    for m in extra:
        me.materials.append(m)
    if mat_index is not None:
        for p, i in zip(me.polygons, mat_index):
            p.material_index = i
    ob = link(bpy.data.objects.new(name, me))
    bm = bmesh.new(); bm.from_mesh(me)
    for v in [v for v in bm.verts if not v.link_faces]:
        bm.verts.remove(v)
    if fix_normals:
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(me); bm.free()
    if subdiv:
        subdivide(ob, subdiv)
    for p in ob.data.polygons:
        p.use_smooth = smooth
    return ob


def apply_mods(ob):
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(ob.evaluated_get(dg), preserve_all_data_layers=True, depsgraph=dg)
    ob.modifiers.clear()
    old = ob.data; ob.data = me
    bpy.data.meshes.remove(old)


def subdivide(ob, levels=1):
    m = ob.modifiers.new('Sub', 'SUBSURF'); m.levels = levels; m.render_levels = levels
    apply_mods(ob)
    for p in ob.data.polygons:
        p.use_smooth = True


def solidify(ob, thickness, offset=-1.0):
    m = ob.modifiers.new('Thick', 'SOLIDIFY'); m.thickness = thickness; m.offset = offset
    m.use_even_offset = True; m.use_rim = True
    apply_mods(ob)


def bridge(fs, a, b, closed=True):
    n = len(a)
    for j in range(n if closed else n - 1):
        fs.append((a[j], a[(j + 1) % n], b[(j + 1) % n], b[j]))


def ellipsoid(name, center, radii, material, rot=None, seg=16, rings=10, smooth=True):
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=seg, v_segments=rings, radius=1.0)
    r = (rot or Matrix.Identity(3)).to_4x4()
    bmesh.ops.transform(bm, matrix=Matrix.Translation(center) @ r @ Matrix.Diagonal((*radii, 1.0)), verts=bm.verts)
    return from_bm(name, bm, material, smooth)


def ring_angles(seg, front=None):
    """Ring vertex angles. front=(half_deg, n): n even steps across +-half_deg around -v (the face side), the rest spread
    over the back. Symmetric in u."""
    if not front:
        return [2 * math.pi * j / seg for j in range(seg)]
    half, n = math.radians(front[0]), front[1]
    a0 = -math.pi / 2 - half
    out = [a0 + 2 * half * j / n for j in range(n)]
    back = seg - n
    return out + [-math.pi / 2 + half + (2 * math.pi - 2 * half) * j / back for j in range(back)]


def loft(name, sections, material, seg=16, cap_start=True, cap_end=True, subdiv=0, smooth=True, mat_rows=None, extra=(), front=None):
    """sections: list of (center Vector, axis_u Vector, axis_v Vector, ru, rv) -> rings bridged in order."""
    vs, fs, rings, idx = [], [], [], []
    angles = ring_angles(seg, front)
    for c, u, v, ru, rv in sections:
        ring = []
        for a in angles:
            ring.append(len(vs)); vs.append(Vector(c) + Vector(u) * (ru * math.cos(a)) + Vector(v) * (rv * math.sin(a)))
        rings.append(ring)
    for k, (a, b) in enumerate(zip(rings, rings[1:])):
        bridge(fs, a, b)
        idx += [mat_rows[k] if mat_rows else 0] * seg
    if cap_start:
        c0 = len(vs); vs.append(sum((vs[i] for i in rings[0]), Vector()) / seg)
        for j in range(seg):
            fs.append((rings[0][(j + 1) % seg], rings[0][j], c0)); idx.append(mat_rows[0] if mat_rows else 0)
    if cap_end:
        c1 = len(vs); vs.append(sum((vs[i] for i in rings[-1]), Vector()) / seg)
        for j in range(seg):
            fs.append((rings[-1][j], rings[-1][(j + 1) % seg], c1)); idx.append(mat_rows[-1] if mat_rows else 0)
    return from_data(name, vs, fs, material, smooth, idx, extra, subdiv)


def tube(name, path, radius, material, seg=8, caps=True, subdiv=0, frame_up=None):
    """Round tube along a polyline. radius may be a float or f(i, n)."""
    P = [Vector(p) for p in path]
    secs = []
    up = Vector(frame_up) if frame_up else None
    for i, p in enumerate(P):
        t = (P[min(i + 1, len(P) - 1)] - P[max(i - 1, 0)]).normalized()
        a = (up.cross(t)).normalized() if up and abs(up.dot(t)) < 0.99 else t.orthogonal().normalized()
        b = t.cross(a).normalized()
        r = radius(i, len(P)) if callable(radius) else radius
        secs.append((p, a, b, r, r))
    return loft(name, secs, material, seg, caps, caps, subdiv)


def join(target, parts):
    """Join mesh objects into target (world space), keeping materials and vertex groups by name."""
    PART_TRIS.setdefault(target.name, sum(len(f.vertices) - 2 for f in target.data.polygons))
    ranges = RANGES.setdefault(target.name, [(target.name, 0, len(target.data.vertices))])
    for p in parts:
        mw = target.matrix_world.inverted() @ p.matrix_world
        names = [m.name for m in target.data.materials]
        for m in p.data.materials:
            if m.name not in names:
                target.data.materials.append(m); names.append(m.name)
        remap = [names.index(m.name) for m in p.data.materials]
        bm = bmesh.new(); bm.from_mesh(target.data)
        off = len(bm.verts)
        pb = bmesh.new(); pb.from_mesh(p.data)
        dl = pb.verts.layers.deform.active
        if dl is not None:          # weights are re-added by group name below
            pb.verts.layers.deform.remove(dl)
        bmesh.ops.transform(pb, matrix=mw, verts=pb.verts)
        for f in pb.faces:
            f.material_index = remap[f.material_index]
        tmp = bpy.data.meshes.new('tmp'); pb.to_mesh(tmp); pb.free()
        PART_TRIS.setdefault(p.name, sum(len(f.vertices) - 2 for f in tmp.polygons))
        ranges.append((p.name, off, len(tmp.vertices)))
        bm.from_mesh(tmp); bm.to_mesh(target.data); bm.free()
        bpy.data.meshes.remove(tmp)
        # vertex groups by name
        for g in p.vertex_groups:
            if target.vertex_groups.get(g.name) is None:
                target.vertex_groups.new(name=g.name)
        for i, v in enumerate(p.data.vertices):
            for gg in v.groups:
                target.vertex_groups[p.vertex_groups[gg.group].name].add([off + i], gg.weight, 'REPLACE')
        bpy.data.objects.remove(p)
    return target


def drop(ob, key, rules):
    """Delete vertices (and their faces) of joined parts hidden under clothes. rules: (part prefix, test, value) with test
    None (whole part), 'absx<' or 'z>' on the world position. Weights of the remaining vertices are kept. Returns tris removed."""
    def hit(name, p):
        for prefix, test, val in rules:
            if name.startswith(prefix) and (test is None or (test == 'absx<' and abs(p.x) < val) or (test == 'z>' and p.z > val)):
                return True
        return False
    owner = {}
    for name, first, count in RANGES[key]:
        for i in range(first, first + count):
            owner[i] = name
    mw = ob.matrix_world
    bm = bmesh.new(); bm.from_mesh(ob.data); bm.verts.ensure_lookup_table()
    dead = {v.index for v in bm.verts if hit(owner[v.index], mw @ v.co)}
    removed = {}
    for f in bm.faces:
        if any(v.index in dead for v in f.verts):
            n = owner[f.verts[0].index]
            removed[n] = removed.get(n, 0) + len(f.verts) - 2
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if v.index in dead], context='VERTS')
    bm.to_mesh(ob.data); bm.free()
    for n, t in removed.items():
        PART_TRIS[n] -= t
    return removed


def bvh_of(objs):
    verts, tris = [], []
    for o in objs:
        me = o.data; me.calc_loop_triangles(); mw = o.matrix_world; base = len(verts)
        verts += [mw @ v.co for v in me.vertices]
        tris += [tuple(base + i for i in lt.vertices) for lt in me.loop_triangles]
    return BVHTree.FromPolygons(verts, tris)


def inside(q, poly):
    c = False
    for i in range(len(poly)):
        a, b = poly[i], poly[i - 1]
        if (a.y > q.y) != (b.y > q.y) and q.x < (b.x - a.x) * (q.y - a.y) / (b.y - a.y) + a.x:
            c = not c
    return c


def decal(name, outline, axes, targets, offset, material, step=0.010, thickness=0.0, smooth=False, edge=0.0):
    """2D outline in a plane (origin, u, v, ray) projected onto target surfaces at `offset`.
    edge > 0 adds outline points at about that spacing (a coarse interior grid then still follows a curved target)."""
    origin, u, v, ray = (Vector(a) for a in axes)
    pts = [Vector(p) for p in outline]
    if edge:
        dense = []
        for i, a in enumerate(pts):
            b = pts[(i + 1) % len(pts)]
            k = max(1, round((b - a).length / edge))
            dense += [a.lerp(b, j / k) for j in range(k)]
        pts = dense
    edges = [(i, (i + 1) % len(pts)) for i in range(len(pts))]
    lo = Vector((min(p.x for p in pts), min(p.y for p in pts)))
    hi = Vector((max(p.x for p in pts), max(p.y for p in pts)))
    interior = []
    nx, ny = max(1, int((hi.x - lo.x) / step)), max(1, int((hi.y - lo.y) / step))
    for i in range(1, nx):
        for j in range(1, ny):
            q = Vector((lo.x + (hi.x - lo.x) * i / nx, lo.y + (hi.y - lo.y) * j / ny))
            if inside(q, pts) and min((q - p).length for p in pts) > step * 0.45:
                interior.append(q)
    res = delaunay_2d_cdt([p.to_tuple() for p in pts + interior], edges, [], 2, 1e-7)
    v2, faces = res[0], res[2]
    faces = [f for f in faces if inside(sum((Vector(v2[i]) for i in f), Vector((0.0, 0.0))) / len(f), pts)]
    bvh = bvh_of(targets)
    vs, misses, depths = [], [], []
    for q in v2:
        p0 = origin + u * q[0] + v * q[1]
        hit = bvh.ray_cast(p0 - ray * 0.7, ray, 1.6)
        if hit[0] is None:
            misses.append(len(vs)); vs.append(p0); continue
        depths.append((hit[0] - p0).dot(ray))
        n = hit[1] if hit[1].dot(ray) < 0 else -hit[1]
        vs.append(hit[0] + n * offset)
    if misses:      # rays that slipped past a thin target: snap to the nearest surface at the typical depth
        depths.sort()
        d = depths[len(depths) // 2] if depths else 0.0
        for i in misses:
            loc, nrm, _, _ = bvh.find_nearest(vs[i] + ray * d)
            if loc is not None:
                nrm = nrm if nrm.dot(ray) < 0 else -nrm
                vs[i] = loc + nrm * offset
    ob = from_data(name, vs, faces, material, smooth, fix_normals=False)
    me = ob.data
    if me.polygons and me.polygons[0].normal.dot(ray) > 0:
        me.flip_normals()
    if thickness:
        solidify(ob, thickness, -1.0)
    return ob


def FRONT():
    return ((0, -0.7, 0), (1, 0, 0), (0, 0, 1), (0, 1, 0))


def BACK():
    return ((0, 0.7, 0), (-1, 0, 0), (0, 0, 1), (0, -1, 0))


def SIDE(s):
    return ((s * 0.7, 0, 0), (0, -s, 0), (0, 0, 1), (-s, 0, 0))


def smoothstep(a, b, x):
    t = max(0.0, min(1.0, (x - a) / (b - a)))
    return t * t * (3 - 2 * t)


def chain(value, anchors):
    if value <= anchors[0][0]:
        return {anchors[0][1]: 1.0}
    for (lo, a), (hi, b) in zip(anchors, anchors[1:]):
        if value <= hi:
            t = smoothstep(lo, hi, value)
            out = {a: 1 - t}
            out[b] = out.get(b, 0) + t
            return out
    return {anchors[-1][1]: 1.0}


def mix(a, b, t):
    out = {k: v * (1 - t) for k, v in a.items()}
    for k, v in b.items():
        out[k] = out.get(k, 0) + v * t
    return out
