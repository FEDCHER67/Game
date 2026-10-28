"""Build driver for the Forest_v01 set (Junkie_Walk, Inject, High_Lie_Loop). Blender 5.2, headless:

  blender -b --factory-startup --python build_forest.py -- <args>      (always pass absolute paths)

  --clip all --final [--dest <dir>]
      author and save <Clip>_v01.blend / .fbx / _authoring.json (never overwrites)
  --clip all --manifest <abs>/forest_manifest_v01.json
  --clip Inject --review <abs dir> [--saved <dir with <Clip>_v01.blend>] [--every 1] [--seq] [--views side,three_quarter]
          [--res 480] [--times 0.5,1.2] [--base] [--no-props] [--device GPU|CPU] [--samples 6]
      review frames. With --saved the delivered <Clip>_v01.blend is opened and rendered as it is; without it the clip
      is re-authored in memory (deterministic, same keys). Rendered on the FOREST_OD_JUNKIE meshes (identical rig,
      bound to the clip's rig in the render scene only); --base renders the A v04 Buddy instead. The syringe
      (SYRINGE-ASTRA-001.fbx), the treadmill stripes and the face shape keys exist only in the render scene.

Reuses Crowd_v01/build_crowd.py (unchanged) for authoring, keying, FBX export and the studio; only the registry
(clips_forest), the rig (clips_forest.ForestRig), the stems and the review stage are this set's own.
"""
from pathlib import Path
import sys, json, math, argparse, types
sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
CROWD = HERE.parent / 'Crowd_v01'
for _p in (str(CROWD), str(HERE)):
    if _p not in sys.path:
        sys.path.insert(0, _p)
import bpy
from mathutils import Vector, Matrix, Quaternion
import build_crowd as BC
import crowd_core as K
import acting_core as C
import clips_forest as F

REV = F.REV
REG = types.SimpleNamespace(CLIPS=F.CLIPS, CONTRACTS=F.CONTRACTS, PLACEMENT=F.PLACEMENT)
BC.CC = REG                    # build_crowd's Author / key / final read these module globals
BC.REV = REV
JUNKIE = C.CHAR / 'Types' / 'FOREST_OD_JUNKIE' / 'SAUSAGE_BUDDY_FOREST_OD_JUNKIE_v01.blend'
VIEWS = dict(BC.VIEWS)
VIEWS['top'] = ((0.0, 0.0, 6.0), (0.0, 0.0, 0.0), 2.4)


def parse():
    argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else sys.argv[1:]
    ap = argparse.ArgumentParser()
    ap.add_argument('--clip', required=True)
    ap.add_argument('--review', default='')
    ap.add_argument('--saved', default='')
    ap.add_argument('--every', type=float, default=2)
    ap.add_argument('--times', default='')
    ap.add_argument('--views', default='side,three_quarter')
    ap.add_argument('--res', type=int, default=320)
    ap.add_argument('--samples', type=int, default=6)
    ap.add_argument('--device', default='GPU')
    ap.add_argument('--seq', action='store_true')
    ap.add_argument('--base', action='store_true')
    ap.add_argument('--no-props', action='store_true')
    ap.add_argument('--final', action='store_true')
    ap.add_argument('--dest', default='')
    ap.add_argument('--manifest', default='')
    return ap.parse_args(argv)


def stem(name):
    return '%s_%s' % (name, REV)


class Author(BC.Author):
    def __init__(self):
        self.B = C.Buddy()
        self.rig = F.ForestRig(self.B)
        K.RIG = self.rig
        self._contracts = {}


# --------------------------------------------------------------------------------------- render-scene helpers
def enable_gpu():
    try:
        prefs = bpy.context.preferences.addons['cycles'].preferences
    except Exception:
        return None
    for kind in ('OPTIX', 'CUDA', 'HIP', 'ONEAPI'):
        try:
            prefs.compute_device_type = kind
            prefs.get_devices()
        except Exception:
            continue
        devs = [d for d in prefs.devices if d.type == kind]
        if devs:
            for d in prefs.devices:
                d.use = d.type == kind
            return kind
    return None


