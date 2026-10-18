"""BLOOD-BAG-ASTRA-001 v05: a blood bag that really fills (procedural, Blender 5.2, background).

blender -b --factory-startup --python build_blood_bag_v05.py [-- --out <dir>]
Writes (refuses to overwrite) into BLOOD-BAG-ASTRA-001/v05/:
  BLOOD_BAG_ASTRA_001_v05.blend / .fbx, blood_bag_v05_validation.json, Previews/blood_bag_v05_fill_{000,050,100}.png

v04 was one opaque mesh with a baked red texture, so in game an "empty" bag could only be re-tinted. v05 separates a
translucent PVC pouch from an inner blood volume that rises.

Hierarchy (metres; Blender +Z = up when the bag hangs = Unity +Y; front/label = -Y; root origin = pouch centre):
  BLOOD_BAG_ASTRA_001_v05      root empty
    BAG_POUCH          translucent PVC pillow (the inflatable chamber)            MAT_BagPVC_v05 (Transparent)
    BAG_SEAL           flat heat-sealed border + hanger tab with a slot            MAT_BagSeal_v05 (Transparent, frosted)
    BAG_LABEL          front label: white sticker, red drop, print lines, volume ticks (opaque decals 0.6 mm off the PVC)
    BAG_PORTS          two outlet ports with twist-off caps (opaque)
    BAG_TUBE           clear line tube from the right port, looping up the side, spike + cap (Transparent)
    BAG_CLAMP          blue roller clamp on the tube (opaque)
    BLOOD_LIQUID       blood volume with a flat surface that rises from the ports to the hanger: basis = empty,
                       cumulative shape keys Fill_025/050/075/100, weight_k = clamp(4*fill - (k-1), 0, 1);
                       origin = the fill plane at the bottom of the chamber
    BLOOD_TUBE_LIQUID  red core inside the tube; show it when fill > 0 (it does not scale)
Unity: render BLOOD_LIQUID opaque (queue 2000) and the PVC parts transparent after it; hide BLOOD_LIQUID below fill 0.01;
the imported mesh bounds are the empty basis, so give the SkinnedMeshRenderer the full bounds from the validation JSON.
"""
import json
import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Matrix, Vector

HERE = Path(__file__).resolve().parent
ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
OUT = Path(ARGS[ARGS.index("--out") + 1]) if "--out" in ARGS else HERE.parent
STEM = "BLOOD_BAG_ASTRA_001_v05"
OUT_BLEND, OUT_FBX, OUT_JSON = OUT / f"{STEM}.blend", OUT / f"{STEM}.fbx", OUT / "blood_bag_v05_validation.json"
PREV = OUT / "Previews"

W, H, R = 0.120, 0.172, 0.024        # chamber outline (inflatable area), corner radius
T_FULL = 0.032                       # pouch thickness at its fullest
SEAL = 0.0075                        # heat-seal border width
SEAL_T = 0.0016
LIQ_INSET = 0.0022                   # blood volume inset from the PVC
sc = bpy.context.scene


def srgb_to_linear(c):
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def material(name, srgb, rough, alpha=1.0, coat=0.0):
    m = bpy.data.materials.new(name)
    rgb = tuple(srgb_to_linear(c) for c in srgb)
    m["unity_base_color_srgb"] = list(srgb)
    m["unity_smoothness"] = round(1 - rough, 2)
    m["unity_surface"] = "Transparent" if alpha < 1 else "Opaque"
    if alpha < 1:
        m["unity_alpha"] = alpha
    m.use_nodes = True
    b = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    b.inputs["Base Color"].default_value = (*rgb, 1)
    b.inputs["Roughness"].default_value = rough
    if coat and "Coat Weight" in b.inputs:
        b.inputs["Coat Weight"].default_value = coat
    if alpha < 1:
        b.inputs["Alpha"].default_value = alpha
        for attr, val in (("surface_render_method", "BLENDED"), ("blend_method", "BLEND")):
            try:
                setattr(m, attr, val)
            except (AttributeError, TypeError):
                pass
        m.use_backface_culling = False
    m.diffuse_color = (*rgb, alpha)
    return m


