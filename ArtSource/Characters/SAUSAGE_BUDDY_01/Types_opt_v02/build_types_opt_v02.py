"""Sausage Buddy NPC types, opt v02: the close-up mesh (LOD0) without what nobody can see, plus a crowd LOD chain
(LOD1 for 15-40 m, LOD2 beyond 40 m) on the same rig. Blender 5.2, background.

  blender -b --factory-startup --python ArtSource/Characters/SAUSAGE_BUDDY_01/Types_opt_v02/build_types_opt_v02.py -- [--types A,B] [--summary] [--out DIR]

Input: Types_opt_v01/SAUSAGE_BUDDY_<TYPE>_vNN_opt_v01.blend (the reviewed close-up mesh; never modified), or for the 10
POOL_SOURCE types opt_v01 left alone (under its budget) Vadim's source revision; for them LOD0 gets step 1 only
(SOURCE_HIDDEN off): opt_v01's hidden-face removal (step 0), steps 2 and 4 changed 6-3,000 px per type at 1.5 m. Vadim's source in Types/ is read only (shading reference, as opt_v01). Output (never overwritten):
SAUSAGE_BUDDY_<TYPE>_vNN_opt_v02.{blend,fbx} + reports/<TYPE>.json; --summary merges them into opt_report_opt_v02.json.
The --island-normal / --lod-normals / --hem-rings / --lod-ratios switches are for review experiments only.

LOD0 = opt_v01 minus what nobody can see (each step measured per type in the report):
 1. Face interior: Face faces (eye-ball backs, lid and shine shells inside the head) covered by Body + Face + Outfit in
    EVERY sampled state: every STATE_STEP frames (and the last) of the 13 body clips, each with the values of its paired
    *_Face shape-key track, plus rest with every shape key at 1 and Blink + each expression. Covered = the opt_v01 test
    (64-direction hemisphere from the centre and near each corner). A hidden face stays when removing it would turn the
    normal of a vertex of a visible face by more than FACE_NORMAL_DEG in the basis, any shape key or any pair of shape
    keys at 1 (normal_margin): the Face has no custom normals (shape keys), so this keeps its shading as before.
 2. Head skin under the Face: Body faces rigid on the Head bone and covered in every state above.
 3. Clean-up: zero-area faces, duplicate faces (same vertex set), loose vertices/edges are counted only: removing the
    zero-area slivers on bevels changed how their neighbours share normals (review renders: OLD_COURIER backpack edges,
    POLICE radio), so LOD0 keeps them (the LODs drop them).
 4. Small parts: closed loose parts of Outfit/Props that are rigid (same skin weights on every vertex), at most
    PART_DIAG across, outside the face zone (brows, beards, eye bags, glasses... are not touched), with no parallel
    surface within ISLAND_GAP_REACH (no decal or layered part) and not frozen (opt_v01 W86: VIP_BEASTMAN_Logo*,
    CONSTR_INDIAN_Hair), are collapsed one by one to the lowest ratio that keeps
      - the surface within ISLAND_TOL (hard maximum, both directions),
      - no triangle turned over,
      - the shading: the interpolated normal the part will get (custom normals restored) within ISLAND_NORMAL_DEG of
        the current one at every triangle centre and edge midpoint.
    Material borders are locked. Open parts (socks, cards), skinned parts and layered decals were tried and showed a
    1 px change on the review renders, so they are left as they are.
 5. Shading: custom corner normals from Vadim's source surface (opt_v01 keep_shading) on every changed Body/Outfit/Prop.
 6. Skin weights: at most 4 influences, normalised; no unweighted vertex.
All LOD0 cuts are on Head-rigid geometry or on loose parts checked in poses, so they also hold in ragdoll poses.
Not cut: the Body (hands, head silhouette: no collinear rows to drop), Face parts that show, shoe-sole undersides (seen
in Panic_Run from behind, TripFall, PlayDead), hair twists/dreads (10 % fewer triangles already turn their shading up to 13 deg),
skinned garments (opt_v01 took them to 1.5 mm). No normal-map bake: the types have no UVs and flat colour materials.

LOD1 / LOD2: each LOD0 object is collapsed (edit-mode decimate: keeps the Face's shape keys, interpolates skin weights)
to LOD[level]['ratio'] of its triangles, with the garment hems (vertices on open edges of Vadim's source that belong to
a garment-sized part, real_hems: hems, cuffs, collars, sock tops; not decal outlines) and HEM_LOCK_RINGS rings around
them kept (collapsing a rolled hem tilts it into a dark band), and the largest polygon of every material kept (no
material loses its faces), then measured
against LOD0 per material in LOD_POSES (skinned) or, for the Face, in FACE_KEY_STATES: LOD0 vertices and triangle
centres to the LOD surface and LOD vertices to the LOD0 surface. Where the error is over the level's limit, those LOD0
vertices and their neighbours are locked and the collapse is redone with the ratio raised by the share of triangles the
locks hold (joints keep their rings, thin parts their shape); if nothing more can be locked the ratio goes up; once
within limits, LOD_TIGHTEN bisection steps lower the ratio again with the same locks. Limits (vertical FOV 60, 1080p:
1 px = 1.07 mm per metre of distance): LOD1 p99 8 mm / max 16 mm (half a pixel / one pixel at 15 m), LOD2 p99 20 mm /
max 43 mm (at 40 m); open edges (hems, borders of the hidden-face holes) OPEN_EDGE_FACTOR of that; a LOD passes when
p99 holds and at most LOD_OVER_SHARE of the vertices exceed their limit, by at most LOD_OVER_FACTOR (thin tips). The
ratios are targets: the locks the limits need decide the final count (reported per object with every round).
Normals: per vertex and material from the source surface facing the same way (lod_shading); Face: computed.

Names: the .blend keeps LOD0 under the opt_v01 names (Body, Face, Outfit, Props_*) and adds <name>_LOD1 / <name>_LOD2
(collections LOD1 / LOD2, hidden). The FBX follows Unity's LOD import convention: <name>_LOD0 / _LOD1 / _LOD2, all
skinned to the one Buddy_Rig_Mixamo65; the Idle clip only and the export options of opt_v01.
"""
import argparse, json, math, sys, time
from pathlib import Path
import bpy, bmesh
import numpy as np
from mathutils import Vector, kdtree
from mathutils.bvhtree import BVHTree
from mathutils.geometry import barycentric_transform

HERE = Path(__file__).resolve().parent
V01_DIR = HERE.parent / 'Types_opt_v01'
sys.path.insert(0, str(V01_DIR))
sys.dont_write_bytecode = True
import build_types_opt_v01 as B   # noqa: E402  (helpers: tris_of, sphere_dirs, erode, delete_faces, clean_weights, set_pose)

TAG = 'opt_v02'
SRC_TAG = 'opt_v01'
RIG = B.RIG
TYPES_DIR = B.TYPES_DIR
# Current pool revisions that have an opt_v01 (= NpcTypesImportV01.Pool, opt_v01 first batch + W86).
POOL = [("FOREST_OD_JUNKIE", 1), ("FOREST_STASHER", 3),
        ("HAMLET_GRANNY", 7), ("HAMLET_SHEPHERD", 6), ("HAMLET_BOXERS_GRANDPA", 5),
        ("CONSTR_INDIAN", 8), ("CONSTR_UZBEK", 5), ("CONSTR_MEXICAN", 5), ("CONSTR_AFROAMERICAN", 5), ("CONSTR_ARAB", 5),
        ("BAD_GOPNIK", 5), ("BAD_RAPPER", 10), ("BAD_HUSTLER", 4), ("BAD_GIRL", 7), ("BAD_BOMZH", 1),
        ("BAD_BOMZHIHA", 2), ("BAD_VAPER", 2), ("BAD_ALTGIRL", 14),
        ("OLD_RAPPER", 1), ("OLD_STREAMER", 9), ("OLD_STUDENT", 8), ("OLD_OFFICE", 4), ("OLD_COURIER", 5),
        ("OLD_BUSINESSMAN", 3), ("OLD_KAREN", 6), ("OLD_POPKING", 1),
        ("PROM_FOREMAN", 4), ("PROM_SAILOR", 3),
        ("HAMLET_MUZHIK", 1), ("HAMLET_HUNTER_GRANDPA", 1), ("POLICE_THIN", 2), ("POLICE_FAT", 2), ("FBI_AGENT", 1),
        ("ARMY_SOLDIER", 1), ("TRAMDURO", 1), ("VIP_BEASTMAN", 1), ("VIP_SPEEDSTER", 1), ("VIP_BLINDFOLD", 1)]
# The pool types opt_v01 left as they were (under its 15k budget): their input is Vadim's source revision, and step 0
# (opt_v01's hidden-face removal, same test and the same 17 poses, on the Body only: removing hidden Outfit faces
# changed the shading of HAMLET_BODYBUILDER's straps on the review renders) runs first.
SOURCE_HIDDEN = False   # source types get step 1 only: step 0 (Body/Outfit), 2 (head skin) and 4 (small parts) changed
                        # 6-3,000 px per type at 1.5 m on the renders (their meshes have no custom normals yet)
