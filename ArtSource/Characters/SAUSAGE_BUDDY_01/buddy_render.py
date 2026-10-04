"""Review renders for the Sausage Buddy (not exported). Soft grey studio like the owner's reference."""
import math
from pathlib import Path
import bpy
from mathutils import Vector
import buddy_geo as G


def studio(scene):
    col = bpy.data.collections.get('Studio_NOT_EXPORTED') or bpy.data.collections.new('Studio_NOT_EXPORTED')
    if col.name not in scene.collection.children:
        scene.collection.children.link(col)
    world = bpy.data.worlds.new('Studio'); scene.world = world
    try:
        world.use_nodes = True
    except Exception:
        pass
    bg = next(n for n in world.node_tree.nodes if n.type == 'BACKGROUND')
    bg.inputs[0].default_value = G.srgb((196, 198, 204)); bg.inputs[1].default_value = 1.0
    def light(name, loc, power, size, color=(1, 1, 1)):
        d = bpy.data.lights.new(name, 'AREA'); d.energy = power; d.shape = 'DISK'; d.size = size; d.color = color
        o = bpy.data.objects.new(name, d); o.location = loc
        o.rotation_euler = (Vector((0, 0, 1.0)) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
        col.objects.link(o)
    light('Key', (-2.6, -3.4, 3.6), 700, 3.0, (1.0, 0.97, 0.93))
    light('Fill', (3.2, -2.6, 2.2), 300, 3.5, (0.93, 0.96, 1.0))
    light('Rim', (0.8, 3.6, 3.0), 420, 2.5)
    fm = bpy.data.materials.new('Studio_Floor')
    try:
        fm.use_nodes = True
    except Exception:
        pass
    fb = next(n for n in fm.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
    fb.inputs['Base Color'].default_value = G.srgb((196, 198, 204)); fb.inputs['Roughness'].default_value = 0.9
    me = bpy.data.meshes.new('Studio_Floor'); me.from_pydata([(-20, -20, 0), (20, -20, 0), (20, 20, 0), (-20, 20, 0)], [], [(0, 1, 2, 3)])
    me.materials.append(fm)
    fl = bpy.data.objects.new('Studio_Floor', me); col.objects.link(fl)
    cd = bpy.data.cameras.new('Studio_Cam'); cam = bpy.data.objects.new('Studio_Cam', cd); col.objects.link(cam)
    scene.camera = cam
    scene.render.engine = 'CYCLES'
    scene.cycles.samples = 48
    try:
        scene.cycles.use_denoising = True
    except Exception:
        pass
    try:
        prefs = bpy.context.preferences.addons['cycles'].preferences
        for dev in ('OPTIX', 'CUDA'):
            try:
                prefs.compute_device_type = dev; prefs.get_devices()
                if any(d.type == dev for d in prefs.devices):
                    for d in prefs.devices:
                        d.use = True
                    scene.cycles.device = 'GPU'; break
            except Exception:
                continue
    except Exception:
        pass
    scene.view_settings.view_transform = 'Standard'
    scene.view_settings.exposure = -0.85
    return col, cam, fl


def shot(scene, cam, path, loc, target, lens=50, res=(1000, 1200), ortho=None, frame=None):
    if frame is not None:
        scene.frame_set(frame)
    cam.location = loc
    cam.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
    if ortho:
        cam.data.type = 'ORTHO'; cam.data.ortho_scale = ortho
    else:
        cam.data.type = 'PERSP'; cam.data.lens = lens
    scene.render.resolution_x, scene.render.resolution_y = res
    scene.render.filepath = str(path)
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.render.render(write_still=True)
