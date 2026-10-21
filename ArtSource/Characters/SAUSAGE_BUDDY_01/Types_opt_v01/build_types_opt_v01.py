"""Sausage Buddy NPC types: lighter LOD0 derivatives (opt v01) of Vadim's pool models. Blender 5.2, background.

  blender -b --factory-startup --python ArtSource/Characters/SAUSAGE_BUDDY_01/Types_opt_v01/build_types_opt_v01.py -- [--types A,B] [--out DIR]

Source: Types/<TYPE>/SAUSAGE_BUDDY_<TYPE>_vNN.blend (the current pool revision, never modified). Output (never overwritten):
<out>/SAUSAGE_BUDDY_<TYPE>_vNN_opt_v01.{blend,fbx} + reports/<TYPE>.json (default <out> = this folder);
--summary merges the per-type reports into opt_report_opt_v01.json and prints the table (no Blender work).

Which types: only those above the crowd budget of the benchmark NPC (Buddy A/B v04 = 14,176 / 14,479 tris, budget 12-15k,
OPTIMIZATION_REPORT_v04.md); lighter types stay as they are.

Per type, on the same rig (Buddy_Rig_Mixamo65, never touched), same object names, materials and their order:
1. Hidden faces: a Body or Outfit face is removed when, from its centre and near each corner, every ray over its outer
   hemisphere (64-direction sphere) hits the Body or Outfit, in each of 17 poses (rest + frames of Idle, panic run/turn,
   trip, play-dead, hide, police call, bonk, surrender). The Face mesh (eyes and lids move by shape keys) and the props
   (hand props are dropped in the game) never count as cover. A material never loses all its faces.
2. Controlled decimation (edge collapse) of the Outfit and the props (and of a Body still denser than the BASE body),
   material by material (largest first, the others frozen): the lowest ratio for which that material's surface
     - stays within TOL of step 1's mesh (both directions, 99th / 99.9th percentile, at rest and skinned in CHECK_POSES),
     - keeps its shading (smooth-normal change: area-weighted mean <= NORMAL_MEAN_DEG, 98 % of the area <= NORMAL_P98_DEG),
     - loses or turns over no surface (MAX_FLIPPED_MM2: a collapsed thin fold shows as a hole with back-face culling).
   Never collapsed: material and flat/smooth borders, open edges and HEM_RINGS rings around the source's open edges
   (hems, cuffs, lapels), edges folding more than FEATURE_DEG (shell rims), steps in the skin weights (> WEIGHT_STEP),
   small loose parts. TOL = 1.5 / 3 mm: about 1 / 2 px at 1.2 m, the closest normal view (Unity vertical FOV 60,
   1080p: 1 px = 1.4 mm); the benchmark v04 itself accepted differences of a few mm. Before it, quads are split along
   the diagonal Blender draws them with (the approved previews), so no fold moves.
   The base Body and the Face (shape keys, the type's identity) are not decimated.
3. Shading kept: custom corner normals taken from the source surface at the same place (removed neighbours and
   collapses would re-weight the computed normals).
4. Skin weights: at most 4 influences per vertex, normalised (as the builder writes them); no unweighted vertices.
Export exactly as build_buddy.py exports a type (rig + Body/Outfit/Face/Props_*, Idle only, same FBX options).
Review renders: render_compare_opt_v01.py; FBX check against the source: verify_fbx_opt_v01.py.
"""
import argparse, json, math, sys, time
from pathlib import Path
import bpy, bmesh
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from mathutils.geometry import barycentric_transform

HERE = Path(__file__).resolve().parent
TYPES_DIR = HERE.parent / 'Types'
TAG = 'opt_v01'
RIG = 'Buddy_Rig_Mixamo65'
# Vadim's pool with current revisions (= NpcTypesImportV01.Pool).
POOL = [("FOREST_OD_JUNKIE", 1), ("FOREST_STASHER", 3),
        ("HAMLET_GRANNY", 7), ("HAMLET_SHEPHERD", 6), ("HAMLET_BODYBUILDER", 4), ("HAMLET_BOXERS_GRANDPA", 5),
        ("CONSTR_INDIAN", 7), ("CONSTR_UZBEK", 4), ("CONSTR_MEXICAN", 4), ("CONSTR_AFROAMERICAN", 5), ("CONSTR_ARAB", 5),
        ("BAD_GOPNIK", 5), ("BAD_RAPPER", 10), ("BAD_HUSTLER", 4), ("BAD_DRUNK", 4), ("BAD_GIRL", 7), ("BAD_BOMZH", 1),
        ("BAD_BOMZHIHA", 2), ("BAD_VAPER", 2), ("BAD_ALTGIRL", 14),
        ("OLD_RAPPER", 1), ("OLD_STREAMER", 9), ("OLD_STUDENT", 8), ("OLD_OFFICE", 4), ("OLD_FITNESS", 5), ("OLD_COURIER", 5),
        ("OLD_BUSINESSMAN", 3), ("OLD_KAREN", 6),
        ("PROM_FOREMAN", 4), ("PROM_SAILOR", 3),
        ("BEACH_CORN", 3), ("BEACH_CASTLE", 1), ("BEACH_SUNBURN", 2), ("BEACH_LIFEGUARD", 3), ("BEACH_DETECTOR", 3),
        ("BEACH_NUDIST", 1), ("BEACH_BURIED", 1)]
