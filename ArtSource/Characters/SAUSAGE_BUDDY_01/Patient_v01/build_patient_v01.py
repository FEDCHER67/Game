"""Sausage Buddy PATIENT v01: the bare operation-table body built from SAUSAGE_BUDDY_BASE_v04 (same rig and clips).

The clothed Buddy's Body is a hidden stand-in: separate torso/arm/leg tubes pushed into each other and no feet.
The patient replaces the torso, arms and legs with ONE continuous voxel-remeshed trunk (a readable belly for the
operation openings), adds simple cartoon feet, wears short trunks (rebuilt shorter than the BASE shorts), and marks the three
stage-1 incision sites with empties parented to the Spine bone.

Run:  blender -b SAUSAGE_BUDDY_BASE_v04.blend --python Patient_v01/build_patient_v01.py
Writes Patient_v01/SAUSAGE_BUDDY_PATIENT_v01.blend and .fbx next to this script. The BASE file is not modified.
"""
import json
import math
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

HERE = Path(__file__).resolve().parent
STEM = 'SAUSAGE_BUDDY_PATIENT_v01'
P = 'mixamorig:'
LEG_X = 0.100
VOXEL = 0.006
TARGET_TRUNK_TRIS = 7000
KEEP_OUTFIT = {'NPC_Shorts'}
# Incision sites on the belly (patient's left = +X). Kidneys low and to the sides, liver upper right.
SITES = {'INC_KIDNEY_L': (0.075, 0.935), 'INC_KIDNEY_R': (-0.075, 0.935), 'INC_LIVER': (-0.060, 1.035)}

scene = bpy.context.scene
rig = bpy.data.objects['Buddy_Rig_Mixamo65']
body = bpy.data.objects['Body']
outfit = bpy.data.objects['Outfit']
report = {'source': bpy.data.filepath, 'voxel_m': VOXEL}

# Build in the rest pose.
if rig.animation_data:
    rig.animation_data.action = None
for pb in rig.pose.bones:
    pb.matrix_basis.identity()
bpy.context.view_layer.update()

for name in ('Prop_Phone',):
    ob = bpy.data.objects.get(name)
    if ob:
        bpy.data.objects.remove(ob, do_unlink=True)


def islands(me):
    bm = bmesh.new()
    bm.from_mesh(me)
    bm.verts.ensure_lookup_table()
    seen, out = set(), []
    for v in bm.verts:
        if v.index in seen:
            continue
        stack, comp = [v], []
        seen.add(v.index)
        while stack:
            x = stack.pop()
            comp.append(x.index)
            for e in x.link_edges:
                o = e.other_vert(x)
                if o.index not in seen:
                    seen.add(o.index)
                    stack.append(o)
        out.append(comp)
    bm.free()
    return out


def classify(me, comp):
    co = [me.vertices[i].co for i in comp]
    xs = [abs(c.x) for c in co]
    zs = [c.z for c in co]
    if max(zs) > 1.70:
        return 'head'
    if min(zs) < 0.10:
        return 'leg'
    if min(zs) > 1.24:
        return 'face_feature'            # nose, ears
    if min(xs) > 0.60:
        return 'hand'                    # palm, fingers, thumb
    if max(xs) > 0.30:
        return 'arm'
    return 'torso'


# --- 1. split the stand-in body into kept parts and trunk parts
me = body.data
kinds = {}
for comp in islands(me):
    k = classify(me, comp)
    kinds.setdefault(k, []).extend(comp)
report['islands'] = {k: len(v) for k, v in kinds.items()}
trunk_verts = set(kinds.get('torso', []) + kinds.get('arm', []) + kinds.get('leg', []))

src = body.copy()                         # weight source: the original stand-in, untouched
src.data = body.data.copy()
src.name = 'WeightSource'
scene.collection.objects.link(src)

trunk = body.copy()
trunk.data = body.data.copy()
trunk.name = 'Trunk'
scene.collection.objects.link(trunk)
trunk.modifiers.clear()
trunk.vertex_groups.clear()
bm = bmesh.new()
bm.from_mesh(trunk.data)
bm.verts.ensure_lookup_table()
bmesh.ops.delete(bm, geom=[v for v in bm.verts if v.index not in trunk_verts], context='VERTS')

# --- 2. cartoon feet: a rounded wedge per side, pushed into the leg end so the remesh fuses them
for s in (1, -1):
    feet = bmesh.ops.create_uvsphere(bm, u_segments=20, v_segments=12, radius=1.0)
    vs = feet['verts']
    for v in vs:
        x, y, z = v.co
        z_scaled = z * 0.055 * (1.0 if z > 0 else 0.6)
        v.co = Vector((s * LEG_X + x * 0.058, -0.048 + y * 0.098, 0.050 + z_scaled))
    # slight upward toe and flat sole
    for v in vs:
        if v.co.z < 0.024:
            v.co.z = 0.024 - (0.024 - v.co.z) * 0.15
