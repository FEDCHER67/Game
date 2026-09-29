"""Build the exterior-only KIDNEY-ASTRA-001 pair in Blender 5.2.

The kidneys use newly authored bean contours. The two source models remain
loose references; no donor mesh is exported.
"""

import bpy
import math
import os
import bmesh
from pathlib import Path
from mathutils import Vector


ROOT = Path(os.environ.get('ASTRA_OUTPUT_ROOT',
    r'C:\Dev\Game\_worktrees\fedya-player-v2\research\KIDNEY-ASTRA-001'))
PREVIEWS = ROOT / 'Previews'
PREVIEWS.mkdir(parents=True, exist_ok=True)
DRAFT = os.environ.get('ASTRA_DRAFT') == '1'

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.render.engine = 'CYCLES'
scene.cycles.samples = 32 if DRAFT else 128
scene.cycles.use_denoising = True
scene.render.resolution_x = 700 if DRAFT else 1000
scene.render.resolution_y = 700 if DRAFT else 1000
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = 'PNG'
scene.render.film_transparent = False
scene.world = bpy.data.worlds.new('Studio ambient')
scene.world.color = (0.075, 0.075, 0.075)
scene.view_settings.view_transform = 'AgX'
scene.view_settings.look = 'None'

asset_col = bpy.data.collections.new('KIDNEY-ASTRA-001 | Game Assembly')
scene.collection.children.link(asset_col)
studio_col = bpy.data.collections.new('Preview Studio | Not Exported')
scene.collection.children.link(studio_col)


def material(name, color, roughness):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = (*color, 1.0)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get('Principled BSDF')
    bsdf.inputs['Base Color'].default_value = (*color, 1.0)
    bsdf.inputs['Roughness'].default_value = roughness
    bsdf.inputs['Metallic'].default_value = 0.0
    bsdf.inputs['IOR'].default_value = 1.45
    if 'Specular IOR Level' in bsdf.inputs:
        bsdf.inputs['Specular IOR Level'].default_value = 0.12
    if 'Diffuse Roughness' in bsdf.inputs:
        bsdf.inputs['Diffuse Roughness'].default_value = 0.32
    return mat


kidney_mat = material('01 | Matte warm brown red', (0.106, 0.028, 0.019), 0.95)
tube_mat = material('02 | Muted warm ureter', (0.145, 0.069, 0.050), 0.95)


def add_mesh(name, verts, faces, uv_corners, mat):
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    uv = mesh.uv_layers.new(name='UV0')
    for poly, face_uv in zip(mesh.polygons, uv_corners):
        for loop_index, coord in zip(poly.loop_indices, face_uv):
            uv.data[loop_index].uv = coord
        poly.use_smooth = True
    obj = bpy.data.objects.new(name, mesh)
    asset_col.objects.link(obj)
    obj.data.materials.append(mat)
    return obj


def catmull_point(points, sample):
    segment = int(sample)
    t = sample - segment
    count = len(points)
    p0, p1, p2, p3 = (points[(segment + offset) % count] for offset in (-1, 0, 1, 2))
    return tuple(0.5 * ((2 * p1[k]) + (-p0[k] + p2[k]) * t
                        + (2*p0[k] - 5*p1[k] + 4*p2[k] - p3[k]) * t*t
                        + (-p0[k] + 3*p1[k] - 3*p2[k] + p3[k]) * t*t*t)
                 for k in (0, 1))