BUDGET = 15000            # crowd budget, upper end (benchmark Buddy A v04 = 14,176)
BASE_BODY_TRIS = 5424     # the BASE body; a denser Body (bust reshape) may be decimated
TOL = {'p99': 0.0015, 'p999': 0.003}     # m; ~1 / 2 px at 1.2 m (vertical FOV 60, 1080p: 1 px = 1.4 mm)
MIN_GAIN = 0.10           # keep the original when the whole type gets less than 10 % lighter
SMALL_PART = 40           # loose parts with fewer faces are never decimated (buttons, freckles, laces)
HIDDEN = True             # step 1 on (review experiments can switch it off)
HIDDEN_MARGIN = 0         # rings of hidden faces kept along the visible ones (1 tried: +12-20 % tris, fixed nothing seen)
HEM_RINGS = 2             # the source's open edges (hems, cuffs, lapels, collars) and this many rings around them are protected
NORMAL_MEAN_DEG = 2.0     # shading: mean change of the smooth normal over the material's surface (area-weighted), deg
NORMAL_P98_DEG = 8.0      # ... and on 98 % of it (a local blotch on a belly or hem)
MAX_FLIPPED_MM2 = 2.0     # surface whose facing flipped or got lost (collapsed folds), mm2 per object
WEIGHT_STEP = 0.2         # edges between differently weighted vertices are not collapsed
FEATURE_DEG = 35.0        # edges folding more than this (shell rims, creases) are kept: collapsing across them
                          # spreads the rim's normal over long triangles (dark patches on a vest bottom)
MIN_MATERIAL_TRIS = 150   # smaller material regions are not decimated
SEARCH_STEPS = 7          # binary search steps per material
VERBOSE = False
CHECK_POSES = [('Idle', 1), ('Panic_Run_Loop', 5), ('FakeSurrender_Flee', 20)]   # deviation also measured skinned
POSES = [(None, 0), ('Idle', 1), ('Idle', 30), ('Panic_Run_Loop', 1), ('Panic_Run_Loop', 5), ('Panic_Run_Loop', 10),
         ('Panic_Run_Loop', 14), ('Panic_TurnFlee', 20), ('Panic_TurnFlee', 60), ('Panic_TurnFlee', 120), ('TripFall', 10),
         ('TripFall', 30), ('PlayDead_Loop', 1), ('Hide_Loop', 1), ('PoliceCall', 30), ('LookBack_Bonk', 20),
         ('FakeSurrender_Flee', 20)]


def tris_of(me):
    return sum(len(p.vertices) - 2 for p in me.polygons)


def sphere_dirs(n=64):
    out = []
    for i in range(n):
        z = 1 - 2 * (i + 0.5) / n
        r = math.sqrt(max(0.0, 1 - z * z))
        phi = i * math.pi * (3 - math.sqrt(5))
        out.append(Vector((r * math.cos(phi), r * math.sin(phi), z)))
    return out


# ------------------------------------------------------------------ 1. hidden faces
def hidden_faces(rig, cover, candidates):
    """{object name: set(face index)} of candidate faces covered in every pose (occluders = cover objects).
    Covered = from the face centre and from points near each of its corners, every ray of the outer hemisphere hits
    another face (the face's own, possibly non-planar, surface does not count)."""
    dirs = sphere_dirs()
    left = {o.name: set(range(len(o.data.polygons))) for o in candidates}
    scene = bpy.context.scene
    keep_action = rig.animation_data.action if rig.animation_data else None
    keep_frame, keep_pos = scene.frame_current, rig.data.pose_position
    for act, frame in POSES:
        if act is not None and act not in bpy.data.actions:
            continue
        rig.data.pose_position = 'REST' if act is None else 'POSE'
        if act is not None:
            rig.animation_data.action = bpy.data.actions[act]
        scene.frame_set(frame)
        dg = bpy.context.evaluated_depsgraph_get()
        verts, polys, faces_of, bases = [], [], {}, {}
        for o in cover:
            oe = o.evaluated_get(dg)
            me = oe.to_mesh()
            mw = o.matrix_world
            base = len(polys)
            bases[o.name] = base
            co = [mw @ v.co for v in me.vertices]
            vbase = len(verts)
            verts += co
            polys += [[vbase + i for i in p.vertices] for p in me.polygons]
            if o.name in left:
                rot = mw.to_3x3()
                faces_of[o.name] = [([co[i] for i in p.vertices], (rot @ p.normal).normalized()) for p in me.polygons]
            oe.to_mesh_clear()
        bvh = BVHTree.FromPolygons(verts, polys)

        def blocked(origin, d, own):
            for _ in range(6):
                loc, _n, idx, dist = bvh.ray_cast(origin, d, 3.0)
                if loc is None:
                    return False
                if idx != own:
                    return True
                origin = loc + d * 1e-5
            return False

        for name, faces in left.items():
            still = set()
            base = bases[name]
            for fi in faces:
                corners, n = faces_of[name][fi]
                if n.length < 0.5:
                    continue                      # degenerate face: keep it
                c = sum(corners, Vector()) / len(corners)
                hemi = [d for d in dirs if d.dot(n) >= 0.05]
                pts = [c] + [c + (q - c) * 0.85 for q in corners]
                if all(blocked(p + n * 0.001, d, base + fi) for p in pts for d in hemi):
                    still.add(fi)
            left[name] = still
    rig.data.pose_position = keep_pos
    if keep_action is not None:
        rig.animation_data.action = keep_action
    scene.frame_set(keep_frame)
    return left


