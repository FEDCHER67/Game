"""Automated checks for Workshop_W86 v01 (run on the saved .blend, headless):
  coplanar overlapping triangles (z-fighting), floating / wall-detached props, unsupported lamps,
  clear van path / door openings / pit / hand-in zone / partition doorways, tri budgets.
  blender -b --factory-startup -noaudio --python check_workshop_w86_v01.py
Prints a JSON summary and writes Workshop_W86_checks_v01.json.
"""
import json
import math
import os
import sys
from collections import defaultdict

import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_workshop_w86_v01 as B  # noqa: E402

OUT = B.OUT


def world_tris(o):
    M = o.matrix_world
    me = o.data
    me.calc_loop_triangles()
    vs = [M @ v.co for v in me.vertices]
    return [(tuple(vs[i] for i in t.vertices), t.material_index) for t in me.loop_triangles], vs


def clip(poly, a, b):
    out = []
    n = len(poly)
    for i in range(n):
        p, q = poly[i], poly[(i + 1) % n]
        cp = (b[0] - a[0]) * (p[1] - a[1]) - (b[1] - a[1]) * (p[0] - a[0])
        cq = (b[0] - a[0]) * (q[1] - a[1]) - (b[1] - a[1]) * (q[0] - a[0])
        if cp >= 0:
            out.append(p)
        if (cp >= 0) != (cq >= 0):
            t = cp / (cp - cq)
            out.append((p[0] + t * (q[0] - p[0]), p[1] + t * (q[1] - p[1])))
    return out


def area2(poly):
    return 0.5 * sum(poly[i][0] * poly[(i + 1) % len(poly)][1] - poly[(i + 1) % len(poly)][0] * poly[i][1] for i in range(len(poly)))


def tri_overlap(t1, t2):
    if area2(t1) < 0:
        t1 = t1[::-1]
    if area2(t2) < 0:
        t2 = t2[::-1]
    poly = list(t2)
    for i in range(3):
        if not poly:
            return 0.0
        poly = clip(poly, t1[i], t1[(i + 1) % 3])
    return abs(area2(poly)) if len(poly) >= 3 else 0.0


def coplanar_check(objs):
    buckets = defaultdict(list)
    for o in objs:
        tris, _ = world_tris(o)
        for k, (t, mi) in enumerate(tris):
            n = (t[1] - t[0]).cross(t[2] - t[0])
            if n.length < 1e-8:
                continue
            ar = n.length * 0.5
            if ar < 2e-5:
                continue
            n.normalize()
            d = n.dot(t[0])
            key = (round(n.x, 2), round(n.y, 2), round(n.z, 2), round(d / 0.0015))
            buckets[key].append((o.name, k, t, n))
    same, opp = [], 0
    for key, items in buckets.items():
        cands = list(items)
        for dd in (-1, 1):
            k2 = (key[0], key[1], key[2], key[3] + dd)
            if k2 in buckets and k2 > key:
                cands += buckets[k2]
        if len(cands) < 2:
            continue
        n = cands[0][3]
        ax = Vector((1, 0, 0)) if abs(n.x) < 0.9 else Vector((0, 1, 0))
        u = n.cross(ax).normalized()
        v = n.cross(u)
        P = [(c, [(p.dot(u), p.dot(v)) for p in c[2]]) for c in cands]
        for i in range(len(P)):
            ci, ti = P[i]
            bxi = (min(a for a, b in ti), max(a for a, b in ti), min(b for a, b in ti), max(b for a, b in ti))
            for j in range(i + 1, len(P)):
                cj, tj = P[j]
                if ci[0] == cj[0] and ci[1] == cj[1]:
                    continue
                bxj = (min(a for a, b in tj), max(a for a, b in tj), min(b for a, b in tj), max(b for a, b in tj))
                if bxi[1] <= bxj[0] + 1e-4 or bxj[1] <= bxi[0] + 1e-4 or bxi[3] <= bxj[2] + 1e-4 or bxj[3] <= bxi[2] + 1e-4:
                    continue
                if ci[0] == cj[0] and abs(ci[1] - cj[1]) <= 1:
                    continue  # two triangles of the same quad
                ov = tri_overlap(ti, tj)
                if ov > 2e-4:
                    same.append(dict(a=ci[0], b=cj[0], area_m2=round(ov, 5), at=[round(x, 3) for x in ci[2][0]],
                                     ta=[[round(x, 3) for x in p] for p in ci[2]], tb=[[round(x, 3) for x in p] for p in cj[2]]))
    return same


