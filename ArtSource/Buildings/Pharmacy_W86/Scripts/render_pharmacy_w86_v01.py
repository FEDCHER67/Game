"""Preview renders for Pharmacy_W86 (Eevee).  Opens Pharmacy_W86_<rev>.blend, adds a render-only context (pavement, road, the
building above, courtyard, van-size dummy), sun/sky, interior area lights at the lamp anchors, then renders the views.
  blender -b --factory-startup -noaudio --python render_pharmacy_w86_v01.py -- [view ...] [--force] [same footprint args as the build]
Writes Renders/preview_<rev>_<view>.png.  Nothing here is exported.
"""
import math
import os
import sys

import bpy
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ph_layout_v01 as P  # noqa: E402
import build_pharmacy_w86_v01 as B  # noqa: E402
from ph_lib_v01 import MB  # noqa: E402

ARGS = P.ARGS
REV = P.REV
RDIR = os.path.join(B.OUT, 'Renders')
os.makedirs(RDIR, exist_ok=True)
X0, X1, Y0, Y3, PY0, PY1, D, H, HW = P.X0, P.X1, P.Y0, P.Y3, P.PY0, P.PY1, P.D, P.H, P.HW
gx = [P.GC0 + (P.GC1 - P.GC0) * (k + 0.5) / 7 for k in range(7)]
dx = [P.CD0 + 0.32, P.GT0 - 0.62]

VIEWS = {
    # name: (camera, target, lens or None, ortho scale, resolution, rear door open)
    'exterior_street': ((-4.6, -10.5, 1.58), (0.9, 0.0, 1.85), 26, None, (1600, 900), False),
    'exterior_oblique': ((7.4, -3.6, 1.58), (2.9, 0.0, 1.85), 28, None, (1600, 900), False),
    'sales_entrance': ((P.DCX - 0.15, Y0 + 0.55, 1.70), (-0.6, PY0, 1.15), 17, None, (1600, 900), False),
    'counter_a': ((gx[1], P.CY0 - 1.30, 1.50), (gx[1], P.CY0 + 0.30, 1.0), 24, None, (1920, 1080), False),
    'counter_b': ((gx[4], P.CY0 - 1.30, 1.50), (gx[4], P.CY0 + 0.30, 1.0), 24, None, (1920, 1080), False),
    'counter_c': ((0.5 * (gx[6] + dx[1]) + 0.3, P.CY0 - 1.45, 1.52), (0.5 * (gx[6] + dx[1]) + 0.3, P.CY0 + 0.30, 1.0), 24, None, (1920, 1080), False),
    'sales_oblique': ((4.45, 2.9, 1.70), (1.9, 6.9, 0.95), 20, None, (1600, 900), False),
    'shelf_oblique': ((-3.3, 1.7, 1.70), (-5.4, 4.3, 1.05), 22, None, (1600, 900), False),
    'stockroom': ((4.05, PY1 + 0.30, 1.70), (0.7, Y3, 1.05), 16, None, (1600, 900), True),
    'stock_oblique': ((-0.2, PY1 + 0.45, 1.70), (-3.0, Y3 - 0.6, 0.8), 18, None, (1600, 900), True),
    'rear_courtyard': ((-6.2, D + 7.6, 1.70), (1.0, D + 0.6, 1.35), 26, None, (1600, 900), True),
    'top_cutaway': ((0.0, 0.5 * (D + 5.0), 40.0), (0.0, 0.5 * (D + 5.0), 0.0), None, max(P.W + 2.0, D + 8.0), (1400, 1400), True),
}


def look_at(ob, target):
    d = Vector(target) - ob.location
    ob.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()


