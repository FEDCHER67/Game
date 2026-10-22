"""MW86_MonumentTramduro v02 - Vadim's TRAMDURO character cast in gold, with a crown, on the v01 podium.

  blender -b --factory-startup --python build_monument_tramduro_v02.py -- [--export] [--save] [--render DIR]

  --export  write Assets/OnlyVolunteers/Art/Props/MapW86_v01/Static/FBX/MW86_MonumentTramduro_A.fbx (same name / axes as v01)
  --save    write MW86_MonumentTramduro_v02.blend next to this script (statue only, no rig)
  --render  write review PNGs (eye level on a plain square) into DIR (add --chest for two close-ups instead)

Pipeline
  1. Append the original rigged TRAMDURO (Characters/SAUSAGE_BUDDY_01/Types/TRAMDURO/SAUSAGE_BUDDY_TRAMDURO_v01.blend),
     clear its animation and pose it as a monument: right arm raised in a wave (open palm forward), left fist on the hip,
     chest out, chin up, feet planted; light smile shape key.
  2. Evaluate the armature (pose applied, no rig left) and scale the figure so soles -> top of hair = FIG_H on the drum.
  3. Body + suit + hair: voxel remesh into one cast surface (no body under the suit, no intersecting layers), delete the
     shells / faces no ray from outside reaches (cavities, soles, hair under the crown band), collapse-decimate.
  4. Small crisp features stay separate low-poly overlays decimated on their own: eyes, nose, tie, lapels, buttons in
     gold; pupils, brows, mouth in the darker gold swatch (same atlas material) so the face reads from the square.
  5. Crown modelled to the posed head (band + beaded rim + 10 points with orbs + red / blue gem dots).
  6. Podium = the v01 builder code (props_city.monument) unchanged; whole model visibility-culled once more
     (hidden podium caps etc.), LOD0 <= 7000 tris, LOD1 ~35 %, UCX = v01 podium boxes + one figure box.
Export conventions are m2lib's (axis_forward -Z, axis_up Y, Blender -Y -> Unity +Z, pivot = base centre on the ground).
"""
import sys, math, json
from pathlib import Path
sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / '_common'))

import bpy, bmesh
from mathutils import Vector, Matrix, Quaternion
from mathutils.bvhtree import BVHTree
import m2lib as L

REPO = HERE.parents[4]
TRAM_BLEND = REPO / 'ArtSource/Characters/SAUSAGE_BUDDY_01/Types/TRAMDURO/SAUSAGE_BUDDY_TRAMDURO_v01.blend'
STATIC = REPO / 'Assets/OnlyVolunteers/Art/Props/MapW86_v01/Static'
FBX = STATIC / 'FBX/MW86_MonumentTramduro_A.fbx'
TEX_DIR = STATIC / 'Textures'
BLEND_OUT = HERE / 'MW86_MonumentTramduro_v02.blend'
ROOT = 'MW86_MonumentTramduro_A'

ARGS = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
EXPORT, SAVE = '--export' in ARGS, '--save' in ARGS
RENDER_DIR = Path(ARGS[ARGS.index('--render') + 1]) if '--render' in ARGS else None

DRUM_TOP = 2.1            # v01 drum + cornice top (figure stands here)
FIG_H = 8.2               # soles -> top of the hair, metres
LOD0_MAX = 7000
LOD1_SHARE = .35
EXPRESSION = {'Happy': .55}
VOXEL = .02               # voxel size (m, statue scale) of the cast surface
SOLIDIFY = .006           # rest-scale thickness given to the open suit sheets so the voxeliser keeps them
SKIP = {'Buddy_Eye_Shine', 'Buddy_Eye_Rim', 'TRAMDURO_Pin_Blue', 'TRAMDURO_Pin_Red'}   # highlight cards, thin eye rims, flag pin (no logos)
HAIR = {'TRAMDURO_Hair', 'TRAMDURO_Hair_Streak'}
SOLE = {'TRAMDURO_Shoe_Sole', 'TRAMDURO_Shoes'}
# overlay group: (source materials, atlas swatch, (tris LOD0, tris LOD1), smooth organic normals, inflate m)
# hand_r / hand_l take the Body skin faces skinned to the hand + finger bones instead of a material
OVERLAYS = {
    'eyes':    ({'Buddy_Eye_White'}, 'gold', (200, 80), True, 0.0),
    'pupils':  ({'Buddy_Pupil'}, 'gold_dark', (56, 24), True, .004),
    'brows':   ({'Buddy_Brow'}, 'gold_dark', (40, 16), True, .006),
    'mouth':   ({'Buddy_Mouth'}, 'gold_dark', (44, 16), True, .004),
    'nose':    ({'Buddy_Skin_Nose'}, 'gold', (90, 40), True, 0.0),
    'tie':     ({'TRAMDURO_Tie'}, 'gold', (90, 36), False, .03),
    'lapels':  ({'TRAMDURO_Lapel'}, 'gold', (110, 44), False, .02),
    'buttons': ({'TRAMDURO_Button'}, 'gold', (16, 0), False, .02),
    'hand_r':  (set(), 'gold', (190, 70), True, 0.0),
    'hand_l':  (set(), 'gold', (150, 60), True, 0.0),
}