bm.to_mesh(trunk.data)
bm.free()

bpy.context.view_layer.objects.active = trunk
rm = trunk.modifiers.new('Remesh', 'REMESH')
rm.mode = 'VOXEL'
rm.voxel_size = VOXEL
rm.adaptivity = 0.0
rm.use_smooth_shade = True
sm = trunk.modifiers.new('Smooth', 'CORRECTIVE_SMOOTH')
sm.factor = 0.5
sm.iterations = 6
sm.smooth_type = 'LENGTH_WEIGHTED'
sm.use_only_smooth = True
bpy.ops.object.select_all(action='DESELECT')
trunk.select_set(True)
for m in list(trunk.modifiers):
    bpy.ops.object.modifier_apply(modifier=m.name)
tris_before = sum(len(p.vertices) - 2 for p in trunk.data.polygons)
# Quad remesh: even quads deform far better at knees/shoulders than a decimated voxel surface.
bpy.ops.object.quadriflow_remesh(target_faces=TARGET_TRUNK_TRIS // 2, use_preserve_sharp=False, use_preserve_boundary=False,
                                 use_mesh_symmetry=True, smooth_normals=True, mode='FACES', seed=7)
sm2 = trunk.modifiers.new('Smooth2', 'CORRECTIVE_SMOOTH')
sm2.factor = 0.4
sm2.iterations = 3
sm2.use_only_smooth = True
bpy.ops.object.modifier_apply(modifier=sm2.name)
for p in trunk.data.polygons:
    p.use_smooth = True
report['trunk_tris_remeshed'] = tris_before

# --- 3. skin weights: nearest-surface transfer from the stand-in, then explicit feet and crotch fixes
for g in src.vertex_groups:
    trunk.vertex_groups.new(name=g.name)
dt = trunk.modifiers.new('Weights', 'DATA_TRANSFER')
dt.object = src
dt.use_vert_data = True
dt.data_types_verts = {'VGROUP_WEIGHTS'}
dt.vert_mapping = 'POLYINTERP_NEAREST'
dt.layers_vgroup_select_src = 'ALL'
dt.layers_vgroup_select_dst = 'NAME'
bpy.ops.object.modifier_apply(modifier=dt.name)


def smoothstep(a, b, x):
    t = max(0.0, min(1.0, (x - a) / (b - a)))
    return t * t * (3 - 2 * t)


def setw(v, weights):
    for g in trunk.vertex_groups:
        g.remove([v.index])
    tot = sum(weights.values()) or 1.0
    for n, w in weights.items():
        if w > 1e-4:
            g = trunk.vertex_groups.get(n) or trunk.vertex_groups.new(name=n)
            g.add([v.index], w / tot, 'REPLACE')


for v in trunk.data.vertices:
    c = trunk.matrix_world @ v.co
    side = 'Left' if c.x >= 0 else 'Right'
    if c.z < 0.13 and abs(abs(c.x) - LEG_X) < 0.09:
        foot = smoothstep(0.125, 0.085, c.z)              # ankle blends from shin to foot
        toe = smoothstep(-0.085, -0.125, c.y) * foot
        setw(v, {P + side + 'Leg': 1 - foot, P + side + 'Foot': foot - toe, P + side + 'ToeBase': toe})
    elif 0.70 < c.z < 0.86 and abs(c.x) < 0.17:
        # crotch and hips: the stand-in had the leg tops inside the torso box, so nearest-surface weights are noisy here
        leg = smoothstep(0.84, 0.72, c.z) * smoothstep(0.015, 0.06, abs(c.x))
        setw(v, {P + 'Hips': 1 - leg, P + side + 'UpLeg': leg})

trunk.vertex_groups.active_index = 0
bpy.ops.object.mode_set(mode='WEIGHT_PAINT')
bpy.ops.object.vertex_group_smooth(group_select_mode='ALL', factor=0.5, repeat=5)
bpy.ops.object.vertex_group_limit_total(group_select_mode='ALL', limit=4)
bpy.ops.object.vertex_group_normalize_all(lock_active=False)
bpy.ops.object.mode_set(mode='OBJECT')

# --- 4. rebuild Body = kept parts (head, face features, hands) + new trunk
bm = bmesh.new()
bm.from_mesh(body.data)
bm.verts.ensure_lookup_table()
bmesh.ops.delete(bm, geom=[bm.verts[i] for i in trunk_verts], context='VERTS')
bm.to_mesh(body.data)
bm.free()
trunk.data.materials.clear()
for m in body.data.materials:
    trunk.data.materials.append(m)