def mat_tex(name, tex, tile, tint=(1, 1, 1), rough=0.9):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    bsdf = next(n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED')
    bsdf.inputs['Roughness'].default_value = rough
    if tex:
        tc = nt.nodes.new('ShaderNodeTexCoord')
        mp = nt.nodes.new('ShaderNodeMapping')
        mp.inputs['Scale'].default_value = (1 / tile, 1 / tile, 1)
        im = nt.nodes.new('ShaderNodeTexImage')
        im.image = bpy.data.images.load(B.ART + tex, check_existing=True)
        mul = nt.nodes.new('ShaderNodeVectorMath')
        mul.operation = 'MULTIPLY'
        mul.inputs[1].default_value = tint
        nt.links.new(tc.outputs['UV'], mp.inputs['Vector'])
        nt.links.new(mp.outputs['Vector'], im.inputs['Vector'])
        nt.links.new(im.outputs['Color'], mul.inputs[0])
        nt.links.new(mul.outputs['Vector'], bsdf.inputs['Base Color'])
    else:
        bsdf.inputs['Base Color'].default_value = (*tint, 1)
    return m


def emit_mat(name, col, strength=4.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    bsdf = next(n for n in m.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
    bsdf.inputs['Base Color'].default_value = (*col, 1)
    bsdf.inputs['Emission Color'].default_value = (*col, 1)
    bsdf.inputs['Emission Strength'].default_value = strength
    return m


def context_geometry(rc):
    lib = {
        'PAVE': mat_tex('CTX_pavement', 'StyleKit_v3/Textures/2b_sidewalk_tiles/2b_sidewalk_tiles_v07_albedo.png', 1.5),
        'ROAD': mat_tex('CTX_road', 'StyleKit_v3/Textures/2a_asphalt/2a_asphalt_v07_albedo.png', 4.0),
        'WALL': mat_tex('CTX_wall', 'MapTextures_W86/T1/Textures/T1_plaster_grey_albedo.png', 3.0, (1.05, 1.03, 1.0)),
        'YARD': mat_tex('CTX_yard', 'MapTextures_W86/T1/Textures/T1_concrete_slabs_old_albedo.png', 6.0),
        'CONC': mat_tex('CTX_conc', 'MapTextures_W86/T1/Textures/T1_concrete_light_albedo.png', 3.0),
        'WIN': mat_tex('CTX_win', None, 1, (0.08, 0.10, 0.12), 0.2),
        'FRAME': mat_tex('CTX_frame', None, 1, (0.75, 0.75, 0.72), 0.5),
        'TREE': mat_tex('CTX_tree', None, 1, (0.16, 0.30, 0.10), 0.9),
        'BARK': mat_tex('CTX_bark', None, 1, (0.20, 0.14, 0.09), 0.9),
        'VAN': mat_tex('CTX_van', None, 1, (0.55, 0.60, 0.66), 0.5),
        'VANW': mat_tex('CTX_vanw', None, 1, (0.03, 0.03, 0.03), 0.6),
        'VANG': mat_tex('CTX_vang', None, 1, (0.05, 0.07, 0.09), 0.1),
    }
    mb = MB('CTX')
    ext = HW + 14.0
    # street side: pavement (0.12 below the floor), kerb, road
    mb.face([(-ext, -3.6, -0.12), (ext, -3.6, -0.12), (ext, 0.0, -0.12), (-ext, 0.0, -0.12)], 'PAVE', want=(0, 0, 1))
    mb.box((-ext, -3.75, -0.30), (ext, -3.6, -0.12), 'CONC', skip=('z-', 'y+'))
    mb.face([(-ext, -16, -0.30), (ext, -16, -0.30), (ext, -3.75, -0.30), (-ext, -3.75, -0.30)], 'ROAD', want=(0, 0, 1))
    # the existing building: neighbour ground floors left/right + storeys above (facade line y = 0 / rear line y = D)
    top = 15.5
    for sx in (-1, 1):
        xa, xb = sorted((sx * HW, sx * ext))
        mb.face([(xa, 0, -0.12), (xb, 0, -0.12), (xb, 0, P.FH), (xa, 0, P.FH)], 'WALL', want=(0, -1, 0))
        mb.face([(xa, D, -0.08), (xb, D, -0.08), (xb, D, H + P.SLAB), (xa, D, H + P.SLAB)], 'WALL', want=(0, 1, 0))
        for k in range(2):
            wx = sx * (HW + 2.0 + k * 4.0)
            mb.box((wx - 0.65, -0.02, 1.0), (wx + 0.65, 0.0, 2.6), 'WIN', skip=('y+',))
            mb.box((wx - 0.72, -0.08, 0.92), (wx + 0.72, 0.0, 1.0), 'FRAME', skip=('y+',))
    mb.face([(-ext, 0, P.FH), (ext, 0, P.FH), (ext, 0, top), (-ext, 0, top)], 'WALL', want=(0, -1, 0))
    mb.face([(-ext, D, H + P.SLAB), (ext, D, H + P.SLAB), (ext, D, top), (-ext, D, top)], 'WALL', want=(0, 1, 0))
    mb.face([(-ext, 0, top), (ext, 0, top), (ext, D, top), (-ext, D, top)], 'WALL', want=(0, 0, 1))
    for fl in range(4):
        z0 = P.FH + 1.1 + fl * 2.8
        for k in range(-4, 5):
            x = k * 2.9
            for yy, sg in ((0.0, -1), (D, 1)):
                mb.box((x - 0.7, yy + sg * 0.0 - (0.02 if sg < 0 else 0.0), z0), (x + 0.7, yy + (0.02 if sg > 0 else 0.0), z0 + 1.45), 'WIN',
                       skip=('y+',) if sg < 0 else ('y-',))
                mb.box((x - 0.78, yy - (0.07 if sg < 0 else 0.0), z0 - 0.08), (x + 0.78, yy + (0.07 if sg > 0 else 0.0), z0), 'FRAME',
                       skip=('y+',) if sg < 0 else ('y-',))
    # courtyard: flat slabs, far wall, trees
    mb.face([(-ext, D, -0.08), (ext, D, -0.08), (ext, D + 22, -0.08), (-ext, D + 22, -0.08)], 'YARD', want=(0, 0, 1))
    mb.box((-ext, D + 20.0, -0.08), (ext, D + 20.3, 2.2), 'CONC', skip=('z-',))
    for (tx, ty) in ((-7.0, D + 17.5), (-1.5, D + 18.2), (5.5, D + 17.8), (11.0, D + 17.0)):
        mb.cyl((tx, ty, -0.08), (tx, ty, 2.4), 0.15, 'BARK', n=8)
    ob = mb.build(lib, rc, name='CTX_static')
    for (tx, ty) in ((-7.0, D + 17.5), (-1.5, D + 18.2), (5.5, D + 17.8), (11.0, D + 17.0)):
        tb = MB('crown')
        tb.lathe([(0.0, 2.0), (1.6, 2.6), (2.0, 3.8), (1.4, 5.0), (0.0, 5.6)], 10, 'TREE')
        o = tb.build(lib, rc, name='CTX_crown')
        o.location = (tx, ty, 0.0)
    # van-size dummy at the van stop (rear doors toward the pharmacy door)
    vb = MB('van')
    cx, cy = P.RDX, D + 1.40 + 1.0 + 2.6
    vb.box((cx - 1.0, cy - 2.6, 0.36), (cx + 1.0, cy + 2.6, 2.4), 'VAN')
    vb.box((cx - 0.92, cy + 1.6, 1.35), (cx + 0.92, cy + 2.62, 2.15), 'VANG', skip=('z-',))
    for sx in (-1, 1):
        for sy in (-1, 1):
            vb.cyl((cx + sx * 0.78, cy + sy * 1.65, 0.30), (cx + sx * 1.0, cy + sy * 1.65, 0.30), 0.36, 'VANW', n=12)
    vb.build(lib, rc, name='CTX_van')


def setup():
    bpy.ops.wm.open_mainfile(filepath=os.path.join(B.OUT, 'Pharmacy_W86_%s.blend' % REV))
    sc = bpy.context.scene
    try:
        sc.render.engine = 'BLENDER_EEVEE'
    except TypeError as e:
        print('engine', e)
    ee = sc.eevee
    for attr, val in (('shadow_pool_size', '4096'), ('taa_render_samples', 64), ('use_raytracing', True), ('use_shadows', True),
                      ('fast_gi_method', 'GLOBAL_ILLUMINATION'), ('use_fast_gi', True), ('fast_gi_distance', 1.5)):
        try:
            setattr(ee, attr, val)
        except Exception as e:
            print('eevee', attr, e)
    try:
        sc.view_settings.view_transform = 'AgX'
        sc.view_settings.look = 'AgX - Medium High Contrast'
    except Exception:
        pass
    for o in bpy.data.objects:
        if o.name.startswith('UCX_') or o.name.endswith('_LOD1'):
            o.hide_render = True
            o.hide_viewport = True
    w = bpy.data.worlds.new('PH_Sky')
    sc.world = w
    w.use_nodes = True
    bg = next(n for n in w.node_tree.nodes if n.type == 'BACKGROUND')
    bg.inputs['Color'].default_value = (0.55, 0.68, 0.86, 1.0)
    bg.inputs['Strength'].default_value = 0.75
    rc = bpy.data.collections.new('PH_RenderOnly')
    sc.collection.children.link(rc)
    sun = bpy.data.objects.new('Sun', bpy.data.lights.new('Sun', 'SUN'))
    rc.objects.link(sun)
    sun.data.energy = 3.6
    sun.data.angle = math.radians(1.5)
    sun.rotation_euler = Vector((0.45, 0.80, -0.62)).to_track_quat('-Z', 'Y').to_euler()
    context_geometry(rc)
    for i, (x, y, z) in enumerate(B_LAMPS('sales')):
        L = bpy.data.lights.new('LS%02d' % i, 'AREA')
        L.shape = 'RECTANGLE'
        L.size, L.size_y = 1.15, 0.22
        L.energy = 130.0
        L.color = (1.0, 0.80, 0.58)
        o = bpy.data.objects.new('LS%02d' % i, L)
        rc.objects.link(o)
        o.location = (x, y, z - 0.012)
    # preview-only bounce fill: weak warm area lights facing the sales ceiling (stands in for Unity ambient/GI)
    for i, x in enumerate((-3.0, 0.0, 3.0)):
        L = bpy.data.lights.new('BOUNCE%02d' % i, 'AREA')
        L.shape = 'RECTANGLE'
        L.size, L.size_y = 3.0, 4.0
        L.energy = 70.0
        L.color = (1.0, 0.86, 0.68)
        o = bpy.data.objects.new('BOUNCE%02d' % i, L)
        rc.objects.link(o)
        o.location = (x, 0.5 * (Y0 + PY0), 1.2)
        o.rotation_euler = (math.pi, 0.0, 0.0)
        L.use_shadow = False
    for i, (x, y, z) in enumerate(B_LAMPS('stock')):
        L = bpy.data.lights.new('LK%02d' % i, 'AREA')
        L.shape = 'RECTANGLE'
        L.size, L.size_y = 0.12, 1.2
        L.energy = 120.0
        L.color = (0.96, 0.97, 0.95)
        o = bpy.data.objects.new('LK%02d' % i, L)
        rc.objects.link(o)
        o.location = (x, y, z - 0.012)
    for name, p, e, col in (('Bulk', (P.RD1 + 0.45, D + 0.2, 2.2), 30.0, (1.0, 0.86, 0.66)),
                            ('Cross', (HW - P.PIL / 2, -0.66, P.OH + 0.30), 6.0, (0.3, 1.0, 0.45)),
                            ('Fridge', (0.5 * (P.FX0 + P.FX1), P.FY0 + 0.35, 1.75), 12.0, (0.9, 0.95, 1.0))):
        L = bpy.data.lights.new(name, 'POINT')
        L.energy = e
        L.color = col
        L.shadow_soft_size = 0.08
        o = bpy.data.objects.new(name, L)
        rc.objects.link(o)
        o.location = p
    cam = bpy.data.objects.new('Cam', bpy.data.cameras.new('Cam'))
    rc.objects.link(cam)
    sc.camera = cam
    cam.data.clip_start = 0.03
    cam.data.clip_end = 300
    cam.data.sensor_width = 36
    return sc, cam, rc


def B_LAMPS(kind):
    out = []
    for o in bpy.data.objects:
        if o.name.startswith('ANCHOR_Light_Sales_') and kind == 'sales':
            out.append(tuple(o.matrix_world.translation))
        if o.name.startswith('ANCHOR_Light_Stock_') and kind == 'stock':
            out.append(tuple(o.matrix_world.translation))
    return out


def markers(rc):
    """Top-view overlay: routes and key anchors (render only)."""
    em = {'staff': emit_mat('MK_staff', (0.15, 0.45, 1.0)), 'carry': emit_mat('MK_carry', (1.0, 0.2, 0.15)),
          'cust': emit_mat('MK_cust', (1.0, 0.85, 0.1)), 'van': emit_mat('MK_van', (1.0, 0.45, 0.0), 2.0)}
    mb = MB('mk')

    def line(pts, key, z=0.03, w=0.06):
        for a, b in zip(pts, pts[1:]):
            a, b = Vector((a[0], a[1], z)), Vector((b[0], b[1], z))
            d = (b - a)
            n = Vector((-d.y, d.x, 0)).normalized() * w
            mb.face([a - n, b - n, b + n, a + n], key, want=(0, 0, 1))

    def dot(p, key, r=0.18):
        mb.disc((p[0], p[1], 0.035), r, 12, key)
    cy0, cy1 = P.CY0, P.CY1
    staff = [(P.REG_X, cy1 + 0.58), (P.SDX, cy1 + 0.75), (P.SDX, PY0 - 0.60), (P.SDX, PY1 + 0.60),
             (0.5 * (P.RDX + P.SDX), 0.5 * (PY1 + Y3) + 0.3), (P.RDX, Y3 - 0.80), (P.RDX, D + 0.80), (P.RDX, D + 2.60)]
    line(staff, 'staff')
    carry = [(0.5 * (P.RD0 + X1) - 0.3, 0.5 * (PY1 + Y3) + 0.2), (P.RDX + 0.15, Y3 - 0.8), (P.RDX + 0.15, D + 0.8), (P.RDX + 0.15, D + 1.9)]
    line(carry, 'carry')
    cust = [(P.DCX, -0.9), (P.DCX, Y0 + 0.9), (P.REG_X + 0.4, cy0 - 0.9), (P.REG_X, cy0 - 0.56)]
    line(cust, 'cust')
    dot((P.REG_X, cy0 - 0.56), 'cust', 0.25)
    dot((P.RDX, D + 1.9), 'carry', 0.25)
    vx, vy = P.RDX, D + 1.40 + 1.0 + 2.6
    line([(vx - 1.0, vy - 2.6), (vx + 1.0, vy - 2.6), (vx + 1.0, vy + 2.6), (vx - 1.0, vy + 2.6), (vx - 1.0, vy - 2.6)], 'van', z=2.6, w=0.05)
    mb.build(em, rc, name='MK_overlay')


def main():
    views = [a for a in ARGS if a in VIEWS] or list(VIEWS)
    sc, cam, rc = setup()
    rear = bpy.data.objects.get('Door_Rear')
    for name in views:
        loc, tgt, lens, ortho, res, rear_open = VIEWS[name]
        path = os.path.join(RDIR, 'preview_%s_%s.png' % (REV, name))
        if os.path.exists(path) and not P.FORCE:
            print('skip existing', path)
            continue
        if rear is not None:
            rear.rotation_euler = (0, 0, math.radians(-95.0 if rear_open else 0.0))
        sun = bpy.data.objects['Sun']
        exterior = name.startswith(('exterior', 'rear', 'top'))
        next(n for n in sc.world.node_tree.nodes if n.type == 'BACKGROUND').inputs['Strength'].default_value = 0.75 if exterior else 0.35
        back = name in ('rear_courtyard',)
        sun.rotation_euler = Vector((0.45, -0.80 if back else 0.80, -0.62)).to_track_quat('-Z', 'Y').to_euler()
        top = name == 'top_cutaway'
        for o in bpy.data.objects:
            if o.name.startswith('PH_Unit_Ceiling') and not o.name.endswith('_LOD1'):
                o.hide_render = top
            if o.name in ('CTX_static',):
                o.hide_render = False
        if top:
            if not bpy.data.objects.get('MK_overlay'):
                markers(rc)
            ctx = bpy.data.objects.get('CTX_static')
            # cut the storeys above for the top view: hide the context building completely, keep the van/trees
            ctx.hide_render = True
        mk = bpy.data.objects.get('MK_overlay')
        if mk:
            mk.hide_render = not top
        cam.location = loc
        look_at(cam, tgt)
        if ortho:
            cam.data.type = 'ORTHO'
            cam.data.ortho_scale = ortho
            cam.rotation_euler = (0, 0, 0)
        else:
            cam.data.type = 'PERSP'
            cam.data.lens = lens
        sc.render.resolution_x, sc.render.resolution_y = res
        sc.render.filepath = path
        bpy.ops.render.render(write_still=True)
        print('RENDERED', path)


if __name__ == '__main__':
    main()