# ------------------------------------------------------------------ source + pose
def reset_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.unit_settings.system = 'METRIC'; sc.unit_settings.scale_length = 1.0
    return sc


def load_tramduro(sc):
    with bpy.data.libraries.load(str(TRAM_BLEND), link=False) as (src, dst):
        dst.objects = [n for n in src.objects if n in ('Body', 'Face', 'Outfit', 'Buddy_Rig_Mixamo65')]
    for o in dst.objects:
        sc.collection.objects.link(o)
    objs = {o.name: o for o in dst.objects}
    sol = objs['Outfit'].modifiers.new('statue_thickness', 'SOLIDIFY')   # after the armature modifier
    sol.thickness = SOLIDIFY; sol.offset = -1; sol.use_rim = True
    sol.show_viewport = sol.show_render = False
    return objs


def pose_monument(objs):
    arm, face = objs['Buddy_Rig_Mixamo65'], objs['Face']
    if arm.animation_data:
        arm.animation_data.action = None
    sk = face.data.shape_keys
    if sk and sk.animation_data:
        sk.animation_data.action = None
    if sk:
        for k in sk.key_blocks[1:]:
            k.value = EXPRESSION.get(k.name, 0.0)
    for pb in arm.pose.bones:
        pb.location = (0, 0, 0); pb.rotation_quaternion = (1, 0, 0, 0); pb.rotation_euler = (0, 0, 0); pb.scale = (1, 1, 1)

    def upd():
        bpy.context.view_layer.update()
    upd()
    P = arm.pose.bones

    def B(n):
        return P['mixamorig:' + n]

    def rot(pb, q):                       # rotate a pose bone (and its children) about its head, armature space
        M = pb.matrix.copy(); h = M.translation.copy()
        pb.matrix = Matrix.Translation(h) @ q.to_matrix().to_4x4() @ Matrix.Translation(-h) @ M
        upd()

    def aim(pb, d):
        rot(pb, (pb.tail - pb.head).normalized().rotation_difference(Vector(d).normalized()))

    def twist_palm(fore, hand, want):     # roll the forearm so the palm (hand bone local Z) faces `want`
        ax = (fore.tail - fore.head).normalized()
        pn = hand.matrix.to_3x3().col[2].normalized()
        w = Vector(want)
        pp = (pn - ax * pn.dot(ax)).normalized(); wp = (w - ax * w.dot(ax)).normalized()
        s = 1 if ax.dot(pp.cross(wp)) > 0 else -1
        rot(fore, Quaternion(ax, s * pp.angle(wp)))

    X, Y, Z = Vector((1, 0, 0)), Vector((0, 1, 0)), Vector((0, 0, 1))
    # proud: chest out, chin up (front = Blender -Y, character right = -X)
    rot(B('Spine1'), Quaternion(X, math.radians(-3)))
    rot(B('Spine2'), Quaternion(X, math.radians(-3)))
    rot(B('Head'), Quaternion(X, math.radians(-6)))
    # feet planted a little apart, toes slightly out, soles flat
    for side, s in (('Right', 1), ('Left', -1)):
        rot(B(side + 'UpLeg'), Quaternion(Y, math.radians(4 * s)))
        rot(B(side + 'Foot'), Quaternion(Y, math.radians(-4 * s)))
        rot(B(side + 'Foot'), Quaternion(Z, math.radians(-8 * s)))
    # right arm raised high in a wave, open palm to the people
    aim(B('RightArm'), (-0.62, -0.22, 0.75))
    aim(B('RightForeArm'), (-0.14, -0.22, 1.0))
    aim(B('RightHand'), (-0.10, -0.16, 1.0))
    twist_palm(B('RightForeArm'), B('RightHand'), (0, -1, 0))
    # left fist on the hip, elbow out
    aim(B('LeftArm'), (0.62, 0.25, -0.75))
    el = B('LeftForeArm').head.copy()
    aim(B('LeftForeArm'), Vector((0.285, 0.0, 0.865)) - el)
    aim(B('LeftHand'), (-0.35, -0.55, -0.75))
    for f in ('Index', 'Middle', 'Ring', 'Pinky'):
        for k, a in ((1, 60), (2, 80), (3, 55)):
            hand_x = B('LeftHand').matrix.to_3x3().col[0].normalized()
            rot(B(f'LeftHand{f}{k}'), Quaternion(hand_x, math.radians(a)))
    return {n: (B(n).head.copy(), B(n).tail.copy()) for n in ('Head', 'RightArm', 'RightHand', 'LeftHand')}


