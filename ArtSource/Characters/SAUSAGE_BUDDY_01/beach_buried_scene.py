"""BEACH_BURIED (TASK-000545): the sand mound the guy is buried in, plus a review render of him buried up to the neck.

  blender -b --factory-startup --python ArtSource/Characters/SAUSAGE_BUDDY_01/beach_buried_scene.py -- --type-revision 1 --revision 1

Opens Types/BEACH_BURIED/SAUSAGE_BUDDY_BEACH_BURIED_vNN.blend (read only), lays him on his back in the idle pose (head
toward +Y, face up), heaps a body-shaped sand mound over him (head and toes out) and writes:
  Types/BEACH_BURIED/BEACH_BURIED_SandMound_vMM.blend / .fbx  - the mound alone, a static prop (origin = ground under his
                                                               hips, the NPC lies with its feet origin at (0, 0, 0.12),
                                                               rotated -90 deg about X)
  Types/BEACH_BURIED/Previews/buried_vMM/*.png                 - review renders
The dig-out mechanic is not built. Never overwrites an existing revision."""
import argparse, math, sys
from pathlib import Path
import bpy
from mathutils import Vector, Matrix, noise

HERE = Path(__file__).resolve().parent
sys.dont_write_bytecode = True
sys.path.insert(0, str(HERE))
import buddy_geo as G          # noqa: E402
import buddy_render as RD      # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument('--type-revision', type=int, required=True)
ap.add_argument('--revision', type=int, required=True)
args, _ = ap.parse_known_args(sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else [])
D = HERE / 'Types' / 'BEACH_BURIED'
SRC = D / f'SAUSAGE_BUDDY_BEACH_BURIED_v{args.type_revision:02d}.blend'
REV = f'v{args.revision:02d}'
OUT_BLEND, OUT_FBX = D / f'BEACH_BURIED_SandMound_{REV}.blend', D / f'BEACH_BURIED_SandMound_{REV}.fbx'
PREV = D / 'Previews' / f'buried_{REV}'
for p in (OUT_BLEND, OUT_FBX, PREV):
    if p.exists():
        sys.exit(f'{p} exists; choose a new --revision')

LIFT = 0.12            # the NPC's back sinks into the sand: feet origin raised by this much after lying down
# body-shaped mound along +Y (feet at y ~ 0, neck at y ~ 1.25 once he lies down): (y, half width, height)
MOUND = [(-0.20, 0.10, 0.10), (-0.10, 0.22, 0.20), (0.10, 0.32, 0.27), (0.36, 0.58, 0.40), (0.62, 0.64, 0.45), (0.88, 0.56, 0.42),
         (1.08, 0.42, 0.36), (1.20, 0.30, 0.24), (1.27, 0.16, 0.10)]                    # wide over the hands at his sides


def sand_mound(name, material, seg=28):
    secs = []
    for y, a, h in MOUND:
        secs.append((Vector((0.0, y, 0.0)), Vector((1, 0, 0)), Vector((0, 0, 1)), a, h))
    ob = G.loft(name, secs, material, seg=seg)
    for v in ob.data.vertices:                       # lumpy shovelled sand, flat underneath
        if v.co.z > 0.01:
            v.co.z += 0.018 * noise.noise(v.co * 7.0) * min(1.0, v.co.z / 0.08)
        else:
            v.co.z = 0.0
    ob.data.update()
    return ob


bpy.ops.wm.open_mainfile(filepath=str(SRC))
scene = bpy.context.scene
col = bpy.data.collections.new('BuriedScene')
scene.collection.children.link(col)
G.COLLECTION = col
rig = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
rig.animation_data.action = bpy.data.actions['Idle']
rig.data.pose_position = 'POSE'
scene.frame_set(1)
rig.matrix_world = Matrix.Translation((0.0, 0.0, LIFT)) @ Matrix.Rotation(math.radians(-90.0), 4, 'X')    # on his back, face up
sand = G.mat('BEACH_BURIED_Sand', (204, 168, 108), 0.95)          # damp dug-up sand
mound = sand_mound('BEACH_BURIED_SandMound', sand)

# the mound alone: blend + fbx (static prop)
for o in bpy.context.view_layer.objects:
    o.select_set(o is mound)
bpy.context.view_layer.objects.active = mound
bpy.ops.export_scene.fbx(filepath=str(OUT_FBX), use_selection=True, object_types={'MESH'}, axis_forward='-Z', axis_up='Y',
                         apply_unit_scale=True, use_mesh_modifiers=False)
tris = sum(len(p.vertices) - 2 for p in mound.data.polygons)

# review renders: studio, a sand patch under him
studio, cam, floor = RD.studio(scene)
floor.data.materials[0] = G.mat('BEACH_BURIED_Beach', (238, 224, 186), 0.95)
RD.shot(scene, cam, PREV / '01_buried_three_quarter.png', (-1.9, -1.6, 1.7), (0.0, 0.75, 0.15), lens=40, res=(1200, 900))
RD.shot(scene, cam, PREV / '02_buried_player_view.png', (0.0, -0.9, 1.7), (0.0, 1.0, 0.1), lens=35, res=(1200, 900))
RD.shot(scene, cam, PREV / '03_buried_head.png', (0.30, 0.85, 0.80), (0.0, 1.55, 0.22), lens=45, res=(1000, 900))
RD.shot(scene, cam, PREV / '04_buried_top.png', (0.0, 0.7, 4.5), (0.0, 0.7, 0.0), lens=35, res=(900, 1200))

# save the mound prop alone (drop the character and the studio from the saved file)
for o in list(bpy.data.objects):
    if o is not mound:
        bpy.data.objects.remove(o)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT_BLEND))
print('[BURIED] mound', OUT_FBX.name, 'tris', tris, 'previews in', PREV)