POOL_SOURCE = [("BEACH_CORN", 3), ("BEACH_CASTLE", 1), ("BEACH_SUNBURN", 2), ("BEACH_LIFEGUARD", 3), ("BEACH_DETECTOR", 3),
               ("BEACH_NUDIST", 1), ("BEACH_BURIED", 1), ("HAMLET_BODYBUILDER", 4), ("BAD_DRUNK", 4), ("OLD_FITNESS", 5)]
FREEZE = {'VIP_BEASTMAN': ('VIP_BEASTMAN_Logo',), 'CONSTR_INDIAN': ('CONSTR_INDIAN_Hair',)}   # as opt_v01 W86


def baseline(tid, rev):
    """(blend, fbx, kind) this type's opt_v02 starts from: its opt_v01, or Vadim's source when it has none."""
    if (tid, rev) in POOL_SOURCE:
        stem = TYPES_DIR / tid / f'SAUSAGE_BUDDY_{tid}_v{rev:02d}'
        return stem.with_suffix('.blend'), stem.with_suffix('.fbx'), 'source'
    stem = V01_DIR / f'SAUSAGE_BUDDY_{tid}_v{rev:02d}_{SRC_TAG}'
    return stem.with_suffix('.blend'), stem.with_suffix('.fbx'), SRC_TAG

RIG_CLIPS = ['Idle', 'Panic_Run_Loop', 'Panic_TurnFlee', 'DoubleTake_Flee', 'LookBack_Bonk', 'FakeSurrender_Flee', 'TripFall',
             'PlayDead_Fall', 'PlayDead_Loop', 'PlayDead_GetUp', 'Hide_Enter', 'Hide_Loop', 'PoliceCall']
STATE_STEP = 15             # frames between sampled states of a clip (and its last frame)
ISLAND_TOL = 0.001          # m, hard maximum for rigid small parts (~1 px at 1 m, 0.6 px at 1.5 m)
ISLAND_MIN_TRIS = 16
ISLAND_GAP_FRACTION = 0.45  # of the gap to a parallel surface within ISLAND_GAP_REACH
ISLAND_GAP_REACH = 0.003
ISLAND_MIN_TOL = 0.00015
ISLAND_NORMAL_DEG = 1.5     # max change of the interpolated shading normal of a collapsed part (custom normals restored)
RIGID_L1 = 0.02             # skin-weight difference (L1) under which a part counts as rigid
PART_DIAG = 0.15            # m; only rigid loose parts up to this size are collapsed
SKINNED_PART_DIAG = 0.0     # m; skinned loose parts up to this size too, checked in LOD_POSES (0 = none: kept out after
                            # the review renders, as are open parts (socks: 1 px change of the outline) and layered ones)
WEIGHT_STEP = 0.2           # skinned parts: edges between differently weighted vertices are locked (as opt_v01)
FACE_NORMAL_DEG = 1.0       # Face: a hidden face stays when removing it would turn a visible vertex's normal more
FACE_ZONE = {'z': (1.30, 1.665), 'y_max': -0.05, 'x_abs': 0.16}   # rest-pose box of facial parts in Outfit (not touched)
LOD = {1: {'ratio': 0.45, 'p99': 0.008, 'max': 0.016}, 2: {'ratio': 0.20, 'p99': 0.020, 'max': 0.043}}
OPEN_EDGE_FACTOR = 0.5      # open-edge (hem / hole border) vertices: this share of the level's max
HEM_LOCK_RINGS = {1: 2, 2: 0}   # LOD level: rings around garment hems kept uncollapsed (opt_v01 HEM_RINGS = 2)
GARMENT_AREA_PER_EDGE = 0.015   # m; a loose part with more area per metre of open edge is a garment (its edges are hems)
LOCK_AT = 0.8               # LOD0 vertices with error above this share of their limit are locked for the next round
LOD_OVER_SHARE = 0.002      # a LOD is within limits when at most this share of the vertices (or LOD_OVER_MIN) exceed
LOD_OVER_MIN = 3            # their limit, by at most LOD_OVER_FACTOR, and p99 holds
LOD_OVER_FACTOR = 1.5
LOD_WEIGHT_SEAM = 0.0       # LOD: vertices on edges whose skin weights differ more (L1) are locked (0 = off: it held
                            # whole hands; the posed limits lock the seams that matter)
LOD_NORMALS = 'source'      # LOD custom normals: 'source' (lod_shading) or 'auto' (computed)
LOD_ITER = 10               # lock rounds
LOD_TIGHTEN = 3             # then bisection steps of the ratio with the final locks
LOD_POSES = [(None, 0), ('Panic_Run_Loop', 5), ('Panic_Run_Loop', 12), ('TripFall', 30), ('FakeSurrender_Flee', 20),
             ('PlayDead_Loop', 1), ('Hide_Loop', 1), ('LookBack_Bonk', 20), ('Panic_TurnFlee', 60)]
FACE_KEY_STATES = [{}, {'Blink': 1.0}, {'Surprised': 1.0}, {'Worried': 1.0}, {'Happy': 1.0}, {'Blink': 1.0, 'Surprised': 1.0}]
VERBOSE = False


def tris_of(me):
    return B.tris_of(me)


def log(*a):
    print(*a, flush=True)


# ------------------------------------------------------------------ states (pose + face shape keys)
def face_keys(face):
    return face.data.shape_keys.key_blocks if face is not None and face.data.shape_keys else []


def sample_states(rig, face):
    """[(action or None, frame, {key: value})]: rest, every STATE_STEP frames of each body clip with the values of its
    *_Face track at that frame, and rest with each key at 1 and Blink + each expression."""
    scene = bpy.context.scene
    sk = face.data.shape_keys if face is not None else None
    states = [(None, 0, {})]
    for act in RIG_CLIPS:
        a = bpy.data.actions.get(act)
        if a is None:
            continue
        fa = bpy.data.actions.get(act + '_Face')
        s, e = (int(round(x)) for x in a.frame_range)
        for fr in sorted(set(list(range(s, e + 1, STATE_STEP)) + [e])):
            keys = {}
            if fa is not None and sk is not None:
                if sk.animation_data is None:
                    sk.animation_data_create()
                sk.animation_data.action = fa
                scene.frame_set(fr)
                keys = {k.name: round(k.value, 3) for k in sk.key_blocks[1:] if k.value > 1e-3}
            states.append((act, fr, keys))
    names = [k.name for k in face_keys(face)][1:]
    for n in names:
        states.append((None, 0, {n: 1.0}))
    for n in ('Surprised', 'Worried', 'Happy'):
        if n in names and 'Blink' in names:
            states.append((None, 0, {'Blink': 1.0, n: 1.0}))
    if sk is not None and sk.animation_data is not None:
        sk.animation_data.action = None
    return states


def apply_state(rig, face_objs, st):
    act, frame, keys = st
    B.set_pose(rig, act, frame)
    for f in face_objs:
        for k in face_keys(f):
            if k.name != 'Basis':
                k.value = keys.get(k.name, 0.0)


# ------------------------------------------------------------------ 1-2. hidden faces over the states
def hidden_over_states(rig, face_objs, states, cover, cand, subset):
    """Faces of cand (subset of indices) covered in every state; occluders = cover objects (evaluated, world space)."""
    dirs = B.sphere_dirs()
    left = set(subset)
    for st in states:
        if not left:
            break
        apply_state(rig, face_objs, st)
        dg = bpy.context.evaluated_depsgraph_get()
        verts, polys, base, faces = [], [], 0, None
        for o in cover:
            oe = o.evaluated_get(dg)
            me = oe.to_mesh()
            mw = o.matrix_world
            co = [mw @ v.co for v in me.vertices]
            vb = len(verts)
            if o == cand:
                base = len(polys)
                rot = mw.to_3x3()
                faces = [([co[i] for i in p.vertices], (rot @ p.normal).normalized()) for p in me.polygons]
            verts += co
            polys += [[vb + i for i in p.vertices] for p in me.polygons]
            oe.to_mesh_clear()
        bvh = BVHTree.FromPolygons(verts, polys)

        def blocked(origin, d, own):
            for _ in range(6):
                loc, _n, idx, _dist = bvh.ray_cast(origin, d, 3.0)
                if loc is None:
                    return False
                if idx != own:
                    return True
                origin = loc + d * 1e-5
            return False

        still = set()
        for fi in left:
            corners, n = faces[fi]
            if n.length < 0.5:
                continue
            c = sum(corners, Vector()) / len(corners)
            hemi = [d for d in dirs if d.dot(n) >= 0.05]
            pts = [c] + [c + (q - c) * 0.85 for q in corners]
            if all(blocked(p + n * 0.001, d, base + fi) for p in pts for d in hemi):
                still.add(fi)
        left = still
    apply_state(rig, face_objs, (None, 0, {}))
    return left


def tri_count(me, faces):
    return sum(len(me.polygons[i].vertices) - 2 for i in faces)