def kidney(name, side, cx, cz, width_scale, height_scale, depth, tilt_deg, notch_shift):
    """Closed bean sculpt: explicit 2D outline lofted into a soft 3D mass."""
    # Local +X faces away from the midline. The deep medial notch sits between
    # distinct upper and lower lobes; the pole shapes deliberately differ.
    controls = [
        (-0.014, 0.053), (0.003, 0.056), (0.021, 0.050),
        (0.034, 0.033), (0.039, 0.009), (0.037, -0.017),
        (0.028, -0.039), (0.010, -0.054), (-0.008, -0.054),
        (-0.022, -0.043), (-0.026, -0.030),
        (-0.024, -0.021), (-0.020, -0.014),
        (-0.020 + notch_shift, -0.008), (-0.019 + notch_shift, -0.001),
        (-0.020 + notch_shift, 0.006), (-0.022, 0.013),
        (-0.025, 0.022), (-0.028, 0.034), (-0.026, 0.045),
    ]
    nr, nt = 64, 128
    center_x, center_z = 0.008, 0.0
    tilt = math.radians(tilt_deg)
    outline = [catmull_point(controls, j * len(controls) / nt) for j in range(nt)]
    verts, faces, face_uv = [], [], []
    for i in range(1, nr):
        theta = math.pi * i / nr
        radial, ct = math.sin(theta)**1.15, math.cos(theta)
        for ox, oz in outline:
            # Keep the outer bean contour while easing the notch into the face.
            notch_relief = math.exp(-((ox + 0.018) / 0.016)**2 - (oz / 0.026)**2)
            lx = center_x + radial * (ox * width_scale - center_x) - 0.008 * radial * (1.0-radial) * notch_relief
            lz = center_z + radial * (oz * height_scale - center_z)
            fullness = 1.0 + 0.12 * lz / 0.056 - 0.045 * lx / 0.040
            hilum = math.exp(-((lx + 0.008) / 0.016)**2 - ((lz + 0.002) / 0.023)**2)
            ly = -depth * ct * fullness + 0.0005 * ct * hilum
            rx = lx * math.cos(tilt) + lz * math.sin(tilt)
            rz = -lx * math.sin(tilt) + lz * math.cos(tilt)
            verts.append((side * (cx + rx), ly, cz + rz))
    front = len(verts)
    verts.append((side * (cx + center_x*math.cos(tilt)), -depth, cz - center_x*math.sin(tilt)))
    rear = len(verts)
    verts.append((side * (cx + center_x*math.cos(tilt)), depth, cz - center_x*math.sin(tilt)))
    for i in range(nr - 2):
        for j in range(nt):
            jn = (j + 1) % nt
            faces.append((i*nt+j, (i+1)*nt+j, (i+1)*nt+jn, i*nt+jn))
            face_uv.append(((j/nt, (i+1)/nr), (j/nt, (i+2)/nr),
                            ((j+1)/nt, (i+2)/nr), ((j+1)/nt, (i+1)/nr)))
    for j in range(nt):
        jn = (j + 1) % nt
        faces.append((front, j, jn))
        face_uv.append((((j+0.5)/nt, 0), (j/nt, 1/nr), ((j+1)/nt, 1/nr)))
        faces.append((rear, (nr-2)*nt+jn, (nr-2)*nt+j))
        face_uv.append((((j+0.5)/nt, 1), ((j+1)/nt, (nr-1)/nr), (j/nt, (nr-1)/nr)))
    obj = add_mesh(name, verts, faces, face_uv, kidney_mat)
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    if bm.calc_volume(signed=True) < 0:
        bmesh.ops.reverse_faces(bm, faces=bm.faces)
        bm.to_mesh(obj.data)
    bm.free()
    obj.data.update()
    # A light surface relaxation rounds the hand-authored loft before the
    # tube union, so the material seam is cut into the finished soft form.
    bpy.context.view_layer.objects.active = obj
    soften = obj.modifiers.new('Broad-form sculpt relaxation', 'SMOOTH')
    soften.factor = 0.7
    soften.iterations = 12
    bpy.ops.object.modifier_apply(modifier=soften.name)
    preserve = obj.modifiers.new('Organic volume preservation', 'LAPLACIANSMOOTH')
    preserve.lambda_factor = 0.2
    preserve.iterations = 3
    preserve.use_volume_preserve = True
    bpy.ops.object.modifier_apply(modifier=preserve.name)
    return obj


def bezier(p0, p1, p2, p3, t):
    u = 1.0 - t
    return (u ** 3) * p0 + 3 * (u ** 2) * t * p1 + 3 * u * (t ** 2) * p2 + (t ** 3) * p3


