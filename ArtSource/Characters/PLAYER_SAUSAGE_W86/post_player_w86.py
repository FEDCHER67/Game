"""PLAYER_SAUSAGE_W86 post stage (Blender 5.2, background): body regions, coverage and clipping checks, crowd LODs,
the FBX files and the manifest.

  blender -b --factory-startup --python ArtSource/Characters/PLAYER_SAUSAGE_W86/post_player_w86.py -- --revision 1 --work <scratch dir> [--no-lods]

Input: <work>/PLAYER_SAUSAGE_W86_vNN.blend from build_player_w86.py (the pipeline's body, face, rig, clips and every part).
Output here (never over an existing file):
  PLAYER_SAUSAGE_W86_vNN.blend          rig, LOD0 meshes, LOD1/LOD2 collections (hidden), every clip and test pose
  PLAYER_SAUSAGE_W86_vNN_base.fbx       rig + Body_* regions + Face + Shoes + Socks (<name>_LOD0/1/2), Idle clip
  PLAYER_SAUSAGE_W86_vNN_parts.fbx      rig + every option mesh (<name>_LOD0/1/2), Idle clip
  PLAYER_SAUSAGE_W86_vNN_manifest.json  options, Russian names, meshes, defaults, hidden body regions, palettes, tris
  validation_PLAYER_SAUSAGE_W86_vNN.json   coverage / clipping / LOD / weights / FBX re-import results

Steps
 1. Shared clips appended read-only from SAUSAGE_BUDDY_01/Animations (the game's Idle / Walk / Run roles, the cargo sit,
    the cop aim, the head hit) and two procedural test poses (Test_Crouch: the KCC crouch, 1.0 m; Test_Carry: arms
    forward holding a load at chest height); no crouch or carry clip exists yet.
 2. Face interior (eye-ball backs inside the head): removed as in Types_opt_v02 step 1 (same functions), covered by the
    body and the face in every sampled clip state and shape-key state.
 3. Body regions: the Body is cut along its loft rings into Body_Head (head, ears, nose, neck base), Body_Hands (hands,
    wrists), Body_Torso, Body_Pelvis, Body_ArmUpper, Body_ArmMid, Body_ArmLower, Body_Thigh, Body_Knee, Body_Shin; the leg below
    the sock tops is removed (always inside the base socks and shoes). Each region keeps the whole body's vertex
    normals (custom normals), so no shading seam shows where two visible regions meet.
 4. Coverage: every vertex of a region an option hides must stay under that option (+ the head, socks and shoes) in
    every test pose: a ray along its normal hits them within 15 cm.
 5. Clipping: for each pair (inner, outer) that can be worn together (visible body regions under each option, bottoms
    under tops, socks and shoes under bottoms, under-hat hair and the face under hats, beards and tops), the inner
    vertices covered by the outer one in the T-pose are followed through every test pose: covered (ray along the
    normal hits the outer mesh), poking through (it does not, but the reverse ray hits the outer surface within 25 mm
    = the inner surface came out through it) or uncovered (slid out from under a hem: not a clip). Plus triangle
    intersections between the two meshes (BVH overlap) per pose against the T-pose count.
 6. LOD1 / LOD2 per mesh with Types_opt_v02.make_lod (same limits, poses and normals); body region borders and garment
    hems locked so neighbouring regions stay sealed. Socks are not decimated (their 4 mm top band collapsed into gaps).
    Every Face (LOD0/1/2) is saved and exported with all shape keys at 0: make_lod leaves its last test state
    (Blink + Surprised = 1) on the LOD copies, which the FBX carries as default blend-shape weights.
"""
import argparse, itertools, json, math, random, sys, time
from pathlib import Path
import bpy, bmesh
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree

HERE = Path(__file__).resolve().parent
BUDDY = HERE.parent / 'SAUSAGE_BUDDY_01'
OPT = BUDDY / 'Types_opt_v02'
for p in (str(BUDDY), str(OPT), str(BUDDY / 'Types_opt_v01'), str(HERE)):
    if p not in sys.path:
        sys.path.insert(0, p)
sys.dont_write_bytecode = True

import build_types_opt_v02 as O        # noqa: E402
import player_w86_parts as PP          # noqa: E402

P = 'mixamorig:'
RIG = 'Buddy_Rig_Mixamo65'
ANIM = BUDDY / 'Animations'
SHARED = {'Idle_Stand_v04': ANIM / 'Idle_Knock_v03' / 'Idle_Stand_v04.blend', 'Walk': ANIM / 'Locomotion_v02' / 'Walk_v04.blend',
          'Flee_Panic_Run': ANIM / 'Crowd_v01' / 'Flee_Panic_Run_v01.blend',
          'Cargo_Sit_Idle_v05': ANIM / 'Idle_Knock_v03' / 'Cargo_Sit_Idle_v05.blend',
          'Cop_Aim_v01': ANIM / 'Escape_Police_v01' / 'Cop_Aim_v01.blend',
          'Hit_React_Head_v01': ANIM / 'Escape_Police_v01' / 'Hit_React_Head_v01.blend'}
# (label, action, fraction of the clip range) ; None = T-pose
TEST_POSES = [('tpose', None, 0), ('idle', 'Idle_Stand_v04', 0.0), ('idle', 'Idle_Stand_v04', 0.5),
              ('walk', 'Walk', 0.0), ('walk', 'Walk', 0.25), ('walk', 'Walk', 0.5), ('walk', 'Walk', 0.75),
              ('run', 'Flee_Panic_Run', 0.0), ('run', 'Flee_Panic_Run', 0.25), ('run', 'Flee_Panic_Run', 0.5),
              ('run', 'Flee_Panic_Run', 0.75), ('crouch', 'Test_Crouch', 0.0), ('carry', 'Test_Carry', 0.0),
              ('sit', 'Cargo_Sit_Idle_v05', 0.0), ('aim', 'Cop_Aim_v01', 0.5), ('hit_head', 'Hit_React_Head_v01', 0.3),
              ('panic_run', 'Panic_Run_Loop', 0.3)]