# ------------------------------------------------------------------ bake
def hand_tags(body):
    """Body vertex index -> 'R' / 'L' when a hand or finger bone moves it at all (the wrist blend zone reaches into
    the cuff, so the separate hand piece plugs the sleeve without a gap)."""
    names = {g.index: g.name for g in body.vertex_groups}
    tags = {}
    for v in body.data.vertices:
        for g in v.groups:
            n = names.get(g.group, '')
            if g.weight > .02 and ('RightHand' in n or 'LeftHand' in n):
                tags[v.index] = 'R' if 'RightHand' in n else 'L'
                break
    return tags


def classify(oname, mn, vids, tags):
    """Which piece a source face goes to: None (dropped), 'cast' or an OVERLAYS group."""
    if mn in SKIP:
        return None
    if oname == 'Body' and mn == 'Buddy_Skin':
        for side, g in (('R', 'hand_r'), ('L', 'hand_l')):
            if 2 * sum(1 for i in vids if tags.get(i) == side) > len(vids):
                return g
    for g, spec in OVERLAYS.items():
        if mn in spec[0]:
            return g
    return 'cast'


def bake(objs, want, tags, solid=False):
    """Evaluated (posed) Body + Outfit + Face faces classified as `want` -> one triangulated bmesh.
    face layer 'part': 1 hair, 2 shoe, 0 other. solid=True evaluates the suit with its statue thickness."""
    objs['Outfit'].modifiers['statue_thickness'].show_viewport = solid
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    bm = bmesh.new()
    lay_part = bm.faces.layers.int.new('part')
    for name in ('Body', 'Outfit', 'Face'):
        ob = objs[name]
        me = bpy.data.meshes.new_from_object(ob.evaluated_get(dg), depsgraph=dg)
        me.transform(ob.matrix_world)
        mats = [m.name if m else '' for m in me.materials]
        tmp = bmesh.new(); tmp.from_mesh(me)
        vmap = {}
        for f in tmp.faces:
            mn = mats[f.material_index] if f.material_index < len(mats) else ''
            if classify(name, mn, [v.index for v in f.verts], tags) != want:
                continue
            vs = []
            for v in f.verts:
                nv = vmap.get(v)
                if nv is None:
                    nv = vmap[v] = bm.verts.new(v.co)
                vs.append(nv)
            try:
                nf = bm.faces.new(vs)
            except ValueError:
                continue
            nf[lay_part] = 1 if mn in HAIR else 2 if mn in SOLE else 0
        tmp.free(); bpy.data.meshes.remove(me)
    # skinning warps quads (twisted sleeve): triangulate so every face is planar for the visibility rays
    bmesh.ops.triangulate(bm, faces=bm.faces[:], quad_method='BEAUTY', ngon_method='BEAUTY')
    bm.normal_update()
    return bm


def statue_matrix(bm):
    lay_part = bm.faces.layers.int['part']
    zmin = min(v.co.z for v in bm.verts)
    hair_top = max(v.co.z for f in bm.faces if f[lay_part] == 1 for v in f.verts)
    sole = [v.co for f in bm.faces if f[lay_part] == 2 for v in f.verts]
    cx = (min(c.x for c in sole) + max(c.x for c in sole)) / 2
    cy = (min(c.y for c in sole) + max(c.y for c in sole)) / 2
    s = FIG_H / (hair_top - zmin)
    return Matrix.Translation((-cx * s, -cy * s, DRUM_TOP - zmin * s)) @ Matrix.Diagonal((s, s, s, 1)), s


# ------------------------------------------------------------------ asset with a frame + organic normals
class FramedAsset(L.Asset):
    """m2lib Asset whose parts can be placed in an arbitrary rigid frame (the tilted head). Faces flagged 'organic'
    (cast figure, eyes, nose) get plain smooth normals after m2lib's weighted-normal pass; hard surfaces keep m2lib's."""
    frame = None

    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        self.organic = self.bm.faces.layers.int.new('organic')

    def _add(self, pb, col, M, *a, **k):
        if self.frame is not None:
            M = self.frame @ M
        super()._add(pb, col, M, *a, **k)

    def to_object(self, name, collection, sharp_deg=50.0):
        ob = super().to_object(name, collection, sharp_deg)
        me = ob.data
        org = [d.value for d in me.attributes['organic'].data]
        vn = [Vector() for _ in me.vertices]
        for p in me.polygons:
            if not org[p.index]:
                continue
            n = p.normal; vs = p.vertices; k = len(vs)
            for i in range(k):
                a = me.vertices[vs[i - 1]].co; b = me.vertices[vs[i]].co; c = me.vertices[vs[(i + 1) % k]].co
                vn[vs[i]] += n * (a - b).angle(c - b, 0.0)
        cur = [Vector(cn.vector) for cn in me.corner_normals]
        for p in me.polygons:
            if org[p.index]:
                for li in p.loop_indices:
                    v = vn[me.loops[li].vertex_index]
                    if v.length > 1e-8:
                        cur[li] = v.normalized()
        me.normals_split_custom_set(cur)
        me.attributes.remove(me.attributes['organic'])
        return ob


