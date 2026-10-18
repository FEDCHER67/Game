"""Sausage Buddy PATIENT v02: v01 body, rig, skin weights and clips unchanged; new anatomical organ markers.

v01 put three incision markers ON the belly skin. v02 moves INC_KIDNEY_L / INC_KIDNEY_R / INC_LIVER to the organ
CENTRES of a believable abdominal layout (scaled from human anatomy to Buddy's torso) and adds:
  INC_ABDOMEN          the one big opening: on the skin, belly midline, centre of the opening and of the cut guide
  GUIDE_BELLY_START    head end of the midline cut guide (on the skin)
  GUIDE_BELLY_END      pubic end of the midline cut guide (on the skin)
All markers are bone-parented to mixamorig:Spine (as in v01). Marker axes: +Z = skin normal (out of the body, the pull
direction), +Y = toward the head (kidneys: the organ's long axis, upper pole), +X = patient's left (liver: its long axis).

Run (v01 file is only read, never written):
  blender -b Patient_v01/SAUSAGE_BUDDY_PATIENT_v01.blend --python Patient_v02/build_patient_v02.py
Writes, next to this script (refuses to overwrite):
  SAUSAGE_BUDDY_PATIENT_v02.blend / .fbx, ORGANS_LAYOUT_v02.json, build_report_SAUSAGE_BUDDY_PATIENT_v02.json

Frames: patient REST frame = model space of the patient (metres, Z up, faces -Y, patient's left = +X, feet at z 0).
TABLE frame = TABLE-ASTRA-001 v02 table-local Blender (see table_rest_contract_v01.json); computed from the Spine bone
of the TABLE_REST pose in Patient_TableRest_v01.blend. Unity prefab-local = (-x, z, -y) of the TABLE frame.
"""
import hashlib
import json
import math
from pathlib import Path

import bpy
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

HERE = Path(__file__).resolve().parent
STEM = 'SAUSAGE_BUDDY_PATIENT_v02'
REPO = Path(r'C:/Dev/Game')
TABLE_REST = REPO / 'ArtSource/Props/TABLE-ASTRA-001/v02/Patient_TableRest_v01.blend'
P = 'mixamorig:'
RIG = 'Buddy_Rig_Mixamo65'
C_B2U = Matrix(((-1, 0, 0), (0, 0, 1), (0, -1, 0)))     # Unity prefab-local <- Blender table-local (points)

