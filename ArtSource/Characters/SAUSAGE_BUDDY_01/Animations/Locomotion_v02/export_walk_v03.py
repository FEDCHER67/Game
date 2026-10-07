"""Export the Walk action of a walk blend to an animation-only FBX for Unity.

Blender 5.2 background:
  blender -b --factory-startup --python export_walk_v03.py -- [--blend Walk_v03.blend] [--fbx Walk_v03.fbx]

Same settings as Walk_v02.fbx (Locomotion_v01): armature only, no leaf bones, all 65 bones, half-frame
bake, -Z forward / Y up. The pose is reset to rest before export so the FBX bind pose is the rest
pose (the v01 mistake). Refuses to overwrite. FBX take name: Buddy_Rig_Mixamo65|Walk.
"""
from pathlib import Path
import sys
import argparse
sys.dont_write_bytecode = True
import bpy

HERE = Path(__file__).resolve().parent
argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
ap = argparse.ArgumentParser()
ap.add_argument('--blend', default=str(HERE / 'Walk_v03.blend'))
ap.add_argument('--fbx', default=str(HERE / 'Walk_v03.fbx'))
args = ap.parse_args(argv)
out = Path(args.fbx)
assert not out.exists(), f'Refusing to overwrite {out}'

bpy.ops.wm.open_mainfile(filepath=args.blend)
rig = bpy.data.objects['Buddy_Rig_Mixamo65']
actions = [a.name for a in bpy.data.actions]
assert actions == ['Walk'], actions          # all-actions bake must export exactly one take
rig.animation_data.action = None
for pb in rig.pose.bones:
    pb.matrix_basis.identity()
bpy.context.view_layer.update()
bpy.ops.object.select_all(action='DESELECT')
rig.select_set(True)
bpy.context.view_layer.objects.active = rig
bpy.ops.export_scene.fbx(filepath=str(out), use_selection=True, object_types={'ARMATURE'},
                         add_leaf_bones=False, use_armature_deform_only=False,
                         bake_anim=True, bake_anim_use_all_actions=True, bake_anim_use_nla_strips=False,
                         bake_anim_step=0.5, bake_anim_simplify_factor=0.0,
                         axis_forward='-Z', axis_up='Y', apply_unit_scale=True, use_mesh_modifiers=False)
print('FBX_READY', out, flush=True)
