"""Build driver for the v02 revisions (BarDoor_Enter, SmokeCorner_Enter, SmokeCorner_Loop) of the Crowd package.

Reuses build_crowd.py (v01, unchanged) for authoring, keying and the review stage; only the registry, the stems
(<Clip>_v02), the rig extension (clips_props_v02.RigV02) and the preview-only props differ.

  python build_crowd_v02.py --clip all --final [--dest <dir>]
      author and save <Clip>_v02.blend / .fbx / _authoring.json (never overwrites)
  python build_crowd_v02.py --clip all --manifest crowd_manifest_v02.json
  python build_crowd_v02.py --clip SmokeCorner_Loop --review <abs dir> [--saved <dir with the saved v02 .blend>]
          [--every 1] [--seq] [--views side,three_quarter] [--res 480] [--times 0.5,1.2] [--no-props]
      review frames. With --saved the saved <Clip>_v02.blend is opened and rendered as it is (exactly the
      delivered animation); without it the clip is re-authored in memory (deterministic, same keys).
      The cigarette / lighter (SmokeCorner) are added to the render scene only, never to a saved file.

(`blender -b --factory-startup --python build_crowd_v02.py -- <args>` works the same.) Contract poses are resolved
exactly as in v01 (build_crowd.Author.contract_values on clips_props.CONTRACTS). Always pass absolute paths.
"""
from pathlib import Path
import sys, json, math, argparse, types
sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import bpy
from mathutils import Vector, Matrix
import build_crowd as BC
import crowd_core as K
import acting_core as C
import clips_props_v02 as V2

REV = V2.REV
DEVICE = 'CPU'               # review renders (the GPU wrapper sets 'GPU')
REG = types.SimpleNamespace(CLIPS=V2.CLIPS, CONTRACTS=V2.CONTRACTS, PLACEMENT=V2.PLACEMENT)
# build_crowd's Author / key / final / manifest read the module globals CC and REV: point them at the v02 registry
BC.CC = REG
BC.REV = REV


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
    ap.add_argument('--seq', action='store_true')
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
        self.rig = V2.RigV02(self.B)
        K.RIG = self.rig
        self._contracts = {}


