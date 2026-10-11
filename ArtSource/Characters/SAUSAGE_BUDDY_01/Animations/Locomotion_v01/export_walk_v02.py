"""v02: same authored motion, bind-pose-safe animation-only FBX export."""
from pathlib import Path
import bpy
HERE=Path(__file__).resolve().parent
for n in ('Walk_v02.blend','Walk_v02.fbx'):assert not (HERE/n).exists(),n
bpy.ops.wm.open_mainfile(filepath=str(HERE/'Walk_v01.blend'))
rig=bpy.data.objects['Buddy_Rig_Mixamo65']
bpy.ops.wm.save_as_mainfile(filepath=str(HERE/'Walk_v02.blend'))
rig.animation_data.action=None
for pb in rig.pose.bones:pb.matrix_basis.identity()
bpy.context.view_layer.update()
bpy.ops.object.select_all(action='DESELECT')
rig.select_set(True);bpy.context.view_layer.objects.active=rig
bpy.ops.export_scene.fbx(filepath=str(HERE/'Walk_v02.fbx'),use_selection=True,
    object_types={'ARMATURE'},add_leaf_bones=False,use_armature_deform_only=False,
    bake_anim=True,bake_anim_use_all_actions=True,bake_anim_use_nla_strips=False,
    bake_anim_step=.5,bake_anim_simplify_factor=0,
    axis_forward='-Z',axis_up='Y',apply_unit_scale=True,use_mesh_modifiers=False)
print('V02_EXPORT_READY',flush=True)