def add_mesh_swatch(A, me, col, organic):
    """Append a mesh to an m2lib Asset with one atlas swatch."""
    pb = bmesh.new(); pb.from_mesh(me)
    u = L.uv_of(col)
    vmap = {v: A.bm.verts.new(v.co) for v in pb.verts}
    for f in pb.faces:
        try:
            nf = A.bm.faces.new([vmap[v] for v in f.verts])
        except ValueError:
            continue
        nf.smooth = True; nf[A.facet] = 0; nf[A.organic] = 1 if organic else 0
        for l in nf.loops:
            l[A.uv].uv = u
    pb.free()


def asset_tris(A):
    return sum(len(f.verts) - 2 for f in A.bm.faces)


# ------------------------------------------------------------------ crown
def fit_crown(bm, bones, M):
    """Crown frame (origin = centre of the band bottom, Z = head axis, -Y = front) and the head radius at the band."""
    lay_part = bm.faces.layers.int['part']
    h0, h1 = M @ bones['Head'][0], M @ bones['Head'][1]
    U = (h1 - h0).normalized()
    Yl = Vector((0, 1, 0)); Yl = (Yl - U * Yl.dot(U)).normalized()
    Xl = Yl.cross(U).normalized()
    hair = {v for f in bm.faces if f[lay_part] == 1 for v in f.verts}
    h_top = max((v.co - h0).dot(U) for v in hair)
    h_b = h_top - .66                                # band bottom this far below the top of the hair
    pts = []
    for v in bm.verts:
        d = v.co - h0
        h = d.dot(U)
        if h_b - .05 <= h <= h_b + .45:
            p = (d.dot(Xl), d.dot(Yl))
            if p[0] * p[0] + p[1] * p[1] < 1.6 ** 2:   # skip the raised hand
                pts.append(p)
    cx = (min(p[0] for p in pts) + max(p[0] for p in pts)) / 2
    cy = (min(p[1] for p in pts) + max(p[1] for p in pts)) / 2
    r = max(math.hypot(p[0] - cx, p[1] - cy) for p in pts)
    o = h0 + U * h_b + Xl * cx + Yl * cy
    return Matrix.Translation(o) @ Matrix((Xl, Yl, U)).transposed().to_4x4(), r


def crown(A, r_in):
    """Classic royal crown: flared band with a beaded rim, 10 points (5 tall with orbs, 5 short), red / blue gem dots."""
    R0 = r_in + .06
    R1 = R0 * 1.08
    H, t = .46, .07
    A.lathe([(R0, 0), (R1, H), (R1 - t, H), (R0 - t, 0)], (0, 0, 0), 'gold', n=24, cap_top=False, cap_bottom=False)
    A.torus(R0 + .012, .055, (0, 0, .02), 'gold', n=24, m=4)
    n = 10
    for i in range(n):
        a = math.pi * 1.5 + i * math.tau / n           # i = 0 at the front (-Y)
        tall = i % 2 == 0
        hp = .78 if tall else .40
        w = 2 * R1 * math.sin(math.pi / n) * 1.04
        poly = [(-w / 2, 0), (w / 2, 0), (w * .16, hp * .55), (0, hp), (-w * .16, hp * .55)]
        pb = bmesh.new()
        bot = [pb.verts.new((x, -t / 2, y)) for x, y in poly]
        top = [pb.verts.new((x, t / 2, y)) for x, y in poly]
        pb.faces.new(bot); pb.faces.new(list(reversed(top)))
        for k in range(len(poly)):
            j = (k + 1) % len(poly)
            pb.faces.new((bot[k], top[k], top[j], bot[j]))
        bmesh.ops.recalc_face_normals(pb, faces=pb.faces)
        rc = R1 - t / 2
        A._add(pb, 'gold', Matrix.Translation((math.cos(a) * rc, math.sin(a) * rc, H - .01)) @ Matrix.Rotation(a + math.pi / 2, 4, 'Z'))
        if tall:
            A.sphere(.11, (math.cos(a) * rc, math.sin(a) * rc, H - .01 + hp + .07), 'gold', seg=8, rings=4)
        # cabochon gem on the band (low dome, open back against the band)
        gr = .085 if tall else .07
        rg = (R0 + R1) / 2 - t / 2 + .005
        Mg = Matrix.Translation((math.cos(a) * rg, math.sin(a) * rg, H * .5)) @ Matrix.Rotation(a, 4, 'Z') @ \
            Matrix.Rotation(math.pi / 2, 4, 'Y')
        pg = bmesh.new()
        ring0 = [pg.verts.new((gr * math.cos(k * math.tau / 6), gr * math.sin(k * math.tau / 6), 0)) for k in range(6)]
        ring1 = [pg.verts.new((.7 * gr * math.cos(k * math.tau / 6), .7 * gr * math.sin(k * math.tau / 6), .09)) for k in range(6)]
        tip = pg.verts.new((0, 0, .12))
        for k in range(6):
            j = (k + 1) % 6
            pg.faces.new((ring0[k], ring0[j], ring1[j], ring1[k]))
            pg.faces.new((ring1[k], ring1[j], tip))
        bmesh.ops.recalc_face_normals(pg, faces=pg.faces)
        A._add(pg, 'red' if tall else 'blue', Mg)