def erode(ob, faces, rings):
    """Hidden faces next to visible ones stay (rings of faces): the cover may move by up to TOL when it is decimated,
    and a removed face right at its edge would show as a hole."""
    me = ob.data
    for _ in range(rings):
        visible_verts = {v for p in me.polygons if p.index not in faces for v in p.vertices}
        faces = {fi for fi in faces if not any(v in visible_verts for v in me.polygons[fi].vertices)}
    return faces


def delete_faces(ob, faces):
    """Deletes faces (and verts/edges left without faces); a material keeps at least its faces if all would go."""
    me = ob.data
    by_mat, hid_mat = {}, {}
    for p in me.polygons:
        by_mat[p.material_index] = by_mat.get(p.material_index, 0) + 1
    for fi in faces:
        m = me.polygons[fi].material_index
        hid_mat[m] = hid_mat.get(m, 0) + 1
    kept_whole = {m for m, n in hid_mat.items() if n >= by_mat[m]}
    faces = {fi for fi in faces if me.polygons[fi].material_index not in kept_whole}
    bm = bmesh.new(); bm.from_mesh(me); bm.faces.ensure_lookup_table()
    bmesh.ops.delete(bm, geom=[bm.faces[i] for i in sorted(faces)], context='FACES')
    bm.to_mesh(me); bm.free(); me.update()
    return len(faces), sorted(me.materials[m].name for m in kept_whole)


# ------------------------------------------------------------------ 2. controlled decimation
def mark_hems(ob):
    """Point attribute OPT_HEM = 1 on the source's open edges and HEM_RINGS rings around them (before step 1, so the
    holes left by removed hidden faces are not hems). A garment edge is a thin rolled surface: collapsing across it
    stays within TOL but changes its shading (hems and lapels turn dark or light)."""
    bm = bmesh.new(); bm.from_mesh(ob.data)
    ring = {v for e in bm.edges if len(e.link_faces) == 1 for v in e.verts}
    hem = set(ring)
    for _ in range(HEM_RINGS):
        ring = {e.other_vert(v) for v in ring for e in v.link_edges} - hem
        hem |= ring
    values = [0.0] * len(bm.verts)
    for v in hem:
        values[v.index] = 1.0
    bm.free()
    attr = ob.data.attributes.get('OPT_HEM') or ob.data.attributes.new('OPT_HEM', 'FLOAT', 'POINT')
    attr.data.foreach_set('value', values)
    return len(hem)


def weight_steps(ob):
    """Vertices on edges whose skin weights differ by more than WEIGHT_STEP (L1 over the bones): a collapse there
    blends two different weightings, and the merged vertex moves its own way when skinned (shoulders, armholes)."""
    me = ob.data
    names = [g.name for g in ob.vertex_groups]
    w = [{names[g.group]: g.weight for g in v.groups if g.weight > 1e-4 and names[g.group] != 'OPT_PROTECT'} for v in me.vertices]
    out = set()
    for e in me.edges:
        a, b = w[e.vertices[0]], w[e.vertices[1]]
        if sum(abs(a.get(k, 0.0) - b.get(k, 0.0)) for k in a.keys() | b.keys()) > WEIGHT_STEP:
            out.update(e.vertices)
    return out


def protect_group(ob, only=None):
    """OPT_PROTECT = vertices the collapse must keep: skin-weight steps, hems, material and flat/smooth borders,
    open edges, edges folding more than FEATURE_DEG, small loose parts and, when only is a material index, every vertex
    of the other materials."""
    bm = bmesh.new(); bm.from_mesh(ob.data); bm.verts.ensure_lookup_table()
    prot = weight_steps(ob)
    hem = ob.data.attributes.get('OPT_HEM')
    if hem is not None:
        prot.update(i for i, a in enumerate(hem.data) if a.value > 0.5)
    feature = math.radians(FEATURE_DEG)
    for e in bm.edges:
        lf = e.link_faces
        if len(lf) != 2 or lf[0].material_index != lf[1].material_index or lf[0].smooth != lf[1].smooth or                 lf[0].normal.angle(lf[1].normal, 0.0) > feature:
            prot.update(v.index for v in e.verts)
    if only is not None:
        prot.update(v.index for f in bm.faces if f.material_index != only for v in f.verts)
    seen = set()
    for v in bm.verts:
        if v.index in seen:
            continue
        isl, stack = [], [v]; seen.add(v.index)
        while stack:
            x = stack.pop(); isl.append(x.index)
            for e in x.link_edges:
                y = e.other_vert(x)
                if y.index not in seen:
                    seen.add(y.index); stack.append(y)
        if len({f.index for i in isl for f in bm.verts[i].link_faces}) < SMALL_PART:
            prot.update(isl)
    free = len(bm.verts) - len(prot)
    bm.free()
    g = ob.vertex_groups.get('OPT_PROTECT')
    if g is not None:
        ob.vertex_groups.remove(g)
    g = ob.vertex_groups.new(name='OPT_PROTECT')
    if prot:
        g.add(sorted(prot), 1.0, 'REPLACE')
    return g.name, free