BASE_FIXED = ['Shoes', 'Socks']
REGIONS = [r for r, _ in PP.BODY_REGIONS]
NEVER_HIDDEN = ['Body_Head', 'Body_Hands']
COVER_REACH = 0.45
SEEN_REACH, FOLLOW_REACH, POKE_REACH, COPLANAR = 0.06, 0.08, 0.025, 0.0006
NO_DECIMATE = {'Socks'}     # the 4 mm sock-top band collapsed into gaps showing the leg at LOD1/2; 288 tris stay as they are


def log(*a):
    print('[POST]', *a, flush=True)

# ------------------------------------------------------------------ option bookkeeping
def options():
    """[(aspect, id, name_ru, mesh or None, mesh_under_hat or None, hides, under_hat)]"""
    out = []
    for pid, name, fn, lower in PP.HAIRS:
        out.append(('hair', pid, name, pid if fn else None, (pid + '_Hat') if fn else None, [], False))
    for pid, name, fn in PP.BEARDS:
        out.append(('beard', pid, name, pid if fn else None, None, [], False))
    for pid, name, fn, hides in PP.TOPS:
        out.append(('top', pid, name, pid, None, hides, False))
    for pid, name, fn, hides in PP.BOTTOMS:
        out.append(('bottom', pid, name, pid, None, hides, False))
    for pid, name, fn, under in PP.HEADS:
        out.append(('head', pid, name, pid if fn else None, None, [], under))
    return out


def part_meshes():
    names = []
    for a, pid, n, mesh, hat, hides, under in options():
        names += [x for x in (mesh, hat) if x]
    return names

# ------------------------------------------------------------------ 1. clips and test poses
def append_action(path, name):
    with bpy.data.libraries.load(str(path), link=False) as (src, dst):
        dst.actions = [name]
    act = dst.actions[0]
    act.use_fake_user = True
    return act


def _upd():
    bpy.context.view_layer.update()


def aim(rig, bone, target):
    pb = rig.pose.bones[P + bone]
    _upd()
    M = pb.matrix.copy()
    h = M.translation.copy()
    cur = (M.to_3x3() @ Vector((0, 1, 0))).normalized()
    q = cur.rotation_difference(Vector(target).normalized())
    pb.matrix = Matrix.Translation(h) @ q.to_matrix().to_4x4() @ Matrix.Translation(-h) @ M
    _upd()


def rotate(rig, bone, axis, deg):
    pb = rig.pose.bones[P + bone]
    _upd()
    M = pb.matrix.copy()
    h = M.translation.copy()
    pb.matrix = Matrix.Translation(h) @ Matrix.Rotation(math.radians(deg), 4, Vector(axis)) @ Matrix.Translation(-h) @ M
    _upd()


def move(rig, bone, delta):
    pb = rig.pose.bones[P + bone]
    _upd()
    pb.matrix = Matrix.Translation(Vector(delta)) @ pb.matrix
    _upd()


def crouch_pose(rig):
    """The KCC crouch (capsule 1.0 m): deep knee bend, thighs forward, torso leaning over the knees, forearms
    hanging in front."""
    move(rig, 'Hips', (0, 0.06, -0.30))
    rotate(rig, 'Spine', (1, 0, 0), 16)
    rotate(rig, 'Spine1', (1, 0, 0), 10)
    rotate(rig, 'Neck', (1, 0, 0), -14)
    rotate(rig, 'Head', (1, 0, 0), -10)
    for side, s in (('Left', 1), ('Right', -1)):
        aim(rig, side + 'UpLeg', (s * 0.16, -0.96, -0.22))
        aim(rig, side + 'Leg', (s * 0.04, 0.42, -0.91))
        aim(rig, side + 'Foot', (0, -0.80, -0.60))
        aim(rig, side + 'ToeBase', (0, -0.986, -0.164))
        aim(rig, side + 'Arm', (s * 0.30, -0.40, -0.86))
        aim(rig, side + 'ForeArm', (s * 0.05, -0.80, -0.60))
        aim(rig, side + 'Hand', (s * 0.05, -0.75, -0.66))


def carry_pose(rig):
    """Arms forward holding a load (a box, a body) at chest height, elbows bent, a slight lean back."""
    rotate(rig, 'Spine1', (1, 0, 0), -6)
    for side, s in (('Left', 1), ('Right', -1)):
        aim(rig, side + 'Arm', (s * 0.30, -0.80, -0.52))
        aim(rig, side + 'ForeArm', (-s * 0.30, -0.90, 0.30))
        aim(rig, side + 'Hand', (-s * 0.20, -0.95, 0.20))
        aim(rig, side + 'UpLeg', (s * 0.02, -0.06, -1.0))
        aim(rig, side + 'Leg', (0, 0.04, -1.0))


def ground_shift(rig, objs):
    _upd()
    dg = bpy.context.evaluated_depsgraph_get()
    low = 1e9
    for o in objs:
        oe = o.evaluated_get(dg)
        me = oe.to_mesh()
        low = min(low, min((o.matrix_world @ v.co).z for v in me.vertices))
        oe.to_mesh_clear()
    return low


def make_pose_action(rig, name, fn, ground_objs):
    ad = rig.animation_data_create()
    ad.action = None
    rig.data.pose_position = 'POSE'
    for pb in rig.pose.bones:
        pb.rotation_mode = 'QUATERNION'
        pb.matrix_basis = Matrix()
    _upd()
    fn(rig)
    move(rig, 'Hips', (0, 0, -ground_shift(rig, ground_objs)))
    act = bpy.data.actions.new(name)
    act.use_fake_user = True
    ad.action = act
    for pb in rig.pose.bones:
        for path in ('location', 'rotation_quaternion', 'scale'):
            pb.keyframe_insert(path, frame=1, group=pb.name)
            pb.keyframe_insert(path, frame=2, group=pb.name)
    ad.action = None
    for pb in rig.pose.bones:
        pb.matrix_basis = Matrix()
    return act