# ------------------------------------------------------------------ visibility clean-up / remesh / decimation
def fib_dirs(n):
    g = math.pi * (3 - math.sqrt(5)); out = []
    for i in range(n):
        z = 1 - 2 * (i + .5) / n; r = math.sqrt(max(0, 1 - z * z))
        out.append(Vector((r * math.cos(g * i), r * math.sin(g * i), z)))
    return out


def cull_hidden(bm, extra_bms, floor, eps=.0015, ndirs=160, multi=False):
    """Delete faces of bm that no ray from outside reaches (occluders: bm, extra_bms and a floor disc (z, radius)).
    Faces reachable only from their back are flipped (the source suit has a few inverted normals: harmless in Blender,
    invisible in Unity). multi=True also tests points next to every corner and edge middle (a face dies only if all
    are hidden, so big caps half under the next podium tier survive).
    Whole shells with no visible sample are dropped first (voxel cavities). Returns (deleted, flipped)."""
    bm.normal_update(); bm.verts.index_update(); bm.faces.index_update()
    V = [v.co.copy() for v in bm.verts]; F = [[v.index for v in f.verts] for f in bm.faces]
    for e in extra_bms:
        e.verts.index_update(); off = len(V)
        V += [v.co.copy() for v in e.verts]; F += [[v.index + off for v in f.verts] for f in e.faces]
    zf, rf = floor; k = len(V); nd = 48
    V += [Vector((rf * math.cos(i * math.tau / nd), rf * math.sin(i * math.tau / nd), zf)) for i in range(nd)]
    F.append(list(range(k, k + nd)))
    tree = BVHTree.FromPolygons(V, F)
    dirs = fib_dirs(ndirs)

    def escapes(o, n):
        for d in dirs:
            if d.dot(n) > .05 and tree.ray_cast(o, d)[0] is None:
                return True
        return False

    def samples(f):
        c = f.calc_center_median()
        if not multi:
            return [c]
        return [c] + [c + (v.co - c) * .98 for v in f.verts] + [c + ((e.verts[0].co + e.verts[1].co) / 2 - c) * .98 for e in f.edges]

    dead, flip, todo, seen = [], [], [], set()
    for f0 in bm.faces:                               # connected shells
        if f0.index in seen:
            continue
        shell, stack = [], [f0]; seen.add(f0.index)
        while stack:
            g = stack.pop(); shell.append(g)
            for e in g.edges:
                for h in e.link_faces:
                    if h.index not in seen:
                        seen.add(h.index); stack.append(h)
        step = max(1, len(shell) // 40)
        if any(escapes(g.calc_center_median() + g.normal * eps, g.normal) or
               escapes(g.calc_center_median() - g.normal * eps, -g.normal) for g in shell[::step] if g.normal.length > .5):
            todo += shell
        else:
            dead += shell
    for f in todo:
        n = f.normal.copy()
        if n.length < .5:
            dead.append(f); continue
        c = f.calc_center_median()
        if c.z < zf + .005 and n.z < -.9:             # faces lying on the floor (soles, podium bottom caps)
            dead.append(f); continue
        pts = samples(f)
        if any(escapes(p + n * eps, n) for p in pts):
            continue
        if any(escapes(p - n * eps, -n) for p in pts):
            flip.append(f)
        else:
            dead.append(f)
    bmesh.ops.reverse_faces(bm, faces=flip)
    bmesh.ops.delete(bm, geom=dead, context='FACES')
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context='VERTS')
    bm.normal_update()
    return len(dead), len(flip)


