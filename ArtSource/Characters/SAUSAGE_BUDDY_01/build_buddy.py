"""Sausage Buddy NPC builder (Blender 5.2, background). New character per the owner's reference
(TASK-000086); Mixamo 65-bone skeleton fitted from the original Mixamo source clip.

  blender -b --factory-startup --python ArtSource/Characters/SAUSAGE_BUDDY_01/build_buddy.py -- --variant A --revision 1
  --stage look   : body + face + rig only, quick review renders into Previews/look_vNN
  --lod full     : v03 geometry (Catmull-Clark on every loft); default 'crowd' is the v04 NPC budget (~12-15k tris);
  --lod low      : v05 budget (~6-7.5k tris): face as in 'crowd', coarser everything else, hidden skin removed
Never overwrites an existing revision.
"""
import argparse, json, re, sys
from pathlib import Path
import bpy
from mathutils import Vector

HERE = Path(__file__).resolve().parent
sys.dont_write_bytecode = True
sys.path.insert(0, str(HERE))
import buddy_geo as G          # noqa: E402
import buddy_body as B         # noqa: E402
import buddy_rig as RG         # noqa: E402
import buddy_anim as A         # noqa: E402
import buddy_render as RD      # noqa: E402
import buddy_clothes as C      # noqa: E402

MOTION = HERE.parent / 'NPC_BASE_01' / 'Sources' / 'Run Look Back.fbx'   # original Mixamo clip (read only)
ap = argparse.ArgumentParser()
ap.add_argument('--variant', choices=['A', 'B', 'C'], default='A')
ap.add_argument('--revision', type=int, required=True)
ap.add_argument('--stage', choices=['look', 'dress', 'full'], default='full')
ap.add_argument('--no-render', action='store_true')
ap.add_argument('--lod', choices=['full', 'crowd', 'low'], default='crowd')
args, _ = ap.parse_known_args(sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else [])
REV = f'v{args.revision:02d}'
if args.stage in ('look', 'dress'):
    PREV = HERE / 'Previews' / f'{args.stage}_{args.variant}_{REV}'
    if PREV.exists():
        sys.exit(f'{PREV} exists; choose a new --revision')
    OUT = None
else:
    STEM = f'SAUSAGE_BUDDY_{args.variant}_{REV}'
    OUT = {k: HERE / v for k, v in (('blend', STEM + '.blend'), ('fbx', STEM + '.fbx'), ('json', f'validation_{args.variant}_{REV}.json'))}
    PREV = HERE / 'Previews' / f'{args.variant}_{REV}'
    for p in OUT.values():
        if p.exists():
            sys.exit(f'Refusing to overwrite {p.name}; choose a new --revision')

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.render.fps = 30
col = bpy.data.collections.new('SausageBuddy'); scene.collection.children.link(col)
G.COLLECTION = col
G.LOD = G.LODS[args.lod]

# ------------------------------------------------------------------ body, face, rig
skin = G.mat('Buddy_Skin', (236, 152, 106), 0.5, sss=0.12)
nose = G.mat('Buddy_Skin_Nose', (226, 128, 94), 0.45, sss=0.12)
inner = G.mat('Buddy_Skin_Inner', (204, 112, 80), 0.6)
body = B.build_body(skin, nose, inner)
face = B.build_face([G.mat('Buddy_Eye_White', (247, 247, 243), 0.2), G.mat('Buddy_Eye_Rim', (150, 92, 70), 0.5),
                     G.mat('Buddy_Pupil', (16, 14, 14), 0.12), G.mat('Buddy_Eye_Shine', (255, 255, 255), 0.1),
                     G.mat('Buddy_Brow', (86, 54, 40), 0.7), G.mat('Buddy_Mouth', (74, 36, 30), 0.6)])
src, imported = RG.import_source(MOTION)
src_rest, motion, (f0, f1) = RG.sample_motion(scene, src)
rig, rest = RG.fit_rig(col, src, src_rest, B.joints())
src_action = src.animation_data.action
for o in imported:
    data = o.data
    bpy.data.objects.remove(o)
    if data is not None and getattr(data, 'users', 1) == 0:
        if isinstance(data, bpy.types.Armature):
            bpy.data.armatures.remove(data)
        elif isinstance(data, bpy.types.Mesh):
            bpy.data.meshes.remove(data)
if src_action and src_action.users == 0:
    bpy.data.actions.remove(src_action)


def skin_to_rig(ob):
    ob.parent = rig
    ob.matrix_parent_inverse.identity()
    m = ob.modifiers.new('Armature', 'ARMATURE'); m.object = rig


for o in (body, face):
    skin_to_rig(o)