# ---------------------------------------------------------------------------------------------------------------
# LAYOUT (patient REST frame). Real adult sizes (cm) and the Buddy scale used:
#   Buddy torso width 0.333 m vs ~0.30 m human (x1.11); Buddy abdomen height (axilla->crotch 0.34 m) vs ~0.51 m human (x0.67).
#   One organ SIZE factor for every organ = 0.9 (~geometric mean 0.86, rounded up for readability), so liver:kidney
#   proportions stay real. POSITIONS follow scaled landmarks: costal margin z ~0.99, xiphoid ~1.07, lumbar L1-L2 ~0.97.
# ---------------------------------------------------------------------------------------------------------------
SIZE_FACTOR = 0.9
ORGANS = {
    # centre (rest frame), size (long, wide, thick) in metres, long axis (rest frame, before orthogonalising to Z)
    'INC_LIVER': {
        'organ': 'liver', 'centre': (-0.030, -0.052, 1.032), 'real_cm': (25, 15, 8),
        'long_axis': (math.cos(math.radians(8)), 0.0, math.sin(math.radians(8))),   # +X, left lobe raised 8 deg
        'long_axis_is': 'X',
        'source_model': 'ArtSource/Props/LIVER-ASTRA-001/LIVER-ASTRA-001_recolour_v01 (mesh "LIVER-ASTRA-001 | clean organ body")',
        'source_bounds_m': (0.2046, 0.0663, 0.1529),          # model X (width), Y (thickness, front -Y), Z (height)
        'model_scale_xyz': (1.08, 1.08, 0.88),                 # cartoon squash of the height only (model is taller than real)
        'model_centre_offset': (0.0, 0.0, 0.0),
    },
    'INC_KIDNEY_L': {
        'organ': 'kidney_left', 'centre': (0.080, 0.010, 0.975), 'real_cm': (11, 6, 3),
        'long_axis': (-math.sin(math.radians(15)), math.sin(math.radians(10)), 1.0),   # upper pole toward the spine, 10 deg back
        'long_axis_is': 'Y',
        'source_model': 'ArtSource/Props/KIDNEY-ASTRA-001/KIDNEY-ASTRA-001_recolour_v01 (mesh "R_Kidney and descending tube": '
                        'the model names its pair from the viewer; its R mesh has the hilum toward model -X = the patient-left kidney)',
        'source_bounds_m': (0.0656, 0.0425, 0.1110),           # bean only, without the descending tube
        'model_scale_xyz': (0.9, 0.9, 0.9),
        'model_centre_offset': (0.0702, 0.0, -0.0008),         # bean centre in model space (the mesh origin is the pair centre)
    },
    'INC_KIDNEY_R': {
        'organ': 'kidney_right', 'centre': (-0.080, 0.010, 0.955), 'real_cm': (11, 6, 3),
        'long_axis': (math.sin(math.radians(15)), math.sin(math.radians(10)), 1.0),
        'long_axis_is': 'Y',
        'source_model': 'ArtSource/Props/KIDNEY-ASTRA-001/KIDNEY-ASTRA-001_recolour_v01 (mesh "L_Kidney and descending tube")',
        'source_bounds_m': (0.0676, 0.0443, 0.1115),
        'model_scale_xyz': (0.9, 0.9, 0.9),
        'model_centre_offset': (-0.0713, 0.0, 0.0012),
    },
}
# The opening (lens shape of a retracted midline laparotomy) and the midline cut guide, on the skin.
OPENING = {'centre_z': 0.960, 'half_length': 0.138, 'half_width': 0.122, 'lens_p': 2.0, 'lens_q': 0.6}
GUIDE = {'start_z': 1.082, 'end_z': 0.840}
# Two cords per kidney, both from the hilum (medial edge, mid height) to the great vessel lying on the spine ridge:
# A = renal artery (upper), B = renal vein (lower). Cartoon simplification: the left kidney's pair ends on the aorta, the
# right kidney's on the inferior vena cava. The kidney model's own short descending tube is the ureter (decor only).
CORDS = {'A_renal_artery': {'along': +0.008, 'end_dz': +0.016, 'radius': 0.0050, 'colour': 'artery red'},
         'B_renal_vein': {'along': -0.008, 'end_dz': -0.012, 'radius': 0.0060, 'colour': 'vein purple'}}
# Great vessels on the spine ridge (rest frame): x, centre y, radius, z range (head end, pubic end).
GREAT_VESSELS = {'aorta': {'x': 0.014, 'y': -0.003, 'r': 0.0085, 'z': (1.050, 0.862)},
                 'vena_cava': {'x': -0.016, 'y': 0.0045, 'r': 0.0100, 'z': (1.050, 0.862)}}
# ---------------------------------------------------------------------------------------------------------------


def refuse_overwrite(*paths):
    for p in paths:
        assert not Path(p).exists(), f'refusing to overwrite {p}'


def rnd(v, n=4):
    return [round(float(c), n) for c in v]


scene = bpy.context.scene
rig = bpy.data.objects[RIG]
body = bpy.data.objects['Body']
assert 'v01' in Path(bpy.data.filepath).stem, 'run on SAUSAGE_BUDDY_PATIENT_v01.blend'
out_blend, out_fbx = HERE / f'{STEM}.blend', HERE / f'{STEM}.fbx'
out_layout, out_report = HERE / 'ORGANS_LAYOUT_v02.json', HERE / f'build_report_{STEM}.json'
refuse_overwrite(out_blend, out_fbx, out_layout, out_report)


