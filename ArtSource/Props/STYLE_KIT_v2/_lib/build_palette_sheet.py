"""Renders _lib/Look_Palette_v2_sheet.png: the kit palette as a labelled, unlit chart (bible 12: "palette sheet,
generated from JSON"). Every chip is an emission-only plane in its exact sRGB swatch (Standard view transform), so the
sheet shows the hex values as stored in docs/art/STYLE_BIBLE_v2.md appendix A.

  "C:/Program Files/Blender Foundation/Blender 5.2/blender.exe" -b --factory-startup \
      --python ArtSource/Props/STYLE_KIT_v2/_lib/build_palette_sheet.py [-- --out Look_Palette_v2b_sheet.png]

v02b: --out writes a new file (the v01 sheet stays); the core count and the gradient spacing follow the bible JSON.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import stylekit2 as sk                                   # noqa: E402
import bpy                                               # noqa: E402

OUT = 'Look_Palette_v2_sheet.png'
if '--' in sys.argv and '--out' in sys.argv[sys.argv.index('--'):]:
    OUT = sys.argv[sys.argv.index('--out') + 1]
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
_mats = {}


def emit(rgb, key):
    if key in _mats:
        return _mats[key]
    m = bpy.data.materials.new(f'Chip_{key}')
    m.use_nodes = True
    nt = m.node_tree
    for n in list(nt.nodes):
        if n.type != 'OUTPUT_MATERIAL':
            nt.nodes.remove(n)
    e = nt.nodes.new('ShaderNodeEmission')
    e.inputs['Color'].default_value = (*sk.srgb_to_linear(rgb), 1.0)
    e.inputs['Strength'].default_value = 1.0
    nt.links.new(e.outputs[0], next(n for n in nt.nodes if n.type == 'OUTPUT_MATERIAL').inputs['Surface'])
    _mats[key] = m
    return m


def chip(x, y, w, h, rgb, key, z=0.0):
    me = bpy.data.meshes.new(f'chip_{key}')
    me.from_pydata([(x, y, z), (x + w, y, z), (x + w, y + h, z), (x, y + h, z)], [], [(0, 1, 2, 3)])
    me.materials.append(emit(rgb, key))
    ob = bpy.data.objects.new(f'chip_{key}', me)
    scene.collection.objects.link(ob)


def grad_chip(x, y, w, h, gname, steps=48):
    for i in range(steps):
        t = (i + 0.5) / steps
        rgb = tuple(round(c) for c in sk.grad_rgb(gname, t))
        chip(x, y + h * i / steps, w, h / steps + 1e-4, rgb, f'{gname}_{i}')


def label(x, y, text, size=0.17, col=(40, 43, 48)):
    cu = bpy.data.curves.new(f'txt_{x:.2f}_{y:.2f}', 'FONT')
    cu.body = text
    cu.size = size
    ob = bpy.data.objects.new(cu.name, cu)
    ob.location = (x, y, 0.001)
    ob.data.materials.append(emit(col, f'text_{col}'))
    scene.collection.objects.link(ob)


def lstar(rgb):
    r, g, b = sk.srgb_to_linear(rgb)
    Y = 0.2126 * r + 0.7152 * g + 0.0722 * b
    f = Y ** (1 / 3) if Y > 216 / 24389 else (24389 / 27 * Y + 16) / 116
    return 116 * f - 16


W_COLS, CW, CH, GX, GY = 6, 2.1, 1.0, 2.5, 1.75
chip(-0.6, -11.7, 16.8, 13.3, (250, 248, 244), 'paper', z=-0.01)
label(0.0, 1.2, f'Look_Palette_v2 - STYLE_BIBLE_v2 appendix A ({len(sk.CORE)} core swatches, light / dark ramp steps, accents, gradients)', 0.26)
for i, name in enumerate(sk.CORE):
    cx, cy = (i % W_COLS) * GX, -(i // W_COLS) * GY
    chip(cx, cy, CW * 0.62, CH, sk.SWATCH[name], name)
    chip(cx + CW * 0.64, cy + CH * 0.52, CW * 0.36, CH * 0.48, sk.SWATCH[name + '.light'], name + '.light')
    chip(cx + CW * 0.64, cy, CW * 0.36, CH * 0.48, sk.SWATCH[name + '.dark'], name + '.dark')
    label(cx, cy - 0.27, f"{name}  {sk._hexstr(sk.SWATCH[name])}  L*{lstar(sk.SWATCH[name]):.0f}", 0.15)
y0 = -(len(sk.CORE) // W_COLS + 1) * GY - 0.4
label(0.0, y0 + 1.25, 'accents (light / dark where defined; neon and lamp_glow are emission only)', 0.18)
for i, name in enumerate(sk.ACCENTS):
    cx = i * 1.75
    chip(cx, y0, 1.1, CH * 0.8, sk.SWATCH[name], name)
    if name + '.light' in sk.SWATCH:
        chip(cx + 1.15, y0 + 0.42, 0.4, 0.38, sk.SWATCH[name + '.light'], name + '.light')
        chip(cx + 1.15, y0, 0.4, 0.38, sk.SWATCH[name + '.dark'], name + '.dark')
    label(cx, y0 - 0.25, f'{name} {sk._hexstr(sk.SWATCH[name])}', 0.13)
y1 = y0 - 3.4
label(0.0, y1 + 2.35, 'vertical gradients (V = height fraction of the shape): crowns, bushes, grass, water', 0.18)
GSTEP = min(1.75, 15.6 / max(1, len(sk.GRAD)))
for i, gname in enumerate(sk.GRAD):
    cx = i * GSTEP
    grad_chip(cx, y1, min(1.1, GSTEP - 0.3), 2.0, gname)
    label(cx, y1 - 0.25, gname.replace('grad.', ''), 0.15)

cam_d = bpy.data.cameras.new('Cam')
cam_d.type = 'ORTHO'
cam_d.ortho_scale = 16.8
cam = bpy.data.objects.new('Cam', cam_d)
scene.collection.objects.link(cam)
cam.location = (7.8, -5.05, 10.0)
scene.camera = cam
scene.render.resolution_x, scene.render.resolution_y = 2000, 1600
try:
    scene.render.engine = 'CYCLES'
    scene.cycles.samples = 8
    scene.cycles.use_denoising = False
except TypeError:
    pass
scene.view_settings.view_transform = 'Standard'
scene.view_settings.look = 'None'
w = bpy.data.worlds.new('W')
scene.world = w
w.use_nodes = True
next(n for n in w.node_tree.nodes if n.type == 'BACKGROUND').inputs['Color'].default_value = (1, 1, 1, 1)
scene.render.image_settings.file_format = 'PNG'
scene.render.filepath = str(sk.LIB_DIR / OUT)
bpy.ops.render.render(write_still=True)
print('palette sheet written')