def snapshot(me):
    """Coordinates, triangles and their materials of a (triangulated) mesh."""
    me.calc_loop_triangles()
    return ([v.co.copy() for v in me.vertices], [tuple(t.vertices) for t in me.loop_triangles],
            [me.polygons[t.polygon_index].material_index for t in me.loop_triangles])


def surface(snap, only):
    """Sample points (vertices and triangle centres) and BVH of one material's triangles."""
    co, tris, mats = snap
    sel = [t for t, m in zip(tris, mats) if m == only]
    if not sel:
        return [], None
    verts = {i for t in sel for i in t}
    pts = [co[i] for i in verts] + [(co[a] + co[b] + co[c]) / 3 for a, b, c in sel]
    return pts, BVHTree.FromPolygons(co, sel)


def deviation(ref, dec):
    (pr, br), (pd, bd) = ref, dec
    if bd is None or br is None:
        return {'p99': 1.0, 'p999': 1.0, 'max': 1.0}
    a = np.array([(bd.find_nearest(p)[0] - p).length for p in pr])
    b = np.array([(br.find_nearest(p)[0] - p).length for p in pd])
    return {'p99': float(max(np.percentile(a, 99), np.percentile(b, 99))),
            'p999': float(max(np.percentile(a, 99.9), np.percentile(b, 99.9))),
            'max': float(max(a.max(), b.max()))}


def smooth_normal_at(me, vn, tri, loc):
    """Interpolated vertex normal (smooth face) or face normal (flat face) at loc on loop triangle tri."""
    p = me.polygons[tri.polygon_index]
    if not p.use_smooth:
        return p.normal.copy()
    i0, i1, i2 = tri.vertices
    w = barycentric_transform(loc, me.vertices[i0].co, me.vertices[i1].co, me.vertices[i2].co,
                              Vector((1, 0, 0)), Vector((0, 1, 0)), Vector((0, 0, 1)))
    return (vn[i0] * w.x + vn[i1] * w.y + vn[i2] * w.z).normalized()


def shading_samples(me):
    """Per triangle of the reference: centre, face normal, smooth normal there, material, area."""
    me.calc_loop_triangles()
    vn = [v.normal.copy() for v in me.vertices]
    out = []
    for lt in me.loop_triangles:
        c = lt.center.copy()
        out.append((c, lt.normal.copy(), smooth_normal_at(me, vn, lt, c), me.polygons[lt.polygon_index].material_index, lt.area))
    return out


def shading_change(samples, me, only):
    """Area-weighted mean angle (deg) between the reference's smooth normals and the decimated surface's, found 1 mm
    above each sample of material only along its face normal (same material, same facing; others are skipped)."""
    me.calc_loop_triangles()
    tris = me.loop_triangles
    vn = [v.normal.copy() for v in me.vertices]
    bvh = BVHTree.FromPolygons([v.co for v in me.vertices], [t.vertices for t in tris])
    ang, wts = [], []
    for c, fn, sn, mat, area in samples:
        if mat != only:
            continue
        loc, hn, idx, _d = bvh.ray_cast(c + fn * 0.001, -fn, 0.001 + 2 * TOL['p999'])
        if loc is None or hn.dot(fn) < 0.5 or me.polygons[tris[idx].polygon_index].material_index != mat:
            continue
        ang.append(math.degrees(sn.angle(smooth_normal_at(me, vn, tris[idx], loc), 0.0)))
        wts.append(area)
    if not ang:
        return 0.0, 0.0
    ang, wts = np.array(ang), np.array(wts)
    order = np.argsort(ang)
    cum = np.cumsum(wts[order]) / wts.sum()
    return float(np.average(ang, weights=wts)), float(ang[order][min(len(ang) - 1, np.searchsorted(cum, 0.98))])


def material_tree(snap, only):
    co, tris, mats = snap
    sel = [t for t, m in zip(tris, mats) if m == only]
    return BVHTree.FromPolygons(co, sel) if sel else None