def mesh_hash(ob):
    h = hashlib.sha1()
    for v in ob.data.vertices:
        h.update(('%.6f %.6f %.6f' % tuple(v.co)).encode())
        for g in v.groups:
            h.update(('%d:%.5f' % (g.group, g.weight)).encode())
    return h.hexdigest()


def bone_hash(r):
    h = hashlib.sha1()
    for b in r.data.bones:
        h.update(b.name.encode())
        for row in b.matrix_local:
            h.update(('%.6f %.6f %.6f %.6f' % tuple(row)).encode())
    return h.hexdigest()


before = {'Body': mesh_hash(body), 'Face': mesh_hash(bpy.data.objects['Face']), 'Shorts': mesh_hash(bpy.data.objects['Shorts']),
          'bones': bone_hash(rig)}
old_markers = {n: bpy.data.objects[n].matrix_world.copy() for n in ('INC_KIDNEY_L', 'INC_KIDNEY_R', 'INC_LIVER')}

# Rest pose (the v01 file is already saved in rest; make sure).
if rig.animation_data:
    rig.animation_data.action = None
for pb in rig.pose.bones:
    pb.matrix_basis.identity()
bpy.context.view_layer.update()

bvh = BVHTree.FromObject(body, bpy.context.evaluated_depsgraph_get())
spine = rig.data.bones[P + 'Spine']


def skin_front(x, z):
    """Front skin point and outward normal at (x, z): ray from the front along +Y."""
    hit, normal, _, _ = bvh.ray_cast(Vector((x, -0.5, z)), Vector((0, 1, 0)))
    assert hit is not None, (x, z)
    if normal.y > 0:
        normal = -normal
    return hit, normal.normalized()


def skin_along(origin, direction):
    hit, _, _, dist = bvh.ray_cast(origin, direction)
    assert hit is not None
    return hit, dist


def frame(z_axis, primary, primary_is):
    z = z_axis.normalized()
    if primary_is == 'Y':
        y = (primary - z * primary.dot(z)).normalized()
        x = y.cross(z)
    else:
        x = (primary - z * primary.dot(z)).normalized()
        y = z.cross(x)
    return Matrix((x, y, z)).transposed()


def add_marker(name, matrix, size=0.05, kind='SINGLE_ARROW'):
    old = bpy.data.objects.get(name)
    if old:
        bpy.data.objects.remove(old, do_unlink=True)
    e = bpy.data.objects.new(name, None)
    e.empty_display_type = kind
    e.empty_display_size = size
    scene.collection.objects.link(e)
    e.matrix_world = matrix
    mw = e.matrix_world.copy()
    e.parent = rig
    e.parent_type = 'BONE'
    e.parent_bone = spine.name
    e.matrix_world = mw
    return e


layout = {'version': 'ORGANS_LAYOUT_v02', 'date': '2026-10-18', 'patient': f'{STEM}.fbx',
          'frames': {
              'rest': 'patient model space, Blender metres, Z up, faces -Y, patient left = +X (bone-parented markers follow '
                      'mixamorig:Spine)',
              'table_blender': 'TABLE-ASTRA-001 v02 table-local Blender in the TABLE_REST pose (head end -Y, patient left -X)',
              'table_unity': 'OperatingTableAstra_v02 prefab-local Unity = (-x, z, -y) of table_blender (head end +Z, patient left +X)',
              'marker_local_blender': 'marker axes in Blender: +X patient left, +Y head / long axis, +Z out of the body',
              'marker_local_unity': 'the same marker after FBX import into Unity: +X = patient RIGHT (X is negated), +Y and +Z '
                                    'unchanged. Every *_marker_local_unity value below already has x negated.'},
          'size_factor_vs_real': SIZE_FACTOR,
          'buddy_torso': {'width_m': 0.333, 'depth_m': 0.212, 'belly_front_y': -0.116, 'back_y': 0.096,
                          'crotch_z': 0.78, 'shorts_waist_z': 0.80, 'armpit_z': 1.13, 'costal_margin_z_est': 0.99,
                          'xiphoid_z_est': 1.07},
          'organs': {}, 'opening': {}, 'guide': {},
          'great_vessels_rest': {k: {'x': v['x'], 'y': v['y'], 'radius': v['r'], 'z_head': v['z'][0], 'z_pubic': v['z'][1]}
                                 for k, v in GREAT_VESSELS.items()}}

