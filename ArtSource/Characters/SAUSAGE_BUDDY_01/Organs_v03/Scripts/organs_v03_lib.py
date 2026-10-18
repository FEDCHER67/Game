"""Shared helpers for the v03 organ set (Blender 5.2, background). Geometry is in metres.

Organ-local frame used for every organ mesh in this set (the SOCKET frame):
  +X = patient's left, +Y = toward the head (organ long axis), +Z = anterior (organ front, out of the body).
A socket in the patient REST frame (Z up, faces -Y, patient left +X) is R_tilt @ Rx(+90 deg): local Y -> rest +Z,
local Z -> rest -Y.
"""
import math

import bmesh
import bpy
import numpy as np
from mathutils import Matrix, Quaternion, Vector
from mathutils.bvhtree import BVHTree

RX90 = Matrix.Rotation(math.radians(90), 4, "X")


# ------------------------------------------------------------------------------------------------ materials
def srgb_to_linear(c):
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def material(name, srgb, rough, coat=0.0, alpha=1.0, emission=0.0, spec=0.5, transmission=0.0):
    """Principled material; colours given in sRGB (as typed into a Unity URP Lit material)."""
    m = bpy.data.materials.get(name)
    if m:
        return m
    rgb = tuple(srgb_to_linear(c) for c in srgb)
    m = bpy.data.materials.new(name)
    m["unity_base_color_srgb"] = [round(c, 3) for c in srgb]
    m["unity_smoothness"] = round(1.0 - rough, 2)
    if alpha < 1.0:
        m["unity_surface"] = "Transparent"
        m["unity_alpha"] = alpha
    m.use_nodes = True
    b = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    b.inputs["Base Color"].default_value = (*rgb, 1)
    b.inputs["Roughness"].default_value = rough
    if "Specular IOR Level" in b.inputs:
        b.inputs["Specular IOR Level"].default_value = spec
    if coat and "Coat Weight" in b.inputs:
        b.inputs["Coat Weight"].default_value = coat
        b.inputs["Coat Roughness"].default_value = 0.15
    if emission and "Emission Strength" in b.inputs:
        b.inputs["Emission Color"].default_value = (*rgb, 1)
        b.inputs["Emission Strength"].default_value = emission
    if transmission and "Transmission Weight" in b.inputs:
        b.inputs["Transmission Weight"].default_value = transmission
    if alpha < 1.0:
        b.inputs["Alpha"].default_value = alpha
        for attr, val in (("blend_method", "BLEND"), ("surface_render_method", "BLENDED")):
            try:
                setattr(m, attr, val)
            except (AttributeError, TypeError):
                pass
        try:
            m.use_backface_culling = False
            m.show_transparent_back = False
        except AttributeError:
            pass
    m.diffuse_color = (*rgb, alpha)
    return m


# ------------------------------------------------------------------------------------------------ mesh utils
def new_object(name, bm, mats, coll, matrix=None, smooth=True):
    me = bpy.data.meshes.new(name)
    bm.normal_update()
    bm.to_mesh(me)
    bm.free()
    for p in me.polygons:
        p.use_smooth = smooth
    for m in mats:
        me.materials.append(m)
    ob = bpy.data.objects.new(name, me)
    coll.objects.link(ob)
    if matrix is not None:
        ob.matrix_world = matrix
    return ob


def tris(ob):
    return sum(len(p.vertices) - 2 for p in ob.data.polygons)


def local_bounds(ob):
    co = [v.co for v in ob.data.vertices]
    mn = Vector((min(c.x for c in co), min(c.y for c in co), min(c.z for c in co)))
    mx = Vector((max(c.x for c in co), max(c.y for c in co), max(c.z for c in co)))
    return mn, mx


def catmull(points, per=8):
    pts = [Vector(p) for p in points]
    out = []
    ext = [pts[0] * 2 - pts[1]] + pts + [pts[-1] * 2 - pts[-2]]
    for i in range(1, len(ext) - 2):
        p0, p1, p2, p3 = ext[i - 1], ext[i], ext[i + 1], ext[i + 2]
        for s in range(per):
            t = s / per
            out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t + (-p0 + 3 * p1 - 3 * p2 + p3) * t ** 3))
    out.append(pts[-1])
    return out


def resample(path, step):
    """Evenly spaced points along a polyline."""
    pts = [Vector(p) for p in path]
    d = [0.0]
    for a, b in zip(pts, pts[1:]):
        d.append(d[-1] + (b - a).length)
    n = max(2, int(round(d[-1] / step)) + 1)
    out = []
    j = 0
    for i in range(n):
        s = d[-1] * i / (n - 1)
        while j < len(d) - 2 and d[j + 1] < s:
            j += 1
        f = (s - d[j]) / max(1e-9, d[j + 1] - d[j])
        out.append(pts[j].lerp(pts[j + 1], f))
    return out


