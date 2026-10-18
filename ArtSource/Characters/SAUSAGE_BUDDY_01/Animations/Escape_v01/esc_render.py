"""Review renders for Escape_v01 (Eevee, never exported). Studio as in Operation_v01/build_op_v01.py."""
from pathlib import Path
import math
import bpy
from mathutils import Vector
import acting_core as AC

# views in TABLE space: (location, target, ortho scale or None for perspective, lens)
VIEWS = {
    'side': ((3.2, -0.02, 0.95), (0.0, -0.10, 0.80), 2.25, None),             # patient's right (table camera side)
    'three_quarter': ((1.45, 1.65, 1.55), (0.0, -0.15, 0.76), None, 30),       # right / foot end, above
    'top': ((0.0, -0.10, 3.2), (0.0, -0.10, 0.70), 2.1, None),
    'wrist_R': ((0.95, 0.55, 1.75), (0.10, -0.10, 0.80), None, 32),           # over the right arm strap
    'wrist_L': ((-0.95, 0.55, 1.75), (-0.10, -0.10, 0.80), None, 32),
    'feet': ((1.30, 1.60, 1.35), (0.0, 0.25, 0.75), None, 30),
    'exit': ((2.5, -1.9, 1.65), (0.95, 0.40, 0.55), None, 26),                 # wide, right side from the head end
    'exit_side': ((3.0, -2.6, 1.5), (1.0, 0.2, 0.6), None, 28),
    'wrist_R_close': ((0.80, 0.40, 1.22), (0.20, -0.04, 0.77), None, 40),
    'wrist_L_close': ((-0.80, 0.40, 1.22), (-0.20, -0.04, 0.77), None, 40),
    'shins_close': ((0.55, 1.45, 1.20), (0.0, 0.58, 0.70), None, 38),
}


def studio(scene):
    col = bpy.data.collections.get('Studio_NOT_EXPORTED') or bpy.data.collections.new('Studio_NOT_EXPORTED')
    if col.name not in scene.collection.children:
        scene.collection.children.link(col)
    world = bpy.data.worlds.new('Studio')
    scene.world = world
    try:
        world.use_nodes = True
    except Exception:
        pass
    bg = next(n for n in world.node_tree.nodes if n.type == 'BACKGROUND')
    bg.inputs[0].default_value = AC.srgb((150, 158, 166))
    bg.inputs[1].default_value = 0.8

    def light(name, loc, power, size, color=(1, 1, 1)):
        d = bpy.data.lights.new(name, 'AREA'); d.energy = power; d.shape = 'DISK'; d.size = size; d.color = color
        o = bpy.data.objects.new(name, d); o.location = loc
        o.rotation_euler = (Vector((0, 0, 0.7)) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
        col.objects.link(o)
    light('Key', (2.2, 1.4, 3.4), 600, 3.0, (1.0, 0.97, 0.93))
    light('Fill', (-2.6, -1.6, 2.6), 380, 3.5, (0.93, 0.96, 1.0))
    light('Rim', (-0.6, -3.2, 2.6), 300, 2.5)
    me = bpy.data.meshes.new('Studio_Floor')
    me.from_pydata([(-8, -8, 0), (8, -8, 0), (8, 8, 0), (-8, 8, 0)], [], [(0, 1, 2, 3)])
    m = bpy.data.materials.new('Studio_Floor')
    try:
        m.use_nodes = True
    except Exception:
        pass
    bs = next(n for n in m.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
    bs.inputs['Base Color'].default_value = AC.srgb((120, 126, 132))
    bs.inputs['Roughness'].default_value = 0.9
    me.materials.append(m)
    col.objects.link(bpy.data.objects.new('Studio_Floor', me))
    cd = bpy.data.cameras.new('Review_Cam')
    cam = bpy.data.objects.new('Review_Cam', cd)
    col.objects.link(cam)
    scene.camera = cam
    scene.view_settings.view_transform = 'Standard'
    scene.view_settings.exposure = -0.6
    return cam


def aim(cam, view):
    loc, tgt, ortho, lens = VIEWS[view]
    cam.location = loc
    cam.rotation_euler = (Vector(tgt) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
    if ortho:
        cam.data.type = 'ORTHO'
        cam.data.ortho_scale = ortho
    else:
        cam.data.type = 'PERSP'
        cam.data.lens = lens
        cam.data.sensor_width = 36


def setup(scene, res=360, samples=12):
    cam = studio(scene)
    AC.use_eevee(scene, (res, res), samples=samples)
    return cam


def render_to(scene, path):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)