def junkie_skin(rig):
    """Bind the FOREST_OD_JUNKIE Body/Face/Outfit (same 65-bone rig, rest matrices identical to A v04) to `rig`
    in the render scene and hide the A v04 meshes from the render. Returns {'Body'|'Face'|'Outfit': object}."""
    with bpy.data.libraries.load(str(JUNKIE), link=False) as (src, dst):
        dst.objects = [n for n in src.objects if n in C.MESH_NAMES]
    out = {}
    for o in dst.objects:
        base = o.name.split('.')[0]
        o.name = 'Junkie_' + base
        bpy.context.scene.collection.objects.link(o)
        o.parent = rig
        o.matrix_parent_inverse = Matrix.Identity(4)
        o.matrix_basis = Matrix.Identity(4)
        for m in o.modifiers:
            if m.type == 'ARMATURE':
                m.object = rig
        if o.data.shape_keys:
            o.data.shape_keys.animation_data_clear()
            for kb in o.data.shape_keys.key_blocks:
                if kb.name != 'Basis':
                    kb.value = 0.0
        out[base] = o
    for n in C.MESH_NAMES:
        bpy.data.objects[n].hide_render = True
    for o in list(bpy.data.objects):            # appended dependency (the junkie's own rig), never rendered
        if o.type == 'ARMATURE' and o is not rig:
            o.hide_render = True
    return out


def set_face(face_obj, values):
    if face_obj is None or not face_obj.data.shape_keys:
        return
    kb = face_obj.data.shape_keys.key_blocks
    for k, v in values.items():
        if k in kb:
            kb[k].value = max(0.0, min(1.0, v))


def import_syringe(col):
    before = set(bpy.data.objects)
    bpy.ops.import_scene.fbx(filepath=F.SYRINGE['fbx'])
    objs = [o for o in bpy.data.objects if o not in before]
    for o in objs:
        o.animation_data_clear()
        for c in list(o.users_collection):
            c.objects.unlink(o)
        col.objects.link(o)
        if any(o.name.startswith(h) for h in F.SYRINGE['hide']):
            o.hide_render = True
    root = next(o for o in objs if o.parent is None)
    plunger = next(o for o in objs if o.name.startswith('CTRL_PlungerTravel_Z'))
    return root, plunger, objs


def floor_matrix(hand_pos):
    """Where the dropped syringe lies on the floor (shared by Inject's end and High_Lie_Loop): beyond the right hand,
    on its side (prop +Y up), needle pointing outward-forward."""
    ax = Vector((0.55, 0.83, 0.0)).normalized()          # prop +Z (tip -> plunger), horizontal
    up = Vector((0.0, 0.0, 1.0))
    xx = up.cross(ax).normalized()
    m = Matrix((xx, up, ax)).transposed().to_4x4()
    m.translation = Vector((hand_pos.x - 0.12, hand_pos.y - 0.10, 0.0245))
    return m


def syringe_driver(spec, rig, root, plunger, N):
    """Per-frame placement of the preview syringe: hidden before SyringeShow, in the right hand (grip matrix), the
    plunger pushed during the injection, falling to the floor after SyringeDrop (render scene only)."""
    sy = spec.get('syringe')
    if not sy:
        root.hide_render = True
        for o in root.children_recursive:
            o.hide_render = True
        return None
    grip = F.syringe_matrix()
    bone = rig.pose.bones[F.SYRINGE['bone']]
    sc = bpy.context.scene
    hidden = [o for o in root.children_recursive if o.hide_render]

    def hand_world(f):
        sc.frame_set(int(f), subframe=f % 1)
        bpy.context.view_layer.update()
        return rig.matrix_world @ bone.matrix @ grip, (rig.matrix_world @ bone.matrix).translation.copy()

    if sy.get('floor'):
        _, hp = hand_world(1.0)
        rest = floor_matrix(hp)
        drop = None
    else:
        _, hp = hand_world(float(N + 1))                     # end pose = high_lie: same floor spot as the loop
        rest = floor_matrix(hp)
        drop = sy.get('drop')
        W0, _ = hand_world(1.0 + drop * C.FPS) if drop is not None else (None, None)
    t_fall = 0.30

    def show(on):
        root.hide_render = not on
        for o in root.children_recursive:
            o.hide_render = (not on) or (o in hidden)

    def update(t):
        if sy.get('floor'):
            show(True)
            root.matrix_world = rest
            plunger.location.z = F.SYRINGE['plunger_in']
            return
        if t < sy['show'] - 1e-6:
            show(False)
            return
        show(True)
        a, b = sy['push']
        u = min(1.0, max(0.0, (t - a) / (b - a)))
        plunger.location.z = F.SYRINGE['plunger_out'] + (F.SYRINGE['plunger_in'] - F.SYRINGE['plunger_out']) * K.smooth(u)
        if drop is None or t < drop:
            root.matrix_world = rig.matrix_world @ bone.matrix @ grip
            return
        s = min(1.0, (t - drop) / t_fall)
        q0, q1 = W0.to_quaternion(), rest.to_quaternion()
        q = q0.slerp(q1, K.smooth(s))
        p0, p1 = W0.translation, rest.translation
        pos = p0.lerp(p1, s)
        pos.z = p0.z + (p1.z - p0.z) * (s * s)              # falls with gravity
        if s >= 1.0:                                         # little bounce after it lands
            e = t - drop - t_fall
            pos.z = p1.z + 0.03 * max(0.0, math.sin(math.pi * e / 0.16)) * (1.0 if e < 0.16 else 0.0)
        m = q.to_matrix().to_4x4()
        m.translation = pos
        root.matrix_world = m
    return update