def mat_tris(me, faces=None):
    out = {}
    for p in (me.polygons if faces is None else (me.polygons[i] for i in faces)):
        n = me.materials[p.material_index].name
        out[n] = out.get(n, 0) + len(p.vertices) - 2
    return out


def normal_margin(ob, hidden):
    """Hidden faces that can go without changing the shading of the visible ones: a hidden face stays when removing it
    would turn the (angle-weighted, as Blender computes it) normal of a vertex of a visible face by more than
    FACE_NORMAL_DEG, in the basis, in any shape key at 1 or any two of them at 1. Returns (faces to remove, tris kept
    for the normals)."""
    me = ob.data
    polys = [tuple(p.vertices) for p in me.polygons]
    states = [np.array([v.co[:] for v in me.vertices])]
    if me.shape_keys:
        kb = me.shape_keys.key_blocks
        basis = np.array([d.co[:] for d in kb[0].data])
        deltas = [np.array([d.co[:] for d in k.data]) - basis for k in kb[1:]]
        states = [basis] + [basis + d for d in deltas] + [basis + deltas[i] + deltas[j] for i in range(len(deltas))
                                                        for j in range(i + 1, len(deltas))]

    def corner_data(co):
        out = []
        for pv in polys:
            pts = co[list(pv)]
            n = np.zeros(3)
            for i in range(len(pv)):
                n += np.cross(pts[i], pts[(i + 1) % len(pv)])
            ln = np.linalg.norm(n)
            n = n / ln if ln > 0 else n
            angs = []
            for i in range(len(pv)):
                a, b = pts[i - 1] - pts[i], pts[(i + 1) % len(pv)] - pts[i]
                la, lb = np.linalg.norm(a), np.linalg.norm(b)
                angs.append(math.acos(max(-1.0, min(1.0, float(np.dot(a, b) / (la * lb))))) if la > 0 and lb > 0 else 0.0)
            out.append((n, angs))
        return out

    cdata = [corner_data(co) for co in states]
    nv = len(me.vertices)

    def normals(cd, skip):
        acc = np.zeros((nv, 3))
        for fi, (pv, (n, angs)) in enumerate(zip(polys, cd)):
            if fi in skip:
                continue
            for v, a in zip(pv, angs):
                acc[v] += n * a
        ln = np.linalg.norm(acc, axis=1)
        ln[ln == 0] = 1.0
        return acc / ln[:, None]

    full = [normals(cd, set()) for cd in cdata]
    faces_of = [[] for _ in range(nv)]
    for fi, pv in enumerate(polys):
        for v in pv:
            faces_of[v].append(fi)
    remove = set(hidden)
    cos_lim = math.cos(math.radians(FACE_NORMAL_DEG))
    visible_v = {v for fi, pv in enumerate(polys) if fi not in hidden for v in pv}
    for _ in range(20):
        bad = set()
        for cd, ref in zip(cdata, full):
            cur = normals(cd, remove)
            for v in visible_v:
                if float(np.dot(cur[v], ref[v])) < cos_lim:
                    bad.add(v)
        back = {fi for v in bad for fi in faces_of[v] if fi in remove}
        if not back:
            break
        remove -= back
    kept = tri_count(me, set(hidden) - remove)
    return remove, kept


# ------------------------------------------------------------------ 3. clean-up
def cleanup(ob, measure_only=False):
    """Zero-area faces, duplicate faces (same vertex set) and loose vertices/edges: counted, and removed unless
    measure_only. LOD0 only measures: removing the zero-area slivers on bevels changes how the normals of their
    neighbours are shared (seen on the review renders: OLD_COURIER backpack, POLICE radio)."""
    me = ob.data
    bm = bmesh.new(); bm.from_mesh(me); bm.faces.ensure_lookup_table()
    zero = {f.index for f in bm.faces if f.calc_area() < 1e-10}
    seen, dup = {}, set()
    for f in bm.faces:
        key = frozenset(v.index for v in f.verts)
        if key in seen:
            dup.add(f.index)
        else:
            seen[key] = f.index
    loose_v = [v for v in bm.verts if not v.link_faces]
    loose_e = [e for e in bm.edges if not e.link_faces]
    bm.free()
    if measure_only:
        return {'zero_area_faces': len(zero), 'duplicate_faces': len(dup), 'faces_removed': 0,
                'loose_verts': len(loose_v), 'loose_edges': len(loose_e)}
    removed, kept = (0, [])
    if zero or dup:
        removed, kept = B.delete_faces(ob, zero | dup)
    if loose_v or loose_e:
        bm = bmesh.new(); bm.from_mesh(me)
        bmesh.ops.delete(bm, geom=[e for e in bm.edges if not e.link_faces], context='EDGES')
        bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context='VERTS')
        bm.to_mesh(me); bm.free(); me.update()
    return {'zero_area_faces': len(zero), 'duplicate_faces': len(dup), 'faces_removed': removed,
            'loose_verts': len(loose_v), 'loose_edges': len(loose_e)}


# ------------------------------------------------------------------ 4. rigid small parts
def islands_of(bm):
    seen, out = set(), []
    for f in bm.faces:
        if f.index in seen:
            continue
        st, isl = [f], []
        seen.add(f.index)
        while st:
            x = st.pop(); isl.append(x.index)
            for e in x.edges:
                for y in e.link_faces:
                    if y.index not in seen:
                        seen.add(y.index); st.append(y)
        out.append(isl)
    return out


def surface_samples(me):
    me.calc_loop_triangles()
    co = [v.co.copy() for v in me.vertices]
    tris = [tuple(t.vertices) for t in me.loop_triangles]
    pts = co + [(co[a] + co[b] + co[c]) / 3 for a, b, c in tris] + [(co[e.vertices[0]] + co[e.vertices[1]]) / 2 for e in me.edges]
    return pts, BVHTree.FromPolygons(co, tris), [t.normal.copy() for t in me.loop_triangles], [t.center.copy() for t in me.loop_triangles]


def hausdorff(a, b):
    pa, ba, _na, _ca = a
    pb, bb, nb, cb = b
    d1 = max((bb.find_nearest(p)[0] - p).length for p in pa)
    d2 = max((ba.find_nearest(p)[0] - p).length for p in pb)
    flipped = 0
    for n, c in zip(nb, cb):
        hit = ba.find_nearest(c)
        if hit[1] is not None and hit[1].dot(n) < 0.2:
            flipped += 1
    return max(d1, d2), flipped


def normal_field(me):
    """The shading of a mesh as rendered: BVH of its loop triangles with their corner normals (custom or computed)."""
    me.calc_loop_triangles()
    cn = me.corner_normals
    co = [v.co.copy() for v in me.vertices]
    lts = list(me.loop_triangles)
    tri_n = [tuple(cn[li].vector.copy() for li in t.loops) for t in lts]
    return (BVHTree.FromPolygons(co, [tuple(t.vertices) for t in lts]), co, [tuple(t.vertices) for t in lts], tri_n,
            [t.normal.copy() for t in lts])


def field_at(field, p, facing):
    """Interpolated normal of the field at its surface point nearest to p (of the triangles facing like facing)."""
    bvh, co, tris, tri_n, fn = field
    hits = bvh.find_nearest_range(p, 0.002)
    if not hits:
        h = bvh.find_nearest(p)
        hits = [h] if h[0] is not None else []
    if not hits:
        return None
    dmin = min(h[3] for h in hits)
    near = [h for h in hits if h[3] <= dmin + 0.0002]
    loc, _n, idx, _d = max(near, key=lambda h: fn[h[2]].dot(facing))
    if fn[idx].dot(facing) < 0.5:
        return None
    a, b, c = tris[idx]
    w = barycentric_transform(loc, co[a], co[b], co[c], Vector((1, 0, 0)), Vector((0, 1, 0)), Vector((0, 0, 1)))
    n0, n1, n2 = tri_n[idx]
    return (n0 * w.x + n1 * w.y + n2 * w.z).normalized()


def shading_change_deg(ref_field, me):
    """Largest angle between the shading a collapsed part will get (corner normals = the reference shading at each
    corner, as keep_shading sets them, interpolated across its triangles) and the reference shading, sampled at the
    centre and edge midpoints of every triangle."""
    me.calc_loop_triangles()
    co = [v.co for v in me.vertices]
    worst = 0.0
    for t in me.loop_triangles:
        fn = t.normal
        corners = [field_at(ref_field, co[i], fn) for i in t.vertices]
        if any(c is None for c in corners):
            continue
        a, b, c = (co[i] for i in t.vertices)
        for wa, wb, wc in ((1 / 3, 1 / 3, 1 / 3), (0.5, 0.5, 0.0), (0.0, 0.5, 0.5), (0.5, 0.0, 0.5)):
            p = a * wa + b * wb + c * wc
            ref = field_at(ref_field, p, fn)
            if ref is None:
                continue
            n = (corners[0] * wa + corners[1] * wb + corners[2] * wc).normalized()
            worst = max(worst, math.degrees(n.angle(ref, 0.0)))
    return worst


