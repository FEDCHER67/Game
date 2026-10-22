"""Renders one Eevee tile per asset .blend (LOD0, 3/4 view, 1.75 m scale figure).

blender -b --factory-startup -P render_tiles.py -- --out DIR [--size 640x480] [--lod 0|1] [--view 35,18] [--variant A] blend1 blend2 ...
"""
import math, sys
from pathlib import Path

import bpy
from mathutils import Vector

argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
out, size, lod, view, variant, blends = None, (640, 480), 0, (-35.0, 18.0), 'A', []
i = 0
while i < len(argv):
    a = argv[i]
    if a == '--out':
        out = Path(argv[i + 1]); i += 2
    elif a == '--size':
        w, h = argv[i + 1].split('x'); size = (int(w), int(h)); i += 2
    elif a == '--lod':
        lod = int(argv[i + 1]); i += 2
    elif a == '--view':
        az, el = argv[i + 1].split(','); view = (float(az), float(el)); i += 2
    elif a == '--variant':
        variant = argv[i + 1]; i += 2
    else:
        blends.append(a); i += 1
out.mkdir(parents=True, exist_ok=True)


def lin(c):
    return tuple(((v / 255) / 12.92 if v / 255 <= 0.04045 else ((v / 255 + 0.055) / 1.055) ** 2.4) for v in c)


for bp in blends:
    bpy.ops.wm.open_mainfile(filepath=bp)
    sc = bpy.context.scene
    obs = [o for o in sc.objects if o.type == 'MESH']
    target = next(o for o in obs if o.name.endswith(f'_LOD{lod}'))
    for o in obs:
        o.hide_render = o is not target
        o.hide_set(o is not target)
    name = target.name.rsplit('_LOD', 1)[0]
    if variant != 'A':
        for m in target.data.materials:
            for n in m.node_tree.nodes:
                if n.type == 'TEX_IMAGE' and n.image:
                    p = Path(bpy.path.abspath(n.image.filepath))
                    alt = p.with_name(p.name.replace('_A.png', f'_{variant}.png'))
                    n.image = bpy.data.images.load(str(alt), check_existing=True)
    co = [target.matrix_world @ v.co for v in target.data.vertices]
    lo = Vector([min(c[k] for c in co) for k in range(3)])
    hi = Vector([max(c[k] for c in co) for k in range(3)])
    water = lo.z < -0.05
    # world, sun
    world = bpy.data.worlds.new('W')
    sc.world = world
    world.use_nodes = True
    bg = next(n for n in world.node_tree.nodes if n.type == 'BACKGROUND')
    bg.inputs[0].default_value = (*lin((200, 214, 228)), 1)
    bg.inputs[1].default_value = 0.9
    sd = bpy.data.lights.new('Sun', 'SUN')
    sd.energy = 3.6
    sd.angle = math.radians(3)
    sun = bpy.data.objects.new('Sun', sd)
    sun.rotation_euler = (math.radians(42), 0, math.radians(-150))
    sc.collection.objects.link(sun)
    # ground or water
    gm = bpy.data.materials.new('G')
    gm.use_nodes = True
    gb = next(n for n in gm.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
    gb.inputs['Base Color'].default_value = (*lin((46, 152, 214) if water else (196, 190, 176)), 1)
    gb.inputs['Roughness'].default_value = 0.6 if water else 1.0
    bpy.ops.mesh.primitive_plane_add(size=400, location=(0, 0, 0))
    g = bpy.context.active_object
    g.data.materials.append(gm)
    # scale figure 0.45 x 0.3 x 1.75
    pm = bpy.data.materials.new('P')
    pm.use_nodes = True
    next(n for n in pm.node_tree.nodes if n.type == 'BSDF_PRINCIPLED').inputs['Base Color'].default_value = (*lin((70, 74, 84)), 1)
    bpy.ops.mesh.primitive_cube_add(size=1, location=(hi.x + 0.7, lo.y + 0.4, 0.875))
    p = bpy.context.active_object
    p.scale = (0.45, 0.3, 1.75)
    p.data.materials.append(pm)
    if water:
        p.hide_render = True
    # camera
    cam_d = bpy.data.cameras.new('C')
    cam = bpy.data.objects.new('C', cam_d)
    sc.collection.objects.link(cam)
    sc.camera = cam
    az, el = map(math.radians, view)
    d = Vector((math.cos(el) * math.sin(az), -math.cos(el) * math.cos(az), math.sin(el)))
    rot = (-d).to_track_quat('-Z', 'Y')
    pts = [Vector((x, y, z)) for x in (lo.x, hi.x) for y in (lo.y, hi.y) for z in (max(lo.z, -0.2), hi.z)]
    if not water:
        pts += [Vector((hi.x + 0.95, lo.y + 0.25, 1.75))]
    centre = sum(pts, Vector()) / len(pts)
    right, up = rot @ Vector((1, 0, 0)), rot @ Vector((0, 1, 0))
    xs = [(q - centre).dot(right) for q in pts]
    ys = [(q - centre).dot(up) for q in pts]
    centre = centre + right * (max(xs) + min(xs)) / 2 + up * (max(ys) + min(ys)) / 2
    wext, hext = max(xs) - min(xs), max(ys) - min(ys)
    aspect = size[0] / size[1]
    cam_d.type = 'ORTHO'
    cam_d.ortho_scale = max(wext, hext * aspect) * 1.12
    dist = (hi - lo).length * 3 + 20
    cam.location = centre + d * dist
    cam.rotation_euler = rot.to_euler()
    cam_d.clip_end = dist * 3
    sc.render.engine = 'BLENDER_EEVEE'
    try:
        sc.eevee.use_shadows = True
    except Exception:
        pass
    sc.view_settings.view_transform = 'Standard'
    sc.render.resolution_x, sc.render.resolution_y = size
    sc.render.film_transparent = False
    sc.render.image_settings.file_format = 'PNG'
    suffix = '' if lod == 0 else f'_LOD{lod}'
    suffix += '' if variant == 'A' else f'_{variant}'
    sc.render.filepath = str(out / f'{name}{suffix}.png')
    bpy.ops.render.render(write_still=True)
    print('[tile]', name, target.name, len(target.data.polygons), 'tris', flush=True)