def box_hits(vs, lo, hi):
    return [tuple(round(c, 3) for c in p) for p in vs if all(lo[i] < p[i] < hi[i] for i in range(3))]


def bbox(o):
    pts = []
    obs = [o] + [c for c in o.children_recursive if c.type == 'MESH' and not c.name.startswith('UCX_') and not c.name.endswith('_LOD1')]
    for ob in obs:
        if ob.type == 'MESH':
            pts += [ob.matrix_world @ v.co for v in ob.data.vertices]
    if not pts:
        return None
    return (Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts))),
            Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts))))


def aabb_overlap(a, lo, hi):
    return all(a[0][i] < hi[i] and a[1][i] > lo[i] for i in range(3))


def main():
    bpy.ops.wm.open_mainfile(filepath=os.path.join(OUT, 'Workshop_W86_v01.blend'))
    res = {}
    bl0 = [bpy.data.objects['WS_Building_Shell_LOD0'], bpy.data.objects['WS_Building_Interior_LOD0']]
    prop_roots = [o for o in bpy.data.collections['WS_Props'].objects if o.parent is None]
    prop_meshes = []
    for r in prop_roots:
        if r.type == 'MESH':
            prop_meshes.append(r)
        prop_meshes += [c for c in r.children if c.type == 'MESH' and c.name.endswith(('_LOD0', '_Mesh'))]
    apron = bpy.data.objects['WS_Apron']
    # ---------- z-fighting
    zf = coplanar_check(bl0 + prop_meshes + [apron])
    res['coplanar_same_facing_overlaps'] = zf
    res['coplanar_same_facing_overlap_count'] = len(zf)
    # ---------- building BVH (for supports)
    allv, alltris = [], []
    for o in bl0 + [apron]:
        tris, _ = world_tris(o)
        for t, _ in tris:
            base = len(allv)
            allv += list(t)
            alltris.append((base, base + 1, base + 2))
    bvh = BVHTree.FromPolygons(allv, alltris)
    bverts = []
    for o in bl0:
        bverts += [o.matrix_world @ v.co for v in o.data.vertices]
    # ---------- props: floating / wall contact / clear zones
    layout = {p[0]: p for p in B.PROP_LAYOUT}
    support_issues, wall_issues = [], []
    for r in prop_roots:
        pid = r.name
        lay = layout[pid]
        bb = bbox(r)
        if lay[4] == 'facade' and lay[1] != 'bollard':
            pass
        if lay[4] == 'facade' and lay[1] != 'bollard' or lay[1] in ('toolboard', 'calendar'):
            Mw = r.matrix_world
            dirv = (Mw.to_3x3() @ Vector((0, 1, 0))).normalized()
            best = None
            for lx in (-0.037, 0.013, 0.041):  # several rays across the mounting plate (corrugation peaks/valleys)
                back = Mw @ Vector((lx, -0.01, 0.2 if lay[1] != 'wall_light' else 0.0))
                h = bvh.ray_cast(back, dirv, 0.3)
                if h[0] is not None and (best is None or h[3] < best[3]):
                    best = h
            hit = best if best is not None else (None, None, None, None)
            if hit[0] is None or hit[3] > 0.05:
                wall_issues.append(dict(prop=pid, gap=None if hit[0] is None else round(hit[3], 3),
                                        start=[round(c, 3) for c in back], dir=[round(c, 3) for c in dirv]))
            continue
        zmin = bb[0].z
        expect = lay[2][2]
        if abs(zmin - expect) > 0.012:
            support_issues.append(dict(prop=pid, zmin=round(zmin, 4), expected=expect))
        # something solid right below the footprint corners (floor / apron / desk)
        if expect == 0.0:
            for cx in (bb[0].x + 0.03, bb[1].x - 0.03):
                for cy in (bb[0].y + 0.03, bb[1].y - 0.03):
                    hit = bvh.ray_cast(Vector((cx, cy, 0.05)), Vector((0, 0, -1)), 0.2)
                    if hit[0] is None:
                        support_issues.append(dict(prop=pid, no_support_at=[round(cx, 2), round(cy, 2)]))
    res['prop_support_issues'] = support_issues
    res['prop_wall_contact_issues'] = wall_issues
    zones = {
        'van_path_middle_bay': ((-1.85, -15.0, 0.03), (1.85, 0.2, 2.85)),
        'door_Middle_opening': ((-1.88, -6.3, 0.02), (1.88, -5.6, 3.45)),
        'door_West_opening': ((6.2, -6.3, 0.02), (10.15, -5.6, 3.45)),
        'west_handin_zone': ((6.4, -5.3, 0.02), (9.95, -0.3, 2.6)),
        'pit_volume': ((-0.44, -3.39, -1.49), (0.44, 0.29, -0.01)),
        'partition_doorway_W': ((4.25, 0.47, 0.02), (4.75, 1.53, 2.18)),
        'partition_doorway_E': ((-4.75, 0.47, 0.02), (-4.25, 1.53, 2.18)),
        'west_bay_drive_in': ((6.3, -15.0, 0.03), (10.05, -0.3, 2.85)),
    }
    zres = {}
    for zn, (lo, hi) in zones.items():
        blk_props = [r.name for r in prop_roots if aabb_overlap(bbox(r), lo, hi)]
        blk_geo = box_hits(bverts, lo, hi)
        blk_ucx = []
        for o in bpy.data.objects:
            if o.name.startswith('UCX_WS_Building') and zn != 'pit_volume':
                bb = (Vector([min((o.matrix_world @ v.co)[i] for v in o.data.vertices) for i in range(3)]),
                      Vector([max((o.matrix_world @ v.co)[i] for v in o.data.vertices) for i in range(3)]))
                if aabb_overlap(bb, lo, hi):
                    blk_ucx.append(o.name)
        zres[zn] = dict(props=blk_props, building_vertices=len(blk_geo), sample=blk_geo[:4], colliders=blk_ucx)
    res['clear_zones'] = zres
    # ---------- lamps hang from rafters
    lamp_issues = []
    for x, y in B.LAMPS:
        for dy in (-0.45, 0.45):
            hit = bvh.ray_cast(Vector((x, y + dy, B.LAMP_Z + 0.002)), Vector((0, 0, 1)), 2.0)
            exp = B.zr(y + dy) - 0.32 - B.LAMP_Z
            if hit[0] is None or abs(hit[3] - exp) > 0.03:
                lamp_issues.append(dict(lamp=[x, y], dy=dy, hit=None if hit[0] is None else round(hit[3], 3), expected=round(exp, 3)))
    res['lamp_support_issues'] = lamp_issues
    # ---------- budgets
    rep = json.load(open(os.path.join(OUT, 'Workshop_W86_report_v01.json')))
    res['budget'] = dict(building_lod0=rep['building_lod0_tris'], building_lod0_limit=25000,
                         props_lod0=rep['props_total_lod0_tris'], props_limit=25000,
                         props_over_500_without_lod=[k for k, v in rep['props_tris'].items() if v['lod0'] > 500 and not v['lod1']])
    path = os.path.join(OUT, 'Workshop_W86_checks_v01.json')
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(res, f, indent=1)
    short = dict(res)
    short['coplanar_same_facing_overlaps'] = res['coplanar_same_facing_overlaps'][:12]
    print('CHECKS', json.dumps(short, indent=1))


if __name__ == '__main__':
    main()
