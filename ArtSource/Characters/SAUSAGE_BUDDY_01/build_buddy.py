"""Sausage Buddy NPC builder (Blender 5.2, background). New character per the owner's reference
(TASK-000086); Mixamo 65-bone skeleton fitted from the original Mixamo source clip.

  blender -b --factory-startup --python ArtSource/Characters/SAUSAGE_BUDDY_01/build_buddy.py -- --variant A --revision 1
  --stage look   : body + face + rig only, quick review renders into Previews/look_vNN
  --lod full     : v03 geometry (Catmull-Clark on every loft); default 'crowd' is the v04 NPC budget (~12-15k tris)
  --variant JUNKIE (or any buddy_types.TYPES key): NPC type (TASK-000246) -> Types/<TYPE>/, still previews + colourways
  --prev DIR     : write look/dress review renders to DIR (outside the repo)
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
import buddy_gags as GG        # noqa: E402
import buddy_types as T        # noqa: E402
import buddy_wear as W         # noqa: E402

MOTION = HERE.parent / 'NPC_BASE_01' / 'Sources' / 'Run Look Back.fbx'   # original Mixamo clip (read only)
ap = argparse.ArgumentParser()
ap.add_argument('--variant', choices=['A', 'B', 'C', 'BASE'] + list(T.TYPES), default='A')
ap.add_argument('--revision', type=int, required=True)
ap.add_argument('--stage', choices=['look', 'dress', 'full'], default='full')
ap.add_argument('--no-render', action='store_true')
ap.add_argument('--lod', choices=['full', 'crowd'], default='crowd')
ap.add_argument('--prev', default=None)
args, _ = ap.parse_known_args(sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else [])
REV = f'v{args.revision:02d}'
TYPE = args.variant if args.variant in T.TYPES else None       # NPC types live in Types/<TYPE>/
BASE_DIR = HERE / 'Types' / TYPE if TYPE else HERE
if args.stage in ('look', 'dress'):
    PREV = Path(args.prev) if args.prev else BASE_DIR / 'Previews' / f'{args.stage}_{args.variant}_{REV}'
    if PREV.exists():
        sys.exit(f'{PREV} exists; choose a new --revision')
    OUT = None
else:
    STEM = f'SAUSAGE_BUDDY_{args.variant}_{REV}'
    OUT = {k: BASE_DIR / v for k, v in (('blend', STEM + '.blend'), ('fbx', STEM + '.fbx'), ('json', f'validation_{args.variant}_{REV}.json'))}
    PREV = BASE_DIR / 'Previews' / (REV if TYPE else f'{args.variant}_{REV}')
    BASE_DIR.mkdir(parents=True, exist_ok=True)
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
LOOK = T.look(TYPE) if TYPE else {}                            # per-type skin / brow / eye-rim colours
skin = G.mat('Buddy_Skin', LOOK.get('skin', (236, 152, 106)), 0.5, sss=0.12)
nose = G.mat('Buddy_Skin_Nose', LOOK.get('nose', (226, 128, 94)), 0.45, sss=0.12)
inner = G.mat('Buddy_Skin_Inner', (204, 112, 80), 0.6)
body = B.build_body(skin, nose, inner)
face = B.build_face([G.mat('Buddy_Eye_White', (247, 247, 243), 0.2), G.mat('Buddy_Eye_Rim', LOOK.get('rim', (150, 92, 70)), 0.5),
                     G.mat('Buddy_Pupil', (16, 14, 14), 0.12), G.mat('Buddy_Eye_Shine', (255, 255, 255), 0.1),
                     G.mat('Buddy_Brow', LOOK.get('brow', (86, 54, 40)), 0.7), G.mat('Buddy_Mouth', LOOK.get('mouth', (74, 36, 30)), 0.6)])
if TYPE and T.arm_down(TYPE):       # every clip starts from idle_joints(): fat types keep the arms off the belly
    A.idle_joints.__defaults__ = (0.0, T.arm_down(TYPE))
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
props = []
if args.stage != 'look':
    if TYPE:
        W.REST = rest                     # hand / head props are placed from the rig's T-pose (TASK-000270)
        garments = T.build(TYPE, body, face, skin)
        held = [o for o in garments if o.get('ov_prop')]
        garments = [o for o in garments if not o.get('ov_prop')]
        groups = {}                       # carried props: one rigid mesh per hand / bone the game can hide or drop
        for o in held:
            groups.setdefault(W.prop_group(o.get('ov_prop_bone', 'Head')), []).append(o)
        for gname, objs in sorted(groups.items()):
            pm = objs[0]
            G.join(pm, objs[1:])
            pm.name = gname; pm.data.name = gname
            skin_to_rig(pm)
            props.append(pm)
    else:
        garments = {'A': lambda: C.variant_a(body), 'B': lambda: C.variant_b(body, face), 'C': lambda: C.variant_c(body),
                    'BASE': lambda: C.variant_base(body)}[args.variant]()
    outfit = garments[0]
    G.join(outfit, garments[1:])
    outfit.name = 'Outfit'; outfit.data.name = 'Outfit'
    if TYPE:
        T.reshape(TYPE, [body, outfit])        # fat belly / thin waist, same displacement for body and clothes
    skin_to_rig(outfit)

if args.stage in ('look', 'dress'):
    idle = A.pose_from_joints(rig, rest, A.idle_joints())
    RG.key_frames(rig, rest, {1: idle}, 'Preview_Idle')
    if TYPE:
        T.set_face(face, TYPE)
    scene.frame_set(1)
    RD.studio(scene)
    cam = scene.camera
    RD.shot(scene, cam, PREV / '01_front.png', (0, -5.2, 0.95), (0, 0, 0.92), lens=70, res=(900, 1200))
    RD.shot(scene, cam, PREV / '02_three_quarter.png', (-2.4, -4.2, 1.35), (0, 0, 0.95), lens=70, res=(900, 1200))
    RD.shot(scene, cam, PREV / '03_head.png', (0, -1.25, 1.50), (0, 0, 1.50), lens=55, res=(900, 1100))
    RD.shot(scene, cam, PREV / '04_head_34.png', (-0.75, -1.05, 1.56), (0, 0, 1.50), lens=55, res=(900, 1100))
    RD.shot(scene, cam, PREV / '06_back.png', (0.9, 5.0, 1.2), (0, 0, 0.92), lens=70, res=(900, 1200))
    RD.shot(scene, cam, PREV / '07_side.png', (5.2, -0.6, 1.1), (0, 0, 0.92), lens=70, res=(900, 1200))
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
gags = GG.build_gags(rig, rest)          # comedy clips (TASK-000243)
meshes = [body, outfit, face]          # floor contact and height; carried props do not count
export_meshes = meshes + props

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
# Comedy clips: every frame's lowest mesh point goes to z = 0 (standing, lying, sliding), except the airborne
# frames, which take the ground offset interpolated from their neighbours (hops, bounces, the dive).
shifts = {}
for name, g in gags.items():
    frames = g['frames']
    fs = sorted(frames)
    act = RG.key_frames(rig, rest, frames, name)
    lows = dict(zip(fs, RG.ground_offset(scene, rig, act, meshes, fs)))
    contact = [f for f in fs if f not in g['airborne']]
    shift = {}
    for f in fs:
        if f in g['airborne']:
            before = [c for c in contact if c < f]
            after = [c for c in contact if c > f]
            if before and after:
                t = (f - before[-1]) / (after[0] - before[-1])
                shift[f] = -lows[before[-1]] * (1 - t) - lows[after[0]] * t
            else:
                shift[f] = -lows[(before or after)[-1 if before else 0]]
        else:
            shift[f] = -lows[f]
    bpy.data.actions.remove(act)
    act = RG.key_frames(rig, rest, {f: {b: Matrix.Translation((0, 0, shift[f])) @ m for b, m in frames[f].items()} for f in fs}, name)
    shifts[name] = shift
    grounding[name] = {'per_frame': True, 'min': round(min(shift.values()), 4), 'max': round(max(shift.values()), 4)}
face_act = A.face_keys(face)
gag_face_acts = [GG.face_action(face, name + '_Face', g['face']) for name, g in gags.items()]
phone = GG.build_phone(col)
phone_act = GG.phone_track(phone, rest, gags['PoliceCall'], shifts['PoliceCall'])
rig.animation_data.action = bpy.data.actions['Panic_TurnFlee']
scene.frame_start, scene.frame_end = 1, 150
scene.frame_set(1)

# validation
report = {'asset': STEM, 'variant': args.variant, 'height_m': None, 'bones': len(rig.data.bones),
          'rig_source': 'Mixamo "Run Look Back" skeleton (names, parents, rolls kept)', 'mixamo_leg_ratio': round(stride, 4),
          'animation': 'procedural startle + 180 turn + cartoon panic run (Run Look Back twists the body backwards, so it was not used)',
          'lod': args.lod, 'actions': {}, 'meshes': {}, 'grounding_offset_m': grounding}
for name in list(clips) + list(gags):
    a = bpy.data.actions[name]
    report['actions'][name] = [int(a.frame_range[0]), int(a.frame_range[1])]
report['face_tracks_blend_only'] = ['Panic_TurnFlee_Face'] + [n + '_Face' for n in gags]
report['props_blend_only'] = {'Prop_Phone': 'PoliceCall_Phone (object keys; attach to the right hand in the game)'}
if TYPE:
    report['npc_type'] = T.manifest(TYPE)
    report['fbx_actions'] = ['Idle']
    report['clips_note'] = 'Same skeleton as SAUSAGE_BUDDY_BASE: the game plays the BASE clips on this model; all clips stay in the .blend'
total = 0
for o in export_meshes:
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
for a in [face_act, phone_act] + gag_face_acts:
    bpy.data.actions.remove(a)
bpy.ops.object.select_all(action='DESELECT')
for o in [rig] + export_meshes:
    o.select_set(True)
bpy.context.view_layer.objects.active = rig
if TYPE:      # NPC types share the BASE clips (same skeleton): the FBX carries the mesh, the rig and Idle only
    rig.animation_data.action = bpy.data.actions['Idle']
    scene.frame_start, scene.frame_end = 1, 60
bpy.ops.export_scene.fbx(filepath=str(OUT['fbx']), use_selection=True, object_types={'MESH', 'ARMATURE'}, add_leaf_bones=False,
                         use_armature_deform_only=False, bake_anim=True, bake_anim_use_all_actions=not TYPE, bake_anim_use_nla_strips=False,
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
if TYPE:          # stills show the type's resting face (no clip face track)
    T.set_face(bpy.data.objects['Face'], TYPE)
RD.shot(scene, cam, PREV / '01_sheet_front.png', (0, -12, 0.9), (0, 0, 0.9), ortho=2.2, res=(1100, 1000))
RD.shot(scene, cam, PREV / '02_sheet_side.png', (12, 0, 0.9), (0, 0, 0.9), ortho=2.2, res=(1100, 1000))
RD.shot(scene, cam, PREV / '03_sheet_back.png', (0, 12, 0.9), (0, 0, 0.9), ortho=2.2, res=(1100, 1000))
rig.data.pose_position = 'POSE'
rig.animation_data.action = bpy.data.actions['Idle']
RD.shot(scene, cam, PREV / '04_idle_three_quarter.png', (-2.4, -4.2, 1.35), (0, 0, 0.95), lens=70, res=(900, 1200), frame=1)
RD.shot(scene, cam, PREV / '05_idle_head.png', (-0.75, -1.05, 1.56), (0, 0, 1.50), lens=55, res=(900, 1100), frame=1)
if TYPE:          # NPC types: stills only, plus the same 3/4 view in the two alternative colourways
    for k in (1, 2):
        T.apply_colourway(TYPE, k)
        RD.shot(scene, cam, PREV / f'06_colourway_{k}.png', (-2.4, -4.2, 1.35), (0, 0, 0.95), lens=70, res=(900, 1200), frame=1)
    T.apply_colourway(TYPE, 0)
    print('[BUDDY] previews in', PREV)
    sys.exit(0)
# clips: camera follows the hips; frames -> GIF (ImageMagick) or frame folders (assemble later)
CLIP_PREVIEWS = [('Panic_TurnFlee', [('Panic_TurnFlee', 1, 150)], Vector((-2.8, -4.6, 0.55)))] + GG.PREVIEWS


def camera_at(spec, f):
    """spec: a follow offset, or [(sequence frame, offset, look_offset), ...] keys interpolated linearly."""
    if isinstance(spec, Vector):
        return spec, Vector()
    keys = sorted(spec, key=lambda k: k[0])
    if f <= keys[0][0]:
        return keys[0][1], keys[0][2]
    for (f0, o0, l0), (f1, o1, l1) in zip(keys, keys[1:]):
        if f <= f1:
            t = (f - f0) / (f1 - f0)
            return o0.lerp(o1, t), l0.lerp(l1, t)
    return keys[-1][1], keys[-1][2]


face_ob = bpy.data.objects['Face']
phone_ob = bpy.data.objects.get('Prop_Phone')
# preview-only props (this file is not saved again): a thin lamp post and a wall
prop_obs = {}
for gif_name, props in GG.PREVIEW_PROPS.items():
    for kind, loc, size in props:
        if kind == 'pole':
            bpy.ops.mesh.primitive_cylinder_add(vertices=24, radius=size[0], depth=size[2], location=(loc[0], loc[1], size[2] / 2))
        else:
            bpy.ops.mesh.primitive_cube_add(size=1.0, location=loc, scale=size)
        ob = bpy.context.active_object
        ob.name = f'Preview_{kind}'
        ob.data.materials.append(G.mat(f'Preview_{kind}', (78, 82, 88) if kind == 'pole' else (214, 206, 190), 0.8))
        ob.hide_render = True
        prop_obs.setdefault(gif_name, []).append(ob)
scene.cycles.samples = 16
scene.render.resolution_x, scene.render.resolution_y = 540, 640
cam.data.type = 'PERSP'; cam.data.lens = 50
for gif_name, segments, cam_spec in CLIP_PREVIEWS:
    for name, obs in prop_obs.items():
        for ob in obs:
            ob.hide_render = name != gif_name
    frames_dir = PREV / f'{gif_name}_frames'
    frames_dir.mkdir(parents=True, exist_ok=True)
    follow, base = None, 0
    for clip_name, f0, f1 in segments:          # one GIF may chain several clips (fall -> loop -> get up)
        rig.animation_data.action = bpy.data.actions[clip_name]
        face_ob.data.shape_keys.animation_data.action = bpy.data.actions[clip_name + '_Face']
        if phone_ob is not None:
            phone_ob.hide_render = clip_name != 'PoliceCall'
        scene.frame_set(f1)                     # force a re-evaluation after switching actions
        for f in range(f0, f1 + 1, 2):
            seq = base + f - f0 + 1
            scene.frame_set(f)
            hips = rig.matrix_world @ rig.pose.bones[P + 'Hips'].head
            offset, look_at = camera_at(cam_spec, seq)
            tgt = hips + look_at
            tgt = Vector((tgt.x, tgt.y, max(0.45, min(0.95, tgt.z))))
            follow = tgt.copy() if follow is None else follow.lerp(tgt, 0.35)
            cam.location = follow + offset
            cam.rotation_euler = (follow + Vector((0, 0, 0.05)) - cam.location).to_track_quat('-Z', 'Y').to_euler()
            scene.render.filepath = str(frames_dir / f'f{seq:03d}.png')
            bpy.ops.render.render(write_still=True)
        base += f1 - f0 + 1
    gif = PREV / f'{gif_name}.gif'
    # ImageMagick 7, else 6. On Windows 'convert' is the system disk tool (convert.exe), never call it there.
    for tool in (['magick'],) + ((['convert'],) if sys.platform != 'win32' else ()):
        try:
            subprocess.run(tool + ['-delay', '7', '-loop', '0', str(frames_dir / 'f*.png'), '-layers', 'Optimize', str(gif)], check=True)
            break
        except (OSError, subprocess.CalledProcessError):
            continue
print('[BUDDY] previews in', PREV)