def set_pose(rig, act, frac):
    if act is None:
        rig.data.pose_position = 'REST'
        bpy.context.scene.frame_set(1)
        return 0
    rig.data.pose_position = 'POSE'
    a = bpy.data.actions[act]
    rig.animation_data.action = a
    f0, f1 = (int(round(x)) for x in a.frame_range)
    fr = int(round(f0 + (f1 - f0) * frac))
    bpy.context.scene.frame_set(fr)
    return fr

# ------------------------------------------------------------------ 3. body regions
def region_of_faces(body):
    """Region name per Body polygon (None = removed: the leg inside the socks)."""
    me = body.data
    bm = bmesh.new(); bm.from_mesh(me); bm.faces.ensure_lookup_table()
    islands = O.islands_of(bm)
    out = [None] * len(me.polygons)
    for isl in islands:
        fs = [bm.faces[i] for i in isl]
        vs = {v for f in fs for v in f.verts}
        lo = Vector((min(v.co.x for v in vs), min(v.co.y for v in vs), min(v.co.z for v in vs)))
        hi = Vector((max(v.co.x for v in vs), max(v.co.y for v in vs), max(v.co.z for v in vs)))
        ax = max(abs(lo.x), abs(hi.x))
        for f in fs:
            c = f.calc_center_median()
            if hi.z > 1.60 or lo.z > 1.30:                       # head capsule, nose, ears
                r = 'Body_Head'
            elif min(abs(lo.x), abs(hi.x)) > 0.55 and lo.z > 1.0:   # palms, fingers, thumbs
                r = 'Body_Hands'
            elif hi.x - lo.x > 0.30 and lo.z > 1.0:              # arm lofts
                x = abs(c.x)
                r = 'Body_ArmUpper' if x < 0.27 else 'Body_ArmMid' if x < 0.44 else 'Body_ArmLower' if x < 0.565 else 'Body_Hands'
            elif lo.z < 0.30:                                    # legs
                r = ('Body_Pelvis' if c.z >= 0.79 else 'Body_Thigh' if c.z >= 0.65 else 'Body_Knee' if c.z >= 0.56 else
                     'Body_Shin' if c.z >= 0.20 else None)
            else:                                                # torso loft
                r = 'Body_Head' if c.z >= 1.18 else 'Body_Torso' if c.z >= 0.90 else 'Body_Pelvis'
            out[f.index] = r
    bm.free()
    return out


def split_body(body):
    me = body.data
    nattr = me.attributes.new('pl_normal', 'FLOAT_VECTOR', 'POINT')
    for v, d in zip(me.vertices, nattr.data):
        d.vector = v.normal.copy()
    regs = region_of_faces(body)
    counts = {}
    objs = {}
    for r in REGIONS:
        ob = body.copy(); ob.data = me.copy()
        ob.name = ob.data.name = r
        for c in body.users_collection:
            c.objects.link(ob)
        bm = bmesh.new(); bm.from_mesh(ob.data); bm.faces.ensure_lookup_table()
        drop = [f for f in bm.faces if regs[f.index] != r]
        bmesh.ops.delete(bm, geom=drop, context='FACES')
        loose = [v for v in bm.verts if not v.link_faces]
        bmesh.ops.delete(bm, geom=loose, context='VERTS')
        bm.to_mesh(ob.data); bm.free()
        m = ob.data
        nn = [Vector(d.vector) for d in m.attributes['pl_normal'].data]
        m.attributes.remove(m.attributes['pl_normal'])
        m.normals_split_custom_set_from_vertices(nn)
        objs[r] = ob
        counts[r] = O.tris_of(m)
    removed = sum(1 for r in regs if r is None)
    me.attributes.remove(me.attributes['pl_normal'])
    return objs, counts, removed

# ------------------------------------------------------------------ evaluation helpers
def snap(ob, dg):
    oe = ob.evaluated_get(dg)
    me = oe.to_mesh()
    mw = ob.matrix_world
    r3 = mw.to_3x3()
    co = [mw @ v.co for v in me.vertices]
    nrm = [(r3 @ v.normal).normalized() for v in me.vertices]
    me.calc_loop_triangles()
    tris = [tuple(t.vertices) for t in me.loop_triangles]
    oe.to_mesh_clear()
    return co, nrm, tris


def bvh_of(snaps):
    vs, ts = [], []
    for co, _n, tris in snaps:
        b = len(vs)
        vs += co
        ts += [(a + b, c + b, d + b) for a, c, d in tris]
    return BVHTree.FromPolygons(vs, ts) if ts else None


def poses_snapshots(rig, names, face=None, face_keys=None):
    """{pose_key: {name: snap}} over TEST_POSES."""
    out = {}
    for label, act, frac in TEST_POSES:
        fr = set_pose(rig, act, frac)
        _upd()
        dg = bpy.context.evaluated_depsgraph_get()
        out[(label, act, fr)] = {n: snap(bpy.data.objects[n], dg) for n in names}
    rig.data.pose_position = 'POSE'
    return out

# ------------------------------------------------------------------ 4-5. coverage and clipping
def coverage(snaps, part, regions):
    """Vertices of the hidden regions in a pose: (escaping, poked, total). Escaping: the ray along the normal leaves
    without meeting the part (+ head, socks, shoes) within COVER_REACH (a view through an opening: a hole once hidden);
    poked: it does not, but the reverse ray meets the part within POKE_REACH (the body came out through the part:
    hiding the region removes that poke, no hole)."""
    occl = bvh_of([snaps[part], snaps['Body_Head']] + [snaps[b] for b in BASE_FIXED])
    out = {}
    for r in regions:
        co, nrm, _ = snaps[r]
        esc = poked = 0
        for p, n in zip(co, nrm):
            if occl.ray_cast(p + n * 1e-4, n, COVER_REACH)[0] is None:
                if occl.ray_cast(p, -n, POKE_REACH)[0] is not None:
                    poked += 1
                else:
                    esc += 1
        out[r] = (esc, poked, len(co))
    return out


