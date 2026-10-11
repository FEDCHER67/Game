"""Build driver for the Crowd_v01 package (Blender 5.2 or the PyPI `bpy` module, headless).

  python build_crowd.py --clip ShopQueue_Loop --review <dir> [--every 2] [--views side,three_quarter,front] [--res 320]
      author in memory and render review frames (Cycles CPU, nothing saved in the package)
  python build_crowd.py --clip all --final [--dest <dir>]
      author and save <stem>.blend, <stem>.fbx, <stem>_authoring.json per clip (never overwrites)
  python build_crowd.py --clip all --manifest crowd_manifest_v01.json
      write the clip manifest (contracts, events, props, Unity notes) without building
  python build_crowd.py --clip X --trace t.json       joint traces for plotting

(`blender -b --factory-startup --python build_crowd.py -- <args>` works the same.)
Rig input: the A v04 source .blend, or its plain-JSON export in ../Idle_Knock_v03 when the .blend
files are Git LFS pointers (acting_core switches automatically). Every clip is sampled at half-frame
steps (60 Hz) and keyed linearly; the first/last frames are keyed with the exact raw values of their
contract pose, so enter -> loop -> exit chains and loop seams match exactly.
"""
from pathlib import Path
import sys, json, math, argparse
sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import bpy
from mathutils import Vector, Matrix
import crowd_core as K
import acting_core as C
import clips_crowd as CC

REV = 'v01'


def parse():
    argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else sys.argv[1:]
    ap = argparse.ArgumentParser()
    ap.add_argument('--clip', required=True)
    ap.add_argument('--review', default='')
    ap.add_argument('--every', type=float, default=2)
    ap.add_argument('--times', default='')
    ap.add_argument('--views', default='side,three_quarter,front')
    ap.add_argument('--res', type=int, default=320)
    ap.add_argument('--samples', type=int, default=6)
    ap.add_argument('--seq', action='store_true')
    ap.add_argument('--final', action='store_true')
    ap.add_argument('--dest', default='')
    ap.add_argument('--trace', default='')
    ap.add_argument('--manifest', default='')
    return ap.parse_args(argv)


def stem(name):
    return '%s_%s' % (name, REV)


# --------------------------------------------------------------------------------------- authoring
class Author:
    def __init__(self):
        self.B = C.Buddy()
        self.rig = K.Rig(self.B)
        K.RIG = self.rig
        self._contracts = {}

    def setup(self, spec):
        # a keyed action would override every pose we install for mesh evaluation (contacts)
        if self.B.rig.animation_data:
            self.B.rig.animation_data.action = None
        self.rig.surfaces = []
        self.rig.wall_y = None
        for f in spec.get('setup', []):
            f(self.rig)

    def contract_values(self, cname):
        """Raw keyed values of a contract pose (cached, so every clip keys identical numbers)."""
        if cname not in self._contracts:
            if cname == 'idle':
                self._contracts[cname] = self.B.idle_values
            else:
                spec = CC.CONTRACTS[cname]
                self.setup(spec)
                out, _ = self.rig.pose(K.fit_params(spec['params']()))
                self._contracts[cname] = self.B.values_from_pose(out)
        return self._contracts[cname]

    def frames(self, name):
        spec = CC.CLIPS[name]
        T = spec['T']
        N = int(round(T * C.FPS))
        assert abs(N - T * C.FPS) < 1e-6, ('clip length must be a whole number of frames', name, T)
        canonical = {1.0: self.contract_values(spec['start']), float(N + 1): self.contract_values(spec['end'])}
        self.setup(spec)
        frames, info = {}, []
        for i in range(2 * N + 1):
            t = i / (2 * C.FPS)
            p = spec['params'](t)
            pose, extra = self.rig.pose(p)
            frames[1 + i / 2] = pose
            extra = dict(extra)
            extra['t'] = t
            info.append(extra)
        # how far the authored first/last samples are from the contract poses they get keyed with (should be ~0)
        def gap(f, vals):
            ref = self.B.pose_from_values(vals)
            return max((frames[f][n].translation - ref[n].translation).length +
                       2 * math.acos(min(1.0, abs(frames[f][n].to_quaternion().dot(ref[n].to_quaternion())))) * 0.5
                       for n in self.B.order)
        # largest local rotation step between neighbouring half-frame keys (limit 25 deg)
        prev, worst = None, (0.0, None, None)
        for f in sorted(frames):
            cur = {n: v['q'] for n, v in self.B.values_from_pose(frames[f]).items()}
            if prev:
                for n in cur:
                    d = abs(sum(a * b for a, b in zip(prev[n], cur[n])))
                    ang = math.degrees(2 * math.acos(min(1.0, d)))
                    if ang > worst[0]:
                        worst = (ang, f, n[len(K.P):])
            prev = cur
        info[0]['max_step'] = worst
        info[0]['start_gap'] = gap(1.0, canonical[1.0])
        info[-1]['end_gap'] = gap(float(N + 1), canonical[float(N + 1)])
        return frames, canonical, info, N

    def key(self, name, frames, canonical, N):
        B = self.B
        for act in list(bpy.data.actions):
            bpy.data.actions.remove(act)
        act, mismatch = B.key_action(name, frames, canonical)
        assert not mismatch, ('canonical end quaternion sign differs from the continuous chain', name, mismatch[:5])
        spec = CC.CLIPS[name]
        B.scene.frame_start, B.scene.frame_end = 1, N + 1
        B.scene.frame_set(1)
        act['duration_seconds'] = spec['T']
        act['fps'] = C.FPS
        act['loop'] = spec['loop']
        act['authoring'] = 'Original local FK/IK acting (Crowd_v01 package); no external motion reused'
        return act


