from pathlib import Path
import bpy, json, hashlib

OUT = Path(__file__).resolve().parent
SRC = OUT.parent.parent
def vec(v): return [round(float(x), 8) for x in v]
def inspect(path):
    bpy.ops.wm.open_mainfile(filepath=str(path))
    rig = bpy.data.objects['Buddy_Rig_Mixamo65']
    bones = {b.name: {'parent': b.parent.name if b.parent else None, 'head': vec(b.head_local), 'tail': vec(b.tail_local), 'rest': [vec(r) for r in b.matrix_local]} for b in rig.data.bones}
    meshes = {o.name: {'vertices':len(o.data.vertices),'polygons':len(o.data.polygons),'parent':o.parent.name if o.parent else None,
       'low_vertices': [{'co':vec(v.co),'weights':[(o.vertex_groups[g.group].name,round(g.weight,6)) for g in v.groups]} for v in o.data.vertices if v.co.z<0.025][:15]} for o in bpy.data.objects if o.type=='MESH'}
    return {'rig_name':rig.name,'rig_matrix':[vec(r) for r in rig.matrix_world], 'bones':bones, 'actions':{a.name:list(a.frame_range) for a in bpy.data.actions},'meshes':meshes}
data={v:inspect(SRC/f'SAUSAGE_BUDDY_{v}_v04.blend') for v in ('A','B')}
data['source_sha256']={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in SRC.glob('*v04.*') if p.suffix in ('.blend','.fbx')}
(OUT/'source_inspection.json').write_text(json.dumps(data,indent=2))
print('A_B_REST_EQUAL',data['A']['bones']==data['B']['bones'])
for n,b in data['A']['bones'].items():
    if any(x in n for x in ('Hips','UpLeg','Leg','Foot','ToeBase','Spine','Arm','Neck','Head')):print(n,b['head'],b['tail'])
print('MESHES',data['A']['meshes'])
print('ACTIONS',data['A']['actions'])
