"""Review renders for GRANDPA_YARD_v01 (called by build_grandpa_yard_v01.py -- --render DIR, after the .blend is saved).
Renders overview / paint close-up / UCX view on a 1 m grid (0.1 m fine grid) with EEVEE and writes labels.json.
compose_contact_sheet_v01.py (system Python + Pillow) turns them into the contact sheet."""
import json, math
from pathlib import Path

import bpy
from mathutils import Vector
from bpy_extras.object_utils import world_to_camera_view

HERE = Path(__file__).resolve().parent
GRANDPA = HERE.parents[1] / 'Characters/SAUSAGE_BUDDY_01/Types/HAMLET_BOXERS_GRANDPA/SAUSAGE_BUDDY_HAMLET_BOXERS_GRANDPA_v05.blend'
VIEW_DIR = Vector((0.95, -1.6, 1.05)).normalized()
SHORT = {'GY_RockingChair_Red': 'Rocking chair', 'GY_Barrel_Wood': 'Wooden barrel', 'GY_Drum_Rain': 'Rain drum 200 L',
         'GY_PaintCan_Open_Green': 'Open can 2.7 L', 'GY_PaintCan_Ochre': 'Can 2.7 L', 'GY_PaintCan_Small_Blue': 'Can 0.9 L',
         'GY_PaintCan_Lid_Green': 'Lid', 'GY_PaintBrush_Green': 'Brush 70 mm'}


def _math(nodes, links, op, a, b=None):
    n = nodes.new('ShaderNodeMath')
    n.operation = op
    for i, v in enumerate((a, b)):
        if v is None:
            continue
        if isinstance(v, (int, float)):
            n.inputs[i].default_value = v
        else:
            links.new(v, n.inputs[i])
    return n.outputs[0]


def grid_material():
    m = bpy.data.materials.new('REVIEW_Grid')
    nt = m.node_tree
    nodes, links = nt.nodes, nt.links
    bsdf = next(n for n in nodes if n.type == 'BSDF_PRINCIPLED')
    bsdf.inputs['Roughness'].default_value = .95
    geo = nodes.new('ShaderNodeNewGeometry')
    sep = nodes.new('ShaderNodeSeparateXYZ')
    links.new(geo.outputs['Position'], sep.inputs[0])

    def line(sock, scale, width):  # width as a fraction of the cell
        s = _math(nodes, links, 'MULTIPLY', sock, scale)
        s = _math(nodes, links, 'ADD', s, width / 2)
        s = _math(nodes, links, 'FRACT', s)
        return _math(nodes, links, 'LESS_THAN', s, width)

    major = _math(nodes, links, 'MAXIMUM', line(sep.outputs['X'], 1, .014), line(sep.outputs['Y'], 1, .014))
    minor = _math(nodes, links, 'MAXIMUM', line(sep.outputs['X'], 10, .05), line(sep.outputs['Y'], 10, .05))
    v = _math(nodes, links, 'SUBTRACT', .40, _math(nodes, links, 'MULTIPLY', minor, .07))
    v = _math(nodes, links, 'SUBTRACT', v, _math(nodes, links, 'MULTIPLY', major, .30))
    comb = nodes.new('ShaderNodeCombineXYZ')
    links.new(v, comb.inputs[0])
    links.new(v, comb.inputs[1])
    links.new(_math(nodes, links, 'MULTIPLY', v, 1.04), comb.inputs[2])
    links.new(comb.outputs[0], bsdf.inputs['Base Color'])
    return m


def flat_material(name, rgba, alpha=1.0, emit=0.0):
    m = bpy.data.materials.new(name)
    nt = m.node_tree
    nodes, links = nt.nodes, nt.links
    nodes.clear()
    out = nodes.new('ShaderNodeOutputMaterial')
    em = nodes.new('ShaderNodeEmission')
    em.inputs['Color'].default_value = rgba
    em.inputs['Strength'].default_value = emit
    if alpha < 1:
        tr = nodes.new('ShaderNodeBsdfTransparent')
        mix = nodes.new('ShaderNodeMixShader')
        mix.inputs[0].default_value = alpha
        links.new(tr.outputs[0], mix.inputs[1])
        links.new(em.outputs[0], mix.inputs[2])
        links.new(mix.outputs[0], out.inputs['Surface'])
        m.surface_render_method = 'BLENDED'
    else:
        links.new(em.outputs[0], out.inputs['Surface'])
    return m


def append_grandpa(loc):
    try:
        with bpy.data.libraries.load(str(GRANDPA), link=False) as (src, dst):
            dst.objects = [n for n in src.objects if n in ('Body', 'Face', 'Outfit', 'Buddy_Rig_Mixamo65', 'Props_Spine2')]
        for o in dst.objects:
            bpy.context.scene.collection.objects.link(o)
        rig = next(o for o in dst.objects if o.type == 'ARMATURE')
        rig.location = loc
        return [o for o in dst.objects if o.type == 'MESH']
    except Exception as e:  # scale reference only
        print('GRANDPA append skipped:', e)
        return []


def world_bounds(objs):
    bpy.context.view_layer.update()
    pts = []
    for o in objs:
        if o.type == 'MESH':
            pts += [o.matrix_world @ Vector(c) for c in o.bound_box]
    return Vector([min(p[i] for p in pts) for i in range(3)]), Vector([max(p[i] for p in pts) for i in range(3)])


