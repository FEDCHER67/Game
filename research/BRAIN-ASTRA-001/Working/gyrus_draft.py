"""Original, hand-authored gyrus-core draft. Renders only six draft previews."""

import math
from pathlib import Path

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1]
PREVIEWS = ROOT / "Previews"
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.render.engine = "CYCLES"
scene.cycles.samples = 24
scene.render.resolution_x = scene.render.resolution_y = 680
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = "PNG"
scene.view_settings.view_transform = "AgX"
scene.view_settings.look = "None"
scene.unit_settings.system = "METRIC"

asset_col = bpy.data.collections.new("BRAIN-ASTRA-001 | Draft Game Mesh")
scene.collection.children.link(asset_col)
studio_col = bpy.data.collections.new("Preview Studio")
scene.collection.children.link(studio_col)

mat = bpy.data.materials.new("01 | Warm dusty rose soft matte")
mat.use_nodes = True
mat.diffuse_color = (0.39, 0.155, 0.16, 1)
mat.roughness = 0.79
bsdf = mat.node_tree.nodes.get("Principled BSDF")
bsdf.inputs["Base Color"].default_value = mat.diffuse_color
bsdf.inputs["Roughness"].default_value = 0.79
bsdf.inputs["Metallic"].default_value = 0
bsdf.inputs["Specular IOR Level"].default_value = 0.035
bsdf.inputs["Coat Weight"].default_value = 0
bsdf.inputs["Sheen Weight"].default_value = 0
bsdf.inputs["Subsurface Weight"].default_value = 0.015
bsdf.inputs["Diffuse Roughness"].default_value = 0.65

# Each pair is (circumferential angle from the crown, longitudinal angle).
# Curves break, bend and double back at staggered positions. They are authored
# for this asset, not traced or extracted from reference geometry.
STROKES = [
    [(0.10,-1.07),(0.24,-.79),(.10,-.48),(.31,-.21),(.18,.10),(.34,.38),(.16,.76),(.32,1.04)],
    [(.46,-1.16),(.63,-.91),(.43,-.65),(.65,-.37),(.49,-.10),(.72,.18),(.48,.48),(.64,.79),(.45,1.08)],
    [(.86,-1.07),(1.02,-.81),(.84,-.56),(1.07,-.28),(.87,.03),(1.08,.31),(.90,.59),(1.04,.90)],
    [(1.24,-1.14),(1.41,-.89),(1.19,-.61),(1.38,-.30),(1.18,-.02),(1.42,.26),(1.22,.54),(1.37,.84),(1.20,1.10)],
    [(1.63,-1.02),(1.78,-.76),(1.58,-.46),(1.82,-.17),(1.60,.12),(1.79,.40),(1.58,.70),(1.78,.98)],
    [(2.02,-.94),(2.16,-.65),(1.99,-.38),(2.19,-.08),(1.97,.21),(2.16,.52),(1.98,.82)],
    # Offset U and S arcs interrupt the long lanes and give the ends mass.
    [(.24,-1.16),(.47,-1.25),(.75,-1.21),(.91,-1.04)],
    [(.23,1.12),(.45,1.25),(.72,1.20),(.88,1.03)],
    [(.66,-.03),(.54,.11),(.62,.29),(.78,.33)],
    [(.31,-.48),(.25,-.67),(.42,-.82),(.57,-.73)],
    [(.90,-.59),(.76,-.47),(.74,-.28),(.88,-.15)],
    [(1.03,.65),(.92,.82),(1.03,1.02),(1.22,1.10)],
    [(1.42,-.77),(1.51,-.95),(1.75,-1.02),(1.92,-.88)],
    [(1.43,.81),(1.59,1.03),(1.88,1.04),(2.04,.86)],
    [(1.80,-.50),(1.68,-.63),(1.65,-.79)],
    [(1.81,.36),(1.90,.51),(1.81,.70)],
    # Flank and end strokes leave a broad unornamented ventral closure.
    [(2.24,-1.04),(2.47,-.84),(2.27,-.54),(2.52,-.28),(2.25,-.02),(2.45,.19)],
    [(2.31,.26),(2.50,.48),(2.29,.72),(2.47,.96),(2.27,1.10)],
    [(.22,-1.24),(.52,-1.37),(.84,-1.43),(1.18,-1.34),(1.49,-1.42),(1.83,-1.30)],
    [(.31,1.26),(.65,1.39),(.93,1.34),(1.26,1.45),(1.59,1.34),(1.92,1.26)],
]


def catmull(points, subdiv=12):
    result = []
    for j in range(len(points)-1):
        a, b, c, d = points[max(0,j-1)], points[j], points[j+1], points[min(len(points)-1,j+2)]
        for k in range(subdiv):
            t = k / subdiv
            result.append(tuple(.5*(2*b[i]+(-a[i]+c[i])*t+(2*a[i]-5*b[i]+4*c[i]-d[i])*t*t+(-a[i]+3*b[i]-3*c[i]+d[i])*t*t*t) for i in range(2)))
    result.append(points[-1])
    return result


def surface(side, beta, v):
    # A direct ellipsoid parameterization; no clamped square root or invalid
    # projection at the front/back ends. Top has beta=0, flank beta=pi/2.
    cx, rx, ry, rz, cz = .037, .043, .077, .039, .003
    cv = math.cos(v)
    local_x = rx*cv*math.sin(beta)
    y = ry*math.sin(v)
    z = cz + rz*cv*math.cos(beta)
    normal = Vector((side*local_x/(rx*rx), y/(ry*ry), (z-cz)/(rz*rz))).normalized()
    # Embed each round stroke into the recessed core. Exposed height is
    # about 5.5 mm; the lower tube half merges instead of sitting on top.
    return Vector((side*(cx+local_x), y, z)) - normal*.0025


