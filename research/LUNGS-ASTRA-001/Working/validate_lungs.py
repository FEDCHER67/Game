"""Reopen blend and reimport FBX; compare structure and sampled breathing poses."""
import bpy
import json
from pathlib import Path
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1]
def state():
    meshes=[o for o in bpy.data.objects if o.type=='MESH']
    rigs=[o for o in bpy.data.objects if o.type=='ARMATURE']
    actions=list(bpy.data.actions)
    return {'meshes':{o.name:{'vertices':len(o.data.vertices),'triangles':sum(len(p.vertices)-2 for p in o.data.polygons),
                                'materials':[m.name for m in o.data.materials],
                                'armature_modifier':any(m.type=='ARMATURE' for m in o.modifiers)} for o in meshes},
            'rigs':{o.name:[b.name for b in o.data.bones] for o in rigs},
            'actions':{a.name:list(a.frame_range) for a in actions}}

def bounds():
    depsgraph=bpy.context.evaluated_depsgraph_get()
    points=[]
    for obj in bpy.data.objects:
        if obj.type!='MESH':continue
        ev=obj.evaluated_get(depsgraph)
        mesh=ev.to_mesh()
        points.extend(ev.matrix_world @ v.co for v in mesh.vertices)
        ev.to_mesh_clear()
    return {'min':[min(p[i] for p in points) for i in range(3)],
            'max':[max(p[i] for p in points) for i in range(3)],
            'size':[max(p[i] for p in points)-min(p[i] for p in points) for i in range(3)]}

def sampled_cycle(rig, action, last):
    rig.animation_data.action=action
    widths=[]
    for frame in range(1,last+1):
        bpy.context.scene.frame_set(frame)
        widths.append(bounds()['size'][0])
    return {'frames':last,'width_min':min(widths),'width_max':max(widths),
            'peak_frame':widths.index(max(widths))+1,
            'seam_width_error':abs(widths[0]-widths[-1]),
            'max_adjacent_width_change':max(abs(b-a) for a,b in zip(widths,widths[1:]))}

bpy.ops.wm.open_mainfile(filepath=str(ROOT/'LUNGS-ASTRA-001.blend'))
blend=state()
rig=next(o for o in bpy.data.objects if o.type=='ARMATURE')
blend['sampled_bounds']={}
for action_name,frame in [('STATIC_Rest',1),('GOOD_Breathe_50f',20),('BAD_Distress_24f',9)]:
    rig.animation_data.action=bpy.data.actions[action_name]
    bpy.context.scene.frame_set(frame)
    blend['sampled_bounds'][action_name]=bounds()
blend['cycles']={name:sampled_cycle(rig,bpy.data.actions[name],last) for name,last in
    [('STATIC_Rest',2),('GOOD_Breathe_50f',51),('BAD_Distress_24f',25)]}

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=str(ROOT/'LUNGS-ASTRA-001.fbx'))
fbx=state()
rigs=[o for o in bpy.data.objects if o.type=='ARMATURE']
fbx['sampled_bounds']={}
if rigs:
    rig=rigs[0]
    for state_name,frame in [('STATIC',1),('GOOD',20),('BAD',9)]:
        matching=[a for a in bpy.data.actions if state_name in a.name]
        if matching:
            rig.animation_data_create()
            rig.animation_data.action=matching[0]
            bpy.context.scene.frame_set(frame)
            fbx['sampled_bounds'][state_name]=bounds()
    fbx['cycles']={}
    for state_name,last in [('STATIC',2),('GOOD',51),('BAD',25)]:
        matching=[a for a in bpy.data.actions if state_name in a.name]
        if matching:
            fbx['cycles'][state_name]=sampled_cycle(rig,matching[0],last)

result={'blend_reopen':blend,'fbx_reimport':fbx}
with open(ROOT/'Working'/'validation.json','w') as f:json.dump(result,f,indent=2)
print('VALIDATION',json.dumps(result))