def frame(cam, objs, aspect, margin=1.12):
    mn, mx = world_bounds(objs)
    target = (mn + mx) / 2
    cam.location = target + VIEW_DIR * 30
    cam.rotation_euler = (-VIEW_DIR).to_track_quat('-Z', 'Y').to_euler()
    bpy.context.view_layer.update()
    inv = cam.matrix_world.inverted()
    pts = [inv @ (o.matrix_world @ Vector(c)) for o in objs if o.type == 'MESH' for c in o.bound_box]
    w = max(p.x for p in pts) - min(p.x for p in pts)
    h = max(p.y for p in pts) - min(p.y for p in pts)
    cx = (max(p.x for p in pts) + min(p.x for p in pts)) / 2
    cy = (max(p.y for p in pts) + min(p.y for p in pts)) / 2
    cam.location = cam.matrix_world @ Vector((cx, cy, 0))
    cam.data.ortho_scale = max(w, h * aspect) * margin


def labels(scene, cam, roots, manifest):
    info = {m['name']: m for m in manifest}
    out = []
    for r in roots:
        vis = [c for c in r.children if c.name.endswith('_Mesh')]
        mn, mx = world_bounds(vis)
        anchor = Vector(((mn.x + mx.x) / 2, mn.y, 0))
        co = world_to_camera_view(scene, cam, anchor)
        m = info[r.name]
        sx, sy, sz = (round(v * 100) for v in m['size_m'])
        out.append(dict(name=r.name, title=SHORT[r.name], line2=f'{sx}x{sy}x{sz} cm  {m["tris"]} tris',
                        x=co.x, y=1 - co.y))
    return out


def render(roots, manifest, out_dir):
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    scene = bpy.context.scene
    try:
        scene.render.engine = 'BLENDER_EEVEE'
    except TypeError as e:
        print('engine fallback', e)
        scene.render.engine = 'CYCLES'
    try:
        scene.eevee.taa_render_samples = 64
        scene.eevee.use_raytracing = True
    except AttributeError:
        pass
    scene.view_settings.view_transform = 'AgX'
    scene.view_settings.exposure = 0.25
    scene.render.film_transparent = False
    scene.render.image_settings.file_format = 'PNG'
    world = bpy.data.worlds.new('REVIEW_World')
    scene.world = world
    bg = next(n for n in world.node_tree.nodes if n.type == 'BACKGROUND')
    bg.inputs['Color'].default_value = (.42, .46, .52, 1)
    bg.inputs['Strength'].default_value = .9
    sun = bpy.data.objects.new('REVIEW_Sun', bpy.data.lights.new('REVIEW_Sun', 'SUN'))
    sun.data.energy = 3.2
    sun.data.angle = math.radians(6)
    sun.rotation_euler = (math.radians(48), 0, math.radians(-38))
    scene.collection.objects.link(sun)
    plane_me = bpy.data.meshes.new('REVIEW_Ground')
    plane_me.from_pydata([(-12, -10, 0), (14, -10, 0), (14, 12, 0), (-12, 12, 0)], [], [(0, 1, 2, 3)])
    plane_me.materials.append(grid_material())
    ground = bpy.data.objects.new('REVIEW_Ground', plane_me)
    scene.collection.objects.link(ground)
    cam = bpy.data.objects.new('REVIEW_Cam', bpy.data.cameras.new('REVIEW_Cam'))
    cam.data.type = 'ORTHO'
    cam.data.clip_end = 100
    scene.collection.objects.link(cam)
    scene.camera = cam

    ucx = [c for r in roots for c in r.children if c.name.startswith('UCX_')]
    vis = [c for r in roots for c in r.children if c.name.endswith('_Mesh')]
    for o in ucx:
        o.hide_render = True
    grandpa = append_grandpa((-1.55, .3, 0))
    meta = {}

    def shot(name, objs, res, lab_roots, margin=1.12):
        scene.render.resolution_x, scene.render.resolution_y = res
        frame(cam, objs, res[0] / res[1], margin)
        scene.render.filepath = str(out_dir / f'{name}.png')
        bpy.ops.render.render(write_still=True)
        meta[name] = dict(size=list(res), ortho_scale=cam.data.ortho_scale,
                          px_per_m=res[0] / cam.data.ortho_scale, labels=labels(scene, cam, lab_roots, manifest))

    shot('overview', vis + grandpa, (1500, 760), roots, 1.08)
    paint = [r for r in roots if r.name.startswith(('GY_Paint',))]
    for o in grandpa:
        o.hide_render = True
    shot('closeup_paint', [c for r in paint for c in r.children if c.name.endswith('_Mesh')], (740, 440), paint, 1.06)
    # collider view: translucent cyan hulls + bright edges over the props
    hull_mat = flat_material('REVIEW_UCX', (0.1, 0.85, 0.95, 1), alpha=.35, emit=.9)
    wire_mat = flat_material('REVIEW_UCX_Wire', (0.2, 1.0, 1.0, 1), emit=2.0)
    for o in ucx:
        o.hide_render = False
        o.display_type = 'TEXTURED'
        o.data.materials.append(hull_mat)
        w = o.copy()
        w.data = o.data.copy()
        w.data.materials.clear()
        w.data.materials.append(wire_mat)
        md = w.modifiers.new('wire', 'WIREFRAME')
        md.thickness = .006
        md.use_replace = True
        scene.collection.objects.link(w)
    shot('ucx', vis, (740, 440), [], 1.06)
    (out_dir / 'labels.json').write_text(json.dumps(meta, indent=1), encoding='utf-8')
    print('REVIEW renders ->', out_dir)