# --------------------------------------------------------------------------------------- review stage
VIEWS = {
    'side': ((5.2, 0.0, 1.0), (0.0, 0.0, 0.9), 2.3),
    'three_quarter': ((3.6, -4.6, 1.9), (0.0, 0.0, 0.88), 2.3),
    'front': ((0.0, -5.2, 1.0), (0.0, 0.0, 0.9), 2.3),
}


def _mat(name, rgb, rough=0.8):
    m = bpy.data.materials.new(name)
    try:
        m.use_nodes = True
    except Exception:
        pass
    b = next(n for n in m.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
    b.inputs['Base Color'].default_value = C.srgb(rgb)
    b.inputs['Roughness'].default_value = rough
    return m


def box(col, name, lo, hi, rgb):
    (x0, y0, z0), (x1, y1, z1) = lo, hi
    v = [(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0), (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)]
    f = [(0, 1, 2, 3), (4, 7, 6, 5), (0, 4, 5, 1), (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0)]
    me = bpy.data.meshes.new(name)
    me.from_pydata(v, [], f)
    me.materials.append(_mat(name, rgb))
    o = bpy.data.objects.new(name, me)
    col.objects.link(o)
    return o


def build_props(col, props):
    """Review-only props (never exported). Geometry comes from clips_crowd.PROPS (the Unity placement contract)."""
    objs = []
    for kind, data in props:
        if kind == 'box':
            objs.append(box(col, data['name'], data['lo'], data['hi'], data['rgb']))
        elif kind == 'treadmill':
            for i in range(-12, 13):
                o = box(col, 'Stripe%d' % i, (-0.6, i * 0.5 - 0.06, -0.002), (0.6, i * 0.5 + 0.06, 0.0015), (150, 152, 160))
                o['tread_y0'] = i * 0.5
                o['tread_v'] = data['speed']
                objs.append(o)
    return objs


def install_on(B, rig, desired):
    for n in B.order:
        pb = rig.pose.bones[n]
        p = B.parent[n]
        kw = {} if p is None else {'parent_matrix': desired[p], 'parent_matrix_local': B.rest[p]}
        pb.matrix_basis = pb.bone.convert_local_to_pose(desired[n], B.rest[n], invert=True, **kw)


def partner(B, col, place):
    """Second Buddy for two-person clips: a copy of the rig + meshes, posed manually per frame."""
    rig2 = B.rig.copy()
    rig2.animation_data_clear()
    col.objects.link(rig2)
    for o in B.meshes:
        o2 = o.copy()
        o2.parent = rig2
        o2.modifiers['Armature'].object = rig2
        col.objects.link(o2)
    loc, yaw = place
    rig2.matrix_world = Matrix.Translation(loc) @ Matrix.Rotation(math.radians(yaw), 4, 'Z') @ B.rig.matrix_world
    return rig2


def review(A, name, frames, N, a):
    B = A.B
    spec = CC.CLIPS[name]
    col, cam = C.studio(B.scene)
    props = build_props(col, spec.get('props', []))
    sc = B.scene
    sc.render.engine = 'CYCLES'
    sc.cycles.samples = a.samples
    sc.cycles.device = 'CPU'
    try:
        sc.cycles.use_denoising = True
    except Exception:
        pass
    sc.render.resolution_x = sc.render.resolution_y = a.res
    sc.render.image_settings.file_format = 'PNG'
    sc.view_settings.exposure = -0.85
    rig2, pframes = None, None
    if spec.get('partner'):
        pname, offset, place = spec['partner']
        rig2 = partner(B, col, place)
        A.setup(CC.CLIPS[pname])
        pspec = CC.CLIPS[pname]
        pframes = {}
        for f in frames:
            t = ((f - 1) / C.FPS + offset) % pspec['T']
            pframes[f], _ = A.rig.pose(pspec['params'](t), contact=False)
        A.setup(spec)
    out = Path(a.review)
    if a.times:
        fl = [1 + float(x) * C.FPS for x in a.times.split(',')]
    else:
        fl = []
        f = 1.0
        while f < N + 1 - 1e-9:
            fl.append(f)
            f += a.every
        fl.append(float(N + 1))
    views = spec.get('views', VIEWS)
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
            if rig2 is not None:
                fk = min(pframes, key=lambda x: abs(x - f))
                install_on(B, rig2, pframes[fk])
            bpy.context.view_layer.update()
            p = out / v / (('s%04d.png' % k) if a.seq else ('f%07.2f.png' % f))
            p.parent.mkdir(parents=True, exist_ok=True)
            sc.render.filepath = str(p)
            bpy.ops.render.render(write_still=True)
    print('REVIEW_DONE', name, len(fl), flush=True)


# --------------------------------------------------------------------------------------- final
def final(A, name, act, N, info, dest):
    B = A.B
    st = stem(name)
    for ext in ('.blend', '.fbx'):
        assert not (dest / (st + ext)).exists(), 'Refusing overwrite ' + st + ext
    rep = dest / (st + '_authoring.json')
    assert not rep.exists(), 'Refusing overwrite ' + rep.name
    assert len(B.rig.data.bones) == 65
    act.name = name
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=str(dest / (st + '.blend')))
    B.export_fbx(act, dest / (st + '.fbx'))
    spec = CC.CLIPS[name]
    rep.write_text(json.dumps({
        'clip': name, 'file_stem': st, 'action': act.name, 'frames': [1, N + 1], 'fps': C.FPS,
        'duration_s': spec['T'], 'loop': spec['loop'], 'start_contract': spec['start'], 'end_contract': spec['end'],
        'sampling': 'half-frame keys (60 Hz), linear interpolation', 'beats': spec.get('beats', []),
        'events': spec.get('events', {}),
        'max_leg_overreach_m': max(i['over'] for i in info),
        'max_contact_lift_m': max(abs(i['dz_contact']) for i in info),
    }, indent=2), encoding='utf-8')
    print('FINAL_SAVED', st, flush=True)


