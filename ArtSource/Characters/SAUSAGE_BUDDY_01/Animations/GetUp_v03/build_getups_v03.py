"""Build the Sausage Buddy get-ups v03 (deterministic; read-only A v04 source rig).

Blender 5.2 headless, run from anywhere:
  blender -b --factory-startup --python build_getups_v03.py -- --clip all --review <scratch dir>
  blender -b --factory-startup --python build_getups_v03.py -- --clip all --final --revision 3
  (python -m pip install bpy==5.2.*; then `python build_getups_v03.py -- ...` works the same way)
--review <dir> renders labelled contact sheets + onion skins (side + three-quarter) of every --every frames
  (--engine workbench: fast software-GL review; eevee: studio look) via render_previews_v03.py.
--final saves GetUp_<clip>_vNN.blend/.fbx + _authoring.json into --outdir (default here); refuses to overwrite
  and refuses while getup_choreo_v03.READY is False.
Without Git LFS set GETUP_SOURCE_BLEND to a rig rebuilt by rebuild_rig_from_json_v03.py (see README).
"""
from pathlib import Path
import sys, json, math, argparse
sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import bpy
import getup_lib_v03 as L
import getup_choreo_v03 as C



def parse_args(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--clip', default='all', choices=('all', 'back', 'belly'))
    ap.add_argument('--review', default='', help='scratch dir: review contact sheets (side + three-quarter)')
    ap.add_argument('--engine', default='workbench', choices=('workbench', 'eevee'))
    ap.add_argument('--every', type=float, default=2.0)
    ap.add_argument("--res", type=int, default=320)
    ap.add_argument("--cols", type=int, default=12)
    ap.add_argument('--final', action='store_true')
    ap.add_argument('--outdir', default=str(HERE), help='--final output folder (default: this folder)')
    ap.add_argument('--revision', type=int, default=3)
    if argv is None:
        argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
    return ap.parse_args(argv)


CLIPS = {'back': ('GetUp_FromBack', C.make_back), 'belly': ('GetUp_FromBelly', C.make_belly)}


def metrics(rig, clip):
    """Per-sample floor clearance by region, hipsStart, and a Stable estimate from the solved poses."""
    P = L.P
    out = {'clip': clip.name, 'frames_0based': [0, clip.N], 'duration_s': clip.N / L.FPS}
    first = clip.poses[0.0]
    hs = first[P + 'Hips'].translation
    out['hipsStart_m'] = [round(hs.x, 6), round(hs.y, 6), round(hs.z, 6)]
    out['start_head_dir'] = [round(c, 4) for c in ((first[P + 'Head'].translation - hs).normalized())]
    sl = rig.region_lows(first)
    out['start_part_heights_m'] = {k: round(sl[k], 4) for k in ('butt', 'upper_back_hood', 'head', 'handL', 'handR',
                                                                 'armL', 'armR', 'legL', 'legR', 'footL', 'footR')}
    worst = {r: 10.0 for r in L.REGIONS}
    for f, d in clip.poses.items():
        lows = rig.region_lows(d)
        for r in L.REGIONS:
            worst[r] = min(worst[r], lows[r])
    out['min_region_height_m'] = {r: round(v, 5) for r, v in worst.items()}
    out['max_floor_lift_m'] = round(max(clip.lift), 5)
    stable = None
    for f in sorted(clip.poses):
        d = clip.poses[f]
        hips = d[P + 'Hips'].translation
        up = (d[P + 'Spine2'].translation - hips).normalized()
        ok = hips.z > 0.6 and math.hypot(hips.x, hips.y) < 0.35 and up.z > math.cos(math.radians(35))
        if ok and stable is None:
            stable = f
        elif not ok:
            stable = None
    out['stable_frame_0based'] = stable
    out['stable_fraction'] = None if stable is None else round(stable / clip.N, 4)
    return out


def export_clip(rig, stem, action, out=HERE):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    for ext in ('.blend', '.fbx'):
        assert not (out / (stem + ext)).exists(), 'Refusing overwrite ' + stem + ext
    r = rig.rig
    assert len(r.data.bones) == 65 and all(abs(s - 1) < 1e-6 for s in r.scale)
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=str(out / (stem + '.blend')))
    r.animation_data.action = None
    for pb in r.pose.bones:
        pb.matrix_basis.identity()
    bpy.context.view_layer.update()
    bpy.ops.object.select_all(action='DESELECT')
    r.select_set(True)
    bpy.context.view_layer.objects.active = r
    bpy.ops.export_scene.fbx(filepath=str(out / (stem + '.fbx')), use_selection=True,
                             object_types={'ARMATURE'}, add_leaf_bones=False, use_armature_deform_only=False,
                             bake_anim=True, bake_anim_use_all_actions=True, bake_anim_use_nla_strips=False,
                             bake_anim_step=.5, bake_anim_simplify_factor=0, axis_forward='-Z', axis_up='Y',
                             apply_unit_scale=True, use_mesh_modifiers=False)
    r.animation_data.action = action
    rig.scene.frame_set(1)
    print('EXPORTED', stem, flush=True)


def build(key):
    """Deterministic build of one clip into the open file. Returns (rig, clip, action, metrics)."""
    name, maker = CLIPS[key]
    rig = L.Rig()
    clip = maker(rig)
    clip.solve(log=lambda m: print('SOLVE', json.dumps(m), flush=True))
    act = clip.key(name + '_' + VERSION)
    m = metrics(rig, clip)
    return rig, clip, act, m


def main(args):
    global VERSION
    VERSION = 'v%02d' % args.revision
    if args.final:
        assert C.READY, 'getup_choreo_v03.READY is False: the performances are stubs; refusing --final'
    for key, (name, maker) in CLIPS.items():
        if args.clip not in ('all', key):
            continue
        stem = name + '_' + VERSION
        rig, clip, act, m = build(key)
        print('METRICS', json.dumps(m), flush=True)
        if args.final:
            rep = Path(args.outdir) / (stem + '_authoring.json')
            rep.parent.mkdir(parents=True, exist_ok=True)
            assert not rep.exists(), 'Refusing overwrite ' + rep.name
            rep.write_text(json.dumps(m, indent=2), encoding='utf-8')
            export_clip(rig, stem, act, args.outdir)
        if args.review:
            import render_previews_v03 as RP
            frames = []
            f = 0.0
            while f <= clip.N + 1e-6:
                frames.append(1 + f)
                f += args.every
            if frames[-1] != 1 + clip.N:
                frames.append(1 + clip.N)
            out = Path(args.review) / name
            RP.setup(rig.scene, args.engine, args.res)
            RP.contact_sheets(rig.scene, out, name, frames, cols=args.cols)
            print('REVIEW_RENDERED', name, len(frames), flush=True)


VERSION = 'v03'
if __name__ == '__main__':
    main(parse_args())
