"""Preview renders for Workshop_W86 v01 (Eevee). Opens Workshop_W86_v01.blend, swaps in project textures,
adds a dirt ground, sun/sky, interior lights at the lamp anchors and a van-size dummy (render only, not exported).
  blender -b --factory-startup -noaudio --python render_workshop_w86_v01.py -- [views...] [--force]
Writes preview_v01_<view>.png next to the FBX files.
"""
import math
import os
import sys

import bpy
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_workshop_w86_v01 as B  # noqa: E402

ARGS = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
FORCE = '--force' in ARGS
OUT = B.OUT
VIEWS = {
    #  name: (cam loc, look at, lens, ortho_scale, res, van, sun_strength)
    'exterior34': ((-16.5, -25.0, 1.7), (0.5, -3.0, 2.2), 30, None, (1600, 900), False),
    'exterior_west': ((16.5, -18.5, 1.7), (4.5, -4.0, 1.9), 30, None, (1600, 900), False),
    'exterior_detail': ((-4.6, -10.5, 1.65), (-7.6, -6.0, 1.7), 35, None, (1600, 900), False),
    'top': ((0.0, -4.3, 60.0), (0.0, -4.3, 0.0), None, 34.0, (1280, 960), False),
    'middlebay_van': ((-3.0, 4.55, 1.7), (0.4, -3.2, 0.9), 20, None, (1600, 900), True),
    'middlebay_pit': ((0.0, -5.45, 1.7), (0.0, 3.0, 0.5), 20, None, (1600, 900), False),
    'mechanic_corner': ((0.4, -0.6, 1.7), (4.2, 3.9, 1.0), 22, None, (1600, 900), False),
    'westbay': ((5.15, -5.35, 1.7), (10.3, 4.2, 1.2), 20, None, (1600, 900), False),
}


def look_at(ob, target):
    d = Vector(target) - ob.location
    ob.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()