def review(name, N, a, scene=None, rig=None):
    spec = REG.CLIPS[name]
    sc = scene or bpy.context.scene
    rig = rig or bpy.data.objects[C.RIG_NAME]
    col, cam = C.studio(sc)
    props = BC.build_props(col, spec.get('props', []))
    skin = {} if a.base else junkie_skin(rig)
    face = skin.get('Face')
    upd = None
    if not a.no_props:
        root, plunger, _ = import_syringe(col)
        upd = syringe_driver(spec, rig, root, plunger, N)
    sc.render.engine = 'CYCLES'
    sc.cycles.samples = a.samples
    dev = enable_gpu() if a.device.upper() == 'GPU' else None
    sc.cycles.device = 'GPU' if dev else 'CPU'
    try:
        sc.cycles.use_denoising = True
    except Exception:
        pass
    sc.render.resolution_x = sc.render.resolution_y = a.res
    sc.render.image_settings.file_format = 'PNG'
    sc.view_settings.exposure = -0.85
    out = Path(a.review)
    assert out.is_absolute(), 'review dir must be absolute'
    if a.clip == 'all' or ',' in a.clip:
        out = out / name
    if a.times:
        fl = [1 + float(x) * C.FPS for x in a.times.split(',')]
    else:
        fl, f = [], 1.0
        while f < N + 1 - 1e-9:
            fl.append(f)
            f += a.every
        fl.append(float(N + 1))
    views = spec.get('views', VIEWS)
    print('REVIEW', name, 'device', sc.cycles.device, dev, 'frames', len(fl), flush=True)
    for v in a.views.split(','):
        loc, tgt, ortho = views[v] if v in views else VIEWS[v]
        C.aim(cam, loc, tgt, ortho)
        for k, f in enumerate(fl):
            sc.frame_set(int(f), subframe=f % 1)
            t = (f - 1) / C.FPS
            for o in props:
                if 'tread_v' in o:
                    y = (o['tread_y0'] + o['tread_v'] * t + 6.25) % 12.5 - 6.25
                    o.location = (0, y - o['tread_y0'], 0)
            if upd:
                upd(t)
            if face is not None and spec.get('face'):
                set_face(face, spec['face'](t))
            bpy.context.view_layer.update()
            p = out / v / (('s%04d.png' % k) if a.seq else ('f%07.2f.png' % f))
            p.parent.mkdir(parents=True, exist_ok=True)
            sc.render.filepath = str(p)
            bpy.ops.render.render(write_still=True)
    print('REVIEW_DONE', name, len(fl), flush=True)


def review_saved(name, a):
    path = Path(a.saved) / (stem(name) + '.blend')
    assert path.is_absolute() and path.exists(), path
    bpy.ops.wm.open_mainfile(filepath=str(path))
    rig = bpy.data.objects[C.RIG_NAME]
    act = rig.animation_data.action
    assert act.name == name, act.name
    f0, f1 = (int(round(x)) for x in act.frame_range)
    review(name, f1 - f0, a, bpy.context.scene, rig)


# --------------------------------------------------------------------------------------- final / manifest
def syringe_attachment():
    q = Quaternion(F.SYRINGE['rot_wxyz'])
    tip = Vector(F.SYRINGE['tip'])
    return {
        'prop': 'ArtSource/Props/SYRINGE-ASTRA-001/SYRINGE-ASTRA-001.fbx (existing prop; origin = needle tip, '
                'long axis +Z toward the plunger)',
        'bone': F.SYRINGE['bone'],
        'frame': 'Blender pose-bone frame of the hand: origin at the wrist joint (bone head), +Y along the bone toward '
                 'the fingers, +X thumb/index side, +Z palm normal',
        'position_m': [round(x, 5) for x in tip],
        'rotation_quaternion_wxyz': [round(x, 6) for x in q],
        'rotation_note': '+90 deg about hand X: prop +Z (tip -> plunger) = hand -Y, prop +X = hand +X (flange wings '
                         'across the hand), prop +Y = hand +Z (palm normal); needle along the fingers',
        'unity_local_guess': {'localPosition': [round(-tip.x, 5), round(tip.y, 5), round(tip.z, 5)],
                              'localRotation_xyzw_of_blender_frame': [round(q.x, 6), round(-q.y, 6), round(-q.z, 6),
                                                                      round(q.w, 6)],
                              'note': 'standard right->left-handed X flip of the Blender bone frame; the syringe FBX '
                                      'has its own import axis conversion, so place it once with a gizmo'},
        'plunger': 'CTRL_PlungerTravel_Z local z %.3f (out) -> %.3f (in) during the Inject event window'
                   % (F.SYRINGE['plunger_out'], F.SYRINGE['plunger_in']),
        'hidden_parts': list(F.SYRINGE['hide']),
    }