def voxel_remesh(bm, voxel):
    me = bpy.data.meshes.new('vox_src'); bm.to_mesh(me)
    ob = bpy.data.objects.new('vox_src', me); bpy.context.scene.collection.objects.link(ob)
    mod = ob.modifiers.new('rm', 'REMESH'); mod.mode = 'VOXEL'; mod.voxel_size = voxel; mod.adaptivity = 0.0
    dg = bpy.context.evaluated_depsgraph_get()
    out = bpy.data.meshes.new_from_object(ob.evaluated_get(dg), depsgraph=dg)
    bpy.data.objects.remove(ob); bpy.data.meshes.remove(me)
    bm2 = bmesh.new(); bm2.from_mesh(out); bpy.data.meshes.remove(out)
    for _ in range(2):                                    # soften the voxel staircase
        bmesh.ops.smooth_vert(bm2, verts=bm2.verts[:], factor=.5, use_axis_x=True, use_axis_y=True, use_axis_z=True)
    bmesh.ops.triangulate(bm2, faces=bm2.faces[:], quad_method='BEAUTY', ngon_method='BEAUTY')
    bm2.normal_update()
    return bm2


def tris_of(me):
    return sum(len(p.vertices) - 2 for p in me.polygons)


def decimate_bm(bm, target, name):
    """Collapse-decimate a copy of bm to <= target tris (binary search on the ratio) -> new mesh datablock."""
    me = bpy.data.meshes.new(name); bm.to_mesh(me)
    if tris_of(me) <= target:
        return me
    ob = bpy.data.objects.new(name, me); bpy.context.scene.collection.objects.link(ob)
    n0 = tris_of(me)
    if n0 > target * 6:                                   # coarse pre-pass so the search below stays fast
        pre = ob.modifiers.new('pre', 'DECIMATE'); pre.decimate_type = 'COLLAPSE'; pre.ratio = target * 6 / n0
        dg = bpy.context.evaluated_depsgraph_get()
        m2 = bpy.data.meshes.new_from_object(ob.evaluated_get(dg), depsgraph=dg)
        ob.modifiers.clear(); ob.data = m2; bpy.data.meshes.remove(me); me = m2
    mod = ob.modifiers.new('dec', 'DECIMATE'); mod.decimate_type = 'COLLAPSE'; mod.use_collapse_triangulate = True
    lo, hi = 0.0, 1.0
    for _ in range(16):
        mod.ratio = (lo + hi) / 2
        dg = bpy.context.evaluated_depsgraph_get()
        if tris_of(ob.evaluated_get(dg).data) > target:
            hi = mod.ratio
        else:
            lo = mod.ratio
    mod.ratio = lo
    dg = bpy.context.evaluated_depsgraph_get()
    out = bpy.data.meshes.new_from_object(ob.evaluated_get(dg), depsgraph=dg)
    bpy.data.objects.remove(ob); bpy.data.meshes.remove(me)
    out.name = name
    return out


# ------------------------------------------------------------------ podium (identical to v01 props_city.monument)
def podium(A):
    for i, (r, z) in enumerate(((4.4, 0), (3.95, .3), (3.5, .6))):
        A.cyl(r, .3, (0, 0, z), 'granite_dark' if i % 2 == 0 else 'granite', n=32, bevel=.03)
    A.cyl(2.7, 1.1, (0, 0, .9), 'granite_dark', n=32, bevel=.05)
    A.cyl(2.85, .2, (0, 0, 1.9), 'granite', n=32, bevel=.04)
    A.cyl(2.75, .12, (0, 0, .9), 'granite', n=32, bevel=.02)
    A.box((1.2, .04, .45), (0, -2.71, 1.45), 'gold_dark', bevel=0, detail=True)        # blank plaque (no text)


def podium_colliders(A):
    for r, z, h in ((4.4, 0, .3), (3.95, .3, .3), (3.5, .6, .3)):
        A.col_box((r * 1.6, r * 1.6, z + h), (0, 0, (z + h) / 2))
    A.col_box((4.4, 4.4, 2.1), (0, 0, 1.05))