def facing_loss(ref_tree, samples, me, only):
    """mm2 of material only whose facing is lost, both ways: decimated triangles with no reference face facing the
    same way within reach (flipped), and reference triangles with no such decimated face (a thin fold whose outer
    layer collapsed onto the inner one: within TOL, but the game culls the inner layer's back -> a hole)."""
    reach = TOL['p999'] + 0.0005
    me.calc_loop_triangles()
    mine = material_tree(snapshot(me), only)
    area = 0.0
    for lt in me.loop_triangles:
        if me.polygons[lt.polygon_index].material_index != only or lt.area < 1e-9:
            continue
        hits = ref_tree.find_nearest_range(lt.center, reach) if ref_tree else []
        if hits and not any(h[1].dot(lt.normal) > 0.0 for h in hits):
            area += lt.area
    for c, fn, _sn, mat, a in samples:
        if mat != only or a < 1e-9:
            continue
        hits = mine.find_nearest_range(c, reach) if mine else []
        if not any(h[1].dot(fn) > 0.0 for h in hits):
            area += a
    return area * 1e6


def triangulate_as_shown(me):
    """Splits every quad along the diagonal Blender itself draws it with (its loop triangles) and the n-gons as
    'beauty' (as Blender fills them). The previews Vadim approved show this surface; a fixed 0-2 split moves strongly
    non-planar quads by up to 8 mm (lapel folds open a gap)."""
    me.calc_loop_triangles()
    tris_of_poly = {}
    for lt in me.loop_triangles:
        tris_of_poly.setdefault(lt.polygon_index, []).append(set(lt.vertices))
    bm = bmesh.new(); bm.from_mesh(me)
    bm.faces.ensure_lookup_table(); bm.verts.ensure_lookup_table()
    quads = [(bm.faces[i], tris_of_poly.get(i)) for i in range(len(bm.faces)) if len(bm.faces[i].verts) == 4]
    for f, tl in quads:
        if not tl or len(tl) != 2:
            continue
        a, b = sorted(tl[0] & tl[1])
        try:
            bmesh.utils.face_split(f, bm.verts[a], bm.verts[b])
        except ValueError:
            pass
    rest = [f for f in bm.faces if len(f.verts) > 3]
    if rest:
        bmesh.ops.triangulate(bm, faces=rest, quad_method='BEAUTY', ngon_method='BEAUTY')
    bm.to_mesh(me); bm.free(); me.update()


def set_pose(rig, act, frame):
    rig.data.pose_position = 'REST' if act is None else 'POSE'
    if act is not None:
        rig.animation_data.action = bpy.data.actions[act]
    bpy.context.scene.frame_set(frame)