markers = {}
# --- organs
for name, o in ORGANS.items():
    c = Vector(o['centre'])
    skin, n = skin_front(c.x, c.z)
    rot = frame(n, Vector(o['long_axis']), o['long_axis_is'])
    m = Matrix.Translation(c) @ rot.to_4x4()
    markers[name] = add_marker(name, m)
    # depth below the skin along the marker's -Z (cast from the centre along +Z to the skin)
    sk, depth = skin_along(c, rot.col[2])
    size = [s * SIZE_FACTOR / 100 for s in o['real_cm']]
    entry = {'organ': o['organ'], 'marker': name,
             'rest': {'centre': rnd(c), 'x_axis': rnd(rot.col[0]), 'y_axis': rnd(rot.col[1]), 'z_axis_skin_normal': rnd(rot.col[2]),
                      'rotation_quat_wxyz': rnd(rot.to_quaternion()), 'skin_point_along_z': rnd(sk)},
             'long_axis': 'marker ' + ('+Y (upper pole)' if o['long_axis_is'] == 'Y' else '+X (toward the left lobe)'),
             'depth_below_skin_m': round(depth, 4),
             'real_size_cm_long_wide_thick': list(o['real_cm']),
             'buddy_size_m_long_wide_thick': rnd(size, 3),
             'source_model': o['source_model'], 'source_bounds_m_xyz': list(o['source_bounds_m']),
             'model_to_marker': 'model up (Blender +Z) -> marker +Y, model front (Blender -Y) -> marker +Z, model +X -> marker +X '
                                '(Blender rotation = Euler X -90 deg); first translate by -model_centre_offset',
             'model_scale_xyz': list(o['model_scale_xyz']), 'model_centre_offset': list(o['model_centre_offset']),
             'pull': {'direction': 'marker +Z', 'exit_distance_m': round(depth + 0.5 * size[2] + 0.03, 3)}}
    layout['organs'][name] = entry

# --- kidney cords (hilum -> spine / pelvis), stored in the kidney marker frame
for name in ('INC_KIDNEY_L', 'INC_KIDNEY_R'):
    mw = markers[name].matrix_world
    rot = mw.to_3x3()
    c = mw.translation
    side = 1 if c.x > 0 else -1
    half_w = 0.5 * ORGANS[name]['real_cm'][1] * SIZE_FACTOR / 100
    hilum = c + rot @ Vector((-side * half_w * 0.95, -0.004, 0.006))      # medial edge, just below mid height, slightly anterior
    gv = GREAT_VESSELS['aorta' if side > 0 else 'vena_cava']
    cords = {}
    for cname, spec in CORDS.items():
        start = hilum + rot @ Vector((side * 0.002, spec['along'], 0))
        end = Vector((gv['x'] + side * 0.6 * gv['r'], gv['y'], hilum.z + spec['end_dz']))
        loc_s, loc_e = mw.inverted() @ start, mw.inverted() @ end
        snip = start.lerp(end, 0.5)
        cords[cname] = {'rest_start': rnd(start), 'rest_end': rnd(end), 'rest_snip_point': rnd(snip),
                        'marker_local_blender_start': rnd(loc_s), 'marker_local_blender_end': rnd(loc_e),
                        'marker_local_unity_start': rnd((-loc_s.x, loc_s.y, loc_s.z)),
                        'marker_local_unity_end': rnd((-loc_e.x, loc_e.y, loc_e.z)),
                        'length_m': round((end - start).length, 4), 'radius_m': spec['radius'], 'colour': spec['colour'],
                        'ends_on': 'aorta' if side > 0 else 'vena_cava',
                        'direction_rest': rnd((end - start).normalized())}
    layout['organs'][name]['hilum_rest'] = rnd(hilum)
    layout['organs'][name]['cords'] = cords