def hemisphere(side):
    cx, rx, ry, rz, cz = .037, .043, .077, .039, .003
    bpy.ops.mesh.primitive_uv_sphere_add(segments=96, ring_count=64, location=(side*cx,0,cz))
    core = bpy.context.object
    core.name = "Closed recessed cerebral core"
    core.scale = (rx,ry,rz)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    parts = [core]
    for j, guide in enumerate(STROKES):
        # Spread authored lanes over the medial crown and outer flank. The
        # crown lies at beta=0; negative beta covers its inner half.
        pts = catmull([(1.45*b-1.0,v) for b,v in guide])
        if j in (3,4,5):
            amp = (.20,.29,.25)[j-3]
            pts = [(b+amp*math.sin(2.8*v + .9*j),v) for b,v in pts]
        if side < 0:
            pts = [(b+.030*math.sin(j*1.7 + v*2.2), v+.018*math.cos(j*1.2)) for b,v in pts]
        curve = bpy.data.curves.new("Rounded authored gyrus %02d" % j, "CURVE")
        curve.dimensions = "3D"
        curve.bevel_depth = .0081 if j < 6 else .0074
        curve.bevel_resolution = 4
        curve.use_fill_caps = True
        spline = curve.splines.new("POLY")
        spline.points.add(len(pts)-1)
        for p, (beta,v) in zip(spline.points, pts):
            p.co = (*surface(side,beta,v),1)
        obj = bpy.data.objects.new("Gyrus %02d" % (j+1), curve)
        scene.collection.objects.link(obj)
        bpy.ops.object.select_all(action="DESELECT")
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.convert(target="MESH")
        parts.append(bpy.context.object)
        # Round the cut end of each stroke before voxel union.
        for beta,v in (pts[0],pts[-1]):
            bpy.ops.mesh.primitive_uv_sphere_add(segments=12, ring_count=8, radius=curve.bevel_depth,
                                                  location=surface(side,beta,v))
            parts.append(bpy.context.object)
    bpy.ops.object.select_all(action="DESELECT")
    for obj in parts:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = core
    bpy.ops.object.join()
    core.data.remesh_voxel_size = .00075
    bpy.ops.object.voxel_remesh()
    smooth = core.modifiers.new("Gentle voxel blend", "SMOOTH")
    smooth.factor = .35
    smooth.iterations = 2
    bpy.ops.object.modifier_apply(modifier=smooth.name)
    core.name = "Left hemisphere" if side < 0 else "Right hemisphere"
    for col in tuple(core.users_collection):
        col.objects.unlink(core)
    asset_col.objects.link(core)
    core.data.materials.append(mat)
    for poly in core.data.polygons:
        poly.use_smooth = True
    print("DRAFT_MESH", core.name, len(core.data.vertices), len(core.data.polygons))
    return core


left, right = hemisphere(-1), hemisphere(1)
world = bpy.data.worlds.new("Organ family blue gray studio")
world.use_nodes = True
world.node_tree.nodes["Background"].inputs["Color"].default_value = (.0165,.0235,.0365,1)
world.node_tree.nodes["Background"].inputs["Strength"].default_value = .48
scene.world = world


def light(name, loc, energy, size, color, hidden=False):
    data = bpy.data.lights.new(name, "AREA")
    data.shape = "DISK"
    data.energy, data.size, data.color, data.specular_factor = energy,size,color,0
    obj = bpy.data.objects.new(name,data)
    studio_col.objects.link(obj)
    obj.location = loc
    obj.rotation_euler = (-obj.location).to_track_quat("-Z","Y").to_euler()
    obj.hide_render = hidden
    return obj


light("Large softbox left",(-.15,-.13,.20),1.86,.201,(1,.987,.977))
light("Back edge softbox",(.08,.16,.16),1.31,.146,(.735,.823,1))
light("Broad fill right",(.18,-.07,.055),.775,.147,(1,.817,.703))
under_fill = light("Underside review fill",(0,-.12,-.18),1.5,.2,(1,.91,.85),True)
rear_fill = light("Rear review fill",(.02,.22,.08),.9,.18,(1,.91,.86),True)
camera_data = bpy.data.cameras.new("Review orthographic")
camera_data.type = "ORTHO"
camera = bpy.data.objects.new("Review orthographic",camera_data)
studio_col.objects.link(camera)
scene.camera = camera


def render(name, loc, target=(0,0,0), scale=.215):
    camera.location = loc
    camera.rotation_euler = (Vector(target)-camera.location).to_track_quat("-Z","Y").to_euler()
    camera_data.ortho_scale = scale
    scene.render.filepath = str(PREVIEWS/name)
    bpy.ops.render.render(write_still=True)


render("draft_front.png",(.067,-.3,.105))
rear_fill.hide_render = False
render("draft_rear.png",(-.02,.3,.055))
rear_fill.hide_render = True
render("draft_side.png",(.29,-.01,.018))
render("draft_top.png",(.01,-.03,.31))
under_fill.hide_render = False
render("draft_underside.png",(.022,-.10,-.3))
under_fill.hide_render = True
neutral = bpy.data.materials.new("Preview only | neutral clay")
neutral.use_nodes = True
shader = neutral.node_tree.nodes.get("Principled BSDF")
shader.inputs["Base Color"].default_value = (.39,.39,.39,1)
shader.inputs["Roughness"].default_value = .9
shader.inputs["Specular IOR Level"].default_value = 0
scene.view_layers[0].material_override = neutral
render("draft_closeup.png",(.025,-.3,.065))