def seen_set(snap_a, bvh_b):
    co, nrm, _ = snap_a
    return [i for i, (p, n) in enumerate(zip(co, nrm)) if bvh_b.ray_cast(p + n * 1e-4, n, SEEN_REACH)[0] is not None]


def follow(snap_a, bvh_b, idx):
    co, nrm, _ = snap_a
    poke, depth, unc, flat = 0, 0.0, 0, 0
    for i in idx:
        p, n = co[i], nrm[i]
        hit = bvh_b.ray_cast(p + n * 1e-4, n, FOLLOW_REACH)
        if hit[0] is not None:
            if hit[3] < COPLANAR:
                flat += 1
            continue
        back = bvh_b.ray_cast(p, -n, POKE_REACH)
        if back[0] is not None:
            poke += 1
            depth = max(depth, back[3])
        else:
            unc += 1
    return poke, depth, unc, flat


def overlap_count(sa, sb):
    a, b = bvh_of([sa]), bvh_of([sb])
    if a is None or b is None:
        return 0
    return len(a.overlap(b))


def clip_pairs():
    """(inner, outer, note) pairs that are worn together."""
    opts = options()
    tops = [o for o in opts if o[0] == 'top']
    bottoms = [o for o in opts if o[0] == 'bottom']
    common_top = set.intersection(*[set(o[5]) for o in tops])
    common_bottom = set.intersection(*[set(o[5]) for o in bottoms])
    pairs = []
    for a, pid, n, mesh, hat, hides, under in opts:
        for m in (mesh, hat):
            if not m:
                continue
            hidden = set(hides) | (common_bottom if a == 'top' else common_top if a == 'bottom' else common_top | common_bottom)
            for r in REGIONS:
                if r not in hidden:
                    pairs.append((r, m, 'body'))
    for b in BASE_FIXED:
        for r in REGIONS:
            if r not in common_top | common_bottom:
                pairs.append((r, b, 'body'))
    for t in tops:
        for bo in bottoms:
            pairs.append((bo[3], t[3], 'bottom under top'))
        for h in [o for o in opts if o[0] == 'hair' and o[3]]:
            pairs.append((h[3], t[3], 'hair / top'))
            pairs.append((t[3], h[3], 'top / hair'))
        for bd in [o for o in opts if o[0] == 'beard' and o[3]]:
            pairs.append((bd[3], t[3], 'beard / top'))
            pairs.append((t[3], bd[3], 'top / beard'))
    for bo in bottoms:
        pairs += [('Socks', bo[3], 'socks under bottom'), ('Shoes', bo[3], 'shoes under bottom'), (bo[3], 'Shoes', 'bottom in shoes')]
    for hd in [o for o in opts if o[0] == 'head' and o[3]]:
        if hd[6]:
            for h in [o for o in opts if o[0] == 'hair' and o[4]]:
                pairs.append((h[4], hd[3], 'hair under hat'))
        else:
            for h in [o for o in opts if o[0] == 'hair' and o[3]]:
                pairs.append((h[3], hd[3], 'hair / glasses'))
                pairs.append((hd[3], h[3], 'glasses / hair'))
        pairs.append(('Face', hd[3], 'face under headwear'))
        for bd in [o for o in opts if o[0] == 'beard' and o[3]]:
            pairs.append((bd[3], hd[3], 'beard / headwear'))
    for h in [o for o in opts if o[0] == 'hair' and o[3]]:
        pairs.append(('Face', h[3], 'face under hair'))
    for bd in [o for o in opts if o[0] == 'beard' and o[3]]:
        pairs.append(('Face', bd[3], 'face under beard'))
    return pairs


def run_checks(rig, face):
    names = REGIONS + BASE_FIXED + ['Face'] + part_meshes()
    face_states = [{}, {'Surprised': 1.0}, {'Happy': 1.0}, {'Worried': 1.0}, {'Blink': 1.0}]
    snaps = poses_snapshots(rig, names)
    rest_key = next(k for k in snaps if k[0] == 'tpose')
    # face shape-key states in the idle pose (the face only matters next to hair, beards and headwear)
    idle_key = next(k for k in snaps if k[0] == 'idle')
    set_pose(rig, idle_key[1], 0.0)
    face_snaps = {}
    for st in face_states:
        for kb in face.data.shape_keys.key_blocks[1:]:
            kb.value = st.get(kb.name, 0.0)
        _upd()
        face_snaps[json.dumps(st)] = snap(face, bpy.context.evaluated_depsgraph_get())
    for kb in face.data.shape_keys.key_blocks[1:]:
        kb.value = 0.0
    rep = {'poses': [f'{l} {a or "T-pose"} f{f}' for l, a, f in snaps], 'coverage': {}, 'clipping': [], 'face_states': {}}
    # coverage of the hidden regions
    for a, pid, n, mesh, hat, hides, under in options():
        if not hides:
            continue
        worst = {}
        for key, sn in snaps.items():
            for r, (esc, poked, tot) in coverage(sn, mesh, hides).items():
                w = worst.setdefault(r, {'escaping_verts_max': 0, 'poked_verts_max': 0, 'verts': tot, 'worst_pose': None})
                if esc > w['escaping_verts_max']:
                    w['escaping_verts_max'], w['worst_pose'] = esc, f'{key[0]} {key[1] or "T-pose"} f{key[2]}'
                w['poked_verts_max'] = max(w['poked_verts_max'], poked)
        rep['coverage'][pid] = worst
    # clipping pairs
    cache = {}

    def bv(key, name, sn):
        if (key, name) not in cache:
            cache[(key, name)] = bvh_of([sn[name]])
        return cache[(key, name)]

    def ovl(key, a, b, sn):
        x, y = bv(key, a, sn), bv(key, b, sn)
        return len(x.overlap(y)) if x is not None and y is not None else 0
    for inner, outer, note in clip_pairs():
        bvh_r = bv(rest_key, outer, snaps[rest_key])
        seen = seen_set(snaps[rest_key][inner], bvh_r)
        ov0 = ovl(rest_key, inner, outer, snaps[rest_key])
        row = {'inner': inner, 'outer': outer, 'note': note, 'inner_verts_under_outer': len(seen), 'overlap_tris_tpose': ov0,
               'poke_verts_max': 0, 'poke_depth_mm_max': 0.0, 'coplanar_verts_max': 0, 'overlap_tris_max': ov0, 'worst_pose': None}
        for key, sn in snaps.items():
            if not seen and key != rest_key:
                pk = (0, 0.0, 0, 0)
            else:
                pk = follow(sn[inner], bv(key, outer, sn), seen)
            ov = ovl(key, inner, outer, sn)
            if pk[0] > row['poke_verts_max'] or ov > row['overlap_tris_max']:
                row['worst_pose'] = f'{key[0]} {key[1] or "T-pose"} f{key[2]}'
            row['poke_verts_max'] = max(row['poke_verts_max'], pk[0])
            row['poke_depth_mm_max'] = max(row['poke_depth_mm_max'], round(pk[1] * 1000, 1))
            row['coplanar_verts_max'] = max(row['coplanar_verts_max'], pk[3])
            row['overlap_tris_max'] = max(row['overlap_tris_max'], ov)
        rep['clipping'].append(row)
    # face shape keys next to hair / beards / headwear (idle pose)
    idle = snaps[idle_key]
    for inner, outer, note in clip_pairs():
        if inner != 'Face':
            continue
        base = face_snaps[json.dumps({})]
        seen = seen_set(base, bvh_of([idle[outer]]))
        res = {}
        for st, fs in face_snaps.items():
            pk = follow(fs, bvh_of([idle[outer]]), seen)
            res[st] = {'poke': pk[0], 'depth_mm': round(pk[1] * 1000, 1), 'overlap_tris': overlap_count(fs, idle[outer])}
        rep['face_states'][outer] = res
    rig.data.pose_position = 'POSE'
    return rep