def tube(name, control, radii, mat, rings=44, sides=18, round_start=False, round_end=False):
    """Smooth variable-radius sweep with capped ends and tube UVs."""
    p = [Vector(x) for x in control]
    verts, faces, face_uv = [], [], []
    points = [bezier(*p, i / (rings - 1)) for i in range(rings)]
    n_prev = None
    for i, point in enumerate(points):
        tangent = (points[min(i + 1, rings - 1)] - points[max(i - 1, 0)]).normalized()
        if n_prev is None:
            ref = Vector((0, 1, 0)) if abs(tangent.y) < 0.9 else Vector((1, 0, 0))
            normal = tangent.cross(ref).normalized()
        else:
            normal = (n_prev - tangent * n_prev.dot(tangent)).normalized()
        binormal = tangent.cross(normal).normalized()
        n_prev = normal
        t = i / (rings - 1)
        r = (1-t)**3 * radii[0] + 3*(1-t)**2*t*radii[1] + 3*(1-t)*t*t*radii[2] + t**3*radii[3]
        r *= 1 + 0.025 * math.sin(math.pi * t)
        if round_start:
            r *= max(0.025, math.sin(0.5 * math.pi * min(1.0, t / 0.033)))
        if round_end:
            r *= max(0.025, math.sin(0.5 * math.pi * min(1.0, (1.0 - t) / 0.033)))
        for j in range(sides):
            a = 2 * math.pi * j / sides
            v = point + r * (math.cos(a) * normal + math.sin(a) * binormal)
            verts.append(tuple(v))
    c0 = len(verts)
    verts.append(tuple(points[0]))
    c1 = len(verts)
    verts.append(tuple(points[-1]))
    for i in range(rings - 1):
        for j in range(sides):
            jn = (j + 1) % sides
            faces.append((i*sides+j, i*sides+jn, (i+1)*sides+jn, (i+1)*sides+j))
            face_uv.append(((j/sides, i/(rings-1)), ((j+1)/sides, i/(rings-1)), ((j+1)/sides, (i+1)/(rings-1)), (j/sides, (i+1)/(rings-1))))
    for j in range(sides):
        jn = (j + 1) % sides
        faces.extend(((c0, jn, j), (c1, (rings-1)*sides+j, (rings-1)*sides+jn)))
        face_uv.extend(((((j+0.5)/sides, 0.5), (jn/sides, 0), (j/sides, 0)), (((j+0.5)/sides, 0.5), (j/sides, 1), (jn/sides, 1))))
    return add_mesh(name, verts, faces, face_uv, mat)


# The two closed kidney bodies remain the hero. Only one descending tube per side.
kidney('L_Kidney | closed bean sculpt', -1, 0.065, 0.001, 1.015, 1.00, 0.0225, 3.0, 0.0)
kidney('R_Kidney | closed bean sculpt', 1, 0.064, -0.001, 0.985, 0.99, 0.0215, 2.0, 0.0010)

tube('L_Ureter | descending tube',
     [(-0.052, 0.001, -0.010), (-0.027, -0.005, -0.019),
      (-0.026, -0.004, -0.063), (-0.028, 0.002, -0.105)],
     [0.0042, 0.0036, 0.0030, 0.0026], tube_mat, 64, 22, round_end=True)
tube('R_Ureter | descending tube',
     [(0.081, 0.004, -0.010), (0.023, -0.012, -0.019),
      (0.023, -0.008, -0.067), (0.026, 0.002, -0.108)],
     [0.0045, 0.0039, 0.0031, 0.0026], tube_mat, 64, 22, round_end=True)


# Sculpt each tube into its kidney so the connection is one continuous closed
# surface rather than two exported meshes overlapping at the hilum.
for tag in ('L', 'R'):
    body = next(o for o in asset_col.objects if o.name.startswith(tag + '_Kidney'))
    stem = next(o for o in asset_col.objects if o.name.startswith(tag + '_Ureter'))
    body.data.materials.append(tube_mat)
    bpy.ops.object.select_all(action='DESELECT')
    body.select_set(True)
    bpy.context.view_layer.objects.active = body
    join = body.modifiers.new('Sculpted hilum-tube union', 'BOOLEAN')
    join.operation = 'UNION'
    join.solver = 'EXACT'
    join.material_mode = 'TRANSFER'
    join.object = stem
    bpy.ops.object.modifier_apply(modifier=join.name)
    bpy.data.objects.remove(stem, do_unlink=True)
    body.name = f'{tag}_Kidney and descending tube | integrated sculpt'
    body.data.name = body.name

    # The exact Boolean can leave a microscopic sliver at a tube root.
    # Dissolve only sub-millimetre degenerate edges before the final UV pass.
    bm = bmesh.new()
    bm.from_mesh(body.data)
    bmesh.ops.dissolve_degenerate(bm, edges=list(bm.edges), dist=1e-6)
    bm.to_mesh(body.data)
    bm.free()
    body.data.update()

    for poly in body.data.polygons:
        poly.use_smooth = True
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(island_margin=0.02)
    bpy.ops.object.mode_set(mode='OBJECT')


def area_light(name, location, energy, color, size):
    data = bpy.data.lights.new(name, 'AREA')
    data.energy = energy
    data.color = color
    data.shape = 'DISK'
    data.size = size
    obj = bpy.data.objects.new(name, data)
    studio_col.objects.link(obj)
    obj.location = location
    obj.rotation_euler = (Vector((0, 0, -0.004)) - obj.location).to_track_quat('-Z', 'Y').to_euler()