def rrect(hw, hh, r, n_corner=6):
    """Rounded rectangle outline (counter-clockwise seen from -Y, i.e. from the front), points in the XZ plane."""
    r = max(0.0015, min(r, hw - 1e-4, hh - 1e-4))
    pts = []
    for cx, cz, a0 in ((hw - r, -hh + r, -90), (hw - r, hh - r, 0), (-hw + r, hh - r, 90), (-hw + r, -hh + r, 180)):
        for k in range(n_corner + 1):
            a = math.radians(a0 + 90 * k / n_corner)
            pts.append(Vector((cx + r * math.cos(a), 0, cz + r * math.sin(a))))
    return pts


def thickness(d, x, z, T, hw):
    """Half thickness of the inflated pillow at inset d from the seal (0 at the seal), slightly domed in the middle."""
    s = min(1.0, d / 0.030)
    s = 1 - (1 - s) ** 2.2
    return 0.5 * T * s * (1 - 0.10 * (x / hw) ** 2)


def pillow(hw, hh, r, T, rings=(0.0, 0.0015, 0.004, 0.0075, 0.012, 0.018, 0.025, 0.033, 0.042, 0.050)):
    """Closed lens-shaped pillow over a rounded rectangle: concentric inset rings, front (-Y) and back (+Y) sheets."""
    bm = bmesh.new()
    front, back = [], []
    for k, d in enumerate(rings):
        if hw - d < 0.004 or hh - d < 0.004:
            break
        out = rrect(hw - d, hh - d, r - d)
        fr, bk = [], []
        for p in out:
            t = thickness(d, p.x, p.z, T, hw)
            if k == 0:
                v = bm.verts.new((p.x, 0.0, p.z))
                fr.append(v)
                bk.append(v)
            else:
                fr.append(bm.verts.new((p.x, -t, p.z)))
                bk.append(bm.verts.new((p.x, t, p.z)))
        front.append(fr)
        back.append(bk)
    n = len(front[0])
    for i in range(len(front) - 1):
        for j in range(n):
            j2 = (j + 1) % n
            bm.faces.new((front[i][j], front[i + 1][j], front[i + 1][j2], front[i][j2]))
            bm.faces.new((back[i][j], back[i][j2], back[i + 1][j2], back[i + 1][j]))
    # close the centre with a strip between the innermost ring's left and right halves
    bm.faces.new(list(reversed(front[-1])))
    bm.faces.new(back[-1])
    bmesh.ops.triangulate(bm, faces=[f for f in bm.faces if len(f.verts) > 4])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return bm


def ring_band(bm, outer, inner, t, mat):
    """Planar band between two closed outlines with the same point count (front, back and both rims)."""
    n = len(outer)
    of = [bm.verts.new((p.x, -t / 2, p.z)) for p in outer]
    ob = [bm.verts.new((p.x, t / 2, p.z)) for p in outer]
    inf = [bm.verts.new((p.x, -t / 2, p.z)) for p in inner]
    inb = [bm.verts.new((p.x, t / 2, p.z)) for p in inner]
    for j in range(n):
        j2 = (j + 1) % n
        for f in ((of[j], of[j2], inf[j2], inf[j]), (ob[j], inb[j], inb[j2], ob[j2]),
                  (of[j], ob[j], ob[j2], of[j2]), (inf[j], inf[j2], inb[j2], inb[j])):
            bm.faces.new(f).material_index = mat


def tube(bm, path, r, segs=10, mat=0, caps=True):
    n = len(path)
    rings = []
    a = None
    for i, p in enumerate(path):
        t = (path[min(i + 1, n - 1)] - path[max(i - 1, 0)]).normalized()
        a = t.orthogonal().normalized() if a is None else (a - t * a.dot(t)).normalized()
        b = t.cross(a)
        rings.append([bm.verts.new(p + (a * math.cos(2 * math.pi * j / segs) + b * math.sin(2 * math.pi * j / segs)) * r)
                      for j in range(segs)])
    for i in range(n - 1):
        for j in range(segs):
            j2 = (j + 1) % segs
            bm.faces.new((rings[i][j], rings[i][j2], rings[i + 1][j2], rings[i + 1][j])).material_index = mat
    if caps:
        bm.faces.new(list(reversed(rings[0]))).material_index = mat
        bm.faces.new(rings[-1]).material_index = mat