def decimate(ob, rig):
    """Per material (largest first, the others frozen): the lowest collapse ratio whose result stays within the
    limits for that material (binary search), applied. Returns the report entry.
    The mesh is first triangulated as Blender draws it (triangulate_as_shown): the collapse triangulates anyway, and
    a non-planar quad has no single surface to measure against otherwise. The deviation is measured at rest and
    skinned in CHECK_POSES (weights are blended at collapsed vertices)."""
    me0 = ob.data
    t0 = tris_of(me0)
    if t0 < 200:
        return {'ratio': 1.0, 'tris_before': t0, 'tris_after': t0, 'note': 'small, not decimated'}
    untouched = me0.copy()
    triangulate_as_shown(me0)
    arm = [m for m in ob.modifiers if m.type == 'ARMATURE']
    keep = (rig.animation_data.action, bpy.context.scene.frame_current, rig.data.pose_position)
    poses = [(a, f) for a, f in CHECK_POSES if a in bpy.data.actions]

    def evaluated(skinned):
        for m in arm:
            m.show_viewport = skinned
        dg = bpy.context.evaluated_depsgraph_get()
        oe = ob.evaluated_get(dg)
        me = oe.to_mesh()
        return oe, me

    ref_rest = snapshot(me0)                # the undecimated surface, at rest and skinned
    shade = shading_samples(me0)
    ref_posed = []
    for a, f in poses:
        set_pose(rig, a, f)
        oe, me = evaluated(True)
        ref_posed.append(snapshot(me))
        oe.to_mesh_clear()
    tri_count = {}
    for m in ref_rest[2]:
        tri_count[m] = tri_count.get(m, 0) + 1
    per_mat = {}
    for only in sorted(tri_count, key=lambda m: -tri_count[m]):
        if tri_count[only] < MIN_MATERIAL_TRIS:
            continue
        name = ob.data.materials[only].name
        group, free = protect_group(ob, only)
        if free < 3:
            continue
        mod = ob.modifiers.new('OPT_Decimate', 'DECIMATE')
        mod.decimate_type = 'COLLAPSE'; mod.use_collapse_triangulate = False
        mod.vertex_group = group; mod.invert_vertex_group = True; mod.vertex_group_factor = 1000.0
        with bpy.context.temp_override(object=ob, active_object=ob):
            bpy.ops.object.modifier_move_to_index(modifier=mod.name, index=0)
        before = tris_of(ob.data)
        mine_before = sum(1 for p in ob.data.polygons if p.material_index == only)
        ref_s = surface(ref_rest, only)
        ref_p = [surface(snap, only) for snap in ref_posed]
        ref_tree = material_tree(ref_rest, only)

        def trial(r):
            mod.ratio = r
            oe, me = evaluated(False)
            snap = snapshot(me)
            dev = deviation(ref_s, surface(snap, only))
            dev['normal_mean_deg'], dev['normal_p98_deg'] = shading_change(shade, me, only)
            dev['flipped_mm2'] = facing_loss(ref_tree, shade, me, only)
            ok = set(snap[2]) >= set(ref_rest[2])
            tris = len(snap[1])
            oe.to_mesh_clear()
            dev['posed_p99'] = dev['posed_p999'] = 0.0
            for (a, f), rp in zip(poses, ref_p):
                set_pose(rig, a, f)
                oe, me = evaluated(True)
                d = deviation(rp, surface(snapshot(me), only))
                oe.to_mesh_clear()
                dev['posed_p99'] = max(dev['posed_p99'], d['p99'])
                dev['posed_p999'] = max(dev['posed_p999'], d['p999'])
            ok = ok and max(dev['p99'], dev['posed_p99']) <= TOL['p99'] and max(dev['p999'], dev['posed_p999']) <= TOL['p999'] \
                and dev['normal_mean_deg'] <= NORMAL_MEAN_DEG and dev['normal_p98_deg'] <= NORMAL_P98_DEG \
                and dev['flipped_mm2'] <= MAX_FLIPPED_MM2
            if VERBOSE:
                print(f"[TRIAL] {ob.name}/{name} r={r:.3f} tris {tris} ok={ok} " +
                      ' '.join(f'{k}={v * (1000 if k[0] in "pm" else 1):.2f}' for k, v in dev.items()), flush=True)
            return ok, tris, dev

        # the ratio is of the whole mesh: search only down to what this material alone can give
        lo = max(0.02, 1.0 - 0.95 * mine_before / before)
        hi, best = 1.0, None
        for _ in range(SEARCH_STEPS):
            mid = (lo + hi) / 2
            ok, t, dev = trial(mid)
            if ok:
                hi, best = mid, (mid, t, dev)
            else:
                lo = mid
        if best is None:
            ob.modifiers.remove(mod)
            continue
        mod.ratio = best[0]
        for m in arm:
            m.show_viewport = True
        with bpy.context.temp_override(object=ob, active_object=ob):
            bpy.ops.object.modifier_apply(modifier=mod.name)
        dev = best[2]
        per_mat[name] = {'tris': [mine_before, sum(1 for p in ob.data.polygons if p.material_index == only)],
                         'dev_mm': {k: round(v * 1000, 2) for k, v in dev.items() if k[0] in 'pm'},
                         'normal_mean_deg': round(dev['normal_mean_deg'], 2), 'normal_p98_deg': round(dev['normal_p98_deg'], 1),
                         'lost_mm2': round(dev['flipped_mm2'], 1)}
    rig.animation_data.action = keep[0]
    bpy.context.scene.frame_set(keep[1])
    rig.data.pose_position = keep[2]
    for m in arm:
        m.show_viewport = True
    if ob.vertex_groups.get('OPT_PROTECT') is not None:
        ob.vertex_groups.remove(ob.vertex_groups['OPT_PROTECT'])
    if not per_mat:                        # nothing gained: keep the mesh as it was (quads)
        tri_mesh, name = ob.data, ob.data.name
        ob.data = untouched
        bpy.data.meshes.remove(tri_mesh)
        untouched.name = name
    else:
        bpy.data.meshes.remove(untouched)
    return {'tris_before': t0, 'tris_after': tris_of(ob.data), 'materials': per_mat}


# ------------------------------------------------------------------ 3. shading
def keep_shading(ob, source):
    """Custom corner normals = the source mesh's normal at the same place: the nearest point of the source surface of
    the same material that faces the same way (interpolated vertex normal on smooth faces, face normal on flat ones).
    Fixes what changing the triangles does to the computed normals: removed hidden neighbours re-weight the border
    vertices, and long collapsed triangles on dense rounded cloth darken bellies, hems and caps."""
    source.calc_loop_triangles()
    vn = [v.normal.copy() for v in source.vertices]
    co = [v.co.copy() for v in source.vertices]
    by_mat = {}
    for lt in source.loop_triangles:
        by_mat.setdefault(source.polygons[lt.polygon_index].material_index, []).append(lt)
    trees = {m: (BVHTree.FromPolygons(co, [lt.vertices for lt in lts]), lts) for m, lts in by_mat.items()}
    me = ob.data
    current = [c.vector.copy() for c in me.corner_normals]
    out = list(current)
    kept = 0
    for p in me.polygons:
        tree = trees.get(p.material_index)
        if tree is None:
            continue
        bvh, lts = tree
        pn = p.normal
        for li in p.loop_indices:
            pos = me.vertices[me.loops[li].vertex_index].co
            hits = bvh.find_nearest_range(pos, 0.004)
            if not hits:
                continue
            dmin = min(h[3] for h in hits)
            near = [h for h in hits if h[3] <= dmin + 0.00005]
            loc, hn, idx, _d = max(near, key=lambda h: h[1].dot(pn))
            if hn.dot(pn) < 0.3:
                continue
            out[li] = smooth_normal_at(source, vn, lts[idx], loc)
            kept += 1
    me.normals_split_custom_set(out)
    return {'corners': len(out), 'from_source': kept}