def world_owner_bvh(objs):
    """Rest-pose BVH of every mesh with an owner tag (object name, island id) per triangle, for the gap rule."""
    verts, tris, owner, normals = [], [], [], []
    for o in objs:
        me = o.data
        me.calc_loop_triangles()
        bm = bmesh.new(); bm.from_mesh(me); bm.faces.ensure_lookup_table()
        isl_of = {}
        for k, isl in enumerate(islands_of(bm)):
            for fi in isl:
                isl_of[fi] = k
        bm.free()
        mw = o.matrix_world
        vb = len(verts)
        verts += [mw @ v.co for v in me.vertices]
        rot = mw.to_3x3()
        for t in me.loop_triangles:
            tris.append(tuple(vb + i for i in t.vertices))
            owner.append((o.name, isl_of.get(t.polygon_index, -1)))
            normals.append((rot @ t.normal).normalized())
    return BVHTree.FromPolygons(verts, tris), owner, normals


def island_tolerance(ob, isl_id, vco, vno, world):
    """ISLAND_TOL, cut to ISLAND_GAP_FRACTION of the gap to a roughly parallel surface of another part nearby."""
    bvh, owner, normals = world
    mw = ob.matrix_world
    rot = mw.to_3x3()
    gaps = []
    for p, n in zip(vco, vno):
        pw = mw @ p
        nw = (rot @ n).normalized()
        best = None
        for loc, _n, idx, dist in bvh.find_nearest_range(pw, ISLAND_GAP_REACH):
            if owner[idx] == (ob.name, isl_id) or abs(normals[idx].dot(nw)) < 0.7:
                continue
            best = dist if best is None else min(best, dist)
        if best is not None:
            gaps.append(best)
    if len(gaps) < max(3, 0.05 * len(vco)):
        return ISLAND_TOL, None
    gap = float(np.percentile(gaps, 10))
    return max(ISLAND_MIN_TOL, min(ISLAND_TOL, ISLAND_GAP_FRACTION * gap)), gap


def in_face_zone(ob, vco):
    c = ob.matrix_world @ (sum(vco, Vector()) / len(vco))
    return FACE_ZONE['z'][0] < c.z < FACE_ZONE['z'][1] and c.y < FACE_ZONE['y_max'] and abs(c.x) < FACE_ZONE['x_abs']


def weight_step_verts(me, dl_get, step=None):
    """Vertices on edges whose skin weights differ by more than step (L1; default WEIGHT_STEP, as opt_v01)."""
    step = WEIGHT_STEP if step is None else step
    out = set()
    for e in me.edges:
        a, b = dl_get(e.vertices[0]), dl_get(e.vertices[1])
        if sum(abs(a.get(k, 0.0) - b.get(k, 0.0)) for k in a.keys() | b.keys()) > step:
            out.update(e.vertices)
    return out


def decimate_island(ob, isl, tol, rig, poses=()):
    """Lowest collapse ratio of one loose part (a temporary copy holding only it) whose surface stays within tol of
    the part at rest and, for a skinned part, in every pose of poses, with no triangle turned over. Open edges, material
    borders and (skinned parts) skin-weight steps are locked. Returns (mesh of the collapsed part at rest, tris before,
    tris after, ratio, deviation) or None."""
    B.set_pose(rig, None, 0)
    tmp = ob.copy()
    tmp.data = ob.data.copy()
    tmp.name = ob.name + '_ISL'
    bpy.context.scene.collection.objects.link(tmp)
    for m in list(tmp.modifiers):
        if m.type != 'ARMATURE' or not poses:
            tmp.modifiers.remove(m)
    arm = [m for m in tmp.modifiers if m.type == 'ARMATURE']
    bm = bmesh.new(); bm.from_mesh(tmp.data); bm.faces.ensure_lookup_table()
    keep = set(isl)
    bmesh.ops.delete(bm, geom=[f for f in bm.faces if f.index not in keep], context='FACES')
    lock = {v.index for e in bm.edges if len(e.link_faces) != 2 or e.link_faces[0].material_index != e.link_faces[1].material_index
            for v in e.verts}
    bm.to_mesh(tmp.data); bm.free(); tmp.data.update()
    if poses:
        names = [g.name for g in tmp.vertex_groups]
        w = [{names[g.group]: g.weight for g in v.groups if g.weight > 1e-4} for v in tmp.data.vertices]
        lock |= weight_step_verts(tmp.data, lambda i: w[i])
    tri0 = tris_of(tmp.data)
    shade_ref = normal_field(tmp.data)
    g = tmp.vertex_groups.new(name='OPT2_LOCK')
    if lock:
        g.add(sorted(lock), 1.0, 'REPLACE')
    mod = tmp.modifiers.new('OPT2_Decimate', 'DECIMATE')
    mod.decimate_type = 'COLLAPSE'; mod.use_collapse_triangulate = False
    mod.vertex_group = g.name; mod.invert_vertex_group = True
    if arm:
        with bpy.context.temp_override(object=tmp, active_object=tmp):
            bpy.ops.object.modifier_move_to_index(modifier=mod.name, index=0)
    states = [(None, 0)] + list(poses)

    def snaps(on):
        mod.show_viewport = on
        out = []
        for k, (a, f) in enumerate(states):
            B.set_pose(rig, a, f)
            dg = bpy.context.evaluated_depsgraph_get()
            te = tmp.evaluated_get(dg)
            me = te.to_mesh()
            out.append((surface_samples(me), tris_of(me), shading_change_deg(shade_ref, me) if on and k == 0 else 0.0))
            te.to_mesh_clear()
        return out

    ref = [x[0] for x in snaps(False)]
    lo, hi, best = 0.05, 1.0, None
    for _ in range(7):
        mid = (lo + hi) / 2
        mod.ratio = mid
        trial = snaps(True)
        shade = trial[0][2]
        d, flipped = 0.0, 0
        for k, ((smp, _t, _s), r) in enumerate(zip(trial, ref)):
            dk, fk = hausdorff(r, smp)
            d = max(d, dk)
            if k == 0:
                flipped = fk
            if d > tol:
                break
        if d <= tol and flipped == 0 and shade <= ISLAND_NORMAL_DEG:
            hi, best = mid, (mid, trial[0][1], d, shade)
        else:
            lo = mid
    B.set_pose(rig, None, 0)
    result = None
    if best is not None and best[1] < tri0:
        mod.ratio = best[0]
        mod.show_viewport = True
        for m in arm:
            m.show_viewport = False
        dg = bpy.context.evaluated_depsgraph_get()
        result = (bpy.data.meshes.new_from_object(tmp.evaluated_get(dg), preserve_all_data_layers=True, depsgraph=dg),
                  tri0, best[1], best[0], best[2], best[3])
    me_tmp = tmp.data
    bpy.data.objects.remove(tmp)
    bpy.data.meshes.remove(me_tmp)
    return result


def rigid_parts(ob, tid, all_objs, rig):
    """Step 4 on one object. Returns the report entry."""
    me = ob.data
    freeze = FREEZE.get(tid, ())
    world = world_owner_bvh(all_objs)
    bm = bmesh.new(); bm.from_mesh(me); bm.verts.ensure_lookup_table(); bm.faces.ensure_lookup_table()
    dl = bm.verts.layers.deform.active
    isl_list = islands_of(bm)
    vnorm = [v.normal.copy() for v in me.vertices]
    jobs, skipped = [], {'small': 0, 'frozen': 0, 'skinned': 0, 'large': 0, 'open': 0, 'face_zone': 0, 'layered': 0}
    for k, isl in enumerate(isl_list):
        fs = [bm.faces[i] for i in isl]
        tri0 = sum(len(f.verts) - 2 for f in fs)
        if tri0 < ISLAND_MIN_TRIS:
            skipped['small'] += tri0; continue
        if any(me.materials[f.material_index].name.startswith(freeze) for f in fs) if freeze else False:
            skipped['frozen'] += tri0; continue
        vs = sorted({v.index for f in fs for v in f.verts})
        vco = [bm.verts[i].co.copy() for i in vs]
        rigid = True
        if dl is not None:
            ws = [{g: w for g, w in bm.verts[i][dl].items() if w > 1e-4} for i in vs]
            rigid = all(sum(abs(a.get(g, 0.0) - ws[0].get(g, 0.0)) for g in a.keys() | ws[0].keys()) < RIGID_L1 for a in ws)
        lo = Vector((min(c.x for c in vco), min(c.y for c in vco), min(c.z for c in vco)))
        hi = Vector((max(c.x for c in vco), max(c.y for c in vco), max(c.z for c in vco)))
        if (hi - lo).length > (PART_DIAG if rigid else SKINNED_PART_DIAG):
            skipped['skinned' if not rigid else 'large'] += tri0; continue
        if any(len(e.link_faces) == 1 for f in fs for e in f.edges):
            skipped['open'] += tri0; continue
        if in_face_zone(ob, vco):
            skipped['face_zone'] += tri0; continue
        tol, gap = island_tolerance(ob, k, vco, [vnorm[i] for i in vs], world)
        if gap is not None:
            skipped['layered'] += tri0; continue
        jobs.append((k, isl, tol, gap, rigid))
    bm.free()
    done = []
    poses = [(a, f) for a, f in LOD_POSES if a is not None and a in bpy.data.actions]
    for k, isl, tol, gap, rigid in jobs:
        r = decimate_island(ob, isl, tol, rig, () if rigid else poses)
        if r is not None:
            done.append((k, isl, tol, gap, r, rigid))
    per_mat = {}
    if done:
        n_groups = len(ob.vertex_groups)
        bm = bmesh.new(); bm.from_mesh(me); bm.faces.ensure_lookup_table()
        gone = {fi for x in done for fi in x[1]}
        mats_before = mat_tris(me)
        bmesh.ops.delete(bm, geom=[bm.faces[i] for i in sorted(gone)], context='FACES')
        for _k, isl, tol, gap, (m_new, t0, t1, ratio, dev, shade), _rigid in done:
            bm.from_mesh(m_new)          # appends the collapsed part (same material list and vertex-group order)
            bpy.data.meshes.remove(m_new)
        dl = bm.verts.layers.deform.active
        if dl is not None:
            for v in bm.verts:
                dv = v[dl]
                for gi in [g for g in dv.keys() if g >= n_groups]:
                    del dv[gi]           # the temporary lock group
        bm.to_mesh(me); bm.free(); me.update()
        mats_after = mat_tris(me)
        for n in mats_before:
            if mats_after.get(n, 0) != mats_before[n]:
                per_mat[n] = [mats_before[n], mats_after.get(n, 0)]
    tols = [round(x[2] * 1000, 2) for x in done]
    return {'parts': len(isl_list), 'candidates': len(jobs), 'collapsed': len(done),
            'collapsed_skinned': sum(1 for x in done if not x[5]),
            'tris_saved': sum(x[4][1] - x[4][2] for x in done),
            'tris_saved_skinned': sum(x[4][1] - x[4][2] for x in done if not x[5]),
            'max_dev_mm': round(max([x[4][4] for x in done], default=0.0) * 1000, 3),
            'max_shading_deg': round(max([x[4][5] for x in done], default=0.0), 2),
            'gap_limited_parts': sum(1 for x in done if x[3] is not None),
            'min_tol_mm': min(tols) if tols else None, 'materials': per_mat, 'skipped_tris': skipped}