def catmull(points, per=8):
    pts = [Vector(p) for p in points]
    ext = [pts[0] * 2 - pts[1]] + pts + [pts[-1] * 2 - pts[-2]]
    out = []
    for i in range(1, len(ext) - 2):
        p0, p1, p2, p3 = ext[i - 1], ext[i], ext[i + 1], ext[i + 2]
        for s in range(per):
            t = s / per
            out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t + (-p0 + 3 * p1 - 3 * p2 + p3) * t ** 3))
    out.append(pts[-1])
    return out


def cylinder(bm, c, axis, r, h, segs=12, mat=0):
    axis = Vector(axis).normalized()
    tube(bm, [Vector(c), Vector(c) + axis * h], r, segs, mat)


def box(bm, c, size, mat=0, bevel=0.0):
    res = bmesh.ops.create_cube(bm, size=1.0)
    vs = res["verts"]
    for v in vs:
        v.co = Vector((v.co.x * size[0], v.co.y * size[1], v.co.z * size[2])) + Vector(c)
    faces = list({f for v in vs for f in v.link_faces})
    for f in faces:
        f.material_index = mat
    if bevel:
        bmesh.ops.bevel(bm, geom=list({e for v in vs for e in v.link_edges}), offset=bevel, segments=2, affect="EDGES")
    return vs


def finish(bm, name, mats, parent, origin=(0, 0, 0), smooth=True):
    bm.normal_update()
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    me.transform(Matrix.Translation(-Vector(origin)))
    for p in me.polygons:
        p.use_smooth = smooth
    for m in mats:
        me.materials.append(m)
    ob = bpy.data.objects.new(name, me)
    sc.collection.objects.link(ob)
    ob.parent = parent
    ob.location = origin
    return ob


