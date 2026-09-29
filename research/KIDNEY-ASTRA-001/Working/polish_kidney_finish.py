"""Material-only finish pass on the existing KIDNEY-ASTRA-001 assembly."""

import os
from pathlib import Path

import bpy
from mathutils import Vector


ROOT = Path(__file__).resolve().parents[1]
PREVIEWS = ROOT / 'Previews'
DRAFT = os.environ.get('ASTRA_DRAFT') == '1'
NEUTRAL_ONLY = os.environ.get('ASTRA_NEUTRAL_ONLY') == '1'

bpy.ops.wm.open_mainfile(filepath=str(ROOT / 'KIDNEY-ASTRA-001.blend'))
scene = bpy.context.scene
asset_col = bpy.data.collections['KIDNEY-ASTRA-001 | Game Assembly']
studio_col = bpy.data.collections['Preview Studio | Not Exported']


def soften_material(name, base_color, roughness, specular_level):
    mat = bpy.data.materials[name]
    bsdf = mat.node_tree.nodes.get('Principled BSDF')
    # Keep the datablock's export-facing properties aligned with the shader.
    # FBX reads these properties even though it cannot retain every Principled
    # control, so do not leave its legacy roughness at the former 0.40 value.
    mat.metallic = 0.0
    mat.diffuse_color = (*base_color, 1.0)
    bsdf.inputs['Base Color'].default_value = (*base_color, 1.0)
    mat.roughness = roughness
    bsdf.inputs['Roughness'].default_value = roughness
    bsdf.inputs['Specular IOR Level'].default_value = specular_level
    bsdf.inputs['Metallic'].default_value = 0.0
    bsdf.inputs['Diffuse Roughness'].default_value = 0.68
    bsdf.inputs['Coat Weight'].default_value = 0.0
    bsdf.inputs['Sheen Weight'].default_value = 0.0


# A restrained burgundy tint is mixed into the approved kidney brown in linear
# RGB.  12.5% of the burgundy swatch (0.286, 0.006, 0.035) over the former
# brown (0.106, 0.028, 0.019) gives (0.1285, 0.02525, 0.0210).  Keeping this
# explicit makes reruns deterministic and leaves the quieter tube material
# unchanged.
KIDNEY_BROWN_WITH_BURGUNDY = (0.1285, 0.02525, 0.0210)
TUBE_WARM_BROWN = (0.145, 0.069, 0.050)

# Keep the approved soft-matte response. The correction removes specular
# lighting directly, rather than flattening the diffuse material response.
soften_material('01 | Matte warm brown red', KIDNEY_BROWN_WITH_BURGUNDY, 0.76, 0.0)
soften_material('02 | Muted warm ureter', TUBE_WARM_BROWN, 0.74, 0.0)

# Align the review studio with the heart's restrained three-disk lighting:
# a moderate key, a quiet rim, and a low warm fill.  The old values were
# materially brighter and lifted a large rectangular-looking key reflection.
scene.view_settings.look = 'None'
world_bg = scene.world.node_tree.nodes.get('Background')
# Use the approved heart studio palette verbatim.  The prior near-neutral
# kidney lights made the front key read as a broad white plastic reflection.
world_bg.inputs['Color'].default_value = (0.0165, 0.0235, 0.0365, 1.0)
world_bg.inputs['Strength'].default_value = 0.48
for name, energy, size, color in (
        ('Large softbox left', 1.86, 0.201, (1.0, 0.987, 0.977)),
        ('Broad fill right', 0.775, 0.147, (1.0, 0.817, 0.703)),
        ('Back edge softbox', 1.31, 0.146, (0.735, 0.823, 1.0))):
    light = studio_col.objects[name].data
    light.energy = energy
    light.size = size
    light.color = color
    # Preserve the existing diffuse key/rim/fill response while suppressing
    # direct specular highlights from every preview light.
    light.specular_factor = 0.0

camera = scene.camera
camera_data = camera.data


def render(name, loc, target, scale, samples=128):
    camera.location = loc
    camera.rotation_euler = (Vector(target) - camera.location).to_track_quat('-Z', 'Y').to_euler()
    camera_data.ortho_scale = scale
    scene.cycles.samples = 32 if DRAFT else samples
    scene.render.resolution_percentage = 70 if DRAFT else 100
    scene.render.filepath = str((Path(os.environ['TEMP']) / 'kidney_finish_draft.png')
                                if DRAFT else (PREVIEWS / name))
    bpy.ops.render.render(write_still=True)


if DRAFT:
    render('01_front_hero.png', (0.025, -0.32, 0.028),
           (0.0, 0.0, -0.025), 0.245)
elif not NEUTRAL_ONLY:
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

if not DRAFT:
    neutral = bpy.data.materials.get('Preview only | neutral clay')
    if neutral is None:
        neutral = bpy.data.materials.new('Preview only | neutral clay')
        neutral.use_nodes = True
        neutral.diffuse_color = (0.42, 0.42, 0.42, 1.0)
        shader = neutral.node_tree.nodes.get('Principled BSDF')
        shader.inputs['Base Color'].default_value = (0.42, 0.42, 0.42, 1.0)
        shader.inputs['Roughness'].default_value = 0.87
        shader.inputs['Metallic'].default_value = 0.0
    scene.view_layers[0].material_override = neutral
    render('09_neutral_sculpt.png', (0.0, -0.32, 0.025), (0.0, 0.0, -0.025), 0.245)
    scene.view_layers[0].material_override = None

    # The source file is the authoritative deliverable.  Do the final material
    # pass again after preview-only override state has been cleared, then save
    # it once at the end of the pipeline.  This prevents an intermediate save
    # from leaving the .blend behind the exported FBX and renders.
    soften_material('01 | Matte warm brown red', KIDNEY_BROWN_WITH_BURGUNDY, 0.76, 0.0)
    soften_material('02 | Muted warm ureter', TUBE_WARM_BROWN, 0.74, 0.0)
    for light_name in ('Large softbox left', 'Broad fill right', 'Back edge softbox'):
        studio_col.objects[light_name].data.specular_factor = 0.0
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=str(ROOT / 'KIDNEY-ASTRA-001.blend'))