# ------------------------------------------------------------------ 5. shading
def keep_shading(ob, source, reach=0.004):
    """opt_v01 keep_shading with a configurable reach: custom corner normals = the source mesh's normal at the nearest
    point of its surface of the same material that faces the same way."""
    source.calc_loop_triangles()
    vn = [v.normal.copy() for v in source.vertices]
    co = [v.co.copy() for v in source.vertices]
    by_mat = {}
    for lt in source.loop_triangles:
        by_mat.setdefault(source.polygons[lt.polygon_index].material_index, []).append(lt)
    trees = {m: (BVHTree.FromPolygons(co, [lt.vertices for lt in lts]), lts) for m, lts in by_mat.items()}
    me = ob.data
    out = [c.vector.copy() for c in me.corner_normals]
    kept = 0
    for p in me.polygons:
        tree = trees.get(p.material_index)
        if tree is None:
            continue
        bvh, lts = tree
        pn = p.normal
        for li in p.loop_indices:
            pos = me.vertices[me.loops[li].vertex_index].co
            hits = bvh.find_nearest_range(pos, reach)
            if not hits:
                hit = bvh.find_nearest(pos)
                hits = [hit] if hit[0] is not None else []
                if not hits or hits[0][3] > reach * 2:
                    continue
            dmin = min(h[3] for h in hits)
            near = [h for h in hits if h[3] <= dmin + 0.00005 + 0.1 * dmin]
            loc, hn, idx, _d = max(near, key=lambda h: h[1].dot(pn))
            if hn.dot(pn) < 0.3:
                continue
            out[li] = B.smooth_normal_at(source, vn, lts[idx], loc)
            kept += 1
    me.normals_split_custom_set(out)
    return {'corners': len(out), 'from_source': kept}


def lod_shading(ob, source, reach):
    """LOD normals: per vertex and material, the source surface normal at the nearest point of that material facing
    like the LOD vertex's own normal (dot >= 0.6), so every corner of a vertex gets the same normal (no seams) and a hem
    rim or an inner layer next to the outer surface is never taken; otherwise the computed normal stays."""
    source.calc_loop_triangles()
    vn = [v.normal.copy() for v in source.vertices]
    co = [v.co.copy() for v in source.vertices]
    by_mat = {}
    for lt in source.loop_triangles:
        by_mat.setdefault(source.polygons[lt.polygon_index].material_index, []).append(lt)
    trees = {m: (BVHTree.FromPolygons(co, [lt.vertices for lt in lts]), lts) for m, lts in by_mat.items()}
    me = ob.data
    own = [v.normal.copy() for v in me.vertices]
    out = [c.vector.copy() for c in me.corner_normals]
    cache, kept = {}, 0
    for p in me.polygons:
        tree = trees.get(p.material_index)
        if tree is None:
            continue
        bvh, lts = tree
        for li in p.loop_indices:
            vi = me.loops[li].vertex_index
            key = (vi, p.material_index, p.use_smooth)
            if key not in cache:
                ref = own[vi] if p.use_smooth else p.normal
                hits = [h for h in bvh.find_nearest_range(me.vertices[vi].co, reach) if h[1].dot(ref) >= 0.6]
                if hits:
                    loc, _hn, idx, _d = min(hits, key=lambda h: h[3])
                    cache[key] = B.smooth_normal_at(source, vn, lts[idx], loc)
                else:
                    cache[key] = None
            if cache[key] is not None:
                out[li] = cache[key]
                kept += 1
    me.normals_split_custom_set(out)
    return {'corners': len(out), 'from_source': kept}


# ------------------------------------------------------------------ LOD chain
def snap_world(o):
    dg = bpy.context.evaluated_depsgraph_get()
    oe = o.evaluated_get(dg)
    me = oe.to_mesh()
    me.calc_loop_triangles()
    co = [o.matrix_world @ v.co for v in me.vertices]
    by = {}
    for t in me.loop_triangles:
        by.setdefault(me.polygons[t.polygon_index].material_index, []).append(tuple(t.vertices))
    oe.to_mesh_clear()
    return co, by


def lod_errors(ref, new, nv_ref, nv_new):
    """Per LOD0 vertex: max distance of it and of its triangles' centres to the LOD surface of the same material;
    per LOD vertex: distance to the LOD0 surface of the same material. A material the LOD lost counts 1 m."""
    (ca, ba), (cb, bb) = ref, new
    ea, eb = np.zeros(nv_ref), np.zeros(nv_new)
    for m, ta in ba.items():
        tb = bb.get(m)
        if not tb:
            for t in ta:
                for i in t:
                    ea[i] = 1.0
            continue
        tree_a, tree_b = BVHTree.FromPolygons(ca, ta), BVHTree.FromPolygons(cb, tb)
        for i in {i for t in ta for i in t}:
            ea[i] = max(ea[i], (tree_b.find_nearest(ca[i])[0] - ca[i]).length)
        for t in ta:
            c = (ca[t[0]] + ca[t[1]] + ca[t[2]]) / 3
            d = (tree_b.find_nearest(c)[0] - c).length
            for i in t:
                if d > ea[i]:
                    ea[i] = d
        for i in {i for t in tb for i in t}:
            eb[i] = max(eb[i], (tree_a.find_nearest(cb[i])[0] - cb[i]).length)
    return ea, eb


def decimated_copy(src, ratio, locked, name):
    c = src.copy()
    c.data = src.data.copy()
    c.name = name
    c.data.name = name
    bpy.context.scene.collection.objects.link(c)
    if c.data.shape_keys:
        c.active_shape_key_index = 0
    g = c.vertex_groups.new(name='OPT2_LOD_LOCK')
    if locked:
        g.add(sorted(locked), 1.0, 'REPLACE')
    for x in bpy.context.view_layer.objects:
        x.select_set(False)
    bpy.context.view_layer.objects.active = c
    c.select_set(True)
    c.vertex_groups.active_index = g.index
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.decimate(ratio=ratio, use_vertex_group=True, vertex_group_factor=1.0, invert_vertex_group=True)
    bpy.ops.object.mode_set(mode='OBJECT')
    c.vertex_groups.remove(c.vertex_groups['OPT2_LOD_LOCK'])
    return c


