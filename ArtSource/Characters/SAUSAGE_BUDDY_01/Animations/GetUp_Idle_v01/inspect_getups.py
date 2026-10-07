"""Read-only inspection of the original Buddy inputs. Outputs stay in this folder."""
from pathlib import Path
import sys, json, hashlib
sys.dont_write_bytecode = True
import bpy
HERE = Path(__file__).resolve().parent
SRC = HERE.parent.parent
bpy.ops.wm.open_mainfile(filepath=str(SRC/'SAUSAGE_BUDDY_A_v04.blend'))
rig = bpy.data.objects['Buddy_Rig_Mixamo65']
scene = bpy.context.scene
print('ACTIONS', [(a.name, list(a.frame_range)) for a in bpy.data.actions])
rig.animation_data.action = bpy.data.actions['Idle']
scene.frame_set(1)
out = {'idle_matrices': {b.name: [list(r) for r in b.matrix] for b in rig.pose.bones},
       'idle_hips': list(rig.pose.bones['mixamorig:Hips'].head), 'meshes': {}}
for name in ('Body','Face','Outfit'):
    o=bpy.data.objects[name]; ev=o.evaluated_get(bpy.context.evaluated_depsgraph_get()); me=ev.to_mesh()
    out['meshes'][name]={'vertices':len(o.data.vertices),'polygons':len(o.data.polygons),
        'triangles':sum(len(p.vertices)-2 for p in o.data.polygons),
        'min_z': min((o.matrix_world@v.co).z for v in me.vertices),
        'scale':list(o.scale),'materials':[m.name for m in o.data.materials]}
    ev.to_mesh_clear()
out['source_sha256']={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in [
    SRC/'SAUSAGE_BUDDY_A_v04.blend', SRC/'SAUSAGE_BUDDY_B_v04.blend',
    SRC/'SAUSAGE_BUDDY_A_v04.fbx', SRC/'SAUSAGE_BUDDY_B_v04.fbx',
    HERE.parent/'Locomotion_v01'/'Walk_v02.blend', HERE.parent/'Locomotion_v01'/'Walk_v02.fbx']}
(HERE/'source_inspection_v01.json').write_text(json.dumps(out,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in out.items() if k!='idle_matrices'},indent=2))