def frames_along(path):
    """Rotation-minimising frames (tangent, normal, binormal) along a path."""
    n = len(path)
    ts = [(path[min(i + 1, n - 1)] - path[max(i - 1, 0)]).normalized() for i in range(n)]
    a = ts[0].orthogonal().normalized()
    out = []
    for i, t in enumerate(ts):
        if i:
            a = (a - t * a.dot(t)).normalized()
        b = t.cross(a)
        out.append((t, a, b))
    return out


def tube(bm, path, radius, segs=12, cap0="round", cap1="round", radius_fn=None, flat=1.0, mat=0, cap_mat=None,
         lumen=0.0):
    """Swept tube. radius may vary via radius_fn(i, n) -> factor. flat < 1 squashes the cross-section along the binormal.
    cap: 'round' (tapered closed end), 'flat' (planar disc), 'cut' (planar ring + recessed dark lumen disc), None (open).
    Returns (first ring, last ring)."""
    n = len(path)
    fr = frames_along(path)
    rings = []
    for i, (p, (t, a, b)) in enumerate(zip(path, fr)):
        r = radius * (radius_fn(i, n) if radius_fn else 1.0)
        if cap0 == "round" and i < 2:
            r *= (0.55, 0.88)[i]
        if cap1 == "round" and i > n - 3:
            r *= (0.55, 0.88)[n - 1 - i]
        rings.append([bm.verts.new(p + (a * math.cos(2 * math.pi * j / segs) + b * flat * math.sin(2 * math.pi * j / segs)) * r)
                      for j in range(segs)])
    for i in range(n - 1):
        for j in range(segs):
            j2 = (j + 1) % segs
            f = bm.faces.new((rings[i][j], rings[i][j2], rings[i + 1][j2], rings[i + 1][j]))
            f.material_index = mat

    def cap(ring, end, kind, t):
        if kind is None:
            return
        if kind in ("round", "flat"):
            c = bm.verts.new(sum((v.co for v in ring), Vector()) / len(ring) + t * (radius * (0.25 if kind == "round" else 0.0)))
            for j in range(segs):
                j2 = (j + 1) % segs
                f = bm.faces.new((ring[j], ring[j2], c) if end else (ring[j2], ring[j], c))
                f.material_index = mat
        elif kind == "cut":
            # wall thickness ring then a recessed lumen disc (dark)
            centre = sum((v.co for v in ring), Vector()) / len(ring)
            inner = [bm.verts.new(centre + (v.co - centre) * (1 - lumen)) for v in ring]
            deep = [bm.verts.new(centre + (v.co - centre) * (1 - lumen) - t * radius * 0.6) for v in ring]
            for j in range(segs):
                j2 = (j + 1) % segs
                f = bm.faces.new((ring[j], ring[j2], inner[j2], inner[j]) if end else (ring[j2], ring[j], inner[j], inner[j2]))
                f.material_index = mat
                f = bm.faces.new((inner[j], inner[j2], deep[j2], deep[j]) if end else (inner[j2], inner[j], deep[j], deep[j2]))
                f.material_index = cap_mat if cap_mat is not None else mat
            c = bm.verts.new(centre - t * radius * 0.6)
            for j in range(segs):
                j2 = (j + 1) % segs
                f = bm.faces.new((deep[j], deep[j2], c) if end else (deep[j2], deep[j], c))
                f.material_index = cap_mat if cap_mat is not None else mat

    t0 = (path[0] - path[1]).normalized()
    t1 = (path[-1] - path[-2]).normalized()
    cap(rings[0], False, cap0, t0)
    cap(rings[-1], True, cap1, t1)
    return rings[0], rings[-1]


def merge_bm(dst, src_mesh_bm):
    me = bpy.data.meshes.new("_tmp")
    src_mesh_bm.to_mesh(me)
    src_mesh_bm.free()
    dst.from_mesh(me)
    bpy.data.meshes.remove(me)


# ------------------------------------------------------------------------------------------------ SDF surfaces
def smin(a, b, k):
    h = np.clip(0.5 + 0.5 * (b - a) / k, 0.0, 1.0)
    return b * (1 - h) + a * h - k * h * (1 - h)


def smax(a, b, k):
    return -smin(-a, -b, k)


def sd_ellipsoid(p, c, r, rot=None):
    q = p - np.asarray(c)
    if rot is not None:
        q = q @ np.asarray(rot)          # rows of rot = local axes
    r = np.asarray(r)
    k0 = np.linalg.norm(q / r, axis=-1)
    k1 = np.linalg.norm(q / (r * r), axis=-1)
    return k0 * (k0 - 1.0) / np.maximum(k1, 1e-9)