# ------------------------------------------------------------------ 4. weights
def clean_weights(ob, bones):
    idx = {i for i, g in enumerate(ob.vertex_groups) if g.name in bones}
    vgs = ob.vertex_groups
    fixed = unweighted = max_infl = 0
    for v in ob.data.vertices:
        ws = sorted(((g.group, g.weight) for g in v.groups if g.group in idx and g.weight > 1e-4), key=lambda t: -t[1])
        keep = ws[:4]
        tot = sum(w for _, w in keep)
        if tot <= 0:
            unweighted += 1
            continue
        allg = [g.group for g in v.groups if g.group in idx]
        if len(allg) != len(keep) or abs(tot - 1.0) > 1e-3:
            for gi in set(allg) - {k for k, _ in keep}:
                vgs[gi].remove([v.index])
            for gi, w in keep:
                vgs[gi].add([v.index], w / tot, 'REPLACE')
            fixed += 1
        max_infl = max(max_infl, len(keep))
    return {'fixed_vertices': fixed, 'unweighted': unweighted, 'max_influences': max_infl}


# ------------------------------------------------------------------ per type
def stats(objs):
    return {o.name: tris_of(o.data) for o in objs}


def optimise(tid, rev, out_dir):
    src = TYPES_DIR / tid / f'SAUSAGE_BUDDY_{tid}_v{rev:02d}.blend'
    stem = f'SAUSAGE_BUDDY_{tid}_v{rev:02d}_{TAG}'
    out = {'blend': out_dir / (stem + '.blend'), 'fbx': out_dir / (stem + '.fbx')}
    bpy.ops.wm.open_mainfile(filepath=str(src))
    rig = bpy.data.objects[RIG]
    objs = sorted((o for o in bpy.data.objects if o.type == 'MESH' and o.parent == rig), key=lambda o: o.name)
    by = {o.name: o for o in objs}
    before = stats(objs)
    rep = {'type': tid, 'revision': rev, 'source': str(src.relative_to(HERE.parent.parent.parent.parent)).replace('\\', '/'),
           'tris_before': before, 'total_before': sum(before.values())}
    if rep['total_before'] <= BUDGET:
        rep['result'] = 'unchanged: within the crowd budget'
        return rep
    t = time.time()
    mats_before = {o.name: [m.name for m in o.data.materials] for o in objs}
    used_before = {o.name: {p.material_index for p in o.data.polygons} for o in objs}
    rig_bones = {b.name: (b.head_local.copy(), b.matrix_local.copy()) for b in rig.data.bones}
    bones = set(rig_bones)
    originals = {o.name: o.data.copy() for o in objs if o.name != 'Face'}
    hems = {o.name: mark_hems(o) for o in objs if o.name != 'Face'}
    cover = [o for o in (by.get('Body'), by.get('Outfit')) if o is not None]
    hid = hidden_faces(rig, cover, cover) if HIDDEN else {o.name: set() for o in cover}
    rep['hidden_removed'] = {}
    for o in cover:
        n, kept = delete_faces(o, erode(o, hid[o.name], HIDDEN_MARGIN))
        rep['hidden_removed'][o.name] = {'faces': n, 'materials_kept_whole': kept, 'tris_after': tris_of(o.data)}
    rep['decimation'] = {}
    for o in objs:
        if o.name == 'Face' or (o.name == 'Body' and tris_of(o.data) <= BASE_BODY_TRIS):
            continue
        rep['decimation'][o.name] = decimate(o, rig)
    for o in objs:
        if o.data.attributes.get('OPT_HEM') is not None:
            o.data.attributes.remove(o.data.attributes['OPT_HEM'])
    rep['hem_verts'] = hems
    rep['shading'] = {}
    for o in objs:
        if o.name in originals and tris_of(o.data) != before[o.name]:
            rep['shading'][o.name] = keep_shading(o, originals[o.name])
    for m in originals.values():
        bpy.data.meshes.remove(m)
    rep['weights'] = {o.name: clean_weights(o, bones) for o in objs if o.name != 'Face'}
    after = stats(objs)
    rep['tris_after'] = after
    rep['total_after'] = sum(after.values())
    rep['seconds'] = round(time.time() - t, 1)
    # checks: rig untouched, materials (names and order) unchanged and all still used, every vertex weighted
    problems = []
    if {b.name for b in rig.data.bones} != bones or any(
            (b.head_local - rig_bones[b.name][0]).length > 1e-7 or
            max(abs(x - y) for r1, r2 in zip(b.matrix_local, rig_bones[b.name][1]) for x, y in zip(r1, r2)) > 1e-7
            for b in rig.data.bones):
        problems.append('rig changed')
    for o in objs:
        if [m.name for m in o.data.materials] != mats_before[o.name]:
            problems.append(f'{o.name}: material slots changed')
        used = {p.material_index for p in o.data.polygons}
        if used != used_before[o.name]:
            problems.append(f'{o.name}: used material slots changed {sorted(used_before[o.name] ^ used)}')
        if o.name != 'Face' and rep['weights'][o.name]['unweighted']:
            problems.append(f'{o.name}: unweighted vertices')
    rep['problems'] = problems
    if problems:
        rep['result'] = 'unchanged: checks failed'
        return rep
    if rep['total_after'] > rep['total_before'] * (1 - MIN_GAIN):
        rep['result'] = f'unchanged: gain below {MIN_GAIN:.0%}'
        return rep
    for p in out.values():
        if p.exists():
            sys.exit(f'Refusing to overwrite {p}')
    bpy.ops.wm.save_as_mainfile(filepath=str(out['blend']))
    export_fbx(rig, objs, out['fbx'])
    rep['result'] = 'optimised'
    rep['outputs'] = {k: v.name for k, v in out.items()}
    return rep