outfit = None
if args.stage != 'look':
    garments = {'A': lambda: C.variant_a(body), 'B': lambda: C.variant_b(body, face), 'C': lambda: C.variant_c(body)}[args.variant]()
    outfit = garments[0]
    G.join(outfit, garments[1:])
    outfit.name = 'Outfit'; outfit.data.name = 'Outfit'
    skin_to_rig(outfit)
    rules = G.LOD.get('drop', {}).get(args.variant)
    dropped = G.drop(body, 'Body', rules) if rules else {}      # after the clothes copied their weights from this skin

if args.stage in ('look', 'dress'):
    idle = A.pose_from_joints(rig, rest, A.idle_joints())
    RG.key_frames(rig, rest, {1: idle}, 'Preview_Idle')
    scene.frame_set(1)
    RD.studio(scene)
    cam = scene.camera
    RD.shot(scene, cam, PREV / '01_front.png', (0, -5.2, 0.95), (0, 0, 0.92), lens=70, res=(900, 1200))
    RD.shot(scene, cam, PREV / '02_three_quarter.png', (-2.4, -4.2, 1.35), (0, 0, 0.95), lens=70, res=(900, 1200))
    RD.shot(scene, cam, PREV / '03_head.png', (0, -1.25, 1.50), (0, 0, 1.50), lens=55, res=(900, 1100))
    RD.shot(scene, cam, PREV / '04_head_34.png', (-0.75, -1.05, 1.56), (0, 0, 1.50), lens=55, res=(900, 1100))
    RD.shot(scene, cam, PREV / '06_back.png', (0.9, 5.0, 1.2), (0, 0, 0.92), lens=70, res=(900, 1200))
    rig.data.pose_position = 'REST'
    RD.shot(scene, cam, PREV / '05_tpose.png', (0, -5.0, 0.95), (0, 0, 0.95), lens=50, res=(1400, 1000))
    bpy.ops.wm.save_as_mainfile(filepath=str(PREV / 'review.blend'))
    print('[BUDDY] look renders in', PREV)
    sys.exit(0)

# ------------------------------------------------------------------ full: animation, export, validation, previews
import subprocess   # noqa: E402
from mathutils import Matrix   # noqa: E402

P = RG.P
leg_t = (rest[P + 'LeftUpLeg'].translation - rest[P + 'LeftFoot'].translation).length
leg_s = (src_rest[P + 'LeftUpLeg'].translation - src_rest[P + 'LeftFoot'].translation).length
stride = leg_t / leg_s
clips = A.build_panic(rig, rest)
meshes = [body, outfit, face]

# Ground contact: lowest mesh point of each clip lifted/lowered to z = 0 (feet on the floor).
grounding = {}
for name, frames in clips.items():
    act = RG.key_frames(rig, rest, frames, name)
    sample = sorted(frames)[::3]
    lows = RG.ground_offset(scene, rig, act, meshes, sample)
    low = min(lows)
    # shift the whole pose in armature space and re-key (hips location keys live in bone space)
    lift = Matrix.Translation((0, 0, -low))
    shifted = {f: {b: lift @ m for b, m in d.items()} for f, d in frames.items()}
    bpy.data.actions.remove(act)
    act = RG.key_frames(rig, rest, shifted, name)
    grounding[name] = round(-low, 4)
face_act = A.face_keys(face)
rig.animation_data.action = bpy.data.actions['Panic_TurnFlee']
scene.frame_start, scene.frame_end = 1, 150
scene.frame_set(1)

# validation
report = {'asset': STEM, 'variant': args.variant, 'height_m': None, 'bones': len(rig.data.bones),
          'rig_source': 'Mixamo "Run Look Back" skeleton (names, parents, rolls kept)', 'mixamo_leg_ratio': round(stride, 4),
          'animation': 'procedural startle + 180 turn + cartoon panic run (Run Look Back twists the body backwards, so it was not used)',
          'lod': args.lod, 'actions': {}, 'meshes': {}, 'grounding_offset_m': grounding,
          'hidden_skin_removed_triangles': dict(sorted(dropped.items()))}
for name in clips:
    a = bpy.data.actions[name]
    report['actions'][name] = [int(a.frame_range[0]), int(a.frame_range[1])]
total = 0
for o in meshes:
    me = o.data
    tris = sum(len(p.vertices) - 2 for p in me.polygons)
    infl = [len([g for g in v.groups if g.weight > 1e-4]) for v in me.vertices]
    report['meshes'][o.name] = {'triangles': tris, 'vertices': len(me.vertices), 'materials': [m.name for m in me.materials],
                                'max_influences': max(infl), 'unweighted_vertices': infl.count(0),
                                'shape_keys': [k.name for k in me.shape_keys.key_blocks] if me.shape_keys else []}
    total += tris