# --- the opening and the guide
zc = OPENING['centre_z']
skin, n = skin_front(0.0, zc)
abd = Matrix.Translation(skin) @ frame(n, Vector((0, 0, 1)), 'Y').to_4x4()
markers['INC_ABDOMEN'] = add_marker('INC_ABDOMEN', abd, 0.08)
for gname, gz in (('GUIDE_BELLY_START', GUIDE['start_z']), ('GUIDE_BELLY_END', GUIDE['end_z'])):
    s, gn = skin_front(0.0, gz)
    markers[gname] = add_marker(gname, Matrix.Translation(s) @ frame(gn, Vector((0, 0, 1)), 'Y').to_4x4(), 0.03, 'SPHERE')
abd_inv = abd.inverted()
layout['opening'] = {'marker': 'INC_ABDOMEN', 'shape': 'lens (retracted midline laparotomy): |x| = W * (1 - |t|^p)^q, '
                     't = y / half_length, marker-local, plus a +-2 mm natural wobble in the mesh',
                     'half_length_m': OPENING['half_length'], 'half_width_m': OPENING['half_width'],
                     'p': OPENING['lens_p'], 'q': OPENING['lens_q'],
                     'rest': {'centre_on_skin': rnd(skin), 'z_axis_skin_normal': rnd(n)},
                     'mesh': 'ArtSource/Props/TABLE-ASTRA-001/v02/OperationAbdomen_v02.fbx (origin and axes = INC_ABDOMEN)'}
gs, ge = markers['GUIDE_BELLY_START'].matrix_world.translation, markers['GUIDE_BELLY_END'].matrix_world.translation
layout['guide'] = {'kind': 'belly midline (linea alba), head end -> pubic end', 'start_marker': 'GUIDE_BELLY_START',
                   'end_marker': 'GUIDE_BELLY_END', 'rest_start': rnd(gs), 'rest_end': rnd(ge),
                   'length_m': round((ge - gs).length, 4),
                   'abdomen_local_start': rnd(abd_inv @ gs), 'abdomen_local_end': rnd(abd_inv @ ge)}

# Liver loop suggestion (marker-local of INC_LIVER): around the part of the liver inside the opening.
layout['organs']['INC_LIVER']['loop'] = {'centre_marker_local_blender': [0.012, -0.004, 0.045],
                                        'centre_marker_local_unity': [-0.012, -0.004, 0.045],
                                        'radius_xy_m': [0.085, 0.056],
                                        'note': 'loop plane 4.5 cm above the liver centre = ~1 cm above its front face; '
                                                'centre nudged 1.2 cm toward the patient left and 0.4 cm down so the loop rings the part of the liver inside the opening'}

bpy.context.view_layer.update()

# --- TABLE_REST frame: Spine bone transform of the lying pose (append the posed rig, read, remove)
with bpy.data.libraries.load(str(TABLE_REST), link=False) as (src, dst):
    dst.objects = [RIG] + ['INC_KIDNEY_L', 'INC_KIDNEY_R', 'INC_LIVER']
trig = next(o for o in dst.objects if o.type == 'ARMATURE')
for ob in dst.objects:
    scene.collection.objects.link(ob)
scene.frame_set(1)
bpy.context.view_layer.update()
t_old = {ob.name.split('.')[0]: ob.matrix_world.copy() for ob in dst.objects if ob.type == 'EMPTY'}
pb = trig.pose.bones[P + 'Spine']
T = trig.matrix_world @ pb.matrix @ pb.bone.matrix_local.inverted()
check = {}
for n_, m_rest in old_markers.items():
    pred = T @ m_rest
    check[n_] = round((pred.translation - t_old[n_].translation).length * 1000, 3)