def export_fbx(rig, objs, path):
    """As build_buddy.py exports an NPC type: rig + skinned meshes, the Idle clip only, face tracks not exported."""
    face = bpy.data.objects.get('Face')
    if face is not None and face.data.shape_keys and face.data.shape_keys.animation_data:
        face.data.shape_keys.animation_data.action = None
    for a in list(bpy.data.actions):
        if a.name.endswith('_Face') or a.name == 'PoliceCall_Phone':
            bpy.data.actions.remove(a)
    bpy.ops.object.select_all(action='DESELECT')
    for o in [rig] + objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = rig
    rig.data.pose_position = 'POSE'
    rig.animation_data.action = bpy.data.actions['Idle']
    scene = bpy.context.scene
    scene.frame_start, scene.frame_end = 1, 60
    scene.frame_set(1)
    bpy.ops.export_scene.fbx(filepath=str(path), use_selection=True, object_types={'MESH', 'ARMATURE'}, add_leaf_bones=False,
                             use_armature_deform_only=False, bake_anim=True, bake_anim_use_all_actions=False, bake_anim_use_nla_strips=False,
                             bake_anim_simplify_factor=0, axis_forward='-Z', axis_up='Y', apply_unit_scale=True, use_mesh_modifiers=False)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--types', default='')
    ap.add_argument('--out', default=str(HERE))
    ap.add_argument('--tol', default='', help='p99,p999 in mm (review experiments only)')
    ap.add_argument('--summary', action='store_true')
    ap.add_argument('--verbose', action='store_true')
    ap.add_argument('--no-hidden', action='store_true', help='skip step 1 (review experiments only)')
    ap.add_argument('--normal', type=float, default=None, help='NORMAL_MEAN_DEG override (review experiments only)')
    args, _ = ap.parse_known_args(sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else [])
    want = [t for t in args.types.split(',') if t]
    if args.tol:
        TOL['p99'], TOL['p999'] = (float(x) / 1000 for x in args.tol.split(','))
    if args.verbose:
        global VERBOSE
        VERBOSE = True
    if args.no_hidden:
        global HIDDEN
        HIDDEN = False
    if args.normal is not None:
        global NORMAL_MEAN_DEG
        NORMAL_MEAN_DEG = args.normal
    out_dir = Path(args.out); out_dir.mkdir(parents=True, exist_ok=True)
    reports = out_dir / 'reports'; reports.mkdir(exist_ok=True)
    if args.summary:
        return summary(out_dir, reports)
    settings = {'budget_tris': BUDGET, 'tolerance_mm': {k: round(v * 1000, 3) for k, v in TOL.items()}, 'min_gain': MIN_GAIN,
                'normal_mean_deg': NORMAL_MEAN_DEG, 'normal_p98_deg': NORMAL_P98_DEG,
                'small_part_faces': SMALL_PART, 'poses': [f'{a}:{f}' if a else 'rest' for a, f in POSES]}
    for tid, rev in POOL:
        if want and tid not in want:
            continue
        rep = optimise(tid, rev, out_dir)
        rep['settings'] = settings
        print(f"[OPT] {tid} v{rev:02d} {rep['total_before']} -> {rep.get('total_after', rep['total_before'])} {rep['result']} "
              f"{rep.get('problems', '')}", flush=True)
        (reports / f'{tid}.json').write_text(json.dumps(rep, indent=1, ensure_ascii=False), encoding='utf-8')


def summary(out_dir, reports):
    merged, rows = {}, []
    for tid, rev in POOL:
        p = reports / f'{tid}.json'
        if not p.exists():
            continue
        r = json.loads(p.read_text(encoding='utf-8'))
        merged[tid] = r
        after = r['total_after'] if r['result'] == 'optimised' else r['total_before']
        rows.append((r['total_before'], tid, rev, after, r['result']))
    (out_dir / f'opt_report_{TAG}.json').write_text(json.dumps(merged, indent=1, ensure_ascii=False), encoding='utf-8')
    for before, tid, rev, after, res in sorted(rows, reverse=True):
        print(f'[SUM] {tid:<22} v{rev:02d} {before:>6} -> {after:>6}  {100 * (1 - after / before):5.1f} %  {res}')
    print(f'[SUM] total {sum(r[0] for r in rows)} -> {sum(r[3] for r in rows)}')


if __name__ == '__main__':
    main()