def real_hems(ob, source):
    """Vertices of ob on an open edge of Vadim's source mesh that belongs to a garment (hems, cuffs, collars, sock
    tops, hairlines), as opposed to the borders of the hidden-face holes opt_v01 cut and to the outlines of decals,
    stripes, straps and trims (loose parts whose area / open-edge length is under GARMENT_AREA_PER_EDGE)."""
    if source is None:
        return set()
    sb = bmesh.new(); sb.from_mesh(source); sb.faces.ensure_lookup_table()
    garment_faces = set()
    for isl in islands_of(sb):
        fs = [sb.faces[i] for i in isl]
        area = sum(f.calc_area() for f in fs)
        edges = {e for f in fs for e in f.edges if len(e.link_faces) == 1}
        border = sum(e.calc_length() for e in edges)
        if border > 0 and area / border >= GARMENT_AREA_PER_EDGE:
            garment_faces.update(isl)
    sb.free()
    bm = bmesh.new(); bm.from_mesh(source)
    segs = [(e.verts[0].co.copy(), e.verts[1].co.copy()) for e in bm.edges
            if len(e.link_faces) == 1 and e.link_faces[0].index in garment_faces]
    bm.free()
    if not segs:
        return set()
    kd = kdtree.KDTree(len(segs) * 3)
    k = 0
    for a, b in segs:
        for p in (a, b, (a + b) / 2):
            kd.insert(p, k); k += 1
    kd.balance()
    bm = bmesh.new(); bm.from_mesh(ob.data)
    out = set()
    for e in bm.edges:
        if len(e.link_faces) != 1:
            continue
        for v in e.verts:
            if kd.find(v.co)[2] <= 0.0008:
                out.add(v.index)
    bm.free()
    return out


def make_lod(rig, src, level, face_objs, hems=frozenset()):
    """Iterative-lock collapse of src to LOD[level]; returns (object, report)."""
    cfg = LOD[level]
    is_face = src.data.shape_keys is not None
    states = [(None, 0, k) for k in FACE_KEY_STATES] if is_face else [(a, f, {}) for a, f in LOD_POSES
                                                                         if a is None or a in bpy.data.actions]
    refs = []
    for st in states:
        apply_state(rig, face_objs, st)
        refs.append(snap_world(src))
    nv = len(src.data.vertices)
    kd = kdtree.KDTree(nv)
    for i, v in enumerate(src.data.vertices):
        kd.insert(v.co, i)
    kd.balance()
    bm = bmesh.new(); bm.from_mesh(src.data); bm.verts.ensure_lookup_table()
    nbr = [[e.other_vert(v).index for e in v.link_edges] for v in bm.verts]
    open_v = {v.index for e in bm.edges if len(e.link_faces) == 1 for v in e.verts}
    bm.free()
    src.data.calc_loop_triangles()
    tri_verts = [tuple(t.vertices) for t in src.data.loop_triangles]
    limit = np.full(nv, cfg['max'])
    for i in open_v:
        limit[i] = cfg['max'] * OPEN_EDGE_FACTOR
    name = f'{src.name}_LOD{level}'
    history = []
    best = None     # (ok, tris, object, (p99, max), over)

    # rest surface of LOD0 per material (object space), for stray vertices
    rest_co = [v.co.copy() for v in src.data.vertices]
    by_mat = {}
    for t in src.data.loop_triangles:
        by_mat.setdefault(src.data.polygons[t.polygon_index].material_index, []).append(tuple(t.vertices))
    rest_trees = {m: BVHTree.FromPolygons(rest_co, ts) for m, ts in by_mat.items()}
    strays = [0]

    def snap_strays(c):
        """A collapse can slide a vertex far along a straight run (no quadric error) into another material's area:
        such a vertex goes back onto the nearest LOD0 surface of its own materials."""
        me = c.data
        mats_of = [set() for _ in me.vertices]
        for p in me.polygons:
            for i in p.vertices:
                mats_of[i].add(p.material_index)
        moved = 0
        for v, ms in zip(me.vertices, mats_of):
            best = None
            for m in ms:
                tree = rest_trees.get(m)
                if tree is None:
                    continue
                hit = tree.find_nearest(v.co)
                if hit[0] is not None and (best is None or hit[3] < best[3]):
                    best = hit
            if best is not None and best[3] > cfg['max'] * OPEN_EDGE_FACTOR:
                delta = best[0] - v.co
                v.co = best[0]
                if me.shape_keys:
                    for k in me.shape_keys.key_blocks:
                        k.data[v.index].co += delta
                moved += 1
        if moved:
            me.update()
        strays[0] = max(strays[0], moved)

    def trial(ratio, locked):
        c = decimated_copy(src, ratio, locked, name + '_TRY')
        snap_strays(c)
        worst = np.zeros(nv)
        p99 = mx = 0.0
        for st, ref in zip(states, refs):
            apply_state(rig, face_objs + ([c] if is_face else []), st)
            new = snap_world(c)
            ea, eb = lod_errors(ref, new, nv, len(c.data.vertices))
            worst = np.maximum(worst, ea)
            for j in np.nonzero(eb > cfg['max'] * LOCK_AT * OPEN_EDGE_FACTOR)[0]:
                _co, i, _d = kd.find(c.data.vertices[int(j)].co)
                worst[i] = max(worst[i], eb[j])
            p99 = max(p99, float(np.percentile(ea, 99)), float(np.percentile(eb, 99)))
            mx = max(mx, float(ea.max()), float(eb.max()))
        over = worst > limit
        tris = tris_of(c.data)
        # a few vertices (thin tips, strands) may exceed the limit by up to half of it
        n_over = int(over.sum())
        ok = p99 <= cfg['p99'] and (n_over == 0 or (n_over <= max(LOD_OVER_MIN, LOD_OVER_SHARE * nv)
                                                     and float((worst / limit).max()) <= LOD_OVER_FACTOR))
        history.append({'ratio': round(ratio, 3), 'locked': len(locked), 'tris': tris, 'p99_mm': round(p99 * 1000, 2),
                        'max_mm': round(mx * 1000, 2), 'over_limit_verts': int(over.sum()), 'ok': ok})
        if VERBOSE:
            log(f'      {name}', history[-1])
        return ok, tris, c, (p99, mx), int(over.sum()), worst

    def keep(res):
        nonlocal best
        ok, tris, c, dev, n_over, _w = res
        better = best is None or (ok and not best[0]) or (ok == best[0] and (tris < best[1] if ok else n_over < best[4]))
        if better:
            if best is not None:
                old = best[2].data
                bpy.data.objects.remove(best[2]); bpy.data.meshes.remove(old)
            best = (ok, tris, c, dev, n_over)
        else:
            old = c.data
            bpy.data.objects.remove(c); bpy.data.meshes.remove(old)

    # hems: open edges (garment hems, hole borders of the hidden-face removal) and HEM_LOCK_RINGS rings stay as in LOD0:
    # collapsing a rolled hem into the outer surface tilts it (dark bands) and can open a view into the garment
    locked = set(hems)
    for _ in range(HEM_LOCK_RINGS[level]):
        locked |= {j for i in locked for j in nbr[i]}
    hem_locked = len(locked)
    # sharp skin-weight seams (straps, ropes, parts on another bone): a collapse across them blends far-apart bones
    names = [g.name for g in src.vertex_groups]
    wts = [{names[g.group]: g.weight for g in v.groups if g.weight > 1e-4} for v in src.data.vertices]
    seams = weight_step_verts(src.data, lambda i: wts[i], LOD_WEIGHT_SEAM) if LOD_WEIGHT_SEAM else set()
    locked |= seams
    # every material keeps a face: the vertices of its largest polygon are locked
    biggest = {}
    for p in src.data.polygons:
        if p.material_index not in biggest or p.area > biggest[p.material_index].area:
            biggest[p.material_index] = p
    locked |= {i for p in biggest.values() for i in p.vertices}
    held = sum(1 for t in tri_verts if any(i in locked for i in t)) / max(1, len(tri_verts))
    base_ratio = cfg['ratio']
    ratio = min(1.0, base_ratio + (1.0 - base_ratio) * held) if locked else base_ratio
    ok_ratio = None
    for _it in range(LOD_ITER):
        res = trial(ratio, locked)
        worst = res[5]
        keep(res)
        if res[0]:
            ok_ratio = ratio
            break
        bad = set(np.nonzero(worst > limit * LOCK_AT)[0].tolist())
        if res[3][0] > cfg['p99']:          # p99 over: lock everything above the p99 limit as well
            bad |= set(np.nonzero(worst > cfg['p99'])[0].tolist())
        grow = set(bad)
        for i in bad:
            grow.update(nbr[i])
        if grow <= locked:
            base_ratio = min(1.0, base_ratio * 1.2)
        locked |= grow
        # the triangles around locked vertices stay: the rest is still collapsed to base_ratio (no cascade)
        held = sum(1 for t in tri_verts if any(i in locked for i in t)) / max(1, len(tri_verts))
        ratio = min(1.0, base_ratio + (1.0 - base_ratio) * held)
    if ok_ratio is not None and ok_ratio > cfg['ratio'] * 1.02 and HEM_LOCK_RINGS[level] >= 0:
        # with the final locks, collapse the free part further while every limit still holds
        lo, hi = cfg['ratio'], ok_ratio
        for _ in range(LOD_TIGHTEN):
            mid = (lo + hi) / 2
            res = trial(mid, locked)
            keep(res)
            if res[0]:
                hi = mid
            else:
                lo = mid
    apply_state(rig, face_objs, (None, 0, {}))
    ok, tris, c, (p99, mx), n_over = best
    c.name = name
    c.data.name = name
    return c, {'tris': tris, 'ok': ok, 'p99_mm': round(p99 * 1000, 2), 'max_mm': round(mx * 1000, 2), 'over_limit_verts': n_over,
               'locked_verts': len(locked), 'hem_locked_verts': hem_locked, 'seam_locked_verts': len(seams),
               'stray_verts_snapped_max': strays[0], 'rounds': len(history), 'history': history}