# --------------------------------------------------------------------------------------- preview-only props
def _emit_mat(name, rgb, strength):
    m = bpy.data.materials.new(name)
    try:
        m.use_nodes = True
    except Exception:
        pass
    b = next(n for n in m.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
    b.inputs['Base Color'].default_value = C.srgb(rgb)
    b.inputs['Roughness'].default_value = 0.6
    for nm in ('Emission Color', 'Emission'):
        if nm in b.inputs:
            b.inputs[nm].default_value = C.srgb(rgb)
            break
    b.inputs['Emission Strength'].default_value = strength
    return m, b


def _cyl(col, name, length, radius, mat, y0, seg=10):
    """Cylinder along local +Y from y0 to y0 + length."""
    v, f = [], []
    for i in range(seg):
        a = 2 * math.pi * i / seg
        x, z = radius * math.cos(a), radius * math.sin(a)
        v += [(x, y0, z), (x, y0 + length, z)]
    for i in range(seg):
        j = (i + 1) % seg
        f.append((2 * i, 2 * j, 2 * j + 1, 2 * i + 1))
    f.append(tuple(2 * i for i in range(seg))[::-1])
    f.append(tuple(2 * i + 1 for i in range(seg)))
    me = bpy.data.meshes.new(name)
    me.from_pydata(v, [], f)
    me.materials.append(mat)
    o = bpy.data.objects.new(name, me)
    col.objects.link(o)
    return o


def preview_props(col, spec):
    """Cigarette (+ lighter and flame) for SmokeCorner previews; returns an updater f(rig, t)."""
    pv = spec.get('preview')
    if not pv:
        return None
    cg = V2.CIGARETTE
    white, _ = _emit_mat('Cig_Paper', (246, 244, 236), 0.0)
    ember_m, ember_b = _emit_mat('Cig_Ember', (255, 96, 20), 2.0)
    ash_m, _ = _emit_mat('Cig_Ash', (120, 116, 110), 0.0)
    filt = cg['filter_out']
    # prop frame: +Y toward the lit end, origin at the grip
    body = _cyl(col, 'Cig_Body_PREVIEW', cg['length'] - cg['ember'], cg['radius'], white, -filt)
    ember = _cyl(col, 'Cig_Ember_PREVIEW', cg['ember'], cg['radius'] * 1.02, ember_m, -filt + cg['length'] - cg['ember'])
    parts = [body, ember]
    M_cig = V2.cig_matrix()
    lighter = flame = None
    if 'lighter' in pv:
        lm, _ = _emit_mat('Lighter_Body', (40, 120, 230), 0.0)
        sx, sy, sz = V2.LIGHTER['size']
        lighter = BC.box(col, 'Lighter_PREVIEW', (-sx / 2, -sy / 2, -sz / 2), (sx / 2, sy / 2, sz / 2), (40, 120, 230))
        lighter.data.materials.clear()
        lighter.data.materials.append(lm)
        fm, _ = _emit_mat('Flame', (255, 170, 40), 12.0)
        flame = BC.box(col, 'Flame_PREVIEW', (-0.005, -0.004, sz / 2), (0.005, 0.004, sz / 2 + 0.028), (255, 170, 40))
        flame.data.materials.clear()
        flame.data.materials.append(fm)
    up = Vector(V2.LIGHTER['up'])
    q_l = Vector((0, 0, 1)).rotation_difference(up)
    M_l = q_l.to_matrix().to_4x4()
    M_l.translation = Vector(V2.LIGHTER['center'])

    def visible(key, t):
        return any(a - 1e-6 <= t <= b + 1e-6 for a, b in pv.get(key, []))

    def update(rig, t):
        W = rig.matrix_world @ rig.pose.bones[cg['bone']].matrix @ M_cig
        on = visible('cig', t)
        for o in parts:
            o.matrix_world = W
            o.hide_render = not on
        g = pv['ember'](t) if 'ember' in pv else 0.3
        if t < pv.get('ember_from', -1.0):
            g = -1.0
        ember_b.inputs['Emission Strength'].default_value = 0.0 if g < 0 else 1.0 + 14.0 * g
        ember.data.materials[0] = ember_m if g >= 0 else white
        if lighter is not None:
            WL = rig.matrix_world @ rig.pose.bones[V2.LIGHTER['bone']].matrix @ M_l
            lighter.matrix_world = WL
            flame.matrix_world = WL
            lighter.hide_render = not visible('lighter', t)
            flame.hide_render = not visible('flame', t)
    return update


# --------------------------------------------------------------------------------------- review stage
def review(name, N, a, scene=None, rig=None):
    """Review frames of the keyed action on the current scene (re-authored, or the opened saved file)."""
    spec = REG.CLIPS[name]
    sc = scene or bpy.context.scene
    rig = rig or bpy.data.objects[C.RIG_NAME]
    col, cam = C.studio(sc)
    props = BC.build_props(col, spec.get('props', []))
    upd = None if a.no_props else preview_props(col, spec)
    sc.render.engine = 'CYCLES'
    sc.cycles.samples = a.samples
    sc.cycles.device = DEVICE
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
        out = out / name                 # several clips: <review>/<Clip>/<view>/...
    if a.times:
        fl = [1 + float(x) * C.FPS for x in a.times.split(',')]
    else:
        fl, f = [], 1.0
        while f < N + 1 - 1e-9:
            fl.append(f)
            f += a.every
        fl.append(float(N + 1))
    views = spec.get('views', BC.VIEWS)
    for v in a.views.split(','):
        loc, tgt, ortho = views[v] if v in views else BC.VIEWS[v]
        C.aim(cam, loc, tgt, ortho)
        for k, f in enumerate(fl):
            sc.frame_set(int(f), subframe=f % 1)
            t = (f - 1) / C.FPS
            if upd:
                upd(rig, t)
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


# --------------------------------------------------------------------------------------- final
def attachments(name):
    spec = REG.CLIPS[name]
    if spec.get('activity') != 'SmokeCorner':
        return {}
    cg = V2.CIGARETTE
    filt, lit = V2.cig_points_local()
    q = V2.cig_matrix().to_quaternion()
    return {'cigarette': {
        'bone': cg['bone'], 'frame': 'Blender pose-bone frame of the hand: origin at the wrist joint (bone head), '
                                     '+Y along the bone toward the fingers, +X thumb side, +Z palm normal',
        'grip_position_m': [round(x, 5) for x in cg['grip']],
        'filter_tip_m': [round(x, 5) for x in filt], 'lit_tip_m': [round(x, 5) for x in lit],
        'prop_axis': 'prop +Y = cigarette axis toward the lit end, origin at the grip (filter tip at y = -%.3f)' % cg['filter_out'],
        'rotation_quaternion_wxyz': [round(x, 6) for x in q], 'length_m': cg['length'], 'diameter_m': 2 * cg['radius'],
        'visible_events': {k: v for k, v in spec.get('events', {}).items() if k in ('CigOn', 'LighterOn', 'LighterOff')}}}


def final(A, name, act, N, info, dest):
    BC.final(A, name, act, N, info, dest)
    rep = dest / (stem(name) + '_authoring.json')
    d = json.loads(rep.read_text(encoding='utf-8'))
    d['revision_of'] = '%s_v01' % name
    d['authoring_note'] = 'v02 revision (clips_props_v02.py); contract poses identical to v01'
    att = attachments(name)
    if att:
        d['preview_only_props'] = att
    rep.write_text(json.dumps(d, indent=2), encoding='utf-8')


def manifest(path):
    p = Path(path)
    assert p.is_absolute(), 'manifest path must be absolute'
    BC.manifest(str(p))
    d = json.loads(p.read_text(encoding='utf-8'))
    for name in d['clips']:
        att = attachments(name)
        if att:
            c = att['cigarette']
            d['clips'][name]['unity'] = ('cigarette = separate attachment on %s: grip %s m, rotation (w,x,y,z) %s in the '
                                         'Blender hand-bone frame; see README v02 section for the Unity mapping'
                                         % (c['bone'], c['grip_position_m'], c['rotation_quaternion_wxyz']))
    p.write_text(json.dumps(d, indent=2), encoding='utf-8')
    print('MANIFEST_V02', p)


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
            A = Author()        # fresh scene per clip (the saved file holds one action, review studios do not pile up)
        frames, canonical, info, N = A.frames(name)
        act = A.key(name, frames, canonical, N)
        if a.review:
            review(name, N, a, A.B.scene, A.B.rig)
        if a.final:
            dest = Path(a.dest) if a.dest else HERE
            assert dest.is_absolute()
            dest.mkdir(parents=True, exist_ok=True)
            final(A, name, act, N, info, dest)
        print('BUILT %-20s frames %4d  overreach %.4f  start_gap %.5f  end_gap %.5f  step %5.1f@f%s %-14s max_lift %.3f' % (
            name, N + 1, max(i['over'] for i in info), info[0]['start_gap'], info[-1]['end_gap'], *info[0]['max_step'],
            max(abs(i['dz_contact']) for i in info)), flush=True)


if __name__ == '__main__':
    main()