# ------------------------------------------------------------------ main
def main():
    sc = reset_scene()
    objs = load_tramduro(sc)
    bones = pose_monument(objs)
    tags = hand_tags(objs['Body'])
    body = bake(objs, 'cast', tags, solid=True)
    ovl_src = {g: bake(objs, g, tags) for g in OVERLAYS}
    M, s = statue_matrix(body)
    for b in [body] + list(ovl_src.values()):
        bmesh.ops.transform(b, matrix=M, verts=b.verts)
        b.normal_update()
    for g, b in ovl_src.items():                          # lift thin reliefs off the cast surface
        if OVERLAYS[g][4]:
            for v in b.verts:
                v.co += v.normal * OVERLAYS[g][4]
            b.normal_update()
    raw_tris = sum(len(f.verts) - 2 for b in [body] + list(ovl_src.values()) for f in b.faces)
    frame, r_head = fit_crown(body, bones, M)
    shoulder_z = (M @ bones['RightArm'][0]).z
    for o in list(objs.values()):                         # the source rig is no longer needed
        bpy.data.objects.remove(o)
    bpy.data.orphans_purge(do_recursive=True)
    L.make_material({k: TEX_DIR / f'MW86_StaticPalette_v01_{k}.png' for k in ('Albedo', 'MetallicSmoothness', 'Emission')})

    # one cast surface for body + suit + hair
    cast = voxel_remesh(body, VOXEL)
    vox_tris = sum(len(f.verts) - 2 for f in cast.faces)
    probe = FramedAsset('crown_probe'); probe.frame = frame
    crown(probe, r_head)
    cast_cull = cull_hidden(cast, [probe.bm], (DRUM_TOP, 2.9), eps=.004, ndirs=96)
    probe.bm.free()
    cast_tris = sum(len(f.verts) - 2 for f in cast.faces)

    def assemble(lod, fig_me, ovl):
        A = FramedAsset(ROOT, lod=lod)
        podium(A)
        A.frame = frame; crown(A, r_head); A.frame = None
        for g, me in ovl.items():
            add_mesh_swatch(A, me, OVERLAYS[g][1], OVERLAYS[g][3])
        if fig_me is not None:
            add_mesh_swatch(A, fig_me, 'gold', True)
        cull_hidden(A.bm, [], (0.0, 40.0), multi=True)
        return A

    def fit_lod(lod, total_max):
        ovl = {g: decimate_bm(ovl_src[g], spec[2][lod], f'{g}{lod}') for g, spec in OVERLAYS.items() if spec[2][lod]}
        A = assemble(lod, None, ovl); fixed = asset_tris(A); A.bm.free()
        target = total_max - fixed - 30
        best = None
        for _ in range(4):
            fig = decimate_bm(cast, target, f'fig{lod}')
            A = assemble(lod, fig, ovl); t = asset_tris(A)
            if t <= total_max:
                if best:
                    best[0].bm.free(); bpy.data.meshes.remove(best[1])
                best = (A, fig, t)
                if total_max - t < 60:
                    break
                target += total_max - t - 30
            else:
                A.bm.free(); bpy.data.meshes.remove(fig)
                target -= t - total_max + 30
        for me in ovl.values():
            bpy.data.meshes.remove(me)
        return best[0], best[1], fixed

    A0, fig0, fixed0 = fit_lod(0, LOD0_MAX)
    # colliders: the v01 podium layout + one box around the figure (drum top -> crown top, body below the shoulders)
    podium_colliders(A0)
    body_pts = [v.co for v in fig0.vertices if v.co.z < shoulder_z]
    bx0, bx1 = min(p.x for p in body_pts), max(p.x for p in body_pts)
    by0, by1 = min(p.y for p in body_pts), max(p.y for p in body_pts)
    ob0 = A0.to_object(ROOT + '_LOD0', sc.collection)
    t0 = L.tri_count(ob0)
    mn0, mx0 = L.bounds([ob0])
    A0.col_box((bx1 - bx0, by1 - by0, mx0.z - DRUM_TOP), ((bx0 + bx1) / 2, (by0 + by1) / 2, (DRUM_TOP + mx0.z) / 2))
    ucx = A0.ucx_objects(ROOT, sc.collection)
    A1, fig1, fixed1 = fit_lod(1, int(round(t0 * LOD1_SHARE)))
    ob1 = A1.to_object(ROOT + '_LOD1', sc.collection)
    t1 = L.tri_count(ob1)
    root = bpy.data.objects.new(ROOT, None); sc.collection.objects.link(root); root.empty_display_size = .5
    for o in [ob0, ob1] + ucx:
        o.parent = root
    for me in (fig0, fig1):
        bpy.data.meshes.remove(me)
    for b in [body, cast] + list(ovl_src.values()):
        b.free()

    info = dict(scale=round(s, 4), raw_tris=raw_tris, voxel_tris=vox_tris, cast_cull=cast_cull, cast_tris=cast_tris,
                fixed_lod0=fixed0, fixed_lod1=fixed1, tris_lod0=t0, tris_lod1=t1,
                bounds_min=[round(v, 3) for v in mn0], bounds_max=[round(v, 3) for v in mx0],
                crown_head_r=round(r_head, 3), ucx=len(ucx),
                figure_box=[round(bx1 - bx0, 2), round(by1 - by0, 2), round(mx0.z - DRUM_TOP, 2)])
    print('[V02] ' + json.dumps(info))
    if EXPORT:
        L.export_fbx([root, ob0, ob1] + ucx, FBX)
        print('[V02] exported', FBX)
    if SAVE:
        bpy.ops.wm.save_as_mainfile(filepath=str(BLEND_OUT), compress=True)
        print('[V02] saved', BLEND_OUT)
    if RENDER_DIR:
        render_review(sc, [ob1] + ucx, mx0)