# ------------------------------------------------------------------ per type
def load_source_meshes(tid, rev, names):
    """Vadim's source meshes of these objects (shading reference), appended under temporary names."""
    src = TYPES_DIR / tid / f'SAUSAGE_BUDDY_{tid}_v{rev:02d}.blend'
    with bpy.data.libraries.load(str(src), link=False) as (df, dt):
        dt.objects = [n for n in names if n in df.objects]
    out = {}
    for o in dt.objects:
        if o is None:
            continue
        base = o.name.rsplit('.', 1)[0]
        out[base] = o.data
        o.data.name = 'OPT2_SRC_' + base
        bpy.data.objects.remove(o)
    return out


def bone_set(rig):
    return {b.name for b in rig.data.bones}


def check(rig, objs, bones0, mats0):
    problems = []
    if bone_set(rig) != set(bones0) or any(
            max(abs(x - y) for r1, r2 in zip(b.matrix_local, bones0[b.name]) for x, y in zip(r1, r2)) > 1e-7 for b in rig.data.bones):
        problems.append('rig changed')
    deform = {b.name for b in rig.data.bones if b.use_deform}
    for o in objs:
        base = o.name.split('_LOD')[0]
        if [m.name for m in o.data.materials] != mats0[base][0]:
            problems.append(f'{o.name}: material slots differ')
        used = {p.material_index for p in o.data.polygons}
        if used != mats0[base][1]:
            problems.append(f'{o.name}: used materials differ {sorted(used ^ mats0[base][1])}')
        names = [g.name for g in o.vertex_groups]
        infl = [len([g for g in v.groups if g.weight > 1e-4 and names[g.group] in deform]) for v in o.data.vertices]
        if infl and (min(infl) == 0 or max(infl) > 4):
            problems.append(f'{o.name}: weights min {min(infl)} max {max(infl)}')
    return problems


def optimise(tid, rev, out_dir):
    src, _fbx, kind = baseline(tid, rev)
    stem = f'SAUSAGE_BUDDY_{tid}_v{rev:02d}_{TAG}'
    out = {'blend': out_dir / (stem + '.blend'), 'fbx': out_dir / (stem + '.fbx')}
    for p in out.values():
        if p.exists():
            sys.exit(f'Refusing to overwrite {p}')
    t_start = time.time()
    bpy.ops.wm.open_mainfile(filepath=str(src))
    scene = bpy.context.scene
    rig = bpy.data.objects[RIG]
    objs = sorted((o for o in bpy.data.objects if o.type == 'MESH' and o.parent == rig), key=lambda o: o.name)
    by = {o.name: o for o in objs}
    face, body, outfit = by.get('Face'), by.get('Body'), by.get('Outfit')
    rep = {'type': tid, 'revision': rev, 'baseline': kind,
           'input': f'{src.parent.name}/{src.name}' if kind == SRC_TAG else f'Types/{tid}/{src.name}',
           'tris_v01': {o.name: tris_of(o.data) for o in objs}}
    rep['total_v01'] = sum(rep['tris_v01'].values())
    bones0 = {b.name: b.matrix_local.copy() for b in rig.data.bones}
    actions0 = {a.name for a in bpy.data.actions}
    mats0 = {o.name: ([m.name for m in o.data.materials], {p.material_index for p in o.data.polygons}) for o in objs}
    keys0 = {o.name: [k.name for k in o.data.shape_keys.key_blocks] if o.data.shape_keys else [] for o in objs}
    sk = face.data.shape_keys if face is not None else None
    keep_face_action = sk.animation_data.action if sk is not None and sk.animation_data else None
    keep_rig = (rig.animation_data.action, scene.frame_current, rig.data.pose_position)
    face_objs = [face] if face is not None else []
    steps = {}

    # 0. (source types) opt_v01's hidden faces of Body and Outfit: covered by Body + Outfit in each of its 17 poses
    t = time.time()
    src_copies = {}
    if kind == 'source':
        # the open file is the source: its untouched meshes are the shading reference
        src_copies = {o.name: o.data.copy() for o in objs if o.name != 'Face'}
        for n, m in src_copies.items():
            m.name = 'OPT2_SRC_' + n
    if kind == 'source' and SOURCE_HIDDEN:
        cover0 = [o for o in (body, outfit) if o is not None]
        st0 = [(a, f, {}) for a, f in B.POSES if a is None or a in bpy.data.actions]
        cand0 = [o for o in (body,) if o is not None]      # Body only: Outfit cuts changed the strap shading (renders)
        hid0 = {o.name: hidden_over_states(rig, face_objs, st0, cover0, o, range(len(o.data.polygons))) for o in cand0}
        steps['0_hidden_body_outfit'] = {}
        for o in cand0:
            before = tris_of(o.data)
            n, kept = B.delete_faces(o, hid0[o.name])
            steps['0_hidden_body_outfit'][o.name] = {'tris': before - tris_of(o.data), 'faces': n, 'materials_kept_whole': kept}
        rep['seconds_hidden_body_outfit'] = round(time.time() - t, 1)

    # 1-2. hidden faces over all states
    t = time.time()
    states = sample_states(rig, face)
    rep['states'] = len(states)
    cover = [o for o in (body, face, outfit) if o is not None]
    if face is not None:
        hid = hidden_over_states(rig, face_objs, states, cover, face, range(len(face.data.polygons)))
        n_hidden = tri_count(face.data, hid)
        hid, normal_kept = normal_margin(face, hid)
        before = tris_of(face.data)
        mats = mat_tris(face.data, hid)
        n, kept = B.delete_faces(face, hid)
        steps['1_face_interior'] = {'tris': before - tris_of(face.data), 'faces': n, 'hidden_tris': n_hidden,
                                    'kept_for_normals_tris': normal_kept, 'materials': mats, 'materials_kept_whole': kept}
    if body is not None and face is not None and (kind != 'source' or SOURCE_HIDDEN):
        names = [g.name for g in body.vertex_groups]
        head = names.index('mixamorig:Head') if 'mixamorig:Head' in names else -1
        rigid_head = {v.index for v in body.data.vertices if any(g.group == head and g.weight >= 0.999 for g in v.groups)}
        cand = [p.index for p in body.data.polygons if all(i in rigid_head for i in p.vertices)]
        hid = hidden_over_states(rig, face_objs, states, cover, body, cand)
        before = tris_of(body.data)
        n, kept = B.delete_faces(body, hid)
        steps['2_head_skin_under_face'] = {'tris': before - tris_of(body.data), 'faces': n, 'candidates': len(cand)}
    rep['seconds_hidden'] = round(time.time() - t, 1)

    # 3. clean-up
    steps['3_cleanup'] = {}
    for o in objs:
        steps['3_cleanup'][o.name] = dict(cleanup(o, measure_only=True), tris=0)

    # 4. rigid small parts
    t = time.time()
    steps['4_rigid_parts'] = {}
    for o in objs:
        if o.name in ('Body', 'Face') or (kind == 'source' and not SOURCE_HIDDEN):
            continue
        before = tris_of(o.data)
        r = rigid_parts(o, tid, objs, rig)
        r['tris'] = before - tris_of(o.data)
        steps['4_rigid_parts'][o.name] = r
    rep['seconds_parts'] = round(time.time() - t, 1)

    # 5-6. shading and weights on LOD0
    src_meshes = src_copies or load_source_meshes(tid, rev, [o.name for o in objs if o.name != 'Face'])
    rep['shading'] = {}
    for o in objs:
        if o.name != 'Face' and tris_of(o.data) != rep['tris_v01'][o.name] and o.name in src_meshes:
            rep['shading'][o.name] = keep_shading(o, src_meshes[o.name])
    bones = bone_set(rig)
    rep['weights_lod0'] = {o.name: B.clean_weights(o, bones) for o in objs}
    rep['steps'] = steps
    rep['tris_lod0'] = {o.name: tris_of(o.data) for o in objs}
    rep['total_lod0'] = sum(rep['tris_lod0'].values())

    # LOD chain
    t = time.time()
    lod_objs = {}
    rep['lods'] = {}
    hems = {o.name: real_hems(o, src_meshes.get(o.name)) for o in objs if o.name != 'Face'}
    rep['hem_verts_lod0'] = {n: len(v) for n, v in hems.items()}
    for level in (1, 2):
        coll = bpy.data.collections.new(f'LOD{level}')
        scene.collection.children.link(coll)
        rep['lods'][level] = {}
        for o in objs:
            c, r = make_lod(rig, o, level, face_objs, hems.get(o.name, set()))
            prev = next((x for x in lod_objs.get(level - 1, []) if x.name.rsplit('_LOD', 1)[0] == o.name), None)
            if prev is not None and tris_of(c.data) > tris_of(prev.data):
                # never heavier than the level below: take a copy of it
                old = c.data
                bpy.data.objects.remove(c); bpy.data.meshes.remove(old)
                c = prev.copy(); c.data = prev.data.copy()
                c.name = c.data.name = f'{o.name}_LOD{level}'
                bpy.context.scene.collection.objects.link(c)
                r['note'] = f'collapse within limits was heavier than LOD{level - 1}: copy of LOD{level - 1}'
            r['cleanup'] = cleanup(c)
            r['tris'] = tris_of(c.data)
            for col in list(c.users_collection):
                col.objects.unlink(c)
            coll.objects.link(c)
            if o.name != 'Face' and o.name in src_meshes and LOD_NORMALS == 'source':
                r['shading'] = lod_shading(c, src_meshes[o.name], reach=max(0.004, LOD[level]['max']))
            elif o.name != 'Face':
                c.data.normals_split_custom_set([(0.0, 0.0, 0.0)] * len(c.data.loops))   # computed normals
                r['shading'] = 'computed'
            r['weights'] = B.clean_weights(c, bones)
            rep['lods'][level][o.name] = r
            lod_objs.setdefault(level, []).append(c)
            log(f"[LOD] {tid} L{level} {o.name:<16} {tris_of(o.data):>6} -> {r['tris']:>6} ok={r['ok']} p99 {r['p99_mm']} max {r['max_mm']} "
                f"rounds {r['rounds']}")
    rep['seconds_lods'] = round(time.time() - t, 1)
    for m in src_meshes.values():
        bpy.data.meshes.remove(m)
    rep['tris_lod1'] = {o.name.rsplit('_LOD', 1)[0]: tris_of(o.data) for o in lod_objs[1]}
    rep['tris_lod2'] = {o.name.rsplit('_LOD', 1)[0]: tris_of(o.data) for o in lod_objs[2]}
    rep['total_lod1'] = sum(rep['tris_lod1'].values())
    rep['total_lod2'] = sum(rep['tris_lod2'].values())

    # checks
    all_objs = objs + lod_objs[1] + lod_objs[2]
    problems = check(rig, all_objs, bones0, mats0)
    for o in all_objs:
        base = o.name.split('_LOD')[0]
        if ([k.name for k in o.data.shape_keys.key_blocks] if o.data.shape_keys else []) != keys0[base]:
            problems.append(f'{o.name}: shape keys differ')
    rep['problems'] = problems
    rep['seconds'] = round(time.time() - t_start, 1)
    if problems:
        rep['result'] = 'not written: checks failed'
        return rep

    # restore the opened state, hide the LOD collections, save
    if keep_face_action is not None:
        sk.animation_data.action = keep_face_action
    rig.animation_data.action = keep_rig[0]
    scene.frame_set(keep_rig[1])
    rig.data.pose_position = keep_rig[2]
    for level in (1, 2):
        coll = bpy.data.collections[f'LOD{level}']
        coll.hide_viewport = True
        coll.hide_render = True
    for a in list(bpy.data.actions):
        if a.name not in actions0:
            bpy.data.actions.remove(a)       # a copy of the rig's current action left by the object copies
    bpy.ops.wm.save_as_mainfile(filepath=str(out['blend']))

    # FBX: Unity LOD naming
    for level in (1, 2):
        coll = bpy.data.collections[f'LOD{level}']
        coll.hide_viewport = False
        coll.hide_render = False
    for o in objs:
        o.name = o.name + '_LOD0'
        o.data.name = o.name
    export_fbx(rig, all_objs, out['fbx'])
    rep['result'] = 'optimised'
    rep['outputs'] = {k: v.name for k, v in out.items()}
    return rep


