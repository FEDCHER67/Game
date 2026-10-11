from pathlib import Path
import bpy
HERE=Path(__file__).resolve().parent
for path in [HERE.parent.parent/'SAUSAGE_BUDDY_A_v04.fbx',HERE/'Walk_v01.fbx']:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=str(path),ignore_leaf_bones=False,automatic_bone_orientation=False)
    rig=next(o for o in bpy.data.objects if o.type=='ARMATURE')
    print(path.name,'rigmatrix',rig.matrix_world)
    for short in ['Hips','LeftUpLeg','LeftLeg','LeftFoot','LeftArm','LeftForeArm']:
        b=rig.data.bones['mixamorig:'+short]
        print(short,'head',list(b.head_local),'tail',list(b.tail_local),'rotation',list(b.matrix_local.to_quaternion()))