assert max(check.values()) < 1.0, f'table-frame mapping check failed: {check}'
for ob in dst.objects:
    bpy.data.objects.remove(ob, do_unlink=True)
for arm in [a for a in bpy.data.armatures if a.users == 0]:
    bpy.data.armatures.remove(arm)
for act in [a for a in bpy.data.actions if a.users == 0 and a.name.startswith('Patient_TableRest')]:
    bpy.data.actions.remove(act)


def table_entry(m):
    t = T @ m
    r = t.to_3x3().normalized()
    ru = C_B2U @ r @ C_B2U.transposed()
    p = t.translation
    return {'table_blender': {'position': rnd(p), 'x_axis': rnd(r.col[0]), 'y_axis': rnd(r.col[1]), 'z_axis': rnd(r.col[2])},
            'table_unity': {'position': rnd(C_B2U @ p), 'z_axis_out': rnd(C_B2U @ r.col[2]), 'y_axis': rnd(C_B2U @ r.col[1]),
                            'rotation_quat_xyzw': rnd(list(ru.to_quaternion())[1:] + [ru.to_quaternion().w], 5)}}


layout['table_rest'] = {'note': 'markers evaluated in the TABLE_REST pose (Patient_TableRest_v01 clip); v01 marker check (mm): '
                        + json.dumps(check)}
for name, ob in markers.items():
    layout['table_rest'][name] = table_entry(ob.matrix_world)
for name in ('INC_KIDNEY_L', 'INC_KIDNEY_R'):
    for cname, cd in layout['organs'][name]['cords'].items():
        for key in ('start', 'end'):
            p = T @ Vector(cd['rest_' + key])
            cd['table_blender_' + key] = rnd(p)
            cd['table_unity_' + key] = rnd(C_B2U @ p)

for k, v in layout['great_vessels_rest'].items():
    for key, zz in (('head', v['z_head']), ('pubic', v['z_pubic'])):
        p = T @ Vector((v['x'], v['y'], zz))
        v['table_blender_' + key] = rnd(p)
        v['table_unity_' + key] = rnd(C_B2U @ p)

# --- checks and output
after = {'Body': mesh_hash(body), 'Face': mesh_hash(bpy.data.objects['Face']), 'Shorts': mesh_hash(bpy.data.objects['Shorts']),
         'bones': bone_hash(rig)}
assert after == before, 'mesh / weights / bones changed'
report = {'source': bpy.data.filepath, 'unchanged_hashes': before, 'table_mapping_check_mm': check,
          'markers': {n: {'rest_position': rnd(o.matrix_world.translation), 'parent_bone': o.parent_bone} for n, o in markers.items()},
          'actions': [a.name for a in bpy.data.actions]}
for name, o in layout['organs'].items():
    report['markers'][name]['depth_below_skin_m'] = o['depth_below_skin_m']

bpy.context.preferences.filepaths.save_version = 0
bpy.ops.wm.save_as_mainfile(filepath=str(out_blend), copy=False)
bpy.ops.object.select_all(action='DESELECT')
for ob in [rig, body, bpy.data.objects['Face'], bpy.data.objects['Shorts']] + list(markers.values()):
    ob.select_set(True)
bpy.context.view_layer.objects.active = rig
bpy.ops.export_scene.fbx(filepath=str(out_fbx), use_selection=True, object_types={'MESH', 'ARMATURE', 'EMPTY'}, add_leaf_bones=False,
                         use_armature_deform_only=False, bake_anim=False, axis_forward='-Z', axis_up='Y',
                         apply_unit_scale=True, use_mesh_modifiers=False)
out_layout.write_text(json.dumps(layout, indent=2), encoding='utf-8')
out_report.write_text(json.dumps(report, indent=2), encoding='utf-8')
print('[PATIENT_v02]', json.dumps(report))
