"""Preview renders for the Workshop_W86 lift v01 (Eevee), in the approved workshop.
Opens Workshop_W86_v01.blend through render_workshop_w86_v01.setup() (same textures, sky, lights, ground), hides its old van
dummy, appends the lift (collection WS_Lift) from Workshop_W86_lift_v01.blend and adds a van-size dummy
(5.2 x 2.0 x 2.4, wheelbase 3.16, render only).  Never saves the .blend.
  blender -b --factory-startup -noaudio --python render_workshop_w86_lift_v01.py -- [views...] [--force] [--quick] [--out DIR]
Writes preview_lift_v01_<view>.png.
"""
import math
import os
import sys

import bpy
from mathutils import Vector, Matrix

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import render_workshop_w86_v01 as R  # noqa: E402
import build_workshop_w86_v01 as B  # noqa: E402

ARGS = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
FORCE = '--force' in ARGS
QUICK = '--quick' in ARGS
OUT = ARGS[ARGS.index('--out') + 1] if '--out' in ARGS else B.OUT
LIFT_BLEND = ARGS[ARGS.index('--lift') + 1] if '--lift' in ARGS else os.path.join(B.OUT, 'Workshop_W86_lift_v01.blend')
LC = Vector((0.0, B.VAN['centre'][1], 0.0))
TRAVEL = 1.6

# name: (cam loc, look at, lens or None, ortho scale, res, van ('none'|'rest'|'raised'|'wheels'), lift, arms engaged, cam roll deg)
VIEWS = {
    'down': ((3.05, -5.5, 2.05), (-0.55, -1.7, 1.45), 17, None, (1600, 900), 'none', 0.0, False, 0),
    'up': ((-3.3, 4.6, 3.0), (0.3, -2.6, 2.55), 16, None, (1600, 900), 'raised', TRAVEL, True, 0),
    'eye': ((3.7, -5.2, 1.7), (0.0, -2.0, 2.3), 17, None, (1600, 900), 'raised', TRAVEL, True, 0),
    'elevation': ((0.0, -5.25, 2.55), (0.0, 2.0, 2.55), None, 9.6, (1600, 900), 'raised', TRAVEL, True, 0),
    'plan': ((0.0, -2.4, 3.7), (0.0, -2.4, 0.0), None, 8.6, (1600, 900), 'wheels', 0.0, True, 90),
    'detail': ((3.35, -3.95, 1.5), (1.85, -2.4, 0.95), 28, None, (1600, 900), 'none', 0.0, False, 0),
}


def look_at(ob, target, roll=0.0):
    d = Vector(target) - ob.location
    q = d.to_track_quat('-Z', 'Y')
    if roll:
        q = q @ Matrix.Rotation(math.radians(roll), 4, 'Z').to_quaternion()
    ob.rotation_euler = q.to_euler()


def setup():
    sc, cam, old_van = R.setup()
    old_van.hide_render = True
    with bpy.data.libraries.load(LIFT_BLEND, link=False) as (src, dst):
        dst.collections = [c for c in src.collections if c == 'WS_Lift']
    for c in dst.collections:
        sc.collection.children.link(c)
    # appended MAT_WS_*.001 -> the textured workshop materials
    for m in list(bpy.data.materials):
        if m.name.startswith('MAT_WS_') and '.' in m.name:
            base = bpy.data.materials.get(m.name.split('.')[0])
            if base:
                m.user_remap(base)
    for o in bpy.data.objects:
        if o.name.startswith('UCX_'):
            o.hide_render = True
            o.hide_viewport = True
        if o.name.endswith('_LOD1'):
            o.hide_render = True
    holders = {o.name: o for o in bpy.data.objects if o.name.startswith('Lift_') and o.type == 'EMPTY'}
    rest = {n: o.location.copy() for n, o in holders.items()}
    # van-size dummy: body + windscreen at the nose (+Y = back wall) + wheels, wheelbase 3.16
    rc = bpy.data.collections['WS_RenderOnly']
    vroot = bpy.data.objects.new('VanDummy2', None)
    rc.objects.link(vroot)
    vroot.location = LC
    vb, wb = B.MB('vanbody'), B.MB('vanwheels')
    vb.box((-1.0, -2.6, 0.36), (1.0, 2.6, 2.4), 'VAN')
    vb.box((-0.88, 2.6, 1.25), (0.88, 2.605, 2.1), 'VANG', skip=('y-',))
    for sx in (-1, 1):
        for sy in (-1, 1):
            wb.cyl((sx * 0.78, sy * 1.58, 0.35), (sx * 1.0, sy * 1.58, 0.35), 0.35, 'VANW', n=16)
    mats = {}
    for name, col in (('VAN', (0.55, 0.62, 0.7, 1)), ('VANW', (0.02, 0.02, 0.02, 1)), ('VANG', (0.08, 0.1, 0.12, 1))):
        m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
        m.use_nodes = True
        next(n for n in m.node_tree.nodes if n.type == 'BSDF_PRINCIPLED').inputs['Base Color'].default_value = col
        mats[name] = m
    body = vb.build(mats, rc, name='VanDummy2_Body')
    wheels = wb.build(mats, rc, name='VanDummy2_Wheels')
    for o in (body, wheels):
        o.parent = vroot
    return sc, cam, holders, rest, vroot, body, wheels


def pose(holders, rest, lift, engaged):
    sys.path.insert(0, HERE)
    import build_workshop_w86_lift_v01 as LB
    for n, o in holders.items():
        if n == 'Lift_Static':
            continue
        o.location = rest[n] + Vector((0, 0, lift))
        if n.startswith('Lift_Arms_'):
            o.rotation_euler = (0, 0, math.radians(LB.arm_engaged_blender_deg(n[-2:])) if engaged else 0.0)


def main():
    sc, cam, holders, rest, vroot, body, wheels = setup()
    views = [v for v in ARGS if v in VIEWS] or list(VIEWS)
    if QUICK:
        sc.eevee.taa_render_samples = 8
    for v in views:
        loc, tgt, lens, ortho, res, van, lift, eng, roll = VIEWS[v]
        path = os.path.join(OUT, 'preview_lift_v01_%s.png' % v)
        if os.path.exists(path) and not FORCE:
            print('skip existing', path)
            continue
        pose(holders, rest, lift, eng)
        vroot.location = LC + Vector((0, 0, TRAVEL if van == 'raised' else 0.0))
        body.hide_render = van in ('none', 'wheels')
        wheels.hide_render = van == 'none'
        cam.location = loc
        look_at(cam, tgt, roll)
        cam.data.clip_start = 0.01 if ortho else 0.05
        if ortho:
            cam.data.type = 'ORTHO'
            cam.data.ortho_scale = ortho
        else:
            cam.data.type = 'PERSP'
            cam.data.lens = lens
        sc.render.resolution_x, sc.render.resolution_y = res
        sc.render.resolution_percentage = 50 if QUICK else 100
        sc.render.filepath = path
        bpy.context.view_layer.update()
        bpy.ops.render.render(write_still=True)
        print('rendered', path)


if __name__ == '__main__':
    main()