# ------------------------------------------------------------------ 6. LODs
def open_verts(me):
    bm = bmesh.new(); bm.from_mesh(me)
    out = {v.index for e in bm.edges if len(e.link_faces) == 1 for v in e.verts}
    bm.free()
    return out


def lods(rig, objs, face, body_src):
    bones = O.bone_set(rig)
    rep = {}
    lod_objs = {1: [], 2: []}
    srcs = {o.name: o.data.copy() for o in objs if o.name != 'Face'}
    for m in srcs.values():
        m.name = 'PL_SRC_' + m.name
    for level in (1, 2):
        coll = bpy.data.collections.new(f'LOD{level}')
        bpy.context.scene.collection.children.link(coll)
        for o in objs:
            if o.name.startswith('Body_'):
                hems = open_verts(o.data)                       # region borders: locked so the regions stay sealed
            elif o.name == 'Face':
                hems = set()
            else:
                hems = O.real_hems(o, srcs[o.name])
            if o.name in NO_DECIMATE:
                c = o.copy(); c.data = o.data.copy()
                c.name = c.data.name = f'{o.name}_LOD{level}'
                bpy.context.scene.collection.objects.link(c)
                r = {'tris': O.tris_of(c.data), 'ok': True, 'note': 'not decimated: copy of LOD0', 'p99_mm': 0.0, 'max_mm': 0.0}
            else:
                c, r = O.make_lod(rig, o, level, [face], hems)
            if c.data.shape_keys is not None:      # make_lod leaves its last test state (Blink + Surprised) on the copy
                for kb in c.data.shape_keys.key_blocks[1:]:
                    kb.value = 0.0
            prev = next((x for x in lod_objs.get(level - 1, []) if x.name.rsplit('_LOD', 1)[0] == o.name), None)
            if prev is not None and O.tris_of(c.data) > O.tris_of(prev.data):
                old = c.data
                bpy.data.objects.remove(c); bpy.data.meshes.remove(old)
                c = prev.copy(); c.data = prev.data.copy()
                c.name = c.data.name = f'{o.name}_LOD{level}'
                bpy.context.scene.collection.objects.link(c)
                r['note'] = f'collapse within limits was heavier than LOD{level - 1}: copy of LOD{level - 1}'
            r['cleanup'] = O.cleanup(c)
            r['tris'] = O.tris_of(c.data)
            for col in list(c.users_collection):
                col.objects.unlink(c)
            coll.objects.link(c)
            if o.name == 'Face':
                c.data.normals_split_custom_set([(0.0, 0.0, 0.0)] * len(c.data.loops))
                r['shading'] = 'computed'
            else:
                src = body_src if o.name.startswith('Body_') else srcs[o.name]
                r['shading'] = O.lod_shading(c, src, reach=max(0.004, O.LOD[level]['max']))
            r['weights'] = O.B.clean_weights(c, bones)
            r.pop('history', None)
            rep.setdefault(o.name, {})[level] = r
            lod_objs[level].append(c)
            log(f"LOD{level} {o.name:<14} {O.tris_of(o.data):>5} -> {r['tris']:>5} ok={r['ok']} p99 {r['p99_mm']} max {r['max_mm']}")
    for m in srcs.values():
        bpy.data.meshes.remove(m)
    return lod_objs, rep

# ------------------------------------------------------------------ exports
def export_fbx(rig, objs, path):
    bpy.ops.object.select_all(action='DESELECT')
    for o in [rig] + objs:
        o.hide_set(False)
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