# ------------------------------------------------------------------ review renders
def render_review(sc, hide, mx):
    RENDER_DIR.mkdir(parents=True, exist_ok=True)
    for o in hide:
        o.hide_render = True
    sc.render.engine = 'BLENDER_EEVEE'
    try:
        sc.eevee.use_raytracing = True
    except Exception:
        pass
    sc.render.film_transparent = False
    try:
        sc.view_settings.view_transform = 'AgX'
        sc.view_settings.look = 'AgX - Medium High Contrast'
    except TypeError:
        pass
    w = bpy.data.worlds.new('REVIEW_Sky'); sc.world = w
    nt = w.node_tree; bg = next(n for n in nt.nodes if n.type == 'BACKGROUND')
    tc = nt.nodes.new('ShaderNodeTexCoord'); sep = nt.nodes.new('ShaderNodeSeparateXYZ')
    ramp = nt.nodes.new('ShaderNodeValToRGB')
    nt.links.new(tc.outputs['Generated'], sep.inputs[0]); nt.links.new(sep.outputs['Z'], ramp.inputs[0])
    nt.links.new(ramp.outputs['Color'], bg.inputs['Color'])
    ramp.color_ramp.elements[0].position = .5; ramp.color_ramp.elements[0].color = (.42, .40, .38, 1)
    ramp.color_ramp.elements[1].position = 1.0; ramp.color_ramp.elements[1].color = (.30, .48, .85, 1)
    e = ramp.color_ramp.elements.new(.53); e.color = (.82, .86, .92, 1)
    bg.inputs['Strength'].default_value = 1.0
    sun = bpy.data.lights.new('REVIEW_Sun', 'SUN'); sun.energy = 4.0; sun.angle = math.radians(2)
    so = bpy.data.objects.new('REVIEW_Sun', sun); sc.collection.objects.link(so)
    so.rotation_euler = Vector((.45, .75, -.55)).normalized().to_track_quat('-Z', 'Y').to_euler()
    gm = bpy.data.materials.new('REVIEW_Paving')
    bsdf = next(n for n in gm.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
    bsdf.inputs['Base Color'].default_value = (.36, .35, .33, 1); bsdf.inputs['Roughness'].default_value = .9
    bpy.ops.mesh.primitive_plane_add(size=300)
    g = bpy.context.active_object; g.name = 'REVIEW_Ground'; g.data.materials.append(gm)
    hm = bpy.data.materials.new('REVIEW_Human')
    hb = next(n for n in hm.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
    hb.inputs['Base Color'].default_value = (.15, .25, .5, 1)
    bpy.ops.mesh.primitive_cylinder_add(radius=.25, depth=1.8, location=(5.6, -3.2, .9))   # 1.8 m player for scale
    bpy.context.active_object.data.materials.append(hm)
    cam_d = bpy.data.cameras.new('REVIEW_Cam')
    cam = bpy.data.objects.new('REVIEW_Cam', cam_d); sc.collection.objects.link(cam); sc.camera = cam
    sc.render.resolution_x, sc.render.resolution_y = 820, 1100
    eye = 1.7
    views = (('a_front34', (-.5, -.87), 15.0, 30, 5.6),
             ('b_side', (1.0, -.05), 15.0, 30, 5.6),
             ('c_head', (-.25, -.97), 26.0, 105, mx.z - 1.6))
    if '--chest' in ARGS:
        views = (('d_chest', (-.15, -.99), 26.0, 200, 7.3), ('e_chest2', (.5, -.86), 26.0, 200, 7.3))
    for name, (dx, dy), dist, lens, look_z in views:
        d = Vector((dx, dy, 0)).normalized()
        cam.location = Vector((d.x * dist, d.y * dist, eye))
        cam.rotation_euler = (Vector((0, 0, look_z)) - cam.location).to_track_quat('-Z', 'Y').to_euler()
        cam_d.lens = lens; cam_d.clip_end = 500
        sc.render.filepath = str(RENDER_DIR / f'{name}.png')
        bpy.ops.render.render(write_still=True)


main()