def manifest(path):
    p = Path(path)
    assert not p.exists(), 'Refusing overwrite ' + str(p)
    clips = {}
    for name, s in CC.CLIPS.items():
        clips[name] = {'file': stem(name) + '.fbx', 'take': 'Buddy_Rig_Mixamo65|' + name, 'frames': [1, int(round(s['T'] * C.FPS)) + 1],
                       'duration_s': s['T'], 'loop': s['loop'], 'start_contract': s['start'], 'end_contract': s['end'],
                       'activity': s.get('activity'), 'role': s.get('role'), 'events': s.get('events', {}),
                       'unity': s.get('unity', '')}
    p.write_text(json.dumps({'package': 'Crowd_' + REV, 'fps': C.FPS, 'rig': 'Buddy_Rig_Mixamo65 (65 bones, root mixamorig:Hips)',
                             'contracts': {k: v['doc'] for k, v in CC.CONTRACTS.items()} | {'idle': 'A v04 Idle frame 1 (exact raw values)'},
                             'placement': CC.PLACEMENT, 'clips': clips}, indent=2), encoding='utf-8')
    print('MANIFEST', p)


def main():
    a = parse()
    if a.manifest:
        manifest(a.manifest)
        return
    names = list(CC.CLIPS) if a.clip == 'all' else a.clip.split(',')
    A = Author()
    for name in names:
        frames, canonical, info, N = A.frames(name)
        if a.trace:
            pts = ('HeadTop_End', 'Head', 'Hips', 'LeftHand', 'RightHand', 'LeftFoot', 'RightFoot')
            Path(a.trace).write_text(json.dumps({'T': CC.CLIPS[name]['T'], 'points': {
                q: [list(frames[f][C.P + q].translation) for f in sorted(frames)] for q in pts}}), encoding='utf-8')
        act = A.key(name, frames, canonical, N)
        if a.review:
            review(A, name, frames, N, a)
        if a.final:
            dest = Path(a.dest) if a.dest else HERE
            dest.mkdir(parents=True, exist_ok=True)
            final(A, name, act, N, info, dest)
            A = Author()        # fresh scene for the next clip (the saved file holds one action)
        print('BUILT %-20s frames %4d  overreach %.4f  start_gap %.5f  end_gap %.5f  step %5.1f@f%s %-14s max_lift %.3f' % (
            name, N + 1, max(i['over'] for i in info), info[0]['start_gap'], info[-1]['end_gap'], *info[0]['max_step'],
            max(abs(i['dz_contact']) for i in info)), flush=True)


if __name__ == '__main__':
    main()