def sd_capsule(p, a, b, r):
    a, b = np.asarray(a), np.asarray(b)
    pa, ba = p - a, b - a
    h = np.clip((pa @ ba) / (ba @ ba), 0, 1)
    return np.linalg.norm(pa - h[:, None] * ba, axis=-1) - r


def sdf_surface(sdf, centre, subdiv=6, rmax=0.12, iters=48):
    """Star-shaped surface: an icosphere around `centre` whose vertices are moved along their rays to sdf == 0
    (bisection). Returns a bmesh."""
    bm = bmesh.new()
    bmesh.ops.create_icosphere(bm, subdivisions=subdiv, radius=1.0)
    dirs = np.array([tuple(v.co.normalized()) for v in bm.verts])
    c = np.asarray(centre)
    lo = np.zeros(len(dirs))
    hi = np.full(len(dirs), rmax)
    assert np.all(sdf(c + dirs * rmax) > 0), "surface not bounded by rmax"
    for _ in range(iters):
        mid = 0.5 * (lo + hi)
        inside = sdf(c + dirs * mid[:, None]) < 0
        lo = np.where(inside, mid, lo)
        hi = np.where(inside, hi, mid)
    rad = 0.5 * (lo + hi)
    for v, d, r in zip(bm.verts, dirs, rad):
        v.co = Vector(tuple(c + d * r))
    return bm


def relax(bm, iters=2, factor=0.35):
    for _ in range(iters):
        bmesh.ops.smooth_vert(bm, verts=bm.verts[:], factor=factor, use_axis_x=True, use_axis_y=True, use_axis_z=True)


def decimate_bm(bm, target_tris):
    """Collapse-decimate a bmesh to about target_tris triangles (shape-preserving)."""
    me = bpy.data.meshes.new("_dec")
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new("_dec", me)
    bpy.context.scene.collection.objects.link(ob)
    n = sum(len(p.vertices) - 2 for p in me.polygons)
    decimate_object(ob, min(1.0, target_tris / n))
    out = bmesh.new()
    out.from_mesh(ob.data)
    bpy.data.objects.remove(ob, do_unlink=True)
    bpy.data.meshes.remove(me)
    return out


def decimate_object(ob, ratio):
    mod = ob.modifiers.new("Decimate", "DECIMATE")
    mod.ratio = ratio
    mod.use_collapse_triangulate = True
    with bpy.context.temp_override(object=ob, active_object=ob, selected_objects=[ob]):
        bpy.ops.object.modifier_apply(modifier=mod.name)


# ------------------------------------------------------------------------------------------------ frames / conversion
def socket_matrix(pos, y_axis=(0, 0, 1), z_axis=(0, -1, 0)):
    """Socket frame in the patient REST frame from its local +Y (head / long axis) and +Z (anterior) directions."""
    y = Vector(y_axis).normalized()
    z = Vector(z_axis)
    z = (z - y * z.dot(y)).normalized()
    x = y.cross(z)
    return Matrix.Translation(Vector(pos)) @ Matrix((x, y, z)).transposed().to_4x4()


def unity_local_pos(v):
    """Blender marker/socket-local -> Unity marker/socket-local (X negated after FBX import)."""
    return [round(-v[0], 5), round(v[1], 5), round(v[2], 5)]


def unity_local_quat(q):
    """Blender rotation (wxyz) in a socket-local frame -> Unity (xyzw) in the same, X-mirrored frame."""
    q = Quaternion(q)
    return [round(q.x, 5), round(-q.y, 5), round(-q.z, 5), round(q.w, 5)]


def rnd(v, n=4):
    return [round(float(c), n) for c in v]


def bvh_of(objs, depsgraph=None):
    verts, polys = [], []
    for ob in objs:
        if depsgraph is not None:
            eo = ob.evaluated_get(depsgraph)
            me = eo.to_mesh()
        else:
            me = ob.data
        off = len(verts)
        verts += [ob.matrix_world @ v.co for v in me.vertices]
        polys += [tuple(i + off for i in p.vertices) for p in me.polygons]
        if depsgraph is not None:
            eo.to_mesh_clear()
    return BVHTree.FromPolygons(verts, polys), verts, polys


def inside_count(bvh, points, ray=Vector((0.0123, 0.0071, 1.0)).normalized()):
    """Number of points inside a closed mesh (odd ray crossings)."""
    n = 0
    for p in points:
        hits = 0
        o = Vector(p)
        for _ in range(64):
            h = bvh.ray_cast(o + ray * 1e-5, ray)
            if h[0] is None:
                break
            hits += 1
            o = h[0]
        n += hits % 2
    return n
