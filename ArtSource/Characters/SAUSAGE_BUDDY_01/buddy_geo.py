"""Geometry helpers for the Sausage Buddy builder (Blender 5.2). Z up, -Y forward, metres."""
import math
import bpy, bmesh
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree
from mathutils.geometry import delaunay_2d_cdt

COLLECTION = None
MATS = {}


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


def loft(name, sections, material, seg=16, cap_start=True, cap_end=True, subdiv=0, smooth=True, mat_rows=None, extra=()):
    """sections: list of (center Vector, axis_u Vector, axis_v Vector, ru, rv) -> rings bridged in order."""
    vs, fs, rings, idx = [], [], [], []
    for c, u, v, ru, rv in sections:
        ring = []
        for j in range(seg):
            a = 2 * math.pi * j / seg
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
    for poly in target.data.polygons:
        pass
    return target


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


def decal(name, outline, axes, targets, offset, material, step=0.010, thickness=0.0, smooth=False):
    """2D outline in a plane (origin, u, v, ray) projected onto target surfaces at `offset`."""
    origin, u, v, ray = (Vector(a) for a in axes)
    pts = [Vector(p) for p in outline]
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