def main():
    for p in (OUT_BLEND, OUT_FBX, OUT_JSON):
        assert not p.exists(), f"refusing to overwrite {p}"
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    M = {"pvc": material("MAT_BagPVC_v05", (0.88, 0.94, 1.00), 0.15, alpha=0.14),
         "seal": material("MAT_BagSeal_v05", (0.92, 0.95, 0.98), 0.35, alpha=0.62),
         "blood": material("MAT_Blood_v05", (0.62, 0.03, 0.07), 0.30, coat=0.3),
         "label": material("MAT_BagLabel_v05", (0.97, 0.96, 0.93), 0.70),
         "red": material("MAT_BagPrintRed_v05", (0.86, 0.12, 0.16), 0.60),
         "dark": material("MAT_BagPrintDark_v05", (0.20, 0.24, 0.30), 0.70),
         "blue": material("MAT_BagClamp_v05", (0.24, 0.46, 0.86), 0.45),
         "white": material("MAT_BagCap_v05", (0.95, 0.95, 0.96), 0.45)}
    root = bpy.data.objects.new(STEM, None)
    root.empty_display_type = "PLAIN_AXES"
    root.empty_display_size = 0.08
    sc.collection.objects.link(root)
    hw, hh = W / 2, H / 2

    # ---- pouch (translucent pillow)
    pouch = finish(pillow(hw, hh, R, T_FULL), "BAG_POUCH", [M["pvc"]], root)
    # ---- seal border + hanger tab with a slot
    bm = bmesh.new()
    inner = rrect(hw, hh, R)
    outer = rrect(hw + SEAL, hh + SEAL, R + SEAL)
    ring_band(bm, outer, inner, SEAL_T, 0)
    tab_w, tab_h = 0.046, 0.026
    top = hh + SEAL
    tab_outer = [Vector((p.x, 0, p.z + top + tab_h / 2 - 0.004)) for p in rrect(tab_w / 2, tab_h / 2 + 0.004, 0.008)]
    slot = [Vector((p.x, 0, p.z + top + tab_h * 0.55)) for p in rrect(0.012, 0.0042, 0.0041)]
    # tab: band between its outline and the slot (resample both to the same count)
    def resample_loop(loop, n):
        L = [0.0]
        for a, b in zip(loop, loop[1:] + loop[:1]):
            L.append(L[-1] + (b - a).length)
        out = []
        for k in range(n):
            s = L[-1] * k / n
            i = max(j for j in range(len(loop)) if L[j] <= s)
            a, b = loop[i], loop[(i + 1) % len(loop)]
            f = (s - L[i]) / max(1e-9, L[i + 1] - L[i])
            out.append(a.lerp(b, f))
        return out
    ring_band(bm, resample_loop(tab_outer, 48), resample_loop(slot, 48), SEAL_T, 0)
    seal = finish(bm, "BAG_SEAL", [M["seal"]], root, smooth=False)

    # ---- label on the front surface (curved onto the pillow, 0.6 mm off), drop icon, print lines, volume ticks
    from mathutils.bvhtree import BVHTree
    pb = BVHTree.FromPolygons([v.co for v in pouch.data.vertices], [p.vertices for p in pouch.data.polygons])

    def onto_front(x, z, lift):
        hit = pb.ray_cast(Vector((x, -0.2, z)), Vector((0, 1, 0)), 0.5)
        return hit[0] + Vector((0, -lift, 0))

    bm = bmesh.new()

    def decal(outline_xz, lift, mat):
        vs = [bm.verts.new(onto_front(x, z, lift)) for x, z in outline_xz]
        c = bm.verts.new(onto_front(sum(p[0] for p in outline_xz) / len(outline_xz), sum(p[1] for p in outline_xz) / len(outline_xz), lift))
        for j in range(len(vs)):
            f = bm.faces.new((vs[j], vs[(j + 1) % len(vs)], c))
            f.material_index = mat

    lc = (0.0, 0.016)
    lab = [(p.x * 1.0 + lc[0], p.z + lc[1]) for p in rrect(0.036, 0.031, 0.006, 4)]
    # subdivide the label a little so it follows the curvature: a grid instead of a fan
    gx, gz = 8, 7
    grid = []
    for i in range(gz + 1):
        row = []
        for j in range(gx + 1):
            x = lc[0] - 0.036 + 0.072 * j / gx
            z = lc[1] - 0.031 + 0.062 * i / gz
            row.append(bm.verts.new(onto_front(x, z, 0.0006)))
        grid.append(row)
    for i in range(gz):
        for j in range(gx):
            bm.faces.new((grid[i][j], grid[i][j + 1], grid[i + 1][j + 1], grid[i + 1][j])).material_index = 0
    # red header stripe
    decal([(lc[0] - 0.033, lc[1] + 0.019), (lc[0] + 0.033, lc[1] + 0.019), (lc[0] + 0.033, lc[1] + 0.028), (lc[0] - 0.033, lc[1] + 0.028)], 0.0010, 1)
    # blood drop (teardrop) on the left of the label
    drop = []
    for k in range(18):
        a = 2 * math.pi * k / 18
        rr = 0.0085 * (1 - 0.0 * math.sin(a))
        x = rr * math.cos(a) * (0.85 + 0.15 * math.sin(a)) * (1 - max(0, math.sin(a)) * 0.55)
        z = rr * math.sin(a) * (1.0 if math.sin(a) < 0 else 1.6)
        drop.append((lc[0] - 0.019 + x, lc[1] - 0.004 + z))
    decal(drop, 0.0010, 1)
    # print lines (text stand-ins) and a big blood-group block
    for k, (w, z) in enumerate(((0.030, 0.006), (0.024, -0.002), (0.028, -0.010), (0.018, -0.018))):
        x0 = lc[0] - 0.004
        decal([(x0, lc[1] + z - 0.0016), (x0 + w, lc[1] + z - 0.0016), (x0 + w, lc[1] + z + 0.0016), (x0, lc[1] + z + 0.0016)], 0.0010, 2)
    # volume ticks on the right side of the chamber (100..500 ml)
    for k in range(5):
        z = -hh + 0.020 + k * (H - 0.050) / 4
        w = 0.010 if k % 2 == 0 else 0.006
        x1 = hw - 0.010
        decal([(x1 - w, z - 0.0009), (x1, z - 0.0009), (x1, z + 0.0009), (x1 - w, z + 0.0009)], 0.0008, 2)
    label = finish(bm, "BAG_LABEL", [M["label"], M["red"], M["dark"]], root)

    # ---- ports (bottom): two outlets with twist-off caps; the right one feeds the tube
    bm = bmesh.new()
    pz = -hh - SEAL
    for x, capped in ((-0.020, True), (0.020, False)):
        cylinder(bm, (x, 0, pz + 0.004), (0, 0, -1), 0.0055, 0.020, 12, 0)
        cylinder(bm, (x, 0, pz - 0.016), (0, 0, -1), 0.0068, 0.004, 12, 1)
        if capped:
            cylinder(bm, (x, 0, pz - 0.020), (0, 0, -1), 0.0062, 0.012, 12, 1)
            box(bm, (x, 0, pz - 0.036), (0.016, 0.004, 0.010), 1, 0.0012)
    ports = finish(bm, "BAG_PORTS", [M["seal"], M["white"]], root)
    ports.data.materials[0] = M["white"]

    # ---- tube: from the right port down, loop to the right and up the side; spike connector + cap at the end
    path = catmull([(0.020, 0, pz - 0.018), (0.022, 0, pz - 0.040), (0.045, -0.004, pz - 0.058), (0.078, -0.006, pz - 0.040),
                    (0.086, -0.006, pz + 0.010), (0.086, -0.006, -0.010), (0.083, -0.006, 0.020)], 8)
    bm = bmesh.new()
    tube(bm, path, 0.0032, 10, 0)
    tube_ob = finish(bm, "BAG_TUBE", [M["pvc"]], root)
    bm = bmesh.new()
    tube(bm, path[1:-1], 0.0021, 8, 0)
    tube_liq = finish(bm, "BLOOD_TUBE_LIQUID", [M["blood"]], root)
    # spike + cap at the tube end, clamp on the vertical run
    bm = bmesh.new()
    end, d = path[-1], (path[-1] - path[-2]).normalized()
    cylinder(bm, end - d * 0.002, d, 0.0048, 0.010, 12, 1)
    cylinder(bm, end + d * 0.008, d, 0.0058, 0.014, 12, 0)
    cl = Vector((0.086, -0.006, pz + 0.000))
    box(bm, cl, (0.013, 0.012, 0.030), 0, 0.002)
    cylinder(bm, cl + Vector((-0.0068, 0.0, 0.004)), (1, 0, 0), 0.0058, 0.0016, 14, 1)     # roller wheel edge
    clamp = finish(bm, "BAG_CLAMP", [M["blue"], M["white"]], root)

    # ---- blood volume: horizontal slices of the pouch interior up to the fill level, flat liquid surface on top.
    # Basis = empty (1.5 mm film). Shape keys are CUMULATIVE steps, so weights add up exactly as in Unity:
    #   Fill_025, Fill_050, Fill_075, Fill_100;  weight_k = clamp(4 * fill - (k - 1), 0, 1)   (k = 1..4)
    a_i, b_i, r_i = hw - LIQ_INSET, hh - LIQ_INSET, R - LIQ_INSET
    T_i = T_FULL - 2 * 0.0009
    z_bot, z_top = -b_i, b_i
    NR, NM = 16, 28

    def d_inside(x, z):
        qx, qz = abs(x) - (a_i - r_i), abs(z) - (b_i - r_i)
        sd = math.hypot(max(qx, 0), max(qz, 0)) + min(max(qx, qz), 0) - r_i
        return max(0.0, -sd)

    def half_width(z):
        dz = abs(z) - (b_i - r_i)
        return a_i if dz <= 0 else (a_i - r_i) + math.sqrt(max(r_i * r_i - dz * dz, 0.0))

    def shape(level):
        pts = []
        for k in range(NR + 1):
            u = k / NR
            z = z_bot + (level - z_bot) * u
            xw = half_width(z) * 0.999
            for j in range(NM):
                ph = 2 * math.pi * j / NM
                x = xw * math.cos(ph)
                t = thickness(d_inside(x, z), x, z, T_i, a_i)
                y = -t if math.sin(ph) < 0 else t
                if abs(math.sin(ph)) < 1e-6:
                    y = 0.0
                pts.append((x, y, z))
        pts.append((0.0, 0.0, level))           # top cap centre
        return pts

    levels = {f: z_bot + max(0.0015, f * (z_top - z_bot)) for f in (0.0, 0.25, 0.5, 0.75, 1.0)}
    S = {f: [Vector(p) for p in shape(lv)] for f, lv in levels.items()}
    bm = bmesh.new()
    vs = [bm.verts.new(p) for p in S[0.0]]
    for k in range(NR):
        for j in range(NM):
            j2 = (j + 1) % NM
            bm.faces.new((vs[k * NM + j], vs[k * NM + j2], vs[(k + 1) * NM + j2], vs[(k + 1) * NM + j]))
    top_c = vs[-1]
    for j in range(NM):
        j2 = (j + 1) % NM
        bm.faces.new((vs[NR * NM + j], vs[NR * NM + j2], top_c))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    liquid = finish(bm, "BLOOD_LIQUID", [M["blood"]], root, origin=(0, 0, z_bot))
    liquid.shape_key_add(name="Basis", from_mix=False)
    steps = [0.0, 0.25, 0.5, 0.75, 1.0]
    for k in range(1, 5):
        key = liquid.shape_key_add(name=f"Fill_{int(steps[k] * 100):03d}", from_mix=False)
        for i, d in enumerate(key.data):
            delta = S[steps[k]][i] - S[steps[k - 1]][i]
            d.co = liquid.data.vertices[i].co + delta
        key.slider_min, key.slider_max = 0.0, 1.0

    def set_fill(f):
        for k in range(1, 5):
            liquid.data.shape_keys.key_blocks[k].value = min(1.0, max(0.0, 4 * f - (k - 1)))
        liquid.hide_render = f < 0.01
        tube_liq.hide_render = f < 0.01

    # validation: every sampled fill shape stays inside the pouch
    from mathutils.bvhtree import BVHTree as BT
    pouch_bvh = BT.FromPolygons([v.co for v in pouch.data.vertices], [p.vertices for p in pouch.data.polygons])
    outside = {}
    for f, pts in S.items():
        n = 0
        for p in pts:
            loc, nrm, _, dist = pouch_bvh.find_nearest(p)
            if (p - loc).dot(nrm) > 1e-5:
                n += 1
        outside[str(f)] = n
    full_max = [max(p[i] for p in S[1.0]) for i in range(3)]
    full_min = [min(p[i] for p in S[1.0]) for i in range(3)]

    def tris(ob):
        return sum(len(p.vertices) - 2 for p in ob.data.polygons)

    objs = [pouch, seal, label, ports, tube_ob, clamp, liquid, tube_liq]
    allv = [(o.matrix_world @ v.co) for o in objs for v in o.data.vertices]
    mn = Vector((min(v.x for v in allv), min(v.y for v in allv), min(v.z for v in allv)))
    mx = Vector((max(v.x for v in allv), max(v.y for v in allv), max(v.z for v in allv)))
    report = {"axis": "Blender +Z up when hanging (Unity +Y); label/front = -Y; root origin = pouch centre",
              "bounds_m": {"min": [round(c, 4) for c in mn], "max": [round(c, 4) for c in mx], "size": [round(c, 4) for c in mx - mn]},
              "chamber_m": {"width": W, "height": H, "full_thickness": T_FULL},
              "fill": {"object": "BLOOD_LIQUID", "kind": "blend shapes (SkinnedMeshRenderer in Unity), basis = empty 1.5 mm film",
                       "shape_keys": ["Fill_025", "Fill_050", "Fill_075", "Fill_100"],
                       "rule": "cumulative steps: weight_k = clamp(4*fill - (k-1), 0, 1) for k = 1..4 (Unity weight x100); "
                               "the liquid surface stays flat and follows the pouch walls; hide BLOOD_LIQUID and "
                               "BLOOD_TUBE_LIQUID below fill 0.01",
                       "origin": "fill plane at the bottom of the chamber, z = %.4f (pouch-centre frame)" % z_bot,
                       "full_bounds_local": {"min": [round(c, 4) for c in full_min], "max": [round(c, 4) for c in full_max]},
                       "unity_bounds_note": "the imported mesh bounds are the EMPTY basis: set SkinnedMeshRenderer.localBounds "
                                            "to full_bounds_local (minus origin) or enable updateWhenOffscreen",
                       "liquid_verts_outside_pouch_per_fill": outside},
              "objects": {o.name: {"tris": tris(o), "materials": [m.name for m in o.data.materials]} for o in objs},
              "total_tris": sum(tris(o) for o in objs),
              "materials_unity": {m.name: {k: (list(m[k]) if hasattr(m[k], "__len__") and not isinstance(m[k], str) else m[k])
                                          for k in m.keys() if k.startswith("unity_")} for m in M.values()},
              "fbx_default_state": "EMPTY basis, shape keys at 0 (set them from fill)", "organ_bag_note": "ORGANBAG-ASTRA-001 G34 v02 is an opaque "
              "insulated pouch with no fill/tint state - not changed"}
    print("[BAG_v05]", json.dumps(report))

    # previews: hanging bag 3/4 front at fill 0 / 50 / 100
    PREV.mkdir(parents=True, exist_ok=True)
    for eng in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"):
        try:
            sc.render.engine = eng
            break
        except TypeError:
            pass
    sc.view_settings.view_transform = "Standard"
    w = bpy.data.worlds.new("W")
    sc.world = w
    w.use_nodes = True
    bgn = next(n for n in w.node_tree.nodes if n.type == "BACKGROUND")
    bgn.inputs["Color"].default_value = (0.30, 0.33, 0.37, 1)
    bgn.inputs["Strength"].default_value = 0.8
    lights = []
    for name, rot, e in (("Key", (math.radians(40), 0, math.radians(-30)), 2.6), ("Rim", (math.radians(70), 0, math.radians(150)), 1.6)):
        ld = bpy.data.lights.new(name, "SUN")
        ld.energy = e
        lo = bpy.data.objects.new(name, ld)
        lo.rotation_euler = rot
        sc.collection.objects.link(lo)
        lights.append(lo)
    bd = bpy.data.meshes.new("Backdrop")
    bd.from_pydata([(-1, 0.25, -1), (1, 0.25, -1), (1, 0.25, 1), (-1, 0.25, 1)], [], [(0, 1, 2, 3)])
    bd.materials.append(material("Backdrop", (0.26, 0.28, 0.32), 0.9))
    bdo = bpy.data.objects.new("Backdrop", bd)
    sc.collection.objects.link(bdo)
    cam = bpy.data.objects.new("Cam", bpy.data.cameras.new("Cam"))
    sc.collection.objects.link(cam)
    sc.camera = cam
    tgt = Vector((0.010, 0, -0.012))
    loc = Vector((-0.20, -0.46, 0.06))
    fwd = (tgt - loc).normalized()
    x = fwd.cross(Vector((0, 0, 1))).normalized()
    cam.matrix_world = Matrix.Translation(loc) @ Matrix((x, x.cross(fwd), -fwd)).transposed().to_4x4()
    cam.data.lens = 60
    sc.render.resolution_x, sc.render.resolution_y = 700, 1000
    for f in (0.0, 0.5, 1.0):
        set_fill(f)
        sc.render.filepath = str(PREV / f"blood_bag_v05_fill_{int(f * 100):03d}.png")
        bpy.ops.render.render(write_still=True)
    set_fill(0.0)
    liquid.hide_render = tube_liq.hide_render = False
    for o in lights + [bdo, cam]:
        o.hide_viewport = True
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=str(OUT_BLEND))
    bpy.ops.object.select_all(action="DESELECT")
    for o in [root] + objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = root
    bpy.ops.export_scene.fbx(filepath=str(OUT_FBX), use_selection=True, object_types={"MESH", "EMPTY"}, axis_forward="-Z", axis_up="Y",
                             apply_unit_scale=True, apply_scale_options="FBX_SCALE_UNITS", use_mesh_modifiers=False, bake_anim=False,
                             add_leaf_bones=False, use_custom_props=True)
    OUT_JSON.write_text(json.dumps(report, indent=1), encoding="utf-8")


main()