def reimport_check(path):
    """Import the FBX into an empty scene: bones, mesh names, triangles, influences."""
    keep = set(bpy.data.objects)
    bpy.ops.import_scene.fbx(filepath=str(path))
    new = [o for o in bpy.data.objects if o not in keep]
    arm = [o for o in new if o.type == 'ARMATURE']
    out = {'armatures': len(arm), 'bones': len(arm[0].data.bones) if arm else 0, 'meshes': {}}
    for o in new:
        if o.type == 'MESH':
            names = {g.index for g in o.vertex_groups}
            infl = [len([g for g in v.groups if g.weight > 1e-4]) for v in o.data.vertices]
            out['meshes'][o.name] = {'tris': O.tris_of(o.data), 'max_infl': max(infl) if infl else 0,
                                     'unweighted': infl.count(0), 'groups': len(names)}
            if o.data.shape_keys is not None:
                out['meshes'][o.name]['shape_keys'] = [k.name for k in o.data.shape_keys.key_blocks]
                out['meshes'][o.name]['shape_key_values_nonzero'] = {k.name: round(k.value, 3) for k in o.data.shape_keys.key_blocks[1:]
                                                                     if k.value > 1e-4}
    out['actions'] = sorted({a.name for a in bpy.data.actions if a.users and any(o.animation_data and o.animation_data.action == a for o in new)})
    for o in new:
        d = o.data
        bpy.data.objects.remove(o)
        if d is not None and d.users == 0:
            (bpy.data.meshes if isinstance(d, bpy.types.Mesh) else bpy.data.armatures).remove(d)
    return out


def combo_tris(tris0, opts):
    """Triangles of every full outfit (5^5 combinations; a hat swaps the hair to its under-hat mesh; body regions
    hidden by the top and bottom dropped): max / mean / min and the heaviest combination."""
    by = {a: [o for o in opts if o[0] == a] for a in ('hair', 'beard', 'top', 'bottom', 'head')}
    fixed = sum(tris0[n] for n in BASE_FIXED + ['Face'])
    totals = []
    for h, b, t, bo, hd in itertools.product(*(by[a] for a in ('hair', 'beard', 'top', 'bottom', 'head'))):
        hidden = set(t[5]) | set(bo[5])
        body = sum(tris0[r] for r in REGIONS if r not in hidden)
        hair = h[4] if hd[6] else h[3]
        s = fixed + body + sum(tris0[m] for m in (hair, b[3], t[3], bo[3], hd[3]) if m)
        totals.append((s, (h[1], b[1], t[1], bo[1], hd[1])))
    totals.sort()
    return {'combinations': len(totals), 'max': totals[-1][0], 'heaviest': totals[-1][1], 'mean': round(sum(t for t, _ in totals) / len(totals)),
            'min': totals[0][0], 'lightest': totals[0][1]}