skin_index = [m.name for m in body.data.materials].index('Buddy_Skin')
for p in trunk.data.polygons:
    p.material_index = skin_index
bpy.ops.object.select_all(action='DESELECT')
trunk.select_set(True)
body.select_set(True)
bpy.context.view_layer.objects.active = body
bpy.ops.object.join()
bpy.data.objects.remove(src, do_unlink=True)

# --- 5. outfit -> short trunks (Fedya 2026-10-15: shorter than the BASE shorts so the body reads longer)
import sys
sys.path.insert(0, str(HERE.parent))
import buddy_clothes as C
import buddy_geo as G
G.COLLECTION = scene.collection
shorts_mat = next(m for m in outfit.data.materials if m and m.name in KEEP_OUTFIT)
bpy.data.objects.remove(outfit, do_unlink=True)
# BASE shorts: waist .880 -> hem .600. Fedya 2026-10-15: low-rise trunks. The waistband drops to .800 so ~8 cm more belly
# shows, and the legs stay covered down to ~.625, so the visible legs read shorter and the body longer. The rig and the
# leg bones are unchanged (all Buddy clips keep working); radii follow the measured patient hips (rx .154, ry ~.096 at z .80).
TRUNK_WAIST = [(.800, .166, .110), (.792, .168, .111), (.776, .169, .109), (.760, .168, .104)]
TRUNK_LEGS = [(.715, .063), (.680, .061), (.640, .059), (.626, .055), (.632, .051)]
outfit = C.legwear('Shorts', TRUNK_WAIST, .735, TRUNK_LEGS, [shorts_mat], n=16, subdiv=1)
C.transfer(outfit, C.weight_source([body]))
outfit.parent = rig
outfit.matrix_parent_inverse.identity()
mod = outfit.modifiers.new('Armature', 'ARMATURE')
mod.object = rig
outfit.data.name = 'Shorts'
for p in outfit.data.polygons:
    p.use_smooth = True

# --- 6. incision site markers on the belly surface, parented to Spine (they follow the breathing/pose)
bvh = BVHTree.FromObject(body, bpy.context.evaluated_depsgraph_get())
spine = rig.data.bones[P + 'Spine']
report['sites'] = {}
for name, (x, z) in SITES.items():
    hit, normal, _, _ = bvh.ray_cast(Vector((x, -0.5, z)), Vector((0, 1, 0)))
    e = bpy.data.objects.new(name, None)
    e.empty_display_type = 'SINGLE_ARROW'
    e.empty_display_size = 0.05
    scene.collection.objects.link(e)
    e.matrix_world = normal.to_track_quat('Z', 'Y').to_matrix().to_4x4()
    e.matrix_world.translation = hit
    mw = e.matrix_world.copy()
    e.parent = rig
    e.parent_type = 'BONE'
    e.parent_bone = spine.name
    e.matrix_world = mw
    report['sites'][name] = {'position': [round(c, 4) for c in hit], 'normal': [round(c, 4) for c in normal]}

# --- 7. checks and output
def tris(ob):
    return sum(len(p.vertices) - 2 for p in ob.data.polygons)


report['meshes'] = {}
for ob in (body, bpy.data.objects['Face'], outfit):
    unweighted = sum(1 for v in ob.data.vertices if not any(g.weight > 1e-4 for g in v.groups))
    report['meshes'][ob.name] = {'triangles': tris(ob), 'unweighted_vertices': unweighted,
                                 'max_influences': max((len(v.groups) for v in ob.data.vertices), default=0)}
zs = [(body.matrix_world @ v.co).z for v in body.data.vertices]
report['height_m'] = round(max(zs), 4)
report['lowest_m'] = round(min(zs), 4)
report['actions'] = [a.name for a in bpy.data.actions]

out_blend = HERE / f'{STEM}.blend'
out_fbx = HERE / f'{STEM}.fbx'
bpy.ops.wm.save_as_mainfile(filepath=str(out_blend), copy=False)
bpy.ops.object.select_all(action='DESELECT')
for ob in [rig, body, bpy.data.objects['Face'], outfit] + [bpy.data.objects[n] for n in SITES]:
    ob.select_set(True)
bpy.context.view_layer.objects.active = rig
bpy.ops.export_scene.fbx(filepath=str(out_fbx), use_selection=True, object_types={'MESH', 'ARMATURE', 'EMPTY'}, add_leaf_bones=False,
                         use_armature_deform_only=False, bake_anim=False, axis_forward='-Z', axis_up='Y',
                         apply_unit_scale=True, use_mesh_modifiers=False)
(HERE / f'build_report_{STEM}.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print('[PATIENT]', json.dumps(report))