report['total_triangles'] = total
# per-part triangles before joining; mirrored parts and the expression copies of the face are summed / skipped
parts = {}
for n, t in G.PART_TRIS.items():
    if re.search(r'\.\d+$', n):
        continue
    g = re.sub(r'_(-?\d+|Left|Right)(?=_|$)', '', n)
    parts[g] = parts.get(g, 0) + t
report['part_triangles'] = dict(sorted(parts.items(), key=lambda kv: -kv[1]))
rig.data.pose_position = 'REST'
bpy.context.view_layer.update()
dg = bpy.context.evaluated_depsgraph_get()
zs = [(o.matrix_world @ v.co).z for o in meshes for v in o.evaluated_get(dg).to_mesh().vertices]
report['height_m'] = round(max(zs) - min(zs), 3)
rig.data.pose_position = 'POSE'

bpy.ops.wm.save_as_mainfile(filepath=str(OUT['blend']))
# FBX: rig + three skinned meshes; body clips only (the face track stays in the .blend; the game drives blend shapes)
key = face.data.shape_keys
key.animation_data.action = None
bpy.data.actions.remove(face_act)
bpy.ops.object.select_all(action='DESELECT')
for o in [rig] + meshes:
    o.select_set(True)
bpy.context.view_layer.objects.active = rig
bpy.ops.export_scene.fbx(filepath=str(OUT['fbx']), use_selection=True, object_types={'MESH', 'ARMATURE'}, add_leaf_bones=False,
                         use_armature_deform_only=False, bake_anim=True, bake_anim_use_all_actions=True, bake_anim_use_nla_strips=False,
                         bake_anim_simplify_factor=0, axis_forward='-Z', axis_up='Y', apply_unit_scale=True, use_mesh_modifiers=False)
OUT['json'].write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding='utf-8')
print('[BUDDY]', STEM, 'tris', total, 'height', report['height_m'], 'actions', report['actions'], 'grounding', grounding)
for k, v in report['meshes'].items():
    print('[BUDDY]', k, v['triangles'], 'max_infl', v['max_influences'], 'unweighted', v['unweighted_vertices'])

if args.no_render:
    sys.exit(0)
bpy.ops.wm.open_mainfile(filepath=str(OUT['blend']))      # back to the saved state (face track included)
scene = bpy.context.scene
rig = bpy.data.objects['Buddy_Rig_Mixamo65']
col, cam, floor = RD.studio(scene)
rig.data.pose_position = 'REST'
RD.shot(scene, cam, PREV / '01_sheet_front.png', (0, -12, 0.9), (0, 0, 0.9), ortho=2.2, res=(1100, 1000))
RD.shot(scene, cam, PREV / '02_sheet_side.png', (12, 0, 0.9), (0, 0, 0.9), ortho=2.2, res=(1100, 1000))
RD.shot(scene, cam, PREV / '03_sheet_back.png', (0, 12, 0.9), (0, 0, 0.9), ortho=2.2, res=(1100, 1000))
rig.data.pose_position = 'POSE'
rig.animation_data.action = bpy.data.actions['Idle']
RD.shot(scene, cam, PREV / '04_idle_three_quarter.png', (-2.4, -4.2, 1.35), (0, 0, 0.95), lens=70, res=(900, 1200), frame=1)
RD.shot(scene, cam, PREV / '05_idle_head.png', (-0.75, -1.05, 1.56), (0, 0, 1.50), lens=55, res=(900, 1100), frame=1)
# panic clip: camera follows the hips; frames -> GIF
rig.animation_data.action = bpy.data.actions['Panic_TurnFlee']
frames_dir = PREV / 'panic_frames'
frames_dir.mkdir(parents=True, exist_ok=True)
scene.cycles.samples = 16
scene.render.resolution_x, scene.render.resolution_y = 540, 640
cam.data.type = 'PERSP'; cam.data.lens = 50
follow = None
for f in range(1, 151, 2):
    scene.frame_set(f)
    hips = rig.matrix_world @ rig.pose.bones[P + 'Hips'].head
    tgt = Vector((hips.x, hips.y, 0.95))
    follow = tgt.copy() if follow is None else follow.lerp(tgt, 0.35)
    cam.location = follow + Vector((-2.8, -4.6, 0.55))
    cam.rotation_euler = (follow + Vector((0, 0, 0.05)) - cam.location).to_track_quat('-Z', 'Y').to_euler()
    scene.render.filepath = str(frames_dir / f'f{f:03d}.png')
    bpy.ops.render.render(write_still=True)
gif = PREV / 'Panic_TurnFlee.gif'
for tool in (['magick'], ['convert']):      # ImageMagick 7, else 6
    try:
        subprocess.run(tool + ['-delay', '7', '-loop', '0', str(frames_dir / 'f*.png'), '-layers', 'Optimize', str(gif)], check=True)
        break
    except (OSError, subprocess.CalledProcessError):
        continue
print('[BUDDY] previews in', PREV)