def rgbhex(c):
    return '#%02X%02X%02X' % tuple(c)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--revision', type=int, required=True)
    ap.add_argument('--work', required=True)
    ap.add_argument('--no-lods', action='store_true')
    ap.add_argument('--out', default=str(HERE))
    args, _ = ap.parse_known_args(sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else [])
    rev = f'v{args.revision:02d}'
    stem = f'{PP.ASSET}_{rev}'
    out_dir = Path(args.out)
    outs = {'blend': out_dir / f'{stem}.blend', 'base': out_dir / f'{stem}_base.fbx', 'parts': out_dir / f'{stem}_parts.fbx',
            'manifest': out_dir / f'{stem}_manifest.json', 'validation': out_dir / f'validation_{stem}.json'}
    for p in outs.values():
        if p.exists():
            sys.exit(f'Refusing to overwrite {p}')
    t0 = time.time()
    src = Path(args.work) / f'{stem}.blend'
    bpy.ops.wm.open_mainfile(filepath=str(src))
    scene = bpy.context.scene
    rig = bpy.data.objects[RIG]
    for pb in rig.pose.bones:
        pb.rotation_mode = 'QUATERNION'
    body, face = bpy.data.objects['Body'], bpy.data.objects['Face']
    build_report = json.loads((Path(args.work) / f'validation_{PP.TID}_{rev}.json').read_text(encoding='utf-8'))
    bones0 = {b.name: b.matrix_local.copy() for b in rig.data.bones}
    keep_action = rig.animation_data.action
    phone = bpy.data.objects.get('Prop_Phone')
    if phone is not None:                                     # the NPC gag phone: not part of the player
        bpy.data.objects.remove(phone)
    val = {'asset': stem, 'source_build': src.name, 'build': {k: build_report[k] for k in ('height_m', 'bones', 'total_triangles', 'actions')}}

    # 1. clips and test poses
    for name, path in SHARED.items():
        append_action(path, name)
    ground = [body, bpy.data.objects['Shoes']]
    make_pose_action(rig, 'Test_Crouch', crouch_pose, ground)
    make_pose_action(rig, 'Test_Carry', carry_pose, ground)
    val['test_clips'] = {n: str(p.relative_to(BUDDY.parent.parent.parent)) for n, p in SHARED.items()}
    val['test_clips'].update({'Test_Crouch': 'procedural (no crouch clip exists): KCC crouch, deep knee bend',
                              'Test_Carry': 'procedural (no carry clip exists): arms forward at chest height'})

    # 2. face interior (Types_opt_v02 step 1, cover = body + face)
    t = time.time()
    states = O.sample_states(rig, face)
    hid = O.hidden_over_states(rig, [face], states, [body, face], face, range(len(face.data.polygons)))
    n_hidden = O.tri_count(face.data, hid)
    hid, kept = O.normal_margin(face, hid)
    before = O.tris_of(face.data)
    O.B.delete_faces(face, hid)
    val['face_interior'] = {'tris_removed': before - O.tris_of(face.data), 'hidden_tris': n_hidden, 'kept_for_normals_tris': kept,
                            'states': len(states), 'seconds': round(time.time() - t, 1)}
    log('face interior', val['face_interior'])
    O.apply_state(rig, [face], (None, 0, {}))

    # 3. body regions
    body_src = body.data.copy()
    body_src.name = 'PL_SRC_Body'
    regions, region_tris, removed = split_body(body)
    bpy.data.objects.remove(body)
    val['body_regions'] = {'tris': region_tris, 'removed_faces_inside_socks': removed}
    log('regions', region_tris, 'removed', removed)

    # 4-5. coverage and clipping
    t = time.time()
    rig.animation_data.action = None
    checks = run_checks(rig, face)
    checks['seconds'] = round(time.time() - t, 1)
    val['checks'] = checks
    bad = [r for r in checks['clipping'] if r['poke_verts_max'] or r['overlap_tris_max'] > r['overlap_tris_tpose']]
    log('coverage', json.dumps(checks['coverage'], ensure_ascii=False))
    log(f'clipping pairs {len(checks["clipping"])}, with pokes or new overlaps: {len(bad)}')
    for r in sorted(bad, key=lambda r: -r['poke_verts_max'])[:60]:
        log('  ', r['inner'], 'under', r['outer'], 'poke', r['poke_verts_max'], f"{r['poke_depth_mm_max']} mm", 'overlap',
            r['overlap_tris_tpose'], '->', r['overlap_tris_max'], r['worst_pose'])

    # tris and LODs
    mesh_names = REGIONS + BASE_FIXED + ['Face'] + part_meshes()
    objs = [bpy.data.objects[n] for n in mesh_names]
    tris0 = {n: O.tris_of(bpy.data.objects[n].data) for n in mesh_names}
    val['tris_lod0'] = tris0
    val['outfit_tris_lod0'] = combo_tris(tris0, options())
    crowd = json.loads((OPT / 'opt_report_opt_v02.json').read_text(encoding='utf-8'))
    l0 = [v['total_lod0'] for v in crowd.values() if v.get('total_lod0')]
    val['crowd_lod0_average'] = round(sum(l0) / len(l0))
    log('outfit tris', val['outfit_tris_lod0'], 'crowd LOD0 average', val['crowd_lod0_average'])
    if args.no_lods:
        bpy.ops.wm.save_as_mainfile(filepath=str(Path(args.work) / f'{stem}_post_nolods.blend'))
        (Path(args.work) / f'validation_{stem}_nolods.json').write_text(json.dumps(val, indent=1, ensure_ascii=False), encoding='utf-8')
        log('no-lods run saved in work dir', round(time.time() - t0, 1), 's')
        return
    t = time.time()
    lod_objs, lod_rep = lods(rig, objs, face, body_src)
    val['lods'] = lod_rep
    val['lod_seconds'] = round(time.time() - t, 1)
    bpy.data.meshes.remove(body_src)
    tris1 = {o.name.rsplit('_LOD', 1)[0]: O.tris_of(o.data) for o in lod_objs[1]}
    tris2 = {o.name.rsplit('_LOD', 1)[0]: O.tris_of(o.data) for o in lod_objs[2]}
    val['tris_lod1'], val['tris_lod2'] = tris1, tris2
    val['outfit_tris_lod1'] = combo_tris(tris1, options())
    val['outfit_tris_lod2'] = combo_tris(tris2, options())
    mats0 = {o.name: ([m.name for m in o.data.materials], {p.material_index for p in o.data.polygons}) for o in objs}
    problems = O.check(rig, objs + lod_objs[1] + lod_objs[2], bones0, mats0)
    if any(max(abs(x - y) for r1, r2 in zip(b.matrix_local, bones0[b.name]) for x, y in zip(r1, r2)) > 1e-7 for b in rig.data.bones):
        problems.append('rig changed')
    val['problems'] = problems
    log('problems', problems)

    # save .blend (LOD collections hidden), then the FBX files with Unity LOD names; every face rests at the basis
    for o in [face] + [x for x in lod_objs[1] + lod_objs[2] if x.data.shape_keys is not None]:
        sk = o.data.shape_keys
        if sk.animation_data:
            sk.animation_data.action = None
        for kb in sk.key_blocks[1:]:
            kb.value = 0.0
    val['face_keys_at_export'] = {o.name: {k.name: k.value for k in o.data.shape_keys.key_blocks[1:] if k.value}
                                  for o in [face] + lod_objs[1] + lod_objs[2] if o.data.shape_keys is not None}
    rig.animation_data.action = keep_action
    rig.data.pose_position = 'POSE'
    scene.frame_set(1)
    for level in (1, 2):
        c = bpy.data.collections[f'LOD{level}']
        c.hide_viewport = True
        c.hide_render = True
    bpy.ops.wm.save_as_mainfile(filepath=str(outs['blend']))
    for level in (1, 2):
        c = bpy.data.collections[f'LOD{level}']
        c.hide_viewport = False
        c.hide_render = False
    for o in objs:
        o.name = o.name + '_LOD0'
        o.data.name = o.name
    base_names = set(REGIONS + BASE_FIXED + ['Face'])
    every = objs + lod_objs[1] + lod_objs[2]
    base_objs = [o for o in every if o.name.rsplit('_LOD', 1)[0] in base_names]
    part_objs = [o for o in every if o.name.rsplit('_LOD', 1)[0] not in base_names]
    sk = face.data.shape_keys
    if sk is not None and sk.animation_data:
        sk.animation_data.action = None
    export_fbx(rig, base_objs, outs['base'])
    export_fbx(rig, part_objs, outs['parts'])
    val['fbx'] = {}
    for k in ('base', 'parts'):
        bpy.ops.wm.read_factory_settings(use_empty=True)
        val['fbx'][outs[k].name] = reimport_check(outs[k])
    write_manifest(outs, val, rev)
    val['seconds'] = round(time.time() - t0, 1)
    outs['validation'].write_text(json.dumps(val, indent=1, ensure_ascii=False), encoding='utf-8')
    log('written', [p.name for p in outs.values()], val['seconds'], 's')


