"""Side-by-side review renders: a type's source revision vs its opt_v01 derivative, from first-person gameplay cameras
(vertical FOV 60, eye height 1.65 m): 1.2 m (closest normal view, Idle) and 4 m (whole body, panic run frame).

  blender -b --factory-startup --python ArtSource/Characters/SAUSAGE_BUDDY_01/Types_opt_v01/render_compare_opt_v01.py -- --types A,B --out DIR

Writes DIR/<TYPE>_{orig,opt}_{near,far}.png (1920x1080 crops). Assemble the sheet with ImageMagick.
"""
import argparse, math, sys
from pathlib import Path
import bpy
from mathutils import Vector

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent)); sys.path.insert(0, str(HERE))
sys.dont_write_bytecode = True
import buddy_render as RD          # noqa: E402
from build_types_opt_v01 import POOL, TYPES_DIR, TAG   # noqa: E402

EYE = 1.65
SHOTS = [('near', 1.2, 'Idle', 1, (0.0, 1.30)), ('far', 4.0, 'Panic_Run_Loop', 5, (0.0, 1.0))]


ENGINE = 'CYCLES'
NO_SHADOWS = False


def setup(path):
    bpy.ops.wm.open_mainfile(filepath=str(path))
    scene = bpy.context.scene
    face = bpy.data.objects.get('Face')
    if face is not None and face.data.shape_keys:
        if face.data.shape_keys.animation_data:
            face.data.shape_keys.animation_data.action = None
        for k in face.data.shape_keys.key_blocks:
            k.value = 0.0
    for o in bpy.data.objects:            # loose preview props (the phone) stay out of the shot
        if o.type == 'MESH' and o.parent is None:
            o.hide_render = True
    col, cam, floor = RD.studio(scene)
    scene.cycles.samples = 32
    if ENGINE != 'CYCLES':
        scene.render.engine = ENGINE
        for m in bpy.data.materials:          # single-sided like the game's URP Lit
            m.use_backface_culling = True
        if NO_SHADOWS:
            for l in bpy.data.lights:
                l.use_shadow = False
    cam.data.sensor_fit = 'VERTICAL'
    cam.data.sensor_height = 24.0
    return scene, cam


def shoot(scene, cam, out, stem):
    rig = bpy.data.objects['Buddy_Rig_Mixamo65']
    rig.data.pose_position = 'POSE'
    for name, dist, act, frame, (dx, look_z) in SHOTS:
        rig.animation_data.action = bpy.data.actions[act]
        # camera in front of the character, 25 degrees to its right, at eye height
        a = math.radians(25)
        loc = (math.sin(a) * dist, -math.cos(a) * dist, EYE)
        cam.data.lens = 12.0 / math.tan(math.radians(30))
        RD.shot(scene, cam, out / f'{stem}_{name}.png', loc, (dx, 0, look_z), lens=cam.data.lens, res=(1920, 1080), frame=frame)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--types', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--opt-dir', default=str(HERE))
    ap.add_argument('--engine', default='CYCLES', help='CYCLES or BLENDER_EEVEE (rasterised, backface culling)')
    ap.add_argument('--no-shadows', action='store_true', help='Eevee: lights without shadows (separates shading from self-shadowing)')
    args, _ = ap.parse_known_args(sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else [])
    out = Path(args.out); out.mkdir(parents=True, exist_ok=True)
    global ENGINE, NO_SHADOWS
    ENGINE = args.engine
    NO_SHADOWS = args.no_shadows
    revs = dict(POOL)
    for tid in args.types.split(','):
        rev = revs[tid]
        orig = TYPES_DIR / tid / f'SAUSAGE_BUDDY_{tid}_v{rev:02d}.blend'
        opt = Path(args.opt_dir) / f'SAUSAGE_BUDDY_{tid}_v{rev:02d}_{TAG}.blend'
        for kind, path in (('orig', orig), ('opt', opt)):
            scene, cam = setup(path)
            shoot(scene, cam, out, f'{tid}_{kind}')
            print('[CMP]', tid, kind, 'done', flush=True)


if __name__ == '__main__':
    main()