def setup():
    bpy.ops.wm.open_mainfile(filepath=os.path.join(OUT, 'Workshop_W86_v01.blend'))
    sc = bpy.context.scene
    lib = {m.name: m for m in bpy.data.materials if m.name.startswith('MAT_WS_')}
    B.texture_materials(lib)
    try:
        sc.render.engine = 'BLENDER_EEVEE'
    except TypeError as e:
        print('engine', e)
    ee = sc.eevee
    for attr, val in (('shadow_pool_size', '1024'), ('taa_render_samples', 48), ('use_raytracing', True), ('use_shadows', True),
                      ('fast_gi_method', 'GLOBAL_ILLUMINATION'), ('use_fast_gi', True)):
        try:
            setattr(ee, attr, val)
        except Exception:
            pass
    try:
        sc.view_settings.view_transform = 'AgX'
        sc.view_settings.look = 'AgX - Medium High Contrast'
    except Exception:
        pass
    # hide colliders and the optional west-door curtain (default state = open)
    for o in bpy.data.objects:
        if o.name.startswith('WS_DoorWest_Curtain'):
            o.hide_render = True
        if o.name.startswith('UCX_'):
            o.hide_render = True
            o.hide_viewport = True
        if o.name.endswith('_LOD1'):
            o.hide_render = True
    # world
    w = bpy.data.worlds.new('WS_Sky')
    sc.world = w
    w.use_nodes = True
    bg = next(n for n in w.node_tree.nodes if n.type == 'BACKGROUND')
    bg.inputs['Color'].default_value = (0.52, 0.64, 0.82, 1.0)
    bg.inputs['Strength'].default_value = 1.1
    rc = bpy.data.collections.new('WS_RenderOnly')
    sc.collection.children.link(rc)
    # sun
    sun = bpy.data.objects.new('Sun', bpy.data.lights.new('Sun', 'SUN'))
    rc.objects.link(sun)
    sun.data.energy = 4.0
    sun.data.angle = math.radians(2.0)
    sun.rotation_euler = Vector((0.55, 0.85, -0.75)).to_track_quat('-Z', 'Y').to_euler()
    # ground (terrain stand-in, dirt road texture like layer L03)
    me = bpy.data.meshes.new('Ground')
    s, z = 60.0, -0.03
    hx, hy = B.HX, B.HY  # no ground inside the footprint (the pit must stay open, as with a terrain hole in Unity)
    vs = [(-s, -s, z), (s, -s, z), (s, s, z), (-s, s, z), (-hx, -hy, z), (hx, -hy, z), (hx, hy, z), (-hx, hy, z)]
    fs = [(0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
    me.from_pydata(vs, [], fs)
    uv = me.uv_layers.new()
    for lp in me.loops:
        v = me.vertices[lp.vertex_index].co
        uv.data[lp.index].uv = (v.x, v.y)
    gm = bpy.data.materials.new('Ground_dirt')
    gm.use_nodes = True
    nt = gm.node_tree
    bsdf = next(n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED')
    tc = nt.nodes.new('ShaderNodeTexCoord')
    mp = nt.nodes.new('ShaderNodeMapping')
    mp.inputs['Scale'].default_value = (1 / 6.0, 1 / 6.0, 1)
    im = nt.nodes.new('ShaderNodeTexImage')
    im.image = bpy.data.images.load(B.ART + 'StyleKit_v3/Textures/1b_dirt_road/1b_dirt_road_v07_albedo.png')
    nt.links.new(tc.outputs['UV'], mp.inputs['Vector'])
    nt.links.new(mp.outputs['Vector'], im.inputs['Vector'])
    nt.links.new(im.outputs['Color'], bsdf.inputs['Base Color'])
    bsdf.inputs['Roughness'].default_value = 0.95
    me.materials.append(gm)
    g = bpy.data.objects.new('Ground', me)
    rc.objects.link(g)
    # interior lights at the lamp anchors
    for i, (x, y) in enumerate(B.LAMPS):
        L = bpy.data.lights.new('Strip%02d' % i, 'AREA')
        L.shape = 'RECTANGLE'
        L.size, L.size_y = 0.16, 1.2
        L.energy = 120.0
        L.color = (1.0, 0.95, 0.86)
        o = bpy.data.objects.new('Strip%02d' % i, L)
        rc.objects.link(o)
        o.location = (x, y, B.LAMP_Z - 0.09)
    for name, p, e in (('Bulk', (9.4, B.IY - 0.3, 2.6), 25.0),):
        L = bpy.data.lights.new(name, 'POINT')
        L.energy = e
        L.color = (1.0, 0.9, 0.75)
        L.shadow_soft_size = 0.1
        o = bpy.data.objects.new(name, L)
        rc.objects.link(o)
        o.location = p
    # van-size dummy (5.2 x 2.0 x 2.4) over the pit
    van = bpy.data.objects.new('VanDummy', bpy.data.meshes.new('VanDummy'))
    rc.objects.link(van)
    vb = B.MB('van')
    cx, cy = B.VAN['centre']
    vb.box((cx - 1.0, cy - 2.6, 0.36), (cx + 1.0, cy + 2.6, 2.4), 'VAN')
    for sx in (-1, 1):
        for sy in (-1, 1):
            vb.cyl((cx + sx * 0.78, cy + sy * 1.65, 0.33), (cx + sx * 1.0, cy + sy * 1.65, 0.33), 0.33, 'VANW', n=12)
    vm = bpy.data.materials.new('VAN')
    vm.use_nodes = True
    next(n for n in vm.node_tree.nodes if n.type == 'BSDF_PRINCIPLED').inputs['Base Color'].default_value = (0.55, 0.62, 0.7, 1)
    wm = bpy.data.materials.new('VANW')
    wm.use_nodes = True
    next(n for n in wm.node_tree.nodes if n.type == 'BSDF_PRINCIPLED').inputs['Base Color'].default_value = (0.02, 0.02, 0.02, 1)
    vo = vb.build({'VAN': vm, 'VANW': wm}, rc, name='VanDummyMesh')
    bpy.data.objects.remove(van)
    cam = bpy.data.objects.new('Cam', bpy.data.cameras.new('Cam'))
    rc.objects.link(cam)
    sc.camera = cam
    cam.data.clip_start = 0.05
    cam.data.clip_end = 500
    return sc, cam, vo


def main():
    sc, cam, van = setup()
    views = [v for v in ARGS if v in VIEWS] or list(VIEWS)
    for v in views:
        loc, tgt, lens, ortho, res, show_van = VIEWS[v]
        path = os.path.join(OUT, 'preview_v01_%s.png' % v)
        if os.path.exists(path) and not FORCE:
            print('skip existing', path)
            continue
        cam.location = loc
        look_at(cam, tgt)
        if ortho:
            cam.data.type = 'ORTHO'
            cam.data.ortho_scale = ortho
        else:
            cam.data.type = 'PERSP'
            cam.data.lens = lens
        van.hide_render = not show_van
        sc.render.resolution_x, sc.render.resolution_y = res
        sc.render.resolution_percentage = 100
        sc.render.filepath = path
        bpy.ops.render.render(write_still=True)
        print('rendered', path)


if __name__ == '__main__':
    main()