def write_manifest(outs, val, rev):
    opts = options()
    t0, t1, t2 = val['tris_lod0'], val['tris_lod1'], val['tris_lod2']

    def tri(m):
        return {'lod0': t0[m], 'lod1': t1[m], 'lod2': t2[m]} if m else None
    aspects = {}
    names_ru = {'hair': 'Причёска', 'beard': 'Борода и усы', 'top': 'Верх', 'bottom': 'Низ', 'head': 'Головной убор / аксессуар'}
    for a in ('hair', 'beard', 'top', 'bottom', 'head'):
        rows = []
        for asp, pid, name, mesh, hat, hides, under in opts:
            if asp != a:
                continue
            row = {'id': pid, 'name_ru': name, 'mesh': mesh, 'lods': [f'{mesh}_LOD{k}' for k in range(3)] if mesh else [],
                   'hides_body_regions': hides, 'tris': tri(mesh)}
            if a == 'hair':
                row['mesh_under_hat'] = hat
                row['lods_under_hat'] = [f'{hat}_LOD{k}' for k in range(3)] if hat else []
                row['tris_under_hat'] = tri(hat)
            if a == 'head':
                row['hair_under_hat'] = under
            if a in ('top', 'bottom'):
                row['default_swatch'] = PP.OPTION_SWATCH[pid]
                cov = val['checks']['coverage'].get(pid, {})
                row['coverage_check'] = {r: {'escaping_verts_max': cov[r]['escaping_verts_max'], 'poked_verts_max': cov[r]['poked_verts_max']}
                                         for r in cov}
            rows.append(row)
        aspects[a] = {'name_ru': names_ru[a], 'default': PP.DEFAULTS[a], 'options': rows}
    man = {
        'asset': PP.ASSET, 'revision': rev,
        'note': 'The player as a customisable Sausage Buddy (Fedya 2026-10-29). Same Buddy_Rig_Mixamo65 (65 Mixamo bones, '
                'BASE rest pose) as every Sausage Buddy NPC: every shared NPC clip plays on it. One option per aspect is worn '
                'at a time. The game shows the base meshes, the chosen option mesh of each aspect, and hides every Body_* '
                'region listed in hides_body_regions of the chosen top and bottom. While a headwear option with '
                'hair_under_hat = true is worn, the hair option shows mesh_under_hat instead of mesh.',
        'files': {'blend': outs['blend'].name, 'fbx_base': outs['base'].name, 'fbx_parts': outs['parts'].name,
                  'validation': outs['validation'].name},
        'rig': {'name': RIG, 'bones': 65, 'axes': 'FBX -Z forward, Y up (as the NPC types)', 'fbx_clip': 'Idle only, like the NPC types; '
                'the game plays the shared clips (Animations/clips.json roles)'},
        'lod_naming': '<mesh>_LOD0 / _LOD1 / _LOD2 (Unity LOD import convention). Toggle all three LODs of an option together. '
                      'Suggested LODGroup screen heights as the NPC crowd: LOD0 > 0.10, LOD1 > 0.037, LOD2 > 0.01.',
        'unity_notes': ['Both FBX files carry the same rig with the same bone names and rest pose: either rebind the parts\' '
                        'SkinnedMeshRenderer.bones to the base skeleton by bone name, or instance the parts FBX under the '
                        'same Animator.',
                        'Colours are material tints: one material per slot shared by every option of an aspect '
                        '(PLAYER_Top_Main / _Trim / _Accent, PLAYER_Bottom_Main / _Trim / _Accent); set them per renderer '
                        '(MaterialPropertyBlock or material instance) from the swatch.',
                        'Skin: tint Buddy_Skin, Buddy_Skin_Nose, Buddy_Skin_Inner and Buddy_Eye_Rim from the skin tone '
                        '(Body_* regions and Face).',
                        'Face blend shapes as the NPCs: Blink, Blink_L, Blink_R, Surprised, Worried, Happy (GreyboxFace).',
                        'Hair, beards and headwear are rigid on mixamorig:Head; nothing is a Props_*Hand mesh (NpcHeldProps '
                        'must not touch the player).'],
        'base': {'meshes': REGIONS + BASE_FIXED + ['Face'], 'always_on': BASE_FIXED + ['Face'] + NEVER_HIDDEN,
                 'body_regions': [{'mesh': r, 'name_ru': d, 'tris': tri(r), 'hidden_by': [o[1] for o in opts if r in o[5]]}
                                  for r, d in PP.BODY_REGIONS],
                 'tris': {n: tri(n) for n in BASE_FIXED + ['Face']}},
        'aspects': aspects,
        'skin_tones': {'name_ru': 'Цвет кожи', 'default': PP.DEFAULT_SKIN,
                       'materials': {'skin': 'Buddy_Skin', 'nose': 'Buddy_Skin_Nose', 'inner': 'Buddy_Skin_Inner', 'rim': 'Buddy_Eye_Rim'},
                       'options': [{'id': k, 'name_ru': n, **{m: rgbhex(c) for m, c in cols.items()}} for k, n, cols in PP.SKIN_TONES]},
        'clothing_swatches': {'name_ru': 'Цвет одежды', 'applies_to': {'top': ['PLAYER_Top_Main', 'PLAYER_Top_Trim', 'PLAYER_Top_Accent'],
                                                                       'bottom': ['PLAYER_Bottom_Main', 'PLAYER_Bottom_Trim', 'PLAYER_Bottom_Accent']},
                              'default_top': PP.DEFAULTS['top_swatch'], 'default_bottom': PP.DEFAULTS['bottom_swatch'],
                              'options': [{'id': k, 'name_ru': n, 'main': rgbhex(m), 'trim': rgbhex(tr), 'accent': rgbhex(ac)}
                                          for k, n, m, tr, ac in PP.SWATCHES]},
        'fixed_materials': {f'PLAYER_{s}': rgbhex(v[0]) for s, v in PP.SLOTS.items() if not s.startswith(('Top_', 'Bottom_'))},
        'default_selection': PP.DEFAULTS,
        'outfit_tris': {'lod0': val['outfit_tris_lod0'], 'lod1': val['outfit_tris_lod1'], 'lod2': val['outfit_tris_lod2'],
                        'crowd_lod0_average': val['crowd_lod0_average']},
    }
    outs['manifest'].write_text(json.dumps(man, indent=1, ensure_ascii=False), encoding='utf-8')


main()