area_light('Large softbox left', (-0.18, -0.18, 0.19), 2.7, (1.0, 0.94, 0.89), 0.22)
area_light('Broad fill right', (0.18, -0.11, 0.09), 1.6, (0.93, 0.95, 1.0), 0.26)
area_light('Back edge softbox', (0.01, 0.17, 0.14), 2.25, (1.0, 0.95, 0.92), 0.24)

camera_data = bpy.data.cameras.new('Review Camera')
camera = bpy.data.objects.new('Review Camera', camera_data)
studio_col.objects.link(camera)
scene.camera = camera
camera_data.type = 'ORTHO'
camera_data.lens = 50
camera.location = (0.025, -0.32, 0.028)
camera.rotation_euler = (Vector((0.0, 0.0, -0.025)) - camera.location).to_track_quat('-Z', 'Y').to_euler()
camera_data.ortho_scale = 0.245


def render(name, loc, target, scale, samples=None):
    if DRAFT and name not in {'01_front_hero.png', '03_left_three_quarter.png',
                               '04_right_three_quarter.png', '05_side.png',
                               '06_kidney_surface_closeup.png',
                               '07_hilum_connection_closeup.png', '08_full_pair_tubes.png'}:
        return
    camera.location = loc
    camera.rotation_euler = (Vector(target) - camera.location).to_track_quat('-Z', 'Y').to_euler()
    camera_data.ortho_scale = scale
    scene.cycles.samples = 32 if DRAFT else (samples or 128)
    scene.render.filepath = str(PREVIEWS / name)
    bpy.ops.render.render(write_still=True)


blend_path = ROOT / 'KIDNEY-ASTRA-001.blend'
bpy.context.preferences.filepaths.save_version = 0
bpy.ops.wm.save_as_mainfile(filepath=str(blend_path))

# Export only finished game meshes. Unity interprets Blender Z-up through FBX axis conversion.
bpy.ops.object.select_all(action='DESELECT')
for obj in asset_col.objects:
    obj.select_set(True)
bpy.context.view_layer.objects.active = next(iter(asset_col.objects))
bpy.ops.export_scene.fbx(
    filepath=str(ROOT / 'KIDNEY-ASTRA-001.fbx'),
    use_selection=True,
    object_types={'MESH'},
    apply_unit_scale=True,
    apply_scale_options='FBX_SCALE_ALL',
    axis_forward='-Z',
    axis_up='Y',
    mesh_smooth_type='FACE',
    use_mesh_modifiers=True,
    add_leaf_bones=False,
    bake_anim=False,
    path_mode='AUTO',
)

render('01_front_hero.png', (0.025, -0.32, 0.028), (0.0, 0.0, -0.025), 0.245)
render('02_rear.png', (0.0, 0.32, 0.025), (0.0, 0.0, -0.025), 0.245)
render('03_left_three_quarter.png', (-0.20, -0.29, 0.042), (0.0, 0.0, -0.025), 0.245)
render('04_right_three_quarter.png', (0.20, -0.29, 0.042), (0.0, 0.0, -0.025), 0.245)
render('05_side.png', (0.32, -0.025, 0.02), (0.0, 0.0, -0.025), 0.22)
render('06_kidney_surface_closeup.png', (-0.11, -0.23, 0.030), (-0.066, 0.0, 0.005), 0.135, 192)
render('07_hilum_connection_closeup.png', (0.02, -0.19, 0.020), (0.053, 0.0, -0.022), 0.115, 192)
render('08_full_pair_tubes.png', (0.0, -0.32, -0.025), (0.0, 0.0, -0.025), 0.245)

# Neutral surface evaluation: diffuse-only material override, broad even lighting.
neutral = material('Preview only | neutral clay', (0.42, 0.42, 0.42), 0.87)
scene.view_layers[0].material_override = neutral
render('09_neutral_sculpt.png', (0.0, -0.32, 0.025), (0.0, 0.0, -0.025), 0.245, 128)
scene.view_layers[0].material_override = None

verts = sum(len(o.data.vertices) for o in asset_col.objects)
tris = sum(sum(len(p.vertices) - 2 for p in o.data.polygons) for o in asset_col.objects)
print(f'ASTRA_BUILD_SUMMARY objects={len(asset_col.objects)} vertices={verts} triangles={tris} materials=2')