def export_fbx(rig, objs, path):
    """As opt_v01 (= build_buddy.py): rig + skinned meshes, the Idle clip only, face tracks not exported."""
    for o in objs:
        sk = o.data.shape_keys
        if sk is not None and sk.animation_data:
            sk.animation_data.action = None
    for a in list(bpy.data.actions):
        if a.name.endswith('_Face') or a.name == 'PoliceCall_Phone':
            bpy.data.actions.remove(a)
    bpy.context.view_layer.update()
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
                             use_armature_deform_only=False, bake_anim=True, bake_anim_use_all_actions=False,
                             bake_anim_use_nla_strips=False, bake_anim_simplify_factor=0, axis_forward='-Z', axis_up='Y',
                             apply_unit_scale=True, use_mesh_modifiers=False)


def summary(reports, out_dir):
    merged, rows = {}, []
    for tid, rev in POOL + POOL_SOURCE:
        p = reports / f'{tid}.json'
        if not p.exists():
            continue
        r = json.loads(p.read_text(encoding='utf-8'))
        merged[tid] = r
        rows.append(r)
    (out_dir / f'opt_report_{TAG}.json').write_text(json.dumps(merged, indent=1, ensure_ascii=False), encoding='utf-8')
    for r in sorted(rows, key=lambda r: -r['total_v01']):
        log(f"[SUM] {r['type']:<22} v{r['revision']:02d} {r['total_v01']:>6} -> LOD0 {r.get('total_lod0', 0):>6} "
            f"LOD1 {r.get('total_lod1', 0):>6} LOD2 {r.get('total_lod2', 0):>6}  {r['result']}")


def main():
    global VERBOSE, ISLAND_NORMAL_DEG, LOD_NORMALS
    ap = argparse.ArgumentParser()
    ap.add_argument('--types', default='')
    ap.add_argument('--summary', action='store_true')
    ap.add_argument('--verbose', action='store_true')
    ap.add_argument('--out', default=str(HERE), help='output folder (test runs elsewhere)')
    ap.add_argument('--island-normal', type=float, default=None, help='ISLAND_NORMAL_DEG override (review experiments)')
    ap.add_argument('--lod-normals', default=None, help="'source' or 'auto' (review experiments)")
    ap.add_argument('--hem-rings', default=None, help='LOD1,LOD2 hem lock rings (review experiments)')
    ap.add_argument('--lod-ratios', default=None, help='LOD1,LOD2 collapse ratios (review experiments)')
    args, _ = ap.parse_known_args(sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else [])
    VERBOSE = args.verbose
    if args.lod_normals:
        LOD_NORMALS = args.lod_normals
    if args.lod_ratios:
        LOD[1]['ratio'], LOD[2]['ratio'] = (float(x) for x in args.lod_ratios.split(','))
    if args.hem_rings:
        HEM_LOCK_RINGS[1], HEM_LOCK_RINGS[2] = (int(x) for x in args.hem_rings.split(','))
    if args.island_normal is not None:
        ISLAND_NORMAL_DEG = args.island_normal
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    reports = out_dir / 'reports'
    reports.mkdir(exist_ok=True)
    if args.summary:
        return summary(reports, out_dir)
    want = [t for t in args.types.split(',') if t]
    settings = {'state_step': STATE_STEP, 'face_normal_deg': FACE_NORMAL_DEG, 'island_tol_mm': ISLAND_TOL * 1000,
                'part_diag_m': PART_DIAG, 'skinned_part_diag_m': SKINNED_PART_DIAG, 'island_normal_deg': ISLAND_NORMAL_DEG,
                'island_gap_fraction': ISLAND_GAP_FRACTION, 'rigid_l1': RIGID_L1, 'face_zone': FACE_ZONE,
                'lod': {k: {'ratio': v['ratio'], 'p99_mm': v['p99'] * 1000, 'max_mm': v['max'] * 1000} for k, v in LOD.items()},
                'open_edge_factor': OPEN_EDGE_FACTOR, 'lod_poses': [f'{a}:{f}' if a else 'rest' for a, f in LOD_POSES],
                'face_key_states': FACE_KEY_STATES, 'freeze': FREEZE, 'hem_lock_rings': HEM_LOCK_RINGS,
                'lod_normals': LOD_NORMALS, 'lod_tighten': LOD_TIGHTEN, 'lock_at': LOCK_AT,
                'lod_over': {'share': LOD_OVER_SHARE, 'min': LOD_OVER_MIN, 'factor': LOD_OVER_FACTOR},
                'garment_area_per_edge_m': GARMENT_AREA_PER_EDGE, 'lod_weight_seam': LOD_WEIGHT_SEAM}
    for tid, rev in POOL + POOL_SOURCE:
        if want and tid not in want:
            continue
        rp = reports / f'{tid}.json'
        if rp.exists():
            sys.exit(f'Refusing to overwrite {rp}')
        rep = optimise(tid, rev, out_dir)
        rep['settings'] = settings
        log(f"[OPT] {tid} v{rev:02d} {rep['total_v01']} -> LOD0 {rep.get('total_lod0')} LOD1 {rep.get('total_lod1')} "
            f"LOD2 {rep.get('total_lod2')} {rep['result']} {rep.get('problems', '')} {rep['seconds']} s")
        rp.write_text(json.dumps(rep, indent=1, ensure_ascii=False), encoding='utf-8')


if __name__ == '__main__':
    main()