def face_hints(name, step=0.25):
    fn = REG.CLIPS[name].get('face')
    if not fn:
        return None
    T = REG.CLIPS[name]['T']
    n = int(round(T / step))
    return {'note': 'preview-only face shape keys (FOREST_OD_JUNKIE Face: Blink, Worried, Surprised, Happy); not in '
                    'the FBX, for GreyboxFace.Set', 'step_s': step,
            'samples': [[round(i * step, 3)] + [round(v, 3) for v in fn(i * step).values()] for i in range(n + 1)],
            'keys': list(fn(0.0).keys())}


def final(A, name, act, N, info, dest):
    BC.final(A, name, act, N, info, dest)
    rep = dest / (stem(name) + '_authoring.json')
    d = json.loads(rep.read_text(encoding='utf-8'))
    spec = REG.CLIPS[name]
    d['package'] = 'Forest_' + REV
    d['authoring'] = 'Original procedural keyframe animation (clips_forest.py on crowd_core / acting_core); no ' \
                     'external motion reused'
    if spec.get('run_speed'):
        d['ground_speed_m_s'] = spec['run_speed']
    if spec.get('feet_free'):
        d['feet_free'] = spec['feet_free']
    if spec.get('syringe'):
        d['syringe_attachment'] = syringe_attachment()
        d['syringe_timing'] = {k: v for k, v in spec['syringe'].items()}
    fh = face_hints(name)
    if fh:
        d['face_hints'] = fh
    rep.write_text(json.dumps(d, indent=2), encoding='utf-8')


def manifest(path):
    p = Path(path)
    assert p.is_absolute(), 'manifest path must be absolute'
    assert not p.exists(), 'Refusing overwrite ' + str(p)
    clips = {}
    for name, s in REG.CLIPS.items():
        clips[name] = {'file': stem(name) + '.fbx', 'take': 'Buddy_Rig_Mixamo65|' + name,
                       'frames': [1, int(round(s['T'] * C.FPS)) + 1], 'duration_s': s['T'], 'loop': s['loop'],
                       'start_contract': s['start'], 'end_contract': s['end'], 'activity': s.get('activity'),
                       'role': s.get('role'), 'events': s.get('events', {}), 'unity': s.get('unity', ''),
                       'beats': s.get('beats', [])}
        if s.get('run_speed'):
            clips[name]['ground_speed_m_s'] = s['run_speed']
        if s.get('syringe'):
            clips[name]['syringe'] = dict(s['syringe'])
    doc = {'package': 'Forest_' + REV, 'fps': C.FPS, 'rig': 'Buddy_Rig_Mixamo65 (65 bones, root mixamorig:Hips)',
           'preview_mesh': 'FOREST_OD_JUNKIE v01 (rig identical to A v04: 65 bones, same order, rest matrices equal)',
           'contracts': {k: v['doc'] for k, v in REG.CONTRACTS.items()} | {'idle': 'A v04 Idle frame 1 (exact raw values)'},
           'placement': REG.PLACEMENT, 'syringe_attachment': syringe_attachment(),
           'face_hints': {n: face_hints(n) for n in REG.CLIPS}, 'clips': clips}
    p.write_text(json.dumps(doc, indent=2), encoding='utf-8')
    print('MANIFEST', p)


def main():
    a = parse()
    if a.manifest:
        manifest(a.manifest)
        return
    names = list(REG.CLIPS) if a.clip == 'all' else a.clip.split(',')
    if a.review and a.saved:
        for name in names:
            review_saved(name, a)
        return
    assert not (a.review and a.final), 'review and final are separate runs (review props must never reach a saved file)'
    A = Author()
    for i, name in enumerate(names):
        if i:
            A = Author()
        frames, canonical, info, N = A.frames(name)
        act = A.key(name, frames, canonical, N)
        if a.review:
            review(name, N, a, A.B.scene, A.B.rig)
        if a.final:
            dest = Path(a.dest) if a.dest else HERE
            assert dest.is_absolute()
            dest.mkdir(parents=True, exist_ok=True)
            final(A, name, act, N, info, dest)
        print('BUILT %-16s frames %4d  overreach %.4f  start_gap %.5f  end_gap %.5f  step %5.1f@f%s %-14s max_lift %.3f' % (
            name, N + 1, max(i['over'] for i in info), info[0]['start_gap'], info[-1]['end_gap'], *info[0]['max_step'],
            max(abs(i['dz_contact']) for i in info)), flush=True)


if __name__ == '__main__':
    main()
